"""
=============================================================================
 RECURSIVE BACKTRACKING — MAZE GENERATION, VISUALIZED
=============================================================================

 A maze generator is really just a depth-first search that eats its own path.

 THE ALGORITHM (recursive backtracking / randomized DFS):
   1. Start at a random cell. Mark it visited. Push it on a stack.
   2. Look at the current cell's unvisited neighbours.
        - If there is at least one: pick one at random, knock down the wall
          between them, mark it visited, push it, and move there.
        - If there are none: pop the stack (BACKTRACK) and step back to the
          previous cell.
   3. Repeat until the stack is empty. Every cell has now been visited.

 WHY IT WORKS:
   Each cell is added to the maze exactly once, and each time we add one we
   carve exactly one corridor into it. So for N cells we carve N-1 corridors:
   that is precisely the definition of a SPANNING TREE. A tree has no cycles
   and is fully connected, which means the finished maze is "perfect" — there
   is exactly ONE path between any two cells, and no loops anywhere.

 THE FINALE:
   Once carving finishes we find the maze's DIAMETER — the longest possible
   path between any two cells — using the classic double-BFS trick:
   BFS from anywhere to find the farthest cell A, then BFS from A to find the
   farthest cell B. A->B is the longest corridor in the maze, and we light it
   up in gold.

 VISUALS:
   Corridors are drawn as glowing neon strokes whose hue is mapped to the
   RECURSION DEPTH at the moment they were carved, so you can literally see
   how deep the search has burrowed. Additive blending gives the bloom, a
   fading trail surface gives the comet tail, and the carve head is tweened
   between cells with a smoothstep ease so nothing ever snaps.

 CONTROLS:
   SPACE  pause / resume
   R      regenerate a brand new maze
   UP/DN  faster / slower carving
   ESC    quit

 Requires: pygame   ->   pip install pygame
 Run with: python maze_recursive_backtracking.py
=============================================================================
"""

import math
import random
import colorsys
import pygame

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
WIDTH, HEIGHT = 1180, 800          # window size
COLS, ROWS = 23, 15                # maze grid in cells
CELL = 44                          # pixels per cell
MARGIN_TOP = 78                    # leaves room for the title bar
CORRIDOR_W = 13                    # thickness of the carved corridor core
DEFAULT_SPEED = 33.0               # cell-moves per second
BG = (6, 8, 16)                    # near-black navy background

# Maze is centred horizontally, pushed down by MARGIN_TOP.
GRID_W, GRID_H = COLS * CELL, ROWS * CELL
OX = (WIDTH - GRID_W) // 2 + CELL // 2
OY = MARGIN_TOP + (HEIGHT - MARGIN_TOP - GRID_H) // 2 + CELL // 2


def cell_xy(c, r):
    """Pixel centre of grid cell (c, r)."""
    return (OX + c * CELL, OY + r * CELL)


def depth_color(depth):
    """Map recursion depth -> a saturated neon colour (the 'colour story')."""
    hue = (0.48 + depth * 0.017) % 1.0        # starts cyan, sweeps the spectrum
    r, g, b = colorsys.hsv_to_rgb(hue, 0.80, 1.0)
    return (int(r * 255), int(g * 255), int(b * 255))


def smoothstep(t):
    """Ease-in-out curve so the carve head accelerates and decelerates."""
    return t * t * (3.0 - 2.0 * t)


# ---------------------------------------------------------------------------
# PURE MAZE LOGIC  (no pygame in here — this is the actual algorithm)
# ---------------------------------------------------------------------------
class MazeGen:
    """Iterative randomized depth-first search with an explicit stack.

    Calling step() advances the search by exactly one cell-move and returns a
    small event describing what happened, so the renderer can animate it.
    """

    DIRS = [(0, -1), (1, 0), (0, 1), (-1, 0)]   # N, E, S, W

    def __init__(self, cols, rows, seed=None):
        self.cols, self.rows = cols, rows
        self.rng = random.Random(seed)
        self.visited = set()
        self.links = set()          # frozenset({cellA, cellB}) for each corridor
        self.depth_of = {}          # cell -> stack depth when it was carved
        self.carved = 0
        self.backtracks = 0
        self.done = False

        start = (self.rng.randrange(cols), self.rng.randrange(rows))
        self.stack = [start]
        self.visited.add(start)
        self.depth_of[start] = 0
        self.carved = 1

    def neighbours(self, cell):
        """Unvisited, in-bounds neighbours of a cell."""
        c, r = cell
        out = []
        for dc, dr in self.DIRS:
            n = (c + dc, r + dr)
            if 0 <= n[0] < self.cols and 0 <= n[1] < self.rows and n not in self.visited:
                out.append(n)
        return out

    def step(self):
        """Advance one move. Returns ('carve'|'backtrack'|'done', frm, to, depth)."""
        if not self.stack:
            self.done = True
            return ("done", None, None, 0)

        current = self.stack[-1]
        options = self.neighbours(current)

        if options:
            # --- carve forward into a random unvisited neighbour -------------
            nxt = self.rng.choice(options)
            self.links.add(frozenset((current, nxt)))
            self.visited.add(nxt)
            self.stack.append(nxt)
            depth = len(self.stack)
            self.depth_of[nxt] = depth
            self.carved += 1
            return ("carve", current, nxt, depth)

        # --- dead end: pop and retreat one cell -----------------------------
        self.stack.pop()
        self.backtracks += 1
        if self.stack:
            return ("backtrack", current, self.stack[-1], len(self.stack))
        self.done = True
        return ("done", current, current, 0)

    # -- graph helpers used for the finale ----------------------------------
    def adjacency(self):
        """Turn the link set into a cell -> [neighbours] dictionary."""
        adj = {}
        for link in self.links:
            a, b = tuple(link)
            adj.setdefault(a, []).append(b)
            adj.setdefault(b, []).append(a)
        return adj

    def diameter_path(self):
        """Longest path in the maze, via the double-BFS trick. Returns a list."""
        adj = self.adjacency()
        if not adj:
            return []

        def bfs(src):
            prev = {src: None}
            queue = [src]
            last = src
            while queue:
                nxt_queue = []
                for cell in queue:
                    last = cell
                    for nb in adj.get(cell, ()):
                        if nb not in prev:
                            prev[nb] = cell
                            nxt_queue.append(nb)
                queue = nxt_queue
            return last, prev

        far_a, _ = bfs(next(iter(adj)))
        far_b, prev = bfs(far_a)

        path, node = [], far_b
        while node is not None:
            path.append(node)
            node = prev[node]
        return path


# ---------------------------------------------------------------------------
# RENDER HELPERS
# ---------------------------------------------------------------------------
def make_glow(radius, color):
    """Pre-render a soft radial glow sprite for cheap additive blitting."""
    size = radius * 2
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    for i in range(radius, 0, -1):
        a = int(255 * (i / radius) ** 3.0 * 0.42)
        pygame.draw.circle(surf, (*color, a), (radius, radius), i)
    return surf


class Spark:
    """A single glowing particle flung off the carve head."""

    def __init__(self, x, y, color):
        ang = random.uniform(0, math.tau)
        spd = random.uniform(28, 165)
        self.x, self.y = x, y
        self.vx, self.vy = math.cos(ang) * spd, math.sin(ang) * spd
        self.life = self.max_life = random.uniform(0.30, 0.75)
        self.color = color

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vx *= 0.94                 # drag, so sparks settle rather than fly off
        self.vy *= 0.94
        self.life -= dt
        return self.life > 0

    def draw(self, surf):
        f = max(0.0, self.life / self.max_life)
        c = tuple(int(v * f) for v in self.color)
        pygame.draw.circle(surf, c, (int(self.x), int(self.y)), max(1, int(3 * f)))


class Ring:
    """Expanding ring pulse — fired on every backtrack (a 'dead end' signal)."""

    def __init__(self, x, y, color):
        self.x, self.y = x, y
        self.r = 4.0
        self.life = self.max_life = 0.45
        self.color = color

    def update(self, dt):
        self.r += 150 * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surf):
        f = max(0.0, self.life / self.max_life)
        c = tuple(int(v * f * 0.9) for v in self.color)
        pygame.draw.circle(surf, c, (int(self.x), int(self.y)), int(self.r), 2)


# ---------------------------------------------------------------------------
# MAIN VISUALIZER
# ---------------------------------------------------------------------------
class Visualizer:
    def __init__(self, screen):
        self.screen = screen

        # Persistent layers. `core` holds the solid corridor strokes, `glow`
        # holds the wide soft bloom. Both are only ever ADDED to, so a finished
        # maze costs two blits per frame no matter how large it is.
        self.core = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.glow = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        # `trail` fades a little every frame, giving the comet tail.
        self.trail = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.fx = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

        self.head_glow = make_glow(46, (255, 255, 255))
        self.font_big = pygame.font.SysFont("consolas,menlo,monospace", 21, bold=True)
        self.font_sm = pygame.font.SysFont("consolas,menlo,monospace", 15)
        self.font_hud = pygame.font.SysFont("consolas,menlo,monospace", 14, bold=True)

        self.speed = DEFAULT_SPEED
        self.paused = False
        self.reset()

    # -- lifecycle ----------------------------------------------------------
    def reset(self):
        self.gen = MazeGen(COLS, ROWS)
        self.core.fill((0, 0, 0, 0))
        self.glow.fill((0, 0, 0, 0))
        self.trail.fill((0, 0, 0, 0))
        self.sparks, self.rings = [], []
        self.elapsed = 0.0
        self.phase = "CARVING"
        self.path = []
        self.pulse_t = 0.0

        start = self.gen.stack[-1]
        self.head = cell_xy(*start)
        self.bake_node(start, 0)
        self.move = self.gen.step()
        self.anim = 0.0

    # -- persistent drawing -------------------------------------------------
    def bake_node(self, cell, depth):
        """Stamp a cell's node dot permanently into the core + glow layers."""
        x, y = cell_xy(*cell)
        col = depth_color(depth)
        pygame.draw.circle(self.glow, (*col, 46), (x, y), CORRIDOR_W + 9)
        pygame.draw.circle(self.core, col, (x, y), CORRIDOR_W // 2)

    def bake_corridor(self, a, b, depth):
        """Stamp a finished corridor permanently into the core + glow layers."""
        p, q = cell_xy(*a), cell_xy(*b)
        col = depth_color(depth)
        # wide, faint halo first...
        pygame.draw.line(self.glow, (*col, 34), p, q, CORRIDOR_W + 16)
        pygame.draw.line(self.glow, (*col, 52), p, q, CORRIDOR_W + 6)
        # ...then the bright solid core on top.
        pygame.draw.line(self.core, col, p, q, CORRIDOR_W)
        self.bake_node(b, depth)

    # -- per-frame update ---------------------------------------------------
    def update(self, dt):
        if self.paused:
            return
        self.elapsed += dt

        if self.phase == "CARVING":
            self.advance_carve(dt)
        else:
            self.pulse_t += dt

        self.sparks = [s for s in self.sparks if s.update(dt)]
        self.rings = [r for r in self.rings if r.update(dt)]

    def advance_carve(self, dt):
        """Tween the head between cells; commit a move when the tween lands."""
        self.anim += dt * self.speed
        while self.anim >= 1.0 and self.phase == "CARVING":
            self.anim -= 1.0
            kind, frm, to, depth = self.move

            if kind == "carve":
                self.bake_corridor(frm, to, depth)
                x, y = cell_xy(*to)
                for _ in range(4):                    # sparks on every carve
                    self.sparks.append(Spark(x, y, depth_color(depth)))
            elif kind == "backtrack":
                x, y = cell_xy(*frm)
                self.rings.append(Ring(x, y, (255, 90, 160)))   # dead-end pulse
            elif kind == "done":
                self.finish()
                return

            self.move = self.gen.step()
            if self.move[0] == "done":
                self.finish()
                return

    def finish(self):
        """Carving is complete — switch to the gold longest-path finale."""
        self.phase = "LONGEST PATH"
        self.path = self.gen.diameter_path()
        self.pulse_t = 0.0
        self.anim = 0.0

    # -- head position ------------------------------------------------------
    def head_pos(self):
        kind, frm, to, _ = self.move
        if frm is None or to is None:
            return self.head
        p, q = cell_xy(*frm), cell_xy(*to)
        t = smoothstep(min(1.0, max(0.0, self.anim)))
        return (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)

    # -- drawing ------------------------------------------------------------
    def draw(self):
        s = self.screen
        s.fill(BG)
        self.draw_backdrop(s)

        # Fade the trail layer slightly each frame -> comet tail behind the head.
        self.trail.fill((0, 0, 0, 13), special_flags=pygame.BLEND_RGBA_SUB)

        self.fx.fill((0, 0, 0, 0))

        if self.phase == "CARVING":
            self.draw_active_stroke()

        hx, hy = self.head_pos()
        kind = self.move[0]
        depth = self.move[3] or 1
        hcol = depth_color(depth) if kind != "backtrack" else (255, 110, 175)

        if self.phase == "CARVING":
            # paint the head into the fading trail layer
            pygame.draw.circle(self.trail, (*hcol, 210), (int(hx), int(hy)), 7)

        # ---- composite the layers -----------------------------------------
        s.blit(self.glow, (0, 0), special_flags=pygame.BLEND_ADD)
        s.blit(self.core, (0, 0))
        s.blit(self.trail, (0, 0), special_flags=pygame.BLEND_ADD)

        if self.phase != "CARVING":
            self.draw_finale(s)

        for r in self.rings:
            r.draw(self.fx)
        for sp in self.sparks:
            sp.draw(self.fx)

        if self.phase == "CARVING":
            # hot white core + coloured bloom on the carve head
            g = self.head_glow
            self.fx.blit(g, (hx - g.get_width() / 2, hy - g.get_height() / 2))
            pygame.draw.circle(self.fx, hcol, (int(hx), int(hy)), 9)
            pygame.draw.circle(self.fx, (255, 255, 255), (int(hx), int(hy)), 4)

        s.blit(self.fx, (0, 0), special_flags=pygame.BLEND_ADD)

        self.draw_title(s)
        self.draw_hud(s)

    def draw_backdrop(self, s):
        """Faint dot grid so the un-carved space still reads as a lattice."""
        for r in range(ROWS):
            for c in range(COLS):
                x, y = cell_xy(c, r)
                pygame.draw.circle(s, (20, 26, 44), (x, y), 2)

    def draw_active_stroke(self):
        """Draw the corridor currently being carved, growing frame by frame."""
        kind, frm, to, depth = self.move
        if kind != "carve" or frm is None:
            return
        p = cell_xy(*frm)
        q = self.head_pos()
        col = depth_color(depth)
        pygame.draw.line(self.glow, (*col, 8), p, q, CORRIDOR_W + 10)
        pygame.draw.line(self.core, col, p, q, CORRIDOR_W)

    def draw_finale(self, s):
        """Dim the maze and run a travelling gold pulse along the longest path."""
        if not self.path:
            return
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 150))
        s.blit(veil, (0, 0))

        pts = [cell_xy(*c) for c in self.path]
        pygame.draw.lines(s, (70, 55, 12), False, pts, CORRIDOR_W + 6)
        pygame.draw.lines(s, (150, 120, 30), False, pts, CORRIDOR_W - 3)

        # A bright comet sweeps the path on a loop, brightening it as it passes.
        n = len(pts)
        cycle = 2.6
        head_i = (self.pulse_t % cycle) / cycle * (n - 1)
        tail = 14.0
        for i in range(n - 1):
            d = head_i - i
            if 0 <= d < tail:
                f = 1.0 - d / tail
                c = (int(255 * f), int(215 * f + 25 * f), int(90 * f))
                pygame.draw.line(self.fx, c, pts[i], pts[i + 1], CORRIDOR_W)
        idx = int(head_i)
        if 0 <= idx < n:
            hx, hy = pts[idx]
            g = self.head_glow
            self.fx.blit(g, (hx - g.get_width() / 2, hy - g.get_height() / 2))
            pygame.draw.circle(self.fx, (255, 255, 235), (hx, hy), 8)

    def draw_title(self, s):
        t = self.font_big.render("RECURSIVE BACKTRACKING  ::  MAZE GENERATION", True, (150, 245, 255))
        s.blit(t, (30, 22))
        sub = self.font_sm.render(
            "randomized depth-first search  |  hue = recursion depth  |  N cells, N-1 corridors = a spanning tree",
            True, (95, 120, 155))
        s.blit(sub, (32, 50))

    def draw_hud(self, s):
        """Small live-stats readout, tucked into the bottom-left corner."""
        g = self.gen
        total = COLS * ROWS
        rows = [
            ("CELLS",      f"{g.carved}/{total}",   (110, 255, 220)),
            ("CORRIDORS",  f"{len(g.links)}",       (255, 120, 235)),
            ("DEPTH",      f"{len(g.stack)}",       (255, 235, 110)),
            ("BACKTRACKS", f"{g.backtracks}",       (255, 130, 130)),
            ("TIME",       f"{self.elapsed:5.1f}s", (150, 200, 255)),
            ("PHASE",      self.phase,              (200, 220, 255)),
        ]
        pad, lh = 12, 19
        w, h = 208, lh * len(rows) + pad * 2
        x, y = 26, HEIGHT - h - 22

        panel = pygame.Surface((w, h), pygame.SRCALPHA)
        panel.fill((10, 16, 30, 190))
        pygame.draw.rect(panel, (60, 200, 220, 120), panel.get_rect(), 1)
        s.blit(panel, (x, y))

        for i, (label, val, col) in enumerate(rows):
            ly = y + pad + i * lh
            s.blit(self.font_hud.render(label, True, (95, 130, 165)), (x + pad, ly))
            surf = self.font_hud.render(val, True, col)
            s.blit(surf, (x + w - pad - surf.get_width(), ly))

        keys = self.font_sm.render("SPACE pause   R new maze   UP/DOWN speed   ESC quit",
                                   True, (80, 105, 140))
        s.blit(keys, (WIDTH - keys.get_width() - 26, HEIGHT - 30))


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------
def main(max_frames=None):
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Recursive Backtracking — Maze Generation")
    clock = pygame.time.Clock()

    vis = Visualizer(screen)
    running, frames = True, 0

    while running:
        dt = clock.tick(60) / 1000.0        # real 60fps loop, dt in seconds
        dt = min(dt, 0.05)                  # clamp so a stutter can't jump the sim

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                elif e.key == pygame.K_SPACE:
                    vis.paused = not vis.paused
                elif e.key == pygame.K_r:
                    vis.reset()
                elif e.key == pygame.K_UP:
                    vis.speed = min(200.0, vis.speed * 1.25)
                elif e.key == pygame.K_DOWN:
                    vis.speed = max(3.0, vis.speed / 1.25)

        vis.update(dt)
        vis.draw()
        pygame.display.flip()

        frames += 1
        if max_frames is not None and frames >= max_frames:
            running = False

    pygame.quit()


if __name__ == "__main__":
    main()
