
REMOTE_USER = 'proxyuser'
REMOTE_HOST = 'remote-host.org'
REMOTE_PORT = 22
REMOTE_KEY = '~/.ssh/id_rsa'
SSH_OPTS = ''

FORWARD = [
    {
        'local': {
            'gateway': False,            # If you want to forward anything from the gateway interface
            'host': '127.0.0.1',         # Local src address
            'port': 8015                 # Local port to forward to remote
        },
        'remote': {
            'gateway': False,     # Bind to a gateway interface (ssh host visible from internet)
            'host': '127.0.0.1',  # IP address to bind to, the tunnel will be
                                  # visible on it (`telnet 127.0.0.1 80` on remote)
            'port': 80            # Port reachable on the remote host
        },
        'validate': {
            # remote_port_ping requires "nc" to be installed on remote host
            'method': 'remote_port_ping',            # Just a check if port is open, you can place there a callback
            'interval': 60,                          # Interval for checking the health and general status
            'wait_time_before_restart': 60,          # After failure wait this time before doing restart,
                                                     # maybe the tunnel will be back
            'kill_existing_tunnel_on_failure': True  # Exit existing tunnel if it is not working
            # 'notify_url': 'http://some-slack-webhook-url'
        },
        'mode': 'remote'  # Forward remote service to be visible locally (options: local, remote)
    }
]
