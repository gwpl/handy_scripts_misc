#!/usr/bin/env python3
"""
envsync: Environment Variable Synchronizer

This tool synchronizes an environment variables file from a local machine to a remote server using the system's SSH and SCP commands.
It performs the following functions:
  - Copies a specified environment file (e.g., '~/.config/stow/magic/magic_vars') to a target location on a remote system.
  - Detects the most appropriate shell profile file on the remote system (e.g., ~/.profile, ~/.xprofile, or ~/.bashrc).
  - Automatically appends a "source <remote_file>" command to the detected profile if it is not already present.
  - Supports a verbosity flag (-v/--verbose) for detailed logging of executed commands.
  - Forwards any additional arguments after the local file and target to the SSH/SCP commands so that custom SSH options can be used.

Usage Example:
    envsync [-v|--verbose] local_file user@server:remote_file [ssh_options...]

Arguments:
    -v, --verbose       Enable verbose logging.
    local_file          Local environment file to copy.
    user@server:remote_file
                        Target SSH destination and remote file path.
    ssh_options         Additional options passed directly to the ssh and scp commands.

This script can be used as both a standalone command-line tool and an importable library.
Dependencies: Uses system SSH and SCP commands.
Author: [Your Name]
License: [Your License]
"""

import sys
import subprocess
import re
import argparse

# Global verbosity flag
VERBOSE = False

def log_info(message):
    """Log information to stderr if verbose is enabled."""
    if VERBOSE:
        print(f"INFO: {message}", file=sys.stderr)

def parse_ssh_target(target):
    """
    Parse a target in the form of user@server:remote_file.
    Returns a tuple (user, server, remote_file).
    """
    match = re.match(r'([^@]+)@([^:]+):(.+)', target)
    if not match:
        raise ValueError(f"Invalid SSH target format: {target} # should be usr@srv:~/path")
    return match.groups()

def run_remote_command(user, server, remote_cmd, extra_ssh_args):
    """
    Execute a remote command via SSH and return (stdout, stderr, returncode).
    """
    ssh_target = f"{user}@{server}"
    ssh_cmd = ["ssh"] + extra_ssh_args + [ssh_target, remote_cmd]
    log_info("Executing: " + " ".join(ssh_cmd))
    result = subprocess.run(ssh_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    return result.stdout, result.stderr, result.returncode

def find_best_profile(user, server, extra_ssh_args):
    """
    Detect the best profile file on the remote machine.
    Tries in order: ~/.profile, ~/.xprofile, ~/.bashrc.
    """
    profile_files = ["~/.profile", "~/.xprofile", "~/.bashrc"]
    for profile in profile_files:
        cmd = f"test -f {profile} && echo exists || echo missing"
        out, _, _ = run_remote_command(user, server, cmd, extra_ssh_args)
        if "exists" in out:
            log_info(f"Found profile file: {profile}")
            return profile
    log_info("No profile file found; defaulting to ~/.profile")
    return "~/.profile"

def add_source_to_profile(user, server, remote_env_file, profile_file, extra_ssh_args):
    """
    Ensure that the 'source <remote_env_file>' line is present in the remote profile file.
    If not, append it.
    """
    source_line = f"source {remote_env_file}"
    # Check if the line already exists
    check_cmd = f"grep -Fxq '{source_line}' {profile_file} && echo found || echo missing"
    out, _, _ = run_remote_command(user, server, check_cmd, extra_ssh_args)
    if "found" in out:
        log_info(f"'{source_line}' is already present in {profile_file}")
        return

    # For .bashrc, append with a preceding comment; for others, simply append.
    if profile_file.endswith(".bashrc"):
        append_cmd = f"echo -e '\\n# Load custom env variables\\n{source_line}' >> {profile_file}"
    else:
        append_cmd = f"echo '{source_line}' >> {profile_file}"
    
    log_info(f"Appending source command to {profile_file}: {append_cmd}")
    run_remote_command(user, server, append_cmd, extra_ssh_args)
    log_info(f"Added '{source_line}' to {profile_file}")

def copy_file(local_file, target, extra_ssh_args):
    """
    Copy the local file to the remote target using scp.
    """
    scp_cmd = ["scp"] + extra_ssh_args + [local_file, target]
    log_info("Copying file: " + " ".join(scp_cmd))
    subprocess.check_call(scp_cmd)

def main():
    parser = argparse.ArgumentParser(
        description="Copy an environment variable file to a remote server and update the remote profile to source it. "
                    "This tool uses system SSH and SCP commands."
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging.")
    parser.add_argument("local_file", help="Local file to copy (e.g., ~/.config/stow/magic/magic_vars)")
    parser.add_argument("target", help="Remote target in the format user@server:remote_file")
    parser.add_argument("ssh_options", nargs=argparse.REMAINDER, help="Additional options to pass to ssh/scp commands")
    args = parser.parse_args()

    # Set global verbosity flag
    global VERBOSE
    VERBOSE = args.verbose

    try:
        user, server, remote_file = parse_ssh_target(args.target)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        # Copy the environment file to the remote system
        copy_file(args.local_file, args.target, args.ssh_options)
    except subprocess.CalledProcessError:
        print("ERROR: SCP failed.", file=sys.stderr)
        sys.exit(1)

    # Determine the best profile file on the remote system
    profile_file = find_best_profile(user, server, args.ssh_options)
    log_info(f"Using profile file: {profile_file}")

    # Append the source command to the profile file if it is not already present
    add_source_to_profile(user, server, remote_file, profile_file, args.ssh_options)

if __name__ == "__main__":
    main()

