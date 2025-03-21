# Bash Sourcing Directory

This directory contains a set of Bash scripts that are designed to be
manually or automatically sourced into your shell configuration (e.g., via your
`.bashrc` or `.profile`).

**Feature** of this directories, is that:

* you can source individual files
* OR via **source all.sh** whole directories with subdirectories **recursively**

The main file, all.sh, sources all other `.sh`
files in the same directory, and also recursively sources any `all.sh`
scripts found in subdirectories ending with `.d`.

## Directory Structure

* `all.sh` — The main script that handles sourcing.
* Other `.sh` files (e.g., `foo.sh`, `bar.sh`) — These scripts will be
  sourced automatically.
* `*.d/` directories — These directories can contain their own all.sh
  script (and additional scripts) that will be sourced recursively.

Example structure:

```
your-directory/  
├── all.sh  
├── foo.sh  
├── bar.sh  
└── config.d/  
  ├── all.sh  
  └── extra.sh
```

## How It Works

1. **Determine the Script Directory:**
   The `all.sh` script uses the `BASH_SOURCE` variable to determine its
   own directory regardless of where it's sourced from.

2. **Recursive Sourcing:**
   It first iterates over any directories ending in `.d` within the
   current directory. For each such directory, if an `all.sh` file
   exists and is readable, it is sourced.

3. **Sourcing Remaining Scripts:**
   Then, `all.sh` iterates over all `.sh` files in its directory and
   sources each one except itself.

## Usage

To integrate these scripts into your shell, simply source all.sh in
your shell configuration file:

```
source /path/to/your-directory/all.sh
```

This ensures that no matter where you place the directory, sourcing
`all.sh` will automatically load all associated scripts.

## Customization

Feel free to add additional scripts or directories as needed. Simply
add new .sh files to the directory or create new subdirectories with
a `.d` suffix containing their own all.sh scripts.

## License

This project is released under the MIT License.
