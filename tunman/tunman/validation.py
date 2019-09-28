
import psutil
import socket
from typing import Callable
from .model import Forwarding, HostTunnelDefinitions
from .logger import Logger


class Validation:
    @staticmethod
    def check_tunnel_alive(definition: Forwarding, configuration: HostTunnelDefinitions) -> bool:
        validation = definition.validate.method

        try:
            if type(validation) == Callable:
                return validation(definition, configuration)

            if validation == 'local_port_ping':
                return Validation.check_port_responding(
                    definition.local.get_host() if definition.local.get_host() else 'localhost',
                    definition.local.port
                )
            elif validation == 'remote_port_ping':
                return Validation.check_remote_port_responding(
                    definition.remote.get_host(),
                    definition.remote.port,
                    configuration
                )

        except Exception as e:
            Logger.error(str(e))
            return False

        # no defined health check
        return True

    @staticmethod
    def is_process_alive(signature: str) -> bool:
        for proc in psutil.process_iter():
            cmdline = " ".join(proc.cmdline())

            if signature in cmdline:
                return proc.pid

        return False

    @staticmethod
    def check_port_responding(host: str, port: int) -> bool:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            return sock.connect_ex((host, port)) == 0
        finally:
            sock.close()

    @staticmethod
    def check_remote_port_responding(host: str, port: int, configuration: HostTunnelDefinitions) -> bool:
        # raises an exception on failure
        configuration.ssh().exec_command('nc -zvw15 %s %i' % (host, port))

        return True
