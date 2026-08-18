"""
Genetic Algorithm: Evolving Creatures Toward a Target
-------------------------------------------------------
A population of simple "creatures" tries to fly from a start point to a
glowing target while dodging obstacles. None of them are hand-programmed
to succeed -- each one just carries a genome (a fixed sequence of steering
directions). Every generation, the creatures that get closest to the
target survive and breed (crossover + mutation) into the next generation.
Watch the swarm's glow color creep from cold blue toward hot white/gold
across generations as fitness improves and paths visibly straighten out.

This is the same core idea (random variation + selection pressure) behind
real genetic algorithms and evolutionary strategies used in optimization
and robotics -- no gradients, no backprop, just "keep what works, mutate
the rest."

Controls:
  SPACE               - pause / resume
  R                   - reset with a brand new random population
  ESC / close window  - quit

Run with: python genetic_creatures.py
Requires: pygame  (pip install pygame)
"""

import os
import math
import random
import pygame

# --- Config ---------------------------------------------------------------
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 700

POP_SIZE = 36            # creatures per generation
GENOME_LEN = 20           # number of steering "genes" per creature
STEPS_PER_GENE = 12       # simulation frames each gene controls
LIFETIME = GENOME_LEN * STEPS_PER_GENE   # total frames per generation (240 -> 4s at 60fps)
CREATURE_SPEED = 6.5      # pixels moved per frame -- fast enough that a well-evolved
                           # genome can actually cover the start-to-target distance
                           # (with room to spare for routing around obstacles) within
                           # one lifetime, so "reaching the target" is achievable on screen.
TURN_EASE = 0.12          # how quickly a creature's heading eases toward its current gene's target direction (0-1, higher = snappier turns)

ELITE_COUNT = 4           # best creatures carried over unchanged
MUTATION_RATE = 0.22      # chance each gene mutates in a child
MUTATION_STRENGTH = 0.6   # radians of random nudge when a gene mutates
RANDOM_IMMIGRANTS = 3     # fresh random genomes injected each generation to
                           # keep exploring and avoid the population stalling
                           # on one mediocre strategy ("random immigrants" GA technique)

TARGET_RADIUS = 20
START_POS = (70, SCREEN_HEIGHT - 70)
TARGET_POS = (SCREEN_WIDTH - 70, 70)

BG_COLOR = (7, 6, 16)
PANEL_BG = (10, 10, 26, 175)
PANEL_BORDER = (90, 100, 150, 210)
TEXT_COLOR = (220, 228, 255)
HINT_COLOR = (120, 130, 170)

# Color story: worst creatures render cold/dim blue, best render hot
# yellow-white. This maps the population's fitness spread directly onto
# color instead of just printing numbers.
COLOR_LOW = (50, 70, 190)     # deep blue -- low fitness
COLOR_HIGH = (255, 235, 90)   # hot gold -- high fitness
COLOR_BEST = (255, 255, 255)  # this generation's single best creature

# Obstacles the creatures have to route around (rects), placed so a
# straight line from start to target is blocked.
OBSTACLES = [
    pygame.Rect(300, 260, 160, 260),
    pygame.Rect(560, 80, 160, 260),
    pygame.Rect(560, 420, 200, 60),
]


def normalize(vec):
    x, y = vec
    length = math.hypot(x, y)
    if length < 1e-9:
        return (1.0, 0.0)
    return (x / length, y / length)


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_color(c_low, c_high, t):
    """Blend two RGB colors by fraction t in [0, 1]."""
    t = max(0.0, min(1.0, t))
    return tuple(int(lerp(c_low[i], c_high[i], t)) for i in range(3))


# --- Genetic algorithm core (pure logic, no rendering) ---------------------
# Kept separate from drawing so it can be unit-tested headlessly by
# stubbing out pygame's rendering entirely.

def random_genome():
    """A genome is just a list of steering angles (radians), one per gene."""
    return [random.uniform(0, math.tau) for _ in range(GENOME_LEN)]


def simulate_creature(genome, obstacles=OBSTACLES, start=START_POS, target=TARGET_POS):
    """Play a genome forward for its whole lifetime and return the path it
    traces, its fitness score, and whether it reached the target / hit an
    obstacle. This is deterministic and side-effect free, which is what
    makes the whole generation's paths precomputable before animating.
    """
    x, y = start
    heading = (1.0, 0.0)  # current smoothed movement direction
    path = [(x, y)]
    collided = False
    reached = False
    reach_frame = None
    min_dist = math.hypot(target[0] - x, target[1] - y)

    for gene_angle in genome:
        target_dir = (math.cos(gene_angle), math.sin(gene_angle))
        for _ in range(STEPS_PER_GENE):
            if collided or reached:
                path.append((x, y))
                continue

            # Ease the heading toward this gene's target direction instead
            # of snapping instantly -- produces smooth curves rather than
            # jagged zig-zag paths.
            heading = normalize((
                lerp(heading[0], target_dir[0], TURN_EASE),
                lerp(heading[1], target_dir[1], TURN_EASE),
            ))

            nx = x + heading[0] * CREATURE_SPEED
            ny = y + heading[1] * CREATURE_SPEED
            nx = min(max(nx, 0), SCREEN_WIDTH)
            ny = min(max(ny, 0), SCREEN_HEIGHT)

            for obs in obstacles:
                if obs.collidepoint(nx, ny):
                    collided = True
                    break

            x, y = nx, ny
            dist = math.hypot(target[0] - x, target[1] - y)
            if dist < min_dist:
                min_dist = dist
            if not reached and dist <= TARGET_RADIUS:
                reached = True
                reach_frame = len(path)

            path.append((x, y))

    # Fitness rewards getting close, heavily rewards actually arriving
    # (and arriving early), and penalizes crashing into an obstacle.
    fitness = -min_dist
    if reached:
        fitness += 500.0 + (LIFETIME - reach_frame) * 0.5
    if collided:
        fitness -= 150.0

    return {
        "path": path,
        "fitness": fitness,
        "reached": reached,
        "collided": collided,
        "min_dist": min_dist,
    }


def crossover(genome_a, genome_b):
    """Uniform crossover: each gene independently comes from one parent."""
    return [genome_a[i] if random.random() < 0.5 else genome_b[i] for i in range(len(genome_a))]


def mutate(genome):
    child = []
    for gene in genome:
        if random.random() < MUTATION_RATE:
            gene = gene + random.gauss(0, MUTATION_STRENGTH)
        child.append(gene % math.tau)
    return child


def evolve_population(genomes, results):
    """Elitism + uniform crossover + mutation. Returns the next generation's
    list of genomes, sorted best-first alongside their source results."""
    ranked = sorted(zip(genomes, results), key=lambda pair: pair[1]["fitness"], reverse=True)
    ranked_genomes = [g for g, _ in ranked]

    next_gen = [list(g) for g in ranked_genomes[:ELITE_COUNT]]  # elites copied unchanged
    top_half = ranked_genomes[:max(2, len(ranked_genomes) // 2)]

    target_size = len(genomes) - RANDOM_IMMIGRANTS
    while len(next_gen) < target_size:
        parent_a = random.choice(top_half)
        parent_b = random.choice(top_half)
        child = mutate(crossover(parent_a, parent_b))
        next_gen.append(child)

    # A few completely fresh, unrelated genomes each generation -- keeps
    # the population from converging too early on one mediocre route.
    for _ in range(RANDOM_IMMIGRANTS):
        next_gen.append(random_genome())

    return next_gen, ranked


# --- Rendering helpers -------------------------------------------------

def draw_glow(surface, pos, radius, color, layers=4, max_alpha=70):
    """Layer shrinking, low-alpha circles and additive-blend them for a
    soft neon glow instead of a flat filled shape."""
    size = int(radius * 4)
    if size <= 0:
        return
    glow_surf = pygame.Surface((size, size), pygame.SRCALPHA)
    center = size // 2
    for layer in range(layers, 0, -1):
        alpha = int(max_alpha / layer)
        r = int(radius * (0.9 + layer * 0.7))
        pygame.draw.circle(glow_surf, (*color, alpha), (center, center), r)
    surface.blit(glow_surf, (pos[0] - center, pos[1] - center), special_flags=pygame.BLEND_RGBA_ADD)


def draw_target(surface, pos, t):
    """A pulsing concentric-ring target so it reads as the clear goal."""
    pulse = (math.sin(t * 3.0) + 1) / 2  # 0..1 breathing pulse
    draw_glow(surface, pos, TARGET_RADIUS + pulse * 6, (255, 60, 220), layers=5, max_alpha=90)
    for i, (radius_mult, color) in enumerate([(1.0, (255, 90, 230)), (0.55, (255, 200, 250))]):
        r = int((TARGET_RADIUS + pulse * 6) * radius_mult)
        pygame.draw.circle(surface, color, pos, max(2, r), width=2 if i == 0 else 0)


def draw_obstacles(surface, t):
    """Dark blocks with a slow-breathing magenta/red outline glow."""
    pulse = (math.sin(t * 2.0) + 1) / 2
    outline_color = (200 + int(pulse * 40), 40, 90)
    for obs in OBSTACLES:
        pygame.draw.rect(surface, (26, 14, 24), obs, border_radius=6)
        pygame.draw.rect(surface, outline_color, obs, width=2, border_radius=6)


def draw_hud(surface, font, small_font, generation, best_fitness, best_ever, reached_count, paused, history):
    box_w, box_h = 250, 118
    hud_surf = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
    pygame.draw.rect(hud_surf, PANEL_BG, (0, 0, box_w, box_h), border_radius=8)
    pygame.draw.rect(hud_surf, PANEL_BORDER, (0, 0, box_w, box_h), width=1, border_radius=8)
    surface.blit(hud_surf, (14, 14))

    lines = [
        f"Generation: {generation}",
        f"Best fitness (gen): {best_fitness:.1f}",
        f"Best fitness (ever): {best_ever:.1f}",
        f"Reached target: {reached_count}/{POP_SIZE}",
    ]
    y = 22
    for line in lines:
        surface.blit(font.render(line, True, TEXT_COLOR), (26, y))
        y += 22

    if paused:
        surface.blit(small_font.render("PAUSED", True, (255, 230, 60)), (26, y))

    # Small glowing sparkline of best-fitness-per-generation, tucked in the
    # same corner panel instead of a plain bar chart -- a thin glowing
    # line with a soft filled area beneath it.
    if len(history) >= 2:
        graph_w, graph_h = 220, 30
        graph_surf = pygame.Surface((graph_w, graph_h), pygame.SRCALPHA)
        lo, hi = min(history), max(history)
        span = max(1.0, hi - lo)
        points = []
        for i, val in enumerate(history[-40:]):
            px = int(i / max(1, len(history[-40:]) - 1) * (graph_w - 4)) + 2
            py = graph_h - 2 - int((val - lo) / span * (graph_h - 4))
            points.append((px, py))
        if len(points) >= 2:
            fill_pts = points + [(points[-1][0], graph_h), (points[0][0], graph_h)]
            pygame.draw.polygon(graph_surf, (60, 220, 255, 50), fill_pts)
            pygame.draw.lines(graph_surf, (100, 240, 255, 230), False, points, width=2)
        surface.blit(graph_surf, (14, 14 + box_h - 4))

    hint = "SPACE: pause   R: new population"
    surface.blit(small_font.render(hint, True, HINT_COLOR), (14, SCREEN_HEIGHT - 26))


def main():
    pygame.init()
    pygame.display.set_caption("Genetic Algorithm: Evolving Creatures")
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pygame.time.Clock()

    font = pygame.font.SysFont("consolas", 17)
    small_font = pygame.font.SysFont("consolas", 13)

    # Trail surface that fades each frame instead of being cleared, so
    # every creature leaves a short glowing streak behind it.
    trail_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    trail_surface.set_alpha(28)
    trail_surface.fill(BG_COLOR)

    genomes = [random_genome() for _ in range(POP_SIZE)]
    generation = 1
    frame_in_gen = 0
    paused = False
    best_ever = float("-inf")
    fitness_history = []

    results = [simulate_creature(g) for g in genomes]

    # Headless self-test support: auto-quit after a bounded number of
    # frames when SDL_VIDEODRIVER=dummy is set, so this can be verified
    # without a real display attached.
    headless_test = os.environ.get("SDL_VIDEODRIVER") == "dummy"
    headless_frame_limit = 400
    total_frames = 0

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_r:
                    genomes = [random_genome() for _ in range(POP_SIZE)]
                    results = [simulate_creature(g) for g in genomes]
                    generation = 1
                    frame_in_gen = 0
                    best_ever = float("-inf")
                    fitness_history = []

        t = total_frames / 60.0

        if not paused:
            frame_in_gen += 1

        # Fade the trail surface onto the screen (cheap way to get long
        # glowing streaks without storing per-creature point history).
        screen.blit(trail_surface, (0, 0))
        draw_obstacles(screen, t)
        draw_target(screen, TARGET_POS, t)

        gen_best_fitness = max(r["fitness"] for r in results)
        best_ever = max(best_ever, gen_best_fitness)
        reached_count = sum(1 for r in results if r["reached"])
        lo_fit = min(r["fitness"] for r in results)
        hi_fit = max(r["fitness"] for r in results)
        span = max(1e-6, hi_fit - lo_fit)
        best_idx = max(range(len(results)), key=lambda i: results[i]["fitness"])

        display_frame = min(frame_in_gen, LIFETIME - 1)
        for i, result in enumerate(results):
            pos = result["path"][display_frame]
            norm_fitness = (result["fitness"] - lo_fit) / span
            color = COLOR_BEST if i == best_idx else lerp_color(COLOR_LOW, COLOR_HIGH, norm_fitness)
            radius = 5.5 if i == best_idx else 3.2 + norm_fitness * 1.5
            # draw the glow onto the fading trail surface so it leaves a streak,
            # and a crisp core dot straight onto the screen each frame.
            draw_glow(trail_surface, (int(pos[0]), int(pos[1])), radius, color, layers=3, max_alpha=55)
            pygame.draw.circle(screen, color, (int(pos[0]), int(pos[1])), max(1, int(radius * 0.6)))

        fitness_history.append(gen_best_fitness)
        draw_hud(screen, font, small_font, generation, gen_best_fitness, best_ever, reached_count, paused, fitness_history)

        pygame.display.flip()
        clock.tick(60)
        total_frames += 1

        if not paused and frame_in_gen >= LIFETIME + 45:  # +45 frame pause to admire the finished generation
            genomes, ranked = evolve_population(genomes, results)
            results = [simulate_creature(g) for g in genomes]
            generation += 1
            frame_in_gen = 0

        if headless_test and total_frames >= headless_frame_limit:
            running = False

    pygame.quit()


if __name__ == "__main__":
    main()
