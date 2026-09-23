"""
Sorting Algorithms Race — Bubble Sort vs. Insertion Sort vs. Quicksort.

WHAT THIS SHOWS
----------------
The exact same shuffled array of values is handed to three different
sorting algorithms at once, each running in its own glowing column:

  LEFT    Bubble Sort     — repeatedly walks the array, swapping any
                            adjacent pair that's out of order.
  MIDDLE  Insertion Sort  — builds up a sorted prefix one element at a
                            time, sliding each new value backward into
                            its correct spot.
  RIGHT   Quicksort       — picks a pivot, partitions everything smaller
                            to its left and everything larger to its
                            right, then recurses on each half.

All three make "one decision" (a comparison, and sometimes a swap) at
the same fixed rate, so the race isn't about clock speed — it's about
how many decisions each algorithm actually needs. Bubble Sort and
Insertion Sort both need on the order of n^2 comparisons in the worst
case; Quicksort needs on the order of n*log(n) on average. Watching
Quicksort's column finish while the other two are still grinding away
*is* the lesson: same hardware, same data, wildly different algorithmic
complexity.

Bars are colored along a neon gradient by their value (deep blue -> cyan
-> magenta -> gold), so a fully sorted column reads as a smooth rainbow
ramp. Every comparison flashes the two bars being examined; every swap
fires a small particle burst and leaves a brief motion trail as the bars
glide (not snap) to their new positions.

CONTROLS
--------
  ESC / close window  -> quit
  R                    -> reshuffle all three columns and restart now
  SPACE                -> pause / resume

Runs standalone: `python sorting_algorithms_race.py` (requires pygame).
"""

import math
import random
import sys

import pygame

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
WIDTH, HEIGHT = 1320, 760
FPS = 60

NUM_BARS = 24            # elements per column (all three race the same values)
OPS_PER_SECOND = 30.0    # comparisons/swaps processed per second, per column
SWAP_EASE_RATE = 9.0     # how fast a bar's visual position chases its slot

BG_COLOR = (7, 8, 16)
PANEL_DIVIDER = (40, 46, 70)
TEXT_COLOR = (185, 205, 225)
TEXT_DIM = (95, 110, 135)
COMPARE_FLASH = (255, 255, 255)
FINISH_GLOW = (140, 255, 170)

PAUSE_ON_COMPLETE = 3.0   # seconds to admire a fully-sorted board before reshuffling

# Column identity colors (used for titles / HUD accents).
COL_COLORS = [
    (0, 230, 255),    # cyan   — Bubble Sort
    (255, 90, 210),   # pink   — Insertion Sort
    (255, 210, 60),   # gold   — Quicksort
]

# Value -> neon color gradient stops (t in [0, 1], color).
VALUE_GRADIENT = [
    (0.00, (40, 90, 255)),
    (0.30, (0, 230, 220)),
    (0.55, (255, 60, 200)),
    (0.80, (255, 140, 30)),
    (1.00, (255, 230, 80)),
]


# ----------------------------------------------------------------------
# Small helpers: easing, color mixing, glow primitives
# ----------------------------------------------------------------------
def lerp(a, b, t):
    return a + (b - a) * t


def lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(lerp(c1[i], c2[i], t)) for i in range(3))


def value_to_color(t):
    """Piecewise-linear gradient lookup for t in [0, 1]."""
    t = max(0.0, min(1.0, t))
    for i in range(len(VALUE_GRADIENT) - 1):
        t0, c0 = VALUE_GRADIENT[i]
        t1, c1 = VALUE_GRADIENT[i + 1]
        if t0 <= t <= t1:
            local_t = 0.0 if t1 == t0 else (t - t0) / (t1 - t0)
            return lerp_color(c0, c1, local_t)
    return VALUE_GRADIENT[-1][1]


def glow_rect(surface, rect, color, layers=3, alpha_scale=1.0):
    """Draw a soft additive-blend glow around a rectangle, then a solid core."""
    x, y, w, h = rect
    pad = 3 + layers * 3
    gw, gh = int(w + pad * 2), int(h + pad * 2)
    if gw <= 0 or gh <= 0:
        return
    for i in range(layers, 0, -1):
        expand = i * 3
        alpha = max(3, int((50 / i) * alpha_scale))
        glow_surf = pygame.Surface((gw, gh), pygame.SRCALPHA)
        pygame.draw.rect(
            glow_surf, (*color, alpha),
            (pad - expand, pad - expand, w + expand * 2, h + expand * 2),
            border_radius=3,
        )
        surface.blit(glow_surf, (x - pad, y - pad), special_flags=pygame.BLEND_RGBA_ADD)
    pygame.draw.rect(surface, color, (x, y, max(1, int(w)), max(1, int(h))), border_radius=2)


def glow_circle(surface, pos, radius, color, layers=3, alpha_scale=1.0):
    for i in range(layers, 0, -1):
        r = int(radius + i * 2.5)
        if r <= 0:
            continue
        alpha = max(3, int((60 / i) * alpha_scale))
        glow_surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*color, alpha), (r, r), r)
        surface.blit(glow_surf, (pos[0] - r, pos[1] - r), special_flags=pygame.BLEND_RGBA_ADD)


def ease_toward(current, target, rate, dt):
    """Exponential ease — current chases target, never overshoots."""
    t = 1.0 - math.exp(-rate * dt)
    return current + (target - current) * t


# ----------------------------------------------------------------------
# Sorting algorithms, expressed as generators that yield one decision at
# a time. Each generator mutates `bars` (a list of dicts) directly, so
# list order == current logical order. Yields are:
#   ('compare', i, j)  -> bars[i] and bars[j] were compared, no change
#   ('swap', i, j)      -> bars[i] and bars[j] were just swapped in place
#   ('done',)           -> fully sorted
# ----------------------------------------------------------------------
def bubble_sort_steps(bars):
    n = len(bars)
    for end in range(n - 1, 0, -1):
        swapped = False
        for j in range(end):
            yield ("compare", j, j + 1)
            if bars[j]["value"] > bars[j + 1]["value"]:
                bars[j], bars[j + 1] = bars[j + 1], bars[j]
                yield ("swap", j, j + 1)
                swapped = True
        if not swapped:
            break
    yield ("done",)


def insertion_sort_steps(bars):
    n = len(bars)
    for i in range(1, n):
        j = i
        while j > 0:
            yield ("compare", j - 1, j)
            if bars[j - 1]["value"] > bars[j]["value"]:
                bars[j - 1], bars[j] = bars[j], bars[j - 1]
                yield ("swap", j - 1, j)
                j -= 1
            else:
                break
    yield ("done",)


def quicksort_steps(bars):
    def _sort(lo, hi):
        if lo >= hi:
            return
        pivot = bars[hi]["value"]
        i = lo - 1
        for j in range(lo, hi):
            yield ("compare", j, hi)
            if bars[j]["value"] <= pivot:
                i += 1
                if i != j:
                    bars[i], bars[j] = bars[j], bars[i]
                    yield ("swap", i, j)
        if i + 1 != hi:
            bars[i + 1], bars[hi] = bars[hi], bars[i + 1]
            yield ("swap", i + 1, hi)
        yield from _sort(lo, i)
        yield from _sort(i + 2, hi)

    yield from _sort(0, len(bars) - 1)
    yield ("done",)


ALGORITHMS = [
    ("Bubble Sort", bubble_sort_steps),
    ("Insertion Sort", insertion_sort_steps),
    ("Quicksort", quicksort_steps),
]


# ----------------------------------------------------------------------
# One racing column: owns its own copy of the values, its own generator,
# its own stats, and a small particle system for swap sparks.
# ----------------------------------------------------------------------
class Column:
    def __init__(self, name, algo_fn, accent, values):
        self.name = name
        self.algo_fn = algo_fn
        self.accent = accent
        self.reset(values)

    def reset(self, values):
        self.bars = [{"value": v, "visual_x": i} for i, v in enumerate(values)]
        self.gen = self.algo_fn(self.bars)
        self.op_accum = 0.0
        self.comparisons = 0
        self.swaps = 0
        self.elapsed = 0.0
        self.finished = False
        self.finish_time = None
        self.compare_flash = None   # (i, j, timer)
        self.particles = []

    def _spawn_particles(self, x, y, color):
        for _ in range(9):
            ang = random.uniform(0, math.tau)
            speed = random.uniform(40, 160)
            self.particles.append({
                "x": x, "y": y,
                "vx": math.cos(ang) * speed,
                "vy": math.sin(ang) * speed - 40,
                "life": random.uniform(0.25, 0.55),
                "max_life": 0.55,
                "color": color,
            })

    def update(self, dt, geom, paused):
        if paused:
            return

        if not self.finished:
            self.elapsed += dt

        # Ease every bar's visual x-position toward its current logical slot.
        for idx, bar in enumerate(self.bars):
            bar["visual_x"] = ease_toward(bar["visual_x"], idx, SWAP_EASE_RATE, dt)

        # Advance the compare-flash timer.
        if self.compare_flash is not None:
            i, j, t = self.compare_flash
            t -= dt
            self.compare_flash = (i, j, t) if t > 0 else None

        # Update particles.
        alive = []
        for p in self.particles:
            p["life"] -= dt
            if p["life"] > 0:
                p["x"] += p["vx"] * dt
                p["y"] += p["vy"] * dt
                p["vy"] += 260 * dt  # gentle gravity on the sparks
                alive.append(p)
        self.particles = alive

        if self.finished:
            return

        # Process discrete algorithm steps at a fixed rate, independent of
        # the (smooth, 60fps) visual easing above.
        self.op_accum += dt * OPS_PER_SECOND
        while self.op_accum >= 1.0 and not self.finished:
            self.op_accum -= 1.0
            try:
                event = next(self.gen)
            except StopIteration:
                self.finished = True
                self.finish_time = self.elapsed
                break

            kind = event[0]
            if kind == "compare":
                _, i, j = event
                self.comparisons += 1
                self.compare_flash = (i, j, 0.16)
            elif kind == "swap":
                _, i, j = event
                self.swaps += 1
                xi = geom["bar_x"](i) + geom["bar_w"] / 2
                xj = geom["bar_x"](j) + geom["bar_w"] / 2
                y = geom["baseline"] - 10
                self._spawn_particles(xi, y, self.accent)
                self._spawn_particles(xj, y, self.accent)
            elif kind == "done":
                self.finished = True
                self.finish_time = self.elapsed


# ----------------------------------------------------------------------
# Layout: three equal-width panels side by side.
# ----------------------------------------------------------------------
PANEL_MARGIN = 18
TOP_MARGIN = 118
BOTTOM_MARGIN = 30
PANEL_GAP = 14


def panel_rect(col_index):
    total_w = WIDTH - PANEL_MARGIN * 2 - PANEL_GAP * 2
    pw = total_w / 3
    x = PANEL_MARGIN + col_index * (pw + PANEL_GAP)
    y = TOP_MARGIN
    h = HEIGHT - TOP_MARGIN - BOTTOM_MARGIN
    return x, y, pw, h


def make_geometry(col_index, max_value):
    x, y, w, h = panel_rect(col_index)
    inner_pad = 10
    usable_w = w - inner_pad * 2
    bar_w = usable_w / NUM_BARS
    baseline = y + h - 4

    def bar_x(i):
        return x + inner_pad + i * bar_w

    def bar_height(value):
        return (value / max_value) * (h - 40)

    return {
        "rect": (x, y, w, h),
        "bar_x": bar_x,
        "bar_w": bar_w,
        "baseline": baseline,
        "bar_height": bar_height,
    }


# ----------------------------------------------------------------------
# Drawing
# ----------------------------------------------------------------------
def draw_column(surface, col, geom, font_hud, font_title):
    x, y, w, h = geom["rect"]

    # Panel divider / frame (subtle, not the visual centerpiece).
    pygame.draw.rect(surface, PANEL_DIVIDER, (x, y, w, h), width=1, border_radius=6)

    # Bars, back to front, colored by value.
    for idx, bar in enumerate(col.bars):
        t = bar["value"] / NUM_BARS
        color = value_to_color(t)
        bh = geom["bar_height"](bar["value"])
        bx = geom["bar_x"](bar["visual_x"])
        by = geom["baseline"] - bh
        glow_rect(surface, (bx + 1, by, geom["bar_w"] - 2, bh), color, layers=2, alpha_scale=0.8)

    # Comparison flash — bright halo over the two bars currently being compared.
    if col.compare_flash is not None:
        i, j, t = col.compare_flash
        strength = max(0.0, t / 0.16)
        for idx in (i, j):
            if 0 <= idx < len(col.bars):
                bar = col.bars[idx]
                bh = geom["bar_height"](bar["value"])
                bx = geom["bar_x"](bar["visual_x"])
                by = geom["baseline"] - bh
                glow_rect(surface, (bx + 1, by, geom["bar_w"] - 2, bh),
                          COMPARE_FLASH, layers=3, alpha_scale=strength)

    # Swap sparks.
    for p in col.particles:
        fade = max(0.0, p["life"] / p["max_life"])
        glow_circle(surface, (p["x"], p["y"]), 2 + 3 * fade, p["color"], layers=2, alpha_scale=fade)

    # Completion pulse across the whole column once sorted.
    if col.finished:
        pulse = 0.5 + 0.5 * math.sin(col.elapsed * 4.0)
        pygame.draw.rect(surface, FINISH_GLOW, (x, y, w, h), width=2, border_radius=6)
        label = font_title.render("SORTED", True, FINISH_GLOW)
        alpha_surf = label.copy()
        alpha_surf.set_alpha(int(140 + 100 * pulse))
        surface.blit(alpha_surf, (x + w / 2 - label.get_width() / 2, y + 8))

    # Per-column title + compact HUD (kept small and at the top of the
    # panel — a supporting element, not the centerpiece).
    title_surf = font_title.render(col.name, True, col.accent)
    surface.blit(title_surf, (x + 10, y - 34))

    if col.finished:
        stats = [
            f"comparisons: {col.comparisons}",
            f"swaps: {col.swaps}",
            f"done in {col.finish_time:4.1f}s",
        ]
    else:
        stats = [
            f"comparisons: {col.comparisons}",
            f"swaps: {col.swaps}",
            f"time: {col.elapsed:4.1f}s",
        ]
    for i, line in enumerate(stats):
        surf = font_hud.render(line, True, TEXT_DIM if not col.finished else TEXT_COLOR)
        surface.blit(surf, (x + 10, y + 10 + i * 17))


def make_shared_values():
    values = list(range(1, NUM_BARS + 1))
    random.shuffle(values)
    return values


def main():
    pygame.init()
    pygame.display.set_caption("Sorting Algorithms Race — Bubble vs. Insertion vs. Quicksort")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()

    font_title = pygame.font.SysFont("consolas", 20, bold=True)
    font_hud = pygame.font.SysFont("consolas", 15)
    font_big = pygame.font.SysFont("consolas", 26, bold=True)
    font_sub = pygame.font.SysFont("consolas", 15)

    shared_values = make_shared_values()
    columns = [
        Column(name, fn, COL_COLORS[i], shared_values)
        for i, (name, fn) in enumerate(ALGORITHMS)
    ]
    geoms = [make_geometry(i, NUM_BARS) for i in range(3)]

    paused = False
    all_done_timer = 0.0
    running = True

    while running:
        dt = clock.tick(FPS) / 1000.0
        dt = min(dt, 0.05)  # guard against huge dt spikes (e.g. window drag)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_r:
                    shared_values = make_shared_values()
                    for col in columns:
                        col.reset(shared_values)
                    all_done_timer = 0.0
                elif event.key == pygame.K_SPACE:
                    paused = not paused

        for col, geom in zip(columns, geoms):
            col.update(dt, geom, paused)

        if all(c.finished for c in columns):
            all_done_timer += dt
            if all_done_timer >= PAUSE_ON_COMPLETE:
                shared_values = make_shared_values()
                for col in columns:
                    col.reset(shared_values)
                all_done_timer = 0.0
        else:
            all_done_timer = 0.0

        # --- draw ---
        screen.fill(BG_COLOR)

        title_surf = font_big.render("SORTING ALGORITHMS RACE", True, (230, 240, 255))
        screen.blit(title_surf, (PANEL_MARGIN, 24))
        sub_surf = font_sub.render(
            "same shuffled array, same decision rate — wildly different amounts of work",
            True, TEXT_DIM,
        )
        screen.blit(sub_surf, (PANEL_MARGIN, 56))
        if paused:
            pause_surf = font_sub.render("PAUSED (space to resume)", True, (255, 210, 60))
            screen.blit(pause_surf, (WIDTH - pause_surf.get_width() - PANEL_MARGIN, 30))

        for col, geom in zip(columns, geoms):
            draw_column(screen, col, geom, font_hud, font_title)

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
