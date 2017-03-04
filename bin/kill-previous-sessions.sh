#!/bin/bash

#--------------------------------------------
# Kill all previously opened ssh sessions
#
# @author Wolnościowiec Team
# @see https://wolnosciowiec.net
#--------------------------------------------

cd "$( dirname "${BASH_SOURCE[0]}" )"
DIR=$(pwd)

for config_file_name in ../conf.d/*.sh
do
    source "$config_file_name"

    for forward_ports in ${PORTS[*]}
    do
        pid=$(ps aux |grep autossh|grep "$source_port:localhost:$dest_port"|grep -v "grep"|awk '{print $2}')

        if [[ $pid ]]; then
            echo " >> Killing $pid"
            kill -9 $pid
        fi
    done
done
