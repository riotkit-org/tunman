#!/bin/bash

cd "$( dirname "${BASH_SOURCE[0]}" )"
DIR=$(pwd)

if [[ ! -f ~/.ssh/id_rsa.pub ]]; then
    echo " >> RSA key not found, generating"
    ssh-keygen -t rsa -f ~/.ssh/id_rsa
fi

for config_file_name in ../conf.d/*.sh
do
    echo " >> Reading $config_file_name"
    source "$config_file_name"

    echo " >> Copying your ID to the $PN_USER@$PN_HOST:$PN_PORT, please log in"
    ssh-copy-id -i ~/.ssh/id_rsa "$PN_USER@$PN_HOST" -p $PN_PORT
done

if [[ $1 == "--loop" ]]; then
    while true; do
        sleep 10
    done
fi
