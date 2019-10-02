
REMOTE_USER = 'proxyuser'
REMOTE_HOST = 'remote-host.org'
REMOTE_PORT = 22
REMOTE_KEY = '~/.ssh/id_rsa'
SSH_OPTS = ''

FORWARD = [
    {
        'local': {
            'gateway': True,      # If you want to bind to a gateway interface (to publish tunnel to the internet)
            'host': None,         # In local network an interface IP address or host you would like to bind to
            'port': 8010          # Port to bind to
        },
        'remote': {
            'gateway': False,     # Bind to a gateway interface (ssh host visible from internet)
            'host': '127.0.0.1',  # IP address of a service reachable on the remote host
            'port': 80            # Port reachable on the remote host
        },
        'validate': {
            'method': 'local_port_ping',             # Just a check if port is open, you can place there a callback
            'interval': 60,                          # Interval for checking the health and general status
            'wait_time_before_restart': 60,          # After failure wait this time before doing restart,
                                                     # maybe the tunnel will be back
            'kill_existing_tunnel_on_failure': True  # Exit existing tunnel if it is not working,
            # 'notify_url': 'http://some-slack-webhook-url'
        },
        'mode': 'local',  # Forward remote service to be visible locally (options: local, remote)
        'retries': 15
    }
]
