#!/bin/bash

# Script to manage Konsole Shift+Enter keybindings
# Author: Script generated to fix Shift+Enter producing OM in Konsole

set -euo pipefail

# Default keytab file location (may vary by distribution)
DEFAULT_KEYTAB="/usr/share/konsole/default.keytab"
USER_KEYTAB="$HOME/.local/share/konsole/default.keytab"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to display usage
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Fix or manage Konsole Shift+Enter keybindings that produce "OM" instead of newline.

OPTIONS:
    (no options)     Display current Return key mappings
    -h, --help      Show this help message
    -f, --fix       Fix Shift+Enter to send newline (\\r\\n) instead of \\EOM
    -r, --revert    Revert Shift+Enter back to default (\\EOM)
    -k, --keytab    Specify custom keytab file (default: $DEFAULT_KEYTAB)
    -e, --explain   Show technical explanation of the issue
    
EXAMPLES:
    $0                    # Show current Return mappings
    $0 --fix              # Fix Shift+Enter in user's keytab
    $0 --fix -k custom.keytab  # Fix in specific keytab file
    $0 --explain          # Learn why this happens

EOF
}

# Function to explain the issue
explain() {
    cat << 'EOF'
TECHNICAL EXPLANATION: Shift+Enter → "OM" in Konsole

ISSUE: Konsole maps Shift+Enter to \EOM (0x1B 0x4F 0x4D) - the VT100 numeric keypad Enter
sequence from 1978. Modern CLIs expecting multiline input get confused.

ROOT CAUSE: Legacy keytab mapping. Konsole's default.keytab has:
  key Return+Shift : "\EOM"  # Should be "\r\n" for modern apps

HISTORICAL CONTEXT: VT100 distinguished main Enter (\r) from keypad Enter (\EOM) for
apps like vim/emacs. Made sense when terminals had physical numeric keypads.

WHY TMUX WORKS: Terminal multiplexers intercept/normalize escape sequences. tmux sees
\EOM and translates it sensibly, knowing apps rarely want keypad codes from Shift+Enter.

KEYTAB SYNTAX:
  Return+Shift         : "\EOM"   # Shift pressed → problem
  Return-Shift+NewLine : "\r\n"   # No Shift, NewLine mode ON
  Return-Shift-NewLine : "\r"     # No Shift, NewLine mode OFF
  (+/- = modifier state, NewLine = terminal mode via ESC[20h, not a key)

FIX: Change mapping to Return+Shift : "\r\n"

RELATED: Home/End producing ~, function key weirdness. Why devs migrate to Alacritty/Kitty.

EOF
}

# Function to find keytab file
find_keytab() {
    local keytab="$1"
    
    # If keytab is already a full path and exists, use it
    if [[ -f "$keytab" ]]; then
        echo "$keytab"
        return 0
    fi
    
    # Search in common locations
    local search_paths=(
        "$HOME/.local/share/konsole"
        "$HOME/.config/konsole"
        "/usr/share/konsole"
        "/usr/share/apps/konsole"
        "/usr/local/share/konsole"
    )
    
    for path in "${search_paths[@]}"; do
        if [[ -f "$path/$keytab" ]]; then
            echo "$path/$keytab"
            return 0
        fi
    done
    
    # Not found
    return 1
}

# Function to display current Return mappings
show_mappings() {
    local keytab="$1"
    
    echo -e "${BLUE}Current Return key mappings in: $keytab${NC}"
    echo
    
    if [[ -f "$keytab" ]]; then
        grep -E "^key Return" "$keytab" | while IFS= read -r line; do
            if [[ "$line" =~ Return\+Shift.*OM ]] || [[ "$line" =~ Return\+Shift.*\\\\EOM ]]; then
                echo -e "${RED}$line${NC}  ← This causes the 'OM' issue"
            elif [[ "$line" =~ Return\+Shift.*\\r\\n ]]; then
                echo -e "${GREEN}$line${NC}  ← Fixed mapping"
            else
                echo "$line"
            fi
        done
    else
        echo -e "${RED}Error: Keytab file not found: $keytab${NC}"
        exit 1
    fi
}

# Function to fix the keybinding
fix_keybinding() {
    local keytab="$1"
    
    # Create user keytab directory if it doesn't exist
    mkdir -p "$(dirname "$USER_KEYTAB")"
    
    # If working on system keytab, copy to user directory
    if [[ "$keytab" == /usr/* ]] || [[ "$keytab" == /etc/* ]]; then
        echo -e "${YELLOW}System keytab detected. Creating user copy...${NC}"
        cp "$keytab" "$USER_KEYTAB"
        keytab="$USER_KEYTAB"
    fi
    
    # Check if already fixed
    if grep -q '^key Return+Shift : "\\r\\n"' "$keytab" 2>/dev/null; then
        echo -e "${GREEN}✓ Shift+Enter is already fixed in $keytab${NC}"
        return 0
    fi
    
    # Backup original
    cp "$keytab" "${keytab}.backup.$(date +%Y%m%d_%H%M%S)"
    
    # Fix the keybinding
    if sed -i 's/^key Return+Shift : "\\EOM"/key Return+Shift : "\\r\\n"/' "$keytab"; then
        echo -e "${GREEN}✓ Fixed Shift+Enter mapping in: $keytab${NC}"
        echo -e "${YELLOW}Note: Restart Konsole or reload the profile for changes to take effect${NC}"
    else
        echo -e "${RED}Error: Failed to update keytab file${NC}"
        exit 1
    fi
}

# Function to revert the keybinding
revert_keybinding() {
    local keytab="$1"
    
    # Create user keytab directory if it doesn't exist
    mkdir -p "$(dirname "$USER_KEYTAB")"
    
    # If working on system keytab, copy to user directory
    if [[ "$keytab" == /usr/* ]] || [[ "$keytab" == /etc/* ]]; then
        echo -e "${YELLOW}System keytab detected. Creating user copy...${NC}"
        cp "$keytab" "$USER_KEYTAB"
        keytab="$USER_KEYTAB"
    fi
    
    # Check if already default
    if grep -q '^key Return+Shift : "\\EOM"' "$keytab" 2>/dev/null; then
        echo -e "${YELLOW}✓ Shift+Enter is already set to default \\EOM in $keytab${NC}"
        return 0
    fi
    
    # Backup original
    cp "$keytab" "${keytab}.backup.$(date +%Y%m%d_%H%M%S)"
    
    # Revert the keybinding
    if sed -i 's/^key Return+Shift : "\\r\\n"/key Return+Shift : "\\EOM"/' "$keytab"; then
        echo -e "${YELLOW}✓ Reverted Shift+Enter mapping to default in: $keytab${NC}"
        echo -e "${YELLOW}Note: Restart Konsole or reload the profile for changes to take effect${NC}"
    else
        echo -e "${RED}Error: Failed to update keytab file${NC}"
        exit 1
    fi
}

# Main script logic
main() {
    local action="show"
    local keytab="$DEFAULT_KEYTAB"
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -h|--help|help)
                usage
                exit 0
                ;;
            -f|--fix)
                action="fix"
                shift
                ;;
            -r|--revert)
                action="revert"
                shift
                ;;
            -k|--keytab)
                keytab="$2"
                shift 2
                ;;
            -e|--explain)
                explain
                exit 0
                ;;
            *)
                echo -e "${RED}Unknown option: $1${NC}"
                usage
                exit 1
                ;;
        esac
    done
    
    # Find the keytab file
    if ! keytab=$(find_keytab "$(basename "$keytab")"); then
        echo -e "${RED}Error: Keytab file not found: $keytab${NC}"
        echo "Searched in: ~/.local/share/konsole, ~/.config/konsole, /usr/share/konsole, etc."
        exit 1
    fi
    
    # Perform the requested action
    case "$action" in
        show)
            show_mappings "$keytab"
            ;;
        fix)
            fix_keybinding "$keytab"
            ;;
        revert)
            revert_keybinding "$keytab"
            ;;
    esac
}

# Run main function
main "$@"