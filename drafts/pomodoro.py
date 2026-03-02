import curses
import time
import subprocess

# ── settings ──────────────────────────────────────────────────────────────────

WORK_MINS        = 25
SHORT_BREAK_MINS = 5
LONG_BREAK_MINS  = 15
LONG_AFTER       = 4   # pomodoros before a long break

# ── big digit glyphs (5 rows × 5 cols; colon is 3 cols) ──────────────────────

GLYPHS = {
    "0": ["█████", "█   █", "█   █", "█   █", "█████"],
    "1": ["  █  ", " ██  ", "  █  ", "  █  ", "█████"],
    "2": ["█████", "    █", "█████", "█    ", "█████"],
    "3": ["█████", "    █", "█████", "    █", "█████"],
    "4": ["█   █", "█   █", "█████", "    █", "    █"],
    "5": ["█████", "█    ", "█████", "    █", "█████"],
    "6": ["█████", "█    ", "█████", "█   █", "█████"],
    "7": ["█████", "    █", "    █", "    █", "    █"],
    "8": ["█████", "█   █", "█████", "█   █", "█████"],
    "9": ["█████", "█   █", "█████", "    █", "█████"],
    ":": [" ● ", "   ", " ● ", "   ", "   "],
}

# ── phases ────────────────────────────────────────────────────────────────────

PHASE_WORK  = "work"
PHASE_SHORT = "short"
PHASE_LONG  = "long"

PHASE_LABEL = {
    PHASE_WORK:  "Work Session",
    PHASE_SHORT: "Short Break",
    PHASE_LONG:  "Long Break ✦",
}
PHASE_SECS = {
    PHASE_WORK:  WORK_MINS * 60,
    PHASE_SHORT: SHORT_BREAK_MINS * 60,
    PHASE_LONG:  LONG_BREAK_MINS * 60,
}

# ── color pair IDs ────────────────────────────────────────────────────────────

CP_WORK   = 1   # red    — work
CP_SHORT  = 2   # green  — short break
CP_LONG   = 3   # cyan   — long break
CP_DIM    = 4   # dim    — hints / secondary
CP_TITLE  = 5   # yellow — title

PHASE_CP = {PHASE_WORK: CP_WORK, PHASE_SHORT: CP_SHORT, PHASE_LONG: CP_LONG}


# ── helpers ───────────────────────────────────────────────────────────────────

def setup_colors():
    curses.start_color()
    curses.use_default_colors()
    has_256 = curses.COLORS >= 256
    curses.init_pair(CP_WORK,  196 if has_256 else curses.COLOR_RED,   -1)
    curses.init_pair(CP_SHORT, 82  if has_256 else curses.COLOR_GREEN, -1)
    curses.init_pair(CP_LONG,  39  if has_256 else curses.COLOR_CYAN,  -1)
    curses.init_pair(CP_DIM,   242 if has_256 else curses.COLOR_WHITE, -1)
    curses.init_pair(CP_TITLE, curses.COLOR_YELLOW, -1)


def cstr(win, y, text, pair, bold=False):
    _, w = win.getmaxyx()
    x = max(0, (w - len(text)) // 2)
    attr = curses.color_pair(pair) | (curses.A_BOLD if bold else 0)
    try:
        win.addstr(y, x, text[: w - x - 1], attr)
    except curses.error:
        pass


def play_alert():
    try:
        subprocess.Popen(
            ["afplay", "/System/Library/Sounds/Glass.aiff"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        curses.beep()


# ── state machine ─────────────────────────────────────────────────────────────

def next_phase(state):
    if state["phase"] == PHASE_WORK:
        state["pomodoros_done"] += 1
        if state["pomodoros_done"] % LONG_AFTER == 0:
            state["phase"] = PHASE_LONG
        else:
            state["phase"] = PHASE_SHORT
    else:
        state["phase"] = PHASE_WORK
    state["seconds_left"] = PHASE_SECS[state["phase"]]
    state["paused"] = False


# ── drawing ───────────────────────────────────────────────────────────────────

def draw_digits(win, top_y, seconds, cp):
    _, w = win.getmaxyx()
    mm, ss = divmod(seconds, 60)
    chars  = f"{mm:02d}:{ss:02d}"
    glyphs = [GLYPHS[c] for c in chars]

    total_w = sum(len(g[0]) for g in glyphs) + len(glyphs) - 1
    x0 = max(0, (w - total_w) // 2)

    for row in range(5):
        x = x0
        for g in glyphs:
            line = g[row]
            try:
                win.addstr(top_y + row, x, line,
                           curses.color_pair(cp) | curses.A_BOLD)
            except curses.error:
                pass
            x += len(line) + 1


def draw_bar(win, y, ratio, cp, bar_w=44):
    _, w = win.getmaxyx()
    bar_w  = min(bar_w, w - 4)
    filled = int(bar_w * ratio)
    x      = max(0, (w - bar_w) // 2)
    try:
        win.addstr(y, x,          "█" * filled,          curses.color_pair(cp) | curses.A_BOLD)
        win.addstr(y, x + filled, "░" * (bar_w - filled), curses.color_pair(CP_DIM))
    except curses.error:
        pass


def draw_dots(win, y, done_in_cycle, total, cp):
    dots = "  ".join("●" if i < done_in_cycle else "○" for i in range(total))
    cstr(win, y, dots, cp, bold=True)


def draw(stdscr, state):
    stdscr.erase()
    h, w   = stdscr.getmaxyx()
    cy     = h // 2
    phase  = state["phase"]
    cp     = PHASE_CP[phase]
    total  = PHASE_SECS[phase]
    ratio  = (total - state["seconds_left"]) / total

    # Title
    cstr(stdscr, cy - 12, "P O M O D O R O", CP_TITLE, bold=True)

    # Phase label (+ PAUSED indicator)
    label = PHASE_LABEL[phase]
    if state["paused"]:
        label += "   ─  PAUSED"
    cstr(stdscr, cy - 10, label, cp, bold=True)

    # Cycle dots  ●●○○
    done_in_cycle = state["pomodoros_done"] % LONG_AFTER
    draw_dots(stdscr, cy - 8, done_in_cycle, LONG_AFTER, cp)

    # Big clock  (rows cy-6 … cy-2)
    draw_digits(stdscr, cy - 6, state["seconds_left"], cp)

    # Progress bar
    draw_bar(stdscr, cy, ratio, cp)

    # Percentage
    cstr(stdscr, cy + 2, f"{int(ratio * 100)}%", CP_DIM)

    # Total sessions
    sessions = state["pomodoros_done"]
    session_label = f"Session {'1' if sessions == 0 else str(sessions + 1)}  ·  {sessions} completed"
    cstr(stdscr, cy + 4, session_label, CP_DIM)

    # Controls
    cstr(stdscr, cy + 7, "space  pause / resume     s  skip     q  quit", CP_DIM)

    stdscr.refresh()


# ── main ──────────────────────────────────────────────────────────────────────

def main(stdscr):
    curses.curs_set(0)
    setup_colors()
    stdscr.nodelay(True)

    state = {
        "phase":          PHASE_WORK,
        "seconds_left":   PHASE_SECS[PHASE_WORK],
        "pomodoros_done": 0,
        "paused":         False,
    }

    last_tick = time.monotonic()

    while True:
        now = time.monotonic()

        if not state["paused"] and now - last_tick >= 1.0:
            last_tick = now
            state["seconds_left"] -= 1
            if state["seconds_left"] <= 0:
                play_alert()
                next_phase(state)

        draw(stdscr, state)

        key = stdscr.getch()
        if key in (ord("q"), ord("Q"), 27):
            break
        elif key == ord(" "):
            state["paused"] = not state["paused"]
            if not state["paused"]:
                last_tick = time.monotonic()   # avoid phantom tick on resume
        elif key in (ord("s"), ord("S")):
            play_alert()
            next_phase(state)

        time.sleep(0.05)


curses.wrapper(main)
