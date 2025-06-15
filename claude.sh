#!/bin/bash
# Generic wrapper script to launch Claude Code with modified git config
# This script appends a configurable suffix to the current git user name.
# Set CLAUDE_SUFFIX environment variable to override, default is "(claude)"
#
# To always run calude "wrapped" put this script in some $PATH directory and alias claude=`claude.sh` to your ~/.bashrc

# Configure suffix (default: "(claude)")
SUFFIX="${CLAUDE_SUFFIX:-"(claude)"}"

# Get current git user config
CURRENT_NAME=$(git config user.name)
CURRENT_EMAIL=$(git config user.email)

# Check if git user is configured
if [ -z "$CURRENT_NAME" ] || [ -z "$CURRENT_EMAIL" ]; then
    echo "Error: Git user.name and user.email must be configured"
    echo "Run: git config --global user.name \"Your Name\""
    echo "Run: git config --global user.email \"your.email@example.com\""
    exit 1
fi

# Set Claude-specific git config using environment variables
export GIT_AUTHOR_NAME="$CURRENT_NAME $SUFFIX"
export GIT_COMMITTER_NAME="$CURRENT_NAME $SUFFIX"

# Add +claude suffix to email if it doesn't already have it
if [[ "$CURRENT_EMAIL" == *"+claude.code"* ]]; then
    export GIT_AUTHOR_EMAIL="$CURRENT_EMAIL"
    export GIT_COMMITTER_EMAIL="$CURRENT_EMAIL"
else
    # Insert +claude before @ symbol
    export GIT_AUTHOR_EMAIL="${CURRENT_EMAIL/@/+claude@}"
    export GIT_COMMITTER_EMAIL="${CURRENT_EMAIL/@/+claude@}"
fi

# Launch Claude Code with all arguments passed through
exec claude "$@"
