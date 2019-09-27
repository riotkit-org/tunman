#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""The app module, containing the app factory function."""

import argparse
import os
from tornado.ioloop import IOLoop
from tornado.web import Application, StaticFileHandler
from tunman.settings import Config
from tunman.app import TunManApplication
from tunman.views import ServeStatusHandler
from tunman.settings import ProdConfig, DevConfig


def start_application(config: Config, action: str):
    tunman = TunManApplication(config)

    try:
        if action == 'start':
            tunman.main()
            spawn_server(tunman, config.PORT, config.LISTEN)
            return
        elif action == 'send-public-key':
            tunman.send_public_key()
            return
        elif action == 'add-to-known-hosts':
            tunman.add_to_known_hosts()
        else:
            print('Invalid command name, possible commands: start, send-public-key, add-to-known-hosts')
    except KeyboardInterrupt:
        print('[CTRL] + [C]')
    finally:
        tunman.on_application_close()


def spawn_server(tunman: TunManApplication, port: int, address: str = ''):
    ServeStatusHandler.app = tunman

    srv = Application([
        (r'/static/(.*)', StaticFileHandler, {'path': os.path.dirname(os.path.abspath(__file__)) + '/tunman/static'}),
        (r"/", ServeStatusHandler)
    ])
    srv.listen(port, address)
    IOLoop.current().start()


if __name__ == '__main__':
    #
    # Arguments parsing
    #
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-c',
        '--config',
        help='Path to the configuration',
        default='.'
    )
    parser.add_argument(
        '-p',
        '--port',
        help='HTTP port to listen on',
        default=8008
    )
    parser.add_argument(
        '-l',
        '--listen',
        help='Address to listen on, defaults to 0.0.0.0',
        default=None
    )
    parser.add_argument(
        'action',
        metavar='N',
        type=str,
        help='Action. Choice: start, send-public-key, add-to-known-hosts'
    )
    parser.add_argument(
        '-e',
        '--env',
        help='Environment: debug, prod',
        default='prod'
    )

    parsed = parser.parse_args()
    config = ProdConfig() if parsed.env == 'prod' else DevConfig()
    config.CONFIG_PATH = parsed.config
    config.PORT = parsed.port
    config.LISTEN = parsed.listen

    start_application(config, parsed.action)
