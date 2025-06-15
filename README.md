# `handy_scripts`

# 🚨 **MIGRATION IN PROGRESS** 🚨

## **We are migrating to a new organizational structure:**

### **New Home: [https://github.com/shibuido](https://github.com/shibuido)**

- **Individual repositories** for each KISS (Keep It Simple, Stupid) script
- **Git superrepos** containing submodules for easy `git pull` and PATH management
- **Symbolic linking** into submodules for convenient access
- **Independent repos** for better management of each tool

### **Current Status:**

This repository (`handy_scripts_misc`) and `handy_scripts_CLIAI` currently contain:
- **WIP** (Work In Progress) scripts
- Scripts **not yet migrated** to individual repos
- Scripts that **don't fit** the KISS zen clarity and beauty standards of shibuido

**Please check [shibuido](https://github.com/shibuido) for the latest, clean, production-ready scripts!**

---

Handy scripts for daily workflows.


(We may add more links here as more tools get their own READMEs.)

In directory **sourceable** 📂, one can source scripts or directories individually, or use `source path.../all.sh` (in your current shell or `.profile`/`.bashrc`) at any level to recursively source all scripts from that directory and its subdirectories.

If you really like script in root directory, you can even point your PATH in .bashrc to this directory ;).

Please check each script to know what is it about.
Maybe in future I will automate keeping readme updated about them.
## Tool-specific READMEs

Some tools/scripts have their own detailed README files in this directory. For example:

* [bookmarks_chromium.README.md](./bookmarks_chromium.README.md) — Documentation for `bookmarks_chromium.py`, a command-line and library utility for managing Chromium/Chrome/Brave bookmarks.
* [collect_urls_from_all_tabs.README.md](./collect_urls_from_all_tabs.README.md) — Documentation for `collect_urls_from_all_tabs.py`, a helper that collects URLs from all open browser tabs and copies them to clipboard.
* [git-branches-graph.README.md](./git-branches-graph.README.md) — Documentation for `git-branches-graph`, a tool that visualizes Git branch relationships as directed graphs in Mermaid, Graphviz, CSV, or PNG formats.
* [paste_lines_to_window.README.md](./paste_lines_to_window.README.md) — Documentation for `paste_lines_to_window.py`, a script that pastes lines into any focused window using xclip and xdotool.
