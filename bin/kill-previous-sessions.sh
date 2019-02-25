#!/bin/bash

#--------------------------------------------
# Kill all previously opened ssh sessions
#
# @author RiotKit Team
# @see riotkit.org
#--------------------------------------------

cd "$( dirname "${BASH_SOURCE[0]}" )"
source include/functions.sh
DIR=$(pwd)
FILTER=${1}

for config_file_name in ../conf.d/*.sh
do
    if [[ "${FILTER}" ]] && [[ ${config_file_name} != *"${FILTER}"* ]]; then
        echo " .. Skipping ${config_file_name} (filtered out)"
        continue
    fi

    source "$config_file_name"

    echo " >> Killing all tunnels for ${config_file_name}"
    killAllTunnelsForHost "${PORTS}" "${PN_HOST}"
done
