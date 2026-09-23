"""
Electric Field Lines & Coulomb's Law
-------------------------------------
A live electrostatics sandbox. A handful of fixed point charges (magenta =
positive, cyan = negative) generate an electric field. Two things make that
invisible field visible at once:

  1. Field LINES - traced by starting just outside each positive charge and
     repeatedly stepping in the direction of the local electric field vector
     (computed by summing Coulomb's law over every charge - the
     "superposition principle"). Lines end when they're pulled into a
     negative charge, or fade out once they leave the screen.
  2. Test PARTICLES - small positive "test charges" that feel the real
     Coulomb force (F = k*q1*q2 / r^2) from every fixed charge and get
     pushed/pulled around exactly like the field lines predict, leaving
     glowing trails behind them.

Nothing about the motion is scripted - both the line shapes and the particle
paths fall directly out of summing an inverse-square law over every charge
on screen, every frame.

Controls:
  Left click          - add a positive charge (magenta) at the cursor
  Right click          - add a negative charge (cyan) at the cursor
  R                    - reset to the default charge arrangement
  SPACE                - pause / resume
  ESC / close window   - quit

Run with: python electric_field_lines.py
Requires: pygame  (pip install pygame)
"""

import os
import math
import random
import pygame

# --- Config --------------------------------------------------------------
SCREEN_WIDTH = 1100
SCREEN_HEIGHT = 750

COULOMB_K = 55000.0     # Coulomb's constant, tuned for a good-looking sim (not SI units)
SOFTENING = 14.0        # prevents force/field from exploding at very short range
MAX_CHARGES = 10

NUM_FIELD_LINES_PER_CHARGE = 20
FIELD_LINE_STEP = 4.5
FIELD_LINE_MAX_STEPS = 260
ABSORB_RADIUS = 16.0     # distance at which a line/particle is "captured" by an opposite charge

NUM_PARTICLES = 90
PARTICLE_MASS = 1.0
PARTICLE_DAMPING = 0.35   # velocity bleed-off per second, keeps orbits from flinging to infinity
PARTICLE_MAX_SPEED = 480.0

TRAIL_ALPHA = 30          # lower = longer-lived trails
BG_COLOR = (5, 4, 12)
TEXT_COLOR = (215, 225, 255)
HINT_COLOR = (120, 130, 170)

POSITIVE_COLOR = (255, 40, 200)   # magenta
NEGATIVE_COLOR = (40, 220, 255)   # cyan
PARTICLE_BASE_COLOR = (255, 230, 90)  # warm gold test charges

# Color stops used to paint field lines from weak field (dim indigo) to a
# very strong field close to a charge (hot white). Field strength is mapped
# on a LOG scale before interpolating, since Coulomb's law falls off as
# 1/r^2 and a linear map would make almost the whole line look "weak".
FIELD_COLOR_STOPS = [
    (20, 15, 60),      # very weak - near-invisible deep indigo
    (70, 40, 160),      # weak - violet
    (180, 40, 200),     # medium - magenta-violet
    (255, 60, 140),     # strong - hot pink
    (255, 220, 120),    # very strong - warm white-gold
]


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_color(c1, c2, t):
    return tuple(int(lerp(c1[i], c2[i], t)) for i in range(3))


def field_color(magnitude, ref_magnitude):
    """Map a field magnitude to a color along FIELD_COLOR_STOPS using a log
    scale, so both the near-charge hotspots and the faint far-field lines
    are visually distinguishable instead of everything looking the same."""
    if ref_magnitude <= 0:
        ref_magnitude = 1.0
    t = math.log10(1.0 + magnitude) / math.log10(1.0 + ref_magnitude)
    t = max(0.0, min(1.0, t))
    n = len(FIELD_COLOR_STOPS) - 1
    scaled = t * n
    i = min(int(scaled), n - 1)
    local_t = scaled - i
    return lerp_color(FIELD_COLOR_STOPS[i], FIELD_COLOR_STOPS[i + 1], local_t)


class Charge:
    """A fixed point charge. Positive charges are where field lines start;
    negative charges are where they (and particles) get absorbed."""

    def __init__(self, x, y, q):
        self.x = x
        self.y = y
        self.q = q  # signed charge magnitude
        self.radius = 10 + 6 * math.sqrt(abs(q))
        self.color = POSITIVE_COLOR if q > 0 else NEGATIVE_COLOR

    def draw(self, surface):
        pos = (int(self.x), int(self.y))
        glow_r = int(self.radius * 3.2)
        glow_surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
        for layer in range(4, 0, -1):
            alpha = int(70 / layer)
            r = int(self.radius * (1 + layer * 0.75))
            pygame.draw.circle(glow_surf, (*self.color, alpha), (glow_r, glow_r), r)
        surface.blit(glow_surf, (pos[0] - glow_r, pos[1] - glow_r), special_flags=pygame.BLEND_RGBA_ADD)
        pygame.draw.circle(surface, self.color, pos, int(self.radius))
        sign = "+" if self.q > 0 else "-"
        pygame.draw.circle(surface, (255, 255, 255), pos, max(2, int(self.radius * 0.25)))
        return sign


def field_at(x, y, charges):
    """Electric field vector (Ex, Ey) at a point, found by summing Coulomb's
    law over every charge in the scene (the superposition principle) -
    exactly the same math whether it's used to trace a field line or push a
    particle."""
    ex, ey = 0.0, 0.0
    for c in charges:
        dx = x - c.x
        dy = y - c.y
        dist_sq = dx * dx + dy * dy + SOFTENING * SOFTENING
        dist = math.sqrt(dist_sq)
        # E = k*q / r^2, pointing away from positive charges, toward negative ones
        strength = COULOMB_K * c.q / dist_sq
        ex += strength * dx / dist
        ey += strength * dy / dist
    return ex, ey


def nearest_opposite_charge(x, y, charges, want_negative):
    best = None
    best_dist = None
    for c in charges:
        if want_negative and c.q >= 0:
            continue
        if not want_negative and c.q <= 0:
            continue
        d = math.hypot(c.x - x, c.y - y)
        if best_dist is None or d < best_dist:
            best_dist = d
            best = c
    return best, best_dist


def trace_field_line(start_x, start_y, charges):
    """Walk from just outside a positive charge, always stepping in the
    direction of the local field vector, until the line either gets pulled
    into a negative charge or wanders off the edge of the screen."""
    points = [(start_x, start_y)]
    mags = []
    x, y = start_x, start_y
    for _ in range(FIELD_LINE_MAX_STEPS):
        ex, ey = field_at(x, y, charges)
        mag = math.hypot(ex, ey)
        mags.append(mag)
        if mag < 1e-6:
            break
        step = FIELD_LINE_STEP
        x += (ex / mag) * step
        y += (ey / mag) * step
        points.append((x, y))

        neg, dist = nearest_opposite_charge(x, y, charges, want_negative=True)
        if neg is not None and dist < ABSORB_RADIUS:
            break
        if x < -60 or x > SCREEN_WIDTH + 60 or y < -60 or y > SCREEN_HEIGHT + 60:
            break
    return points, mags


def generate_field_lines(charges):
    """Seed NUM_FIELD_LINES_PER_CHARGE lines evenly around every positive
    charge. Recomputed only when the charge layout changes, since the field
    shape only changes when a charge is added or reset."""
    lines = []
    positives = [c for c in charges if c.q > 0]
    for c in positives:
        for i in range(NUM_FIELD_LINES_PER_CHARGE):
            angle = (i / NUM_FIELD_LINES_PER_CHARGE) * math.tau
            sx = c.x + math.cos(angle) * (c.radius + 3)
            sy = c.y + math.sin(angle) * (c.radius + 3)
            points, mags = trace_field_line(sx, sy, charges)
            if len(points) > 2:
                lines.append((points, mags))
    return lines


class Particle:
    """A small positive test charge that feels the real Coulomb force from
    every fixed charge on screen. Its path is the field lines made kinetic:
    same underlying force law, but now with mass and momentum."""

    def __init__(self, x, y, vx, vy):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.q = 0.9
        self.trail = []

    def respawn_at_edge(self):
        edge = random.choice(["top", "bottom", "left", "right"])
        if edge == "top":
            self.x, self.y = random.uniform(0, SCREEN_WIDTH), -10
            self.vx, self.vy = random.uniform(-30, 30), random.uniform(40, 90)
        elif edge == "bottom":
            self.x, self.y = random.uniform(0, SCREEN_WIDTH), SCREEN_HEIGHT + 10
            self.vx, self.vy = random.uniform(-30, 30), random.uniform(-90, -40)
        elif edge == "left":
            self.x, self.y = -10, random.uniform(0, SCREEN_HEIGHT)
            self.vx, self.vy = random.uniform(40, 90), random.uniform(-30, 30)
        else:
            self.x, self.y = SCREEN_WIDTH + 10, random.uniform(0, SCREEN_HEIGHT)
            self.vx, self.vy = random.uniform(-90, -40), random.uniform(-30, 30)
        self.trail.clear()

    def update(self, dt, charges):
        ex, ey = field_at(self.x, self.y, charges)
        fx, fy = self.q * ex, self.q * ey
        ax, ay = fx / PARTICLE_MASS, fy / PARTICLE_MASS

        self.vx += ax * dt
        self.vy += ay * dt
        # Light damping so particles settle into flowing along field lines
        # rather than permanently accelerating into a nearby charge.
        damp = max(0.0, 1.0 - PARTICLE_DAMPING * dt)
        self.vx *= damp
        self.vy *= damp

        speed = math.hypot(self.vx, self.vy)
        if speed > PARTICLE_MAX_SPEED:
            scale = PARTICLE_MAX_SPEED / speed
            self.vx *= scale
            self.vy *= scale

        self.x += self.vx * dt
        self.y += self.vy * dt

        self.trail.append((self.x, self.y))
        if len(self.trail) > 26:
            self.trail.pop(0)

        neg, dist = nearest_opposite_charge(self.x, self.y, charges, want_negative=True)
        absorbed = neg is not None and dist < ABSORB_RADIUS
        off_screen = self.x < -40 or self.x > SCREEN_WIDTH + 40 or self.y < -40 or self.y > SCREEN_HEIGHT + 40
        if absorbed or off_screen:
            self.respawn_at_edge()

    def speed(self):
        return math.hypot(self.vx, self.vy)

    def draw_trail(self, surface):
        n = len(self.trail)
        if n < 2:
            return
        for i in range(1, n):
            t = i / n
            faded = tuple(int(c * (0.10 + 0.55 * t)) for c in PARTICLE_BASE_COLOR)
            width = max(1, int(2 * t))
            pygame.draw.line(surface, faded, self.trail[i - 1], self.trail[i], width)

    def draw(self, surface):
        speed_t = max(0.0, min(1.0, self.speed() / PARTICLE_MAX_SPEED))
        color = lerp_color(PARTICLE_BASE_COLOR, (255, 255, 255), speed_t * 0.7)
        pos = (int(self.x), int(self.y))
        glow_r = 10
        glow_surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*color, 90), (glow_r, glow_r), glow_r)
        surface.blit(glow_surf, (pos[0] - glow_r, pos[1] - glow_r), special_flags=pygame.BLEND_RGBA_ADD)
        pygame.draw.circle(surface, color, pos, 3)


def make_default_charges():
    cx, cy = SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2
    return [
        Charge(cx - 180, cy, 3.0),
        Charge(cx + 180, cy, -3.0),
        Charge(cx, cy - 220, 1.4),
    ]


def make_particles():
    particles = []
    for _ in range(NUM_PARTICLES):
        p = Particle(0, 0, 0, 0)
        p.respawn_at_edge()
        # scatter their initial progress so they don't all arrive in one wave
        for _ in range(random.randint(0, 40)):
            p.x += p.vx * (1 / 60.0)
            p.y += p.vy * (1 / 60.0)
        particles.append(p)
    return particles


def draw_field_lines(surface, lines, ref_magnitude, phase):
    """Draw each traced field line as a faded, color-graded polyline, plus a
    small bright pulse dot that travels along it over time so static field
    geometry still reads as 'live' rather than a printed diagram."""
    for points, mags in lines:
        n = len(points)
        for i in range(1, n):
            mag = mags[i - 1] if i - 1 < len(mags) else mags[-1]
            color = field_color(mag, ref_magnitude)
            faded = tuple(int(c * 0.55) for c in color)
            pygame.draw.line(surface, faded, points[i - 1], points[i], 2)

        if n > 4:
            pulse_pos = (phase % 1.0) * (n - 1)
            idx = int(pulse_pos)
            frac = pulse_pos - idx
            if idx + 1 < n:
                px = lerp(points[idx][0], points[idx + 1][0], frac)
                py = lerp(points[idx][1], points[idx + 1][1], frac)
                pygame.draw.circle(surface, (255, 240, 200), (int(px), int(py)), 3)


def draw_hud(surface, font, small_font, charge_count, line_count, elapsed_seconds, paused):
    box_w, box_h = 230, 90
    hud_surf = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
    pygame.draw.rect(hud_surf, (10, 10, 25, 165), (0, 0, box_w, box_h), border_radius=8)
    pygame.draw.rect(hud_surf, (80, 90, 140, 200), (0, 0, box_w, box_h), width=1, border_radius=8)
    surface.blit(hud_surf, (14, 14))

    lines = [
        (f"Charges: {charge_count}", TEXT_COLOR),
        (f"Field lines: {line_count}", TEXT_COLOR),
        (f"Time: {elapsed_seconds:.1f}s", TEXT_COLOR),
    ]
    y = 22
    for text, color in lines:
        surface.blit(font.render(text, True, color), (26, y))
        y += 24

    if paused:
        surface.blit(small_font.render("PAUSED", True, (255, 230, 60)), (26, y))

    hint = "Left click: + charge   Right click: - charge   R: reset   SPACE: pause"
    surface.blit(small_font.render(hint, True, HINT_COLOR), (14, SCREEN_HEIGHT - 26))


def main():
    pygame.init()
    pygame.display.set_caption("Electric Field Lines & Coulomb's Law")
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pygame.time.Clock()

    font = pygame.font.SysFont("consolas", 18)
    small_font = pygame.font.SysFont("consolas", 14)

    trail_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    trail_surface.set_alpha(TRAIL_ALPHA)
    trail_surface.fill(BG_COLOR)

    charges = make_default_charges()
    particles = make_particles()
    field_lines = generate_field_lines(charges)
    # Reference magnitude for color scaling: the strongest field found right
    # next to any charge, so the color gradient always spans the current scene.
    ref_magnitude = max((m for _, mags in field_lines for m in mags), default=1.0)

    paused = False
    phase = 0.0
    frame_count = 0
    start_ticks = pygame.time.get_ticks()

    # Headless self-test: auto-quit after a bounded number of frames when
    # SDL_VIDEODRIVER=dummy is set, so this script can be verified without a
    # real display.
    headless_test = os.environ.get("SDL_VIDEODRIVER") == "dummy"
    headless_frame_limit = 240

    running = True
    while running:
        charges_changed = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_r:
                    charges = make_default_charges()
                    charges_changed = True
                elif event.key == pygame.K_SPACE:
                    paused = not paused
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if len(charges) < MAX_CHARGES:
                    mx, my = pygame.mouse.get_pos()
                    if event.button == 1:
                        charges.append(Charge(mx, my, random.uniform(1.5, 2.5)))
                        charges_changed = True
                    elif event.button == 3:
                        charges.append(Charge(mx, my, -random.uniform(1.5, 2.5)))
                        charges_changed = True

        if charges_changed:
            field_lines = generate_field_lines(charges)
            ref_magnitude = max((m for _, mags in field_lines for m in mags), default=1.0)

        screen.blit(trail_surface, (0, 0))

        if not paused:
            dt = 1.0 / 60.0
            for p in particles:
                p.update(dt, charges)
            phase += dt * 0.18

        draw_field_lines(screen, field_lines, ref_magnitude, phase)
        for p in particles:
            p.draw_trail(screen)
        for p in particles:
            p.draw(screen)
        for c in charges:
            c.draw(screen)

        elapsed_seconds = (pygame.time.get_ticks() - start_ticks) / 1000.0
        draw_hud(screen, font, small_font, len(charges), len(field_lines), elapsed_seconds, paused)

        pygame.display.flip()
        clock.tick(60)
        frame_count += 1

        if headless_test and frame_count >= headless_frame_limit:
            running = False

    pygame.quit()


if __name__ == "__main__":
    main()
