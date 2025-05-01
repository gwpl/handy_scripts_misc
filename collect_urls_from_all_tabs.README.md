## `collect_urls_from_all_tabs.py`

Command-line + importable Python tool that grabs the URL from every open
tab of a focused browser window (Chromium / Chrome / Brave / Firefox) and
emits the list to **stdout** *and* the system clipboard.

### Features
* Waits until a supported browser window is focused before it starts.
* Walks through tabs with `Ctrl+PgDown`, copying each URL (`Ctrl+C`).
* Stops automatically once it has seen the same URL *N* consecutive
  times (configurable – prevents infinite loops).
* Three URL processing modes  
  • **full**   – keep URL untouched  
  • **cleaned** – strip query/trackers (default)  
  • **minimalistic** – per-site shortest form (e.g. `youtu.be/<id>`).
* Fully adjustable timing (`--sleep`, `--item-delay`).
* Verbose mode (`-v`, `-vv`) prints detailed progress/ETA.
* Puts the final list on the clipboard via `xclip` for instant reuse.

### Example usage
```bash
# Collect cleaned URLs (default) – save to file and clipboard
./collect_urls_from_all_tabs.py > urls.txt

# Keep full URLs and be verbose
./collect_urls_from_all_tabs.py -f -v

# Ensure at least 1 s per tab on slow machines
./collect_urls_from_all_tabs.py -S 1.0
```

#### Combined workflow with other tools

```bash
# Paste bookmarks from several folders into Telegram with 12-second pauses
for folder in foo bar zoo ; do \
    bookmarks_chromium.py -f Bookmarks ls "$folder" -F urls ; \
done | paste_lines_to_window.py -v -e -S 12
```

### Dependencies
Python 3, `xdotool`, `xclip`, `xprop`  
Arch Linux:

```bash
sudo pacman -S xdotool xclip xorg-xprop
```

### Future roadmap
* Handle multiple browser windows / monitors.
* Export directly to Markdown / HTML.
* Pipe result into `bookmarks_chromium.py` to bulk-bookmark URLs.
