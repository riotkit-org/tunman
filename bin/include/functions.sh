function resetIteration() {
    PN_USER=""
    PN_PORT=""
    PN_HOST=""

    PN_VALIDATE=""
    PN_VALIDATE_COMMAND=""
    PORTS=()
}

function iterateOverConfiguration() {
    cd "$( dirname "${BASH_SOURCE[0]}" )"
    DIR=$(pwd)

    for config_file_name in ../../conf.d/*.sh
    do
        resetIteration
        source $config_file_name
        executeIterationAction $config_file_name
    done
}

function parsePortForwarding() {
    IFS='>' read -r -a parts <<< "$1"
    source_port=${parts[0]}
    dest_port=${parts[1]}
}

function executeHooks() {
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
