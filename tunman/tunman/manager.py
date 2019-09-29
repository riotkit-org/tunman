
import subprocess
import psutil
from typing import List, Union
from time import sleep
from threading import RLock
from .model import Forwarding, HostTunnelDefinitions
from .logger import Logger
from .validation import Validation
from .notify import Notify


class TunnelManager:
    _signatures: List[str]
    _procs: List[subprocess.Popen]
    _sleep_time = 10
    is_terminating: bool

    def __init__(self):
        self.is_terminating = False
        self._signatures = []
        self._procs = []
        self._lock = RLock(timeout=60)
        self._starts_history = {}

    def get_stats(self, definitions: List[Forwarding]) -> dict:
        definitions_status = {}

        for definition in definitions:
            proc = self._find_process_by_signature(definition.create_ssh_forwarding_signature())

            definitions_status[definition] = {
                'pid': proc.pid if proc else '',
                'is_alive': proc is not None,
                'starts_history': definition.starts_history,
                'restarts_count': definition.current_restart_count
            }

        return {
            'signatures': self._signatures,
            'status': definitions_status,
            'procs_count': len(self._procs),
            'is_terminating': self.is_terminating
        }

    def spawn_tunnel(self, definition: Forwarding, configuration: HostTunnelDefinitions):
        """
        Threads: Per thread

        :param definition:
        :param configuration:
        :return:
        """

        signature = definition.create_ssh_forwarding_signature()
        Logger.info('Created SSH args: %s' % definition.create_ssh_arguments())

        with self._lock:
            self._signatures.append(signature)

        self.spawn_ssh_process(definition, configuration, signature)

    def spawn_ssh_process(self, forwarding: Forwarding,
                          configuration: HostTunnelDefinitions, signature: str):

        """
        Spawns a SSH process and starts supervising

        Threads: Per thread

        :param forwarding:
        :param configuration:
        :param signature:
        :return:
        """

        # remove old, died processes from the internal registry
        with self._lock:
            self._clean_up()

        if self.is_terminating:
            return

        cmd = configuration.create_complete_command_with_supervision(forwarding)

        Logger.info('Spawning %s' % cmd)
        proc = subprocess.Popen(cmd, shell=True)

        # maintain the registry
        with self._lock:
            if self.is_terminating:
                return

            self._procs.append(proc)

            forwarding.on_tunnel_started()
            Notify.notify_tunnel_restarted(forwarding)

        sleep(10)

        # make a delayed retry on start
        if not Validation.is_process_alive(signature):
            try:
                stdout, stderr = [proc.stdout.read().decode('utf-8'), proc.stderr.read().decode('utf-8')]
            except:
                stdout, stderr = ['', '']

            Logger.error('Cannot spawn %s, stdout=%s, stderr=%s' % (cmd, stdout, stderr))
            sleep(15)

            return self.spawn_ssh_process(forwarding, configuration, signature)

        Logger.info('Process for "%s" survived initialization, got pid=%i' % (signature, proc.pid))
        self._tunnel_loop(forwarding, configuration, signature)

    def _tunnel_loop(self, definition: Forwarding, configuration: HostTunnelDefinitions, signature: str):
        """
        One tunnel = one thread of health monitoring and reacting

        Threads: Per thread

        :param definition:
        :param configuration:
        :param signature:
        :return:
        """

        while True:
            if not self._carefully_sleep(definition.validate.interval):
                return

            Logger.debug('Running checks for signature "%s"' % signature)

            if not Validation.is_process_alive(signature):
                Logger.error('The tunnel process exited for signature "%s"' % signature)
                return self.spawn_ssh_process(definition, configuration, signature)

            if not Validation.check_tunnel_alive(definition, configuration):
                Logger.error('The health check "%s" failed for signature "%s"' % (
                    definition.validate.method, signature))

                time_to_wait_on_health_check_failure = definition.validate.wait_time_before_restart
                sleep(time_to_wait_on_health_check_failure)

                # check if after given additional short wait time the health is OK
                if time_to_wait_on_health_check_failure and Validation.check_tunnel_alive(definition, configuration):
                    Logger.info('Tunnel "%s" was recovered with restart' % signature)
                    continue

                if definition.validate.kill_existing_tunnel_on_failure:
                    self._kill_process_by_signature(signature)

                return self.spawn_ssh_process(definition, configuration, signature)

    def _carefully_sleep(self, sleep_time: int):
        for i in range(0, sleep_time):
            if self.is_terminating:
                Logger.debug('Careful sleep: got termination signal')
                return False

            sleep(1)

        return True

    def close_all_tunnels(self):
        """
        Kill all processes spawned by the TunnelManager

        Threads: Called from main thread
        :return:
        """

        self.is_terminating = True

        for signature in self._signatures:
            proc = self._find_process_by_signature(signature)

            if proc:
                Logger.info('Killing %i (%s)' % (proc.pid, proc.name()))
                proc.kill()

            for proc in psutil.process_iter():
                cmdline = " ".join(proc.cmdline())

                if signature in cmdline:
                    proc.kill()

        for proc in self._procs:
            Logger.info('Killing %i' % proc.pid)
            proc.kill()

    @staticmethod
    def _find_process_by_signature(signature: str) -> Union[psutil.Process, None]:
        for proc in psutil.process_iter():
            cmdline = " ".join(proc.cmdline())

            if signature in cmdline and "autossh" in cmdline:
                return proc

        return None

    def _kill_process_by_signature(self, signature: str):
        proc = self._find_process_by_signature(signature)

        if proc:
            proc.kill()

    def _clean_up(self):
        """ Free up information about processes that no longer are alive,
            so the application will not attempt to kill when gracefully shutting down
        """

        for proc in self._procs.copy():
            Logger.debug('clean_up: Checking if process pid=%i is still alive' % proc.pid)

            if proc.poll() is not None:
                Logger.debug('clean_up: Freeing proc pid=%i' % proc.pid)

                try:
                    self._procs.remove(proc)
                except ValueError:
                    continue

