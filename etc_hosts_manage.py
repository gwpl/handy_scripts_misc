#!/usr/bin/env python3
"""
A script to manage custom lines in /etc/hosts

This script allows adding, updating, disabling, enabling, deleting, and listing
hosts entries that it manages in /etc/hosts.

Usage Examples:
    etc_hosts_manage.py add --ip 127.0.0.50 --hostname test.local
    etc_hosts_manage.py update --ip 127.0.0.99 --hostname test.local
    etc_hosts_manage.py disable --hostname test.local
    etc_hosts_manage.py enable --hostname test.local
    etc_hosts_manage.py delete --hostname test.local
    etc_hosts_manage.py list

It supports optional comment, marker, verbosity levels, etc.

By default, only lines that end with the marker are modified. The default marker
is "# ManagedByHostsTool". If the marker is changed to an empty string, all lines
are considered when searching for matches.

The script returns 0 if the operation was successful or a non-zero code otherwise.
"""

import sys
import argparse
import json
import os
import subprocess
import tempfile

DEFAULT_MARKER = "# ManagedByHostsTool"
DEFAULT_HOSTS_PATH = "/etc/hosts"

VERBOSITY_LEVEL = 0

def log_debug(msg):
    if VERBOSITY_LEVEL >= 4:
        print(f"DEB: {msg}", file=sys.stderr)

def log_info(msg):
    if VERBOSITY_LEVEL >= 1:
        print(f"INFO: {msg}", file=sys.stderr)

def error_exit(msg, code=1):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)

def is_ssh_path(path):
    """
    Naive check if a path looks like 'user@host:/some/path'.
    We'll look for a '@' and a ':' in the string.
    """
    return ('@' in path) and (':' in path)

def parse_ssh_path(path):
    """
    Parse an SSH-style path user@host:/remote/path into (user_host, remote_path).
    If user@ is omitted, we still handle 'host:/remote/path'.
    """
    user_host, remote_path = path.split(':', 1)
    return user_host, remote_path

def read_remote_file(ssh_cmd, ssh_extra_args, user_host, remote_path):
    """
    Use ssh to read the remote file and return a list of lines.
    """
    cmd = [ssh_cmd] + ssh_extra_args + [user_host, 'cat', remote_path]
    log_debug(f"Reading remote file with command: {' '.join(cmd)}")
    try:
        out = subprocess.check_output(cmd, encoding='utf-8')
    except subprocess.CalledProcessError as e:
        error_exit(f"Cannot read remote file: {e}", 1)
    lines = out.splitlines()
    return lines

def write_remote_file(ssh_cmd, ssh_extra_args, user_host, remote_path, lines_data):
    """
    Use ssh to create a backup of the remote file, then write new content via stdin.
    """
    # Create backup on remote
    cmd_backup = [ssh_cmd] + ssh_extra_args + [
        user_host,
        f"cp '{remote_path}' '{remote_path}.bak' 2>/dev/null || true"
    ]
    log_debug(f"Backing up remote file with command: {' '.join(cmd_backup)}")
    try:
        subprocess.check_call(cmd_backup)
    except subprocess.CalledProcessError as e:
        error_exit(f"Failed creating backup on remote: {e}", 1)

    # Write new file content
    cmd_write = [ssh_cmd] + ssh_extra_args + [user_host, f"cat > '{remote_path}'"]
    log_debug(f"Writing remote file with command: {' '.join(cmd_write)}")
    try:
        proc = subprocess.Popen(cmd_write, stdin=subprocess.PIPE, text=True)
        proc.communicate("\n".join(lines_data) + "\n")
        if proc.returncode != 0:
            error_exit("Failed to write remote file.", proc.returncode)
    except Exception as e:
        error_exit(f"Failed to write to remote hosts file: {e}")

def parse_local_file(hosts_path):
    """
    Parse /etc/hosts (or local file) into a list of lines.
    """
    if not os.path.exists(hosts_path):
        error_exit(f"Hosts file not found: {hosts_path}")

    lines_data = []
    with open(hosts_path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.rstrip('\n')
            lines_data.append(line)
    return lines_data

def write_local_file(hosts_path, lines_data):
    """
    Write lines back to local /etc/hosts (or any local file), creating a backup.
    """
    backup_path = hosts_path + ".bak"
    try:
        # create backup
        with open(backup_path, "w", encoding="utf-8") as backup_fd:
            original = []
            if os.path.exists(hosts_path):
                with open(hosts_path, "r", encoding="utf-8") as orig_fd:
                    original = orig_fd.read()
            backup_fd.write(original)

        # overwrite hosts file
        with open(hosts_path, "w", encoding="utf-8") as fd:
            fd.write("\n".join(lines_data) + "\n")

    except Exception as e:
        error_exit(f"Failed to write to {hosts_path}: {e}")

def parse_hosts(hosts_path, ssh_cmd, ssh_extra_args):
    """
    Parse the hosts file from either local or remote based on the path format.
    """
    if is_ssh_path(hosts_path):
        user_host, remote_path = parse_ssh_path(hosts_path)
        return read_remote_file(ssh_cmd, ssh_extra_args, user_host, remote_path)
    else:
        return parse_local_file(hosts_path)

def write_hosts(hosts_path, lines_data, ssh_cmd, ssh_extra_args):
    """
    Write the hosts file to either local or remote based on the path format.
    """
    if is_ssh_path(hosts_path):
        user_host, remote_path = parse_ssh_path(hosts_path)
        write_remote_file(ssh_cmd, ssh_extra_args, user_host, remote_path, lines_data)
    else:
        write_local_file(hosts_path, lines_data)

def parse_line_components(line):
    """
    Returns (original_line, ip, hostname, unused, trailing, is_commented_out).
    If line is blank or no IP found, returns placeholders.
    """
    original_line = line
    is_commented_out = False
    line = line.strip()
    if not line or line.startswith('#'):
        if line.startswith('#'):
            is_commented_out = True
            line = line[1:].strip()
        else:
            return (original_line, "", "", "", "", is_commented_out)

    parts = line.split()
    if len(parts) < 2:
        return (original_line, "", "", "", "", is_commented_out)

    ip_part = parts[0]
    hostname_part = parts[1]
    remainder = parts[2:] if len(parts) > 2 else []
    joined_remainder = " ".join(remainder)
    return (original_line, ip_part, hostname_part, "", joined_remainder, is_commented_out)

def build_line(ip, hostname, comment, marker, is_commented_out):
    """
    Construct the line from the components. The comment (if present) is
    placed before the marker. If marker is present and not empty, it is appended.
    """
    final_line = f"{ip} {hostname}"
    comment = comment.strip()

    if comment:
        final_line += f" {comment}"
    if marker.strip():
        final_line += f" {marker.strip()}"

    if is_commented_out:
        return "# " + final_line
    else:
        return final_line

def find_line_index(lines_data, hostname, marker):
    """
    Finds the index of the line for the given hostname that ends with the marker.
    If marker is empty, then any line with the given hostname is considered.
    Returns index or None if not found.
    """
    for i, line in enumerate(lines_data):
        _, ip, host, _, trailing, commented = parse_line_components(line)
        if host == hostname:
            if marker == "":
                return i
            else:
                if trailing.endswith(marker):
                    return i
    return None

def add_entry(lines_data, ip, hostname, user_comment, marker):
    """
    Adds a new entry. If hostname already exists (with lines ending
    in marker if marker is not empty) then refuse.
    """
    idx = find_line_index(lines_data, hostname, marker)
    if idx is not None:
        error_exit("Hostname already exists with marker. Use update instead.", 1)

    new_line = build_line(ip, hostname, user_comment, marker, False)
    lines_data.append(new_line)
    return lines_data

def update_entry(lines_data, ip, hostname, user_comment, marker):
    """
    Update existing line about same hostname if it exists
    otherwise create new one.
    """
    idx = find_line_index(lines_data, hostname, marker)
    if idx is None:
        # create new
        lines_data = add_entry(lines_data, ip, hostname, user_comment, marker)
        return lines_data
    # update
    original_line, old_ip, old_host, _, old_trailing, old_commented = parse_line_components(
        lines_data[idx]
    )
    lines_data[idx] = build_line(ip, hostname, user_comment, marker, old_commented)
    return lines_data

def disable_entry(lines_data, hostname, marker):
    """
    Comment out line about hostname if it exists.
    """
    idx = find_line_index(lines_data, hostname, marker)
    if idx is None:
        error_exit("Cannot disable. No entry found.", 1)

    original_line, ip, host, _, trailing, commented = parse_line_components(
        lines_data[idx]
    )
    if commented:
        log_info("Entry is already disabled.")
        return lines_data
    lines_data[idx] = build_line(ip, host, "", trailing, True)
    return lines_data

def enable_entry(lines_data, hostname, marker):
    """
    Un-comment line about hostname if it exists.
    """
    idx = find_line_index(lines_data, hostname, marker)
    if idx is None:
        error_exit("Cannot enable. No entry found.", 1)

    original_line, ip, host, _, trailing, commented = parse_line_components(
        lines_data[idx]
    )
    if not commented:
        log_info("Entry is already enabled.")
        return lines_data
    lines_data[idx] = build_line(ip, host, "", trailing, False)
    return lines_data

def delete_entry(lines_data, hostname, marker):
    """
    Delete line about hostname if it exists
    """
    idx = find_line_index(lines_data, hostname, marker)
    if idx is None:
        error_exit("Cannot delete. No entry found.", 1)
    lines_data.pop(idx)
    return lines_data

def list_entries(lines_data, marker, output_json=False):
    """
    List lines that are managed by this tool, i.e. lines that
    end with the marker (unless marker is empty).
    """
    managed = []
    for line in lines_data:
        original_line, ip, host, _, trailing, commented = parse_line_components(line)
        if host and (marker == "" or trailing.endswith(marker)):
            entry = {
                "ip": ip,
                "hostname": host,
                "disabled": commented,
                "comment_or_marker": trailing,
            }
            managed.append(entry)

    if output_json:
        print(json.dumps(managed, indent=2))
    else:
        disabled_entries = [entry for entry in managed if entry["disabled"]]
        enabled_entries = [entry for entry in managed if not entry["disabled"]]

        print("## Disabled lines:")
        for entry in disabled_entries:
            print(f"{entry['ip']} {entry['hostname']} {entry['comment_or_marker']} (disabled)")

        print("\n## Enabled lines:")
        for entry in enabled_entries:
            print(f"{entry['ip']} {entry['hostname']} {entry['comment_or_marker']} (enabled)")

def parse_full_line(line):
    """
    Parse a string meant to look like an /etc/hosts line:
    e.g. '127.0.0.1   myhost.local   # Some comment'
    We'll extract ip, hostname, and everything after as comment.
    Raises ValueError if we can't find at least IP and hostname.
    """
    line = line.strip()
    if not line:
        raise ValueError("Empty line provided as --full-line")
    if line.startswith('#'):
        # If user typed a fully commented line, let's remove '#' and parse
        line = line[1:].strip()

    parts = line.split()
    if len(parts) < 2:
        raise ValueError("Must have both IP and hostname in the provided line")

    ip = parts[0]
    hostname = parts[1]
    comment_parts = parts[2:] if len(parts) > 2 else []
    comment = " ".join(comment_parts)
    return ip, hostname, comment

def main():
    global VERBOSITY_LEVEL
    parser = argparse.ArgumentParser(
        description="Manage custom /etc/hosts entries."
    )
    parser.add_argument("-v", "--verbose", action="count", default=0,
                        help="Increase verbosity. Multiple -v options increase verbosity.")
    parser.add_argument("-f", "--hosts-path", default=DEFAULT_HOSTS_PATH,
                        help="Local or remote path to the /etc/hosts file. "
                             "Can be local (e.g. /etc/hosts) "
                             "or SSH notation (user@host:/etc/hosts).")
    parser.add_argument("-M", "--marker", default=DEFAULT_MARKER,
                        help="Marker text used to identify lines managed by this tool. "
                             "Set to empty string to manage all lines. Default is '# ManagedByHostsTool'.")
    parser.add_argument("-o", "--output", choices=["json"], default=None,
                        help="Output format for the 'list' subcommand. E.g. 'json' for machine parseable output.")
    # new arguments to specify custom ssh command or extra args:
    parser.add_argument("--ssh-cmd", default=os.environ.get("SSH_CMD", "ssh"),
                        help="Specify a custom SSH command (default: 'ssh'). "
                             "Environment variable SSH_CMD can also be used.")
    parser.add_argument("--ssh-extra-args", default=None,
                        help="Extra arguments (space separated) to pass to the SSH command.")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # add
    parser_add = subparsers.add_parser("add", help="Add a new entry to /etc/hosts.")
    parser_add.add_argument("-i", "--ip", required=False, help="IP address to add.")
    parser_add.add_argument("-d", "--hostname", required=False, help="Hostname to add.")
    parser_add.add_argument("--comment", default="", help="Optional comment for this entry.")
    parser_add.add_argument("--full-line", required=False,
                            help="Provide a full string in /etc/hosts format (includes IP, hostname, etc.). "
                                 "If used, do not combine with --ip or --hostname or --comment.")

    # update
    parser_update = subparsers.add_parser("update", help="Update an existing entry or create if not found.")
    parser_update.add_argument("-i", "--ip", required=False, help="IP address to update.")
    parser_update.add_argument("-d", "--hostname", required=False, help="Hostname to update.")
    parser_update.add_argument("--comment", default="", help="Optional comment for this entry.")
    parser_update.add_argument("--full-line", required=False,
                               help="Provide a full string in /etc/hosts format (includes IP, hostname, etc.). "
                                    "If used, do not combine with --ip or --hostname or --comment.")

    # disable
    parser_disable = subparsers.add_parser("disable", help="Comment out an existing entry.")
    parser_disable.add_argument("--hostname", required=True, help="Hostname to disable.")

    # enable
    parser_enable = subparsers.add_parser("enable", help="Un-comment an existing entry.")
    parser_enable.add_argument("--hostname", required=True, help="Hostname to enable.")

    # delete
    parser_delete = subparsers.add_parser("delete", help="Delete an existing entry.")
    parser_delete.add_argument("--hostname", required=True, help="Hostname to delete.")

    # list
    parser_list = subparsers.add_parser("list", help="List entries managed by this tool.")

    args = parser.parse_args()
    VERBOSITY_LEVEL = args.verbose

    # parse ssh extra args
    ssh_extra_args = []
    if args.ssh_extra_args:
        ssh_extra_args = args.ssh_extra_args.split()

    command = args.command
    marker = args.marker
    hosts_path = args.hosts_path

    # read lines from local or remote
    lines_data = parse_hosts(hosts_path, args.ssh_cmd, ssh_extra_args)

    if command == "add":
        if args.full_line and (args.ip or args.hostname or args.comment):
            error_exit("Cannot combine --full-line with --ip/--hostname/--comment.", 2)
        if not args.full_line and (not args.ip or not args.hostname):
            error_exit("Must provide either --full-line OR both --ip and --hostname.", 2)

        if args.full_line:
            try:
                ip, host, comment = parse_full_line(args.full_line)
                lines_data = add_entry(lines_data, ip, host, comment, marker)
            except ValueError as ve:
                error_exit(str(ve), 3)
        else:
            lines_data = add_entry(lines_data, args.ip, args.hostname, args.comment, marker)

        write_hosts(hosts_path, lines_data, args.ssh_cmd, ssh_extra_args)
        sys.exit(0)

    elif command == "update":
        if args.full_line and (args.ip or args.hostname or args.comment):
            error_exit("Cannot combine --full-line with --ip/--hostname/--comment.", 2)
        if not args.full_line and (not args.ip or not args.hostname):
            error_exit("Must provide either --full-line OR both --ip and --hostname.", 2)

        if args.full_line:
            try:
                ip, host, comment = parse_full_line(args.full_line)
                lines_data = update_entry(lines_data, ip, host, comment, marker)
            except ValueError as ve:
                error_exit(str(ve), 3)
        else:
            lines_data = update_entry(lines_data, args.ip, args.hostname, args.comment, marker)

        write_hosts(hosts_path, lines_data, args.ssh_cmd, ssh_extra_args)
        sys.exit(0)

    elif command == "disable":
        lines_data = disable_entry(lines_data, args.hostname, marker)
        write_hosts(hosts_path, lines_data, args.ssh_cmd, ssh_extra_args)
        sys.exit(0)

    elif command == "enable":
        lines_data = enable_entry(lines_data, args.hostname, marker)
        write_hosts(hosts_path, lines_data, args.ssh_cmd, ssh_extra_args)
        sys.exit(0)

    elif command == "delete":
        lines_data = delete_entry(lines_data, args.hostname, marker)
        write_hosts(hosts_path, lines_data, args.ssh_cmd, ssh_extra_args)
        sys.exit(0)

    elif command == "list":
        list_entries(lines_data, marker, (args.output == "json"))
        sys.exit(0)

if __name__ == "__main__":
    main()
