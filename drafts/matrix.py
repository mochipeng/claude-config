import curses
import random
import time

# Half-width katakana + digits — gives that authentic Matrix feel
CHARS = (
    "ｦｧｨｩｪｫｬｭｮｯｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿ"
    "ﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜﾝ"
    "0123456789"
)

COLOR_NAMES    = ["Green", "Blue", "Red", "Cyan", "Purple"]
SETTINGS_ITEMS = COLOR_NAMES + ["← Back"]

# 256-color gradients per scheme: (bright, mid, dim)
SCHEMES_256 = {
    "Green":  (82,  40,  22),
    "Blue":   (33,  27,  18),
    "Red":    (196, 160, 88),
    "Cyan":   (51,  37,  23),
    "Purple": (129, 93,  54),
}

# Color pair IDs — rain
CP_HEAD   = 1
CP_BRIGHT = 2
CP_MID    = 3
CP_DIM    = 4
# Color pair IDs — UI
CP_TITLE    = 5
CP_BORDER   = 6
CP_SELECTED = 7
CP_NORMAL   = 8


# ── helpers ───────────────────────────────────────────────────────────────────

def setup_colors(state):
    curses.start_color()
    curses.use_default_colors()
    state["has_256"] = curses.COLORS >= 256

    # Map color names to a basic fallback for terminals without 256 colors
    state["basic_colors"] = {
        "Green":  curses.COLOR_GREEN,
        "Blue":   curses.COLOR_BLUE,
        "Red":    curses.COLOR_RED,
        "Cyan":   curses.COLOR_CYAN,
        "Purple": curses.COLOR_MAGENTA,
    }

    curses.init_pair(CP_TITLE,    curses.COLOR_GREEN, -1)
    curses.init_pair(CP_BORDER,   curses.COLOR_CYAN,  -1)
    curses.init_pair(CP_SELECTED, curses.COLOR_BLACK,  curses.COLOR_WHITE)
    curses.init_pair(CP_NORMAL,   curses.COLOR_WHITE,  -1)

    _refresh_rain_color(state)


def _refresh_rain_color(state):
    curses.init_pair(CP_HEAD, curses.COLOR_WHITE, -1)
    if state["has_256"]:
        bright, mid, dim = SCHEMES_256[state["color"]]
    else:
        c = state["basic_colors"][state["color"]]
        bright = mid = dim = c
    curses.init_pair(CP_BRIGHT, bright, -1)
    curses.init_pair(CP_MID,    mid,    -1)
    curses.init_pair(CP_DIM,    dim,    -1)


def attr_for(depth):
    if depth == 0:
        return curses.color_pair(CP_HEAD) | curses.A_BOLD
    if depth <= 2:
        return curses.color_pair(CP_BRIGHT) | curses.A_BOLD
    if depth <= 7:
        return curses.color_pair(CP_MID)
    return curses.color_pair(CP_DIM)


def cstr(win, y, text, pair, bold=False):
    """Draw text centered on row y, clipped to window width."""
    _, w = win.getmaxyx()
    x = max(0, (w - len(text)) // 2)
    attr = curses.color_pair(pair) | (curses.A_BOLD if bold else 0)
    try:
        win.addstr(y, x, text[: w - x - 1], attr)
    except curses.error:
        pass


# ── screens ───────────────────────────────────────────────────────────────────

def show_welcome(stdscr, state):
    """Returns 'start' | 'color' | 'quit'."""
    stdscr.nodelay(False)
    selected = 0
    items = ["Start", "Color", "Quit"]

    while True:
        stdscr.erase()
        h, _ = stdscr.getmaxyx()
        cy = h // 2

        cstr(stdscr, cy - 8, "╔═════════════════════════╗", CP_BORDER)
        cstr(stdscr, cy - 7, "║    M A T R I X  R A I N ║", CP_BORDER)
        cstr(stdscr, cy - 6, "╚═════════════════════════╝", CP_BORDER)
        cstr(stdscr, cy - 4, "Enter the Matrix",            CP_TITLE, bold=True)

        for i, name in enumerate(items):
            text = f"  {i + 1})  {name}  "
            pair = CP_SELECTED if i == selected else CP_NORMAL
            cstr(stdscr, cy - 1 + i * 2, text, pair, bold=(i == selected))

        cstr(stdscr, cy + 7, "↑ ↓  navigate    enter  select", CP_NORMAL)

        stdscr.refresh()
        key = stdscr.getch()

        if key == curses.KEY_UP:
            selected = (selected - 1) % len(items)
        elif key == curses.KEY_DOWN:
            selected = (selected + 1) % len(items)
        elif key in (curses.KEY_ENTER, 10, 13):
            return items[selected].lower()
        elif key == ord("1"):
            return "start"
        elif key == ord("2"):
            return "color"
        elif key == ord("3"):
            return "quit"


def show_color(stdscr, state):
    """Color picker. Saves to state on confirm; Back discards."""
    stdscr.nodelay(False)
    selected = COLOR_NAMES.index(state["color"])

    while True:
        stdscr.erase()
        h, _ = stdscr.getmaxyx()
        cy = h // 2

        cstr(stdscr, cy - 7, "╔═════════════════════════╗", CP_BORDER)
        cstr(stdscr, cy - 6, "║         Color           ║", CP_BORDER)
        cstr(stdscr, cy - 5, "╚═════════════════════════╝", CP_BORDER)
        cstr(stdscr, cy - 3, "Rain Color", CP_TITLE, bold=True)

        for i, name in enumerate(SETTINGS_ITEMS):
            if name == "← Back":
                row  = cy + 9
                text = f"  {name}  "
            else:
                row    = cy - 1 + i * 2
                marker = "◉" if name == state["color"] else "○"
                text   = f"  {marker}  {name}  "
            pair = CP_SELECTED if i == selected else CP_NORMAL
            cstr(stdscr, row, text, pair, bold=(i == selected))

        cstr(stdscr, cy + 11, "↑ ↓  navigate    enter  select", CP_NORMAL)

        stdscr.refresh()
        key = stdscr.getch()

        if key == curses.KEY_UP:
            selected = (selected - 1) % len(SETTINGS_ITEMS)
        elif key == curses.KEY_DOWN:
            selected = (selected + 1) % len(SETTINGS_ITEMS)
        elif key in (curses.KEY_ENTER, 10, 13):
            choice = SETTINGS_ITEMS[selected]
            if choice != "← Back":
                state["color"] = choice
                _refresh_rain_color(state)
            return


# ── matrix rain ───────────────────────────────────────────────────────────────

def new_stream(x, h):
    length = random.randint(8, h // 2)
    return {
        "x":      x,
        "y":      random.randint(-length, 0),
        "length": length,
        "speed":  random.randint(1, 4),
        "tick":   random.randint(0, 4),
        "chars":  [random.choice(CHARS) for _ in range(length + 2)],
    }


def run_matrix(stdscr, state):
    _refresh_rain_color(state)
    stdscr.nodelay(True)

    h, w = stdscr.getmaxyx()
    streams = [new_stream(x, h) for x in range(w)]

    while True:
        h, w = stdscr.getmaxyx()
        stdscr.erase()

        for idx, s in enumerate(streams):
            s["tick"] += 1
            if s["tick"] >= s["speed"]:
                s["tick"] = 0
                s["y"] += 1
                s["chars"][random.randrange(len(s["chars"]))] = random.choice(CHARS)
                if s["y"] - s["length"] > h:
                    streams[idx] = new_stream(s["x"], h)
                    continue

            x = s["x"]
            if x >= w:
                continue

            for depth in range(s["length"]):
                y = s["y"] - depth
                if 0 <= y < h - 1:
                    try:
                        stdscr.addstr(y, x, s["chars"][depth], attr_for(depth))
                    except curses.error:
                        pass

        hint = " q  menu "
        try:
            stdscr.addstr(h - 1, w - len(hint) - 1, hint, curses.color_pair(CP_DIM))
        except curses.error:
            pass

        stdscr.refresh()

        key = stdscr.getch()
        if key in (ord("q"), ord("Q"), 27):
            break

        time.sleep(0.04)


# ── entry point ───────────────────────────────────────────────────────────────

def main(stdscr):
    curses.curs_set(0)
    state = {"color": "Green"}
    setup_colors(state)

    while True:
        choice = show_welcome(stdscr, state)
        if choice == "start":
            run_matrix(stdscr, state)
        elif choice == "color":
            show_color(stdscr, state)
        elif choice == "quit":
            break


curses.wrapper(main)
