"""
0/1 Knapsack — Dynamic Programming, Visualized
================================================

WHAT THIS SHOWS
The classic 0/1 knapsack problem: given a set of items, each with a weight
and a value, pick a subset that fits inside a knapsack of fixed capacity
while maximizing total value. You either take an item whole or leave it
(no splitting) — hence "0/1".

The brute-force way to solve this is to try every subset (2^n possibilities).
Dynamic programming instead builds a table dp[i][w] = "the best value
achievable using only the first i items, with a knapsack capacity of w".
Each cell is computed from cells already solved:

    dp[i][w] = dp[i-1][w]                                  if item i doesn't fit in w
    dp[i][w] = max( dp[i-1][w],                             skip item i
                     dp[i-1][w - weight[i]] + value[i] )    take item i

Once the whole table is filled, dp[n][W] holds the optimal value, and
walking BACKWARDS through the table (comparing dp[i][w] to dp[i-1][w])
reconstructs which items were actually chosen.

This script animates that table filling in, cell by cell, then animates
the backtrace that recovers the answer.

CONTROLS
    ESC / close window  - quit
    SPACE                - pause / resume
    R                    - reshuffle items and restart immediately

Runs standalone: `python knapsack_dp.py` (requires only pygame).
"""

import sys
import math
import random
import pygame

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
WIDTH, HEIGHT = 1280, 800
BG_COLOR = (8, 9, 20)               # near-black navy backdrop
FPS = 60

N_ITEMS = 9                          # number of candidate items
CAPACITY = 28                        # knapsack capacity (grid width)

FRAMES_PER_CELL = 3                  # how fast the DP fill sweeps (lower = faster)
BACKTRACE_FRAMES_PER_STEP = 14       # slower, more dramatic backtrace
HOLD_FRAMES = 150                    # pause on the finished result before restart

CELL_W = 34
CELL_H = 34
GRID_LEFT = 380
GRID_TOP = 150

# Neon palette used throughout. Each item gets a distinct hue so the same
# color identifies it in the item list, the grid glow, and the backtrace.
NEON_HUES = [
    (0, 255, 220),    # cyan
    (255, 0, 200),    # magenta
    (255, 230, 0),    # yellow
    (80, 255, 80),    # green
    (255, 120, 0),    # orange
    (140, 100, 255),  # violet
    (0, 180, 255),    # electric blue
    (255, 60, 100),   # hot pink-red
    (170, 255, 0),    # lime
    (0, 255, 150),    # spring green
]

FONT_NAME = "consolas"


def lerp(a, b, t):
    return a + (b - a) * t


def ease_in_out(t):
    """Smoothstep easing so the cursor glides rather than snaps."""
    return t * t * (3 - 2 * t)


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def blend_color(c1, c2, t):
    return tuple(int(lerp(c1[i], c2[i], t)) for i in range(3))


class Item:
    """A single candidate item: a weight, a value, and a display color."""

    def __init__(self, idx, weight, value):
        self.idx = idx
        self.weight = weight
        self.value = value
        self.color = NEON_HUES[idx % len(NEON_HUES)]
        self.taken = False          # set True once the backtrace selects it
        self.flash_timer = 0.0      # brief glow pulse when selected


def make_items(n):
    items = []
    for i in range(n):
        w = random.randint(2, 9)
        v = random.randint(4, 30)
        items.append(Item(i, w, v))
    return items


class KnapsackDemo:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("0/1 Knapsack — Dynamic Programming")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()

        self.font_small = pygame.font.SysFont(FONT_NAME, 15)
        self.font_med = pygame.font.SysFont(FONT_NAME, 19, bold=True)
        self.font_big = pygame.font.SysFont(FONT_NAME, 26, bold=True)

        # Persistent glow layer we additively blend each frame, then fade,
        # so filled cells leave a soft afterglow instead of a hard cut.
        self.glow_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

        self.reset()

    # ------------------------------------------------------------------
    def reset(self):
        self.items = make_items(N_ITEMS)
        n, cap = N_ITEMS, CAPACITY

        # dp[i][w]: best value using first i items with capacity w
        self.dp = [[0] * (cap + 1) for _ in range(n + 1)]
        # choice[i][w]: True if item i-1 was taken to reach dp[i][w]
        self.choice = [[False] * (cap + 1) for _ in range(n + 1)]

        # Fill order visits every (i, w) cell in row-major order (i=1..n, w=0..cap)
        self.fill_order = [(i, w) for i in range(1, n + 1) for w in range(cap + 1)]
        self.fill_pos = 0
        self.frame_in_cell = 0

        self.phase = "filling"         # "filling" -> "backtrace" -> "done"
        self.prev_cursor_cell = (0, 0)
        self.cur_cursor_cell = (0, 0)

        # backtrace state
        self.bt_i = n
        self.bt_w = cap
        self.bt_frame = 0
        self.bt_path = []              # list of (i, w) visited, for drawing the trail
        self.hold_timer = 0

        self.total_capacity_used = 0
        self.total_value_taken = 0

        self.glow_surface.fill((0, 0, 0, 0))

        self.paused = False

    # ------------------------------------------------------------------
    def step_fill(self):
        """Advance the DP fill by one cell (called at FRAMES_PER_CELL cadence)."""
        i, w = self.fill_order[self.fill_pos]
        item = self.items[i - 1]

        skip_val = self.dp[i - 1][w]
        if item.weight <= w:
            take_val = self.dp[i - 1][w - item.weight] + item.value
            if take_val > skip_val:
                self.dp[i][w] = take_val
                self.choice[i][w] = True
            else:
                self.dp[i][w] = skip_val
        else:
            self.dp[i][w] = skip_val

        # Stamp a glow blob onto the persistent glow layer, brightness
        # scaled by how much value this cell represents relative to the
        # best possible total (sum of all item values) — this is the
        # "map intensity to color" requirement: bigger partial answers glow hotter.
        max_possible = sum(it.value for it in self.items)
        frac = clamp(self.dp[i][w] / max_possible, 0, 1) if max_possible else 0
        cell_color = blend_color((20, 30, 70), (255, 60, 220), frac)
        hot_color = blend_color(cell_color, (255, 255, 255), frac * 0.35)

        cx = GRID_LEFT + w * CELL_W + CELL_W // 2
        cy = GRID_TOP + i * CELL_H + CELL_H // 2
        radius = int(CELL_W * 0.62)
        glow = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*hot_color, 150), (radius, radius), radius)
        self.glow_surface.blit(glow, (cx - radius, cy - radius), special_flags=pygame.BLEND_RGBA_ADD)

        self.prev_cursor_cell = self.cur_cursor_cell
        self.cur_cursor_cell = (i, w)

        self.fill_pos += 1
        if self.fill_pos >= len(self.fill_order):
            self.phase = "backtrace"
            self.bt_i = N_ITEMS
            self.bt_w = CAPACITY

    # ------------------------------------------------------------------
    def step_backtrace(self):
        """Advance the backtrace by one item-row (called at BACKTRACE cadence)."""
        if self.bt_i == 0:
            self.phase = "done"
            self.hold_timer = 0
            return

        i, w = self.bt_i, self.bt_w
        took = self.choice[i][w]
        self.bt_path.append((i, w))

        if took:
            item = self.items[i - 1]
            item.taken = True
            item.flash_timer = 1.0
            self.total_value_taken += item.value
            self.total_capacity_used += item.weight
            self.bt_w -= item.weight

        self.bt_i -= 1

    # ------------------------------------------------------------------
    def update(self):
        if self.paused:
            return

        # gently fade the persistent glow layer so old cells dim but never
        # vanish completely -- gives the whole grid a "still warm" look.
        fade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        fade.fill((0, 0, 0, 2))
        self.glow_surface.blit(fade, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)

        for item in self.items:
            if item.flash_timer > 0:
                item.flash_timer = max(0.0, item.flash_timer - 0.02)

        if self.phase == "filling":
            self.frame_in_cell += 1
            if self.frame_in_cell >= FRAMES_PER_CELL:
                self.frame_in_cell = 0
                self.step_fill()

        elif self.phase == "backtrace":
            self.frame_in_cell += 1
            if self.frame_in_cell >= BACKTRACE_FRAMES_PER_STEP:
                self.frame_in_cell = 0
                self.step_backtrace()

        elif self.phase == "done":
            self.hold_timer += 1
            if self.hold_timer > HOLD_FRAMES:
                self.reset()

    # ------------------------------------------------------------------
    def cursor_screen_pos(self):
        """Smoothly interpolated pixel position of the active-cell cursor."""
        t = clamp(self.frame_in_cell / max(1, FRAMES_PER_CELL), 0, 1)
        t = ease_in_out(t)
        pi, pw = self.prev_cursor_cell
        ci, cw = self.cur_cursor_cell
        i = lerp(pi, ci, t)
        w = lerp(pw, cw, t)
        x = GRID_LEFT + w * CELL_W + CELL_W / 2
        y = GRID_TOP + i * CELL_H + CELL_H / 2
        return x, y

    # ------------------------------------------------------------------
    def draw_grid(self):
        # faint gridlines so the table structure reads even where nothing
        # has glowed yet
        grid_color = (30, 34, 56)
        for w in range(CAPACITY + 2):
            x = GRID_LEFT + w * CELL_W
            pygame.draw.line(self.screen, grid_color, (x, GRID_TOP), (x, GRID_TOP + (N_ITEMS + 1) * CELL_H))
        for i in range(N_ITEMS + 2):
            y = GRID_TOP + i * CELL_H
            pygame.draw.line(self.screen, grid_color, (GRID_LEFT, y), (GRID_LEFT + (CAPACITY + 1) * CELL_W, y))

        # persistent glow (the actual DP values, as heat)
        self.screen.blit(self.glow_surface, (0, 0))

        # axis labels
        cap_label = self.font_small.render("capacity (w) -->", True, (120, 130, 170))
        self.screen.blit(cap_label, (GRID_LEFT, GRID_TOP - 26))
        item_label = self.font_small.render("items (i)", True, (120, 130, 170))
        rotated = pygame.transform.rotate(item_label, 90)
        self.screen.blit(rotated, (GRID_LEFT - 40, GRID_TOP + 10))

    def draw_cursor(self):
        if self.phase not in ("filling",):
            return
        x, y = self.cursor_screen_pos()
        pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.02)
        radius = int(CELL_W * 0.55 + pulse * 4)
        glow = pygame.Surface((radius * 4, radius * 4), pygame.SRCALPHA)
        pygame.draw.circle(glow, (0, 255, 220, 90), (radius * 2, radius * 2), radius * 2)
        pygame.draw.circle(glow, (255, 255, 255, 200), (radius * 2, radius * 2), max(2, radius // 3), 2)
        self.screen.blit(glow, (x - radius * 2, y - radius * 2), special_flags=pygame.BLEND_RGBA_ADD)

    def draw_backtrace(self):
        if not self.bt_path:
            return
        pts = []
        for (i, w) in self.bt_path:
            x = GRID_LEFT + w * CELL_W + CELL_W / 2
            y = GRID_TOP + i * CELL_H + CELL_H / 2
            pts.append((x, y))
        if len(pts) >= 2:
            trail = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            pygame.draw.lines(trail, (255, 230, 60, 220), False, pts, 4)
            self.screen.blit(trail, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        for (x, y) in pts:
            pygame.draw.circle(self.screen, (255, 245, 180), (int(x), int(y)), 5)

    def draw_item_panel(self):
        """Left-side panel: each item as a glowing weight/value bar."""
        x0 = 30
        y = 110
        title = self.font_med.render("ITEMS (weight / value)", True, (200, 210, 240))
        self.screen.blit(title, (x0, 74))

        max_val = max(it.value for it in self.items)
        for item in self.items:
            row_y = y + item.idx * 34
            glow_boost = item.flash_timer
            color = blend_color(item.color, (255, 255, 255), glow_boost * 0.6)

            # bar length maps to value -> visual intensity encodes magnitude
            bar_w = int(20 + (item.value / max_val) * 220)
            bar_rect = pygame.Rect(x0 + 90, row_y, bar_w, 18)

            if item.taken:
                glow = pygame.Surface((bar_w + 30, 40), pygame.SRCALPHA)
                pygame.draw.rect(glow, (*color, 120), (0, 0, bar_w + 30, 40), border_radius=10)
                self.screen.blit(glow, (x0 + 90 - 15, row_y - 11), special_flags=pygame.BLEND_RGBA_ADD)

            pygame.draw.rect(self.screen, color, bar_rect, border_radius=6)
            if item.taken:
                pygame.draw.rect(self.screen, (255, 255, 255), bar_rect, 2, border_radius=6)

            label = self.font_small.render(
                f"#{item.idx}  w{item.weight:>2} v{item.value:>2}", True, (210, 215, 235)
            )
            self.screen.blit(label, (x0, row_y + 1))

            if item.taken:
                tag = self.font_small.render("TAKEN", True, (255, 255, 255))
                self.screen.blit(tag, (x0 + 100 + bar_w, row_y + 1))

    def draw_hud(self):
        """Small stats readout, tucked in a corner -- supporting detail,
        not the visual centerpiece."""
        lines = [
            f"phase: {self.phase}",
            f"cells filled: {min(self.fill_pos, len(self.fill_order))}/{len(self.fill_order)}",
            f"capacity: {CAPACITY}   used: {self.total_capacity_used}",
            f"optimal value: {self.dp[N_ITEMS][CAPACITY]}" if self.phase != "filling"
            else f"current cell value: {self.dp[self.cur_cursor_cell[0]][self.cur_cursor_cell[1]]}",
        ]
        panel = pygame.Surface((300, 92), pygame.SRCALPHA)
        pygame.draw.rect(panel, (10, 12, 28, 190), (0, 0, 300, 92), border_radius=10)
        pygame.draw.rect(panel, (0, 255, 220, 90), (0, 0, 300, 92), 1, border_radius=10)
        for idx, line in enumerate(lines):
            txt = self.font_small.render(line, True, (150, 240, 230))
            panel.blit(txt, (12, 10 + idx * 19))
        self.screen.blit(panel, (WIDTH - 320, 20))

    def draw_title(self):
        title = self.font_big.render("0/1 Knapsack — Dynamic Programming", True, (240, 245, 255))
        self.screen.blit(title, (30, 24))
        sub = self.font_small.render(
            "dp[i][w] = max(skip item i, take item i)      "
            "grid heat = best value found so far", True, (130, 140, 175)
        )
        self.screen.blit(sub, (30, 56))

        if self.phase == "done":
            msg = self.font_med.render(
                f"OPTIMAL VALUE = {self.dp[N_ITEMS][CAPACITY]}   "
                f"(using {self.total_capacity_used}/{CAPACITY} capacity) -- restarting...",
                True, (255, 230, 90)
            )
            self.screen.blit(msg, (GRID_LEFT, GRID_TOP + (N_ITEMS + 2) * CELL_H))

    # ------------------------------------------------------------------
    def draw(self):
        self.screen.fill(BG_COLOR)
        self.draw_title()
        self.draw_item_panel()
        self.draw_grid()
        self.draw_backtrace()
        self.draw_cursor()
        self.draw_hud()
        pygame.display.flip()

    # ------------------------------------------------------------------
    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_SPACE:
                        self.paused = not self.paused
                    elif event.key == pygame.K_r:
                        self.reset()

            self.update()
            self.draw()
            self.clock.tick(FPS)

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    KnapsackDemo().run()
