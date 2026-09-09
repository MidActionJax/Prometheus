"""
Spring-Mass-Damper: Damping Styles & Resonance
------------------------------------------------
Four real damped-harmonic-oscillator systems (m*x'' + c*x' + k*x = F(t)),
integrated live with RK4, running side by side so you can SEE the
difference between:

    Lane 1 (cyan)    - underdamped    (zeta < 1)   -> oscillates while decaying
    Lane 2 (green)   - critically damped (zeta = 1) -> fastest return, no overshoot
    Lane 3 (magenta) - overdamped     (zeta > 1)    -> slow, sluggish return
    Lane 4 (gold)    - driven, lightly damped, with the drive frequency
                        slowly swept across the natural frequency -> shows
                        RESONANCE: amplitude swells dramatically as the
                        drive frequency passes through omega0 = sqrt(k/m).

Each lane renders as a glowing animated coil spring on the left (the actual
physical picture) and a glowing scrolling oscilloscope-style trace on the
right (x(t) over the last few seconds), so you get both the "physical"
intuition and the "signal" intuition on screen at once.

Lanes 1-3 auto re-trigger with a fresh displacement kick whenever they
settle back near equilibrium, so the demo never goes visually dead.

Controls:
  SPACE               - pause / resume
  R                   - reset all systems
  ESC / close window  - quit

Run with: python spring_mass_damper.py
Requires: pygame  (pip install pygame)
"""

import os
import math
import pygame

# --- Config ---------------------------------------------------------------
SCREEN_WIDTH = 1150
SCREEN_HEIGHT = 780

BG_COLOR = (5, 4, 12)
TEXT_COLOR = (210, 220, 255)
HINT_COLOR = (110, 120, 160)

FPS = 60
SUBSTEPS = 4              # physics substeps per rendered frame (accuracy)
DT = (1.0 / FPS) / SUBSTEPS

MASS = 1.0
STIFFNESS = 40.0          # k, shared by lanes 1-3 so damping is the only variable
OMEGA0 = math.sqrt(STIFFNESS / MASS)   # natural frequency, ~6.32 rad/s
C_CRIT = 2.0 * math.sqrt(MASS * STIFFNESS)  # critical damping coefficient

KICK_X = 2.0               # world-unit displacement used to re-trigger a settled lane
SETTLE_EPS = 0.03          # |x| and |v| below this counts as "settled"

PIXELS_PER_UNIT = 34        # world units -> pixels for spring/mass displacement
WAVE_SECONDS = 4.0          # time window shown in the scrolling waveform panels
WAVE_SAMPLES = int(WAVE_SECONDS * FPS)

# Lane layout
LANE_HEIGHT = 168
LANE_TOP0 = 96
WALL_X = 90
SPRING_END_X = 430          # equilibrium x of the mass, in pixels
WAVE_X0 = 560
WAVE_X1 = 1080

NEON_CYAN = (0, 255, 220)
NEON_GREEN = (110, 255, 130)
NEON_MAGENTA = (255, 50, 200)
NEON_GOLD = (255, 210, 50)


def lerp(a, b, t):
    return a + (b - a) * t


def color_lerp(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(lerp(c1[i], c2[i], t)) for i in range(3))


def glow_circle(surface, color, center, radius, layers=5):
    """Draw a soft additive-glow circle by stacking translucent rings on a
    per-pixel-alpha surface, then blending it onto the target additively."""
    size = radius * 4
    glow_surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx, cy = size // 2, size // 2
    for i in range(layers, 0, -1):
        r = int(radius * (i / layers) * 2.2)
        alpha = int(70 * (1 - i / layers) + 12)
        pygame.draw.circle(glow_surf, (*color, alpha), (cx, cy), r)
    pygame.draw.circle(glow_surf, (255, 255, 255, 230), (cx, cy), max(2, radius // 2))
    surface.blit(glow_surf, (center[0] - cx, center[1] - cy), special_flags=pygame.BLEND_RGBA_ADD)


def draw_glow_line(surface, points, color, base_width=2):
    """Draw a polyline three times with shrinking width / growing brightness
    on an additive-blend layer, producing a soft neon-tube look."""
    if len(points) < 2:
        return
    size = (SCREEN_WIDTH, SCREEN_HEIGHT)
    glow_surf = pygame.Surface(size, pygame.SRCALPHA)
    for width, alpha in ((base_width + 5, 40), (base_width + 2, 90), (base_width, 220)):
        pygame.draw.lines(glow_surf, (*color, alpha), False, points, width)
    surface.blit(glow_surf, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)


def draw_spring(surface, x0, y, x1, color, coils=13, amp=11, width=3):
    """Draw a zigzag 'coil' spring between the wall (x0) and the mass (x1)
    at height y. Amplitude tapers near the ends so it reads as anchored."""
    if x1 <= x0 + 10:
        x1 = x0 + 10
    points = [(x0, y)]
    n = coils * 2
    for i in range(1, n):
        t = i / n
        taper = math.sin(t * math.pi)  # 0 at ends, 1 in the middle
        px = x0 + (x1 - x0) * t
        py = y + (amp * taper) * (1 if i % 2 == 0 else -1)
        points.append((px, py))
    points.append((x1, y))
    draw_glow_line(surface, points, color, base_width=width)


class Oscillator:
    """A single damped (optionally driven) harmonic oscillator, integrated
    with classic RK4 for a stable, accurate trace even with stiff damping."""

    def __init__(self, name, color, zeta, driven=False):
        self.name = name
        self.color = color
        self.zeta = zeta
        self.c = zeta * C_CRIT
        self.driven = driven
        self.x = KICK_X if not driven else 0.0
        self.v = 0.0
        self.t = 0.0
        self.kicks = 0
        self.wave = [0.0] * WAVE_SAMPLES
        # Resonance sweep parameters (only used when driven=True)
        self.omega_min = 0.3 * OMEGA0
        self.omega_max = 1.7 * OMEGA0
        self.sweep_period = 8.0
        self.force_amp = 6.0

    def drive_omega(self):
        t_mod = self.t % (2 * self.sweep_period)
        frac = t_mod / self.sweep_period if t_mod < self.sweep_period else 2 - t_mod / self.sweep_period
        return lerp(self.omega_min, self.omega_max, frac)

    def forcing(self, t):
        if not self.driven:
            return 0.0
        omega = self.drive_omega()
        return self.force_amp * math.cos(omega * t)

    def accel(self, x, v, t):
        return (self.forcing(t) - self.c * v - STIFFNESS * x) / MASS

    def rk4_step(self, dt):
        t = self.t
        x, v = self.x, self.v

        a1 = self.accel(x, v, t)
        k1x, k1v = v, a1

        a2 = self.accel(x + 0.5 * dt * k1x, v + 0.5 * dt * k1v, t + 0.5 * dt)
        k2x, k2v = v + 0.5 * dt * k1v, a2

        a3 = self.accel(x + 0.5 * dt * k2x, v + 0.5 * dt * k2v, t + 0.5 * dt)
        k3x, k3v = v + 0.5 * dt * k2v, a3

        a4 = self.accel(x + dt * k3x, v + dt * k3v, t + dt)
        k4x, k4v = v + dt * k3v, a4

        self.x = x + (dt / 6.0) * (k1x + 2 * k2x + 2 * k3x + k4x)
        self.v = v + (dt / 6.0) * (k1v + 2 * k2v + 2 * k3v + k4v)
        self.t += dt

    def update(self, dt, substeps):
        for _ in range(substeps):
            self.rk4_step(dt)
            if not self.driven and abs(self.x) < SETTLE_EPS and abs(self.v) < SETTLE_EPS:
                # Settled -> give it a fresh kick so the lane stays alive.
                self.x = KICK_X
                self.v = 0.0
                self.kicks += 1
        self.wave.append(self.x)
        if len(self.wave) > WAVE_SAMPLES:
            self.wave.pop(0)


def main():
    os.environ.setdefault("SDL_VIDEODRIVER", os.environ.get("SDL_VIDEODRIVER", ""))
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Spring-Mass-Damper: Damping & Resonance")
    clock = pygame.time.Clock()

    font = pygame.font.SysFont("consolas", 18)
    font_small = pygame.font.SysFont("consolas", 14)
    font_title = pygame.font.SysFont("consolas", 26, bold=True)

    lanes = [
        Oscillator("Underdamped  (zeta=0.12)", NEON_CYAN, 0.12),
        Oscillator("Critically damped (zeta=1.0)", NEON_GREEN, 1.0),
        Oscillator("Overdamped  (zeta=2.5)", NEON_MAGENTA, 2.5),
        Oscillator("Driven / Resonance sweep", NEON_GOLD, 0.05, driven=True),
    ]

    running = True
    paused = False
    max_speed_seen = 4.0  # for color-mapping velocity -> heat, adapts upward

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
                    for lane in lanes:
                        lane.x = KICK_X if not lane.driven else 0.0
                        lane.v = 0.0
                        lane.t = 0.0
                        lane.kicks = 0
                        lane.wave = [0.0] * WAVE_SAMPLES

        if not paused:
            for lane in lanes:
                lane.update(DT, SUBSTEPS)
                max_speed_seen = max(max_speed_seen, abs(lane.v))

        screen.fill(BG_COLOR)

        # --- Title ---
        title = font_title.render("Spring-Mass-Damper: Damping & Resonance", True, TEXT_COLOR)
        screen.blit(title, (WALL_X, 30))
        hint = font_small.render("SPACE pause   R reset   ESC quit", True, HINT_COLOR)
        screen.blit(hint, (WALL_X, 62))

        for i, lane in enumerate(lanes):
            lane_top = LANE_TOP0 + i * LANE_HEIGHT
            mid_y = lane_top + LANE_HEIGHT // 2 - 14

            # Wall anchor (a short bright vertical bar)
            pygame.draw.line(screen, (90, 95, 130), (WALL_X, mid_y - 34), (WALL_X, mid_y + 34), 4)

            # Mass position in pixels (clamped only for drawing safety)
            disp_px = max(-140, min(140, lane.x * PIXELS_PER_UNIT))
            mass_x = SPRING_END_X + disp_px

            # Color the spring/mass by current speed -> cool (slow) to hot white (fast)
            speed_t = min(1.0, abs(lane.v) / max_speed_seen)
            heat_color = color_lerp(lane.color, (255, 255, 255), speed_t * 0.55)

            draw_spring(screen, WALL_X, mid_y, mass_x, heat_color)
            glow_circle(screen, heat_color, (int(mass_x), mid_y), 13)

            # Lane label + live stats (kept small, corner-of-lane, not dominant)
            label = font.render(lane.name, True, lane.color)
            screen.blit(label, (WALL_X, lane_top))
            stat_txt = f"x={lane.x:+.2f}  v={lane.v:+.2f}"
            if lane.driven:
                ratio = lane.drive_omega() / OMEGA0
                stat_txt += f"  omega/omega0={ratio:.2f}"
            else:
                stat_txt += f"  kicks={lane.kicks}"
            stat = font_small.render(stat_txt, True, HINT_COLOR)
            screen.blit(stat, (WALL_X, lane_top + 130))

            # --- Scrolling oscilloscope-style waveform panel ---
            pygame.draw.rect(screen, (18, 18, 30), (WAVE_X0, lane_top, WAVE_X1 - WAVE_X0, LANE_HEIGHT - 20), border_radius=6)
            wave = lane.wave
            span = max(2.5, max(abs(v) for v in wave) if wave else 2.5)
            pts = []
            for j, val in enumerate(wave):
                px = WAVE_X0 + (WAVE_X1 - WAVE_X0) * (j / max(1, WAVE_SAMPLES - 1))
                py = lane_top + (LANE_HEIGHT - 20) / 2 - (val / span) * ((LANE_HEIGHT - 40) / 2)
                pts.append((px, py))
            draw_glow_line(screen, pts, lane.color, base_width=2)

        # --- Global HUD (top-right corner, small supporting element) ---
        hud_lines = [
            f"t = {lanes[0].t:6.1f}s",
            f"total kicks = {sum(l.kicks for l in lanes if not l.driven)}",
            f"omega0 = {OMEGA0:.2f} rad/s",
        ]
        for k, line in enumerate(hud_lines):
            txt = font_small.render(line, True, TEXT_COLOR)
            screen.blit(txt, (SCREEN_WIDTH - 230, 30 + k * 18))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()
