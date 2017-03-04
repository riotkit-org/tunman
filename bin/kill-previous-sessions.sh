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
        IFS='>' read -r -a parts <<< "$forward_ports"
        source_port=${parts[0]}
        dest_port=${parts[1]}
        
        pid=$(ps aux |grep ssh|grep "$source_port:localhost:$dest_port"|grep -v "grep"|awk '{print $2}')

        if [[ $pid ]]; then
            echo " >> Killing $pid"
            kill -9 $pid
        fi
    done
done
