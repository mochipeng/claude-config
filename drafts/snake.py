import curses
import random
import time

def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.keypad(True)

    h, w = stdscr.getmaxyx()

    # Game area (leave 1-cell border)
    max_y, max_x = h - 1, w - 1

    snake = [(max_y // 2, max_x // 4 + i) for i in range(3)]  # head first
    direction = curses.KEY_RIGHT
    score = 0
    speed = 0.12

    def place_food():
        while True:
            y = random.randint(1, max_y - 1)
            x = random.randint(1, max_x - 1)
            if (y, x) not in snake:
                return (y, x)

    food = place_food()

    while True:
        stdscr.erase()

        # Border
        stdscr.border()

        # Score
        stdscr.addstr(0, 2, f" Score: {score} ")

        # Food
        stdscr.addch(food[0], food[1], "●")

        # Snake
        for i, (y, x) in enumerate(snake):
            stdscr.addch(y, x, "█" if i == 0 else "▪")

        stdscr.refresh()

        time.sleep(speed)

        # Input (non-blocking, take last key pressed)
        key = -1
        while True:
            k = stdscr.getch()
            if k == -1:
                break
            key = k

        opposites = {
            curses.KEY_UP: curses.KEY_DOWN,
            curses.KEY_DOWN: curses.KEY_UP,
            curses.KEY_LEFT: curses.KEY_RIGHT,
            curses.KEY_RIGHT: curses.KEY_LEFT,
        }
        if key in opposites and opposites[key] != direction:
            direction = key
        elif key == ord("q"):
            break

        # Move
        head_y, head_x = snake[0]
        if direction == curses.KEY_UP:
            head_y -= 1
        elif direction == curses.KEY_DOWN:
            head_y += 1
        elif direction == curses.KEY_LEFT:
            head_x -= 1
        elif direction == curses.KEY_RIGHT:
            head_x += 1

        # Wall collision
        if head_y <= 0 or head_y >= max_y or head_x <= 0 or head_x >= max_x:
            break

        # Self collision
        if (head_y, head_x) in snake:
            break

        snake.insert(0, (head_y, head_x))

        if (head_y, head_x) == food:
            score += 10
            food = place_food()
            speed = max(0.05, speed - 0.003)  # speed up gradually
        else:
            snake.pop()

    # Game over screen
    msg = f"Game Over! Score: {score}  (press any key)"
    stdscr.addstr(max_y // 2, max(0, (max_x - len(msg)) // 2), msg)
    stdscr.refresh()
    stdscr.nodelay(False)
    stdscr.getch()


curses.wrapper(main)
