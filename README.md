# reverse-networking
Network setup automation scripts written in Bash, based on reverse proxy idea.
Allows to create multiple reverse tunnels from inside of NAT to the external server.

![example structure](./docs/Reverse%20networking%20infrastructure.png "Reverse networking structure")

## Requirements

Those packages needs to be installed:
- bash
- autossh
- ssh (client)
- awk
- grep
- nc

*The remote server needs to support public-key authorization method.*

## Setup

- Put your configuration files into `conf.d`

```
1. File must be with ".sh" extension
2. File must be executable (eg. chmod +x "webserver.sh")
3. File must be in a proper syntax and implement proper configuration variables
   described as an example in the "config-example.sh.md"
```

Send public key to all servers described in your configuration
so the communication could be without a password using a ssh key.

Run: `./bin/send-public-key.sh`

- Bind your ports to the external server

Run: `./bin/bind-network.sh`

That's all!
Your local services should be exposed to the remote server and be
visible on eg. http://localhost:1234, so you need an internal proxy or
a load balancer like nginx to forward the traffic to the internet.

## Example configurations


##### Expose MySQL from docker container

How to connect between two separate docker networks using SSH, and access a hidden MySQL server.

```gherkin
Given we have a HOST_1 with SSH container + MySQL container
And we have a client HOST_2
When we want to access MySQL:3306 from HOST_2
Then we make a tunnel from HOST_2 to HOST_1 SSH container that exposes db_mysql:3306
And we make it available as a localhost:3307 at HOST_2
```

```bash
PN_USER=revproxy        # HOST_1 user in SSH
PN_PORT=9800            # HOST_1 port
PN_HOST=192.168.0.114   # HOST_1 host
PN_VALIDATE=none
PN_TYPE=local           # connection type - we access remote resource, not exposing self to remote
PN_SSH_OPTS=            # optional SSH options
PORTS[0]="3307>3306>db_mysql"   # HOST_1 container name
```

##### Expose ports to external server

Expose health check endpoints of a machine hidden behind NAT/firewall to an external machine via SSH.

```gherkin
Given we have a HOST_1 that is a VPS with public IP address and SSH server
And we have a HOST_2 that is behind NAT
When we want to access /healthcheck endpoint placed at HOST_2 from internet we call http://some-subdomain.HOST_1/healthcheck
Then we make a tunnel from HOST_2 to HOST_1 exposing a HTTP webserver from HOST_2 to HOST_1:8000
```

```bash
PN_USER=some_host_1_user
PN_PORT=22
PN_HOST=host_1.org
PN_VALIDATE=local
PN_TYPE=reverse
PN_SSH_OPTS=

# optional:
#PN_VALIDATE_COMMAND="curl http://mydomain.org" # custom validation command that will be ran locally or remotely

# destination port on remote server => local port, will be available as localhost:8000 on HOST_1
PORTS[0]="80>8000"

# requires GatewayPorts in SSH to be enabled, can be insecure, will be available at PUBLIC_IP_ADDRESS:8001
# easier option to configure, does not require a webserver to expose local port to the internet
#PORTS[2]="80>8001>@gateway" # port will be available publicly
```

#### Monitoring

There is a tool in `./bin/monitor.sh` that verifies all tunnels by doing a ping
on every forwarded port.

To take an action on detected failure place your hook in the hooks.d/monitor-down.d

##### Configuration

Set `PN_VALIDATE` to check the tunnel health using a simple ping to the port with `nc`.

Possible values:
- ssh: Executes `nc` on remote machine in case the service is not accessible from outside
- local: Executes `nc` locally to ping remote machine's port

Use `PN_VALIDATE_COMMAND` for custom validation executed locally or remotely if `nc` is not enough.

Examples:
- PN_VALIDATE_COMMAND="/bin/true" # for testing purposes, try it yourself
- PN_VALIDATE_COMMAND="/bin/false" # for testing
- PN_VALIDATE_COMMAND="curl http://your-domain.org:8002"
