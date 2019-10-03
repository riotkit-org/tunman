Configuring SSH server
======================

We spent a lot of time testing various configurations of TunMan and OpenSSH Server.
In this document we share the results with you.

### Create a separate user for tunneling

TunMan assumes that on the remote SSH there will be a very basic environment such as fresh Alpine Linux,
and there will be limited access to the `/proc`. This removes a possibility to use `netstat` to detect frozen/zombie tunnels that are blocking ports.

So, tho avoid this TunMan has a setting `RESTART_ALL_TUNNELS_ON_FORWARDING_FAILURE = True` in root level of a configuration file.
The setting is killing all SSH sessions of current user to allow respawning of all sessions, in case when a port is blocked by a zombie session.
That's a workaround for a permissions limitation on target machine, TunMan cannot detect which `sshd` process opened which process due to limited access to `netstat` and `/proc`

**Recommendations:**
- Create a separate user for tunneling
- Set `RESTART_ALL_TUNNELS_ON_FORWARDING_FAILURE = True`


### Let the SSH server kill all zombie connections quickly

SSH Server is able to "ping" ssh connections, to check their activity. 
The frozen/zombie connections could be quickly disconnected. That preparation on server side allows to set `RESTART_ALL_TUNNELS_ON_FORWARDING_FAILURE = False` securely.

**Recommendations for the sshd_config file:**

```
# separate user allows to keep your sessions normally without disconnects
Match User tunman
    # each 10 seconds to a check of a connection
    ClientAliveInterval 10
    
    # kill the connection after 3 failures
    ClientAliveCountMax 3
    
    # this gives 3 * 10 = 30 seconds of zombie process
```
