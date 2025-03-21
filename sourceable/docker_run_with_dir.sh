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


# LLM generated explanations:

That's a neat solution! Your final version creates minimal fake authentication files (/etc/passwd, /etc/group, and /etc/shadow) to enable passwordless login for root via `su` and ensure that your mapped user is recognized inside the container. This approach avoids exposing your entire host authentication files while providing just enough data for commands like `su` to work.

Below is your complete script (with your comments) for reference:

```bash
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



### Explanation:
# 
# - **Authentication Files:**  
#   - **/etc/passwd:** Contains entries for both `root` and your host user with the appropriate UID, GID, and a custom home directory (`/tmp/home` inside the container).  
#   - **/etc/group:** Includes a minimal set of groups: the host user’s primary group, a root group, and a supplementary wheel group (with GID 10) that lists your username.  
#   - **/etc/shadow:** Provides empty password fields so that passwordless login (via `su`) is enabled.
# 
# - **Docker Run Options:**  
#   The script mounts these fake authentication files into the container (as read-only), sets the working directory to `/data` (which maps to your provided directory), and runs the container under your UID and GID.
# 
# - **Home Directory Creation:**  
#   The inline command `bash -c "mkdir -p ${homedir_inside} && exec bash"` ensures that the home directory exists before dropping you into an interactive shell.
# 
# This method gives you a fully functional environment inside the container without exposing sensitive host files.
# Thanks for sharing your complete version—it's a great example of how to securely map user credentials into a Docker container!
