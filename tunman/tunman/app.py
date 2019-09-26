
import threading
from .manager import TunnelManager
from .model import ConfigurationFactory, HostTunnelDefinitions
from .settings import Config
from .logger import setup_logger, Logger

"""
    Application main() - spawns threads managed by TunnelManager()
"""


class TunManApplication(object):
    _threads: list
    config: ConfigurationFactory
    tun_manager: TunnelManager

    def __init__(self, config: Config):
        setup_logger(config.LOG_PATH, config.LOG_LEVEL)
        self.config = ConfigurationFactory(config)
        self.tun_manager = TunnelManager()
        self._threads = []

    def main(self):
        for config in self.config.provide_all_configurations():
            self._spawn_threads(config)

    def _spawn_threads(self, configuration: HostTunnelDefinitions):
        Logger.info('Spawning thread for %s' % configuration)

        for definition in configuration.forward:
            thr = threading.Thread(target=lambda: self.tun_manager.spawn_tunnel(definition, configuration))
            thr.start()
            self._threads.append(thr)

    def on_application_close(self):
        Logger.info('Closing the application')
        self.tun_manager.close_all_tunnels()
