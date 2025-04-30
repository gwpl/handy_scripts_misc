#!/usr/bin/env python3
r"""
==============================================================================
Chromium-Bookmarks Utility
==============================================================================
This script provides a CLI + library for working with the JSON “Bookmarks”
file used by Chromium based browsers (Chromium, Chrome, Brave, etc.).

Specification / Road-Map (keep in sync as the script evolves)
------------------------------------------------------------------------------
Current features
* Locate a “Bookmarks” file for:
  - default user-data-dir &/or profile
  - an explicitly given --user-data-dir or --bookmarks-file path
* List bookmark *directories* (folders)
  - Output formats:
      • path  (unix-style “/” hierarchy, similar to `find`)
      • path+id  (folder path with “ (id:42)” suffix)
      • csv   (id,parent_id,name)
      • jsonl (one JSON object per line)
  - Optional: include folders *and* bookmarks below each folder
  - Ability to start listing at a selected subtree (by id or name fragment)
* List *contents* of a concrete folder
  - Filter: only folders / only bookmarks / mixed
  - Output formats:
      • urls            (one per line)
      • urls+titles     (“URL  TITLE” separated by TAB)
      • jsonl           (raw nodes)
      • markdown        (“* [title](url)”)
* Folder *selector*: accepts numeric id or (partial) name.  Ambiguity triggers
  a fatal “ERROR: … ambiguous …” message.

Verbosity & logging
* -v / --verbose flag is cumulative.  
  Level 0 = WARNING/ERROR only  
  Level 1 = INFO  
  Level 2+ = DEBUG  
* All log lines go to *stderr* and are prefixed with “INFO: ”, “DEBUG: ”, etc.

Future road-map (☞ not yet implemented)
* Moving / merging folders, duplicate search, add / edit / delete bookmarks,
  sync between browsers, import/export, sqlite3 meta-store …

Standard library only ‑ except that the external `jq` binary *may* be used
but only for future advanced features; today everything is Python.

The module is import-safe: no work is executed on import aside from constant
definitions.  `main()` must be called for CLI use.

Author: 2025-04
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------#
# Logging helpers                                                            #
# ---------------------------------------------------------------------------#
_VERBOSITY = 0  # 0-warning, 1-info, 2-debug


def _log(level: str, msg: str, *, v_required: int = 0) -> None:
    """Internal logging respecting global _VERBOSITY."""
    if _VERBOSITY >= v_required:
        sys.stderr.write(f"{level}: {msg}\n")


def log_error(msg: str) -> None:
    _log("ERROR", msg)


def log_warning(msg: str) -> None:
    _log("WARNING", msg)


def log_info(msg: str) -> None:
    _log("INFO", msg, v_required=1)


def log_debug(msg: str) -> None:
    _log("DEBUG", msg, v_required=2)


# ---------------------------------------------------------------------------#
# Bookmarks file discovery                                                   #
# ---------------------------------------------------------------------------#
_LINUX_DEFAULT_DIRS = [
    Path("~/.config/chromium").expanduser(),
    Path("~/.config/google-chrome").expanduser(),
    Path("~/.config/brave-browser").expanduser(),
]


def _detect_bookmarks_file(
    user_data_dir: Optional[Path], profile: str
) -> Optional[Path]:
    """Return the Bookmarks file Path or None if not found."""
    candidates: List[Path] = []
    if user_data_dir is not None:
        candidates.append(user_data_dir.expanduser() / profile / "Bookmarks")
    else:
        for base in _LINUX_DEFAULT_DIRS:
            candidates.append(base / profile / "Bookmarks")

    for path in candidates:
        if path.is_file():
            log_debug(f"Found Bookmarks file at {path}")
            return path
    return None


# ---------------------------------------------------------------------------#
# JSON helpers                                                               #
# ---------------------------------------------------------------------------#
Node = Dict[str, Any]


def _load_bookmarks(path: Path) -> Dict[str, Any]:
    log_info(f"Loading bookmarks from {path}")
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------#
# Traversal utils                                                            #
# ---------------------------------------------------------------------------#
def _iter_folders(
    node: Node, parent_id: Optional[str] = None, path_parts: Optional[List[str]] = None
):
    """Yield tuples (folder_node, parent_id, path_parts)."""
    path_parts = list(path_parts or [])
    if node.get("type") == "folder":
        yield node, parent_id, path_parts + [node["name"]]
        for child in node.get("children", []):
            yield from _iter_folders(child, node["id"], path_parts + [node["name"]])


def _iter_children(node: Node):
    """Yield direct children nodes of *folder* `node`."""
    return node.get("children", [])


def _match_selector(folders: List[Tuple[Node, str, List[str]]], selector: str) -> Node:
    """Return the single matching folder node for selector."""
    by_id = [f for f, *_ in folders if f["id"] == selector]
    if by_id:
        if len(by_id) > 1:  # Impossible by definition of id, but sanity check
            log_error(f"Internal error: multiple folders with id {selector}")
            sys.exit(1)
        return by_id[0]

    # match by (case-insensitive) substring of name
    sel_low = selector.lower()
    matches = [f for f, *_ in folders if sel_low in f["name"].lower()]
    if not matches:
        log_error(f"No bookmark folder matches selector '{selector}'")
        sys.exit(1)
    if len(matches) > 1:
        names = ", ".join(f"{'/'.join(p)} (id:{f['id']})" for f, _, p in folders if f in matches)
        log_error(
            "ERROR: ambiguous bookmark folder selector, expected one folder to "
            f"match while all these folders match: {names}"
        )
        sys.exit(1)
    return matches[0]


# ---------------------------------------------------------------------------#
# Format helpers                                                             #
# ---------------------------------------------------------------------------#
def _folder_path(path_parts: List[str]) -> str:
    return "/" + "/".join(path_parts)


def _print_folder_line(
    folder: Node,
    parent_id: Optional[str],
    path_parts: List[str],
    args: argparse.Namespace,
):
    path_str = _folder_path(path_parts)
    if args.format == "path":
        suffix = f" (id:{folder['id']})" if args.show_ids else ""
        print(path_str + suffix)
    elif args.format == "csv":
        print(f'{folder["id"]},{parent_id or ""},"{folder["name"]}"')
    elif args.format == "jsonl":
        obj = {
            "id": folder["id"],
            "parent_id": parent_id,
            "name": folder["name"],
            "path": path_str,
        }
        print(json.dumps(obj, ensure_ascii=False))
    else:
        raise ValueError(args.format)


def _print_node(
    node: Node,
    args: argparse.Namespace,
):
    if node["type"] == "folder":
        if args.contents_type in ("all", "folders"):
            if args.contents_format == "urls":
                print(_folder_path([node["name"]]))
            elif args.contents_format == "urls_titles":
                print(f"{_folder_path([node['name']])}\t{node['name']}")
            elif args.contents_format == "markdown":
                print(f"* **{node['name']}**")
            elif args.contents_format == "jsonl":
                print(json.dumps(node, ensure_ascii=False))
    elif node["type"] == "url":
        if args.contents_type in ("all", "bookmarks"):
            if args.contents_format == "urls":
                print(node["url"])
            elif args.contents_format == "urls_titles":
                print(f"{node['url']}\t{node['name']}")
            elif args.contents_format == "markdown":
                print(f"* [{node['name']}]({node['url']})")
            elif args.contents_format == "jsonl":
                print(json.dumps(node, ensure_ascii=False))


# ---------------------------------------------------------------------------#
# Sub-commands                                                               #
# ---------------------------------------------------------------------------#
def cmd_list_dirs(args: argparse.Namespace) -> None:
    bm_path = _detect_bookmarks_file(args.user_data_dir, args.profile) if not args.bookmarks_file else Path(args.bookmarks_file)
    if bm_path is None:
        log_error("Bookmarks file not found. Use --bookmarks-file or --user-data-dir.")
        sys.exit(1)
    data = _load_bookmarks(bm_path)

    roots = data["roots"]
    folders_iter = []
    for root_name, root in roots.items():
        if isinstance(root, dict):
            folders_iter.extend(_iter_folders(root, None, [root_name]))

    # limit to subtree?
    if args.selector:
        sel_folder = _match_selector(folders_iter, args.selector)
        folders_iter = list(_iter_folders(sel_folder, None, []))

    for folder, parent_id, path_parts in folders_iter:
        _print_folder_line(folder, parent_id, path_parts, args)
        if args.with_bookmarks:
            for child in _iter_children(folder):
                if child["type"] == "url":
                    cname = child["name"]
                    cpath = _folder_path(path_parts + [cname])
                    if args.format == "path":
                        print(cpath)
                    elif args.format == "csv":
                        print(f'{child["id"]},{folder["id"]},"{cname}"')
                    elif args.format == "jsonl":
                        print(json.dumps(child, ensure_ascii=False))


def cmd_ls(args: argparse.Namespace) -> None:
    bm_path = _detect_bookmarks_file(args.user_data_dir, args.profile) if not args.bookmarks_file else Path(args.bookmarks_file)
    if bm_path is None:
        log_error("Bookmarks file not found. Use --bookmarks-file or --user-data-dir.")
        sys.exit(1)
    data = _load_bookmarks(bm_path)

    # collect folders once to resolve selector
    all_folders = []
    for root_name, root in data["roots"].items():
        if isinstance(root, dict):
            all_folders.extend(_iter_folders(root, None, [root_name]))

    if not args.selector:
        log_error("A folder selector is required for ls sub-command.")
        sys.exit(1)

    folder_node = _match_selector(all_folders, args.selector)

    # list direct children
    for child in _iter_children(folder_node):
        _print_node(child, args)


# ---------------------------------------------------------------------------#
# CLI argument parsing                                                       #
# ---------------------------------------------------------------------------#
def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Utility to inspect Chromium/Chrome/Brave bookmarks."
    )
    p.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase verbosity (can be given multiple times)",
    )
    p.add_argument("--user-data-dir", type=Path, help="Custom --user-data-dir path")
    p.add_argument("--profile", default="Default", help="Browser profile name")
    p.add_argument(
        "--bookmarks-file",
        type=str,
        help="Explicit path to Bookmarks file (overrides user-data-dir/profile)",
    )

    sub = p.add_subparsers(dest="cmd", required=True)

    # list-dirs
    p_dirs = sub.add_parser("list-dirs", help="List bookmark folders")
    p_dirs.add_argument(
        "--format",
        choices=["path", "csv", "jsonl"],
        default="path",
        help="Output format",
    )
    p_dirs.add_argument(
        "--show-ids",
        action="store_true",
        help="For --format path: append (id:XX)",
    )
    p_dirs.add_argument(
        "--with-bookmarks",
        action="store_true",
        help="Include bookmark items below each folder",
    )
    p_dirs.add_argument(
        "selector",
        nargs="?",
        help="Folder selector (id or name fragment) to start from",
    )
    p_dirs.set_defaults(func=cmd_list_dirs)

    # ls
    p_ls = sub.add_parser(
        "ls", help="List contents of a bookmark folder (similar to `ls`)"
    )
    p_ls.add_argument(
        "--contents-type",
        choices=["all", "folders", "bookmarks"],
        default="all",
        help="What kinds of child nodes to display",
    )
    p_ls.add_argument(
        "--contents-format",
        choices=["urls", "urls_titles", "markdown", "jsonl"],
        default="urls_titles",
        help="How to format each child",
    )
    p_ls.add_argument("selector", help="Folder selector (id or name fragment)")
    p_ls.set_defaults(func=cmd_ls)

    return p


def main(argv: Optional[List[str]] = None) -> None:
    global _VERBOSITY
    args = _build_parser().parse_args(argv)
    _VERBOSITY = args.verbose

    log_debug(f"Arguments: {args}")

    # Dispatch
    args.func(args)


# ---------------------------------------------------------------------------#
# Entry point                                                                #
# ---------------------------------------------------------------------------#
if __name__ == "__main__":  # pragma: no cover
    try:
        main()
    except KeyboardInterrupt:
        log_warning("Interrupted by user")

exit


"""

Please implement python script, 
keep description and specification I provide you at a top of the file in comment
clearly annotated for future file editors to be kept and updated as script evolves,
in structured way with short reusable functions,
in a way that can be imported by other python3 scripts and used as library.
Tool can use `jq` external commandline tool, whenever appropriate to simplify codecase.

When used from command line.
the more -v|--verbose flag used the more verbose it becomes,
and verbosity logging is prefixed 'INFO:' 'DEBUG:' 'WARNING:' 'ERROR:' and goes to STDERR.

We like an utility that would allow working
with chromium bookmarks json file standard
(chromium, chrome, brave, etc).

We want to support usecase of users that use default data directory
and multiple profiles,
as well as users who set custom --user-data-dir= chromium/chrome base directory.

For now we would like to be able to :

* list bookmark directories paths 
   * In different formats : in format similar to `find` with `/` , also with option to display `id` next to each at the end, or just as csv with id, parentid, and name..., jsonl (jsonlines)
   * displaying such three without or with bookmarks themselves
   * possibility to start at selected subtree
* list contents of some bookmark folder (bookmarks and folders, or just bookmarks, or just folders...)
   * also in different formats (just urls, or urls and titles, or as jsonl, or as markdown)
* as "selector" for selecting directory user should be able to use either id or name or fragment of foldername (and in case of ambiguity get 'ERROR: ambiguous bookmark folder selector, expected one folder to match while all those folders match: ... .

Prepare structurally codebase for future were new features will be added, and keep in project description list notes as future roadmap:

* features for modyfing bookmarks:
  * moving bookmark between folders
  * merging bookmark folders
  * searching for duplicates
  * adding bookmarks
  * editing bookmark (title, url, etc) or folder
  * syncing bookmarks between browsers
  * import/export of bookmarks to other formars, files, maybe tracking in sqlite3, especially for meta menagement of bookmarks from multple browsers

---

HERE are extra notes from assistant that may help you implement it:

Summary of https://www.perplexity.ai/search/bookmarks-sqlite-of-chromium-c-_2mYTGT3QcyWsGSZMBbS9Q

Essence of Chromium-Based Browser Bookmarks Management and `jq` Utilization

#### Storage and Structure

- **Location**: Chromium-based browsers (Chrome, Chromium, Brave) store bookmarks in a JSON file, not in a SQLite database, with paths varying by OS:
  - **Chrome** (Windows): `C:\\Users\\[USERNAME]\\AppData\\Local\\Google\\Chrome\\User Data\\Default\\Bookmarks`
  - **Brave**: Similar path structure, replacing `Google\\Chrome` with `BraveSoftware\\Brave-Browser`.
  - **Chromium**: Typically found in `~/.config/chromium/Default/Bookmarks` on Linux.

- **JSON Structure**: The bookmarks file comprises:
  - A `checksum` for integrity.
  - A `roots` element hosting the bookmarks hierarchy.
  - Special folders like `bookmark_bar`, `other`, and `mobile`.

- **Node Types**:
  - **Folders**: Include `type: "folder"` and `children` array.
  - **Bookmarks**: With `type: "url"`, `url`, `guid`, `date_added`.

#### Programmatic Manipulation with Python and `jq`

**Python**
- **Read/Write**: Utilize Python's `json` module for reading and manipulating JSON.
  - Backup before modification: `shutil.copy2(bookmarks_path, bookmarks_path + '.bak')`
  - Restart the browser to apply changes.

- **Operations**:
  - Add, update, and move bookmarks by altering node properties.
  - Traverse nodes to find bookmarks/folders via recursive functions.

**`jq` Utility**
- A command-line JSON processor, `jq` enables:
  - **Reading**: Query JSON for bookmarks using path selection and filtering.
  - **Updating**: Modify properties and reorder bookmarks with deep traversal capabilities, using constructs like `walk` for recursion.
  - **Batch Processing**: Incorporate CSV inputs for bulk updates, maintaining JSON integrity with `jq empty`.

#### Performance and Safety

- **Optimization**: Efficient handling of large datasets (~10k bookmarks) with linear scaling.
- **Safety**: Ensure JSON validity, make backups, and use atomic operations (`sponge` for replacing files safely).

#### Alternatives
- **Chrome Extension API**: For direct, supported bookmark manipulations within the browser context.
- **Import/Export**: Use browser capabilities for robust backup and migration handling.
- **Hybrid Approaches**: Combine `jq` with browser API calls for comprehensive management, making `jq` ideal for batch and CI/CD scenarios.

By leveraging the flexibility and power of `jq` alongside Python scripting, users can achieve automated and scalable bookmark management across Chromium-based browsers while maintaining JSON integrity and system stability.


"""
