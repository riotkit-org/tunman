
import os
import sys
import unittest
from ipaddress import IPv4Address
from typing import List
from unittest_data_provider import data_provider

sys.path.append(os.path.dirname(__file__) + "/../tunman")

from ..tunman.model import HostTunnelDefinitions
from ..tunman.logger import setup_dummy_logger


def create_ssh_connection_string_provider():
    return [
        # Regular, key-based
        [
            {
                'remote_host': '127.0.0.1',
                'remote_port': 22,
                'remote_password': '',
                'remote_key': '/tmp/some-key_rsa',
                'remote_user': 'riotkit',
                'ssh_opts': '-E /tmp/test.log'
            },
            {
                'ssh_executable': 'ssh'
            },
            [
                'ssh', 'riotkit@127.0.0.1', '-p 22', '-i /tmp/some-key_rsa',
                '-E /tmp/test.log'
            ],
            []
        ],

        # Password based, should not contain "-i" switch
        [
            {
                'remote_host': 'riotkit.org',
                'remote_port': 2222,
                'remote_password': 'stalin-was-a-panty-pisser',
                'remote_key': '',
                'remote_user': 'riotkit',
                'ssh_opts': '-E /tmp/test.log'
            },
            {
                'ssh_executable': '/usr/bin/ssh-other-binary'
            },
            [
                '/usr/bin/ssh-other-binary', 'riotkit@riotkit.org', '-p 2222',
                '-E /tmp/test.log'
            ],
            ['-i ', '-p 22 ']
        ],

        # Without key and custom ssh options (kwargs)
        [
            {
                'remote_host': '127.0.0.1',
                'remote_port': 22,
                'remote_password': '',
                'remote_key': '/tmp/some-key_rsa',
                'remote_user': 'riotkit',
                'ssh_opts': '-E /tmp/test.log'
            },
            {
                'ssh_executable': '', 'with_key': False, 'with_custom_opts': False
            },
            [],
            ['-E /tmp/test.log', '-i /tmp/some-key_rsa', 'ssh ']
        ]
    ]


class HostTunnelDefinitionsTest(unittest.TestCase):
    def setUp(self) -> None:
        setup_dummy_logger()

    @data_provider(create_ssh_connection_string_provider)
    def test_create_ssh_connection_string(self, definition_props: dict, method_kwargs: dict,
                                          expectations_contains: List[str], expectations_not_contains: List[str]):
        definition = HostTunnelDefinitions()

        for key, value in definition_props.items():
            definition.__setattr__(key, value)

        out = definition.create_ssh_connection_string(**method_kwargs)

        for expected_string in expectations_contains:
            assert expected_string in out, 'Expected that the output command will contain %s' % expected_string

        for unexpected_string in expectations_not_contains:
            assert unexpected_string not in out, 'Expected that the output command will not contain %s' % \
                                                 unexpected_string

    @staticmethod
    def test_get_remote_gateway():
        definition = HostTunnelDefinitions()
        definition.remote_host = 'localhost'

        assert definition.get_remote_gateway() == '127.0.0.1'

    @staticmethod
    def test_get_local_gateway():
        definition = HostTunnelDefinitions()
        definition.remote_host = '1.2.3.4'
        definition.remote_port = 2222
        definition.remote_user = 'international-workers-association'
        definition.remote_key = ''
        definition.remote_password = 'world-should-be-free'
        definition.remote_passphrase = 'social-revolution'

        gw = definition.get_local_gateway()

        assert IPv4Address(gw)

    def test_parse(self):
        definition = HostTunnelDefinitions()
        definition.variables_post_processor = lambda x, y: x

        gw = definition.get_local_gateway()
        parsed = definition.parse('Local GW is {{ local_gw }}')

        assert "Local GW is %s" % gw in parsed

    def test_create_ssh_keyscan_command(self):
        definition = HostTunnelDefinitions()
        definition.remote_port = 2222
        definition.remote_host = 'iwa-ait.org'

        out = definition.create_ssh_keyscan_command()

        assert "ssh-keyscan" in out
        assert "-p 2222" in out
        assert "iwa-ait.org" in out
