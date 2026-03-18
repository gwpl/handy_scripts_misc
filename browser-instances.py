#!/usr/bin/env python3
"""
browser-instances.py - Manage stale browser instances (Chromium/Chrome/Brave/Firefox)

Discovers running browser processes, groups them by session (main process),
shows resource usage, user-data paths, debugging ports, and age.
Provides actions: SIGTERM, SIGKILL, SIGSTOP, SIGCONT, and
"stop-all-except" for temporary CPU relief (e.g., during videocalls).
"""

import argparse
import os
import signal
import sys
import time
import datetime
import re
import subprocess
from collections import defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BROWSER_PATTERNS = {
    "chromium":  ["/usr/lib/chromium/chromium", "chromium-browser"],
    "chrome":    ["/opt/google/chrome/chrome", "google-chrome", "chrome"],
    "brave":     ["/opt/brave-bin/brave", "/opt/brave.com/brave/brave", "brave"],
    "firefox":   ["/usr/lib/firefox/firefox", "firefox", "firefox-esr"],
}

# Helper executables that belong to a browser session but aren't main processes
HELPER_NAMES = {
    "chrome_crashpad_handler", "crashpad_handler",
    "nacl_helper", "nacl_helper_bootstrap",
    "plasma-browser-integration-host",
}

INTERESTING_FLAGS = [
    "--user-data-dir",
    "--profile-directory",
    "--remote-debugging-port",
    "--remote-debugging-address",
    "--remote-debugging-pipe",
    "--headless",
    "--no-sandbox",
    "--disable-gpu",
    "--incognito",
    "--private-window",
    "--temp-profile",
]

COLORS = {
    "reset":   "\033[0m",
    "bold":    "\033[1m",
    "dim":     "\033[2m",
    "red":     "\033[31m",
    "green":   "\033[32m",
    "yellow":  "\033[33m",
    "blue":    "\033[34m",
    "magenta": "\033[35m",
    "cyan":    "\033[36m",
    "white":   "\033[37m",
}

NO_COLORS = {k: "" for k in COLORS}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def c(name, palette):
    return palette.get(name, "")


def human_duration(seconds):
    if seconds < 60:
        return f"{int(seconds)}s"
    if seconds < 3600:
        return f"{int(seconds // 60)}m{int(seconds % 60)}s"
    if seconds < 86400:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        return f"{h}h{m}m"
    d = int(seconds // 86400)
    h = int((seconds % 86400) // 3600)
    return f"{d}d{h}h"


def human_bytes(n):
    for unit in ("B", "K", "M", "G", "T"):
        if abs(n) < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}P"


def read_proc_file(pid, name):
    try:
        return Path(f"/proc/{pid}/{name}").read_text()
    except (OSError, PermissionError):
        return ""


def get_cmdline(pid):
    raw = read_proc_file(pid, "cmdline")
    if not raw:
        return []
    parts = [p for p in raw.split("\0") if p]
    # Some processes have all args in a single NUL field (launched via shell string).
    # Detect this: if there's only 1 part but it contains spaces and known flags, split it.
    if len(parts) == 1 and " --" in parts[0]:
        parts = parts[0].split()
    return parts


def get_stat_fields(pid):
    """Return (state, ppid, starttime_ticks) from /proc/[pid]/stat."""
    raw = read_proc_file(pid, "stat")
    if not raw:
        return None
    # Parse around the comm field which may contain spaces/parens
    m = re.match(r"(\d+)\s+\(.*?\)\s+(\S+)\s+(\d+)", raw)
    if not m:
        return None
    state = m.group(2)
    ppid = int(m.group(3))
    # starttime is field 22 (0-indexed: 21) - split the rest after comm
    rest = raw[m.end():].split()
    # We already consumed fields 1-4, rest starts at field 5
    # starttime is field 22, so index 22-5 = 17 in rest
    if len(rest) > 17:
        starttime = int(rest[17])
    else:
        starttime = 0
    return state, ppid, starttime


_boot_time = None
_clk_tck = None

def get_boot_time():
    global _boot_time
    if _boot_time is None:
        for line in Path("/proc/stat").read_text().splitlines():
            if line.startswith("btime "):
                _boot_time = int(line.split()[1])
                break
    return _boot_time


def get_clk_tck():
    global _clk_tck
    if _clk_tck is None:
        _clk_tck = os.sysconf("SC_CLK_TCK")
    return _clk_tck


def pid_start_time(pid, starttime_ticks):
    """Absolute start time in epoch seconds."""
    return get_boot_time() + starttime_ticks / get_clk_tck()


def get_resource_usage(pid):
    """Return (rss_bytes, cpu_percent_approx) from /proc/[pid]/stat + statm."""
    statm = read_proc_file(pid, "statm")
    rss_pages = 0
    if statm:
        parts = statm.split()
        if len(parts) >= 2:
            rss_pages = int(parts[1])
    page_size = os.sysconf("SC_PAGE_SIZE")
    rss_bytes = rss_pages * page_size

    # CPU: read utime+stime from stat
    stat_raw = read_proc_file(pid, "stat")
    cpu_pct = 0.0
    if stat_raw:
        m = re.match(r"\d+\s+\(.*?\)\s+\S+\s+\d+", stat_raw)
        if m:
            rest = stat_raw[m.end():].split()
            # utime=field14(idx10 in rest), stime=field15(idx11)
            if len(rest) > 17:
                utime = int(rest[10])
                stime = int(rest[11])
                starttime = int(rest[17])
                total_ticks = utime + stime
                elapsed = time.time() - pid_start_time(pid, starttime)
                if elapsed > 0:
                    cpu_pct = (total_ticks / get_clk_tck()) / elapsed * 100.0

    return rss_bytes, cpu_pct


def identify_browser(cmdline):
    """Return (browser_name, process_type) or None."""
    if not cmdline:
        return None
    exe = cmdline[0]
    exe_base = os.path.basename(exe)
    exe_lower = exe.lower()

    # Check helper executables (crashpad handlers, nacl, etc.)
    if exe_base in HELPER_NAMES:
        # Identify browser from directory path - check most specific first
        # e.g. /usr/lib/chromium/chrome_crashpad_handler -> chromium
        #      /opt/brave-bin/chrome_crashpad_handler -> brave
        # Also check --database= flag for crash report path
        search_strings = [exe_lower]
        for arg in cmdline[1:]:
            if arg.startswith("--database=") or arg.startswith("--metrics-dir="):
                search_strings.append(arg.lower())

        # Order matters: check chromium before chrome (more specific first)
        browser_check_order = ["chromium", "brave", "firefox", "chrome"]
        for browser in browser_check_order:
            for s in search_strings:
                if browser in s:
                    return browser, "helper"
        return "unknown", "helper"

    # Check main/subprocess executables - most specific first
    browser_check_order = ["chromium", "brave", "firefox", "chrome"]
    for browser in browser_check_order:
        patterns = BROWSER_PATTERNS[browser]
        for pat in patterns:
            if pat.lower() in exe_lower or pat.lower() == exe_base.lower():
                # Determine subprocess type from --type= flag
                ptype = "main"
                for arg in cmdline[1:]:
                    if arg.startswith("--type="):
                        ptype = arg.split("=", 1)[1]
                        break
                    # Zygote processes identified by flag
                    if arg in ("--no-zygote-sandbox",) and "--type=" not in " ".join(cmdline):
                        ptype = "zygote"
                return browser, ptype

    return None


def extract_flags(cmdline):
    """Extract interesting flags and file:// URLs from cmdline."""
    flags = {}
    urls = []
    for arg in cmdline[1:]:
        for flag in INTERESTING_FLAGS:
            if arg.startswith(flag + "="):
                flags[flag] = arg.split("=", 1)[1]
            elif arg == flag:
                flags[flag] = True
        if arg.startswith("file://") or arg.startswith("http://") or arg.startswith("https://"):
            urls.append(arg)
    return flags, urls


def detect_default_user_data_dir(browser):
    """Return the default user-data-dir for a browser."""
    home = Path.home()
    defaults = {
        "chromium": home / ".config" / "chromium",
        "chrome":   home / ".config" / "google-chrome",
        "brave":    home / ".config" / "BraveSoftware" / "Brave-Browser",
        "firefox":  home / ".mozilla" / "firefox",
    }
    return str(defaults.get(browser, "unknown"))


# ---------------------------------------------------------------------------
# Process discovery
# ---------------------------------------------------------------------------

class BrowserProcess:
    __slots__ = ("pid", "ppid", "browser", "ptype", "state", "start_epoch",
                 "rss", "cpu_pct", "flags", "urls", "cmdline_str", "is_defunct")

    def __init__(self, pid, ppid, browser, ptype, state, start_epoch,
                 rss, cpu_pct, flags, urls, cmdline_str, is_defunct):
        for attr, val in zip(self.__slots__, (pid, ppid, browser, ptype, state,
                start_epoch, rss, cpu_pct, flags, urls, cmdline_str, is_defunct)):
            setattr(self, attr, val)


class BrowserSession:
    """A group of processes belonging to the same browser instance."""
    __slots__ = ("leader", "children", "browser", "user_data_dir",
                 "profile_dir", "debug_port", "urls")

    def __init__(self, leader):
        self.leader = leader
        self.children = []
        self.browser = leader.browser
        self.user_data_dir = leader.flags.get("--user-data-dir",
                                               detect_default_user_data_dir(leader.browser))
        self.profile_dir = leader.flags.get("--profile-directory", "Default")
        self.debug_port = leader.flags.get("--remote-debugging-port", None)
        self.urls = list(leader.urls)

    def add(self, proc):
        self.children.append(proc)
        self.urls.extend(proc.urls)
        # Inherit debug port from children if leader didn't have it
        if not self.debug_port and proc.flags.get("--remote-debugging-port"):
            self.debug_port = proc.flags["--remote-debugging-port"]

    @property
    def all_pids(self):
        return [self.leader.pid] + [c.pid for c in self.children]

    @property
    def total_rss(self):
        return self.leader.rss + sum(c.rss for c in self.children)

    @property
    def total_cpu(self):
        return self.leader.cpu_pct + sum(c.cpu_pct for c in self.children)

    @property
    def age_seconds(self):
        return time.time() - self.leader.start_epoch

    @property
    def process_count(self):
        return 1 + len(self.children)

    @property
    def is_stopped(self):
        return self.leader.state == "T"

    @property
    def is_defunct(self):
        return self.leader.is_defunct


def discover_processes():
    """Find all browser processes for the current user."""
    uid = os.getuid()
    procs = []

    for entry in os.listdir("/proc"):
        if not entry.isdigit():
            continue
        pid = int(entry)
        try:
            if os.stat(f"/proc/{pid}").st_uid != uid:
                continue
        except OSError:
            continue

        cmdline = get_cmdline(pid)
        if not cmdline or not cmdline[0]:
            # Check comm for defunct processes
            comm = read_proc_file(pid, "comm").strip()
            if not comm:
                continue
            found = False
            for browser, patterns in BROWSER_PATTERNS.items():
                for pat in patterns:
                    if comm.lower() in pat.lower() or pat.lower().endswith(comm.lower()):
                        found = True
                        stat = get_stat_fields(pid)
                        if not stat:
                            continue
                        state, ppid, starttime = stat
                        start_epoch = pid_start_time(pid, starttime)
                        procs.append(BrowserProcess(
                            pid=pid, ppid=ppid, browser=browser, ptype="defunct",
                            state=state, start_epoch=start_epoch,
                            rss=0, cpu_pct=0.0, flags={}, urls=[],
                            cmdline_str=f"[{comm}] <defunct>", is_defunct=True,
                        ))
                        break
                if found:
                    break
            continue

        ident = identify_browser(cmdline)
        if not ident:
            continue

        browser, ptype = ident
        stat = get_stat_fields(pid)
        if not stat:
            continue
        state, ppid, starttime = stat
        start_epoch = pid_start_time(pid, starttime)
        rss, cpu_pct = get_resource_usage(pid)
        flags, urls = extract_flags(cmdline)

        # Truncate cmdline for display
        full = " ".join(cmdline)
        if len(full) > 200:
            full = full[:197] + "..."

        procs.append(BrowserProcess(
            pid=pid, ppid=ppid, browser=browser, ptype=ptype,
            state=state, start_epoch=start_epoch,
            rss=rss, cpu_pct=cpu_pct, flags=flags, urls=urls,
            cmdline_str=full, is_defunct="Z" in state,
        ))

    return procs


def _extract_crash_db(proc):
    """Extract crash report database path from helper process cmdline."""
    for part in proc.cmdline_str.split():
        if part.startswith("--database="):
            return part.split("=", 1)[1]
    return None


def group_into_sessions(procs):
    """Group processes into sessions by finding 'main' processes and attaching children.

    Handles reparented helpers (e.g. crashpad handlers adopted by init) by matching
    them to sessions via browser type and start-time proximity.
    """
    by_pid = {p.pid: p for p in procs}
    sessions = []
    assigned = set()

    # Sort by start time so parents come first
    procs_sorted = sorted(procs, key=lambda p: p.start_epoch)

    # Find leader processes: main browser processes whose parent is not in our set
    leaders = []
    for p in procs_sorted:
        if p.ptype in ("main", "defunct"):
            if p.ppid not in by_pid:
                leaders.append(p)

    # Collect children transitively via parent chain
    def collect_children(leader_pid):
        children = []
        for p in procs:
            if p.pid == leader_pid:
                continue
            curr = p
            visited = set()
            while curr.ppid in by_pid and curr.ppid != leader_pid and curr.pid not in visited:
                visited.add(curr.pid)
                curr = by_pid[curr.ppid]
            if curr.ppid == leader_pid:
                children.append(p)
        return children

    for leader in leaders:
        if leader.pid in assigned:
            continue
        session = BrowserSession(leader)
        assigned.add(leader.pid)
        children = collect_children(leader.pid)
        for ch in children:
            if ch.pid not in assigned:
                session.add(ch)
                assigned.add(ch.pid)
        sessions.append(session)

    # Attach orphaned helpers (reparented to init) to nearest session of same browser
    # by start-time proximity (crashpad handlers start within seconds of main process)
    orphan_helpers = [p for p in procs if p.pid not in assigned and p.ptype == "helper"]
    for helper in orphan_helpers:
        best_session = None
        best_dt = float("inf")
        for s in sessions:
            if s.browser == helper.browser:
                dt = abs(helper.start_epoch - s.leader.start_epoch)
                if dt < best_dt:
                    best_dt = dt
                    best_session = s
        # Attach if started within 60 seconds of the session leader
        if best_session and best_dt < 60:
            best_session.add(helper)
            assigned.add(helper.pid)

    # Remaining orphans get their own session
    for p in procs:
        if p.pid not in assigned:
            session = BrowserSession(p)
            assigned.add(p.pid)
            sessions.append(session)

    return sessions


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def print_sessions(sessions, pal, verbose=False, sort_by="age"):
    if sort_by == "age":
        sessions.sort(key=lambda s: s.age_seconds, reverse=True)
    elif sort_by == "memory":
        sessions.sort(key=lambda s: s.total_rss, reverse=True)
    elif sort_by == "cpu":
        sessions.sort(key=lambda s: s.total_cpu, reverse=True)

    now = time.time()
    total_rss = sum(s.total_rss for s in sessions)
    total_procs = sum(s.process_count for s in sessions)

    print(f"\n{c('bold', pal)}{c('cyan', pal)}Browser Instances Summary{c('reset', pal)}")
    print(f"  Sessions: {len(sessions)}  |  Processes: {total_procs}  |  "
          f"Total RSS: {c('yellow', pal)}{human_bytes(total_rss)}{c('reset', pal)}")
    print(f"  {c('dim', pal)}(showing processes owned by uid {os.getuid()}){c('reset', pal)}\n")

    for i, s in enumerate(sessions):
        status_indicator = ""
        if s.is_defunct:
            status_indicator = f" {c('red', pal)}[DEFUNCT]{c('reset', pal)}"
        elif s.is_stopped:
            status_indicator = f" {c('yellow', pal)}[STOPPED]{c('reset', pal)}"

        age = human_duration(s.age_seconds)
        age_color = c('green', pal)
        if s.age_seconds > 86400 * 7:
            age_color = c('red', pal)
        elif s.age_seconds > 86400:
            age_color = c('yellow', pal)

        browser_color = {
            "chromium": c('blue', pal),
            "chrome":   c('green', pal),
            "brave":    c('magenta', pal),
            "firefox":  c('yellow', pal),
        }.get(s.browser, c('white', pal))

        print(f"{c('bold', pal)}[{i}] {browser_color}{s.browser.upper()}{c('reset', pal)}"
              f"  PID {c('bold', pal)}{s.leader.pid}{c('reset', pal)}"
              f"  ({s.process_count} procs){status_indicator}")
        print(f"    Age: {age_color}{age}{c('reset', pal)}"
              f"  |  RSS: {c('yellow', pal)}{human_bytes(s.total_rss)}{c('reset', pal)}"
              f"  |  CPU: {s.total_cpu:.1f}%")
        print(f"    User-data: {c('dim', pal)}{s.user_data_dir}{c('reset', pal)}")
        if s.profile_dir != "Default":
            print(f"    Profile:   {s.profile_dir}")
        if s.debug_port:
            print(f"    Debug port: {c('cyan', pal)}{s.debug_port}{c('reset', pal)}")
        if s.urls:
            for url in s.urls[:5]:
                truncated = url if len(url) <= 120 else url[:117] + "..."
                print(f"    URL: {c('dim', pal)}{truncated}{c('reset', pal)}")
            if len(s.urls) > 5:
                print(f"    ... and {len(s.urls) - 5} more URLs")

        # Notable flags
        notable = []
        for flag in ("--headless", "--no-sandbox", "--incognito", "--private-window", "--temp-profile"):
            if flag in s.leader.flags:
                notable.append(flag)
        if notable:
            print(f"    Flags: {' '.join(notable)}")

        if verbose:
            print(f"    {c('dim', pal)}Cmdline: {s.leader.cmdline_str}{c('reset', pal)}")
            for ch in s.children[:10]:
                state_char = ch.state
                print(f"      └─ PID {ch.pid} [{ch.ptype}] state={state_char} "
                      f"rss={human_bytes(ch.rss)} cpu={ch.cpu_pct:.1f}%")
            if len(s.children) > 10:
                print(f"      └─ ... and {len(s.children) - 10} more child processes")

        print()


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

def send_signal_to_session(session, sig, pal, dry_run=False):
    """Send a signal to all processes in a session (children first, then leader)."""
    sig_name = signal.Signals(sig).name
    pids = list(reversed(session.all_pids))  # children first
    if dry_run:
        print(f"  {c('yellow', pal)}[DRY-RUN]{c('reset', pal)} Would send {sig_name} to "
              f"{len(pids)} processes (session leader PID {session.leader.pid}): "
              f"{', '.join(str(p) for p in pids[:8])}"
              f"{'...' if len(pids) > 8 else ''}")
        return
    success = 0
    for pid in pids:
        try:
            os.kill(pid, sig)
            success += 1
        except ProcessLookupError:
            pass
        except PermissionError:
            print(f"  {c('red', pal)}Permission denied for PID {pid}{c('reset', pal)}")
    print(f"  Sent {sig_name} to {success}/{len(pids)} processes "
          f"(session leader PID {session.leader.pid})")


def action_signal(sessions, indices, sig, pal, dry_run=False):
    for idx in sorted(indices):
        if 0 <= idx < len(sessions):
            send_signal_to_session(sessions[idx], sig, pal, dry_run=dry_run)
        else:
            print(f"  {c('red', pal)}Invalid index: {idx}{c('reset', pal)}")


def action_stop_all_except(sessions, except_indices, duration_seconds, pal, dry_run=False):
    """SIGSTOP all sessions except the listed ones, wait, then SIGCONT."""
    to_stop = []
    for i, s in enumerate(sessions):
        if i not in except_indices:
            to_stop.append((i, s))

    if not to_stop:
        print(f"  {c('yellow', pal)}Nothing to stop (all excluded).{c('reset', pal)}")
        return

    print(f"\n  {c('bold', pal)}{'[DRY-RUN] Would stop' if dry_run else 'Stopping'} "
          f"{len(to_stop)} session(s) for "
          f"{human_duration(duration_seconds)}...{c('reset', pal)}")
    print(f"  Keeping alive: {', '.join(str(i) for i in sorted(except_indices))}")

    for idx, s in to_stop:
        send_signal_to_session(s, signal.SIGSTOP, pal, dry_run=dry_run)

    if dry_run:
        print(f"\n  {c('yellow', pal)}[DRY-RUN]{c('reset', pal)} Would wait "
              f"{human_duration(duration_seconds)}, then SIGCONT all stopped sessions.")
        return

    print(f"\n  {c('yellow', pal)}Press Ctrl+C to resume early, or wait "
          f"{human_duration(duration_seconds)}.{c('reset', pal)}")

    try:
        time.sleep(duration_seconds)
    except KeyboardInterrupt:
        print(f"\n  {c('cyan', pal)}Interrupted - resuming now.{c('reset', pal)}")

    print(f"\n  {c('bold', pal)}Resuming stopped sessions...{c('reset', pal)}")
    for idx, s in to_stop:
        send_signal_to_session(s, signal.SIGCONT, pal)
    print(f"  {c('green', pal)}All resumed.{c('reset', pal)}")


HEADLESS_KEYWORDS = {"headless"}
HEADED_KEYWORDS = {"headed", "headfull", "headful"}

def parse_indices(spec, max_idx, sessions=None):
    """Parse '0,2,5-7', 'all', 'headless', 'headed'/'headfull' into a set of integers.

    Keywords can be mixed with indices: 'headless,3' or used standalone.
    'headless' selects sessions whose leader has --headless flag.
    'headed'/'headfull' selects sessions without --headless flag.
    """
    result = set()
    for part in spec.split(","):
        part = part.strip().lower()
        if part == "all":
            return set(range(max_idx + 1))
        elif part in HEADLESS_KEYWORDS and sessions:
            for i, s in enumerate(sessions):
                if "--headless" in s.leader.flags:
                    result.add(i)
        elif part in HEADED_KEYWORDS and sessions:
            for i, s in enumerate(sessions):
                if "--headless" not in s.leader.flags:
                    result.add(i)
        elif "-" in part and part[0] != "-":
            lo, hi = part.split("-", 1)
            for i in range(int(lo), int(hi) + 1):
                if 0 <= i <= max_idx:
                    result.add(i)
        elif part.isdigit():
            result.add(int(part))
    return result


def parse_duration(spec):
    """Parse '30m', '1h', '90s', '1h30m' into seconds."""
    total = 0
    for m in re.finditer(r"(\d+)\s*([smhd]?)", spec.lower()):
        val = int(m.group(1))
        unit = m.group(2) or "s"
        total += val * {"s": 1, "m": 60, "h": 3600, "d": 86400}[unit]
    return total if total > 0 else 300  # default 5 minutes


# ---------------------------------------------------------------------------
# Interactive mode
# ---------------------------------------------------------------------------

def interactive_loop(sessions, pal, verbose, dry_run=False):
    """Simple REPL for managing sessions."""
    print(f"{c('bold', pal)}Commands:{c('reset', pal)}")
    print(f"  {c('cyan', pal)}list/l{c('reset', pal)}              - refresh & list sessions")
    print(f"  {c('cyan', pal)}verbose/v{c('reset', pal)}           - toggle verbose display")
    print(f"  {c('cyan', pal)}term/t <targets>{c('reset', pal)}    - SIGTERM sessions  (e.g. t 0,2,5-7)")
    print(f"  {c('cyan', pal)}kill/k <targets>{c('reset', pal)}    - SIGKILL sessions")
    print(f"  {c('cyan', pal)}stop/s <targets>{c('reset', pal)}    - SIGSTOP (pause) sessions")
    print(f"  {c('cyan', pal)}cont/c <targets>{c('reset', pal)}    - SIGCONT (resume) sessions")
    print(f"  {c('cyan', pal)}freeze <dur> except=<targets>{c('reset', pal)}")
    print(f"                        - stop all except listed for duration")
    print(f"                          e.g.  freeze 30m except=0,2")
    print(f"  {c('cyan', pal)}sort <age|memory|cpu>{c('reset', pal)} - change sort order")
    print(f"  {c('cyan', pal)}dry/n{c('reset', pal)}               - toggle dry-run mode")
    print(f"  {c('cyan', pal)}quit/q{c('reset', pal)}              - exit")
    print(f"\n  {c('dim', pal)}Targets: indices (0,2,5-7), all, headless, headed/headfull{c('reset', pal)}")
    if dry_run:
        print(f"  {c('yellow', pal)}[DRY-RUN mode active]{c('reset', pal)}")
    print()

    sort_by = "age"

    while True:
        try:
            cmd = input(f"{c('bold', pal)}> {c('reset', pal)}").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not cmd:
            continue

        parts = cmd.split()
        action = parts[0].lower()

        if action in ("quit", "q", "exit"):
            break

        elif action in ("list", "l", "ls", "refresh"):
            procs = discover_processes()
            sessions = group_into_sessions(procs)
            print_sessions(sessions, pal, verbose=verbose, sort_by=sort_by)

        elif action in ("verbose", "v"):
            verbose = not verbose
            print(f"  Verbose: {'on' if verbose else 'off'}")
            print_sessions(sessions, pal, verbose=verbose, sort_by=sort_by)

        elif action in ("sort",):
            if len(parts) > 1 and parts[1] in ("age", "memory", "cpu"):
                sort_by = parts[1]
                print_sessions(sessions, pal, verbose=verbose, sort_by=sort_by)
            else:
                print("  Usage: sort <age|memory|cpu>")

        elif action in ("dry", "n", "dry-run", "dryrun"):
            dry_run = not dry_run
            state = f"{c('yellow', pal)}ON{c('reset', pal)}" if dry_run else f"{c('green', pal)}OFF{c('reset', pal)}"
            print(f"  Dry-run: {state}")

        elif action in ("term", "t"):
            if len(parts) < 2:
                print("  Usage: term <targets>  (e.g. t 0,2,5-7)")
                continue
            indices = parse_indices(parts[1], len(sessions) - 1, sessions)
            action_signal(sessions, indices, signal.SIGTERM, pal, dry_run=dry_run)

        elif action in ("kill", "k"):
            if len(parts) < 2:
                print("  Usage: kill <targets>")
                continue
            indices = parse_indices(parts[1], len(sessions) - 1, sessions)
            action_signal(sessions, indices, signal.SIGKILL, pal, dry_run=dry_run)

        elif action in ("stop", "s"):
            if len(parts) < 2:
                print("  Usage: stop <targets>")
                continue
            indices = parse_indices(parts[1], len(sessions) - 1, sessions)
            action_signal(sessions, indices, signal.SIGSTOP, pal, dry_run=dry_run)

        elif action in ("cont", "c", "resume"):
            if len(parts) < 2:
                print("  Usage: cont <targets>")
                continue
            indices = parse_indices(parts[1], len(sessions) - 1, sessions)
            action_signal(sessions, indices, signal.SIGCONT, pal, dry_run=dry_run)

        elif action == "freeze":
            # freeze 30m except=0,2
            duration_spec = "5m"
            except_spec = ""
            for p in parts[1:]:
                if p.startswith("except="):
                    except_spec = p.split("=", 1)[1]
                else:
                    duration_spec = p
            duration = parse_duration(duration_spec)
            except_indices = parse_indices(except_spec, len(sessions) - 1, sessions) if except_spec else set()
            action_stop_all_except(sessions, except_indices, duration, pal, dry_run=dry_run)
            # Refresh after freeze (only if not dry-run)
            if not dry_run:
                procs = discover_processes()
                sessions = group_into_sessions(procs)

        else:
            print(f"  Unknown command: {action}")

    return sessions


# ---------------------------------------------------------------------------
# CLI actions (non-interactive)
# ---------------------------------------------------------------------------

def cli_action(args, sessions, pal):
    """Handle non-interactive CLI actions."""
    dry_run = args.dry_run

    if args.action == "list":
        return  # already printed

    sig_map = {
        "term":  signal.SIGTERM,
        "kill":  signal.SIGKILL,
        "stop":  signal.SIGSTOP,
        "cont":  signal.SIGCONT,
    }

    if args.action in sig_map:
        if not args.targets:
            print(f"Error: --targets required for '{args.action}' action", file=sys.stderr)
            sys.exit(1)
        indices = parse_indices(args.targets, len(sessions) - 1, sessions)
        action_signal(sessions, indices, sig_map[args.action], pal, dry_run=dry_run)

    elif args.action == "freeze":
        duration = parse_duration(args.duration or "5m")
        except_indices = parse_indices(args.except_indices or "", len(sessions) - 1, sessions)
        action_stop_all_except(sessions, except_indices, duration, pal, dry_run=dry_run)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Manage stale browser instances (Chromium/Chrome/Brave/Firefox)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # interactive mode
  %(prog)s list                     # list sessions and exit
  %(prog)s list -v                  # verbose listing
  %(prog)s list --sort=memory       # sort by memory usage
  %(prog)s term --targets=0,2       # SIGTERM sessions 0 and 2
  %(prog)s kill --targets=3-5       # SIGKILL sessions 3,4,5
  %(prog)s stop --targets=1         # SIGSTOP (pause) session 1
  %(prog)s cont --targets=1         # SIGCONT (resume) session 1
  %(prog)s freeze --duration=30m --except=0,2
                                    # stop all except 0,2 for 30 min
  %(prog)s --no-color list          # disable colors
""",
    )
    parser.add_argument("action", nargs="?", default="interactive",
                        choices=["list", "term", "kill", "stop", "cont", "freeze", "interactive"],
                        help="Action to perform (default: interactive)")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Show detailed process info")
    parser.add_argument("--sort", default="age", choices=["age", "memory", "cpu"],
                        help="Sort sessions by (default: age)")
    parser.add_argument("--targets", "-t", default=None,
                        help="Session indices to act on (e.g. 0,2,5-7)")
    parser.add_argument("--duration", "-d", default="5m",
                        help="Duration for freeze action (e.g. 30m, 1h)")
    parser.add_argument("--except", dest="except_indices", default=None,
                        help="Session indices to exclude from freeze")
    parser.add_argument("--no-color", action="store_true",
                        help="Disable colored output")
    parser.add_argument("--dry-run", "-n", action="store_true",
                        help="Show what would be done without sending signals")

    args = parser.parse_args()

    pal = NO_COLORS if args.no_color or not sys.stdout.isatty() else COLORS

    procs = discover_processes()
    if not procs:
        print("No browser processes found.")
        sys.exit(0)

    sessions = group_into_sessions(procs)
    print_sessions(sessions, pal, verbose=args.verbose, sort_by=args.sort)

    if args.action == "interactive":
        interactive_loop(sessions, pal, args.verbose, dry_run=args.dry_run)
    else:
        cli_action(args, sessions, pal)


if __name__ == "__main__":
    main()
