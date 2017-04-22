```
PN_USER=xxx
PN_PORT=22
PN_HOST=mydomain.org
PN_VALIDATE=local # local or ssh, both requires "nc" to be installed on local or remote ($PN_HOST) machine

# local port => destination port on remote server
PORTS[0]="8000>80"
PORTS[1]="22>2222"
```