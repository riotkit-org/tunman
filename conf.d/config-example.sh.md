```
PN_USER=xxx
PN_PORT=22
PN_HOST=mydomain.org
PN_VALIDATE=local # local or ssh, both requires "nc" to be installed on local or remote ($PN_HOST) machine

# destination port on remote server => local port
PORTS[0]="80>8000"
PORTS[1]="2222>22"
```
