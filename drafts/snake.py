import curses
import random
import time

# Color pair IDs
CP_TITLE    = 1
CP_SUBTITLE = 2
CP_SELECTED = 3
CP_NORMAL   = 4
CP_SNAKE    = 5
CP_FOOD     = 6
CP_BORDER   = 7
CP_SCORE    = 8

COLOR_OPTIONS  = ["Red", "Orange", "Yellow", "Pink"]
SETTINGS_ITEMS = COLOR_OPTIONS + ["← Back"]

HEAD_CHARS = {
    curses.KEY_RIGHT: "▶",
    curses.KEY_LEFT:  "◀",
    curses.KEY_UP:    "▲",
    curses.KEY_DOWN:  "▼",
}
OPPOSITE = {
    curses.KEY_UP:    curses.KEY_DOWN,
    curses.KEY_DOWN:  curses.KEY_UP,
    curses.KEY_LEFT:  curses.KEY_RIGHT,
    curses.KEY_RIGHT: curses.KEY_LEFT,
}


# ── helpers ───────────────────────────────────────────────────────────────────

def setup_colors(state):
    curses.start_color()
    curses.use_default_colors()
    has_256 = curses.COLORS >= 256
    state["color_map"] = {
        "Red":    curses.COLOR_RED,
        "Orange": 202 if has_256 else curses.COLOR_YELLOW,
        "Yellow": curses.COLOR_YELLOW,
        "Pink":   213 if has_256 else curses.COLOR_MAGENTA,
    }
    curses.init_pair(CP_TITLE,    curses.COLOR_GREEN,  -1)
    curses.init_pair(CP_SUBTITLE, curses.COLOR_CYAN,   -1)
    curses.init_pair(CP_SELECTED, curses.COLOR_BLACK,  curses.COLOR_WHITE)
    curses.init_pair(CP_NORMAL,   curses.COLOR_WHITE,  -1)
    curses.init_pair(CP_FOOD,     curses.COLOR_RED,    -1)
    curses.init_pair(CP_BORDER,   curses.COLOR_CYAN,   -1)
    curses.init_pair(CP_SCORE,    curses.COLOR_YELLOW, -1)
    _refresh_snake_color(state)


def _refresh_snake_color(state):
    curses.init_pair(CP_SNAKE, state["color_map"][state["snake_color"]], -1)


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
    """Returns 'play' | 'settings' | 'quit'."""
    stdscr.nodelay(False)
    selected = 0
    items = ["Play", "Settings", "Quit"]

    while True:
        stdscr.erase()
        h, _ = stdscr.getmaxyx()
        cy = h // 2

        cstr(stdscr, cy - 8, "╔═════════════════════════╗", CP_BORDER)
        cstr(stdscr, cy - 7, "║        S N A K E        ║", CP_BORDER)
        cstr(stdscr, cy - 6, "╚═════════════════════════╝", CP_BORDER)
        cstr(stdscr, cy - 4, "Welcome to the Snake Game",  CP_TITLE, bold=True)

        for i, name in enumerate(items):
            text = f"  {i + 1})  {name}  "
            pair = CP_SELECTED if i == selected else CP_NORMAL
            cstr(stdscr, cy - 1 + i * 2, text, pair, bold=(i == selected))

        cstr(stdscr, cy + 7, "Created by mochi peng",         CP_SUBTITLE)
        cstr(stdscr, cy + 9, "↑ ↓  navigate    enter  select", CP_NORMAL)

        stdscr.refresh()
        key = stdscr.getch()

        if key == curses.KEY_UP:
            selected = (selected - 1) % len(items)
        elif key == curses.KEY_DOWN:
            selected = (selected + 1) % len(items)
        elif key in (curses.KEY_ENTER, 10, 13):
            return items[selected].lower()
        elif key == ord("1"):
            return "play"
        elif key == ord("2"):
            return "settings"
        elif key == ord("3"):
            return "quit"


def show_settings(stdscr, state):
    """Color picker. Saves to state on confirm; Back discards."""
    stdscr.nodelay(False)
    selected = COLOR_OPTIONS.index(state["snake_color"])

    while True:
        stdscr.erase()
        h, _ = stdscr.getmaxyx()
        cy = h // 2

        cstr(stdscr, cy - 7, "╔═════════════════════════╗", CP_BORDER)
        cstr(stdscr, cy - 6, "║        Settings         ║", CP_BORDER)
        cstr(stdscr, cy - 5, "╚═════════════════════════╝", CP_BORDER)
        cstr(stdscr, cy - 3, "Snake Color", CP_TITLE, bold=True)

        for i, name in enumerate(SETTINGS_ITEMS):
            if name == "← Back":
                row = cy + 8          # extra gap before Back
                text = f"  {name}  "
            else:
                row = cy - 1 + i * 2  # Red=cy-1, Orange=cy+1, Yellow=cy+3, Pink=cy+5
                marker = "◉" if name == state["snake_color"] else "○"
                text = f"  {marker}  {name}  "
            pair = CP_SELECTED if i == selected else CP_NORMAL
            cstr(stdscr, row, text, pair, bold=(i == selected))

        cstr(stdscr, cy + 10, "↑ ↓  navigate    enter  select", CP_NORMAL)

        stdscr.refresh()
        key = stdscr.getch()

        if key == curses.KEY_UP:
            selected = (selected - 1) % len(SETTINGS_ITEMS)
        elif key == curses.KEY_DOWN:
            selected = (selected + 1) % len(SETTINGS_ITEMS)
        elif key in (curses.KEY_ENTER, 10, 13):
            choice = SETTINGS_ITEMS[selected]
            if choice != "← Back":
                state["snake_color"] = choice
                _refresh_snake_color(state)
            return


def run_game(stdscr, state):
    """Run the game. Returns final score."""
    _refresh_snake_color(state)
    stdscr.nodelay(True)
    h, w = stdscr.getmaxyx()

    top, left     = 1, 1
    bottom, right = h - 2, w - 2
    mid_y = (top + bottom) // 2
    mid_x = (left + right) // 2

    snake     = [(mid_y, mid_x - i) for i in range(3)]  # head first, moving right
    direction = curses.KEY_RIGHT
    score     = 0
    speed     = 0.12

    def place_food():
        while True:
            y = random.randint(top, bottom)
            x = random.randint(left, right)
            if (y, x) not in snake:
                return y, x

    food = place_food()

    while True:
        stdscr.erase()

        # Border
        try:
            stdscr.attron(curses.color_pair(CP_BORDER))
            stdscr.border()
            stdscr.attroff(curses.color_pair(CP_BORDER))
        except curses.error:
            pass

        # Score (top-right)
        score_text = f" Score: {score} "
        try:
            stdscr.addstr(0, w - len(score_text) - 2, score_text,
                          curses.color_pair(CP_SCORE) | curses.A_BOLD)
        except curses.error:
            pass

        # Food
        try:
            stdscr.addstr(food[0], food[1], "●",
                          curses.color_pair(CP_FOOD) | curses.A_BOLD)
        except curses.error:
            pass

        # Snake
        snake_attr = curses.color_pair(CP_SNAKE) | curses.A_BOLD
        for i, (y, x) in enumerate(snake):
            ch = HEAD_CHARS.get(direction, "▶") if i == 0 else "■"
            try:
                stdscr.addstr(y, x, ch, snake_attr)
            except curses.error:
                pass

        stdscr.refresh()
        time.sleep(speed)

        # Drain input; keep last key
        key = -1
        while True:
            k = stdscr.getch()
            if k == -1:
                break
            key = k

        if key == ord("q"):
            break
        if key in OPPOSITE and OPPOSITE[key] != direction:
            direction = key

        # Move head
        hy, hx = snake[0]
        if   direction == curses.KEY_UP:    hy -= 1
        elif direction == curses.KEY_DOWN:  hy += 1
        elif direction == curses.KEY_LEFT:  hx -= 1
        elif direction == curses.KEY_RIGHT: hx += 1

        # Collision checks
        if not (top <= hy <= bottom and left <= hx <= right):
            break
        if (hy, hx) in snake:
            break

        snake.insert(0, (hy, hx))
        if (hy, hx) == food:
            score += 10
            food   = place_food()
            speed  = max(0.05, speed - 0.003)
        else:
            snake.pop()

    stdscr.nodelay(False)
    return score


def show_game_over(stdscr, score):
    """Game over screen. Enter/R returns to menu."""
    stdscr.nodelay(False)

    while True:
        stdscr.erase()
        h, _ = stdscr.getmaxyx()
        cy = h // 2

        cstr(stdscr, cy - 5, "╔═════════════════════════╗", CP_BORDER)
        cstr(stdscr, cy - 4, "║       Game  Over        ║", CP_BORDER)
        cstr(stdscr, cy - 3, "╚═════════════════════════╝", CP_BORDER)
        cstr(stdscr, cy - 1, f"Final Score:  {score}",       CP_SCORE,    bold=True)
        cstr(stdscr, cy + 2, "  [ Return to Menu ]  ",       CP_SELECTED, bold=True)
        cstr(stdscr, cy + 5, "enter / r  to return",         CP_NORMAL)

        stdscr.refresh()
        key = stdscr.getch()
        if key in (curses.KEY_ENTER, 10, 13, ord("r"), ord("R")):
            return


# ── entry point ───────────────────────────────────────────────────────────────

def main(stdscr):
    curses.curs_set(0)
    state = {"snake_color": "Yellow", "color_map": {}}
    setup_colors(state)

    while True:
        choice = show_welcome(stdscr, state)
        if choice == "play":
            score = run_game(stdscr, state)
            show_game_over(stdscr, score)
        elif choice == "settings":
            show_settings(stdscr, state)
        elif choice == "quit":
            break


curses.wrapper(main)
