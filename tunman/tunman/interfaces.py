import abc
from typing import Callable, NamedTuple


class ConfigurationInterface(abc.ABC):
    remote_user: str
    remote_host: str
    remote_port: int
    remote_key: str
    remote_password: str
    remote_passphrase: str
    forward: list
    ssh_opts: str
    variables_post_processor: Callable

    @abc.abstractmethod
    def post_process_variables(self, variables: dict) -> dict:
        pass

    @abc.abstractmethod
    def parse(self, conn_string: str) -> str:
        pass

    @abc.abstractmethod
    def get_remote_gateway(self) -> str:
        pass

    @abc.abstractmethod
    def get_remote_docker_host_ip(self) -> str:
        pass

    @abc.abstractmethod
    def get_local_gateway(self):
        pass

    @abc.abstractmethod
    def create_ssh_connection_string(self, with_key: bool = True, with_custom_opts: bool = True,
                                     append: str = '') -> str:
        pass

    @abc.abstractmethod
    def create_ssh_keyscan_command(self, executable: str = 'ssh-keyscan') -> str:
        pass

    def __str__(self):
        return 'Host<ssh=%s@%s:%i> (contains %i forwardings)' % (
            self.remote_user,
            self.remote_host,
            self.remote_port,
            len(self.forward)
        )


class PortDefinition(object):
    gateway: str
    host: str
    port: int
    configuration: ConfigurationInterface

    def __init__(self, gateway: str, host: str, port: int, configuration: ConfigurationInterface):
        self.gateway = gateway
        self.host = host
        self.port = port
        self.configuration = configuration

    def __str__(self):
        return 'PortDefinition<%s:%i, gw=%s' % (
            self.host, self.port, str(self.gateway)
        )

