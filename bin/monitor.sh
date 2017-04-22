#!/bin/bash

cd "$( dirname "${BASH_SOURCE[0]}" )"
source include/functions.sh

#
# Use local nc to validate the connection
# (this may be faster, but do not work if destination address is not accessible from external internet)
#
function performLocalValidation() {
    nc -z -v -w15 $1 $2 > /dev/null 2>&1
    return $?
}

#
# Connect to remote server via ssh and perform a validation using nc
# (safe way to perform validation)
#
function performRemoteValidation() {
    # include internal forwarding
    hosts=( $1 localhost )

    for host in ${hosts[@]}; do
        if ssh -o ConnectTimeout=30 -o PubkeyAuthentication=yes $PN_USER@$PN_HOST -p $PN_PORT "nc -z -v -w15 $host $2" > /dev/null 2>&1; then
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
        parsePortForwarding $forward_ports
        echo " >> Performing a health check for $config_file_name - $PN_HOST $dest_port"

        if [[ $PN_VALIDATE == "local" ]] && ! performLocalValidation $PN_HOST $dest_port; then
            echo "  ~ $PN_HOST $dest_port IS DOWN"
            executeHooks "monitor-down"
            continue

        elif [[ $PN_VALIDATE == "ssh" ]] && ! performRemoteValidation $PN_HOST $dest_port; then
            echo " ~ $PN_HOST $dest_port IS DOWN"
            executeHooks "monitor-down"
            continue

        elif [[ ! $PN_VALIDATE ]]; then
            echo "  ~ No validation method configured, please use PN_VALIDATE with values: ssh, local"
            continue
        fi

        echo "  ~ $PN_HOST $dest_port is up"
        executeHooks "monitor-up"
        echo ""
    done

    return 0
}

iterateOverConfiguration
