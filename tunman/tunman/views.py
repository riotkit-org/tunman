
import os
import json
from typing import Optional, Awaitable
from tornado.web import RequestHandler
from jinja2 import Environment, FileSystemLoader
from typing import List
from .app import TunManApplication
from .model import Forwarding


class ServeStatusHandler(RequestHandler):
    app: TunManApplication = None

    def data_received(self, chunk: bytes) -> Optional[Awaitable[None]]:
        pass

    def get(self):
        loader = FileSystemLoader(os.path.dirname(os.path.abspath(__file__)) + '/templates')
        tpl = Environment(loader=loader, autoescape=False).get_template('status.html.j2')

        self.write(tpl.render(**self._get_data()))

    def _get_data(self) -> dict:
        all_forwardings = self._get_forwardings()
        stats = self.app.tun_manager.get_stats(all_forwardings)
        data = {
            'forwardings': []
        }

        for definition in all_forwardings:
            forwarding = {
                'is_alive': False,
                'current_pid': '',
                'ident': definition.ident,
                'signature': definition.create_ssh_forwarding_signature(),
                'restarts_count': 0
            }

            if definition in stats['status']:
                forwarding['is_alive'] = stats['status'][definition]['is_alive']
                forwarding['current_pid'] = stats['status'][definition]['pid']
                forwarding['restarts_count'] = stats['status'][definition]['restarts_count']

            data['forwardings'].append(forwarding)

        return data

    def _get_forwardings(self) -> List[Forwarding]:
        all_definitions = []

        for host_tunnels in self.app.config.provide_all_configurations():
            for tunnel in host_tunnels.forward:
                all_definitions.append(tunnel)

        return all_definitions


class ServeJsonStatus(ServeStatusHandler):
    def get(self):
        """ Returns a JSON formatted status page """

        data = self._get_data()
        tunnels = {}
        global_status = True

        for forwarding in data['forwardings']:
            if not forwarding['is_alive']:
                global_status = False

            tunnels[forwarding['ident']] = {
                'ok': forwarding['is_alive'],
                'ident': forwarding['ident'] + '=' + str(forwarding['is_alive'])
            }

        self.add_header('Content-Type', 'application/json')
        self.write(
            json.dumps({
                'status': {
                    'tunnels': tunnels,
                    'ident': 'global_status=' + str(global_status),
                    'ok': global_status
                },
                'data': data
            }, indent=4)
        )
