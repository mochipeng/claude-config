import curses
import time

# ── color pairs ───────────────────────────────────────────────────────────────

CP_TITLE  = 1
CP_POLE   = 2
CP_BASE   = 3
CP_DIM    = 4
CP_SELECT = 5
CP_WIN    = 6
CP_ERR    = 7
CP_DISK   = 10   # CP_DISK + (size - 1) per disk

DISK_COLORS_256   = [196, 208, 226, 82, 51, 129, 201]
POLE_ROWS         = 2    # empty pole rows above highest possible disk
MSG_SECS          = 1.5


def setup_colors():
    curses.start_color()
    curses.use_default_colors()
    has_256 = curses.COLORS >= 256
    curses.init_pair(CP_TITLE,  curses.COLOR_YELLOW, -1)
    curses.init_pair(CP_POLE,   curses.COLOR_WHITE,  -1)
    curses.init_pair(CP_BASE,   curses.COLOR_CYAN,   -1)
    curses.init_pair(CP_DIM,    242 if has_256 else curses.COLOR_WHITE, -1)
    curses.init_pair(CP_SELECT, curses.COLOR_BLACK,   curses.COLOR_WHITE)
    curses.init_pair(CP_WIN,    82  if has_256 else curses.COLOR_GREEN, -1)
    curses.init_pair(CP_ERR,    196 if has_256 else curses.COLOR_RED,   -1)
    basics = [curses.COLOR_RED, curses.COLOR_YELLOW, curses.COLOR_GREEN,
              curses.COLOR_CYAN, curses.COLOR_BLUE, curses.COLOR_MAGENTA,
              curses.COLOR_WHITE]
    for i in range(7):
        c = DISK_COLORS_256[i] if has_256 else basics[i]
        curses.init_pair(CP_DISK + i, c, -1)


def disk_cp(size):
    return CP_DISK + size - 1


# ── helpers ───────────────────────────────────────────────────────────────────

def cstr(win, y, text, pair, bold=False):
    _, w = win.getmaxyx()
    x = max(0, (w - len(text)) // 2)
    attr = curses.color_pair(pair) | (curses.A_BOLD if bold else 0)
    try:
        win.addstr(y, x, text[: w - x - 1], attr)
    except curses.error:
        pass


def put_disk(win, y, cx, size, attr):
    disk_w = 2 * size + 1
    x      = cx - size
    try:
        win.addstr(y, x, "━" * disk_w, attr)
    except curses.error:
        pass


# ── game state ────────────────────────────────────────────────────────────────

def new_state(n):
    return {
        "n":         n,
        "pegs":      [list(range(n, 0, -1)), [], []],  # index 0=bottom, -1=top
        "selected":  None,
        "moves":     0,
        "message":   "",
        "msg_until": 0.0,
        "won":       False,
    }


def err(state, msg):
    state["message"]   = msg
    state["msg_until"] = time.monotonic() + MSG_SECS


def try_move(state, dst):
    src = state["selected"]
    state["selected"] = None          # always deselect after a destination press

    if src == dst:
        return                        # same peg = cancel

    top = state["pegs"][src][-1] if state["pegs"][src] else None
    if top is None:
        err(state, "That peg is empty")
        return

    dst_top = state["pegs"][dst][-1] if state["pegs"][dst] else None
    if dst_top is not None and dst_top < top:
        err(state, "Can't place a larger disk on a smaller one")
        return

    state["pegs"][dst].append(state["pegs"][src].pop())
    state["moves"] += 1

    n = state["n"]
    if len(state["pegs"][1]) == n or len(state["pegs"][2]) == n:
        state["won"] = True


# ── drawing ───────────────────────────────────────────────────────────────────

def draw(stdscr, state):
    stdscr.erase()
    h, w = stdscr.getmaxyx()
    n    = state["n"]
    sel  = state["selected"]

    # Geometry
    zone_w     = 2 * n + 7           # space per peg column
    board_w    = zone_w * 3
    board_left = max(0, (w - board_w) // 2)
    peg_cx     = [board_left + i * zone_w + zone_w // 2 for i in range(3)]
    base_row   = h * 2 // 3
    peg_top    = base_row - n - POLE_ROWS   # top of pole (fixed height)
    hold_row   = peg_top - 2               # row where lifted disk floats

    # Title
    cstr(stdscr, max(0, hold_row - 3), "T O W E R  O F  H A N O I", CP_TITLE, bold=True)
    cstr(stdscr, max(0, hold_row - 2),
         f"Moves: {state['moves']}    Min: {(1 << n) - 1}    Disks: {n}",
         CP_DIM)

    for pi in range(3):
        cx    = peg_cx[pi]
        disks = state["pegs"][pi]
        is_sel = (pi == sel)

        # Pole (full fixed height, disks drawn on top)
        pole_attr = curses.color_pair(CP_SELECT) if is_sel else curses.color_pair(CP_POLE)
        for row in range(peg_top, base_row):
            try:
                stdscr.addstr(row, cx, "┃", pole_attr)
            except curses.error:
                pass

        # Disks — hide top when this peg is selected (it's being held)
        visible = disks[:-1] if (is_sel and disks) else disks
        for j, size in enumerate(visible):
            y    = base_row - 1 - j
            attr = curses.color_pair(disk_cp(size)) | curses.A_BOLD
            put_disk(stdscr, y, cx, size, attr)

        # Floating held disk
        if is_sel and disks:
            size = disks[-1]
            attr = curses.color_pair(disk_cp(size)) | curses.A_BOLD
            put_disk(stdscr, hold_row, cx, size, attr)

        # Label  [1] A
        label = f"[{pi + 1}] {'ABC'[pi]}"
        lx    = max(0, cx - len(label) // 2)
        la    = curses.color_pair(CP_SELECT) | curses.A_BOLD if is_sel else curses.color_pair(CP_DIM)
        try:
            stdscr.addstr(base_row + 1, lx, label, la)
        except curses.error:
            pass

    # Base line
    try:
        stdscr.addstr(base_row, board_left, "═" * board_w,
                      curses.color_pair(CP_BASE))
    except curses.error:
        pass

    # Status / message
    msg_y = base_row + 3
    if state["won"]:
        cstr(stdscr, msg_y,
             f"*** Solved in {state['moves']} moves! ***", CP_WIN, bold=True)
        cstr(stdscr, msg_y + 2, "r  new game    q  quit", CP_DIM)
    elif state["message"] and time.monotonic() < state["msg_until"]:
        cstr(stdscr, msg_y, state["message"], CP_ERR, bold=True)
    elif sel is not None:
        cstr(stdscr, msg_y,
             f"Moving from {'ABC'[sel]}  ->  press 1 / 2 / 3 to place  (same key to cancel)",
             CP_DIM)
    else:
        cstr(stdscr, msg_y,
             "1 / 2 / 3  or  A / B / C  to pick a peg     r  reset     q  quit",
             CP_DIM)

    stdscr.refresh()


# ── input ─────────────────────────────────────────────────────────────────────

PEG_KEYS = {
    ord("1"): 0, ord("a"): 0, ord("A"): 0,
    ord("2"): 1, ord("b"): 1, ord("B"): 1,
    ord("3"): 2, ord("c"): 2, ord("C"): 2,
}


def handle_key(key, state):
    if state["won"]:
        return "reset" if key in (ord("r"), ord("R")) else None

    if key in PEG_KEYS:
        pi = PEG_KEYS[key]
        if state["selected"] is None:
            if state["pegs"][pi]:
                state["selected"] = pi
            else:
                err(state, "That peg is empty")
        else:
            try_move(state, pi)

    elif key in (ord("r"), ord("R")):
        return "reset"

    return None


# ── disk picker ───────────────────────────────────────────────────────────────

def choose_n(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(False)
    options  = [3, 4, 5, 6, 7]
    selected = 1   # default: 4 disks

    while True:
        stdscr.erase()
        h, _ = stdscr.getmaxyx()
        cy   = h // 2

        cstr(stdscr, cy - 7, "╔═════════════════════════╗", CP_BASE)
        cstr(stdscr, cy - 6, "║    Tower  of  Hanoi     ║", CP_BASE)
        cstr(stdscr, cy - 5, "╚═════════════════════════╝", CP_BASE)
        cstr(stdscr, cy - 3, "How many disks?", CP_TITLE, bold=True)

        for i, n in enumerate(options):
            text = f"  {n} disks  (min {(1 << n) - 1} moves)  "
            pair = CP_SELECT if i == selected else CP_DIM
            cstr(stdscr, cy - 1 + i * 2, text, pair, bold=(i == selected))

        cstr(stdscr, cy + 11, "arrow keys  navigate    enter  start", CP_DIM)
        stdscr.refresh()

        key = stdscr.getch()
        if key == curses.KEY_UP:
            selected = (selected - 1) % len(options)
        elif key == curses.KEY_DOWN:
            selected = (selected + 1) % len(options)
        elif key in (curses.KEY_ENTER, 10, 13):
            return options[selected]
        elif key in (ord("q"), ord("Q"), 27):
            return None


# ── entry point ───────────────────────────────────────────────────────────────

def main(stdscr):
    setup_colors()

    n = choose_n(stdscr)
    if n is None:
        return

    stdscr.nodelay(True)
    state = new_state(n)

    while True:
        draw(stdscr, state)
        key = stdscr.getch()

        if key in (ord("q"), ord("Q"), 27):
            break

        action = handle_key(key, state)
        if action == "reset":
            state = new_state(state["n"])

        time.sleep(0.05)


curses.wrapper(main)
