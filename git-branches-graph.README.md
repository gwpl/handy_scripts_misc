# git-branches-graph

A visualization tool that generates directed graphs showing the relationships between Git branches and their common ancestors.

> **Tip:** Before running `git-branches-graph` with the `--all` flag (or when you want to see up-to-date remote branches), it's a good idea to refresh your local view of remotes:
>
> ```bash
> git fetch --prune --all
> ```
> This ensures that deleted or newly created remote branches are accurately reflected in the graph.

## Overview

`git-branches-graph` analyzes your Git repository's branch structure and creates visual representations of how branches relate to each other through their merge-base ancestors. This helps understand the branching history and relationships in complex Git repositories.

## Features

- **Multiple output formats**: Mermaid, Graphviz DOT, CSV, PNG, and interactive HTML
- **Automatic branch detection**: Analyzes all local branches by default
- **Flexible input**: Specify branches explicitly, read from stdin, provide comma-separated lists, or load from file
- **Branch/tag disambiguation**: Automatically resolves naming conflicts, preferring branches over tags
- **Tag support**: Include Git tags in the analysis alongside branches
- **Transitive reduction**: Simplifies graphs by removing redundant edges (can be disabled)
- **Smart labeling**: Uses branch names when ancestors are branch tips, otherwise shows commit hashes
- **Branch clustering**: Group branches pointing to the same commit for clarity

## Usage

```bash
# Visualize all local branches (default Mermaid output)
./git-branches-graph

# Generate PNG image with Graphviz
./git-branches-graph --format png

# Analyze specific branches
./git-branches-graph main feature/auth feature/ui

# Output to specific file
./git-branches-graph --format dot --output branches.dot

# Process branches from git command
git branch | ./git-branches-graph --stdin

# Analyze repository in different directory
./git-branches-graph --repo /path/to/repo

# Include remote branches
./git-branches-graph --all

# Include Git tags in the analysis
./git-branches-graph --tags

# Include both remote branches and tags
./git-branches-graph --all --tags

# Specify branches/tags with comma-separated list
./git-branches-graph --list main,develop,v1.0.0,feature/auth

# Load branches/tags from a file (one per line)
./git-branches-graph --list-file branches.txt

# Show full graph without transitive reduction
./git-branches-graph --no-transitive-reduction

# [EXPERIMENTAL] Show all branches in clusters when they point to same commit
./git-branches-graph --all --cluster-same-commit

# Generate interactive HTML with pan/zoom capabilities
./git-branches-graph --format html --output graph.html

# Open HTML directly in browser (starts local server)
./git-branches-graph --format html --browser
```

## Options

### Input Options
- `-h, --help`: Show help message
- `-s, --stdin`: Read branch names from standard input (mutually exclusive with `-l` and `-L`)
- `-l, --list LIST`: Comma-separated list of branch/tag names (mutually exclusive with `-s` and `-L`)
- `-L, --list-file FILE`: Path to file with branch/tag names, one per line (mutually exclusive with `-s` and `-l`)
- `-a, --all`: Include remote branches in addition to local branches
- `-T, --tags, --include-tags`: Include Git tags in addition to branches
- `-r, --repo REPO`: Path to Git repository (default: current directory)

### Output Options
- `-f, --format {mermaid,dot,csv,png,html}`: Output format (default: mermaid)
- `-o, --output OUTPUT`: Write output to file (auto-generates filename for PNG if omitted)
- `-B, --browser`: When using HTML format, start a local server and open in browser

### Graph Options
- `-C, --cluster-same-commit`: [EXPERIMENTAL] Group branches pointing to same commit into clusters
- `--no-transitive-reduction, --full-graph`: Skip transitive reduction to show all edges including redundant paths

## Example Output

### Mermaid Diagram

Here's an example of what the tool generates for a repository with multiple feature branches:

```mermaid
graph LR
    main --> feature/auth
    main --> feature/ui
    main --> develop
    develop --> feature/api
    develop --> bugfix/login
    feature/ui --> feature/ui-redesign
```

This visualization shows:
- `main` is the common ancestor of `feature/auth`, `feature/ui`, and `develop`
- `develop` branches into `feature/api` and `bugfix/login`
- `feature/ui` has a sub-branch `feature/ui-redesign`

### Real-World Example

For a more complex repository, the tool might generate:

```mermaid
graph LR
    main --> release/v2.0
    main --> develop
    develop --> feature/payment
    develop --> feature/notifications
    release/v2.0 --> hotfix/security
    feature/payment --> feature/payment-refactor
    a1b2c3d --> feature/experimental
    a1b2c3d --> spike/performance
```

Note: Commit hashes (like `a1b2c3d`) appear when the common ancestor isn't a branch tip.

```mermaid
graph LR
    0e42ba5 --> foo-branch00
    0e42ba5 --> e4cba6f
    24fbae1 --> 0e42ba5
    24fbae1 --> leaf-branch-name
    99fbae9 --> woo-woo-branch
    99fbae9 --> master
    99fbae9 --> foo-branch
    zoo-branch --> xoo-branch-20
    e4cba6f --> 99fbae9
    e4cba6f --> master-digitalocean
    woo-woo-branch --> boo-branch
    doodoo-branch --> qwerty-branch
    xoo-branch-20 --> doodoo-branch
    foo-branch --> boo-branch-new
    foo-branch --> arr-branch
    arr-branch --> zoo-branch
    24fbae1 --> ror-branch
    ror-branch --> dudu-branch
```

## How It Works

1. **Branch Collection**: Gathers branch names from Git or user input (including tags if requested)
2. **Name Resolution**: Resolves names to commits, handling branch/tag disambiguation
3. **Ancestor Discovery**: Finds merge-base for each branch pair
4. **Graph Construction**: Builds directed edges from ancestors to descendants
5. **Transitive Reduction**: Removes redundant paths for cleaner visualization (optional)
6. **Output Generation**: Formats the graph in the requested format

## Important Note about Multiple Branches on Same Commit

When multiple branches (local and/or remote) point to the same commit, only one branch name will be shown in the graph for that commit. This is because the graph uses commits as nodes, not branches. 

For example, if both `master` and `origin/master` point to the same commit, the graph will show only one of these branch names as the label for that node (typically the last one alphabetically). This behavior is particularly noticeable when using the `--all` flag to include remote branches.

## Experimental Features

### --cluster-same-commit Flag

This experimental feature addresses the limitation above by grouping branches that point to the same commit into visual clusters:

- **Mermaid**: Creates subgraphs containing all branch names
- **Graphviz/DOT**: Creates clusters with a gray background
- **Purpose**: Shows ALL branch names even when they reference the same commit
- **Usage**: `./git-branches-graph --all --cluster-same-commit`

Example output with clustering:
```mermaid
graph LR
    subgraph cluster_1[" "]
        master[master]
        origin/master[origin/master]
    end
    master --> feature/auth
    origin/master --> feature/auth
```

Note: This feature is experimental and may produce more complex graphs. It's particularly useful when you need to see all branch references clearly.

## HTML Output Format

The HTML output format creates an interactive visualization with the following features:

- **Pan and Zoom**: Use mouse wheel to zoom, click and drag to pan
- **Double-click**: Zoom to a specific point
- **Control buttons**: Zoom in/out, reset view, fit to screen
- **Keyboard shortcuts**: +/- for zoom, 0 to reset, F to fit
- **Full-screen view**: The diagram uses the entire browser viewport
- **Embedded Mermaid**: Uses Mermaid.js for rendering with svg-pan-zoom for interactivity

### Usage Examples

```bash
# Save to HTML file
./git-branches-graph --format html -o branches.html

# Open directly in browser (starts local server)
./git-branches-graph --format html --browser

# Combine with other options
./git-branches-graph --all --cluster-same-commit --format html --browser
```

The HTML template includes Font Awesome icons and provides a professional, interactive viewing experience for complex branch graphs.

## Requirements

- Python 3.6+
- Git
- Graphviz (optional, only for PNG output)

## Installation

The script is standalone and requires no installation. Just make it executable:

```bash
chmod +x git-branches-graph
```

## Tips

- Use `--format png` for quick visual inspection
- Pipe Mermaid output to documentation or GitHub README files
- Use CSV format for further processing with other tools
- Combine with `git branch --merged` to focus on active branches
- Use `--list` for analyzing specific branches/tags without affecting your working directory
- Use `--no-transitive-reduction` to see all relationships before simplification
- Combine `--all --tags` to get a complete view of your repository structure

## Troubleshooting

- **"Not in a Git repository"**: Run from within a Git repository or use `--repo`
- **Empty output**: Ensure you have multiple branches to compare
- **PNG generation fails**: Install Graphviz (`apt install graphviz` or `brew install graphviz`)

---

## FAQ

### Why don't I see all remote branches, or why do some deleted branches still appear?

`git-branches-graph` relies on your local Git repository's knowledge of remote branches. If you haven't fetched recently, or if remote branches have been deleted or renamed, your local view may be out of date. To ensure the graph reflects the current state of all remotes, run:

```bash
git fetch --prune --all
```

This updates your local references and prunes any branches that have been deleted on the remote.

### Why do some commits show only one branch name, even if multiple branches point to the same commit?

By default, the tool uses commits as graph nodes, and only one branch name is shown per commit. If you want to see all branch names that point to the same commit, use the experimental `--cluster-same-commit` flag.

### How does the tool handle branches and tags with the same name?

When resolving names, the tool prioritizes branches over tags. It checks in this order:
1. Local branches (`refs/heads/name`)
2. Remote branches (`refs/remotes/name`)
3. Tags (`refs/tags/name`)

This ensures that if a branch and tag share the same name, the branch will be used. When using `--tags`, tags are explicitly marked with "(tag)" suffix to avoid confusion.
