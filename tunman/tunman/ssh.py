
import paramiko
import socket
import time
from typing import Union
from traceback import format_exc
from .logger import Logger
from .network.ipparser import ParsedNetworkingInformation


class SSHClient:
    """
    Wrapper to a SSH client, adds timeouts, retries, error handling and the list of common commands
    """

    _ssh: paramiko.SSHClient
    _connection_setup: dict
    _timeout: int
    _ip_route: Union[ParsedNetworkingInformation, None]

    def __init__(self, host: str, port: int, user: str, key: str, password: str, passphrase: str, timeout: int = 15):
        self._ip_route = None
        self._timeout = timeout
        self._connection_setup = {
            'hostname': host, 'port': port, 'username': user,
            'key_filename': key, 'password': password,
            'passphrase': passphrase, 'look_for_keys': False
        }

        self._connect()

    def _connect(self):
        Logger.info('SSH internal connection is starting')
        self._ssh = paramiko.SSHClient()
        self._ssh.load_system_host_keys()
        self._ssh.connect(**self._connection_setup)

    def raw_exec_command(self, command: str, env: dict = None, retries: int = 3) -> tuple:
        try:
            stdin, stdout, stderr = self._ssh.exec_command(command, environment=env, timeout=self._timeout)
        except (socket.timeout, paramiko.ssh_exception.SSHException):
            Logger.warning('SSH command failed due to timeout, retrying')
            self._connect()
            return self.raw_exec_command(command, env, retries - 1)
        except:
            Logger.warning('SSH command not possible to execute')
            Logger.warning(format_exc())

            time.sleep(1)
            self._connect()
            return self.raw_exec_command(command, env, retries - 1)

        return stdin, stdout, stderr

    def exec(self, cmd: str, env: dict = None) -> str:
        Logger.debug('SSH cmd: %s' % cmd)
        stdin, stdout, stderr = self.raw_exec_command(cmd, env=env)
        stderr_content = stderr.read().decode('utf-8')
        stdout_content = stdout.read().decode('utf-8').strip()

        if stderr_content:
            Logger.warning('SSH stderr: %s' % stderr_content)

        Logger.debug('SSH stdout: %s' % stdout_content)

        return stdout_content

    def kill_all_sessions(self):
        """ Kill all SSH sessions on the remote, then reconnect """

        try:
            self.exec('killall sshd || true')
        except paramiko.ssh_exception.SSHException:
            pass

        self._connect()

    def get_interface_ip(self, name: str) -> str:
        return self._get_parsed_ip_route().get_interface_ip(name)

    def get_docker_host_ip(self) -> str:
        return self._get_parsed_ip_route().gateway

    def get_route_gateway(self) -> str:
        return self._get_parsed_ip_route().gateway_interface_ip

    def _get_parsed_ip_route(self) -> ParsedNetworkingInformation:
        if self._ip_route is None:
            self._ip_route = ParsedNetworkingInformation(self.exec('ip route'))

        return self._ip_route
