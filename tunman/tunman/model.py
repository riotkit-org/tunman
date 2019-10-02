
import subprocess
import paramiko
from socket import gethostbyname
from typing import List, NamedTuple, Callable, Union
from jinja2 import Environment, BaseLoader
from datetime import date
from threading import RLock
from .logger import Logger
from .interfaces import ConfigurationInterface, PortDefinition


ValidationDefinition = NamedTuple('ValidationDefinition', [
    ('method', any), ('interval', int), ('wait_time_before_restart', int), ('kill_existing_tunnel_on_failure', bool),
    ('notify_url', str)
])


class RemotePortDefinition(PortDefinition):
    def get_host(self):
        host = self.host

        if not host:
            return '0.0.0.0'

        return self.configuration.parse(host)

    def get_port(self) -> int:
        return int(self.configuration.parse(str(self.port)))


class LocalPortDefinition(PortDefinition):
    def get_host(self) -> str:
        host = self.host

        if not host:
            return '0.0.0.0'

        return self.configuration.parse(host)

    def get_port(self) -> int:
        return int(self.configuration.parse(str(self.port)))


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

    # dynamic state
    starts_history: list
    _cache: dict

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
        return '<Forwarding mode=' + self.mode + ', forwarding=' + \
               self.create_ssh_forwarding_signature() + '> from ' + \
               str(self.configuration)


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
            'remote_docker_container': self.get_remote_docker_container_ip,
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
        with self._lock:
            ident = 'get_remote_interface_ip_(%s)' % name

            if ident not in self._cache:
                self._cache[ident] = self._exec_ssh(("ip addr show |grep %s | grep -E '^\s*inet' |" +
                                                    " grep -m1 global | awk '{ print $2 }' | sed 's|/.*||'") % name)

            return self._cache[ident]

    def get_remote_docker_container_ip(self):
        """
        Returns IP address of first non-lo interface
        :return:
        """

        with self._lock:
            ident = 'non_lo_iface'

            if ident not in self._cache:
                self._cache[ident] = self._exec_ssh('ls /sys/class/net/|grep -v lo|tail -n 1 2>&1')

        return self.get_remote_interface_ip(self._cache[ident])

    def get_remote_interface_gateway(self):
        with self._lock:
            ident = 'get_remote_interface_gateway'

            if ident not in self._cache:
                self._cache[ident] = self._exec_ssh(self._route_gateway_command)

            return self._cache[ident]

    def get_remote_gateway(self):
        with self._lock:
            if 'get_remote_gateway' not in self._cache:
                self._cache['get_remote_gateway'] = gethostbyname(self.remote_host).strip()

            return self._cache['get_remote_gateway']

    def get_remote_docker_host_ip(self):
        with self._lock:
            if 'get_remote_docker_host_ip' not in self._cache:
                self._cache['get_remote_docker_host_ip'] = self._exec_ssh("ip route|awk '/default/ { print $3 }'")

            return self._cache['get_remote_docker_host_ip']

    def get_local_gateway(self):
        with self._lock:
            if 'get_local_gateway' not in self._cache:
                self._cache['get_local_gateway'] = subprocess.check_output(self._route_gateway_command,
                                                                           shell=True).decode('utf-8').strip()

            return self._cache['get_local_gateway']

    @property
    def _route_gateway_command(self):
        return "ip route| grep $(ip route |grep default | awk '{ print $5 }') | grep -v " + \
                    "\"default\" | grep \"src\" | awk '{ print $5 }'"

    def _exec_ssh(self, cmd: str) -> str:
        Logger.debug('SSH cmd: %s' % cmd)
        stdin, stdout, stderr = self.ssh().exec_command(cmd)
        stderr_content = stderr.read().decode('utf-8')
        stdout_content = stdout.read().decode('utf-8').strip()

        if stderr_content:
            Logger.warning('SSH stderr: %s' % stderr_content)

        Logger.debug('SSH stdout: %s' % stdout_content)

        return stdout_content

    def ssh(self) -> paramiko.SSHClient:
        with self._lock:
            if not self._ssh:
                self._ssh = paramiko.SSHClient()
                self._ssh.load_system_host_keys()
                self._ssh.connect(hostname=self.remote_host, port=self.remote_port, username=self.remote_user,
                                  key_filename=self.remote_key, password=self.remote_password,
                                  passphrase=self.remote_passphrase, look_for_keys=False)

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

        cmd += "autossh -M 0 -N -f -o 'PubkeyAuthentication=yes' -o 'PasswordAuthentication=no' -nT %s" % args

        return cmd

