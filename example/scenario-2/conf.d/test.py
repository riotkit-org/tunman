
import paramiko
import subprocess

REMOTE_USER = 'proxyuser'
REMOTE_HOST = 'remote-host.org'
REMOTE_PORT = 22
REMOTE_KEY = '~/.ssh/id_rsa'
SSH_OPTS = ''


def vars_post_processor(variables: dict, host_configuration):
    # vars_post_processor() is a recognized name, just like a configuration variable
    # it is launched when local.host, remote.host and overall ssh arguments are processed
    #
    # How it works?
    # 1. You define variables there
    # 2. The templating system in TunMan executes your function and uses your variables

    # host_configuration: tunman.model.HostTunnelDefinitions
    # (not doing the typing, as you can run TunMan without installing it as a package)

    ssh: paramiko.SSHClient = host_configuration.ssh()

    # executes on REMOTE SSH
    # get IP address of a container that is named "backup_primary_db_mysql_1"
    # (this command should work with Alpine Linux and sh)
    stdin, stdout, stderr = ssh.exec_command(
        "getent hosts backup_primary_db_mysql_1 | awk '{ print $1 }'")

    variables['remote_mysql_container_ip'] = stdout.read().decode('utf-8').strip()

    return variables


# typing:
# tunnel_definition: tunman.model.Forwarding
# host_configuration: tunman.model.HostTunnelDefinitions

def mysql_check(tunnel_definition, host_configuration):
    # will raise "subprocess.CalledProcessError" on error
    subprocess.check_output('mysql -u root -proot -h %s -e "SELECT 1;"' % tunnel_definition.local.get_host(),
                            shell=True)

    return True


FORWARD = [
    {
        'local': {
            'gateway': True,      # If you want to bind to a gateway interface (to publish tunnel to the internet)
            'host': None,         # In local network an interface IP address or host you would like to bind to
            'port': 3306          # Port to bind to
        },
        'remote': {
            'gateway': False,     # Bind to a gateway interface (ssh host visible from internet)
            'host': '{{ remote_mysql_container_ip }}',  # Remote IP address is discovered by vars_post_processor()
            'port': 3306          # Port reachable on the remote host
        },
        'validate': {
            'method': mysql_check,                   # Just a check if port is open, you can place there a callback
            'interval': 60,                          # Interval for checking the health and general status
            'wait_time_before_restart': 60,          # After failure wait this time before doing restart,
                                                     # maybe the tunnel will be back
            'kill_existing_tunnel_on_failure': True  # Exit existing tunnel if it is not working
            # 'notify_url': 'http://some-slack-webhook-url'
        },
        'mode': 'local'  # Forward remote service to be visible locally (options: local, remote)
    }
]
