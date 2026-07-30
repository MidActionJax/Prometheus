"""
Ant Colony Optimization — Shortest Path Discovery
===================================================

WHAT THIS DEMONSTRATES
-----------------------
A colony of ants needs to get from the NEST to a FOOD source. There are four
possible routes of slightly different lengths. No single ant knows which
route is shortest — there is no map, no central planner, no lookahead.
Instead, each ant lays down a chemical "pheromone" trail as it walks, that
trail slowly evaporates, and future ants are more likely to follow paths
that already smell strongly of pheromone.

Because ants on SHORTER paths complete their round trip faster, they lay
down pheromone more *often* per unit of time than ants on longer paths.
That small speed advantage compounds: more pheromone -> more ants choose
that path -> even more pheromone -> even more ants. This is a positive
feedback loop called "stigmergy" (indirect coordination through a shared
environment), and it's the same core idea behind Ant Colony Optimization
(ACO) algorithms used for real routing and scheduling problems.

Meanwhile pheromone evaporation keeps the system from getting permanently
stuck: if the "best" path were ever blocked, or a better one appeared, the
colony can still shift its behavior because old trails fade rather than
lasting forever. That evaporation is what balances EXPLOITATION (follow the
strong trail) against EXPLORATION (still sometimes try a weaker one).

Watch the four glowing lines: they all start dim and roughly equal. Over
time, the paths carrying more ants get thicker and brighter, and the
longest path fades into the dark — with nobody "deciding" anything.

CONTROLS
--------
  SPACE  - pause / resume
  R      - reset the simulation
  ESC    - quit

Run with:  python ant_colony_optimization.py
Requires:  pip install pygame
"""

import math
import random

import pygame

# ---------------------------------------------------------------------------
# Window / simulation constants
# ---------------------------------------------------------------------------
WIDTH, HEIGHT = 1000, 600
FPS = 60
BG_COLOR = (8, 10, 18)

NEST_POS = (80, 300)
FOOD_POS = (920, 300)

ALPHA = 1.3               # how strongly pheromone concentration drives choice
BETA = 2.5                # how strongly raw distance (a built-in "instinct") drives choice
EVAPORATION_RATE = 0.5     # fraction of a path's pheromone lost per second
DEPOSIT_Q = 500.0          # pheromone units deposited per arriving ant = Q / path_length
MIN_PHEROMONE = 0.05       # floor so a path never fully "dies" (keeps exploration alive)
ANT_SPEED = 260.0          # pixels / second
SPAWN_INTERVAL = 0.25      # seconds between spawn waves
ANTS_PER_WAVE = 2          # ants dispatched at each wave

# Each path is a quadratic Bezier curve from NEST to FOOD through one
# control point. Slightly different control points -> slightly different
# lengths, which is all ACO needs to eventually tell them apart.
PATH_CONTROL_POINTS = [
    (500, 330),   # path 0: nearly straight -> shortest
    (500, 175),   # path 1: gentle upward arc
    (520, 500),   # path 2: downward arc
    (560, 60),    # path 3: big upward arc -> longest
]

PATH_COLORS = [
    (0, 255, 255),    # cyan
    (255, 0, 255),    # magenta
    (255, 255, 0),    # yellow
    (60, 255, 120),   # green
]


# ---------------------------------------------------------------------------
# Geometry helpers — pure math, no pygame calls. Kept separate from drawing
# so the algorithm itself can be tested without a display.
# ---------------------------------------------------------------------------

def quadratic_bezier(p0, p1, p2, t):
    """Point at parameter t (0..1) along a quadratic Bezier curve."""
    x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0]
    y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1]
    return (x, y)


def sample_bezier(p0, p1, p2, samples=48):
    """Sample the curve into a polyline so we can draw it and measure it."""
    return [quadratic_bezier(p0, p1, p2, i / (samples - 1)) for i in range(samples)]


def point_at_distance(points, seg_lengths, total_length, dist):
    """Walk a sampled polyline and return the (x, y) point `dist` pixels
    along it from the start. Clamped to the endpoints."""
    if dist <= 0:
        return points[0]
    if dist >= total_length:
        return points[-1]
    covered = 0.0
    for i, seg_len in enumerate(seg_lengths):
        if covered + seg_len >= dist:
            remain = dist - covered
            t = 0.0 if seg_len == 0 else remain / seg_len
            x = points[i][0] + (points[i + 1][0] - points[i][0]) * t
            y = points[i][1] + (points[i + 1][1] - points[i][1]) * t
            return (x, y)
        covered += seg_len
    return points[-1]


# ---------------------------------------------------------------------------
# Core ACO simulation state — no pygame calls anywhere in this section.
# `main()` at the bottom only *reads* this object to draw the frame.
# ---------------------------------------------------------------------------

class PheromonePath:
    def __init__(self, idx, p0, p1, p2, color):
        self.idx = idx
        self.points = sample_bezier(p0, p1, p2)
        self.seg_lengths = [
            math.dist(self.points[i], self.points[i + 1])
            for i in range(len(self.points) - 1)
        ]
        self.length = sum(self.seg_lengths)
        self.pheromone = 1.0
        self.color = color

    def evaporate(self, dt):
        # Exponential decay, framerate-independent: shrink by (1 - rate) every
        # second, regardless of how big or small dt is.
        self.pheromone *= (1.0 - EVAPORATION_RATE) ** dt
        if self.pheromone < MIN_PHEROMONE:
            self.pheromone = MIN_PHEROMONE

    def deposit(self):
        # Ants on shorter paths deposit relatively more pheromone per trip,
        # AND complete more trips per unit time -- a double advantage.
        self.pheromone += DEPOSIT_Q / self.length

    def point_at(self, dist):
        return point_at_distance(self.points, self.seg_lengths, self.length, dist)


class Ant:
    __slots__ = ("path_idx", "progress", "speed")

    def __init__(self, path_idx, speed=ANT_SPEED):
        self.path_idx = path_idx
        self.progress = 0.0
        self.speed = speed

    def update(self, dt, path_length):
        self.progress += self.speed * dt
        return self.progress >= path_length


class Simulation:
    """Owns every path and every ant, and advances the ACO algorithm one
    tick at a time. Completely independent of pygame/rendering."""

    def __init__(self):
        self.paths = [
            PheromonePath(i, NEST_POS, ctrl, FOOD_POS, PATH_COLORS[i])
            for i, ctrl in enumerate(PATH_CONTROL_POINTS)
        ]
        self.ants = []
        self.tick_count = 0
        self.dispatched = 0
        self.arrived = 0
        self.spawn_timer = 0.0

    def _desirabilities(self):
        # Classic ACO transition rule: pheromone^alpha * heuristic^beta,
        # where the heuristic here is "1 / distance" (shorter = instinctively
        # more attractive, same as real ants preferring straighter walks).
        return [
            (p.pheromone ** ALPHA) * ((1.0 / p.length) ** BETA)
            for p in self.paths
        ]

    def selection_probabilities(self):
        weights = self._desirabilities()
        total = sum(weights) or 1.0
        return [w / total for w in weights]

    def choose_path(self):
        weights = self._desirabilities()
        total = sum(weights)
        r = random.random() * total
        acc = 0.0
        for i, w in enumerate(weights):
            acc += w
            if r <= acc:
                return i
        return len(weights) - 1

    def step(self, dt):
        self.tick_count += 1

        # Spawn new ants at a steady rate, each choosing a path right now
        # based on the current pheromone levels.
        self.spawn_timer += dt
        while self.spawn_timer >= SPAWN_INTERVAL:
            self.spawn_timer -= SPAWN_INTERVAL
            for _ in range(ANTS_PER_WAVE):
                idx = self.choose_path()
                self.ants.append(Ant(idx))
                self.dispatched += 1

        # Advance every ant currently walking; collect arrivals.
        still_travelling = []
        for ant in self.ants:
            arrived = ant.update(dt, self.paths[ant.path_idx].length)
            if arrived:
                self.paths[ant.path_idx].deposit()
                self.arrived += 1
            else:
                still_travelling.append(ant)
        self.ants = still_travelling

        # Every path's pheromone fades a little each tick.
        for p in self.paths:
            p.evaporate(dt)

    def best_path(self):
        return max(self.paths, key=lambda p: p.pheromone)


# ---------------------------------------------------------------------------
# Rendering + main loop (pygame only lives below this line)
# ---------------------------------------------------------------------------

def draw_hud(screen, font, sim):
    probs = sim.selection_probabilities()
    best = sim.best_path()

    lines = [
        f"Tick: {sim.tick_count}    Ants dispatched: {sim.dispatched}    Arrived: {sim.arrived}",
        "",
        "Path pheromone strength & live choice probability:",
    ]
    for p, prob in zip(sim.paths, probs):
        tag = "  <-- currently favored" if p is best and sim.tick_count > 90 else ""
        lines.append(
            f"  Path {p.idx + 1}  len {int(p.length):4d}px   "
            f"pheromone {p.pheromone:6.1f}   chosen {prob * 100:4.1f}% of the time{tag}"
        )

    y = 14
    for line in lines:
        surf = font.render(line, True, (225, 228, 235))
        screen.blit(surf, (16, y))
        y += 22


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Ant Colony Optimization — Shortest Path Discovery")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 16)
    label_font = pygame.font.SysFont("consolas", 20, bold=True)

    sim = Simulation()

    # A translucent surface that ants draw glowing dots onto. Multiplying it
    # by a near-black color each frame (instead of clearing it) is the
    # classic trick for a fading comet-trail effect.
    trail_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    fade_layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    fade_layer.fill((0, 0, 0, 20))

    paused = False
    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_r:
                    sim = Simulation()

        if not paused:
            sim.step(dt)

        # Fade the ant trail layer toward transparent.
        trail_surface.blit(fade_layer, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)

        screen.fill(BG_COLOR)

        # Draw each pheromone path -- brighter & thicker as pheromone builds.
        max_pher = max(p.pheromone for p in sim.paths) or 1.0
        for p in sim.paths:
            strength = p.pheromone / max_pher
            width = 1 + int(strength * 6)
            color = tuple(int(c * (0.25 + 0.75 * strength)) for c in p.color)
            pygame.draw.lines(screen, color, False, p.points, width)

        # Draw ants (bright dots) and feed their glow into the trail layer.
        for ant in sim.ants:
            path = sim.paths[ant.path_idx]
            x, y = path.point_at(ant.progress)
            pygame.draw.circle(trail_surface, (*path.color, 255), (int(x), int(y)), 3)
            pygame.draw.circle(screen, (255, 255, 255), (int(x), int(y)), 3)

        screen.blit(trail_surface, (0, 0))

        # Nest + food markers.
        pygame.draw.circle(screen, (0, 220, 255), NEST_POS, 14)
        pygame.draw.circle(screen, (255, 60, 220), FOOD_POS, 14)
        screen.blit(label_font.render("NEST", True, (0, 220, 255)), (NEST_POS[0] - 32, NEST_POS[1] + 20))
        screen.blit(label_font.render("FOOD", True, (255, 60, 220)), (FOOD_POS[0] - 32, FOOD_POS[1] + 20))

        draw_hud(screen, font, sim)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
