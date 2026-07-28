"""
Boids Flocking Simulation
--------------------------
A classic emergent-behavior demo: dozens of simple "boid" agents follow just
three local rules (separation, alignment, cohesion) with no central
controller, yet the whole flock self-organizes into fluid, lifelike motion.

Controls:
  Click and hold (left mouse button) - spawn an attractor; boids steer toward it
  R                                  - reset the flock
  ESC / close window                 - quit

Run with: python boids_flocking.py
Requires: pygame  (pip install pygame)
"""

import os
import math
import random
import pygame

# --- Config -----------------------------------------------------------
SCREEN_WIDTH = 1100
SCREEN_HEIGHT = 720
NUM_BOIDS = 90

MAX_SPEED = 4.5
MAX_FORCE = 0.09

PERCEPTION_RADIUS = 60      # how far a boid "sees" its neighbors
SEPARATION_RADIUS = 24      # min comfortable distance between boids

SEPARATION_WEIGHT = 1.6
ALIGNMENT_WEIGHT = 1.0
COHESION_WEIGHT = 1.0
ATTRACTOR_WEIGHT = 1.4

TRAIL_ALPHA = 40             # lower = longer motion trails

# --- Neon color palette -------------------------------------------------
BG_COLOR = (6, 6, 14)
NEON_CYAN = (0, 255, 220)
NEON_MAGENTA = (255, 40, 200)
NEON_GREEN = (80, 255, 120)
NEON_YELLOW = (255, 230, 60)
TEXT_COLOR = (220, 230, 255)
ATTRACTOR_COLOR = (255, 255, 255)

NEON_PALETTE = [NEON_CYAN, NEON_MAGENTA, NEON_GREEN, NEON_YELLOW]


def speed_to_color(speed, max_speed):
    """Map a boid's current speed to a neon color along the palette
    so fast-moving boids read visually 'hotter' than slow ones."""
    t = max(0.0, min(1.0, speed / max_speed))
    # interpolate cyan (slow) -> magenta (fast)
    c1 = NEON_CYAN
    c2 = NEON_MAGENTA
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    )


class Vector2:
    """Minimal 2D vector helper (avoids an external dependency)."""

    __slots__ = ("x", "y")

    def __init__(self, x=0.0, y=0.0):
        self.x = x
        self.y = y

    def __add__(self, other):
        return Vector2(self.x + other.x, self.y + other.y)

    def __sub__(self, other):
        return Vector2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar):
        return Vector2(self.x * scalar, self.y * scalar)

    def length(self):
        return math.hypot(self.x, self.y)

    def normalized(self):
        length = self.length()
        if length == 0:
            return Vector2(0, 0)
        return Vector2(self.x / length, self.y / length)

    def limit(self, max_len):
        length = self.length()
        if length > max_len and length > 0:
            scale = max_len / length
            self.x *= scale
            self.y *= scale
        return self


class Boid:
    """A single flocking agent following separation, alignment and cohesion."""

    def __init__(self, x, y):
        self.position = Vector2(x, y)
        angle = random.uniform(0, math.tau)
        speed = random.uniform(MAX_SPEED * 0.4, MAX_SPEED)
        self.velocity = Vector2(math.cos(angle) * speed, math.sin(angle) * speed)
        self.acceleration = Vector2(0, 0)
        self.trail = []

    def edges(self):
        """Wrap around screen edges so the flock stays on screen forever."""
        if self.position.x < 0:
            self.position.x = SCREEN_WIDTH
        elif self.position.x > SCREEN_WIDTH:
            self.position.x = 0
        if self.position.y < 0:
            self.position.y = SCREEN_HEIGHT
        elif self.position.y > SCREEN_HEIGHT:
            self.position.y = 0

    def steer_towards(self, desired):
        """Reynolds steering: desired_velocity - current_velocity, force-limited."""
        desired = desired.normalized() * MAX_SPEED
        steer = desired - self.velocity
        steer.limit(MAX_FORCE)
        return steer

    def flock(self, boids, attractor):
        separation = Vector2(0, 0)
        alignment = Vector2(0, 0)
        cohesion = Vector2(0, 0)
        total = 0

        for other in boids:
            if other is self:
                continue
            diff = self.position - other.position
            dist = diff.length()
            if dist < PERCEPTION_RADIUS and dist > 0:
                total += 1
                alignment = alignment + other.velocity
                cohesion = cohesion + other.position
                if dist < SEPARATION_RADIUS:
                    # push away harder the closer the neighbor is
                    separation = separation + (diff.normalized() * (1.0 / dist))

        if total > 0:
            alignment = alignment * (1.0 / total)
            alignment_force = self.steer_towards(alignment) * ALIGNMENT_WEIGHT

            cohesion = cohesion * (1.0 / total)
            cohesion_dir = cohesion - self.position
            cohesion_force = self.steer_towards(cohesion_dir) * COHESION_WEIGHT

            if separation.length() > 0:
                separation_force = self.steer_towards(separation) * SEPARATION_WEIGHT
            else:
                separation_force = Vector2(0, 0)

            self.acceleration = (
                self.acceleration + alignment_force + cohesion_force + separation_force
            )

        if attractor is not None:
            towards = attractor - self.position
            if towards.length() > 4:
                attractor_force = self.steer_towards(towards) * ATTRACTOR_WEIGHT
                self.acceleration = self.acceleration + attractor_force

    def update(self):
        self.velocity = self.velocity + self.acceleration
        self.velocity.limit(MAX_SPEED)
        self.position = self.position + self.velocity
        self.acceleration = Vector2(0, 0)

        self.trail.append((self.position.x, self.position.y))
        if len(self.trail) > 6:
            self.trail.pop(0)

    def draw(self, surface):
        speed = self.velocity.length()
        color = speed_to_color(speed, MAX_SPEED)

        heading = math.atan2(self.velocity.y, self.velocity.x)
        size = 7
        p1 = (
            self.position.x + math.cos(heading) * size * 1.6,
            self.position.y + math.sin(heading) * size * 1.6,
        )
        p2 = (
            self.position.x + math.cos(heading + 2.5) * size,
            self.position.y + math.sin(heading + 2.5) * size,
        )
        p3 = (
            self.position.x + math.cos(heading - 2.5) * size,
            self.position.y + math.sin(heading - 2.5) * size,
        )
        pygame.draw.polygon(surface, color, [p1, p2, p3])


def make_flock():
    return [
        Boid(random.uniform(0, SCREEN_WIDTH), random.uniform(0, SCREEN_HEIGHT))
        for _ in range(NUM_BOIDS)
    ]


def draw_hud(surface, font, small_font, frame_count, elapsed_seconds, avg_speed, attractor_active):
    lines = [
        f"Boids: {NUM_BOIDS}",
        f"Avg Speed: {avg_speed:.2f}",
        f"Time: {elapsed_seconds:.1f}s",
    ]
    y = 14
    for line in lines:
        text_surface = font.render(line, True, TEXT_COLOR)
        surface.blit(text_surface, (16, y))
        y += 26

    hint = "Click + hold: attract flock   |   R: reset   |   ESC: quit"
    hint_surface = small_font.render(hint, True, (150, 160, 190))
    surface.blit(hint_surface, (16, SCREEN_HEIGHT - 28))

    if attractor_active:
        beacon = small_font.render("ATTRACTOR ACTIVE", True, NEON_YELLOW)
        surface.blit(beacon, (SCREEN_WIDTH - beacon.get_width() - 16, 14))


def main():
    pygame.init()
    pygame.display.set_caption("Boids Flocking Simulation")
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pygame.time.Clock()

    font = pygame.font.SysFont("consolas", 20)
    small_font = pygame.font.SysFont("consolas", 15)

    # A translucent surface drawn each frame (instead of a hard clear)
    # creates soft motion trails behind every boid.
    trail_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    trail_surface.set_alpha(TRAIL_ALPHA)
    trail_surface.fill(BG_COLOR)

    flock = make_flock()

    frame_count = 0
    start_ticks = pygame.time.get_ticks()

    # Headless self-test mode: when SDL_VIDEODRIVER=dummy is set (used to
    # verify this script runs cleanly without a real display), auto-quit
    # after a couple hundred frames instead of running forever.
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
                    flock = make_flock()

        attractor = None
        if pygame.mouse.get_pressed()[0]:
            mx, my = pygame.mouse.get_pos()
            attractor = Vector2(mx, my)

        screen.blit(trail_surface, (0, 0))

        total_speed = 0.0
        for boid in flock:
            boid.flock(flock, attractor)
            boid.update()
            boid.edges()
            boid.draw(screen)
            total_speed += boid.velocity.length()

        if attractor is not None:
            pygame.draw.circle(screen, ATTRACTOR_COLOR, (int(attractor.x), int(attractor.y)), 5)
            pygame.draw.circle(screen, NEON_YELLOW, (int(attractor.x), int(attractor.y)), 14, width=1)

        avg_speed = total_speed / len(flock) if flock else 0.0
        elapsed_seconds = (pygame.time.get_ticks() - start_ticks) / 1000.0
        draw_hud(screen, font, small_font, frame_count, elapsed_seconds, avg_speed, attractor is not None)

        pygame.display.flip()
        clock.tick(60)
        frame_count += 1

        if headless_test and frame_count >= headless_frame_limit:
            running = False

    pygame.quit()


if __name__ == "__main__":
    main()
