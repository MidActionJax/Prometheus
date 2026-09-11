"""
decision_tree_growth.py

Visualizes a CART (Classification and Regression Tree) decision tree learning
to classify a 2D checkerboard-style dataset, one axis-aligned split at a time.

THE CONCEPT
A decision tree classifier repeatedly asks "is feature X above or below some
threshold?" It picks, at each step, the split that most reduces "impurity"
(how mixed the classes are) using the Gini impurity measure:

    Gini(node) = 1 - p0^2 - p1^2

where p0/p1 are the fractions of each class in that node. A split is scored
by how much it lowers the *weighted average* Gini of the two children versus
the parent. The tree greedily takes the best split, then recurses on each
child -- carving the 2D plane into an increasingly fine mosaic of rectangles.

Because splits are always axis-aligned (a single vertical or horizontal cut),
a decision tree approximates any true boundary as a "staircase" of rectangles.
That's exactly what you'll watch happen here: the tree is trying to reproduce
a 3x3 checkerboard pattern using nothing but straight cuts.

CONTROLS
    SPACE  - restart immediately with a freshly generated dataset
    ESC    - quit

Run with:  python decision_tree_growth.py
Dependency: pygame  (pip install pygame)
"""

import math
import random
import sys

import pygame

# ----------------------------------------------------------------------------
# Configuration / visual constants
# ----------------------------------------------------------------------------
WIDTH, HEIGHT = 1280, 720
FPS = 60

BG_COLOR = (7, 9, 18)
PANEL_BG = (14, 17, 30, 170)          # translucent panel fill (RGBA)
PANEL_BORDER = (60, 70, 100)

CLASS_COLOR = {0: (0, 255, 255), 1: (255, 40, 190)}   # cyan / magenta
LINE_GLOW_COLOR = (255, 235, 90)                        # warm gold split line
TEXT_DIM = (140, 150, 175)
TEXT_BRIGHT = (225, 230, 245)
TITLE_COLOR = (120, 235, 255)

# Data-generation parameters (unit square [0,1] x [0,1])
GRID_N = 3            # 3x3 checkerboard cells
POINTS_PER_CELL = 18
LABEL_NOISE = 0.05     # fraction of points with a deliberately flipped label

# Tree-growth parameters
MAX_DEPTH = 4
MIN_LEAF = 6
MIN_GAIN = 1e-4

# Animation timing (frames @ 60fps)
ROOT_HOLD_FRAMES = 50
LINE_ANIM_FRAMES = 26
WASH_FADE_FRAMES = 26
PAUSE_FRAMES = 20
END_HOLD_FRAMES = 170

# Layout rectangles
PLANE_RECT = pygame.Rect(50, 92, 620, 580)
TREE_RECT = pygame.Rect(724, 92, 506, 360)
HUD_RECT = pygame.Rect(724, 470, 506, 130)
LEGEND_RECT = pygame.Rect(724, 616, 506, 56)


# ----------------------------------------------------------------------------
# Data model
# ----------------------------------------------------------------------------
class Node:
    """One node of the decision tree (either an internal split or a leaf)."""

    __slots__ = ("indices", "depth", "bbox", "left", "right",
                 "feature", "threshold", "majority", "purity")

    def __init__(self, indices, depth, bbox):
        self.indices = indices          # list of point indices in this region
        self.depth = depth
        self.bbox = bbox                # (xmin, xmax, ymin, ymax) in data space
        self.left = None
        self.right = None
        self.feature = None             # 0 = split on x, 1 = split on y
        self.threshold = None
        self.majority = None
        self.purity = None


def generate_dataset(rng):
    """Build a jittered 3x3 checkerboard of two-class points with label noise."""
    points = []
    cell = 1.0 / GRID_N
    for gy in range(GRID_N):
        for gx in range(GRID_N):
            base_cls = (gx + gy) % 2
            for _ in range(POINTS_PER_CELL):
                x = gx * cell + rng.uniform(0.10 * cell, cell - 0.10 * cell)
                y = gy * cell + rng.uniform(0.10 * cell, cell - 0.10 * cell)
                cls = base_cls
                if rng.random() < LABEL_NOISE:
                    cls = 1 - cls
                points.append([x, y, cls])
    return points


def gini(labels):
    n = len(labels)
    if n == 0:
        return 0.0
    p1 = sum(labels) / n
    p0 = 1.0 - p1
    return 1.0 - p0 * p0 - p1 * p1


def best_split(points, indices):
    """Search both axes for the threshold that most reduces weighted Gini."""
    n = len(indices)
    if n < 2 * MIN_LEAF:
        return None
    labels_all = [points[i][2] for i in indices]
    base = gini(labels_all)
    best = None
    for feature in (0, 1):
        vals = sorted(set(points[i][feature] for i in indices))
        for j in range(len(vals) - 1):
            thresh = (vals[j] + vals[j + 1]) / 2.0
            left = [i for i in indices if points[i][feature] <= thresh]
            right = [i for i in indices if points[i][feature] > thresh]
            if len(left) < MIN_LEAF or len(right) < MIN_LEAF:
                continue
            weighted = (len(left) * gini([points[i][2] for i in left]) +
                        len(right) * gini([points[i][2] for i in right])) / n
            gain = base - weighted
            if best is None or gain > best[0]:
                best = (gain, feature, thresh, left, right)
    if best is not None and best[0] <= MIN_GAIN:
        return None
    return best


def build_tree(points):
    """Grow the full tree up-front (CART, greedy Gini) and record split
    events in level order (breadth-first) so the animation reveals shallow,
    high-impact splits before deeper, finer ones -- matching how the
    algorithm actually reasons about the data."""
    root = Node(list(range(len(points))), 0, (0.0, 1.0, 0.0, 1.0))
    events = []
    queue = [root]
    while queue:
        node = queue.pop(0)
        labels = [points[i][2] for i in node.indices]
        ones = sum(labels)
        node.majority = 1 if ones * 2 >= len(labels) else 0
        node.purity = max(ones, len(labels) - ones) / max(len(labels), 1)

        if node.depth >= MAX_DEPTH or node.purity >= 0.97:
            continue

        split = best_split(points, node.indices)
        if split is None:
            continue

        _gain, feature, thresh, left_idx, right_idx = split
        xmin, xmax, ymin, ymax = node.bbox
        if feature == 0:
            left_bbox = (xmin, thresh, ymin, ymax)
            right_bbox = (thresh, xmax, ymin, ymax)
        else:
            left_bbox = (xmin, xmax, ymin, thresh)
            right_bbox = (xmin, xmax, thresh, ymax)

        left_node = Node(left_idx, node.depth + 1, left_bbox)
        right_node = Node(right_idx, node.depth + 1, right_bbox)
        node.left, node.right = left_node, right_node
        node.feature, node.threshold = feature, thresh

        events.append((node, feature, thresh))
        queue.append(left_node)
        queue.append(right_node)
    return root, events


def compute_point_paths(root, n_points):
    """For every point, the list of nodes from root down to its final leaf."""
    paths = [[] for _ in range(n_points)]

    def recurse(node):
        for i in node.indices:
            paths[i].append(node)
        if node.left:
            recurse(node.left)
        if node.right:
            recurse(node.right)

    recurse(root)
    return paths


def layout_tree_diagram(root):
    """Assign each node an (x, y) grid position for the mini tree diagram:
    x from in-order leaf position, y from depth."""
    counter = [0]
    positions = {}

    def recurse(node):
        if node.left is None and node.right is None:
            x = counter[0]
            counter[0] += 1
            positions[node] = (x, node.depth)
            return x
        xl = recurse(node.left)
        xr = recurse(node.right)
        x = (xl + xr) / 2.0
        positions[node] = (x, node.depth)
        return x

    recurse(root)
    return positions, max(1, counter[0] - 1)


# ----------------------------------------------------------------------------
# Small drawing helpers (additive-ish glow via layered translucent shapes)
# ----------------------------------------------------------------------------
def ease_out_cubic(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def lerp_color(c0, c1, t):
    return tuple(c0[k] + (c1[k] - c0[k]) * t for k in range(3))


def draw_glow_circle(surf, color, center, radius, core_alpha=255):
    x, y = int(center[0]), int(center[1])
    for i, (mult, alpha) in enumerate(((3.2, 28), (2.0, 55), (1.2, 110))):
        r = max(1, int(radius * mult))
        pygame.draw.circle(surf, (*color, alpha), (x, y), r)
    pygame.draw.circle(surf, (*color, core_alpha), (x, y), max(1, int(radius)))


def draw_glow_line(surf, color, p1, p2, width=2, alpha=255):
    for mult, a in ((6, 22), (3.4, 45), (1.6, 90)):
        pygame.draw.line(surf, (*color, int(a * alpha / 255)), p1, p2,
                          max(1, int(width * mult)))
    pygame.draw.line(surf, (*color, alpha), p1, p2, max(1, width))


# ----------------------------------------------------------------------------
# Main application
# ----------------------------------------------------------------------------
class DecisionTreeDemo:
    def __init__(self, screen, font_small, font_med, font_title):
        self.screen = screen
        self.font_small = font_small
        self.font_med = font_med
        self.font_title = font_title
        self.glow = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.frame_count = 0
        self.reset()

    # -- (re)initialize a fresh dataset + tree ------------------------------
    def reset(self):
        rng = random.Random()
        self.points = generate_dataset(rng)
        self.root, self.events = build_tree(self.points)
        self.paths = compute_point_paths(self.root, len(self.points))
        self.tree_positions, self.max_leaf_x = layout_tree_diagram(self.root)
        self.max_depth_seen = max(pos[1] for pos in self.tree_positions.values())

        self.revealed = {self.root}
        self.revealed_at = {self.root: self.frame_count}
        self.event_index = 0
        self.splits_done = 0
        self.phase = "root_hold"
        self.phase_frame = 0

    # -- coordinate mapping --------------------------------------------------
    @staticmethod
    def data_to_plane(x, y):
        px = PLANE_RECT.x + x * PLANE_RECT.w
        py = PLANE_RECT.y + (1.0 - y) * PLANE_RECT.h
        return px, py

    # -- per-frame state machine ---------------------------------------------
    def update(self):
        self.phase_frame += 1

        if self.phase == "root_hold":
            if self.phase_frame > ROOT_HOLD_FRAMES:
                if self.events:
                    self._enter_line_phase()
                else:
                    # Degenerate case: no split ever beat MIN_GAIN (rare with
                    # this dataset, but guarded against so a run never crashes).
                    self.phase = "end_hold"
                    self.phase_frame = 0

        elif self.phase == "line":
            if self.phase_frame > LINE_ANIM_FRAMES:
                node, _feature, _thresh = self.events[self.event_index]
                self.revealed.add(node.left)
                self.revealed.add(node.right)
                self.revealed_at[node.left] = self.frame_count
                self.revealed_at[node.right] = self.frame_count
                self.phase = "wash"
                self.phase_frame = 0

        elif self.phase == "wash":
            if self.phase_frame > WASH_FADE_FRAMES:
                self.splits_done += 1
                self.phase = "pause"
                self.phase_frame = 0

        elif self.phase == "pause":
            if self.phase_frame > PAUSE_FRAMES:
                self.event_index += 1
                if self.event_index >= len(self.events):
                    self.phase = "end_hold"
                    self.phase_frame = 0
                else:
                    self._enter_line_phase()

        elif self.phase == "end_hold":
            if self.phase_frame > END_HOLD_FRAMES:
                self.reset()

        self.frame_count += 1

    def _enter_line_phase(self):
        self.phase = "line"
        self.phase_frame = 0

    # -- HUD stats -------------------------------------------------------
    def current_accuracy(self):
        correct = 0
        for i, path in enumerate(self.paths):
            assigned = path[0]
            for node in path:
                if node in self.revealed:
                    assigned = node
                else:
                    break
            if assigned.majority == self.points[i][2]:
                correct += 1
        return correct / len(self.points)

    def current_leaf_count(self):
        return sum(1 for n in self.revealed
                    if not (n.left in self.revealed and n.right in self.revealed))

    # -- drawing --------------------------------------------------------
    def draw(self):
        screen = self.screen
        screen.fill(BG_COLOR)
        self.glow.fill((0, 0, 0, 0))

        self._draw_regions()
        self._draw_active_split_line()
        self._draw_points()
        self._draw_tree_diagram()
        self._draw_hud()
        self._draw_legend()
        self._draw_titles()

        screen.blit(self.glow, (0, 0))
        self._draw_plane_border()
        self._draw_footer()

    def _region_color_alpha(self, node):
        labels = [self.points[i][2] for i in node.indices]
        frac1 = sum(labels) / max(len(labels), 1)
        color = lerp_color(CLASS_COLOR[0], CLASS_COLOR[1], frac1)
        purity = max(frac1, 1 - frac1)
        target_alpha = 40 + 150 * purity
        return color, target_alpha

    def _draw_regions(self):
        # Draw parents first, children after -- children (nested, smaller
        # rectangles) visually overwrite the portion of their parent they
        # cover, and a fade-in makes the takeover feel like a live reveal.
        for node in sorted(self.revealed, key=lambda n: n.depth):
            t = ease_out_cubic((self.frame_count - self.revealed_at[node]) / WASH_FADE_FRAMES)
            color, target_alpha = self._region_color_alpha(node)
            alpha = int(target_alpha * t)
            if alpha <= 0:
                continue
            xmin, xmax, ymin, ymax = node.bbox
            p0 = self.data_to_plane(xmin, ymax)
            p1 = self.data_to_plane(xmax, ymin)
            rect = pygame.Rect(p0[0], p0[1], p1[0] - p0[0], p1[1] - p0[1])
            pygame.draw.rect(self.glow, (*[int(c) for c in color], alpha), rect)

    def _draw_active_split_line(self):
        if self.phase not in ("line", "wash", "pause"):
            return
        if self.event_index >= len(self.events):
            return
        node, feature, thresh = self.events[self.event_index]
        xmin, xmax, ymin, ymax = node.bbox

        if self.phase == "line":
            t = ease_out_cubic(self.phase_frame / LINE_ANIM_FRAMES)
        else:
            t = 1.0

        pulse = 0.5 + 0.5 * math.sin(self.frame_count * 0.25)
        width = 2 + int(1.5 * pulse) if self.phase == "line" else 2

        if feature == 0:
            y_lo, y_hi = ymin, ymin + (ymax - ymin) * t
            p1 = self.data_to_plane(thresh, y_lo)
            p2 = self.data_to_plane(thresh, y_hi)
        else:
            x_lo, x_hi = xmin, xmin + (xmax - xmin) * t
            p1 = self.data_to_plane(x_lo, thresh)
            p2 = self.data_to_plane(x_hi, thresh)

        draw_glow_line(self.glow, LINE_GLOW_COLOR, p1, p2, width=width, alpha=255)

    def _draw_points(self):
        for i, (x, y, cls) in enumerate(self.points):
            px, py = self.data_to_plane(x, y)
            color = CLASS_COLOR[cls]
            draw_glow_circle(self.glow, color, (px, py), 3.4)

            # Thin gold ring on points the current (partially grown) tree
            # still gets wrong -- a live "error" indicator.
            path = self.paths[i]
            assigned = path[0]
            for node in path:
                if node in self.revealed:
                    assigned = node
                else:
                    break
            if assigned.majority != cls:
                pygame.draw.circle(self.glow, (255, 210, 90, 170),
                                    (int(px), int(py)), 6, 1)

    def _draw_plane_border(self):
        pygame.draw.rect(self.screen, PANEL_BORDER, PLANE_RECT, 1, border_radius=4)

    def _draw_tree_diagram(self):
        panel = pygame.Surface((TREE_RECT.w, TREE_RECT.h), pygame.SRCALPHA)
        panel.fill(PANEL_BG)
        pygame.draw.rect(panel, PANEL_BORDER, panel.get_rect(), 1, border_radius=6)

        label = self.font_small.render("TREE STRUCTURE", True, TEXT_DIM)
        panel.blit(label, (12, 8))

        margin_x, margin_y = 26, 34
        avail_w = TREE_RECT.w - 2 * margin_x
        avail_h = TREE_RECT.h - margin_y - 18
        depth_span = max(1, self.max_depth_seen)

        def pos_to_px(node):
            gx, gy = self.tree_positions[node]
            px = margin_x + (gx / self.max_leaf_x) * avail_w if self.max_leaf_x else margin_x + avail_w / 2
            py = margin_y + (gy / depth_span) * avail_h
            return px, py

        # edges first
        for node in self.revealed:
            if node.left in self.revealed and node.right in self.revealed:
                x0, y0 = pos_to_px(node)
                for child in (node.left, node.right):
                    x1, y1 = pos_to_px(child)
                    pygame.draw.aaline(panel, (90, 100, 130), (x0, y0), (x1, y1))

        # nodes on top
        for node in self.revealed:
            x0, y0 = pos_to_px(node)
            color, _alpha = self._region_color_alpha(node)
            color = tuple(int(c) for c in color)
            is_frontier = not (node.left in self.revealed and node.right in self.revealed)
            radius = 6 if is_frontier else 4
            pygame.draw.circle(panel, color, (x0, y0), radius)
            pygame.draw.circle(panel, (255, 255, 255, 120), (x0, y0), radius, 1)

        self.screen.blit(panel, TREE_RECT.topleft)

    def _draw_hud(self):
        panel = pygame.Surface((HUD_RECT.w, HUD_RECT.h), pygame.SRCALPHA)
        panel.fill(PANEL_BG)
        pygame.draw.rect(panel, PANEL_BORDER, panel.get_rect(), 1, border_radius=6)

        lines = [
            ("SPLITS MADE", f"{self.splits_done} / {len(self.events)}"),
            ("TREE DEPTH", f"{max((n.depth for n in self.revealed), default=0)} / {MAX_DEPTH}"),
            ("ACTIVE LEAVES", f"{self.current_leaf_count()}"),
            ("LIVE ACCURACY", f"{self.current_accuracy() * 100:4.1f}%"),
        ]
        y = 12
        for label, value in lines:
            lab_surf = self.font_small.render(label, True, TEXT_DIM)
            val_surf = self.font_med.render(value, True, TEXT_BRIGHT)
            panel.blit(lab_surf, (14, y))
            panel.blit(val_surf, (HUD_RECT.w - val_surf.get_width() - 14, y - 3))
            y += 28

        self.screen.blit(panel, HUD_RECT.topleft)

    def _draw_legend(self):
        panel = pygame.Surface((LEGEND_RECT.w, LEGEND_RECT.h), pygame.SRCALPHA)
        panel.fill(PANEL_BG)
        pygame.draw.rect(panel, PANEL_BORDER, panel.get_rect(), 1, border_radius=6)

        pygame.draw.circle(panel, CLASS_COLOR[0], (22, 18), 6)
        panel.blit(self.font_small.render("Class A", True, TEXT_DIM), (36, 11))
        pygame.draw.circle(panel, CLASS_COLOR[1], (22, 38), 6)
        panel.blit(self.font_small.render("Class B", True, TEXT_DIM), (36, 31))

        pygame.draw.circle(panel, (255, 210, 90), (150, 18), 6, 1)
        panel.blit(self.font_small.render("misclassified by", True, TEXT_DIM), (164, 11))
        panel.blit(self.font_small.render("current tree", True, TEXT_DIM), (164, 31))

        self.screen.blit(panel, LEGEND_RECT.topleft)

    def _draw_titles(self):
        title = self.font_title.render("DECISION TREE GROWTH", True, TITLE_COLOR)
        subtitle = self.font_small.render(
            "Greedy CART splits carving a 2D plane by Gini impurity reduction",
            True, TEXT_DIM)
        self.screen.blit(title, (50, 24))
        self.screen.blit(subtitle, (50, 58))

    def _draw_footer(self):
        text = self.font_small.render("SPACE restart demo    ESC quit", True, TEXT_DIM)
        self.screen.blit(text, (WIDTH - text.get_width() - 20, HEIGHT - 26))


def main():
    pygame.init()
    pygame.display.set_caption("Decision Tree Growth")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()

    font_small = pygame.font.SysFont("consolas,couriernew,monospace", 15)
    font_med = pygame.font.SysFont("consolas,couriernew,monospace", 18, bold=True)
    font_title = pygame.font.SysFont("consolas,couriernew,monospace", 26, bold=True)

    demo = DecisionTreeDemo(screen, font_small, font_med, font_title)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    demo.reset()

        demo.update()
        demo.draw()

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
