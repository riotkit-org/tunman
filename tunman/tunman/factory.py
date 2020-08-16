
import os
from importlib.machinery import SourceFileLoader
from typing import List
from .settings import Config
from .exceptions import ConfigurationError
from .model import HostTunnelDefinitions, Forwarding, LocalPortDefinition, RemotePortDefinition, ValidationDefinition
from .logger import Logger


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

    def provide_all_configurations(self) -> List[HostTunnelDefinitions]:
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
        definition.restart_all_on_forward_failure = raw.RESTART_ALL_TUNNELS_ON_FORWARDING_FAILURE \
            if 'RESTART_ALL_TUNNELS_ON_FORWARDING_FAILURE' in raw_opts else False
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
                        'kill_existing_tunnel_on_failure', False),
                    notify_url=raw_definition.get('validate').get('notify_url', '')
                ),
                mode=raw_definition.get('mode'),
                configuration=configuration,
                retries=raw_definition.get('retries', 10),
                use_autossh=raw_definition.get('use_autossh', False),
                health_check_connect_timeout=raw_definition.get('health_check_connect_timeout', 60),
                warm_up_time=raw_definition.get('warm_up_time', 5),
                time_before_restart_at_initialization=raw_definition.get('time_before_restart_at_initialization', 10),
                wait_time_after_all_retries_failed=raw_definition.get('wait_time_after_all_retries_failed', 600)
            ))

        return definitions
