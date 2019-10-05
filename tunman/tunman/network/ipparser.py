
import re
from typing import List


class ParsedNetworkingInformation(object):
    """
    `ip route` command parser

    Provides a more stable way of extracting network information from `ip route`, it's more safe than using AWK or SED
    Because in various configurations the columns list is different, also on different systems the `ip route` gives
    different results.
    """

    _parsed: dict

    def __init__(self, ip_route_output: str):
        self._parsed = {
            'gw_interface': '',
            'gw_interface_ip': '',
            'gw_ip': '',
            'interfaces_ip': {}
        }
        self._parse(ip_route_output)

    def _parse(self, output: str):
        as_lines = output.split("\n")

        self._parse_gateway_interface(as_lines)
        self._parse_ip_of_interfaces(as_lines)
        self._parse_ip_of_gateway_interface()

    def _parse_gateway_interface(self, output: List[str]):
        for line in output:
            if "default via" in line:
                match_dev = re.search('dev ([a-z0-9]+)', line)
                match_ip = re.search('via ([0-9.]+)', line)

                self._parsed['gw_interface'] = match_dev.group(1)
                self._parsed['gw_ip'] = match_ip.group(1)
                break

    def _parse_ip_of_interfaces(self, output: List[str]):
        for line in output:
            if " dev " not in line or " src " not in line:
                continue

            match_dev = re.search('dev ([a-z0-9]+)', line)
            match_ip = re.search('src ([0-9.]+)', line)

            if not match_ip or not match_dev:
                raise Exception('Cannot parse `ip route` line: %s' % line)

            self._parsed['interfaces_ip'][match_dev.group(1)] = match_ip.group(1)

    def _parse_ip_of_gateway_interface(self):
        self._parsed['gw_interface_ip'] = self._parsed['interfaces_ip'][self._parsed['gw_interface']]

    @property
    def gateway_interface(self) -> str:
        """
        Gateway interface name ex. eth0 if all traffic goes through eth0 (default gateway)

        `default via 192.168.0.1 dev wlp2s0 proto dhcp metric 600`

        :return:
        """

        return self._parsed['gw_interface']

    @property
    def gateway_interface_ip(self) -> str:
        """
        Interface that is a default gateway ex. eth0 ip address
        Example: 192.168.0.1 is a gateway, and 192.168.0.100 is the IP address assigned on it, it will be returned

        `192.168.0.0/24 dev wlp2s0 proto kernel scope link src 192.168.0.109 metric 600`

        :return:
        """

        return self._parsed['gw_interface_ip']

    @property
    def gateway(self) -> str:
        """
        Get the gateway IP (the route where the traffic goes through ex. a WAN interface)

        Example: 192.168.0.1

        `default via 192.168.0.1 dev wlp2s0 proto dhcp metric 600`

        :return:
        """

        return self._parsed['gw_ip']

    def get_interface_ip(self, interface_name: str) -> str:
        if interface_name not in self._parsed:
            raise KeyError('%s is not a recognized interface in `ip route` output' % interface_name)

        return self._parsed['interfaces_ip'][interface_name]
