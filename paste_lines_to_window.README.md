## `paste_lines_to_window.py`

Reads non-empty lines from **stdin** or a file and pastes / types each
line into any X-org window using `xclip` and `xdotool`.  
Perfect for dropping long URL lists into chat apps, editors, shells, or
opening them as new browser tabs.

### Features
* Detects the current terminal window, then waits until you focus the
  **target** window before starting – rock-solid workflow.
* Built-in paste modes (mutually exclusive):  
  • Editor / IM   `ctrl+v,Return` (default)  
  • Terminal    `ctrl+shift+v,Return`  
  • Browser new-tab `ctrl+t,ctrl+v,Return`  
  • Custom sequences via `--paste-commands`.
* Fine-grained timing control  
  • Inter-key delay (`--sleep`)  
  • Exact per-line delay (`--item-delay`) – auto-distributed across the
    sequence.
* Verbose output (`-v`, `-vv`) shows progress, ETA, timing per line, etc.
* Aborts gracefully if the target window loses focus mid-run.

### Examples
```bash
# Paste each line from urls.txt into Telegram (default mode)
./paste_lines_to_window.py -f urls.txt

# Open each line as a new tab in the browser
cat urls.txt | ./paste_lines_to_window.py -B

# Guarantee 2 s per line regardless of sequence length
./paste_lines_to_window.py -f commands.sh -S 2.0 -v
```

### Dependencies
Python 3, `xdotool`, `xclip`, `xprop`

```bash
sudo pacman -S xdotool xclip xorg-xprop
```

### Future roadmap
* Visual progress bar.
* Wayland, macOS, Windows back-ends.
