#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""The app module, containing the app factory function."""

import argparse
import os
import logging
from tornado.ioloop import IOLoop
from tornado.web import Application, StaticFileHandler

try:
    from .tunman.settings import Config
    from .tunman.app import TunManApplication
    from .tunman.views import ServeStatusHandler, ServeJsonStatus
    from .tunman.settings import ProdConfig, DevConfig
except ImportError:
    from tunman.settings import Config
    from tunman.app import TunManApplication
    from tunman.views import ServeStatusHandler, ServeJsonStatus
    from tunman.settings import ProdConfig, DevConfig


def start_application(config: Config, action: str):
    tunman = TunManApplication(config)

    try:
        if action == 'start':
            tunman.main()
            spawn_server(tunman, config.PORT, config.LISTEN, config.SECRET_PREFIX)
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


def spawn_server(tunman: TunManApplication, port: int, address: str = '', secret_prefix: str = ''):
    ServeStatusHandler.app = tunman

    prefix = '/'

    if secret_prefix:
        prefix += secret_prefix + "/"

    srv = Application([
        (r"" + prefix + "static/(.*)", StaticFileHandler, {'path': os.path.dirname(os.path.abspath(__file__)) + '/tunman/static'}),
        (r"" + prefix + "health", ServeJsonStatus),
        (r"" + prefix, ServeStatusHandler)
    ])

    # disable logger
    hn = logging.NullHandler()
    hn.setLevel(logging.DEBUG)

    if tunman.settings.DEBUG is False:
        for logger_name in ['tornado.application', 'tornado.general']:
            logging.getLogger(logger_name).addHandler(hn)
            logging.getLogger(logger_name).propagate = False

    srv.listen(port, address)
    IOLoop.current().start()


def main():
    #
    # Arguments parsing
    #
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-c',
        '--config',
        help='Path to the configuration',
        default=os.getenv('TUNMAN_CONFIG', '.')
    )
    parser.add_argument(
        '-p',
        '--port',
        help='HTTP port to listen on',
        default=8015
    )
    parser.add_argument(
        '-l',
        '--listen',
        help='Address to listen on, defaults to 0.0.0.0',
        default=None
    )
    parser.add_argument(
        '-s',
        '--secret-prefix',
        default=os.getenv('TUNMAN_SECRET_PREFIX', ''),
        help='Add a subdirectory prefix to the URL example: https://your-domain.org/some-secret-code-here/health'
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
        default=os.getenv('TUNMAN_ENV', 'prod')
    )

    parsed = parser.parse_args()
    config = ProdConfig() if parsed.env == 'prod' else DevConfig()
    config.CONFIG_PATH = parsed.config
    config.PORT = parsed.port
    config.LISTEN = parsed.listen
    config.SECRET_PREFIX = parsed.secret_prefix

    start_application(config, parsed.action)


if __name__ == '__main__':
    main()
