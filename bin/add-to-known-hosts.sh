#!/bin/bash

#--------------------------------------------
# Kill all previously opened ssh sessions
#
# @author RiotKit Team
# @see riotkit.org
#--------------------------------------------

cd "$( dirname "${BASH_SOURCE[0]}" )"
source include/functions.sh

KNOWN_HOSTS_FILE=~/.ssh/known_hosts

#
# Iterate over each host and fetch it's fingerprint
#
# @framework method
#
executeIterationAction() {
    config_file_name=$1

    if contains_fingerprint ${PN_HOST} ${PN_PORT}; then
        echo " .. Fingerprint already present"
        return 0
    fi

    echo " .. Fetching a fingerprint for ${PN_HOST}:${PN_PORT}"
    ssh-keyscan -p "${PN_PORT}" "${PN_HOST}" >> ${KNOWN_HOSTS_FILE}
}

#
# $1 - hostname
# $2 - port
#
contains_fingerprint () {
    content=$(cat ${KNOWN_HOSTS_FILE})
    host_name=${1}

    # non-standard port is differently formatted
    if [[ "${2}" != "22" ]]; then
        host_name="[${1}]:${2}"
    fi

    if [[ "${content}" == *"${host_name} ssh-"* ]] \
        || [[ "${content}" == *"${host_name} ecdsa"* ]] \
        || [[ "${content}" == *"${host_name},"* ]]; then
        return 0
    fi

    return 1
}

echo " >> Fetching hosts fingerprint first time"
cat ${KNOWN_HOSTS_FILE}
iterateOverConfiguration
