#!/usr/bin/env python3

"""
Tab URL Collector Script
Collects URLs from browser tabs using xclip and xdotool.
Requires: xclip, xdotool
"""

import subprocess
import time
import sys
import argparse
import re
from typing import List, Optional, Callable, Dict, Pattern
# No enum needed anymore, we'll use strings directly

def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Collect URLs from browser tabs')
    parser.add_argument('-b', '--boot', type=float, default=0.5,
                        help='Boot time delay in seconds (default: 0.5)')
    delay_group = parser.add_argument_group('delay options (choose one)')
    delay_mode = delay_group.add_mutually_exclusive_group()
    delay_mode.add_argument('-s', '--sleep', type=float, default=0.1,
                        help='Sleep time between operations in seconds (default: 0.1)')
    delay_mode.add_argument('-S', '--item-delay', type=float, default=None,
                        help='Delay per tab iteration in seconds (overrides --sleep)')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Enable verbose output')
    
    # URL processing mode options
    url_mode_group = parser.add_argument_group('URL processing mode (choose one)')
    url_mode = url_mode_group.add_mutually_exclusive_group()
    url_mode.add_argument('-f', '--full-urls', action='store_true',
                        help='Keep FULL URLs with all parameters')
    url_mode.add_argument('-c', '--cleaned-urls', action='store_true', default=True,
                        help='Clean URLs by removing query parameters (default)')
    url_mode.add_argument('-m', '--minimalistic-urls', action='store_true',
                        help='Create minimalistic URLs using site-specific rules')
    
    parser.add_argument('-d', '--duplicates-threshold', type=int, default=4,
                        help='Number of consecutive duplicate URLs before stopping (default: 4)')
    parser.add_argument('-M', '--max-tabs', type=int, default=1000,
                        help='Maximum number of tabs to process before stopping (default: 1000)')
    return parser.parse_args()

def log_verbose(message: str, verbose: bool) -> None:
    """Print verbose messages to stderr if verbose mode is enabled"""
    if verbose:
        print(f"INFO: {message}", file=sys.stderr)

def get_focused_window_class() -> str:
    """Get the class of the currently focused window"""
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
        
        return window_class.lower()
    except subprocess.CalledProcessError:
        return ""

class BrowserFocusLostError(Exception):
    """Exception raised when browser focus is lost during operation"""
    pass

def is_browser_focused(verbose: bool = False) -> bool:
    """Check if a supported browser window is currently focused"""
    browser_classes = ['chromium', 'chrome', 'firefox']
    current_window = get_focused_window_class()
    
    if verbose:
        log_verbose(f"Current focused window: {current_window}", verbose)
    
    return any(browser in current_window for browser in browser_classes)

def wait_for_browser_focus(verbose: bool) -> None:
    """Wait until a supported browser window is focused"""
    while True:
        if is_browser_focused(verbose):
            log_verbose(f"Detected browser window is focused", verbose)
            break
        
        time.sleep(0.5)

def assert_browser_focused(verbose: bool) -> None:
    """Assert that a browser window is focused, raise exception if not"""
    if not is_browser_focused(verbose):
        raise BrowserFocusLostError("Browser window focus lost during operation")

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
        # Input the content through stdin using input parameter
        subprocess.run(
            ['xclip', '-selection', 'clipboard'],
            input=content.encode('utf-8'),
            check=True
        )
    except FileNotFoundError:
        print("Error: xclip is not installed. Please install it first.")
        print("You can install it using: sudo apt-get install xclip")
        raise
    except subprocess.CalledProcessError as e:
        print(f"Error: Failed to copy to clipboard. Error code: {e.returncode}")
        raise


def get_clipboard() -> str:
    """Get clipboard contents using xclip"""
    try:
        result = subprocess.run(['xclip', '-o', '-selection', 'clipboard'],
                              capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error accessing clipboard: {e}", file=sys.stderr)
        return ""

# URL processing functions
def is_youtube_url(url: str) -> bool:
    """Check if the URL is from YouTube"""
    youtube_domains = ['youtube.com', 'www.youtube.com', 'youtu.be']
    for domain in youtube_domains:
        if domain in url:
            return True
    return False

def is_amazon_url(url: str) -> bool:
    """Check if the URL is from Amazon"""
    amazon_domains = ['amazon.com', 'amazon.de', 'amazon.co.uk', 'amazon.ca', 'amazon.fr', 
                     'amazon.it', 'amazon.es', 'amazon.jp', 'amazon.in']
    for domain in amazon_domains:
        if domain in url:
            return True
    return False

def clean_url(url: str) -> str:
    """Remove query parameters from URL (basic cleaning)"""
    return url.split('?')[0]

def clean_youtube_url(url: str) -> str:
    """Clean YouTube URL by keeping only the video ID parameter"""
    if 'youtu.be/' in url:
        # For youtu.be short links, just return as is or clean it
        return clean_url(url)
    
    # For youtube.com links, keep only the v parameter
    base_url, _, query = url.partition('?')
    if not query:
        return url
    
    params = query.split('&')
    video_id = None
    for param in params:
        if param.startswith('v='):
            video_id = param.split('=')[1]
            break
    
    if video_id:
        return f"{base_url}?v={video_id}"
    return base_url

def clean_amazon_url(url: str) -> str:
    """Clean Amazon URL by removing all query parameters"""
    return clean_url(url)

def minimize_youtube_url(url: str) -> str:
    """Convert YouTube URL to its shortest form (youtu.be)"""
    # First clean the URL
    cleaned = clean_youtube_url(url)
    
    # Extract video ID
    video_id = None
    if 'youtu.be/' in cleaned:
        video_id = cleaned.split('youtu.be/')[1]
    elif 'v=' in cleaned:
        video_id = cleaned.split('v=')[1]
    
    if video_id:
        return f"https://youtu.be/{video_id}"
    return cleaned

def minimize_amazon_url(url: str) -> str:
    """Minimize Amazon URL to just the product page"""
    # First clean the URL
    cleaned = clean_amazon_url(url)
    
    # Extract the product ID (dp/XXXXXXXXXX)
    dp_match = re.search(r'(/dp/[A-Z0-9]{10})', cleaned)
    if dp_match:
        # Get the domain
        domain_match = re.match(r'(https?://[^/]+)', cleaned)
        if domain_match:
            domain = domain_match.group(1)
            return f"{domain}{dp_match.group(1)}/"
    
    return cleaned

def process_url(url: str, mode: str) -> str:
    """
    Process URL based on the selected mode
    
    Args:
        url (str): The URL to process
        mode (str): The processing mode ('full', 'cleaned', or 'minimalistic')
    
    Returns:
        str: The processed URL
    """
    if mode == 'full':
        return url
    
    # Apply site-specific processing
    if is_youtube_url(url):
        if mode == 'cleaned':
            return clean_youtube_url(url)
        elif mode == 'minimalistic':
            return minimize_youtube_url(url)
    elif is_amazon_url(url):
        if mode == 'cleaned':
            return clean_amazon_url(url)
        elif mode == 'minimalistic':
            return minimize_amazon_url(url)
    
    # Default processing for other URLs
    if mode == 'cleaned':
        return clean_url(url)
    elif mode == 'minimalistic':
        return clean_url(url)  # For now, minimalistic is same as cleaned for unknown sites
    
    # Fallback
    return url

def send_key(key_command: str, verbose: bool = False) -> None:
    """Send keyboard commands using xdotool, but first verify browser is focused"""
    # Check that browser is still focused before sending any keys
    assert_browser_focused(verbose)
    
    try:
        subprocess.run(['xdotool', 'key', key_command], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error sending keyboard command: {e}", file=sys.stderr)

def calculate_step_delay(sleep_delay: float, item_delay: Optional[float], verbose: bool) -> float:
    """Calculate the appropriate delay per step based on sleep_delay and item_delay"""
    # Number of steps per tab iteration
    STEPS_PER_TAB = 3  # Ctrl+L, Ctrl+C, Ctrl+PgDn
    
    if item_delay is None:
        return sleep_delay
    
    # Calculate what the sleep_delay would need to be to achieve the desired item_delay
    calculated_sleep = item_delay / STEPS_PER_TAB
    
    # Use the larger of the two values
    final_delay = max(sleep_delay, calculated_sleep)
    
    if verbose and final_delay != sleep_delay:
        print(f"INFO: Using calculated step delay of {final_delay:.3f}s to achieve tab delay of {item_delay}s", 
              file=sys.stderr)
    
    return final_delay

def collect_urls(boot_delay: float, sleep_delay: float, item_delay: Optional[float], 
                url_mode: str, duplicates_threshold: int, max_tabs: int, verbose: bool) -> List[str]:
    """Collect URLs from browser tabs"""
    collected_urls: List[str] = []
    duplicates_counter = 0
    duplicates_consecutive = 0
    tabs_visited = 0
    
    # Calculate the appropriate delay per step
    effective_sleep_delay = calculate_step_delay(sleep_delay, item_delay, verbose)

    # Wait for browser window to be focused
    log_verbose("Waiting for browser window to be focused...", verbose)
    wait_for_browser_focus(verbose)

    log_verbose(f"Waiting {boot_delay} seconds before starting...", verbose)
    time.sleep(boot_delay)

    log_verbose(f"URL processing mode: {url_mode}", verbose)

    while duplicates_consecutive < duplicates_threshold and tabs_visited < max_tabs:
        # Select address bar
        log_verbose("Pressing Ctrl+L (to select location)", verbose)
        send_key('ctrl+l', verbose)
        time.sleep(effective_sleep_delay)  # Wait for address bar to be selected

        # Copy URL
        log_verbose("Pressing Ctrl+C (to copy to clipboard)", verbose)
        send_key('ctrl+c', verbose)
        time.sleep(effective_sleep_delay)  # Wait for clipboard to be updated

        # Get and process URL
        original_url = get_clipboard()
        new_url = process_url(original_url, url_mode)
        
        if verbose and original_url != new_url:
            log_verbose(f"Processed URL: {original_url} -> {new_url}", verbose)
        
        if new_url in collected_urls:
            duplicates_counter += 1
            duplicates_consecutive += 1
            log_verbose(f"Duplicate URL found ({duplicates_counter}/{duplicates_threshold})", verbose)
        else:
            duplicates_consecutive = 0
            collected_urls.append(new_url)
            print(new_url)
            duplicates_counter = 0  # Reset counter when new URL is found

        # Move to next tab
        log_verbose("Moving to next tab", verbose)
        send_key('ctrl+Page_Down', verbose)
        time.sleep(effective_sleep_delay)  # Wait for tab switch
        tabs_visited += 1

    return collected_urls

def main() -> None:
    """Main function"""
    args = parse_arguments()
    
    # Determine URL processing mode
    url_mode = 'full' if args.full_urls else 'minimalistic' if args.minimalistic_urls else 'cleaned'
    
    try:
        urls = collect_urls(args.boot, args.sleep, args.item_delay, url_mode, 
                           args.duplicates_threshold, args.max_tabs, args.verbose)
        paste_to_clipboard("\n".join(urls))
        
        if args.verbose:
            print(f"Collected {len(urls)} unique URLs in {url_mode} mode", file=sys.stderr)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        sys.exit(1)
    except BrowserFocusLostError:
        print("\nOperation cancelled: Browser window focus was lost", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()


# This script includes:
# 
# 1. Proper argument handling with argparse
# 2. Type hints for better code readability and maintenance
# 3. Comprehensive error handling
# 4. Verbose logging option
# 5. Clean function separation
# 6. Enum for keyboard commands
# 7. Documentation strings
# 8. Consistent timing between operations
# 9. proper main() function with error handling
# 
# To use the script:
# 
# ```bash
# # Basic usage
# ./script.py
# 
# # With custom boot delay and verbose output
# ./script.py -b 2.5 -v
# 
# # Show help
# ./script.py --help
# ```
# 
# Dependencies:
# - Python 3
# - xclip
# - xdotool
# 
# On Arch Linux, you can install the dependencies with:
# ```bash
# sudo pacman -S xclip xdotool
# ```
# 
# The script will collect URLs from your browser tabs until it encounters the same URL multiple times (defined by duplicates_threshold), indicating it has cycled through all tabs.
# 
# The changes made include:
# 
# 1. Added a new command line argument `-s` or `--sleep` with a default value of 0.25 seconds in the `parse_arguments` function.
# 2. Modified the `collect_urls` function signature to accept the new `sleep_delay` parameter.
# 3. Replaced all the hardcoded 0.5-second delays after xdotool commands with the new `sleep_delay` parameter.
# 4. Updated the main function to pass the sleep delay to `collect_urls`.
# 
# Now users can control the delay between commands using the `-s` or `--sleep` flag, with a default of 0.25 seconds if not specified.
# 
# 
# The main changes include:
# 
# 1. Added `get_focused_window_class()` function that uses `xdotool` and `xprop` to get the class name of the currently focused window.
# 
# 2. Added `wait_for_browser_focus()` function that continuously checks the focused window until it detects a supported browser (Chromium, Chrome, or Firefox).
# 
# 3. Modified the `collect_urls()` function to wait for browser focus before starting the collection process.
# 
# The script now requires both `xprop` and `xdotool` packages. For Arch Linux, you can install them with:
# 
# ```bash
# sudo pacman -S xorg-xprop xdotool
# ```
# 
# 
# When running with `-v` or `--verbose`, the script will now show which window is currently focused while waiting for a browser window. Once a supported browser window is detected, it will proceed with the original functionality.
# 
# This improvement ensures that the script only starts when the user has focused on a supported browser window, making it more reliable and user-friendly.
# 
