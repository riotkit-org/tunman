
#
# Common methods
#   Naming convention: Common methods and the framework methods are camelCase, the rest is snake_case
#

resetIteration() {
    PN_USER=""
    PN_PORT=""
    PN_HOST=""
    PN_TYPE=remote
    PN_SSH_OPTS=

    PN_VALIDATE=""
    PN_VALIDATE_COMMAND=""
    PORTS=()
}

iterateOverConfiguration() {
    cd "$( dirname "${BASH_SOURCE[0]}" )"
    DIR=$(pwd)

    for config_file_name in ../../conf.d/*.sh
    do
        resetIteration
        source $config_file_name
        executeIterationAction $config_file_name
    done
}

#
# @param $1 port_definition
# @param $2 PN_HOST
#
parsePortForwarding() {
    port_definition=$1
    PN_HOST=$2

    IFS='>' read -r -a parts <<< "${port_definition}"
    local_port=${parts[0]}
    remote_port=${parts[1]}
    remote_port_host="localhost:"
    local_gateway_host=""

    #
    # gateway at remote means public server IP address
    #
    if [[ "${parts[2]}" ]]; then
        remote_port_host="${parts[2]}:"

        if [[ "${remote_port_host}" == "@gateway:" ]]; then
            remote_port_host="$(getHostIpAddress $PN_HOST):"
        fi
    fi

    #
    # local gateway means our public IP address
    #
    if [[ ${parts[3]} ]]; then
        local_gateway_host="${parts[3]}:"

        if [[ "${local_gateway_host}" == "@gateway:" ]]; then
            local_gateway_host="$(getSelfIpAddress):"
        fi
    fi
}

executeHooks() {
    for hook_name in $(ls ../../hooks.d/$1.d |grep .sh)
    do
        file_name=$(basename "$hook_name")
        extension="${file_name##*.}"

        if [[ $extension != "sh" ]]; then
            continue
        fi

        echo "     * Executing hook: $hook_name"
        source ../../hooks.d/$1.d/$hook_name
    done
}

#
# @param $1 host name
#
getHostIpAddress() {
    getent hosts $1 | awk '{ print $1 }'
}

getSelfIpAddress () {
    if [[ -f /.dockerenv ]]; then
        awk 'END{print $1}' /etc/hosts
        return 0
    fi

    # get IP address of a network, that is a default gateway
    ip route| grep $(ip route |grep default | awk '{ print $5 }') | grep -v "default" | awk '/scope/ { print $9 }'
    return 0
}

#
# Creates arguments for the SSH forwarding
#   Examples:
#     Gateway: "10.50.30.40:3307:db_mysql:3306"
#     To localhost: "3307:db_mysql:3306"
#     From remote localhost to local localhost: "3307:localhost:3306"
#
# @param $1 port_definition
# @param $2 PN_HOST
#
createForwarding() {
    parsePortForwarding "${1}" "${2}"

    echo "${local_gateway_host}${local_port}:${remote_port_host}${remote_port}"
    return 0
}

#
# Factory method + spawner, basing on the arguments creates a proper command
#
spawnForwarding () {
    port_definition=$1
    PN_USER=$2
    PN_HOST=$3
    PN_PORT=$4
    PN_TYPE=$5

    forwarding=$(createForwarding "${port_definition}" "${PN_HOST}")

    if [[ ${PN_TYPE} == "local" ]]; then
        echo " --> Forwarding locally ${forwarding}"
        spawnAutossh ${PN_SSH_OPTS} -L "${forwarding}" "${PN_USER}@${PN_HOST}" -p ${PN_PORT}

        return $?
    fi

    echo " --> Forwarding ${forwarding}"
    spawnAutossh ${PN_SSH_OPTS} -R "${forwarding}" "${PN_USER}@${PN_HOST}" -p ${PN_PORT}

    return $?
}

#
# Spawns a SSH tunnel using autossh
#
spawnAutossh () {
    echo " --> Spawning SSH"
    autossh -M 0 -N -f -o 'PubkeyAuthentication=yes' -o 'PasswordAuthentication=no' -nNT "$@"
    echo " --> SSH should be spawned"

    return $?
}

setupTunnelsForHost () {
    local ssh_user=${1}
    local ssh_host=${2}
    local ssh_port=${3}
    local type=${4}
    local ports=${PORTS}

    for forward_ports in ${ports[*]}
    do
        spawnForwarding "${forward_ports}" "${ssh_user}" "${ssh_host}" "${ssh_port}" "${type}"

        if [[ $? != 0 ]]; then
            echo " ~ The port forwarding failed, please verify if your SSH keys are well installed"
            exit 1
        fi
    done
}

killAllTunnelsForHost () {
    local ports=${1}
    local host=${2}

    for forward_ports in ${ports[*]}
    do
        forwarding=$(createForwarding "${forward_ports}" "${PN_HOST}")
        pid=$(ps ax -o pid,comm,args|grep autossh|grep "${forwarding}"|grep -v "grep"|awk '{print $1}')

        if [[ $pid ]]; then
            echo "Killing ${pid}"
            kill "${pid}"
        fi
    done
}

hasHostAtLeastOneTunnelDown () {
    local ports=${1}
    local host=${2}

    for forward_ports in ${ports[*]}
    do
        forwarding=$(createForwarding "${forward_ports}" "${PN_HOST}")
        pid=$(ps ax -o pid,comm,args|grep autossh|grep "${forwarding}"|grep -v "grep"|awk '{print $1}')

        if [[ ! $pid ]]; then
            return 0
        fi
    done

    return 1
}