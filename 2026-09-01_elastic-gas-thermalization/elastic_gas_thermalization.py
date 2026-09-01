"""
Elastic Gas Thermalization
---------------------------
A sealed box starts split in two by a divider: a cluster of fast, hot
(red/orange) particles on the right, a cluster of slow, cold (blue/violet)
particles on the left. When the divider drops, every particle collision
inside the box is a perfectly ELASTIC collision -- no energy is lost, only
exchanged. Nothing pushes the system toward balance on purpose. Watch what
happens anyway: within a few seconds the hot and cold populations blend into
a single, statistically stable mix of speeds. That emergent stability is the
Maxwell-Boltzmann speed distribution, the same law that describes molecules
bouncing around in a real gas.

Physics demonstrated:
  - Elastic collisions between equal-mass bodies: for two circles of equal
    mass, an elastic collision simply exchanges the component of velocity
    that lies along the line connecting their centers, and leaves the
    perpendicular component untouched. That one rule is all this sim needs.
  - Conservation of momentum -- the vector sum of every particle's momentum
    is checked live and stays flat across thousands of collisions.
  - Conservation of kinetic energy -- elastic collisions conserve KE exactly
    (nothing here is inelastic / no energy leaks to heat or deformation).
  - Emergence of the Maxwell-Boltzmann speed distribution: no particle is
    told to seek a "fair" speed. The equilibrium curve emerges purely from
    many random elastic collisions, and the live histogram converges to the
    theoretical curve drawn on top of it.

Controls:
  SPACE               - pause / resume
  R                   - reset (re-splits into hot/cold halves with a divider)
  ESC / close window  - quit

Run with: python elastic_gas_thermalization.py
Requires: pygame  (pip install pygame)
"""

import math
import random
import sys

import pygame

# --- Config ---------------------------------------------------------------
SCREEN_WIDTH = 1100
SCREEN_HEIGHT = 750

BOX_LEFT, BOX_TOP = 60, 90
BOX_RIGHT, BOX_BOTTOM = SCREEN_WIDTH - 60, SCREEN_HEIGHT - 70

N_PARTICLES = 70
RADIUS = 6.0
DIVIDER_DROP_TIME = 2.2      # seconds the divider stays up before dropping
TRAIL_ALPHA = 42             # lower = longer-lingering motion trails

BG_COLOR = (5, 6, 14)
TEXT_COLOR = (215, 225, 255)
HINT_COLOR = (120, 130, 170)
BOX_LINE_COLOR = (70, 80, 120)

# Speed -> color stops, cold to hot (thermal-camera style palette).
SPEED_GRADIENT = [
    (0.00, (60, 90, 255)),    # deep blue  = cold / slow
    (0.30, (60, 220, 255)),   # cyan
    (0.55, (120, 255, 120)),  # green
    (0.75, (255, 230, 60)),   # yellow
    (1.00, (255, 60, 90)),    # hot red/magenta = fast
]


def speed_color(speed, max_speed):
    """Map a particle's speed to a color along SPEED_GRADIENT."""
    t = max(0.0, min(1.0, speed / max_speed))
    for i in range(len(SPEED_GRADIENT) - 1):
        t0, c0 = SPEED_GRADIENT[i]
        t1, c1 = SPEED_GRADIENT[i + 1]
        if t0 <= t <= t1:
            local_t = 0 if t1 == t0 else (t - t0) / (t1 - t0)
            return tuple(int(c0[k] + (c1[k] - c0[k]) * local_t) for k in range(3))
    return SPEED_GRADIENT[-1][1]


class Particle:
    def __init__(self, x, y, vx, vy, hot):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.hot = hot  # which side this particle started on, for the flash color

    def speed(self):
        return math.hypot(self.vx, self.vy)

    def step(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt


def resolve_wall_collisions(p):
    bounced = False
    if p.x - RADIUS < BOX_LEFT:
        p.x = BOX_LEFT + RADIUS
        p.vx = abs(p.vx)
        bounced = True
    elif p.x + RADIUS > BOX_RIGHT:
        p.x = BOX_RIGHT - RADIUS
        p.vx = -abs(p.vx)
        bounced = True
    if p.y - RADIUS < BOX_TOP:
        p.y = BOX_TOP + RADIUS
        p.vy = abs(p.vy)
        bounced = True
    elif p.y + RADIUS > BOX_BOTTOM:
        p.y = BOX_BOTTOM - RADIUS
        p.vy = -abs(p.vy)
        bounced = True
    return bounced


def resolve_particle_collision(a, b):
    """Elastic collision between two equal-mass circles: swap the velocity
    component along the line connecting their centers, leave the
    perpendicular component untouched. Returns True if a collision happened."""
    dx = b.x - a.x
    dy = b.y - a.y
    dist_sq = dx * dx + dy * dy
    min_dist = RADIUS * 2
    if dist_sq >= min_dist * min_dist or dist_sq == 0:
        return False

    dist = math.sqrt(dist_sq)
    nx, ny = dx / dist, dy / dist

    # Separate overlapping circles so they don't stick together.
    overlap = min_dist - dist
    a.x -= nx * overlap / 2
    a.y -= ny * overlap / 2
    b.x += nx * overlap / 2
    b.y += ny * overlap / 2

    # Relative velocity along the normal.
    dvx = b.vx - a.vx
    dvy = b.vy - a.vy
    vel_along_normal = dvx * nx + dvy * ny
    if vel_along_normal > 0:
        return False  # already separating, no exchange needed

    # Equal masses -> exchange the full normal-component of velocity.
    a.vx += vel_along_normal * nx
    a.vy += vel_along_normal * ny
    b.vx -= vel_along_normal * nx
    b.vy -= vel_along_normal * ny
    return True


def make_particles():
    particles = []
    mid_x = (BOX_LEFT + BOX_RIGHT) / 2
    gap = 14  # keep particles off the divider line

    # Cold, slow cluster on the left.
    for _ in range(N_PARTICLES // 2):
        x = random.uniform(BOX_LEFT + RADIUS * 2, mid_x - gap)
        y = random.uniform(BOX_TOP + RADIUS * 2, BOX_BOTTOM - RADIUS * 2)
        angle = random.uniform(0, math.tau)
        speed = random.uniform(20, 60)
        particles.append(Particle(x, y, math.cos(angle) * speed, math.sin(angle) * speed, hot=False))

    # Hot, fast cluster on the right.
    for _ in range(N_PARTICLES - N_PARTICLES // 2):
        x = random.uniform(mid_x + gap, BOX_RIGHT - RADIUS * 2)
        y = random.uniform(BOX_TOP + RADIUS * 2, BOX_BOTTOM - RADIUS * 2)
        angle = random.uniform(0, math.tau)
        speed = random.uniform(220, 340)
        particles.append(Particle(x, y, math.cos(angle) * speed, math.sin(angle) * speed, hot=True))

    return particles


def total_momentum(particles):
    px = sum(p.vx for p in particles)
    py = sum(p.vy for p in particles)
    return math.hypot(px, py)


def total_kinetic_energy(particles):
    # mass = 1 for every particle, so KE = 0.5 * v^2 summed.
    return sum(0.5 * (p.vx * p.vx + p.vy * p.vy) for p in particles)


def draw_glow_circle(surface, color, pos, radius):
    """Layer translucent circles of shrinking radius / rising alpha, then
    additive-blit them, so each particle reads as a small glowing orb."""
    glow_r = int(radius * 4)
    glow_surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
    for layer in range(4, 0, -1):
        alpha = int(60 / layer)
        r = int(radius * (1 + layer * 0.85))
        pygame.draw.circle(glow_surf, (*color, alpha), (glow_r, glow_r), r)
    surface.blit(glow_surf, (pos[0] - glow_r, pos[1] - glow_r), special_flags=pygame.BLEND_RGBA_ADD)
    pygame.draw.circle(surface, color, pos, int(radius))
    pygame.draw.circle(surface, (255, 255, 255), pos, max(1, int(radius * 0.35)))


def draw_collision_flash(surface, pos, color, age, max_age):
    """A quickly-expanding, fading ring drawn at each collision point --
    the visual 'proof' that a collision is happening right there, right now."""
    t = age / max_age
    if t >= 1.0:
        return
    r = int(RADIUS + t * 26)
    alpha = int(200 * (1 - t))
    flash_surf = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
    pygame.draw.circle(flash_surf, (*color, alpha), (r + 2, r + 2), r, width=2)
    surface.blit(flash_surf, (pos[0] - r - 2, pos[1] - r - 2), special_flags=pygame.BLEND_RGBA_ADD)


def maxwell_boltzmann_2d(v, sigma_sq):
    """2D Maxwell-Boltzmann speed distribution: f(v) = (v / sigma^2) *
    exp(-v^2 / (2*sigma^2)), where sigma^2 = k*T/m (here estimated straight
    from the live data, since m = 1)."""
    if sigma_sq <= 1e-6:
        return 0.0
    return (v / sigma_sq) * math.exp(-(v * v) / (2 * sigma_sq))


def draw_histogram(surface, small_font, particles, max_speed):
    """Small corner panel: live speed histogram (bars, color-matched to the
    speed gradient) with the theoretical Maxwell-Boltzmann curve drawn over
    it in bright white, so you can watch the bars converge onto the curve."""
    panel_w, panel_h = 250, 130
    px0, py0 = SCREEN_WIDTH - panel_w - 18, SCREEN_HEIGHT - panel_h - 18

    panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    pygame.draw.rect(panel, (10, 10, 25, 165), (0, 0, panel_w, panel_h), border_radius=8)
    pygame.draw.rect(panel, (80, 90, 140, 200), (0, 0, panel_w, panel_h), width=1, border_radius=8)

    n_bins = 18
    bin_w = max_speed / n_bins
    counts = [0] * n_bins
    for p in particles:
        b = min(n_bins - 1, int(p.speed() / bin_w))
        counts[b] += 1
    peak = max(counts) if counts else 1

    plot_left, plot_bottom, plot_h, plot_w = 10, panel_h - 16, panel_h - 34, panel_w - 20
    bar_w = plot_w / n_bins
    for i, c in enumerate(counts):
        bar_h = (c / peak) * plot_h if peak else 0
        color = speed_color((i + 0.5) * bin_w, max_speed)
        x = plot_left + i * bar_w
        pygame.draw.rect(panel, (*color, 220), (x, plot_bottom - bar_h, max(1, bar_w - 2), bar_h))

    # Overlay the theoretical Maxwell-Boltzmann curve, scaled to the panel.
    mean_sq_speed = sum(p.vx ** 2 + p.vy ** 2 for p in particles) / max(1, len(particles))
    sigma_sq = mean_sq_speed / 2.0
    curve_peak = maxwell_boltzmann_2d(math.sqrt(sigma_sq), sigma_sq) if sigma_sq > 0 else 0
    if curve_peak > 0:
        points = []
        for i in range(60):
            v = (i / 59) * max_speed
            f = maxwell_boltzmann_2d(v, sigma_sq)
            y = plot_bottom - (f / curve_peak) * plot_h * (peak / peak)  # scaled to same visual height
            x = plot_left + (v / max_speed) * plot_w
            points.append((x, min(plot_bottom, max(plot_bottom - plot_h, y))))
        if len(points) > 1:
            pygame.draw.lines(panel, (255, 255, 255, 235), False, points, 2)

    label = small_font.render("speed distribution  (curve = Maxwell-Boltzmann)", True, (200, 210, 240))
    panel.blit(label, (10, 4))
    surface.blit(panel, (px0, py0))


def draw_hud(surface, font, small_font, elapsed, collisions, momentum, energy, initial_energy, paused):
    box_w, box_h = 250, 118
    hud = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
    pygame.draw.rect(hud, (10, 10, 25, 165), (0, 0, box_w, box_h), border_radius=8)
    pygame.draw.rect(hud, (80, 90, 140, 200), (0, 0, box_w, box_h), width=1, border_radius=8)
    surface.blit(hud, (14, 14))

    energy_ratio = energy / initial_energy if initial_energy else 1.0
    lines = [
        (f"Time: {elapsed:.1f}s", TEXT_COLOR),
        (f"Collisions: {collisions}", (255, 210, 90)),
        (f"|momentum|: {momentum:6.1f}", (110, 220, 255)),
        (f"KE / KE0: {energy_ratio * 100:5.1f}%", (150, 255, 150)),
    ]
    y = 22
    for text, color in lines:
        surface.blit(font.render(text, True, color), (26, y))
        y += 22

    if paused:
        surface.blit(small_font.render("PAUSED", True, (255, 230, 60)), (26, y))


def draw_box_and_divider(surface, small_font, divider_up, divider_progress):
    pygame.draw.rect(
        surface, BOX_LINE_COLOR,
        (BOX_LEFT, BOX_TOP, BOX_RIGHT - BOX_LEFT, BOX_BOTTOM - BOX_TOP), width=2, border_radius=4
    )
    if divider_up:
        mid_x = (BOX_LEFT + BOX_RIGHT) / 2
        # Divider retracts upward out of the box as it "drops" (opens).
        top = BOX_TOP + (BOX_BOTTOM - BOX_TOP) * divider_progress
        glow = pygame.Surface((10, BOX_BOTTOM - top), pygame.SRCALPHA)
        pygame.draw.rect(glow, (255, 255, 255, 140), (3, 0, 4, glow.get_height()))
        surface.blit(glow, (mid_x - 5, top), special_flags=pygame.BLEND_RGBA_ADD)

    label = "left: cold / slow start        right: hot / fast start"
    surface.blit(small_font.render(label, True, HINT_COLOR), (BOX_LEFT, BOX_TOP - 26))

    hint = "SPACE: pause    R: reset    ESC: quit"
    surface.blit(small_font.render(hint, True, HINT_COLOR), (14, SCREEN_HEIGHT - 26))


def main():
    pygame.init()
    pygame.display.set_caption("Elastic Gas Thermalization")
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pygame.time.Clock()

    font = pygame.font.SysFont("consolas", 18)
    small_font = pygame.font.SysFont("consolas", 14)

    trail_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    trail_surface.set_alpha(TRAIL_ALPHA)
    trail_surface.fill(BG_COLOR)

    particles = make_particles()
    initial_energy = total_kinetic_energy(particles)
    max_speed_seen = max(p.speed() for p in particles)

    elapsed = 0.0
    collisions = 0
    flashes = []          # list of [x, y, color, age]
    FLASH_MAX_AGE = 0.35
    divider_up = True
    paused = False

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        dt = min(dt, 1 / 30)  # clamp so a stalled frame can't fling particles through walls

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_r:
                    particles = make_particles()
                    initial_energy = total_kinetic_energy(particles)
                    max_speed_seen = max(p.speed() for p in particles)
                    elapsed = 0.0
                    collisions = 0
                    flashes = []
                    divider_up = True

        if not paused:
            elapsed += dt

            if divider_up and elapsed >= DIVIDER_DROP_TIME:
                divider_up = False

            for p in particles:
                p.step(dt)
                resolve_wall_collisions(p)

            # O(n^2) pairwise collision check -- fine at this particle count.
            for i in range(len(particles)):
                for j in range(i + 1, len(particles)):
                    a, b = particles[i], particles[j]
                    if divider_up:
                        # Divider still up: block collisions/crossing across the midline
                        # by simply skipping cross-side pairs (they're already kept apart
                        # spatially by their starting positions and wall bounces).
                        mid_x = (BOX_LEFT + BOX_RIGHT) / 2
                        if (a.x < mid_x) != (b.x < mid_x):
                            continue
                    if resolve_particle_collision(a, b):
                        collisions += 1
                        mx, my = (a.x + b.x) / 2, (a.y + b.y) / 2
                        flash_color = speed_color(max(a.speed(), b.speed()), max_speed_seen)
                        flashes.append([mx, my, flash_color, 0.0])

            if divider_up:
                mid_x = (BOX_LEFT + BOX_RIGHT) / 2
                for p in particles:
                    if p.hot and p.x - RADIUS < mid_x + 3:
                        p.x = mid_x + 3 + RADIUS
                        p.vx = abs(p.vx)
                    elif not p.hot and p.x + RADIUS > mid_x - 3:
                        p.x = mid_x - 3 - RADIUS
                        p.vx = -abs(p.vx)

            for f in flashes:
                f[3] += dt
            flashes = [f for f in flashes if f[3] < FLASH_MAX_AGE]

            current_max = max(p.speed() for p in particles)
            max_speed_seen = max(max_speed_seen * 0.995, current_max)  # slowly relax the ceiling

        # --- draw ---
        screen.blit(trail_surface, (0, 0))
        divider_progress = min(1.0, elapsed / DIVIDER_DROP_TIME) if divider_up or elapsed < DIVIDER_DROP_TIME else 1.0
        draw_box_and_divider(screen, small_font, divider_up, divider_progress)

        for f in flashes:
            draw_collision_flash(screen, (f[0], f[1]), f[2], f[3], FLASH_MAX_AGE)

        for p in particles:
            color = speed_color(p.speed(), max_speed_seen)
            draw_glow_circle(screen, color, (int(p.x), int(p.y)), RADIUS)

        momentum = total_momentum(particles)
        energy = total_kinetic_energy(particles)
        draw_hud(screen, font, small_font, elapsed, collisions, momentum, energy, initial_energy, paused)
        draw_histogram(screen, small_font, particles, max_speed_seen)

        pygame.display.flip()

        # Fade the trail surface toward the background each frame instead of a
        # hard clear, so recent motion leaves a soft, glowing streak behind it.
        trail_surface.fill(BG_COLOR)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
