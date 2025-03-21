#!/bin/bash

# Determine the directory of this script regardless of how it's called.
CURRENT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# First, loop over directories ending with .d in the current directory.
for dir in "$CURRENT_DIR"/*.d; do
  if [ -d "$dir" ]; then
    allfile="${dir}/all.sh"
    if [ -r "$allfile" ]; then
      source "$allfile"
    fi
  fi
done

# Then, loop through all .sh files in the current directory, sourcing each except this script.
for file in "$CURRENT_DIR"/*.sh; do
  if [ "$(basename "$file")" != "all.sh" -a -r "$file" ]; then
    source "$file"
  fi
done


