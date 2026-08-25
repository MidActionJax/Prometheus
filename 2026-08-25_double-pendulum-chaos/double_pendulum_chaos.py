"""
Double Pendulum Chaos: The Butterfly Effect, Visualized
--------------------------------------------------------
A fan of double pendulums, all released from ANGLES that differ by a
fraction of a degree, swinging under the exact same physics (real
Lagrangian double-pendulum dynamics, integrated with RK4). For the first
second or two they swing together almost as one. Then they visibly tear
apart into total chaos -- a live demonstration of sensitive dependence on
initial conditions, the defining feature of a chaotic system.

Nothing about the divergence is scripted or faked: every pendulum obeys
the identical equations of motion, starting from a near-identical state.
The fact that they end up in wildly different places is the physics
itself, not an animation trick.

Controls:
  R                   - reset with a fresh random base angle
  UP / DOWN           - widen / narrow the starting-angle spread (epsilon)
  SPACE               - pause / resume
  ESC / close window  - quit

Run with: python double_pendulum_chaos.py
Requires: pygame  (pip install pygame)
"""

import os
import math
import random
import pygame

# --- Config -------------------------------------------------------------
SCREEN_WIDTH = 1100
SCREEN_HEIGHT = 750

PIVOT = (SCREEN_WIDTH // 2, 190)

NUM_PENDULUMS = 7
L1_M = 1.0          # upper rod length, meters
L2_M = 1.0          # lower rod length, meters
M1 = 1.0            # upper bob mass, kg
M2 = 1.0            # lower bob mass, kg
G = 9.81            # real gravitational acceleration, m/s^2
SCALE = 150.0       # pixels per meter, for drawing only

SUBSTEPS = 4        # RK4 substeps per rendered frame, for numerical stability
TRAIL_MAXLEN = 260  # points kept per pendulum's chaos trail
TRAIL_ALPHA = 22    # lower = longer-lived fading trails

BG_COLOR = (4, 5, 14)
TEXT_COLOR = (215, 225, 255)
HINT_COLOR = (120, 130, 170)

DEFAULT_EPSILON = 0.0015  # radians of starting-angle spread between neighbors

# Neon fan palette: each pendulum gets its own hue so the "family" of
# trajectories reads as a rainbow fan tearing apart, not one blob.
NEON_COLORS = [
    (0, 255, 220),    # cyan
    (60, 180, 255),   # electric blue
    (140, 120, 255),  # violet
    (255, 40, 200),   # magenta
    (255, 120, 60),   # orange
    (255, 230, 60),   # yellow
    (120, 255, 120),  # green
]


def derivs(state):
    """Return d(state)/dt for the real double-pendulum equations of motion.

    state = (theta1, omega1, theta2, omega2), angles measured from the
    downward vertical. These are the standard Lagrangian double-pendulum
    equations for two point masses on massless rigid rods -- the same
    physics used in every textbook chaos demo.
    """
    t1, w1, t2, w2 = state
    delta = t1 - t2
    den = 2 * M1 + M2 - M2 * math.cos(2 * t1 - 2 * t2)

    num1 = (
        -G * (2 * M1 + M2) * math.sin(t1)
        - M2 * G * math.sin(t1 - 2 * t2)
        - 2 * math.sin(delta) * M2 * (w2 * w2 * L2_M + w1 * w1 * L1_M * math.cos(delta))
    )
    alpha1 = num1 / (L1_M * den)

    num2 = 2 * math.sin(delta) * (
        w1 * w1 * L1_M * (M1 + M2)
        + G * (M1 + M2) * math.cos(t1)
        + w2 * w2 * L2_M * M2 * math.cos(delta)
    )
    alpha2 = num2 / (L2_M * den)

    return (w1, alpha1, w2, alpha2)


def rk4_step(state, dt):
    """One classic 4th-order Runge-Kutta integration step.

    Double pendulums are numerically stiff near swing reversals; plain
    Euler integration visibly leaks energy and drifts. RK4 keeps the
    motion physically honest over the length of a recording.
    """

    def add_scaled(a, b, s):
        return tuple(a[i] + b[i] * s for i in range(4))

    k1 = derivs(state)
    k2 = derivs(add_scaled(state, k1, dt / 2))
    k3 = derivs(add_scaled(state, k2, dt / 2))
    k4 = derivs(add_scaled(state, k3, dt))
    return tuple(
        state[i] + (dt / 6.0) * (k1[i] + 2 * k2[i] + 2 * k3[i] + k4[i])
        for i in range(4)
    )


class Pendulum:
    def __init__(self, theta1, theta2, color):
        self.state = (theta1, 0.0, theta2, 0.0)
        self.color = color
        self.trail = []  # bob-2 positions, most recent last

    def step(self, dt, substeps):
        sub_dt = dt / substeps
        for _ in range(substeps):
            self.state = rk4_step(self.state, sub_dt)

    def positions(self):
        """Pixel positions of the pivot, bob1, and bob2."""
        t1, _, t2, _ = self.state
        x1 = PIVOT[0] + L1_M * SCALE * math.sin(t1)
        y1 = PIVOT[1] + L1_M * SCALE * math.cos(t1)
        x2 = x1 + L2_M * SCALE * math.sin(t2)
        y2 = y1 + L2_M * SCALE * math.cos(t2)
        return (x1, y1), (x2, y2)

    def angular_speed(self):
        _, w1, _, w2 = self.state
        return math.sqrt(w1 * w1 + w2 * w2)

    def record_trail(self):
        _, bob2 = self.positions()
        self.trail.append(bob2)
        if len(self.trail) > TRAIL_MAXLEN:
            self.trail.pop(0)

    def draw_trail(self, surface):
        n = len(self.trail)
        if n < 2:
            return
        for i in range(1, n):
            t = i / n  # 0 = oldest/faintest, 1 = newest/brightest
            fade = 0.08 + 0.72 * t
            faded = tuple(int(c * fade) for c in self.color)
            width = 1 if t < 0.55 else 2
            pygame.draw.line(surface, faded, self.trail[i - 1], self.trail[i], width)

    def draw(self, surface, max_speed):
        p0, p1 = PIVOT, None
        pos1, pos2 = self.positions()

        speed = self.angular_speed()
        heat = max(0.0, min(1.0, speed / max_speed))
        hot_color = tuple(
            int(self.color[i] + (255 - self.color[i]) * heat * 0.55) for i in range(3)
        )

        # Rods: soft, slightly translucent glow lines rather than bare 1px lines.
        rod_color = tuple(int(c * 0.55) for c in self.color)
        pygame.draw.line(surface, rod_color, PIVOT, pos1, 2)
        pygame.draw.line(surface, rod_color, pos1, pos2, 2)

        # Bob 1: small, dim, mostly a hinge.
        pygame.draw.circle(surface, rod_color, (int(pos1[0]), int(pos1[1])), 6)
        pygame.draw.circle(surface, self.color, (int(pos1[0]), int(pos1[1])), 4)

        # Bob 2: the chaotic bob. Additive-blend glow sized/colored by how
        # fast this pendulum is currently swinging -- a visible "flare"
        # during each fast pass through the bottom of the arc.
        glow_r = int(10 + 16 * heat)
        glow_surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
        for r in range(glow_r, 0, -2):
            a = int(70 * (1 - r / glow_r))
            pygame.draw.circle(glow_surf, (*hot_color, a), (glow_r, glow_r), r)
        surface.blit(
            glow_surf,
            (pos2[0] - glow_r, pos2[1] - glow_r),
            special_flags=pygame.BLEND_RGBA_ADD,
        )
        pygame.draw.circle(surface, hot_color, (int(pos2[0]), int(pos2[1])), 7)
        pygame.draw.circle(surface, (255, 255, 255), (int(pos2[0]), int(pos2[1])), 2)


def make_fan(base_theta1, base_theta2, epsilon):
    """Build NUM_PENDULUMS pendulums whose starting angles differ from each
    other by tiny, evenly-spaced increments of epsilon radians."""
    pendulums = []
    mid = (NUM_PENDULUMS - 1) / 2.0
    for i in range(NUM_PENDULUMS):
        offset = (i - mid) * epsilon
        color = NEON_COLORS[i % len(NEON_COLORS)]
        pendulums.append(Pendulum(base_theta1 + offset, base_theta2, color))
    return pendulums


def random_base_angles():
    # High-energy, off-vertical starts swing vigorously and diverge fast --
    # near-straight-down starts barely move and take too long to show chaos.
    base_theta1 = random.uniform(1.6, 2.6)   # radians, past horizontal
    base_theta2 = random.uniform(-2.6, 2.6)
    return base_theta1, base_theta2


def draw_hud(surface, font, small_font, elapsed_seconds, epsilon, divergence_deg, paused, steps):
    box_w, box_h = 300, 130
    hud_surf = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
    pygame.draw.rect(hud_surf, (10, 12, 24, 190), (0, 0, box_w, box_h), border_radius=10)
    pygame.draw.rect(hud_surf, (0, 255, 220, 90), (0, 0, box_w, box_h), width=1, border_radius=10)
    surface.blit(hud_surf, (14, 14))

    lines = [
        (f"time: {elapsed_seconds:5.1f}s   steps: {steps}", TEXT_COLOR),
        (f"start-angle spread: {math.degrees(epsilon):.3f} deg", (140, 220, 255)),
        (f"bob-2 divergence: {divergence_deg:6.1f} deg", (255, 210, 90)),
        (f"pendulums: {NUM_PENDULUMS}   integrator: RK4", HINT_COLOR),
    ]
    y = 24
    for text, color in lines:
        surface.blit(font.render(text, True, color), (26, y))
        y += 22

    if paused:
        surface.blit(small_font.render("PAUSED", True, (255, 230, 60)), (26, y + 4))

    hint = "R reset | UP/DOWN spread | SPACE pause"
    surface.blit(small_font.render(hint, True, HINT_COLOR), (14, SCREEN_HEIGHT - 26))


def main():
    pygame.init()
    pygame.display.set_caption("Double Pendulum Chaos")
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pygame.time.Clock()

    font = pygame.font.SysFont("consolas", 17)
    small_font = pygame.font.SysFont("consolas", 14)

    trail_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    trail_surface.set_alpha(TRAIL_ALPHA)
    trail_surface.fill(BG_COLOR)

    epsilon = DEFAULT_EPSILON
    base_theta1, base_theta2 = random_base_angles()
    pendulums = make_fan(base_theta1, base_theta2, epsilon)

    paused = False
    frame_count = 0
    steps = 0
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
                    base_theta1, base_theta2 = random_base_angles()
                    pendulums = make_fan(base_theta1, base_theta2, epsilon)
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_UP:
                    epsilon = min(epsilon * 1.6, 0.2)
                    pendulums = make_fan(base_theta1, base_theta2, epsilon)
                elif event.key == pygame.K_DOWN:
                    epsilon = max(epsilon / 1.6, 0.0002)
                    pendulums = make_fan(base_theta1, base_theta2, epsilon)

        screen.blit(trail_surface, (0, 0))

        if not paused:
            dt = 1.0 / 60.0
            for p in pendulums:
                p.step(dt, SUBSTEPS)
                p.record_trail()
            steps += 1

        max_speed = max((p.angular_speed() for p in pendulums), default=1.0)
        max_speed = max(max_speed, 1.0)

        for p in pendulums:
            p.draw_trail(screen)
        for p in pendulums:
            p.draw(screen, max_speed)

        # Divergence stat: angular separation in degrees between the
        # first and last pendulum in the fan -- the single number that
        # makes the chaos "provable" rather than just pretty.
        t2_first = pendulums[0].state[2]
        t2_last = pendulums[-1].state[2]
        divergence_deg = abs(math.degrees(t2_first - t2_last)) % 360
        if divergence_deg > 180:
            divergence_deg = 360 - divergence_deg

        elapsed_seconds = (pygame.time.get_ticks() - start_ticks) / 1000.0
        draw_hud(screen, font, small_font, elapsed_seconds, epsilon, divergence_deg, paused, steps)

        pygame.display.flip()
        clock.tick(60)
        frame_count += 1

        if headless_test and frame_count >= headless_frame_limit:
            running = False

    pygame.quit()


if __name__ == "__main__":
    main()
