#
# CONFIGURATION REFERENCE
# -----------------------
#
#  This file should always contain all possible configuration options for documentation
#  It does not serve to run. The configuration should show possible options, not a well configured setup to run.
#


# ======================================================
#  Basic SSH connection details, common for all tunnels
# ======================================================
REMOTE_USER = 'proxyuser'
REMOTE_HOST = 'remote-host.org'
REMOTE_PORT = 22
REMOTE_KEY = '~/.ssh/id_rsa'
SSH_OPTS = ''

# ==========================================================================
#  Defined SSH tunnels that will be forwarded via SSH host specified above
# ==========================================================================
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
            'method': 'local_port_ping',              # Opts: local_port_ping, remote_port_ping,
                                                      #        you can place there a callback
            'interval': 60,                           # Checks tunnel health and status each X seconds
            'wait_time_before_restart': 60,           # After failure wait this time before doing restart,
                                                      # maybe the tunnel will be back without doing anything
            'kill_existing_tunnel_on_failure': True,  # Exit existing tunnel if it is not working,
            'notify_url': 'http://some-slack-webhook-url'  # Slack/Mattermost integration
        },
        'mode': 'local',       # local - forward remote resource to localhost, remote - reverse, to remote
        'retries': 15,                              # number of retries
        'wait_time_after_all_retries_failed': 600,  # time to wait, when all retries exhausted

        'use_autossh': False,  # use autossh? (not recommended), may be deprecated and removed in future releases

        'health_check_connect_timeout': 60,   # timeout for the health check
        'warm_up_time': 5,                    # wait this time before saying that the tunnel was started successfully

        'time_before_restart_at_initialization': 10,  # wait this time before restarting, when the process
                                                      # does not start from the beginning
    }
]
