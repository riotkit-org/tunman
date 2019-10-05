
import os
import sys
import unittest
from typing import Tuple
from unittest.mock import Mock, patch

sys.path.append(os.path.dirname(__file__) + "/../tunman")

from ..tunman.model import HostTunnelDefinitions, Forwarding, LocalPortDefinition, RemotePortDefinition
from ..tunman.manager.ssh import TunnelManager, Validation, SIGNAL_RESTART
from ..tunman.logger import setup_dummy_logger


def create_example_portmapping(config) -> tuple:
    return LocalPortDefinition(
        gateway=False,
        host='192.168.1.5',
        port=22,
        configuration=config
    ), RemotePortDefinition(
        gateway=False,
        host='192.168.5.20',
        port=2222,
        configuration=config
    )


class ManagerTest(unittest.TestCase):
    def prepare_data(self) -> Tuple[Forwarding, HostTunnelDefinitions]:
        setup_dummy_logger()

        # prepare dependencies
        config = HostTunnelDefinitions()
        local_port, remote_port = create_example_portmapping(config)

        validate = Mock()
        validate.interval = 0
        validate.wait_time_before_restart = 1
        validate.kill_existing_tunnel_on_failure = False

        fw = Forwarding(configuration=config, local=local_port, remote=remote_port,
                        validate=validate, mode='local', retries=5, use_autossh=False, health_check_connect_timeout=0,
                        warm_up_time=0, time_before_restart_at_initialization=0, wait_time_after_all_retries_failed=0)

        return fw, config

    def test_tunnel_loop_spawns_tunnel_on_died_process(self):
        """
        Scenario: is_process_alive() returns False
        Expectation: Tunnel restart will be called

        :return:
        """

        fw, config = self.prepare_data()

        with patch.object(Validation, 'is_process_alive') as is_process_alive_mock:
            is_process_alive_mock.return_value = False

            manager = TunnelManager()
            manager.spawn_ssh_process = Mock()
            result = manager._tunnel_loop(Mock(), fw, config, '-L 127.0.0.1:3306:192.168.1.5:3306')

            assert result == SIGNAL_RESTART

    def test_tunnel_loop_spawns_tunnel_on_health_check_failed(self):
        """
        Scenario: check_tunnel_alive() fails, it means that health check failed
        Expectation: Tunnel restart will be called

        :return:
        """
        fw, config = self.prepare_data()

        with patch.object(Validation, 'is_process_alive') as is_process_alive_mock:
            is_process_alive_mock.return_value = True

            with patch.object(Validation, 'check_tunnel_alive') as check_tunnel_alive_mock:
                check_tunnel_alive_mock.return_value = False

                manager = TunnelManager()
                manager.spawn_ssh_process = Mock()
                result = manager._tunnel_loop(Mock(), fw, config, '-L 127.0.0.1:3306:192.168.1.5:3306')

                assert result == SIGNAL_RESTART

    def test_tunnel_loop_will_not_respawn_tunnel_when_its_a_false_alarm(self):
        """
        Scenario: check_tunnel_alive() fails, it means that health check failed
                  But after giving the situation a time (1 sec configured), the service brings back automatically
        Expected: Do not take any action, if the service is back online

        :return:
        """

        fw, config = self.prepare_data()
        manager = TunnelManager()

        with patch.object(manager, '_carefully_sleep') as sleep_mock:
            sleep_mock.side_effect = [True, False]  # on False the loop should exit

            with patch.object(Validation, 'is_process_alive') as is_process_alive_mock:
                is_process_alive_mock.return_value = True

                with patch.object(Validation, 'check_tunnel_alive') as check_tunnel_alive_mock:
                    check_tunnel_alive_mock.side_effect = [False, True]

                    manager.spawn_ssh_process = Mock()
                    manager._tunnel_loop(Mock(), fw, config, '-L 127.0.0.1:3306:192.168.1.5:3306')

                    assert manager.spawn_ssh_process.call_count == 0
