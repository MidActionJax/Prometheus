"""
N-Body Gravity Simulation
--------------------------
A small "solar system" of bodies that pull on EVERY other body at once
(true N-body gravity, not just orbiting a fixed sun). Nothing is scripted:
each frame just sums up Newton's law of gravitation between every pair of
bodies and lets the resulting motion play out, which is what produces the
looping, braided orbital trails you see build up over time.

Controls:
  Click               - fling a new glowing body into the system from your cursor
  R                   - reset to a fresh random system
  SPACE               - pause / resume
  ESC / close window  - quit

Run with: python gravity_nbody.py
Requires: pygame  (pip install pygame)
"""

import os
import math
import random
import pygame

# --- Config -------------------------------------------------------------
SCREEN_WIDTH = 1100
SCREEN_HEIGHT = 750

NUM_BODIES = 7
G = 4000.0          # gravitational constant, tuned for a good-looking sim (not real-world units)
SOFTENING = 18.0     # prevents force from exploding when two bodies get very close
TRAIL_ALPHA = 18     # lower = longer, more visible trails
MAX_TRAIL_POINTS = 90

BG_COLOR = (5, 4, 12)
TEXT_COLOR = (215, 225, 255)
HINT_COLOR = (120, 130, 170)

# Neon palette bodies are assigned from, so every system reads as colorful
# rather than everything being the same shade.
NEON_COLORS = [
    (0, 255, 220),    # cyan
    (255, 40, 200),   # magenta
    (255, 230, 60),   # yellow
    (120, 255, 120),  # green
    (140, 120, 255),  # violet
    (255, 130, 60),   # orange
    (60, 180, 255),   # electric blue
]


def glow_color(base_color, speed, max_speed):
    """Blend a body's base neon color toward hot white as it speeds up,
    so fast-moving bodies visually 'flare' during close gravitational passes."""
    t = max(0.0, min(1.0, speed / max_speed))
    white = (255, 255, 255)
    return tuple(int(base_color[i] + (white[i] - base_color[i]) * t * 0.6) for i in range(3))


class Body:
    def __init__(self, x, y, vx, vy, mass, color):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.mass = mass
        self.radius = 4 + math.sqrt(mass) * 0.9
        self.color = color
        self.trail = []  # list of (x, y) points, most recent last

    def apply_gravity_from(self, others, dt):
        ax = 0.0
        ay = 0.0
        for other in others:
            if other is self:
                continue
            dx = other.x - self.x
            dy = other.y - self.y
            dist_sq = dx * dx + dy * dy + SOFTENING * SOFTENING
            dist = math.sqrt(dist_sq)
            # Newton's law of gravitation: F = G * m1 * m2 / r^2
            # acceleration on self = F / self.mass = G * other.mass / r^2
            force = G * other.mass / dist_sq
            ax += force * dx / dist
            ay += force * dy / dist
        self.vx += ax * dt
        self.vy += ay * dt

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt

        self.trail.append((self.x, self.y))
        if len(self.trail) > MAX_TRAIL_POINTS:
            self.trail.pop(0)

    def speed(self):
        return math.hypot(self.vx, self.vy)

    def draw_trail(self, surface, max_speed):
        if len(self.trail) < 2:
            return
        n = len(self.trail)
        for i in range(1, n):
            # fade the trail from transparent (old) to bright (recent)
            t = i / n
            color = glow_color(self.color, self.speed(), max_speed)
            faded = tuple(int(c * (0.15 + 0.65 * t)) for c in color)
            width = max(1, int(2 * t))
            pygame.draw.line(surface, faded, self.trail[i - 1], self.trail[i], width)

    def draw(self, surface, max_speed):
        color = glow_color(self.color, self.speed(), max_speed)
        pos = (int(self.x), int(self.y))
        # Fake a soft "glow" by layering translucent circles of shrinking
        # radius and rising alpha on a per-body glow surface, then blit it.
        glow_r = int(self.radius * 4)
        glow_surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
        for layer in range(4, 0, -1):
            alpha = int(55 / layer)
            r = int(self.radius * (1 + layer * 0.9))
            pygame.draw.circle(glow_surf, (*color, alpha), (glow_r, glow_r), r)
        surface.blit(glow_surf, (pos[0] - glow_r, pos[1] - glow_r), special_flags=pygame.BLEND_RGBA_ADD)
        pygame.draw.circle(surface, color, pos, int(self.radius))
        pygame.draw.circle(surface, (255, 255, 255), pos, max(1, int(self.radius * 0.35)))


def make_system():
    bodies = []
    cx, cy = SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2

    # One heavy anchor body near the center so the system has something to
    # orbit, plus several lighter bodies scattered around it with tangential
    # velocity so they start in roughly stable-ish, chaotic orbits.
    bodies.append(Body(cx, cy, 0, 0, mass=900, color=(255, 240, 200)))

    for i in range(NUM_BODIES - 1):
        angle = random.uniform(0, math.tau)
        dist = random.uniform(90, 300)
        x = cx + math.cos(angle) * dist
        y = cy + math.sin(angle) * dist
        mass = random.uniform(8, 40)

        # Rough tangential velocity for a quasi-circular starting orbit
        # (not exact, since with N>2 bodies it will drift and get chaotic
        # almost immediately -- that unpredictability is the whole point).
        orbital_speed = math.sqrt(G * 900 / dist) * random.uniform(0.75, 1.15)
        tangent_angle = angle + math.pi / 2
        vx = math.cos(tangent_angle) * orbital_speed
        vy = math.sin(tangent_angle) * orbital_speed

        color = NEON_COLORS[i % len(NEON_COLORS)]
        bodies.append(Body(x, y, vx, vy, mass, color))

    return bodies


def spawn_body_at(x, y):
    mass = random.uniform(10, 30)
    angle = random.uniform(0, math.tau)
    speed = random.uniform(20, 60)
    color = random.choice(NEON_COLORS)
    return Body(x, y, math.cos(angle) * speed, math.sin(angle) * speed, mass, color)


def draw_hud(surface, font, small_font, body_count, elapsed_seconds, avg_speed, paused):
    box_w, box_h = 210, 90
    hud_surf = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
    pygame.draw.rect(hud_surf, (10, 10, 25, 165), (0, 0, box_w, box_h), border_radius=8)
    pygame.draw.rect(hud_surf, (80, 90, 140, 200), (0, 0, box_w, box_h), width=1, border_radius=8)
    surface.blit(hud_surf, (14, 14))

    lines = [
        (f"Bodies: {body_count}", TEXT_COLOR),
        (f"Avg speed: {avg_speed:.1f}", TEXT_COLOR),
        (f"Time: {elapsed_seconds:.1f}s", TEXT_COLOR),
    ]
    y = 22
    for text, color in lines:
        surface.blit(font.render(text, True, color), (26, y))
        y += 24

    if paused:
        surface.blit(small_font.render("PAUSED", True, (255, 230, 60)), (26, y))

    hint = "Click: add body   R: reset   SPACE: pause"
    surface.blit(small_font.render(hint, True, HINT_COLOR), (14, SCREEN_HEIGHT - 26))


def main():
    pygame.init()
    pygame.display.set_caption("N-Body Gravity Simulation")
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pygame.time.Clock()

    font = pygame.font.SysFont("consolas", 18)
    small_font = pygame.font.SysFont("consolas", 14)

    trail_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    trail_surface.set_alpha(TRAIL_ALPHA)
    trail_surface.fill(BG_COLOR)

    bodies = make_system()
    paused = False
    frame_count = 0
    start_ticks = pygame.time.get_ticks()

    # Headless self-test: auto-quit after a bounded number of frames when
    # SDL_VIDEODRIVER=dummy is set, so this script can be verified without
    # a real display.
    headless_test = os.environ.get("SDL_VIDEODRIVER") == "dummy"
    headless_frame_limit = 240

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_r:
                    bodies = make_system()
                elif event.key == pygame.K_SPACE:
                    paused = not paused
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = pygame.mouse.get_pos()
                bodies.append(spawn_body_at(mx, my))

        screen.blit(trail_surface, (0, 0))

        if not paused:
            dt = 1.0 / 60.0
            for body in bodies:
                body.apply_gravity_from(bodies, dt)
            for body in bodies:
                body.update(dt)

        max_speed = max((b.speed() for b in bodies), default=1.0)
        max_speed = max(max_speed, 1.0)

        for body in bodies:
            body.draw_trail(screen, max_speed)
        for body in bodies:
            body.draw(screen, max_speed)

        avg_speed = sum(b.speed() for b in bodies) / len(bodies) if bodies else 0.0
        elapsed_seconds = (pygame.time.get_ticks() - start_ticks) / 1000.0
        draw_hud(screen, font, small_font, len(bodies), elapsed_seconds, avg_speed, paused)

        pygame.display.flip()
        clock.tick(60)
        frame_count += 1

        if headless_test and frame_count >= headless_frame_limit:
            running = False

    pygame.quit()


if __name__ == "__main__":
    main()
