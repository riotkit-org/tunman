#!/bin/bash

#--------------------------------------------
# Bind network ports to the remote server
# using a reverse proxy strategy
#
# @author RiotKit Team
# @see riotkit.org
#--------------------------------------------

cd "$( dirname "${BASH_SOURCE[0]}" )"
source include/functions.sh
DIR=$(pwd)

#
# @framework method
#
executeIterationAction () {
    setupTunnelsForHost "${PN_USER}" "${PN_HOST}" "${PN_PORT}" "${PN_TYPE}" "${PORTS}"
}

main () {
    ./kill-previous-sessions.sh
    iterateOverConfiguration

    if [[ $1 == "--loop" ]]; then
        echo ' >> Running in a loop'

        while true; do
            sleep 10
        done
    fi

    if [[ $1 == "--healthcheck-loop" ]]; then
        echo " >> Running a healthcheck loop (SLEEP_TIME=${LOOP_SLEEP_TIME})"

        while true; do
            sleep ${LOOP_SLEEP_TIME:-5}
            $(dirname "${BASH_SOURCE[0]}")/../bin/monitor.sh
        done
    fi
}

main "$@"
