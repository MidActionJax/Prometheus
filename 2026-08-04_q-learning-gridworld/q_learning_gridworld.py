"""
Q-Learning Grid World — Watching a Policy Emerge
==================================================

WHAT THIS DEMONSTRATES
-----------------------
An agent drops into a grid world with no map and no instructions. All it
knows is: at each cell it can move UP, DOWN, LEFT, or RIGHT, it gets -1
"points" for every step it takes, -20 and a reset if it wanders into the
red hazard, and +50 and a reset if it reaches the gold goal. That's it.
No one tells it where the goal is or what a "wall" means.

This is tabular Q-LEARNING, one of the founding algorithms of reinforcement
learning. The agent keeps a table of Q-VALUES — one number per (cell,
action) pair, estimating "how good is it, long-term, to take this action
from this cell?" Every step it takes, it updates that estimate using the
Bellman equation:

    Q(s, a)  +=  alpha * ( reward + gamma * max(Q(s', ·)) - Q(s, a) )

In plain language: "nudge my estimate for this (state, action) toward the
reward I just got, plus a discounted estimate of how good things look from
wherever I ended up." Do that enough times, from enough states, and the
Q-values downstream of the goal start propagating backwards through the
grid — cells near the goal become clearly better than cells near the
hazard, and a full policy (an arrow at every cell pointing toward the best
known action) emerges without anyone programming a single pathfinding rule.

Early on the agent moves mostly at random (a high "epsilon" — the chance it
ignores its own table and just explores). Over many episodes epsilon decays,
the agent leans more on what it has learned, and its path visibly
straightens out. Watch the grid color (the Q-value "heatmap") light up
along the real route to the goal, and the tiny arrows in each cell start
pointing the way.

WHAT'S ON SCREEN
-----------------
- Grid cells are shaded by their current best-known Q-value: near-black
  means "still a mystery / looks bad," bright yellow-gold means "the agent
  is confident this is a great cell to be in."
- Small white arrows show the agent's current best action per cell (the
  emerging policy).
- Dark blocks are walls. The pulsing red cell is a hazard (big penalty).
  The pulsing gold cell is the goal.
- The bright cyan dot is the agent; it leaves a short fading trail so you
  can see its most recent path.
- The HUD (top) shows live training stats — proof this is really learning,
  not just replaying a canned animation.

CONTROLS
--------
  SPACE  - pause / resume
  R      - reset training completely (fresh Q-table, epsilon back to 1.0)
  ESC    - quit

Run with:  python q_learning_gridworld.py
Requires:  pip install pygame

Tip: let it run for 30-45 seconds before you start recording — that's
enough time for the policy arrows to visibly organize into a clean route
around the walls and away from the hazard.
"""

import random

import pygame

# ---------------------------------------------------------------------------
# Grid layout
# ---------------------------------------------------------------------------
COLS, ROWS = 14, 9
CELL = 56
GRID_ORIGIN = (20, 112)

START = (0, 4)
GOAL = (13, 1)

# Two staggered wall segments force the agent to snake through them rather
# than walk a straight line -- a more interesting policy to watch emerge
# than "go directly right."
WALLS = set()
for c in range(3, 11):
    if c != 6:
        WALLS.add((c, 2))
for c in range(3, 11):
    if c != 9:
        WALLS.add((c, 6))

HAZARDS = {(7, 4), (8, 4)}

# Actions as (delta_col, delta_row), matched 1:1 with ACTION_NAMES / arrows.
ACTIONS = [(0, -1), (0, 1), (-1, 0), (1, 0)]
ACTION_NAMES = ["UP", "DOWN", "LEFT", "RIGHT"]
N_ACTIONS = len(ACTIONS)

# ---------------------------------------------------------------------------
# Q-learning hyperparameters -- tuned to converge fast enough to be visible
# within a single short recording, not for textbook optimality.
# ---------------------------------------------------------------------------
ALPHA = 0.3            # learning rate
GAMMA = 0.9             # discount factor for future reward
EPSILON_START = 1.0     # fully random at first
EPSILON_MIN = 0.05       # always keep a little exploration alive
EPSILON_DECAY = 0.90     # multiplied in per completed episode
MAX_STEPS_PER_EPISODE = 150   # safety cap so an unlucky episode can't run forever

STEP_REWARD = -1.0
HAZARD_REWARD = -20.0
GOAL_REWARD = 50.0

# ---------------------------------------------------------------------------
# Pure environment + agent logic -- zero pygame calls anywhere below, so this
# section can be imported and run headlessly for testing.
# ---------------------------------------------------------------------------


def in_bounds(cell):
    c, r = cell
    return 0 <= c < COLS and 0 <= r < ROWS


class GridWorld:
    """The environment. Owns only the agent's current position."""

    def __init__(self):
        self.pos = START

    def reset(self):
        self.pos = START
        return self.pos

    def step(self, action_idx):
        dc, dr = ACTIONS[action_idx]
        col, row = self.pos
        new_cell = (col + dc, row + dr)

        # Bumping a wall or the grid edge just means you stay put -- still
        # costs a step, which teaches the agent to avoid wasting moves.
        if not in_bounds(new_cell) or new_cell in WALLS:
            new_cell = self.pos

        self.pos = new_cell

        if new_cell == GOAL:
            return new_cell, GOAL_REWARD, True
        if new_cell in HAZARDS:
            return new_cell, HAZARD_REWARD, True
        return new_cell, STEP_REWARD, False


class QLearningAgent:
    """A tabular Q-learning agent. `self.q` maps state -> [q_up, q_down,
    q_left, q_right]. Unvisited states default to all zeros."""

    def __init__(self):
        self.q = {}

    def values(self, state):
        return self.q.setdefault(state, [0.0] * N_ACTIONS)

    def epsilon_for_episode(self, episode):
        return max(EPSILON_MIN, EPSILON_START * (EPSILON_DECAY ** episode))

    def choose_action(self, state, epsilon):
        if random.random() < epsilon:
            return random.randrange(N_ACTIONS)
        q = self.values(state)
        best = max(q)
        # Break ties randomly so the agent doesn't get stuck always picking
        # action 0 (UP) whenever several actions look equally good, which
        # happens a lot early on when everything is still 0.0.
        candidates = [i for i, v in enumerate(q) if v == best]
        return random.choice(candidates)

    def update(self, state, action, reward, next_state, done):
        q = self.values(state)
        target = reward if done else reward + GAMMA * max(self.values(next_state))
        q[action] += ALPHA * (target - q[action])

    def best_action(self, state):
        """Returns None if the agent has never visited this state."""
        if state not in self.q:
            return None
        q = self.q[state]
        best = max(q)
        if best == 0.0 and all(v == 0.0 for v in q):
            return None
        candidates = [i for i, v in enumerate(q) if v == best]
        return candidates[0]


class TrainingSession:
    """Owns the environment, the agent, and all live bookkeeping. Advancing
    the simulation by exactly one agent step is `tick()`. Everything the
    renderer needs to draw is a plain attribute read afterward -- no pygame
    calls anywhere in this class."""

    def __init__(self):
        self.env = GridWorld()
        self.agent = QLearningAgent()
        self.state = self.env.reset()
        self.episode = 0
        self.step_in_episode = 0
        self.total_steps = 0
        self.episode_reward_acc = 0.0
        self.last_episode_reward = 0.0
        self.last_episode_length = 0
        self.best_episode_length = None
        self.path_this_episode = [self.state]
        self.epsilon = self.agent.epsilon_for_episode(0)

    def tick(self):
        self.epsilon = self.agent.epsilon_for_episode(self.episode)
        action = self.agent.choose_action(self.state, self.epsilon)
        next_state, reward, done = self.env.step(action)
        self.agent.update(self.state, action, reward, next_state, done)

        self.state = next_state
        self.path_this_episode.append(next_state)
        self.episode_reward_acc += reward
        self.step_in_episode += 1
        self.total_steps += 1

        timed_out = self.step_in_episode >= MAX_STEPS_PER_EPISODE
        if done or timed_out:
            self.last_episode_reward = self.episode_reward_acc
            self.last_episode_length = self.step_in_episode
            if next_state == GOAL:
                if self.best_episode_length is None or self.step_in_episode < self.best_episode_length:
                    self.best_episode_length = self.step_in_episode

            self.episode += 1
            self.step_in_episode = 0
            self.episode_reward_acc = 0.0
            self.state = self.env.reset()
            self.path_this_episode = [self.state]


# ---------------------------------------------------------------------------
# Rendering + main loop -- pygame only lives below this line.
# ---------------------------------------------------------------------------

BG_COLOR = (8, 9, 16)
GRID_LINE_COLOR = (34, 36, 48)
WALL_COLOR = (46, 48, 60)
WALL_OUTLINE = (70, 74, 90)
HUD_COLOR = (225, 228, 235)
AGENT_COLOR = (80, 240, 255)
ARROW_COLOR = (255, 255, 255)

# Heatmap gradient stops: (position 0..1, RGB). Dark indigo (low/unknown)
# through purple and cyan up to bright gold (high value, near the goal).
COLOR_STOPS = [
    (0.0, (14, 10, 30)),
    (0.35, (95, 20, 145)),
    (0.65, (0, 200, 220)),
    (1.0, (255, 225, 60)),
]
VMIN, VMAX = -15.0, 45.0


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def lerp(a, b, t):
    return a + (b - a) * t


def color_for_value(v):
    t = clamp((v - VMIN) / (VMAX - VMIN), 0.0, 1.0)
    for i in range(len(COLOR_STOPS) - 1):
        t0, c0 = COLOR_STOPS[i]
        t1, c1 = COLOR_STOPS[i + 1]
        if t <= t1 or i == len(COLOR_STOPS) - 2:
            local_t = 0.0 if t1 == t0 else clamp((t - t0) / (t1 - t0), 0.0, 1.0)
            return tuple(int(lerp(c0[k], c1[k], local_t)) for k in range(3))
    return COLOR_STOPS[-1][1]


def cell_rect(cell):
    c, r = cell
    x = GRID_ORIGIN[0] + c * CELL
    y = GRID_ORIGIN[1] + r * CELL
    return pygame.Rect(x, y, CELL, CELL)


def cell_center(cell):
    rect = cell_rect(cell)
    return rect.centerx, rect.centery


def draw_arrow(screen, cell, action_idx):
    """Small triangle in `cell` pointing in the direction of `action_idx`."""
    cx, cy = cell_center(cell)
    size = CELL * 0.22
    dc, dr = ACTIONS[action_idx]
    # Tip of the arrow points along (dc, dr); base is perpendicular to it.
    tip = (cx + dc * size, cy + dr * size)
    perp = (-dr, dc)
    base_a = (cx - dc * size * 0.5 + perp[0] * size * 0.6, cy - dr * size * 0.5 + perp[1] * size * 0.6)
    base_b = (cx - dc * size * 0.5 - perp[0] * size * 0.6, cy - dr * size * 0.5 - perp[1] * size * 0.6)
    pygame.draw.polygon(screen, ARROW_COLOR, [tip, base_a, base_b])


def draw_grid(screen, session, pulse):
    for row in range(ROWS):
        for col in range(COLS):
            cell = (col, row)
            rect = cell_rect(cell)

            if cell in WALLS:
                pygame.draw.rect(screen, WALL_COLOR, rect)
                pygame.draw.rect(screen, WALL_OUTLINE, rect, 1)
                continue

            q = session.agent.q.get(cell)
            value = max(q) if q else 0.0
            pygame.draw.rect(screen, color_for_value(value), rect)
            pygame.draw.rect(screen, GRID_LINE_COLOR, rect, 1)

            best = session.agent.best_action(cell)
            if best is not None and cell != GOAL:
                draw_arrow(screen, cell, best)

    # Hazard cells: pulsing red overlay.
    hazard_alpha = int(120 + 100 * pulse)
    hazard_surf = pygame.Surface((CELL, CELL), pygame.SRCALPHA)
    hazard_surf.fill((255, 40, 60, hazard_alpha))
    for cell in HAZARDS:
        screen.blit(hazard_surf, cell_rect(cell).topleft)

    # Goal cell: pulsing gold ring.
    gx, gy = cell_center(GOAL)
    radius = int(CELL * 0.28 + CELL * 0.08 * pulse)
    pygame.draw.circle(screen, (255, 215, 60), (gx, gy), radius, 3)
    pygame.draw.circle(screen, (255, 215, 60), (gx, gy), max(radius - 10, 4))


def draw_hud(screen, font, session):
    lines = [
        f"Episode {session.episode:5d}   Total steps {session.total_steps:6d}   "
        f"Epsilon {session.epsilon * 100:5.1f}%",
        f"Last episode: {session.last_episode_length:4d} steps, reward {session.last_episode_reward:6.1f}"
        + ("" if session.best_episode_length is None
           else f"    Best route so far: {session.best_episode_length} steps"),
    ]
    y = 14
    for line in lines:
        surf = font.render(line, True, HUD_COLOR)
        screen.blit(surf, (20, y))
        y += 24


def main():
    pygame.init()
    width = GRID_ORIGIN[0] * 2 + COLS * CELL
    height = GRID_ORIGIN[1] + ROWS * CELL + 24
    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption("Q-Learning Grid World — Watching a Policy Emerge")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 17)
    title_font = pygame.font.SysFont("consolas", 15, bold=True)

    session = TrainingSession()

    # Fading glow trail behind the agent, same alpha-subtract trick used in
    # the other demos in this series: multiply the trail layer toward
    # transparent each frame instead of clearing it outright.
    trail_surface = pygame.Surface((width, height), pygame.SRCALPHA)
    fade_layer = pygame.Surface((width, height), pygame.SRCALPHA)
    fade_layer.fill((0, 0, 0, 28))

    paused = False
    running = True
    t = 0.0
    while running:
        dt = clock.tick(60) / 1000.0
        t += dt
        pulse = 0.5 + 0.5 * (1 if int(t * 2) % 2 == 0 else -1) * (t * 2 % 1)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_r:
                    session = TrainingSession()
                    trail_surface.fill((0, 0, 0, 0))

        if not paused:
            prev_state = session.state
            session.tick()
            if session.step_in_episode == 0:
                # Episode just reset -- clear the trail so each episode's
                # path is easy to read on its own.
                trail_surface.fill((0, 0, 0, 0))
            else:
                x, y = cell_center(session.state)
                pygame.draw.circle(trail_surface, (*AGENT_COLOR, 255), (x, y), 6)

        trail_surface.blit(fade_layer, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)

        screen.fill(BG_COLOR)
        screen.blit(title_font.render(
            "Q-VALUE HEATMAP  (dark = unexplored/bad  ->  gold = confident/good)",
            True, (150, 155, 170)), (20, 88))
        draw_grid(screen, session, pulse)
        screen.blit(trail_surface, (0, 0))

        # Agent itself, drawn crisp on top of its glow trail.
        ax, ay = cell_center(session.state)
        pygame.draw.circle(screen, (255, 255, 255), (ax, ay), 7)
        pygame.draw.circle(screen, AGENT_COLOR, (ax, ay), 5)

        draw_hud(screen, font, session)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
