
import paramiko

REMOTE_USER = 'revproxy'
REMOTE_HOST = 'backups.riotkit.org'
REMOTE_PORT = 9800
REMOTE_KEY = '/home/damian/id_test'
SSH_OPTS = ''

FORWARD = [
    {
        'local': {
            'gateway': True,
            'host': None,
            'port': 8010
        },
        'remote': {
            'gateway': False,
            'host': '{{ remote_docker_host }}',
            'port': 80
        },
        'validate': {
            'method': 'local_port_ping',
            'interval': 60,
            'wait_time_before_restart': 60,
            'kill_existing_tunnel_on_failure': True
        },
        'mode': 'local'
    },
    {
        'local': {
            'gateway': True,
            'host': None,
            'port': 5432
        },
        'remote': {
            'gateway': False,
            'host': '{{ remote_docker_host }}',
            'port': 5432
        },
        'validate': {
            'method': 'local_port_ping',
            'interval': 60,
            'wait_time_before_restart': 2,
            'kill_existing_tunnel_on_failure': True
        },
        'mode': 'local'
    }
]


# def vars_post_processor(variables: dict, definition):
#     ssh: paramiko.SSHClient = definition.ssh()
#     stdin, stdout, stderr = ssh.exec_command(
#         "getent hosts backup_primary_db_mysql_1 | awk '{ print $1 }'")
#
#     variables['remote_mysql_container_ip'] = stdout.read().decode('utf-8').strip()
#
#     print('!!!!!', variables)
#
#     return variables


# other docker container IP:
# getent hosts backup_primary_db_mysql_1 | awk '{ print $1 }'
