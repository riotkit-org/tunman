
import subprocess
from socket import gethostbyname
from typing import List, NamedTuple, Callable, Union
from jinja2 import Environment, BaseLoader
from datetime import date
from threading import RLock
from .interfaces import ConfigurationInterface, PortDefinition
from .ssh import SSHClient
from .network.ipparser import ParsedNetworkingInformation


ValidationDefinition = NamedTuple('ValidationDefinition', [
    ('method', any), ('interval', int), ('wait_time_before_restart', int), ('kill_existing_tunnel_on_failure', bool),
    ('notify_url', str)
])


class RemotePortDefinition(PortDefinition):
    pass


class LocalPortDefinition(PortDefinition):
    pass


class Forwarding(object):
    """
    Tunnel definition local <==> remote

    Aggregate decides about SSH forwarding params
    """

    # immutable
    local: LocalPortDefinition
    remote: RemotePortDefinition
    validate: ValidationDefinition
    mode: str
    configuration: ConfigurationInterface
    retries: int
    use_autossh: bool
    health_check_connect_timeout: int
    warm_up_time: int
    time_before_restart_at_initialization: int
    wait_time_after_all_retries_failed: int

    # dynamic state
    starts_history: list
    _cache: dict

    def __init__(self, local: LocalPortDefinition,
                 remote: RemotePortDefinition,
                 validate: ValidationDefinition,
                 mode: str,
                 configuration: ConfigurationInterface,
                 retries: int,
                 use_autossh: bool,
                 health_check_connect_timeout: int,
                 warm_up_time: int,
                 time_before_restart_at_initialization: int,
                 wait_time_after_all_retries_failed: int):
        self.local = local
        self.remote = remote
        self.validate = validate
        self.mode = mode
        self.configuration = configuration
        self.retries = retries
        self.use_autossh = use_autossh
        self.health_check_connect_timeout = health_check_connect_timeout
        self.warm_up_time = warm_up_time
        self.time_before_restart_at_initialization = time_before_restart_at_initialization
        self.wait_time_after_all_retries_failed = wait_time_after_all_retries_failed

        # dynamic
        self._cache = {}
        self.starts_history = []

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

        return self.mode == 'remote'

    def create_ssh_forwarding_signature(self) -> str:
        """
        Creates a set of SSH options for forwarding
        :return:
        """

        if 'create_ssh_forwarding' in self._cache:
            return self._cache['create_ssh_forwarding']

        c_str = ' -o ServerAliveInterval=15 -o ServerAliveCountMax=4 -o ExitOnForwardFailure=yes '

        if self.remote.gateway or self.local.gateway:
            c_str += ' -g '

        if self.is_forwarding_local_to_remote():
            c_str += '-R '

            if not self.remote.gateway:
                c_str += '%s:' % self.remote.get_host()

            c_str += '%i:%s:%i' % (
                self.remote.get_port(),
                self.local.get_host(),
                self.local.get_port()
            )

        if self.is_forwarding_remote_to_local():
            c_str += '-L '

            if not self.local.gateway:
                c_str += '%s:' % self.local.get_host()

            c_str += '%i:%s:%i' % (
                self.local.get_port(),
                self.remote.get_host(),
                self.remote.get_port()
            )

        result = self.configuration.parse(c_str)
        self._cache['create_ssh_forwarding'] = result

        return result

    def create_ssh_arguments(self, with_forwarding: bool = True) -> str:
        """
        Creates full SSH arguments, including forwarding
        :return:
        """

        return self._create_ssh_connection_string(
            with_key=True,
            with_custom_opts=True,
            append=self.create_ssh_forwarding_signature() if with_forwarding else ''
        )

    def _create_ssh_connection_string(self, with_key: bool = True, with_custom_opts: bool = True,
                                      append: str = '') -> str:
        return self.configuration.create_ssh_connection_string(
            with_key=with_key,
            with_custom_opts=with_custom_opts,
            append=append
        )

    def on_tunnel_started(self):
        self.starts_history.append(date.today())

    @property
    def current_restart_count(self):
        return len(self.starts_history) - 1 if self.starts_history else 0

    def __str__(self) -> str:
        """ Visual representation for health checks and web gui for the human """

        return 'Forwarding of [%s <-> %s] for %s' % (
            self.local, self.remote, self.configuration
        )

    @property
    def ident(self) -> str:
        return 'Forward[' + self.local.ident + '][' + self.remote.ident + ']_at_' + self.configuration.ident


class HostTunnelDefinitions(ConfigurationInterface):
    """
    Single host, multiple tunneling definitions.
    Defines ACCESS to the host, where the SSH Server is placed at.
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
    restart_all_on_forward_failure: bool
    _ip_route: Union[ParsedNetworkingInformation, None]
    _ssh: Union[SSHClient, None]
    _cache: dict
    _lock: RLock

    def __init__(self):
        self._cache = {}
        self._ssh = None
        self._lock = RLock(timeout=120)
        self._ip_route = None

    def post_process_variables(self, variables: dict) -> dict:
        if self.variables_post_processor:
            return self.variables_post_processor(variables, self)

        return variables

    def parse(self, conn_string: str):
        """
        Parses connection string ex. {{ remote_gw }}:3306 into 192.168.1.2:3306

        :param conn_string:
        :return:
        """

        to_inject = {
            'local_gw': self.get_local_gateway()
        }

        to_inject = self.post_process_variables(to_inject)

        # make it lazy
        lazy_vars = {
            'remote_gw': self.get_remote_gateway,
            'remote_interface_gw': self.get_remote_interface_gateway,
            'remote_docker_host': self.get_remote_docker_host_ip,
            'remote_docker_container': self.get_remote_interface_gateway,
            'remote_interface_eth0': lambda: self.get_remote_interface_ip('eth0'),
            'remote_interface_eth1': lambda: self.get_remote_interface_ip('eth1'),
            'remote_interface_eth2': lambda: self.get_remote_interface_ip('eth2')
        }

        for key, callback in lazy_vars.items():
            if key in conn_string and (key not in to_inject or to_inject[key] == ''):
                to_inject[key] = callback()
            else:
                to_inject[key] = ''

        tpl = Environment(loader=BaseLoader, autoescape=False).from_string(conn_string)

        return tpl.render(**to_inject)

    def get_remote_interface_ip(self, name: str):
        return self._cached(
            'get_remote_interface_ip_(%s)' % name,
            lambda: self._get_ssh_client().get_interface_ip(name)
        )

    def get_remote_interface_gateway(self):
        return self._cached(
            'get_remote_interface_gateway',
            lambda: self._get_ssh_client().get_route_gateway()
        )

    def get_remote_gateway(self):
        return self._cached(
            'get_remote_gateway',
            lambda: gethostbyname(self.remote_host).strip()
        )

    def get_remote_docker_host_ip(self):
        return self._cached(
            'get_remote_docker_host_ip',
            lambda: self._get_ssh_client().get_docker_host_ip()
        )

    def get_local_gateway(self):
        return self._cached(
            'get_local_gateway',
            lambda: self._get_parsed_ip_route().gateway_interface_ip
        )

    def _get_parsed_ip_route(self) -> ParsedNetworkingInformation:
        if self._ip_route is None:
            self._ip_route = ParsedNetworkingInformation(
                subprocess.check_output('ip route', shell=True).decode('utf-8'))

        return self._ip_route

    def _cached(self, cache_id: str, callback: Callable) -> any:
        with self._lock:
            if cache_id not in self._cache:
                self._cache[cache_id] = callback()

            return self._cache[cache_id]

    def ssh_kill_all_sessions_on_remote(self):
        with self._lock:
            self._get_ssh_client().kill_all_sessions()

    def exec_ssh(self, cmd: str, env: dict = None) -> str:
        """
        Execute a command via SSH
        :param cmd:
        :param env:
        :return:
        """

        ssh = self._get_ssh_client()

        with self._lock:
            return ssh.exec(cmd, env=env)

    def _get_ssh_client(self) -> SSHClient:
        """
        RAW ssh client, DO NOT USE - have not implemented locking
        Only for internal model usage

        :return:
        """

        with self._lock:
            if not self._ssh:
                self._ssh = SSHClient(
                    host=self.remote_host, port=self.remote_port, user=self.remote_user,
                    key=self.remote_key, password=self.remote_password, passphrase=self.remote_passphrase
                )

            return self._ssh

    def create_ssh_connection_string(self, with_key: bool = True, with_custom_opts: bool = True,
                                     append: str = '', ssh_executable: str = '') -> str:
        opts = ssh_executable

        # custom ssh options defined in the configuration file
        if self.ssh_opts and with_custom_opts:
            opts += ' ' + self.ssh_opts + ' '

        # private key to use
        if self.remote_key and with_key:
            opts += ' -i %s' % self.remote_key

        # custom string that could be passed optionally
        opts += ' ' + append + ' '

        # -p user@host, basic information
        opts += '-p %i %s@%s' % (
            self.remote_port,
            self.remote_user,
            self.remote_host
        )

        return opts

    def create_ssh_keyscan_command(self, executable: str = 'ssh-keyscan'):
        return '%s -p %i %s' % (
            executable,
            self.remote_port,
            self.remote_host
        )

    def create_complete_command_with_supervision(self, forwarding: Forwarding):
        cmd = ''
        args = forwarding.create_ssh_arguments()

        if self.remote_password:
            cmd += 'sshpass -p "%s" ' % self.remote_password

        if forwarding.use_autossh:
            cmd += "autossh -M 0 -N -f -o 'PubkeyAuthentication=yes' -nT " + args
        else:
            cmd += 'ssh -N -T ' + args

        return cmd
