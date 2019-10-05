
import os
import sys
import unittest
from unittest_data_provider import data_provider

sys.path.append(os.path.dirname(__file__) + "/../tunman")

from ..tunman.network.ipparser import ParsedNetworkingInformation


def data():
    return [
        # Check local gateway interface IP address
        [
            '''
                default via 192.168.0.1 dev wlp2s0 proto dhcp metric 600 
                172.17.0.0/16 dev docker0 proto kernel scope link src 172.17.0.1 
                172.29.0.0/16 dev br-58e9d7c4f56c proto kernel scope link src 172.29.0.1 linkdown 
                192.168.0.0/24 dev wlp2s0 proto kernel scope link src 192.168.0.109 metric 600 
            ''',
            {
                'gw_interface': 'wlp2s0',
                'gw': '192.168.0.1',
                'gw_interface_ip': '192.168.0.109'
            }
        ],

        # With a VPN
        [
            '''
                default via 192.168.0.1 dev wlp2s0 proto dhcp metric 600 
                10.5.0.0/16 dev br-60c84770cf1c proto kernel scope link src 10.5.0.1 linkdown 
                10.10.74.0/24 dev tun0 proto static scope link metric 50 
                10.40.0.22 dev tun0 proto kernel scope link src 10.40.0.22 metric 50 
                10.74.73.0/24 dev tun0 proto static scope link metric 50 
                10.74.74.0/24 dev tun0 proto static scope link metric 50 
                10.74.75.0/24 dev tun0 proto static scope link metric 50 
                85.1.2.3 via 192.168.0.1 dev wlp2s0 proto static metric 600 
                172.17.0.0/16 dev docker0 proto kernel scope link src 172.17.0.1 
                172.18.0.0/16 dev br-0a61433a1ec6 proto kernel scope link src 172.18.0.1 linkdown 
                172.19.0.0/16 dev br-6392b79fc4d8 proto kernel scope link src 172.19.0.1 linkdown 
                172.21.0.0/16 dev br-00f6e41d973a proto kernel scope link src 172.21.0.1 linkdown 
                172.27.0.0/16 dev br-d3ecf485c906 proto kernel scope link src 172.27.0.1 linkdown 
                172.29.0.0/16 dev br-58e9d7c4f56c proto kernel scope link src 172.29.0.1 linkdown 
                172.31.0.0/16 dev tun0 proto static scope link metric 50 
                192.168.0.0/24 dev tun0 proto static scope link metric 50 
                192.168.0.0/24 dev wlp2s0 proto kernel scope link src 192.168.0.109 metric 600 
                192.168.0.1 dev wlp2s0 proto static scope link metric 600 
                192.168.2.0/24 dev tun0 proto static scope link metric 50 
                192.168.32.0/20 dev br-13da41dbf0cd proto kernel scope link src 192.168.32.1 linkdown 
                192.168.74.0/24 dev tun0 proto static scope link metric 50 
                192.168.96.0/20 dev br-ab66953755d3 proto kernel scope link src 192.168.96.1 linkdown 
                192.168.112.0/20 dev br-7ae3e41a3978 proto kernel scope link src 192.168.112.1 linkdown 
                192.168.160.0/20 dev br-fd5ffd8f13e2 proto kernel scope link src 192.168.160.1 linkdown
            ''',
            {
                'gw_interface': 'wlp2s0',
                'gw': '192.168.0.1',
                'gw_interface_ip': '192.168.0.109'
            }
        ]
    ]


class ParsedNetworkingInformationTest(unittest.TestCase):
    @data_provider(data)
    def test_resolves_values_correctly(self, output: str, checks: dict):
        parsed = ParsedNetworkingInformation(output)

        self.assertEqual(parsed.gateway, checks['gw'])
        self.assertEqual(parsed.gateway_interface_ip, checks['gw_interface_ip'])
        self.assertEqual(parsed.gateway_interface, checks['gw_interface'])
