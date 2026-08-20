"""
Dijkstra's Shortest Path -- Animated Edge Relaxation
------------------------------------------------------
A scattered network of glowing nodes and weighted edges. Starting from a
single source node, Dijkstra's algorithm expands outward one node at a
time, always settling whichever reachable node currently has the smallest
known distance -- and every time it finds a SHORTER route to a node it
hasn't settled yet, that is a "relaxation": the edge flashes and the
node's tentative distance (and color) updates on the spot.

The whole screen is one continuously looping proof of the algorithm:
- Node color = shortest distance found so far (cyan = close, magenta/red
  = far), so you watch a "heat wavefront" grow outward from the source.
- A bright white flash on an edge = a relaxation just happened on it.
- Once every reachable node is settled, a comet-like particle races back
  along the actual shortest-path tree to the farthest node, tracing the
  final route the algorithm discovered.

Controls:
  SPACE               - pause / resume
  R                   - regenerate a fresh random graph immediately
  ESC / close window  - quit

Run with: python dijkstra_shortest_path.py
Requires: pygame  (pip install pygame)
"""

import os
import math
import heapq
import random

import pygame

# --- Config --------------------------------------------------------------
SCREEN_WIDTH = 1150
SCREEN_HEIGHT = 760

NUM_NODES = 30
NODE_MARGIN = 60
MIN_NODE_DIST = 68          # minimum spacing between nodes when scattering
EXTRA_EDGES_PER_NODE = 2    # nearest-neighbor "shortcut" edges added on top of the MST

NODE_RADIUS = 7

STEP_INTERVAL_MS = 230      # how often the algorithm settles the next node
FLASH_DURATION_MS = 380     # how long a relaxed edge stays bright
RIPPLE_DURATION_MS = 700    # how long a "just settled" ripple ring lasts
TRACE_DURATION_MS = 2600    # how long the final path-trace animation takes
HOLD_AFTER_TRACE_MS = 1600  # pause on the finished path before looping

BG_COLOR = (6, 7, 20)
DIM_EDGE_COLOR = (55, 60, 90)
UNVISITED_COLOR = (75, 85, 120)
TEXT_COLOR = (215, 225, 255)
HINT_COLOR = (120, 130, 170)
SOURCE_COLOR = (255, 255, 255)
TARGET_RING_COLOR = (255, 215, 60)

# Heat gradient stops used to color a node by its shortest distance from
# the source: close -> electric cyan, then green, then gold, then hot
# magenta/red the farther out you get. This is what turns plain distance
# numbers into an actual visual "wavefront" instead of printed text.
HEAT_STOPS = [
    (0.00, (0, 220, 255)),
    (0.33, (80, 255, 140)),
    (0.66, (255, 210, 40)),
    (1.00, (255, 55, 130)),
]


def ease_out_cubic(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def ease_in_out_quad(t):
    t = max(0.0, min(1.0, t))
    if t < 0.5:
        return 2 * t * t
    return 1 - ((-2 * t + 2) ** 2) / 2


def heat_color(t):
    """Piecewise-linear interpolation across HEAT_STOPS for t in [0, 1]."""
    t = max(0.0, min(1.0, t))
    for i in range(len(HEAT_STOPS) - 1):
        t0, c0 = HEAT_STOPS[i]
        t1, c1 = HEAT_STOPS[i + 1]
        if t0 <= t <= t1:
            local = 0.0 if t1 == t0 else (t - t0) / (t1 - t0)
            return tuple(int(c0[k] + (c1[k] - c0[k]) * local) for k in range(3))
    return HEAT_STOPS[-1][1]


def glow_circle(surface, pos, radius, color, alpha_scale=1.0, layers=4):
    """Layer soft translucent circles with additive blending to fake a glow,
    same technique as the other neon demos in this series."""
    span = int(radius * 4)
    if span <= 0:
        return
    glow_surf = pygame.Surface((span * 2, span * 2), pygame.SRCALPHA)
    for layer in range(layers, 0, -1):
        alpha = int((60 / layer) * alpha_scale)
        r = int(radius * (1 + layer * 0.8))
        pygame.draw.circle(glow_surf, (*color, max(0, min(255, alpha))), (span, span), r)
    surface.blit(glow_surf, (pos[0] - span, pos[1] - span), special_flags=pygame.BLEND_RGBA_ADD)
    pygame.draw.circle(surface, color, pos, int(radius))


def generate_points(n, w, h, margin, min_dist):
    """Rejection-sample n points so nodes don't overlap and stay readable."""
    points = []
    attempts = 0
    while len(points) < n and attempts < n * 400:
        attempts += 1
        p = (random.uniform(margin, w - margin), random.uniform(margin, h - margin))
        if all(math.hypot(p[0] - q[0], p[1] - q[1]) >= min_dist for q in points):
            points.append(p)
    # If rejection sampling stalls (tight packing), just fill in remaining
    # points without the spacing guarantee rather than looping forever.
    while len(points) < n:
        points.append((random.uniform(margin, w - margin), random.uniform(margin, h - margin)))
    return points


def build_graph(points):
    """Build a connected weighted graph: a minimum spanning tree (guarantees
    every node is reachable) plus a handful of nearest-neighbor shortcut
    edges layered on top, so Dijkstra actually has alternate routes to
    choose between -- which is what makes 'relaxation' visible at all."""
    n = len(points)

    def dist(i, j):
        return math.hypot(points[i][0] - points[j][0], points[i][1] - points[j][1])

    # Prim's algorithm for the MST.
    in_tree = [False] * n
    in_tree[0] = True
    edge_set = set()
    frontier = [(dist(0, j), 0, j) for j in range(1, n)]
    heapq.heapify(frontier)
    remaining = n - 1
    while remaining > 0 and frontier:
        w, i, j = heapq.heappop(frontier)
        if in_tree[j]:
            continue
        in_tree[j] = True
        edge_set.add((min(i, j), max(i, j)))
        remaining -= 1
        for k in range(n):
            if not in_tree[k]:
                heapq.heappush(frontier, (dist(j, k), j, k))

    # Nearest-neighbor shortcut edges on top of the tree.
    for i in range(n):
        dists = sorted(range(n), key=lambda j: dist(i, j))
        added = 0
        for j in dists:
            if j == i:
                continue
            key = (min(i, j), max(i, j))
            if key not in edge_set:
                edge_set.add(key)
                added += 1
            if added >= EXTRA_EDGES_PER_NODE:
                break

    edges = [(i, j, dist(i, j)) for (i, j) in edge_set]
    adjacency = {i: [] for i in range(n)}
    for i, j, w in edges:
        adjacency[i].append((j, w))
        adjacency[j].append((i, w))
    return edges, adjacency


class DijkstraRun:
    """Owns the graph plus the step-by-step Dijkstra state machine and all
    of the transient animation state (flashes, ripples, path trace) that
    rides on top of it."""

    def __init__(self, w, h):
        self.points = generate_points(NUM_NODES, w, h, NODE_MARGIN, MIN_NODE_DIST)
        self.edges, self.adjacency = build_graph(self.points)
        self.n = len(self.points)

        self.source = random.randrange(self.n)
        self.dist = [math.inf] * self.n
        self.prev = [None] * self.n
        self.settled = [False] * self.n
        self.dist[self.source] = 0.0

        self.heap = [(0.0, self.source)]
        self.relax_count = 0
        self.settle_order = []

        self.flashes = []   # list of dicts: edge (i,j), start_ms
        self.ripples = []   # list of dicts: node, start_ms

        self.phase = "SEARCHING"  # SEARCHING -> DONE -> TRACING -> HOLDING
        self.target = None
        self.trace_path = []       # list of node indices, source -> target
        self.trace_cum_dist = []   # cumulative arc length along trace_path
        self.trace_start_ms = None
        self.trail_points = []     # comet trail during tracing
        self.phase_change_ms = 0

    def max_settled_dist(self):
        finite = [d for d, ok in zip(self.dist, self.settled) if ok and math.isfinite(d)]
        return max(finite) if finite else 1.0

    def step(self, now_ms):
        """Pop and settle exactly one node, relaxing its neighbors."""
        while self.heap:
            d, u = heapq.heappop(self.heap)
            if self.settled[u]:
                continue  # stale heap entry from an earlier, worse distance
            self.settled[u] = True
            self.settle_order.append(u)
            self.ripples.append({"node": u, "start_ms": now_ms})

            for v, w in self.adjacency[u]:
                if self.settled[v]:
                    continue
                alt = self.dist[u] + w
                if alt < self.dist[v]:
                    self.dist[v] = alt
                    self.prev[v] = u
                    heapq.heappush(self.heap, (alt, v))
                    self.relax_count += 1
                    self.flashes.append({"edge": (u, v), "start_ms": now_ms})
            return True
        return False  # heap exhausted -- search is over

    def begin_trace(self, now_ms):
        reachable = [i for i in range(self.n) if self.settled[i] and i != self.source]
        if not reachable:
            self.phase = "HOLDING"
            self.phase_change_ms = now_ms
            return
        self.target = max(reachable, key=lambda i: self.dist[i])

        path = []
        node = self.target
        while node is not None:
            path.append(node)
            node = self.prev[node]
        path.reverse()
        self.trace_path = path

        cum = [0.0]
        for i in range(1, len(path)):
            a, b = self.points[path[i - 1]], self.points[path[i]]
            cum.append(cum[-1] + math.hypot(a[0] - b[0], a[1] - b[1]))
        self.trace_cum_dist = cum

        self.phase = "TRACING"
        self.trace_start_ms = now_ms
        self.trail_points = []

    def tree_edges(self):
        """Current shortest-path tree, derived fresh from prev[] each frame."""
        return [(self.prev[i], i) for i in range(self.n) if self.prev[i] is not None]

    def particle_position(self, t):
        """Position along the traced path at arc-length fraction t in [0, 1]."""
        if len(self.trace_path) < 2:
            p = self.points[self.trace_path[0]] if self.trace_path else (0, 0)
            return p
        total = self.trace_cum_dist[-1]
        target_dist = t * total
        for i in range(1, len(self.trace_cum_dist)):
            if target_dist <= self.trace_cum_dist[i] or i == len(self.trace_cum_dist) - 1:
                seg_start = self.trace_cum_dist[i - 1]
                seg_len = self.trace_cum_dist[i] - seg_start
                local_t = 0.0 if seg_len == 0 else (target_dist - seg_start) / seg_len
                a = self.points[self.trace_path[i - 1]]
                b = self.points[self.trace_path[i]]
                return (a[0] + (b[0] - a[0]) * local_t, a[1] + (b[1] - a[1]) * local_t)
        return self.points[self.trace_path[-1]]


def heat_t(d, max_d):
    """Normalize a settled distance to [0, 1] for the heat gradient, safely
    handling the zero-division edge case (max_d == 0 right when only the
    source itself has been settled) and unreachable/unset distances."""
    if not math.isfinite(d):
        return 1.0
    if max_d <= 0:
        return 0.0
    return max(0.0, min(1.0, d / max_d))


def draw_hud(surface, font, small_font, run, elapsed_s, paused):
    box_w, box_h = 240, 118
    hud_surf = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
    pygame.draw.rect(hud_surf, (10, 10, 25, 170), (0, 0, box_w, box_h), border_radius=8)
    pygame.draw.rect(hud_surf, (80, 90, 140, 200), (0, 0, box_w, box_h), width=1, border_radius=8)
    surface.blit(hud_surf, (14, 14))

    settled_count = sum(run.settled)
    lines = [
        f"Settled: {settled_count}/{run.n}",
        f"Relaxations: {run.relax_count}",
        f"Frontier: {len(run.heap)}",
        f"Phase: {run.phase}",
        f"Time: {elapsed_s:.1f}s",
    ]
    y = 22
    for line in lines:
        surface.blit(font.render(line, True, TEXT_COLOR), (26, y))
        y += 20

    if paused:
        surface.blit(small_font.render("PAUSED", True, (255, 230, 60)), (26, y))

    hint = "SPACE: pause   R: new graph"
    surface.blit(small_font.render(hint, True, HINT_COLOR), (14, SCREEN_HEIGHT - 26))


def draw_scene(surface, font, small_font, run, now_ms, elapsed_s, paused):
    surface.fill(BG_COLOR)
    max_d = run.max_settled_dist()

    # 1) Faint background edges for every edge in the graph.
    for i, j, _w in run.edges:
        pygame.draw.line(surface, DIM_EDGE_COLOR, run.points[i], run.points[j], 1)

    # 2) Current shortest-path tree, thicker and colored by the child's heat.
    for u, v in run.tree_edges():
        color = heat_color(heat_t(run.dist[v], max_d))
        pygame.draw.line(surface, color, run.points[u], run.points[v], 3)

    # 3) Relaxation flashes: bright fading pulses on top of the edge.
    live_flashes = []
    for f in run.flashes:
        age = now_ms - f["start_ms"]
        if age > FLASH_DURATION_MS:
            continue
        live_flashes.append(f)
        t = age / FLASH_DURATION_MS
        alpha = 1.0 - t
        i, j = f["edge"]
        # Bright white-hot flash that fades out and thins as it ages.
        flash_color = (255, int(255 * alpha), int(255 * alpha))
        width = max(1, int(4 * (1 - t) + 1))
        pygame.draw.line(surface, flash_color, run.points[i], run.points[j], width)
    run.flashes = live_flashes

    # 4) Settle ripples: expanding rings that ease outward and fade.
    live_ripples = []
    for r in run.ripples:
        age = now_ms - r["start_ms"]
        if age > RIPPLE_DURATION_MS:
            continue
        live_ripples.append(r)
        t = ease_out_cubic(age / RIPPLE_DURATION_MS)
        node = r["node"]
        color = heat_color(heat_t(run.dist[node], max_d))
        radius = int(NODE_RADIUS + t * 34)
        alpha = int(255 * (1 - t))
        ring_surf = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
        pygame.draw.circle(ring_surf, (*color, alpha), (radius + 2, radius + 2), radius, width=2)
        pos = run.points[node]
        surface.blit(ring_surf, (pos[0] - radius - 2, pos[1] - radius - 2), special_flags=pygame.BLEND_RGBA_ADD)
    run.ripples = live_ripples

    # 5) Nodes themselves.
    pulse = 0.5 + 0.5 * math.sin(now_ms / 220.0)  # shared pulse phase for frontier nodes
    frontier_ids = {u for _d, u in run.heap if not run.settled[u]}
    for idx, (x, y) in enumerate(run.points):
        pos = (int(x), int(y))
        if idx == run.source:
            glow_circle(surface, pos, NODE_RADIUS + 2, SOURCE_COLOR, alpha_scale=1.3)
        elif run.settled[idx]:
            color = heat_color(heat_t(run.dist[idx], max_d))
            glow_circle(surface, pos, NODE_RADIUS, color, alpha_scale=0.9)
        elif idx in frontier_ids:
            # Pulsing cyan glow for nodes waiting in the priority queue.
            glow_circle(surface, pos, NODE_RADIUS * (0.9 + 0.35 * pulse), (0, 235, 255), alpha_scale=0.7 + 0.5 * pulse)
        else:
            pygame.draw.circle(surface, UNVISITED_COLOR, pos, NODE_RADIUS - 2)

        if run.phase in ("TRACING", "HOLDING") and idx == run.target:
            ring_r = NODE_RADIUS + 9 + int(2 * pulse)
            pygame.draw.circle(surface, TARGET_RING_COLOR, pos, ring_r, width=2)

    # 6) Path-trace comet, drawn last so it's always on top.
    if run.phase == "TRACING" and run.trace_start_ms is not None:
        raw_t = (now_ms - run.trace_start_ms) / TRACE_DURATION_MS
        eased_t = ease_in_out_quad(raw_t)
        pos = run.particle_position(eased_t)
        run.trail_points.append(pos)
        if len(run.trail_points) > 26:
            run.trail_points.pop(0)

        # Highlight the whole final path faintly gold underneath the comet.
        for i in range(1, len(run.trace_path)):
            a = run.points[run.trace_path[i - 1]]
            b = run.points[run.trace_path[i]]
            pygame.draw.line(surface, (140, 120, 30), a, b, 2)

        n_trail = len(run.trail_points)
        for i, p in enumerate(run.trail_points):
            t = i / max(1, n_trail - 1)
            alpha = t
            r = 2 + t * 4
            trail_color = (255, int(215 * t + 40), int(60 * t))
            trail_surf = pygame.Surface((int(r * 4) + 2, int(r * 4) + 2), pygame.SRCALPHA)
            pygame.draw.circle(trail_surf, (*trail_color, int(180 * alpha)), (int(r * 2) + 1, int(r * 2) + 1), int(r))
            surface.blit(trail_surf, (p[0] - r * 2, p[1] - r * 2), special_flags=pygame.BLEND_RGBA_ADD)

        glow_circle(surface, (int(pos[0]), int(pos[1])), 6, (255, 255, 255), alpha_scale=1.4)

    draw_hud(surface, font, small_font, run, elapsed_s, paused)


def main():
    pygame.init()
    pygame.display.set_caption("Dijkstra's Shortest Path -- Animated Edge Relaxation")
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pygame.time.Clock()

    font = pygame.font.SysFont("consolas", 17)
    small_font = pygame.font.SysFont("consolas", 14)

    run = DijkstraRun(SCREEN_WIDTH, SCREEN_HEIGHT)
    paused = False
    last_step_ms = 0
    start_ticks = pygame.time.get_ticks()
    pause_accum_ms = 0
    pause_started_ms = None

    # Headless self-test hook: with SDL_VIDEODRIVER=dummy set, auto-quit
    # after a bounded number of frames so this script can be verified
    # without a real display attached.
    headless_test = os.environ.get("SDL_VIDEODRIVER") == "dummy"
    headless_frame_limit = 420
    frame_count = 0

    running = True
    while running:
        now_ms = pygame.time.get_ticks()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_r:
                    run = DijkstraRun(SCREEN_WIDTH, SCREEN_HEIGHT)
                    start_ticks = now_ms
                    pause_accum_ms = 0
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                    if paused:
                        pause_started_ms = now_ms
                    else:
                        pause_accum_ms += now_ms - pause_started_ms

        if not paused:
            if run.phase == "SEARCHING":
                if now_ms - last_step_ms >= STEP_INTERVAL_MS:
                    last_step_ms = now_ms
                    if not run.step(now_ms):
                        run.phase = "DONE"
                        run.phase_change_ms = now_ms
            elif run.phase == "DONE":
                run.begin_trace(now_ms)
            elif run.phase == "TRACING":
                if now_ms - run.trace_start_ms >= TRACE_DURATION_MS:
                    run.phase = "HOLDING"
                    run.phase_change_ms = now_ms
            elif run.phase == "HOLDING":
                if now_ms - run.phase_change_ms >= HOLD_AFTER_TRACE_MS:
                    run = DijkstraRun(SCREEN_WIDTH, SCREEN_HEIGHT)
                    start_ticks = now_ms
                    pause_accum_ms = 0

        elapsed_s = (now_ms - start_ticks - pause_accum_ms) / 1000.0
        draw_scene(screen, font, small_font, run, now_ms, elapsed_s, paused)

        pygame.display.flip()
        clock.tick(60)
        frame_count += 1

        if headless_test and frame_count >= headless_frame_limit:
            running = False

    pygame.quit()


if __name__ == "__main__":
    main()
