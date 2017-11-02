#!/bin/bash

#--------------------------------------------
# Bind network ports to the remote server
# using a reverse proxy strategy
#
# @author Wolnościowiec Team
# @see https://wolnosciowiec.net
#--------------------------------------------

cd "$( dirname "${BASH_SOURCE[0]}" )"
source include/functions.sh
DIR=$(pwd)

./kill-previous-sessions.sh

for config_file_name in ../conf.d/*.sh
do
    echo " >> Reading $config_file_name"
    source "$config_file_name"

    for forward_ports in ${PORTS[*]}
    do
        IFS='>' read -r -a parts <<< "$forward_ports"
        source_port=${parts[0]}
        dest_port=${parts[1]}
        dest_host=""

        if [[ "${parts[2]}" ]]; then
            dest_host="${parts[2]}:"

            if [[ "${dest_host}" == "@gateway:" ]]; then
                dest_host="$(getHostIpAddress $PN_HOST)"
            fi
        fi

        echo " --> Forwarding ${dest_host}${source_port}:${PN_HOST}:${dest_port}"
        autossh -M 0 -N -f -o "PubkeyAuthentication=yes" -o "PasswordAuthentication=no" -R "${dest_host}${source_port}:localhost:${dest_port}" "${PN_USER}@${PN_HOST}" -p ${PN_PORT}

        if [[ $? != 0 ]]; then
            echo " ~ The port forwarding failed, please verify if your SSH keys are well installed"
            exit 1
        fi
    done
done

if [[ $1 == "--loop" ]]; then
    while true; do
        sleep 10
    done
fi
