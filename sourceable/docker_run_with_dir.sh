#!/bin/bash
# **Jump into docker and work there on current directory with ease**
#
#  "Usage: docker_run_with_dir <directory> [ro|rw] [image=ubuntu:latest]"
#
# Features:
# * maps your user and group, so created files will be accessible on host
# * your username and group inside docker (via synthetic /etc/passwd, /etc/groups)
# * working `su` - allows your user inside docker to enter root via `su` passwordless.

docker_run_with_dir () {
    local dir="$1" mode="${2:-ro}" image="${3:-ubuntu:latest}"

    if [[ -z "$dir" || ! -d "$dir" ]]; then
        echo "Usage: docker_run_with_dir <directory> [ro|rw] [image=$image]" >&2
        return 1
    fi

    local uid=$(id -u) gid=$(id -g) username=$(id -un) groupname=$(getent group "$gid" | cut -d: -f1)
    local temp_dir=$(mktemp -d)

    trap 'rm -rf "$temp_dir"' EXIT

    local homedir_inside='/tmp/home'
     # Create a minimal /etc/passwd file that includes both root and the host user.
    cat > "${temp_dir}/passwd" <<EOF
root:x:0:0:root:/root:/bin/bash
${username}:x:${uid}:${gid}:,,${homedir_inside}:/data:/bin/bash
EOF

    # Create a minimal /etc/group file with a root group, the host user's primary group,
    # and a wheel group with GID 10 that includes the user.
    cat > "${temp_dir}/group" <<EOF
root:x:0:
${groupname}:x:${gid}:
wheel:x:10:${username}
EOF

    # Minimal /etc/shadow: empty password fields enable passwordless login.
    # The fields are: username:password:lastchg:min:max:warn:inactive:expire:flag
    cat > "${temp_dir}/shadow" <<EOF
root::17936:0:99999:7:::
${username}::17936:0:99999:7:::
EOF


    docker run -it --rm \
        -v "$dir":/data:"$mode" \
        -v "${temp_dir}/passwd":/etc/passwd:ro \
        -v "${temp_dir}/group":/etc/group:ro \
        -v "${temp_dir}/shadow":/etc/shadow:ro \
        -w /data \
        -u "${uid}:${gid}" \
        "$image" \
        bash -c "mkdir -p ${homedir_inside} && exec bash"
}

# Main function
main() {
    docker_run_with_dir "$@"
}

# Detect if the script is being sourced or executed
# `${BASH_SOURCE[0]}` is the file name of the current script
# `$0` is the name of the shell or script being executed
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
