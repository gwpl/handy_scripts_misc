To create a minimal example script that can be both *sourced* and *executed*, follow this template. It allows usage as a library (by sourcing) or as a standalone tool (by executing).

### Key Concepts

1. **Function Definition**:
    - The script centers around the `example_tool` function, which performs a generic task.

2. **Usage Detection**:
    - Uses `BASH_SOURCE` to determine if the script is executed directly or sourced.

3. **Main Function**:
    - The `main` function is invoked only when executed directly, enabling additional functionality when sourced.

### Example Script Template

```bash
#!/bin/bash
# **Example Tool**
#
# *Usage*: `./example_tool.sh <arg1> [arg2]`
#
# This script can be *sourced* or *executed* directly

example_tool() {
    local arg1="$1" arg2="${2:-default}"

    if [[ -z "$arg1" ]]; then
        echo "Usage: example_tool <arg1> [arg2]" >&2
        return 1
    fi

    # Example operation
    echo "Running example_tool with arg1: $arg1 and arg2: $arg2"
}

# Main entry point
main() {
    example_tool "$@"
}

# Check if the script is being sourced or executed
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
```

### Usage

- **Sourcing**: 
  - Source the script to use `example_tool` in other scripts or the shell:  
    ```bash
    source example_tool.sh
    example_tool arg1 arg2
    ```

- **Direct Execution**:
  - Run the script directly:  
    ```bash
    ./example_tool.sh arg1 arg2
    ```

### Integration

- **Modular Architecture**:
  - This script fits into a modular sourcing architecture, allowing individual sourcing or execution. Use `all.sh` to source all scripts in the directory, as detailed in `ABOUT_SOURCABLE.md`.

