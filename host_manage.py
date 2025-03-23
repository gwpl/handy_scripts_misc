#!/usr/bin/env python3
"""
A script to manage custom lines in /etc/hosts

This script allows adding, updating, disabling, enabling, deleting, and listing
hosts entries that it manages in /etc/hosts.

Usage Examples:
    hosts_manage.py add --ip 127.0.0.50 --hostname test.local
    hosts_manage.py update --ip 127.0.0.99 --hostname test.local
    hosts_manage.py disable --hostname test.local
    hosts_manage.py enable --hostname test.local
    hosts_manage.py delete --hostname test.local
    hosts_manage.py list

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

def parse_hosts(hosts_path):
    """
    Parse /etc/hosts into a list of lines and also keep track of
    which lines are 'active' or commented out, and any trailing text (comments).
    """
    if not os.path.exists(hosts_path):
        error_exit(f"Hosts file not found: {hosts_path}")

    lines_data = []
    with open(hosts_path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.rstrip('\n')
            stripped = line.lstrip()
            is_commented = stripped.startswith('#')
            lines_data.append(line)
    return lines_data

def write_hosts(hosts_path, lines_data):
    """
    Write the lines back to /etc/hosts.
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

def parse_line_components(line):
    """
    Returns (leading_comment, ip, hostname, comment, marker, is_commented_out).
    If line is blank or no IP found, returns placeholders.
    """
    original_line = line
    is_commented_out = False
    leading_whitespace = len(line) - len(line.lstrip())
    line = line.strip()
    if not line or line.startswith('#'):
        # commented or blank
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

    # Everything after the second part might be comment, marker, etc.
    remainder = parts[2:] if len(parts) > 2 else []
    # We'll try to see if the remainder has a marker or comment
    joined_remainder = " ".join(remainder)
    return (original_line, ip_part, hostname_part, "", joined_remainder, is_commented_out)

def build_line(ip, hostname, comment, marker, is_commented_out):
    """
    Construct the line from the components. The comment (if present) is
    placed before the marker. If marker is present and not empty, it is appended.
    """
    tokens = [ip, hostname]
    # The user comment is appended as '# usercomment' if provided
    # But to keep it consistent, we might just keep the raw comment
    # The marker is appended at the end if not empty.

    # We'll store comment as part of the line if it doesn't contain '#'
    # Or if it does, we just keep it as is. It's up to the user.
    line_comment = ""
    if comment.strip():
        line_comment = f"{comment.strip()}"

    final_line = f"{ip} {hostname}"
    if line_comment:
        final_line += f" {line_comment}"
    if marker.strip():
        # ensure we add a space if there's something else
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
        original_line, ip, host, _, trailing, commented = parse_line_components(line)
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
    # parse user comment from old trailing?
    # We'll just override with the new user comment for clarity
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
            # We'll parse user comment from trailing if needed
            # For now let's just store everything in a dict for JSON
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
        for entry in managed:
            if entry["disabled"]:
                status = "(disabled)"
            else:
                status = "(enabled)"
            print(f"{entry['ip']} {entry['hostname']} {entry['comment_or_marker']} {status}")

def main():
    global VERBOSITY_LEVEL
    parser = argparse.ArgumentParser(
        description="Manage custom /etc/hosts entries."
    )
    parser.add_argument("-v", "--verbose", action="count", default=0,
                        help="Increase verbosity. Multiple -v options increase verbosity.")
    parser.add_argument("--hosts-path", default=DEFAULT_HOSTS_PATH,
                        help="Path to the /etc/hosts file. Default is /etc/hosts.")
    parser.add_argument("-M", "--marker", default=DEFAULT_MARKER,
                        help="Marker text used to identify lines managed by this tool. "
                             "Set to empty string to manage all lines. Default is '# ManagedByHostsTool'.")
    parser.add_argument("-o", "--output", choices=["json"], default=None,
                        help="Output format for the 'list' subcommand. E.g. 'json' for machine parseable output.")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # add
    parser_add = subparsers.add_parser("add", help="Add a new entry to /etc/hosts.")
    parser_add.add_argument("--ip", required=True, help="IP address to add.")
    parser_add.add_argument("--hostname", required=True, help="Hostname to add.")
    parser_add.add_argument("--comment", default="", help="Optional comment for this entry.")

    # update
    parser_update = subparsers.add_parser("update", help="Update an existing entry or create if not found.")
    parser_update.add_argument("--ip", required=True, help="IP address to update.")
    parser_update.add_argument("--hostname", required=True, help="Hostname to update.")
    parser_update.add_argument("--comment", default="", help="Optional comment for this entry.")

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

    command = args.command
    marker = args.marker
    hosts_path = args.hosts_path
    lines_data = parse_hosts(hosts_path)

    if command == "add":
        lines_data = add_entry(lines_data, args.ip, args.hostname, args.comment, marker)
        write_hosts(hosts_path, lines_data)
        sys.exit(0)

    elif command == "update":
        lines_data = update_entry(lines_data, args.ip, args.hostname, args.comment, marker)
        write_hosts(hosts_path, lines_data)
        sys.exit(0)

    elif command == "disable":
        lines_data = disable_entry(lines_data, args.hostname, marker)
        write_hosts(hosts_path, lines_data)
        sys.exit(0)

    elif command == "enable":
        lines_data = enable_entry(lines_data, args.hostname, marker)
        write_hosts(hosts_path, lines_data)
        sys.exit(0)

    elif command == "delete":
        lines_data = delete_entry(lines_data, args.hostname, marker)
        write_hosts(hosts_path, lines_data)
        sys.exit(0)

    elif command == "list":
        list_entries(lines_data, marker, (args.output == "json"))
        sys.exit(0)

if __name__ == "__main__":
    main()
