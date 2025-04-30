## `bookmarks_chromium.py`

Script to interact with chromium/chrome/brave/... bookmarks json file from commandline.

Desgined to serve users using multiple profiles and/or multiple `--user-data-dir=` separate browser instances via separate directories roots.

Most up to date info about flags via `--help` of course :).

Sub commands many have more flags, then one needs to call `cmd` command with `--help` flag (or `-h`), like `bookmarks_chromiu.py lds -h`.

Design of script:

* designed to be useful from commandline or `import` in your python script to use its routines.
* if reachable from `$PATH`, you can call it from anywhere, otherwise call directly.
* Hopefully no venv: Script is meant it have minimal dependencies, hopefully run without need for venv.
* Requirements: May need `jq` installed.

Features:
* Locate Chromium/Chrome/Brave bookmarks file automatically for default or custom user-data-dir and profile, or via explicit path.
* List bookmark folders (directories) in multiple formats:
  * Unix-style `/` path tree (like `find`), optionally with folder id.
  * CSV: `id`, `parent_id`, `name`.
  * JSONL: one JSON object per line.
  * Optionally include bookmarks (URLs) under each folder.
  * Can restrict listing to a subtree by folder id or name fragment.
* List contents of a specific bookmark folder:
  * Filter: only folders, only bookmarks, or both.
  * Output formats: URLs, URLs+titles (tab-separated), markdown, or JSONL.
* Folder selection by id or (partial) name; ambiguous selectors trigger clear error with all matches listed.
* Verbosity: `-v`/`--verbose` increases logging (INFO, DEBUG, etc.) to stderr.
* All features available both as CLI and as importable Python library.

Future roadmap (see script for details):
* Bookmark/folder modification: move, merge, add, edit, delete.
* Duplicate search, sync between browsers, import/export, sqlite3 meta-store.
* Advanced batch operations (may use `jq` for complex JSON manipulation).

### Example usacase: "Bookmark all tabs and paste as markdown into Telegram"

1. Bookmark all tabs from given window into folder:

"Bookmark All Tabs" / Ctrl+Shift+D, e.g. as "Nerdy curiosities by scribblemouth_ Instagrammer".

2. Check matching folders: our custom chromium instance

We use separate chromium instance with `--user-data-dir` (we can use shortflag `-d`) , e.g. `lsd` to list folders:

```
$ bookmarks_chromium.py -d browser_instances/instanceX lsd | grep scrib
```

3. List folder contents with `ls` (top 3 results via `head -n 3`):

Assuming using fragment of folder name `scribblemouth_` is sufficient to identify one folder, we can just use fragment of folder name:

```
$ bookmarks_chromium.py -d browser_instances/instanceX ls scribblemouth_  | head -n 3
https://www.instagram.com/scribblemouth_/reel/DI8lwEsvRZz/      ScribbleMouth | 🃏 🧠You are scientifically amazing!! Proven by a deck of cards. The universe tends towards maximum entropy, and yet as a little island of... | Instagram
https://www.instagram.com/scribblemouth_/reel/DJEPdlrPiQy/      ScribbleMouth | ♾🔭Mathematics reveals the most amazing things about our reality 🧠. #education #science #facts #universe #mystery #philosophy #bigbang... | Instagram
https://www.instagram.com/scribblemouth_/reel/DHFwhqYvLc3/      ScribbleMouth | YOU SHOULD NOT EXIST. At lest the chances of your specific existence are so incredibly low that it seems so strange you exist at all... | Instagram
```

4. Let's set format to markdown with -F markdown (top 3 via `head -n 3`):

```
$ bookmarks_chromium.py -d browser_instances/instanceX ls scribblemouth_ -F markdown | head -n 3
* [ScribbleMouth | 🃏 🧠You are scientifically amazing!! Proven by a deck of cards. The universe tends towards maximum entropy, and yet as a little island of... | Instagram](https://www.instagram.com/scribblemouth_/reel/DI8lwEsvRZz/)
* [ScribbleMouth | ♾🔭Mathematics reveals the most amazing things about our reality 🧠. #education #science #facts #universe #mystery #philosophy #bigbang... | Instagram](https://www.instagram.com/scribblemouth_/reel/DJEPdlrPiQy/)
* [ScribbleMouth | YOU SHOULD NOT EXIST. At lest the chances of your specific existence are so incredibly low that it seems so strange you exist at all... | Instagram](https://www.instagram.com/scribblemouth_/reel/DHFwhqYvLc3/)
```

or any other format e.g. `-F jsonl` , `-F urls`, `-F urls_titles` ... e.g. (top 3 via `head -n 3):

```
$ bookmarks_chromium.py -d browser_instances/instanceX ls scribblemouth_ -F urls_titles | head -n 3
https://www.instagram.com/scribblemouth_/reel/DI8lwEsvRZz/      ScribbleMouth | 🃏 🧠You are scientifically amazing!! Proven by a deck of cards. The universe tends towards maximum entropy, and yet as a little island of... | Instagram
https://www.instagram.com/scribblemouth_/reel/DJEPdlrPiQy/      ScribbleMouth | ♾🔭Mathematics reveals the most amazing things about our reality 🧠. #education #science #facts #universe #mystery #philosophy #bigbang... | Instagram
https://www.instagram.com/scribblemouth_/reel/DHFwhqYvLc3/      ScribbleMouth | YOU SHOULD NOT EXIST. At lest the chances of your specific existence are so incredibly low that it seems so strange you exist at all... | Instagram
```
