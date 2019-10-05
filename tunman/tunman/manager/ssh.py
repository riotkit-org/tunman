
import subprocess
from typing import List
from time import sleep
from threading import RLock
from traceback import format_exc
from ..model import Forwarding, HostTunnelDefinitions
from ..logger import Logger
from ..validation import Validation
from ..notify import Notify
from .sysprocess import SystemProcessManager

SIGNAL_TERMINATE = 1
SIGNAL_RESTART = 2


class TunnelManager:
    """
    Spawns tunnels and supervises them
    """

    _signatures: List[str]
    _proc_manager: SystemProcessManager
    _sleep_time = 10
    is_terminating: bool

    def __init__(self):
        self.is_terminating = False
        self._signatures = []
        self._lock = RLock(timeout=60)
        self._starts_history = {}
        self._proc_manager = SystemProcessManager()

    def spawn_tunnel(self, definition: Forwarding, configuration: HostTunnelDefinitions):
        """
        Glues the parameters, restarts the loop on crash, handles application shutdown

        Threads: Per thread

        :param definition:
        :param configuration:
        :return:
        """

        try:
            signature = definition.create_ssh_forwarding_signature()
        except Exception as e:
            signature = 'not_working_signature'

            Logger.error('Cannot create a forwarding signature, maybe an SSH error? Error says %s' % str(e))
            Logger.error(format_exc())

        Logger.info('Created SSH args: %s' % definition.create_ssh_arguments())

        with self._lock:
            self._signatures.append(signature)

        retries_left = definition.retries

        while True:
            if retries_left == 0:
                retries_left = definition.retries
                self._carefully_sleep(definition.wait_time_after_all_retries_failed)

            try:
                signal = self.spawn_ssh_process(definition, configuration, signature)
            except:
                Logger.error(format_exc())
                self._carefully_sleep(5)
                continue

            if signal == SIGNAL_TERMINATE:
                return

            if signal != SIGNAL_RESTART:
                raise Exception('Application error, unknown signal "%s"' % str(signal))

            # should not matter, secures from too much CPU usage
            self._carefully_sleep(2)
            retries_left -= 1

    def spawn_ssh_process(self, forwarding: Forwarding,
                          configuration: HostTunnelDefinitions, signature: str) -> int:
        """
        Spawns a SSH process and delegates supervising
        After fresh run of SSH tunnel it performs initial check

        Threads: Per thread

        :param forwarding:
        :param configuration:
        :param signature:
        :return:
        """

        # remove old, died processes from the internal registry
        with self._lock:
            self._proc_manager.clean_up_already_exited_processes()

        if self.is_terminating:
            return SIGNAL_TERMINATE

        cmd = configuration.create_complete_command_with_supervision(forwarding)

        # maintain the registry
        with self._lock:
            proc = self._proc_manager.spawn(cmd)

            forwarding.on_tunnel_started()
            Notify.notify_tunnel_restarted(forwarding)

        self._carefully_sleep(forwarding.warm_up_time)

        # make a delayed retry on start
        if not Validation.is_process_alive(signature):
            stdout, stderr = self._proc_manager.communicate(proc)
            Logger.error('Cannot spawn %s, stdout=%s, stderr=%s' % (cmd, stdout, stderr))

            if not self._recover_from_error(stdout + stderr, configuration):
                self._carefully_sleep(forwarding.time_before_restart_at_initialization)

            return SIGNAL_RESTART

        Logger.info('Process for "%s" survived initialization, got pid=%i' % (signature, proc.pid))

        return self._tunnel_loop(proc, forwarding, configuration, signature)

    def _tunnel_loop(self, proc: subprocess.Popen, definition: Forwarding, configuration: HostTunnelDefinitions,
                     signature: str) -> int:
        """
        One tunnel = one thread of health monitoring and reacting

        Threads: Per thread

        :param definition:
        :param configuration:
        :param signature:
        :return:
        """

        Logger.debug('Starting monitoring loop for "%s"' % signature)

        while True:
            if not self._carefully_sleep(definition.validate.interval):
                return SIGNAL_TERMINATE

            if not self._proc_manager.wait(proc):
                Logger.error('The process just exited')
                return SIGNAL_RESTART

            Logger.debug('Running checks for signature "%s"' % signature)

            if not Validation.is_process_alive(signature):
                Logger.error('The tunnel process exited for signature "%s"' % signature)
                return SIGNAL_RESTART

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
                    self._proc_manager.kill_process_by_signature(signature)

                return SIGNAL_RESTART

    def get_stats(self, definitions: List[Forwarding]) -> dict:
        definitions_status = {}

        for definition in definitions:
            proc = self._proc_manager.find_process_by_signature(definition.create_ssh_forwarding_signature())

            definitions_status[definition] = {
                'pid': proc.pid if proc else '',
                'is_alive': proc is not None,
                'starts_history': definition.starts_history,
                'restarts_count': definition.current_restart_count,
                'ident': definition.ident
            }

        return {
            'signatures': self._signatures,
            'status': definitions_status,
            'procs_count': self._proc_manager.get_procs_count(),
            'is_terminating': self.is_terminating
        }

    @staticmethod
    def _recover_from_error(error_message: str, config: HostTunnelDefinitions) -> bool:
        """
        :param error_message:
        :param config:
        :return: Returns True when recovery was performed
        """

        if "remote port forwarding failed for listen port" in error_message and config.restart_all_on_forward_failure:
            Logger.warning('Killing all remote SSH sessions to free up the busy port')

            config.ssh_kill_all_sessions_on_remote()
            sleep(2)

            return True

        return False

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
        self._proc_manager.close_all_tunnels(self._signatures)
