import curses
import random
import time
from collections import deque

CHARSET = list("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz@#$%&*+=?<>\uFF66\uFF67\uFF68\uFF69\uFF6A\uFF76\uFF77\uFF78\uFF79\uFF7A\uFF7B\uFF7C\uFF7D")
MESSAGES = [
    "THE MATRIX HAS YOU",
    "FOLLOW THE WHITE RABBIT",
    "WAKE UP, NEO",
    "GLITCH IN THE CODE"
]
MESSAGE_ROTATE_SECONDS = 12
PAYLOAD_TRIGGER = "payload"


class Column:
    def __init__(self, x, height):
        self.x = x
        self.speed = random.uniform(8.5, 20.0)
        self.buffer = random.random()
        self.cells = []
        self.max_length = 6
        self.spawn_density = random.uniform(0.7, 1.0)
        self.reseed(height)

    def reseed(self, height):
        if height <= 1:
            self.max_length = 1
        else:
            lower = max(6, (height // 2) + 3)
            upper = max(lower, height)
            self.max_length = random.randint(lower, upper)
        self.spawn_density = random.uniform(0.7, 1.0)
        self.cells.clear()
        if height <= 0:
            return
        initial_length = random.randint(0, min(self.max_length, height - 1 if height > 0 else 0))
        start_y = random.randint(0, max(0, height - 1)) if height > 1 else 0
        for i in range(initial_length):
            y = start_y + i
            if y >= height:
                break
            self.cells.append((y, self.random_char()))
        self.cells.sort(key=lambda c: c[0])

    def random_char(self):
        return random.choice(CHARSET)

    def mutate(self):
        for idx in range(1, len(self.cells)):
            if random.random() < 0.15:
                y, _ = self.cells[idx]
                self.cells[idx] = (y, self.random_char())

    def update(self, dt, height):
        if height <= 0:
            self.cells.clear()
            return
        self.buffer += self.speed * dt
        steps = int(self.buffer)
        if steps <= 0:
            return
        self.buffer -= steps
        for _ in range(steps):
            moved = []
            for y, ch in self.cells:
                new_y = y + 1
                if new_y < height:
                    moved.append((new_y, ch))
            self.cells = moved
            if random.random() <= self.spawn_density or not self.cells:
                self.cells.insert(0, (0, self.random_char()))
            if len(self.cells) > self.max_length:
                self.cells = self.cells[: self.max_length]
        self.mutate()

    def draw(self, stdscr, scheme, message_char, message_row):
        total = len(self.cells)
        for idx, (y, ch) in enumerate(self.cells):
            draw_char = ch
            attr = scheme["tail_dim"]
            if idx == 0:
                attr = scheme["head"]
            elif idx < min(4, total):
                attr = scheme["tail_bright"]
            if message_char and y == message_row:
                draw_char = message_char
                attr = scheme["message"]
            try:
                stdscr.addstr(y, self.x, draw_char, attr)
            except curses.error:
                pass


def build_color_schemes():
    if curses.has_colors():
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_GREEN, -1)
        curses.init_pair(2, curses.COLOR_GREEN, -1)
        curses.init_pair(3, curses.COLOR_WHITE, -1)
        curses.init_pair(4, curses.COLOR_RED, -1)
        curses.init_pair(5, curses.COLOR_RED, -1)
        curses.init_pair(6, curses.COLOR_YELLOW, -1)
        normal = {
            "head": curses.color_pair(1) | curses.A_BOLD,
            "tail_bright": curses.color_pair(1),
            "tail_dim": curses.color_pair(2) | curses.A_DIM,
            "message": curses.color_pair(3) | curses.A_BOLD,
        }
        alert = {
            "head": curses.color_pair(4) | curses.A_BOLD,
            "tail_bright": curses.color_pair(4),
            "tail_dim": curses.color_pair(5) | curses.A_DIM,
            "message": curses.color_pair(6) | curses.A_BOLD,
        }
    else:
        normal = {
            "head": curses.A_BOLD,
            "tail_bright": curses.A_NORMAL,
            "tail_dim": curses.A_DIM,
            "message": curses.A_BOLD,
        }
        alert = normal
    return normal, alert


def compute_message_map(width, message):
    if width <= 0:
        return {}
    trimmed = message[:width]
    start_x = max(0, (width - len(trimmed)) // 2)
    mapping = {}
    for idx, ch in enumerate(trimmed):
        x = start_x + idx
        mapping[x] = ch if ch != " " else None
    return mapping


def main(stdscr):
    try:
        curses.curs_set(0)
    except curses.error:
        pass
    stdscr.nodelay(True)
    stdscr.keypad(True)
    normal_scheme, alert_scheme = build_color_schemes()

    height, width = stdscr.getmaxyx()
    columns = [Column(x, height) for x in range(max(1, width))]
    message_index = 0
    current_message = MESSAGES[message_index]
    message_map = compute_message_map(width, current_message)
    message_row = height // 2 if height > 0 else 0
    last_switch = time.time()
    red_alert = False
    typed = deque(maxlen=len(PAYLOAD_TRIGGER))
    last_time = time.time()

    while True:
        now = time.time()
        dt = now - last_time
        last_time = now

        new_height, new_width = stdscr.getmaxyx()
        if new_height != height or new_width != width:
            height, width = new_height, new_width
            columns = [Column(x, height) for x in range(max(1, width))]
            message_map = compute_message_map(width, current_message)
            message_row = height // 2 if height > 0 else 0

        if now - last_switch > MESSAGE_ROTATE_SECONDS:
            message_index = (message_index + 1) % len(MESSAGES)
            current_message = MESSAGES[message_index]
            message_map = compute_message_map(width, current_message)
            last_switch = now

        scheme = alert_scheme if red_alert else normal_scheme

        for col in columns:
            col.update(dt, height)

        stdscr.erase()
        for col in columns:
            message_char = message_map.get(col.x)
            col.draw(stdscr, scheme, message_char, message_row)

        stdscr.refresh()

        try:
            key = stdscr.getch()
        except curses.error:
            key = -1

        if key == -1:
            time.sleep(0.02)
            continue

        if key == curses.KEY_RESIZE:
            height, width = stdscr.getmaxyx()
            columns = [Column(x, height) for x in range(max(1, width))]
            message_map = compute_message_map(width, current_message)
            message_row = height // 2 if height > 0 else 0
            continue

        if key in (ord('q'), ord('Q')):
            break
        if key in (ord('m'), ord('M')):
            message_index = (message_index + 1) % len(MESSAGES)
            current_message = MESSAGES[message_index]
            message_map = compute_message_map(width, current_message)
            last_switch = now
            continue

        if 0 <= key < 256:
            ch = chr(key)
            typed.append(ch.lower())
            if ''.join(typed).endswith(PAYLOAD_TRIGGER):
                red_alert = not red_alert
                typed.clear()
        time.sleep(0.02)


if __name__ == "__main__":
    curses.wrapper(main)
