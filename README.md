# reverse-networking
Network setup automation scripts written in Bash, based on reverse proxy idea.
Allows to create multiple reverse tunnels from inside of NAT to the external server.

![example structure](./docs/Reverse%20networking%20infrastructure.png "Reverse networking structure")

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
