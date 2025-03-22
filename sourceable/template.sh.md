To create a minimal example script that can be both sourced and executed, while providing functionality like entering a Docker container with user credentials, let's deconstruct the script and use comments for clarification. This approach allows it to be used both as a library (by sourcing it) and as a standalone tool (by executing it).

### Script Breakdown

1. **Function Definition**:
    - The script primarily revolves around the `docker_run_with_dir` function, which sets up a Docker container environment that mimics the user's credentials and directory setup on their host machine.
    
2. **Detecting Script Usage**:
    - The script uses `BASH_SOURCE` to check whether it is being executed directly or sourced into another script.

3. **Main Function**:
    - A `main` function is defined and called only if the script is executed directly. This encapsulation allows for additional functionality if sourced, such as using functions separately.

Here is a minimal example script template:

```bash
#!/bin/bash
# **Docker Environment Setup**
#
# "Usage: ./docker_script.sh <directory> [ro|rw] [image=ubuntu:latest]"
#
# This script can be sourced or executed directly

docker_run_with_dir() {
    local dir="$1" mode="${2:-ro}" image="${3:-ubuntu:latest}"

    if [[ -z "$dir" || ! -d "$dir" ]]; then
        echo "Usage: docker_run_with_dir <directory> [ro|rw] [image=$image]" >&2
        return 1
    fi

    local uid=$(id -u)
    local gid=$(id -g)
    local username=$(id -un)
    local groupname=$(getent group "$gid" | cut -d: -f1)
    local temp_dir=$(mktemp -d)

    trap 'rm -rf "$temp_dir"' EXIT

    local homedir_inside='/tmp/home'

    # Prepare minimal user credential files for inside Docker
    cat > "${temp_dir}/passwd" <<EOF
root:x:0:0:root:/root:/bin/bash
${username}:x:${uid}:${gid}:,,${homedir_inside}:/data:/bin/bash
EOF

    cat > "${temp_dir}/group" <<EOF
root:x:0:
${groupname}:x:${gid}:
EOF

    # Execute Docker run with custom settings
    docker run -it --rm \
        -v "$dir":/data:"$mode" \
        -v "${temp_dir}/passwd":/etc/passwd:ro \
        -v "${temp_dir}/group":/etc/group:ro \
        -w /data \
        -u "${uid}:${gid}" \
        "$image" \
        bash -c "mkdir -p ${homedir_inside} && exec bash"
}

# Main entry point
main() {
    docker_run_with_dir "$@"
}

# Check whether the script is being sourced or executed
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
```

### Explanation

- **Functionality**: 
  - The `docker_run_with_dir` function takes a directory, access mode (`ro` or `rw`), and an optional Docker image name. It sets up Docker with the user's credentials and mounts the specified directory.
  
- **Credential Files**:
  - Creates minimal `/etc/passwd` and `/etc/group` files for the Docker environment to reflect the current user's identity and groups.

- **Cleanup**:
  - Uses `mktemp` to create a temporary directory for credentials and ensures cleanup with `trap`.

- **Execution Handling**:
  - The `main` function is invoked only if the script is executed (`BASH_SOURCE[0]` will be the script name when executed and not when sourced).
  
By following this template, you have a script that easily adapts to be part of larger systems or act as a standalone utility while using Docker securely.

