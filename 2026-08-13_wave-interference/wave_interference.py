"""
=============================================================================
 WAVE INTERFERENCE  --  the superposition principle, rendered as a live field
=============================================================================

Drop two stones in a pond and the ripples do NOT collide, bounce, or block
each other. They pass straight through -- and where they overlap, the water
height is simply the SUM of what each ripple would have done on its own.

That is the superposition principle, and it is the whole of this demo.

Each source emits a circular travelling wave:

        h_i(x, y, t) = A_i(r) * sin(k * r_i  -  omega * t)

    r_i   = distance from source i to the point (x, y)
    k     = 2*pi / wavelength      (how tightly packed the crests are)
    omega = 2*pi * frequency       (how fast the whole pattern marches)
    A_i(r)= amplitude, decaying with distance as the ring spreads out

The field you see is the plain sum over every source:

        H(x, y, t) = SUM_i  h_i(x, y, t)

Where two crests meet, H is large and positive -> CONSTRUCTIVE interference
(cyan, blazing to white). Where a crest meets a trough they cancel to zero
-> DESTRUCTIVE interference (the dark, still "nodal lines" that fan out from
between the sources). Troughs render magenta. Those dark lines are exactly
the dark fringes of Young's double-slit experiment -- the same physics that
proved light behaves as a wave in 1801.

-----------------------------------------------------------------------------
 PERFORMANCE NOTE (why the code looks the way it does)
-----------------------------------------------------------------------------
Evaluating sin() for every pixel, every source, every frame would be far too
slow in pure Python. So we do the classic demoscene trick:

  1. Sample the field on a coarse grid (~120x76), then bilinearly upscale it
     with pygame.transform.smoothscale -- the blur is free anti-aliasing and
     makes the field look like glowing liquid instead of chunky squares.
  2. Precompute, per source per cell, the *phase index* (an integer into a
     sine lookup table) and the *amplitude*. Those only change when a source
     moves or the wavelength changes -- not every frame.
  3. Per frame, the entire physics update collapses to one list comprehension
     of integer-indexed table lookups and multiply-adds. No sin(), no sqrt().

The physics is exact; only the sampling is approximate.

-----------------------------------------------------------------------------
 CONTROLS
-----------------------------------------------------------------------------
   1 / 2 / 3     number of wave sources (1, 2 or 3)
   LEFT / RIGHT  wavelength down / up   (watch the nodal lines sweep)
   UP / DOWN     frequency up / down
   M             toggle the orbiting source on / off
   T             toggle the floating tracer particles
   MOUSE CLICK   drag the nearest source to the cursor
   SPACE         pause / resume time
   R             reset
   ESC or Q      quit

 Requires: pygame  ->  pip install pygame
 Run with:  python wave_interference.py
=============================================================================
"""

import math
import random

# -----------------------------------------------------------------------------
# CONFIGURATION
# -----------------------------------------------------------------------------
WIDTH, HEIGHT = 1100, 700          # window size in pixels

GW, GH = 120, 76                   # coarse simulation grid (cells across/down)
CELLS = GW * GH                    # ~9k cells: fast enough for pure Python
CELL_W = WIDTH / GW                # pixels per grid cell, used for mapping
CELL_H = HEIGHT / GH

LUT_N = 720                        # sine lookup table resolution (0.5 deg steps)

DEFAULT_LAMBDA = 11.0              # wavelength, in grid cells
MIN_LAMBDA, MAX_LAMBDA = 4.5, 30.0
DEFAULT_FREQ = 0.55                # cycles per second
MIN_FREQ, MAX_FREQ = 0.1, 2.0

TRACER_COUNT = 150                 # floating "buoy" particles riding the wave
TRACER_SWING = 13.0                # max pixel displacement of a tracer

# Colour anchors for the diverging palette -----------------------------------
BG_DEEP = (5, 7, 20)               # zero displacement: near-black navy
CREST = (0, 235, 255)              # positive displacement: neon cyan
TROUGH = (255, 42, 190)            # negative displacement: neon magenta

SRC_COLORS = [(120, 255, 225), (255, 150, 235), (255, 235, 130)]


# =============================================================================
# SINE + COLOUR LOOKUP TABLES
# =============================================================================

def build_sine_table():
    """One period of sine, stored twice back-to-back.

    Doubling it lets us index with (phase - time) without a modulo or a
    branch: we keep every stored phase in [LUT_N, 2*LUT_N) and every time
    index in [0, LUT_N), so the difference always lands inside the table.
    """
    one = [math.sin(2.0 * math.pi * i / LUT_N) for i in range(LUT_N)]
    return one + one


def build_color_table():
    """Diverging neon palette, indexed by int(value * 255) + 255.

    value = -1 -> hot magenta   (deepest trough)
    value =  0 -> near-black    (undisturbed water)
    value = +1 -> white-hot cyan(highest crest)

    The gamma (**0.62) lifts the mid-tones so faint ripples far from the
    sources stay visible instead of crushing to black, and the final
    white-hot blend makes strong constructive interference genuinely glow.
    """
    table = []
    for j in range(-255, 256):
        v = j / 255.0
        mag = abs(v) ** 0.62                       # perceptual lift
        base = CREST if v >= 0.0 else TROUGH
        r = BG_DEEP[0] + (base[0] - BG_DEEP[0]) * mag
        g = BG_DEEP[1] + (base[1] - BG_DEEP[1]) * mag
        b = BG_DEEP[2] + (base[2] - BG_DEEP[2]) * mag
        # Blow out the extremes toward white -> "interference hot spots".
        if mag > 0.70:
            w = ((mag - 0.70) / 0.30) ** 1.5 * 0.9
            r += (255 - r) * w
            g += (255 - g) * w
            b += (255 - b) * w
        table.append(bytes((int(min(255, r)), int(min(255, g)), int(min(255, b)))))
    return table


SINE2 = build_sine_table()
CLUT = build_color_table()


# =============================================================================
# THE PHYSICS  --  deliberately free of any pygame calls so it can be tested
#                  (and read) on its own.
# =============================================================================

class WaveField:
    """Superposition of N circular travelling waves on a coarse grid."""

    def __init__(self, lam=DEFAULT_LAMBDA, freq=DEFAULT_FREQ):
        self.lam = lam               # wavelength in grid cells
        self.freq = freq             # cycles per second
        self.t = 0.0                 # elapsed simulated seconds
        self.sources = []            # [[gx, gy], ...] in grid coordinates
        self.dists = []              # per source: distance from source to cell
        self.amps = []               # per source: amplitude at each cell
        self.pairs = []              # per source: zipped (amp, phase_index)
        self.set_source_count(2)

    # -- source layout --------------------------------------------------------
    def set_source_count(self, n):
        """Preset layouts. Two sources is the classic double-slit geometry."""
        cx, cy = GW * 0.5, GH * 0.5
        if n == 1:
            self.sources = [[cx, cy]]
        elif n == 2:
            self.sources = [[cx, cy - GH * 0.22], [cx, cy + GH * 0.22]]
        else:
            self.sources = [[cx, cy - GH * 0.24],
                            [cx - GW * 0.20, cy + GH * 0.18],
                            [cx + GW * 0.20, cy + GH * 0.18]]
        self.rebuild_all()

    def rebuild_all(self):
        self.dists = [None] * len(self.sources)
        self.amps = [None] * len(self.sources)
        self.pairs = [None] * len(self.sources)
        for i in range(len(self.sources)):
            self.recompute_source(i)

    # -- per-source tables ----------------------------------------------------
    def recompute_source(self, i):
        """Distance + amplitude tables for source i. Only when it MOVES."""
        sx, sy = self.sources[i]
        dists = []
        push = dists.append
        for gy in range(GH):
            dy = gy + 0.5 - sy
            dy2 = dy * dy
            for gx in range(GW):
                dx = gx + 0.5 - sx
                push(math.sqrt(dx * dx + dy2))
        self.dists[i] = dists

        # A 2D circular wave spreads its energy around a growing circumference,
        # so amplitude falls off roughly as 1/sqrt(r). The +1 avoids a blow-up
        # at r = 0, and 1/n keeps the summed field inside [-1, +1] so it can
        # index the colour table directly.
        scale = 1.0 / len(self.sources)
        self.amps[i] = [scale / math.sqrt(1.0 + d * 0.17) for d in dists]
        self.rebuild_phase(i)

    def rebuild_phase(self, i):
        """Integer phase index per cell. Only when the WAVELENGTH changes."""
        k = LUT_N / self.lam                      # table steps per grid cell
        phase = [int(d * k) % LUT_N + LUT_N for d in self.dists[i]]
        self.pairs[i] = list(zip(self.amps[i], phase))

    def rebuild_all_phases(self):
        for i in range(len(self.sources)):
            self.rebuild_phase(i)

    def move_source(self, i, gx, gy):
        self.sources[i] = [max(1.0, min(GW - 1.0, gx)),
                           max(1.0, min(GH - 1.0, gy))]
        self.recompute_source(i)

    def nearest_source(self, gx, gy):
        best, bd = 0, 1e9
        for i, (sx, sy) in enumerate(self.sources):
            d = (sx - gx) ** 2 + (sy - gy) ** 2
            if d < bd:
                best, bd = i, d
        return best

    # -- the actual per-frame simulation --------------------------------------
    def sample(self):
        """Return the summed displacement of every grid cell, in [-1, +1].

        This is H(x, y, t) = SUM_i A_i * sin(k*r_i - omega*t), evaluated with
        table lookups: subtracting the time index from each cell's stored
        phase index IS the '- omega*t' term.
        """
        ti = int(self.t * self.freq * LUT_N) % LUT_N
        pairs = self.pairs
        acc = [a * SINE2[p - ti] for a, p in pairs[0]]
        for i in range(1, len(pairs)):
            acc = [x + a * SINE2[p - ti]
                   for x, (a, p) in zip(acc, pairs[i])]
        return acc

    def advance(self, dt):
        self.t += dt


# =============================================================================
# RENDERING  (everything below here touches pygame)
# =============================================================================

def make_glow(radius, color, strength=1.0):
    """Pre-render a soft radial glow sprite, blitted later with BLEND_ADD."""
    import pygame
    size = radius * 2
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    for r in range(radius, 0, -1):
        f = (1.0 - r / radius) ** 2.2 * strength
        col = (int(color[0] * f), int(color[1] * f), int(color[2] * f))
        pygame.draw.circle(surf, col, (radius, radius), r)
    return surf


def ease(current, target, rate, dt):
    """Frame-rate independent exponential ease-out toward a target value."""
    return current + (target - current) * (1.0 - math.exp(-rate * dt))


def main():
    import pygame

    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Wave Interference  --  superposition in real time")
    clock = pygame.time.Clock()

    try:
        font = pygame.font.SysFont("consolas,dejavusansmono,menlo", 14)
        font_big = pygame.font.SysFont("consolas,dejavusansmono,menlo", 19, bold=True)
    except Exception:
        font = pygame.font.Font(None, 16)
        font_big = pygame.font.Font(None, 22)

    field = WaveField()

    # Target values are eased toward, so parameter changes glide instead of
    # snapping -- the nodal lines visibly sweep across the screen.
    lam_target = field.lam
    freq_target = field.freq

    # Trail layer for the tracer particles. Never hard-cleared: each frame its
    # alpha is subtracted a little, so old positions fade into comet tails.
    trails = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

    glow_big = make_glow(64, (90, 235, 255), 0.55)
    glow_small = make_glow(26, (255, 255, 255), 0.9)

    # Tracer anchors: a jittered grid of points that bob with the local field.
    random.seed(7)
    anchors = []
    for _ in range(TRACER_COUNT):
        anchors.append((random.uniform(40, WIDTH - 40),
                        random.uniform(40, HEIGHT - 40)))

    paused = False
    show_tracers = True
    orbiting = True
    orbit_t = 0.0
    orbit_home = None
    frame = 0
    peak_smooth = 0.0

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        dt = min(dt, 0.05)                    # clamp after a stall
        frame += 1

        # ---------------- input ------------------------------------------
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                elif ev.key == pygame.K_SPACE:
                    paused = not paused
                elif ev.key == pygame.K_t:
                    show_tracers = not show_tracers
                elif ev.key == pygame.K_m:
                    orbiting = not orbiting
                    orbit_home = None
                elif ev.key == pygame.K_r:
                    field = WaveField()
                    lam_target, freq_target = field.lam, field.freq
                    orbit_home = None
                    trails.fill((0, 0, 0, 0))
                elif ev.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                    field.set_source_count(ev.key - pygame.K_0)
                    orbit_home = None
            elif ev.type == pygame.MOUSEBUTTONDOWN:
                mx, my = ev.pos
                gx, gy = mx / CELL_W, my / CELL_H
                field.move_source(field.nearest_source(gx, gy), gx, gy)
                orbit_home = None

        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            lam_target = max(MIN_LAMBDA, lam_target - 22.0 * dt)
        if keys[pygame.K_RIGHT]:
            lam_target = min(MAX_LAMBDA, lam_target + 22.0 * dt)
        if keys[pygame.K_UP]:
            freq_target = min(MAX_FREQ, freq_target + 0.9 * dt)
        if keys[pygame.K_DOWN]:
            freq_target = max(MIN_FREQ, freq_target - 0.9 * dt)

        # ---------------- parameter easing --------------------------------
        old_lam = field.lam
        field.lam = ease(field.lam, lam_target, 7.0, dt)
        field.freq = ease(field.freq, freq_target, 7.0, dt)
        if abs(field.lam - old_lam) > 0.004:
            field.rebuild_all_phases()        # phases depend on wavelength

        # ---------------- orbiting source ---------------------------------
        # One source drifts along a slow ellipse. Its distance table has to be
        # rebuilt when it moves, which is the single most expensive operation
        # here -- so we only do it on alternate frames. The motion is slow
        # enough that nobody can tell.
        if orbiting and not paused and len(field.sources) > 1 and frame % 2 == 0:
            if orbit_home is None:
                orbit_home = list(field.sources[-1])
            orbit_t += dt * 2.0
            field.move_source(len(field.sources) - 1,
                              orbit_home[0] + math.cos(orbit_t * 0.35) * GW * 0.11,
                              orbit_home[1] + math.sin(orbit_t * 0.47) * GH * 0.09)

        if not paused:
            field.advance(dt)

        # ---------------- physics -> pixels -------------------------------
        acc = field.sample()

        # One list comprehension turns 9,120 displacement values into a raw
        # RGB byte buffer, which pygame wraps as a tiny surface for free.
        raw = b"".join([CLUT[int(v * 255.0) + 255] for v in acc])
        small = pygame.image.frombuffer(raw, (GW, GH), "RGB")
        screen.blit(pygame.transform.smoothscale(small, (WIDTH, HEIGHT)), (0, 0))

        # ---------------- tracer particles --------------------------------
        # Fade the trail layer instead of clearing it: subtracting alpha each
        # frame leaves a decaying comet tail behind every particle.
        trails.fill((0, 0, 0, 26), special_flags=pygame.BLEND_RGBA_SUB)

        if show_tracers:
            srcs_px = [(sx * CELL_W, sy * CELL_H) for sx, sy in field.sources]
            for ax, ay in anchors:
                gx = int(ax / CELL_W)
                gy = int(ay / CELL_H)
                if gx < 0 or gx >= GW or gy < 0 or gy >= GH:
                    continue
                v = acc[gy * GW + gx]

                # Push the tracer radially away from its nearest source by an
                # amount proportional to the local displacement -- so the dots
                # physically ride the ring as it passes through them.
                nx, ny, best = 0.0, 0.0, 1e18
                for px, py in srcs_px:
                    ddx, ddy = ax - px, ay - py
                    d2 = ddx * ddx + ddy * ddy
                    if d2 < best:
                        best = d2
                        d = math.sqrt(d2) + 1e-6
                        nx, ny = ddx / d, ddy / d

                x = ax + nx * v * TRACER_SWING
                y = ay + ny * v * TRACER_SWING

                mag = abs(v)
                if mag < 0.04:
                    continue
                base = CREST if v >= 0 else TROUGH
                f = min(1.0, mag * 1.7)
                col = (int(base[0] * f + 255 * f * f * 0.55),
                       int(base[1] * f + 255 * f * f * 0.55),
                       int(base[2] * f + 255 * f * f * 0.55))
                col = (min(255, col[0]), min(255, col[1]), min(255, col[2]))
                pygame.draw.circle(trails, col, (int(x), int(y)),
                                   1 + int(mag * 2.6))

        screen.blit(trails, (0, 0), special_flags=pygame.BLEND_ADD)

        # ---------------- source markers ----------------------------------
        # Each marker pulses in lockstep with the wave it is emitting, so you
        # can see the beat that drives the whole field.
        pulse = 0.5 + 0.5 * math.sin(field.t * field.freq * 2.0 * math.pi)
        for i, (sx, sy) in enumerate(field.sources):
            px, py = int(sx * CELL_W), int(sy * CELL_H)
            col = SRC_COLORS[i % len(SRC_COLORS)]

            g = pygame.transform.smoothscale(
                glow_big, (int(90 + 46 * pulse), int(90 + 46 * pulse)))
            screen.blit(g, (px - g.get_width() // 2, py - g.get_height() // 2),
                        special_flags=pygame.BLEND_ADD)
            screen.blit(glow_small,
                        (px - glow_small.get_width() // 2,
                         py - glow_small.get_height() // 2),
                        special_flags=pygame.BLEND_ADD)

            # Expanding ring: one wavefront leaving the source, on repeat.
            ring_r = int(6 + pulse * 26)
            ring = pygame.Surface((ring_r * 2 + 4, ring_r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(ring, col + (int(150 * (1.0 - pulse)),),
                               (ring_r + 2, ring_r + 2), ring_r, 2)
            screen.blit(ring, (px - ring_r - 2, py - ring_r - 2),
                        special_flags=pygame.BLEND_ADD)
            pygame.draw.circle(screen, (255, 255, 255), (px, py), 4)
            pygame.draw.circle(screen, col, (px, py), 7, 1)

        # ---------------- HUD (small, corner-anchored) ---------------------
        # Stats are sampled every 13th cell -- plenty for a readout, and it
        # keeps the HUD off the critical path.
        sample = acc[::13]
        peak = max(abs(v) for v in sample)
        peak_smooth = ease(peak_smooth, peak, 6.0, dt)
        constructive = sum(1 for v in sample if abs(v) > 0.55) / len(sample)
        nodal = sum(1 for v in sample if abs(v) < 0.06) / len(sample)

        panel = pygame.Surface((248, 132), pygame.SRCALPHA)
        panel.fill((6, 10, 26, 195))
        pygame.draw.rect(panel, (0, 235, 255, 90), panel.get_rect(), 1)
        screen.blit(panel, (18, HEIGHT - 150))

        rows = [
            ("SOURCES", "%d" % len(field.sources), (140, 255, 240)),
            ("WAVELENGTH", "%.1f px" % (field.lam * CELL_W), (0, 235, 255)),
            ("FREQUENCY", "%.2f Hz" % field.freq, (0, 235, 255)),
            ("PEAK |H|", "%.2f" % peak_smooth, (255, 235, 130)),
            ("CONSTRUCTIVE", "%.0f%%" % (constructive * 100), (255, 42, 190)),
            ("NODAL (dark)", "%.0f%%" % (nodal * 100), (120, 150, 200)),
        ]
        for i, (label, val, col) in enumerate(rows):
            y = HEIGHT - 142 + i * 20
            screen.blit(font.render(label, True, (110, 130, 165)), (30, y))
            screen.blit(font.render(val, True, col), (168, y))

        title = font_big.render("WAVE INTERFERENCE", True, (215, 250, 255))
        screen.blit(title, (20, 18))
        sub = font.render("H(x,y,t) = SUM  A/sqrt(r) * sin(kr - wt)",
                          True, (90, 190, 215))
        screen.blit(sub, (22, 44))

        hint = font.render(
            "1/2/3 sources   LEFT/RIGHT wavelength   UP/DOWN freq   "
            "M orbit   T tracers   CLICK move   SPACE pause",
            True, (78, 96, 128))
        screen.blit(hint, (WIDTH - hint.get_width() - 18, HEIGHT - 26))
        if paused:
            p = font_big.render("PAUSED", True, (255, 235, 130))
            screen.blit(p, (WIDTH - p.get_width() - 20, 18))

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
