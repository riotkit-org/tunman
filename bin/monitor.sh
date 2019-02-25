#!/bin/bash

#--------------------------------------------
# Kill all previously opened ssh sessions
#
# @author RiotKit Team
# @see riotkit.org
#--------------------------------------------

cd "$( dirname "${BASH_SOURCE[0]}" )"
source include/functions.sh

function get_ping_cmd() {
    if [[ $PN_VALIDATE_COMMAND ]]; then
        echo $PN_VALIDATE_COMMAND
        return 0
    fi

    echo "nc -z -v -w15 $1 $2"
    return 0
}

#
# Use local nc to validate the connection
# (this may be faster, but do not work if destination address is not accessible from external internet)
#
function perform_local_validation() {
    command=$(get_ping_cmd $1 $2)

    echo " .. ${command}"
    eval "$command" > /dev/null 2>&1

    return $?
}

make_sure_tunnel_is_alive () {
    echo " >> There is a problem with SSH tunnels or the application..."

    if hasHostAtLeastOneTunnelDown "${PORTS}" "${PN_HOST}"; then
        echo " .. Restarting all SSH tunnels for host ${PN_HOST}, because at least one tunnel was down"
        echo " .. Killing all existing tunnels"
        killAllTunnelsForHost "${PORTS}" "${PN_HOST}"

        echo " .. Spawning new tunnels"
        setupTunnelsForHost "${PN_USER}" "${PN_HOST}" "${PN_PORT}" "${PN_TYPE}" "${PORTS}"
        echo " .. Done"

        sleep 2
    fi
}

#
# Connect to remote server via ssh and perform a validation using nc
# (safe way to perform validation)
#
function perform_remote_validation() {
    # include internal forwarding
    hosts=( ${1//\:/} localhost )

    for host in ${hosts[@]}; do
        command=$(get_ping_cmd $host $2)

        if ssh -o ConnectTimeout=30 -o PubkeyAuthentication=yes $PN_USER@$PN_HOST -p $PN_PORT "$command" > /dev/null 2>&1; then
            return 0
        fi
    done

    return 1
}

#
# Action to execute for every entry
#
function executeIterationAction() {
    config_file_name=$1

    for forward_ports in ${PORTS[*]}
    do
        parsePortForwarding ${forward_ports} ${PN_HOST}
        echo " >> Performing a health check for ${config_file_name}"

        local_gateway_host=${local_gateway_host//\:/}

        if [[ $PN_VALIDATE == "local" ]] && ! perform_local_validation $PN_HOST $remote_port; then
            echo "  ~ $PN_HOST $remote_port IS DOWN"
            make_sure_tunnel_is_alive ${config_file_name}
            executeHooks "monitor-down"

            continue

        elif [[ $PN_VALIDATE == "local-port" ]] && ! perform_local_validation ${local_gateway_host} $local_port; then
            echo "  ~ ${local_gateway_host} $local_port IS DOWN"
            make_sure_tunnel_is_alive ${config_file_name}
            executeHooks "monitor-down"

            continue

        elif [[ $PN_VALIDATE == "ssh" ]] && ! perform_remote_validation $PN_HOST $remote_port; then
            echo " ~ $PN_HOST $remote_port IS DOWN"
            make_sure_tunnel_is_alive ${config_file_name}
            executeHooks "monitor-down"

            continue

        elif [[ ! $PN_VALIDATE ]]; then
            echo "  ~ No validation method configured, please use PN_VALIDATE with values: ssh, local"
            continue
        fi

        echo "  ~ ${config_file_name} is up"
        executeHooks "monitor-up"
        echo ""
    done

    return 0
}

iterateOverConfiguration
