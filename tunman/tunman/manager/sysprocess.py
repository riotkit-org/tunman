
import psutil
import subprocess
from typing import Union, List, Tuple
from ..logger import Logger


class SystemProcessManager:
    """
    Manages all opened processes
    """

    _procs: List[subprocess.Popen]

    def __init__(self):
        self._procs = []

    """
    System process helper methods
    """

    def spawn(self, cmd: str) -> subprocess.Popen:
        Logger.info('Spawning %s' % cmd)
        proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.wait(proc)

        if proc.poll() is None:
            self._procs.append(proc)

        return proc

    @staticmethod
    def communicate(proc: subprocess.Popen) -> Tuple[str, str]:
        try:
            streams = proc.communicate(timeout=2)
            return streams[0].decode('utf-8'), streams[1].decode('utf-8')
        except subprocess.TimeoutExpired:
            return '', ''

    def close_all_tunnels(self, signatures: List[str]):
        """
        Kill all processes spawned previously (finds by tunnel parameters)
        :return:
        """

        for signature in signatures:
            proc = self.find_process_by_signature(signature)

            if proc:
                Logger.info('Killing %i (%s)' % (proc.pid, proc.name()))
                self._kill_proc(proc)

            for proc in psutil.process_iter():
                cmdline = " ".join(proc.cmdline())

                if signature in cmdline:
                    self._kill_proc(proc)

        for proc in self._procs:
            Logger.info('Killing %i' % proc.pid)

            self._kill_proc(proc)

    @staticmethod
    def _kill_proc(proc):
        SystemProcessManager.wait(proc)
        proc.kill()

    @staticmethod
    def wait(proc) -> bool:
        try:
            proc.wait(timeout=1)
        except subprocess.TimeoutExpired:
            return True
        except psutil.TimeoutExpired:
            return True

        return False

    @staticmethod
    def find_process_by_signature(signature: str) -> Union[psutil.Process, None]:
        for proc in psutil.process_iter():
            cmdline = " ".join(proc.cmdline())

            if signature in cmdline and "ssh" in cmdline:
                return proc

        return None

    @staticmethod
    def kill_process_by_signature(signature: str):
        proc = SystemProcessManager.find_process_by_signature(signature)

        if proc:
            proc.kill()

    def clean_up_already_exited_processes(self):
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

    def get_procs_count(self) -> int:
        return len(self._procs)
