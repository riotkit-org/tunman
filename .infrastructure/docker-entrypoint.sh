#!/bin/bash

#
# Option to mount read-only id_rsa and id_rsa.pub on the root directory
# so the files will be copied to proper place and permissions will be corrected
#
# Reason: Each container run on original files would change permissions (chmod), that would charm git repository
#
if [[ -f /id_rsa ]] && [[ -f /id_rsa.pub ]]; then
    mkdir -p /home/tunman/.ssh
    cp /id_rsa /home/tunman/.ssh/
    cp /id_rsa.pub /home/tunman/.ssh/
    chown -R tunman:tunman /home/revproxy/.ssh
    chmod 700 /home/tunman/.ssh/id_rsa
fi

echo " >> Correcting permissions"
chown -R tunman:tunman /home/tunman 2>/dev/null

echo " >> Adding hosts to known hosts first time, if there are not all added"
su tunman -c "tunman add-to-known-hosts"

echo " >> Starting port forwarding"
exec su tunman -c "$@"
