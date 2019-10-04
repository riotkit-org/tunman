
import psutil
import socket
from typing import Callable
from .model import Forwarding, HostTunnelDefinitions
from .logger import Logger


# @todo: Add connection timeouts
class Validation:
    @staticmethod
    def check_tunnel_alive(definition: Forwarding, configuration: HostTunnelDefinitions) -> bool:
        validation = definition.validate.method

        try:
            if type(validation) == Callable:
                return validation(definition, configuration)

            if validation == 'local_port_ping':
                return Validation.check_port_responding(
                    definition.local.get_host_as_ip_address(),
                    definition.local.port
                )
            elif validation == 'remote_port_ping':
                return Validation.check_remote_port_responding(
                    definition.remote.get_host_as_ip_address(),
                    definition.remote.port,
                    configuration
                )

        except Exception as e:
            Logger.error('Validation error:' + str(e))
            return False

        # no defined health check
        return True

    @staticmethod
    def is_process_alive(signature: str) -> bool:
        for proc in psutil.process_iter():
            cmdline = " ".join(proc.cmdline())

            if signature in cmdline:
                return proc.pid > 0

        return False

    @staticmethod
    def check_port_responding(host: str, port: int) -> bool:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(15)

        try:
            return sock.connect_ex((host, port)) == 0
        finally:
            sock.close()

    @staticmethod
    def check_remote_port_responding(host: str, port: int, configuration: HostTunnelDefinitions) -> bool:
        exit_code = int(configuration.exec_ssh('nc -zw15 %s %i 1>&2; echo $?' % (host, port)).strip())

        return exit_code == 0
