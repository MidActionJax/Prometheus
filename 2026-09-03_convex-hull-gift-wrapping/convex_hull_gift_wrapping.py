"""
Convex Hull — Gift Wrapping (Jarvis March), animated as a radar sweep.

WHAT THIS SHOWS
----------------
Given a cloud of scattered points, the convex hull is the smallest convex
polygon that contains every point — imagine stretching a rubber band around
all the dots and letting it snap tight. The Gift Wrapping algorithm (a.k.a.
Jarvis March) builds that polygon one edge at a time:

  1. Start at the guaranteed-hull point furthest to the left.
  2. From the current hull point, sweep a beam across every remaining point
     and keep whichever one is the most "clockwise" relative to all others
     (formally: the point for which every other point lies to its left).
  3. That winner becomes the next hull vertex. Move there and repeat.
  4. Stop when the sweep wraps back around to the starting point.

This script animates step 2 explicitly: a rotating beam scans the point
cloud in angular order, dimly pinging each candidate it rejects and glowing
brighter on the current best guess, before committing the winning edge to
the glowing hull polygon.

CONTROLS
--------
  ESC / close window  -> quit
  R                    -> reshuffle the point cloud immediately

Runs standalone: `python convex_hull_gift_wrapping.py` (requires pygame).
"""

import math
import random
import sys

import pygame

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
WIDTH, HEIGHT = 1280, 720
FPS = 60

NUM_POINTS = 34
POINT_MARGIN = 90  # keep points off the very edge of the canvas

BG_COLOR = (8, 9, 18)
FADE_ALPHA = 40  # how quickly the beam/ray trails fade each frame (0-255)

DIM_POINT = (70, 90, 130)
LIVE_POINT = (0, 230, 255)      # cyan — points not yet absorbed into the hull
HULL_POINT = (255, 225, 60)     # gold — confirmed hull vertices
BEAM_COLOR = (0, 255, 210)      # bright teal — the sweeping search beam
REJECT_COLOR = (140, 40, 200)   # dim magenta/purple — rejected candidates
BEST_COLOR = (255, 60, 160)     # hot pink — current best candidate this sweep
EDGE_COLOR_A = (255, 225, 60)   # hull edge gradient start (gold)
EDGE_COLOR_B = (0, 230, 255)    # hull edge gradient end (cyan)
TEXT_COLOR = (170, 210, 230)
TEXT_DIM = (90, 110, 130)

SECONDS_PER_SWEEP = 1.6   # time to test every candidate for one hull vertex
EDGE_DRAW_SECONDS = 0.35  # time to animate a committed hull edge growing in
PAUSE_ON_COMPLETE = 2.2   # seconds to admire the finished hull before reset


# ----------------------------------------------------------------------
# Small geometry helpers
# ----------------------------------------------------------------------
def cross(o, a, b):
    """Cross product of (a-o) x (b-o). Sign tells us which side b is on."""
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def lerp(a, b, t):
    return a + (b - a) * t


def ease_in_out(t):
    """Smoothstep easing so motion accelerates then decelerates."""
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(lerp(c1[i], c2[i], t)) for i in range(3))


def make_points(n):
    pts = []
    for _ in range(n):
        x = random.uniform(POINT_MARGIN, WIDTH - POINT_MARGIN)
        y = random.uniform(POINT_MARGIN + 40, HEIGHT - POINT_MARGIN)
        pts.append((x, y))
    return pts


# ----------------------------------------------------------------------
# Glow-drawing helpers (additive-blended soft circles/lines give the
# neon look instead of flat pygame primitives)
# ----------------------------------------------------------------------
def glow_circle(surface, pos, radius, color, layers=4, core=True):
    for i in range(layers, 0, -1):
        r = int(radius + i * 3)
        alpha = max(4, int(55 / i))
        glow_surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*color, alpha), (r, r), r)
        surface.blit(glow_surf, (pos[0] - r, pos[1] - r), special_flags=pygame.BLEND_RGBA_ADD)
    if core:
        pygame.draw.circle(surface, color, (int(pos[0]), int(pos[1])), max(2, radius // 2))


def glow_line(surface, start, end, color, width=2, layers=3, alpha_scale=1.0):
    # Allocate a surface sized to the line's own bounding box (plus glow
    # padding) rather than the full canvas — this is the difference between
    # a few thousand pixels and ~1M pixels per call, which matters a lot
    # once dozens of glow lines are drawn per frame at 60fps.
    pad = width + layers * 4
    min_x = int(min(start[0], end[0])) - pad
    max_x = int(max(start[0], end[0])) + pad
    min_y = int(min(start[1], end[1])) - pad
    max_y = int(max(start[1], end[1])) + pad
    w, h = max_x - min_x, max_y - min_y
    if w <= 0 or h <= 0:
        return
    for i in range(layers, 0, -1):
        lw = width + i * 3
        alpha = max(3, int((45 / i) * alpha_scale))
        line_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.line(line_surf, (*color, alpha),
                          (start[0] - min_x, start[1] - min_y),
                          (end[0] - min_x, end[1] - min_y), lw)
        surface.blit(line_surf, (min_x, min_y), special_flags=pygame.BLEND_RGBA_ADD)
    pygame.draw.line(surface, color, start, end, width)


# ----------------------------------------------------------------------
# The demo itself, as a small state machine so the algorithm can be
# animated step-by-step rather than solved instantly.
# ----------------------------------------------------------------------
class HullDemo:
    PHASE_SWEEP = "sweep"       # rotating beam testing candidates
    PHASE_COMMIT = "commit"     # animating the winning edge growing in
    PHASE_DONE = "done"         # hull complete, pausing before reset

    def __init__(self):
        self.stats_comparisons = 0
        self.stats_edges = 0
        self.stats_resets = 0
        self.elapsed = 0.0
        self.reset()

    def reset(self):
        self.points = make_points(NUM_POINTS)
        start = min(self.points, key=lambda p: (p[0], p[1]))
        self.hull = [start]
        self.current = start
        self.beam_angle = 0.0
        self.stats_resets += 1
        self._begin_sweep()

    def _begin_sweep(self):
        """Set up a new angular sweep from self.current to find the next
        hull vertex."""
        candidates = [p for p in self.points if p != self.current]
        # Order candidates by angle around 'current' so the beam sweeps
        # smoothly in one direction instead of jumping randomly.
        candidates.sort(key=lambda p: math.atan2(p[1] - self.current[1], p[0] - self.current[0]))
        self.test_order = candidates
        self.test_index = 0
        self.best = candidates[0] if candidates else None
        self.tested_so_far = []
        self.phase = self.PHASE_SWEEP
        self.phase_t = 0.0
        if candidates:
            self.beam_angle = math.atan2(candidates[0][1] - self.current[1],
                                          candidates[0][0] - self.current[0])

    def _target_angle_for(self, p):
        return math.atan2(p[1] - self.current[1], p[0] - self.current[0])

    def update(self, dt):
        self.elapsed += dt

        if self.phase == self.PHASE_SWEEP:
            self.phase_t += dt / SECONDS_PER_SWEEP
            target_i = int(ease_in_out(min(self.phase_t, 1.0)) * len(self.test_order))
            target_i = min(target_i, len(self.test_order))

            # Process any newly-reached candidates in the sweep order.
            while self.test_index < target_i:
                p = self.test_order[self.test_index]
                self.stats_comparisons += 1
                c = cross(self.current, self.best, p)
                if c < 0 or (c == 0 and dist(self.current, p) > dist(self.current, self.best)):
                    self.best = p
                self.tested_so_far.append(p)
                self.test_index += 1

            # Smoothly rotate the beam toward whatever we're testing next.
            look_idx = min(self.test_index, len(self.test_order) - 1)
            if self.test_order:
                target_angle = self._target_angle_for(self.test_order[look_idx])
                diff = (target_angle - self.beam_angle + math.pi) % (2 * math.pi) - math.pi
                self.beam_angle += diff * min(1.0, dt * 10)

            if self.phase_t >= 1.0:
                self.phase = self.PHASE_COMMIT
                self.phase_t = 0.0

        elif self.phase == self.PHASE_COMMIT:
            self.phase_t += dt / EDGE_DRAW_SECONDS
            if self.phase_t >= 1.0:
                self.phase_t = 1.0
                # Commit the edge for real.
                self.stats_edges += 1
                closed = self.best == self.hull[0]
                self.current = self.best
                if not closed:
                    self.hull.append(self.current)
                if closed or len(self.hull) > NUM_POINTS:
                    self.phase = self.PHASE_DONE
                    self.phase_t = 0.0
                else:
                    self._begin_sweep()

        elif self.phase == self.PHASE_DONE:
            self.phase_t += dt
            if self.phase_t >= PAUSE_ON_COMPLETE:
                self.reset()

    # ------------------------------------------------------------------
    def draw(self, surface, fade_surface):
        # Fade the previous frame's transient beam/ray trails toward black
        # instead of a hard clear, so the sweep leaves soft light trails.
        fade_surface.fill((*BG_COLOR, FADE_ALPHA))
        surface.blit(fade_surface, (0, 0))

        # --- persistent elements, redrawn every frame at full brightness ---
        hull_set = set(self.hull)
        for p in self.points:
            if p in hull_set:
                continue
            glow_circle(surface, p, 3, DIM_POINT, layers=1, core=True)

        # Confirmed hull edges (gradient glow polygon).
        n = len(self.hull)
        for i in range(n):
            a = self.hull[i]
            b = self.hull[(i + 1) % n] if (i + 1) < n else None
            if b is None:
                continue
            t = i / max(1, n - 1)
            col = lerp_color(EDGE_COLOR_A, EDGE_COLOR_B, t)
            glow_line(surface, a, b, col, width=3, layers=3)

        for p in self.hull:
            glow_circle(surface, p, 6, HULL_POINT, layers=4)

        # --- transient, phase-specific elements ---
        if self.phase == self.PHASE_SWEEP:
            # Only draw a short rolling trail of the most recently rejected
            # candidates (not every point tested so far) — keeps the sweep
            # looking like a moving radar trail instead of an ever-growing
            # tangle, and keeps per-frame draw cost bounded.
            for p in self.tested_so_far[-8:]:
                if p != self.best:
                    glow_line(surface, self.current, p, REJECT_COLOR, width=1, layers=2, alpha_scale=0.5)
            if self.best is not None:
                glow_line(surface, self.current, self.best, BEST_COLOR, width=2, layers=3)
                glow_circle(surface, self.best, 7, BEST_COLOR, layers=4)

            # The rotating search beam itself, cast far across the canvas.
            bx = self.current[0] + math.cos(self.beam_angle) * WIDTH
            by = self.current[1] + math.sin(self.beam_angle) * HEIGHT
            glow_line(surface, self.current, (bx, by), BEAM_COLOR, width=2, layers=2, alpha_scale=0.6)
            glow_circle(surface, self.current, 8, BEAM_COLOR, layers=5)

        elif self.phase == self.PHASE_COMMIT:
            t = ease_in_out(self.phase_t)
            end = (lerp(self.current[0], self.best[0], t), lerp(self.current[1], self.best[1], t))
            glow_line(surface, self.current, end, (255, 255, 255), width=3, layers=4)
            glow_circle(surface, self.current, 8, HULL_POINT, layers=4)

        elif self.phase == self.PHASE_DONE:
            pulse = 0.5 + 0.5 * math.sin(self.phase_t * 6.0)
            for p in self.hull:
                glow_circle(surface, p, 6 + pulse * 4, HULL_POINT, layers=4)

    # ------------------------------------------------------------------
    def hud_lines(self):
        phase_label = {
            self.PHASE_SWEEP: "sweeping for next hull point...",
            self.PHASE_COMMIT: "committing edge...",
            self.PHASE_DONE: "hull complete!",
        }[self.phase]
        return [
            f"points: {len(self.points)}",
            f"hull vertices: {len(self.hull)}",
            f"comparisons: {self.stats_comparisons}",
            f"sweeps run: {self.stats_resets}",
            f"time: {self.elapsed:5.1f}s",
            phase_label,
        ]


# ----------------------------------------------------------------------
# Main loop
# ----------------------------------------------------------------------
def main():
    pygame.init()
    pygame.display.set_caption("Convex Hull — Gift Wrapping (Jarvis March)")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()

    font_title = pygame.font.SysFont("consolas", 22, bold=True)
    font_hud = pygame.font.SysFont("consolas", 16)

    demo = HullDemo()
    fade_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_r:
                    demo.reset()

        demo.update(dt)
        demo.draw(screen, fade_surface)

        # Title
        title_surf = font_title.render("CONVEX HULL — GIFT WRAPPING", True, (0, 230, 255))
        screen.blit(title_surf, (24, 20))
        sub_surf = font_hud.render("radar-sweep search for each hull edge", True, TEXT_DIM)
        screen.blit(sub_surf, (24, 48))

        # HUD block, bottom-left corner, small and out of the way of the
        # actual visual (per the "supporting element, not the centerpiece"
        # guidance).
        hud_x, hud_y = 24, HEIGHT - 24 - 18 * 6
        for i, line in enumerate(demo.hud_lines()):
            color = TEXT_COLOR if i < 5 else BEST_COLOR
            surf = font_hud.render(line, True, color)
            screen.blit(surf, (hud_x, hud_y + i * 18))

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
