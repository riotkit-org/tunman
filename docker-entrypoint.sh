#!/bin/bash

echo " >> Correcting permissions"
chown -R revproxy:revproxy /home/revproxy

echo " >> Adding hosts to known hosts first time, if there are not all added"
su revproxy -c "/rn/bin/add-to-known-hosts.sh"

echo " >> Starting port forwarding"
exec su revproxy -c "$@"
