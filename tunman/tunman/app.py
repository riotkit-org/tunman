
import threading
import os
from .manager.ssh import TunnelManager
from .model import HostTunnelDefinitions
from .factory import ConfigurationFactory
from .settings import Config
from .logger import setup_logger, Logger
from time import sleep

"""
    Application main() - spawns threads managed by TunnelManager()
"""


class TunManApplication(object):
    _threads: list
    config: ConfigurationFactory
    settings: Config
    tun_manager: TunnelManager

    def __init__(self, config: Config):
        setup_logger(config.LOG_PATH, config.LOG_LEVEL)
        self.config = ConfigurationFactory(config)
        self.settings = config
        self.tun_manager = TunnelManager()
        self._threads = []

    def main(self):
        """ Start tunnelling and the web server """

        for config in self.config.provide_all_configurations():
            self._spawn_threads(config)

    def send_public_key(self):
        """ Execute ssh-copy-id for all configured hosts """

        for config in self.config.provide_all_configurations():
            Logger.info('Processing %s, please enter credentials when asked' % str(config))
            os.system(config.create_ssh_connection_string(ssh_executable='ssh-copy-id'))

    def add_to_known_hosts(self):
        """ Executes ssh-keyscan and adds signatures to ~/.ssh/known_hosts """

        os.system('mkdir -p ~/.ssh; touch ~/.ssh/known_hosts')
        path = os.path.expanduser('~/.ssh/known_hosts')

        with open(path, 'rb') as f:
            content = f.read().decode('utf-8')

        for config in self.config.provide_all_configurations():
            Logger.info('Adding %s to the %s' % (str(config), path))

            if config.remote_host in content:
                Logger.info('%s already present in the %s' % (config.remote_host, path))
                continue

            os.system(config.create_ssh_keyscan_command('ssh-keyscan') + ' >> ~/.ssh/known_hosts')

    def _spawn_threads(self, configuration: HostTunnelDefinitions):
        Logger.info('Spawning thread for %s' % configuration)

        for definition in configuration.forward:
            thr = threading.Thread(target=lambda: self.tun_manager.spawn_tunnel(definition, configuration))
            thr.start()
            self._threads.append(thr)
            sleep(0.5)

    def on_application_close(self):
        Logger.debug('Closing the application')
        self.tun_manager.close_all_tunnels()
