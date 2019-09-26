
import subprocess
import os
import paramiko
import abc
from socket import gethostbyname
from importlib.machinery import SourceFileLoader
from typing import List, NamedTuple, Callable, Union
from jinja2 import Environment, BaseLoader
from .settings import Config
from .exceptions import ConfigurationError
from .logger import Logger
from threading import RLock


class ConfigurationInterface(abc.ABC):
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


PortDefinition = NamedTuple('PortDefinition', [
    ('gateway', str), ('host', str), ('port', int), ('configuration', ConfigurationInterface)
])
ValidationDefinition = NamedTuple('ValidationDefinition', [
    ('method', str), ('interval', int), ('wait_time_before_restart', int), ('kill_existing_tunnel_on_failure', bool)
])


class RemotePortDefinition(PortDefinition):
    def get_host(self):
        host = self.host

        if self.gateway:
            host = self.configuration.get_remote_gateway()

        return self.configuration.parse(host)

    def get_port(self) -> int:
        return int(self.configuration.parse(str(self.port)))


class LocalPortDefinition(PortDefinition):
    def get_host(self) -> str:
        host = self.host

        if self.gateway:
            host = self.configuration.get_local_gateway()

        return self.configuration.parse(host)

    def get_port(self) -> int:
        return int(self.configuration.parse(str(self.port)))


class Forwarding(object):
    """
    Tunnel definition local <==> remote

    Aggregate decides about SSH forwarding params
    """

    local: LocalPortDefinition
    remote: RemotePortDefinition
    validate: ValidationDefinition
    mode: str
    configuration: ConfigurationInterface

    def __init__(self, local: LocalPortDefinition,
                 remote: RemotePortDefinition,
                 validate: ValidationDefinition,
                 mode: str,
                 configuration: ConfigurationInterface):
        self.local = local
        self.remote = remote
        self.validate = validate
        self.mode = mode
        self.configuration = configuration

    def is_forwarding_remote_to_local(self):
        """
        Provide a SSH tunnel for a remote resource for connection encryption

        Case 1: (wrap remote resource into a secure tunnel)
        Case 2: Expose service from a NAT of a remote network

        :return:
        """

        return self.mode == 'local'

    def is_forwarding_local_to_remote(self):
        """
        Expose local port via tunnel on remote machine
        :return:
        """

        return self.mode == 'from-nat-to-internet'

    def create_ssh_forwarding(self) -> str:
        """
        Creates a set of SSH options for forwarding
        :return:
        """

        c_str = ''

        if self.is_forwarding_local_to_remote():
            c_str += '-R '

        if self.is_forwarding_remote_to_local():
            c_str += '-L '

        c_str += self.local.get_host() + ':%i:%s:%i' % (
            self.local.get_port(),
            self.remote.get_host(),
            self.remote.get_port()
        )

        return self.configuration.parse(c_str)


class HostTunnelDefinitions(ConfigurationInterface):
    """
    Single host, multiple tunneling definitions
    """

    remote_user: str
    remote_host: str
    remote_port: int
    remote_key: str
    remote_password: str
    remote_passphrase: str
    ssh_opts: str
    forward: List[Forwarding]
    variables_post_processor: Callable
    _ssh: Union[paramiko.SSHClient, None]
    _cache: dict
    _lock: RLock

    def __init__(self):
        self._cache = {}
        self._ssh = None
        self._lock = RLock(timeout=120)

    def __str__(self):
        return 'Host<ssh=%s@%s:%i> (contains %i forwardings)' % (
            self.remote_user,
            self.remote_host,
            self.remote_port,
            len(self.forward)
        )

    def post_process_variables(self, variables: dict) -> dict:
        if self.variables_post_processor:
            return self.variables_post_processor(variables, self)

        return variables

    def parse(self, conn_string: str):
        to_inject = {
            'local_gw': self.get_local_gateway(),
            'remote_gw': '',
            'remote_docker_host': ''
        }

        to_inject = self.post_process_variables(to_inject)

        # make it lazy
        if "remote_gw" in conn_string and to_inject['remote_gw'] == '':
            to_inject['remote_gw'] = self.get_remote_gateway()

        if "remote_docker_host" in conn_string and to_inject['remote_docker_host'] == '':
            to_inject['remote_docker_host'] = self.get_remote_docker_host_ip()

        tpl = Environment(loader=BaseLoader, autoescape=False).from_string(conn_string)

        return tpl.render(**to_inject)

    def get_remote_gateway(self):
        with self._lock:
            if 'get_remote_gateway' not in self._cache:
                self._cache['get_remote_gateway'] = gethostbyname(self.remote_host).strip()

            return self._cache['get_remote_gateway']

    def get_remote_docker_host_ip(self):
        with self._lock:
            if 'get_remote_docker_host_ip' not in self._cache:
                stdin, stdout, stderr = self.ssh().exec_command("ip route|awk '/default/ { print $3 }'")
                self._cache['get_remote_docker_host_ip'] = stdout.read().decode('utf-8').strip()

            return self._cache['get_remote_docker_host_ip']

    def get_local_gateway(self):
        with self._lock:
            if 'get_local_gateway' not in self._cache:
                self._cache['get_local_gateway'] = subprocess.check_output(
                    "ip route| grep $(ip route |grep default | awk '{ print $5 }') | grep -v " +
                    "\"default\" | grep \"src\" | awk '/scope/ { print $9 }'", shell=True).decode('utf-8').strip()

            return self._cache['get_local_gateway']

    def ssh(self) -> paramiko.SSHClient:
        with self._lock:
            if not self._ssh:
                self._ssh = paramiko.SSHClient()
                self._ssh.load_system_host_keys()
                self._ssh.connect(hostname=self.remote_host, port=self.remote_port, username=self.remote_user,
                                  key_filename=self.remote_key, password=self.remote_password,
                                  passphrase=self.remote_passphrase, look_for_keys=False)

            return self._ssh


class ConfigurationFactory(object):
    """
    Factory method for the model
    """

    _definitions: list

    def __init__(self, config: Config):
        self._definitions = []
        self._load_from_directory(config.CONFIG_PATH + '/conf.d/')

    def _load_from_directory(self, path: str):
        Logger.debug('Looking up configuration at "%s" path' % path)

        if not os.path.isdir(path):
            raise NotADirectoryError('Specified directory "%s" does not exist' % path)

        files = os.scandir(path)

        for file in files:
            conf_path = path + '/' + file.name

            if not os.path.isfile(conf_path):
                continue

            raw_cfg = SourceFileLoader("Conf", conf_path).load_module()

            try:
                self._definitions.append(self._parse(raw_cfg))
            except AttributeError as e:
                raise ConfigurationError('Error while parsing "%s". %s' % (conf_path, str(e)))

    def provide_all_configurations(self):
        return self._definitions

    def _parse(self, raw) -> HostTunnelDefinitions:
        raw_opts = dir(raw)

        definition = HostTunnelDefinitions()
        definition.remote_host = raw.REMOTE_HOST
        definition.remote_port = raw.REMOTE_PORT
        definition.remote_user = raw.REMOTE_USER
        definition.remote_key = raw.REMOTE_KEY if 'REMOTE_KEY' in raw_opts else None
        definition.remote_passphrase = raw.REMOTE_KEY_PASSPHRASE if 'REMOTE_KEY_PASSPHRASE' in raw_opts else None
        definition.remote_password = raw.REMOTE_PASSWORD if 'REMOTE_PASSWORD' in raw_opts else None
        definition.forward = self._parse_forwarding(raw, configuration=definition)
        definition.variables_post_processor = raw.vars_post_processor if 'vars_post_processor' in raw_opts else None
        definition.ssh_opts = raw.SSH_OPTS

        return definition

    @staticmethod
    def _parse_forwarding(raw, configuration: HostTunnelDefinitions) -> List[Forwarding]:
        definitions = []

        for raw_definition in raw.FORWARD:
            definitions.append(Forwarding(
                local=LocalPortDefinition(
                    gateway=raw_definition.get('local').get('gateway', False),
                    port=raw_definition.get('local').get('port'),
                    host=raw_definition.get('local').get('host', ''),
                    configuration=configuration
                ),
                remote=RemotePortDefinition(
                    gateway=raw_definition.get('remote').get('gateway', False),
                    host=raw_definition.get('remote').get('host'),
                    port=raw_definition.get('remote').get('port'),
                    configuration=configuration
                ),
                validate=ValidationDefinition(
                    method=raw_definition.get('validate').get('method', 'none'),
                    interval=raw_definition.get('validate').get('interval', 300),
                    wait_time_before_restart=raw_definition.get('validate').get('wait_time_before_restart', 10),
                    kill_existing_tunnel_on_failure=raw_definition.get('validate').get(
                        'kill_existing_tunnel_on_failure', False)
                ),
                mode=raw_definition.get('mode'),
                configuration=configuration
            ))

        return definitions
