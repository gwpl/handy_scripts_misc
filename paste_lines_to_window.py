#!/usr/bin/env python3

"""
Line Paster Script
Pastes lines from input (stdin or file) to a target window using xclip and xdotool.
Requires: xclip, xdotool, xprop
"""

import subprocess
import time
import sys
import argparse
import datetime
from typing import List, Optional, TextIO
# No enum needed anymore, we'll use strings directly

def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Paste lines to a target window')
    parser.add_argument('-b', '--boot', type=float, default=0.5,
                        help='Boot time delay in seconds (default: 0.5)')
    parser.add_argument('-s', '--sleep', type=float, default=5,
                        help='Sleep time between operations in seconds (default: 5)')
    parser.add_argument('-S', '--item-delay', type=float, default=None,
                        help='Delay per line iteration in seconds (overrides --sleep)')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Enable verbose output')
    parser.add_argument('-f', '--file', type=str, default='-',
                        help='Input file (default: stdin)')
    paste_group = parser.add_argument_group('paste mode (choose one)')
    paste_mode = paste_group.add_mutually_exclusive_group()
    paste_mode.add_argument('-p', '--paste-commands', type=str, default='ctrl+v,Return',
                        help='Comma-separated keyboard commands (default: ctrl+v,Return)')
    paste_mode.add_argument('-e', '--editor-paste', action='store_true',
                        help='Use editor/IM/Telegram paste commands (ctrl+v,Return)')
    paste_mode.add_argument('-t', '--terminal-paste', action='store_true',
                        help='Use terminal paste commands (ctrl+shift+v,Return)')
    paste_mode.add_argument('-B', '--browser-new-tabs', action='store_true',
                        help='Use browser new tab sequence (ctrl+t,ctrl+v,Return)')
    parser.add_argument('-d', '--delimiter', type=str, default=',',
                        help='Delimiter for paste commands (default: ,)')
    return parser.parse_args()

def resolve_paste_commands(args) -> str:
    """
    Resolve paste commands based on command line arguments.
    Returns a string of comma-separated commands.
    """
    if args.terminal_paste:
        commands = 'ctrl+shift+v,Return'
    elif args.browser_new_tabs:
        commands = 'ctrl+t,ctrl+v,Return'
    elif args.editor_paste:
        commands = 'ctrl+v,Return'
    else:
        commands = args.paste_commands
    
    return commands

def log_verbose(message: str, verbose: bool) -> None:
    """Print verbose messages to stderr if verbose mode is enabled"""
    if verbose:
        print(f"INFO: {message}", file=sys.stderr)

def get_focused_window_class() -> str:
    """Get the class and ID of the currently focused window"""
    try:
        # Get window ID of focused window
        window_id = subprocess.run(
            ['xdotool', 'getwindowfocus'],
            capture_output=True, text=True, check=True
        ).stdout.strip()
        
        # Get window class using the window ID
        window_class = subprocess.run(
            ['xprop', '-id', window_id, 'WM_CLASS'],
            capture_output=True, text=True, check=True
        ).stdout.strip()
        
        return f"{window_class.lower()} (ID: {window_id})"
    except subprocess.CalledProcessError:
        return ""

class WindowFocusLostError(Exception):
    """Exception raised when target window focus is lost during operation"""
    pass

def wait_for_focus_change(initial_focus: str, verbose: bool) -> str:
    """Wait until focus changes from the initial window"""
    log_verbose(f"Initial focus: {initial_focus}", verbose)
    log_verbose("Waiting for focus to change (please click on target window)...", verbose)
    
    while True:
        current_focus = get_focused_window_class()
        if current_focus != initial_focus:
            log_verbose(f"Focus changed to: {current_focus}", verbose)
            return current_focus
        
        time.sleep(0.5)

def assert_window_focused(expected_focus: str, verbose: bool) -> None:
    """Assert that the expected window is focused, raise exception if not"""
    current_focus = get_focused_window_class()
    if verbose:
        log_verbose(f"Checking focus: {current_focus}", verbose)
    
    # Extract just the window ID for comparison
    expected_id = expected_focus.split("(ID: ")[1].split(")")[0]
    current_id = current_focus.split("(ID: ")[1].split(")")[0]
    
    if expected_id != current_id:
        raise WindowFocusLostError("Target window focus lost during operation")

def paste_to_clipboard(content: str):
    """
    Copy content to the system clipboard using xclip.
    
    Args:
        content (str): The text content to be copied to clipboard
    
    Raises:
        subprocess.CalledProcessError: If xclip command fails
        FileNotFoundError: If xclip is not installed
    """
    try:
        # Run xclip command with -selection clipboard to copy to system clipboard
        subprocess.run(
            ['xclip', '-selection', 'clipboard'],
            input=content.encode('utf-8'),
            check=True
        )
    except FileNotFoundError:
        print("Error: xclip is not installed. Please install it first.", file=sys.stderr)
        print("You can install it using: sudo pacman -S xclip", file=sys.stderr)
        raise
    except subprocess.CalledProcessError as e:
        print(f"Error: Failed to copy to clipboard. Error code: {e.returncode}", file=sys.stderr)
        raise

def send_key(key_command: str, target_focus: str, verbose: bool = False) -> None:
    """Send keyboard commands using xdotool, but first verify target window is focused"""
    # Check that target window is still focused before sending any keys
    assert_window_focused(target_focus, verbose)
    
    try:
        subprocess.run(['xdotool', 'key', key_command], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error sending keyboard command: {e}", file=sys.stderr)

def open_input_file(file_path: str) -> TextIO:
    """Open the input file or use stdin if file_path is '-'"""
    if file_path == '-':
        log_verbose("Reading from standard input", True)
        return sys.stdin
    
    try:
        return open(file_path, 'r')
    except Exception as e:
        print(f"Error opening file {file_path}: {e}", file=sys.stderr)
        sys.exit(1)

def format_time_remaining(seconds: float) -> str:
    """Format time remaining in a human-readable format"""
    if seconds < 60:
        return f"{int(seconds)} sec"
    
    # Convert to timedelta for easier formatting
    td = datetime.timedelta(seconds=int(seconds))
    
    # Extract days, hours, minutes, seconds
    days = td.days
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if days > 0:
        return f"{days}days {hours:02d}:{minutes:02d}:{seconds:02d}"
    elif hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes:02d}:{seconds:02d}"

def calculate_step_delay(sleep_delay: float, item_delay: Optional[float], commands: List[str], verbose: bool) -> float:
    """Calculate the appropriate delay per step based on sleep_delay and item_delay"""
    # Number of steps per line iteration is based on the number of commands
    STEPS_PER_LINE = len(commands)
    
    if item_delay is None:
        return sleep_delay
    
    # When item_delay is specified, use it directly (divided by steps)
    # instead of comparing with the default sleep_delay
    calculated_sleep = item_delay / STEPS_PER_LINE
    
    if verbose:
        print(f"INFO: Using calculated step delay of {calculated_sleep:.3f}s to achieve line delay of {item_delay}s", 
              file=sys.stderr)
    
    return calculated_sleep

def paste_lines(input_file: TextIO, boot_delay: float, sleep_delay: float, 
               item_delay: Optional[float], verbose: bool,
               paste_commands: str = 'ctrl+v,Return', delimiter: str = ',') -> None:
    """Paste lines from input to target window"""
    # Get initial focus (terminal)
    initial_focus = get_focused_window_class()
    
    # Wait for user to change focus to target window
    target_focus = wait_for_focus_change(initial_focus, verbose)
    
    log_verbose(f"Waiting {boot_delay} seconds before starting...", verbose)
    time.sleep(boot_delay)
    
    # Split paste commands using the delimiter
    commands = paste_commands.split(delimiter)
    log_verbose(f"Using keyboard commands: {commands}", verbose)
    
    # Calculate the appropriate delay per step
    effective_sleep_delay = calculate_step_delay(sleep_delay, item_delay, commands, verbose)
    
    # Count total lines first
    total_lines = 0
    lines_to_process = []
    
    for line in input_file:
        line = line.rstrip('\n')
        if line:  # Skip empty lines
            total_lines += 1
            lines_to_process.append(line)
    
    if verbose:
        log_verbose(f"Found {total_lines} non-empty lines to process", verbose)
    
    line_count = 0
    start_time = time.time()
    
    for line in lines_to_process:
        line_count += 1
        
        # Print the line to stdout before pasting
        print(line)
        
        # Log line number before processing
        if verbose:
            # Calculate ETA
            if line_count > 1:  # Use actual timing data if available
                elapsed_time = time.time() - start_time
                avg_time_per_line = elapsed_time / (line_count - 1)
                remaining_lines = total_lines - line_count + 1
                time_remaining = avg_time_per_line * remaining_lines
                eta_str = format_time_remaining(time_remaining)
            else:
                # Initial estimate based on configured delays
                steps_per_line = len(commands)
                estimated_time_per_line = effective_sleep_delay * steps_per_line
                time_remaining = estimated_time_per_line * total_lines
                eta_str = format_time_remaining(time_remaining)
            
            # Adding extra newlines \n\n for readability in verbose mode:
            print(f"\n\nINFO: PROCESSING LINE NUMBER {line_count}/{total_lines} (ETA: {eta_str})", file=sys.stderr)
            total_line_time = effective_sleep_delay * len(commands)
            print(f"INFO: TOTAL LINE PROCESSING TIME: {total_line_time:.2f} sec.", file=sys.stderr)
            print(f"INFO: USING STEP DELAY: {effective_sleep_delay:.2f} sec.", file=sys.stderr)
        
        # Copy line to clipboard
        log_verbose(f"Copying to clipboard: {line}", verbose)
        paste_to_clipboard(line)
        
        # Execute each keyboard command in sequence
        for i, command in enumerate(commands):
            log_verbose(f"Executing command {i+1}/{len(commands)}: {command}", verbose)
            send_key(command, target_focus, verbose)
            log_verbose(f"Waiting {effective_sleep_delay:.2f} seconds after command", verbose)
            time.sleep(effective_sleep_delay)
    
    if verbose:
        elapsed_time = time.time() - start_time
        print(f"INFO: FINISHED PASTING {line_count}/{total_lines} LINES in {format_time_remaining(elapsed_time)}", file=sys.stderr)

def main() -> None:
    """Main function"""
    args = parse_arguments()
    
    # Resolve paste commands based on command line arguments
    paste_commands = resolve_paste_commands(args)
    if args.verbose and paste_commands != args.paste_commands:
        log_verbose(f"Using paste commands: {paste_commands}", args.verbose)
    
    try:
        with open_input_file(args.file) as input_file:
            paste_lines(input_file, args.boot, args.sleep, args.item_delay, 
                       args.verbose, paste_commands, args.delimiter)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        sys.exit(1)
    except WindowFocusLostError:
        print("\nOperation cancelled: Target window focus was lost", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
