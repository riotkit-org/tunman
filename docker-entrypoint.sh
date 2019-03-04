#!/bin/bash

#
# Option to mount read-only id_rsa and id_rsa.pub on the root directory
# so the files will be copied to proper place and permissions will be corrected
#
# Reason: Each container run on original files would change permissions (chmod), that would charm git repository
#
if [[ -f /id_rsa ]] && [[ -f /id_rsa.pub ]]; then
    mkdir -p /home/revproxy/.ssh
    cp /id_rsa /home/revproxy/.ssh/
    cp /id_rsa.pub /home/revproxy/.ssh/
    chown -R revproxy:revproxy /home/revproxy/.ssh
    chmod 700 /home/revproxy/.ssh/id_rsa
fi

echo " >> Correcting permissions"
chown -R revproxy:revproxy /home/revproxy 2>/dev/null

echo " >> Adding hosts to known hosts first time, if there are not all added"
su revproxy -c "/rn/bin/add-to-known-hosts.sh"

echo " >> Starting port forwarding"
exec su revproxy -c "$@"
