"""
Perceptron / Logistic Regression via Gradient Descent
-------------------------------------------------------
Visualizes a single linear classifier (a "perceptron" trained with a smooth
logistic/sigmoid activation, i.e. logistic regression) learning to separate
two clouds of 2D points using gradient descent on binary cross-entropy loss.

WHAT YOU'RE WATCHING:
  - Two glowing clouds of points: cyan (class 0) and magenta (class 1).
  - A live "confidence field" painted behind the points: at every pixel we
    evaluate the model's current sigmoid output and blend cyan -> magenta
    based on that probability, with a bright glowing seam exactly where the
    model is 50/50 (the decision boundary).
  - Every frame we take one gradient-descent step on the weights (w1, w2, b),
    smoothly nudging the glowing seam until it settles between the clouds.
  - Misclassified points flash amber/red so you can see the mistakes the
    model is actively correcting.
  - A small HUD (top-left) reports epoch, loss, and accuracy live.

CONTROLS:
  - R: reshuffle a brand new random dataset and restart training
  - SPACE: pause / resume gradient descent
  - ESC / close window: quit

Dependencies: pygame, numpy (pip install pygame numpy)
Run: python perceptron_gradient_descent.py
"""

import sys
import math
import random

import numpy as np
import pygame

# ----------------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------------
WIDTH, HEIGHT = 960, 620
FIELD_W, FIELD_H = 192, 124          # low-res grid for the confidence field (fast to compute)
FPS = 60
N_POINTS_PER_CLASS = 55
LEARNING_RATE = 2.5
STEPS_PER_FRAME = 1                   # one gradient step per rendered frame -> visibly gradual

# World-space bounds that map onto the field/screen (centered coordinate system)
WORLD_X = (-6.0, 6.0)
WORLD_Y = (-4.0, 4.0)

# Neon palette
COLOR_BG = (6, 8, 18)
COLOR_CLASS0 = (60, 245, 245)      # cyan
COLOR_CLASS1 = (255, 55, 210)      # magenta
COLOR_MISCLASS = (255, 200, 40)    # amber flash for wrong predictions
COLOR_BOUNDARY_GLOW = (255, 255, 255)
COLOR_HUD_TEXT = (215, 240, 255)
COLOR_HUD_ACCENT = (120, 255, 200)
COLOR_PANEL = (10, 14, 28)

random.seed()
np.random.seed()


def world_to_screen(x, y):
    """Map world coordinates to screen pixel coordinates."""
    sx = (x - WORLD_X[0]) / (WORLD_X[1] - WORLD_X[0]) * WIDTH
    sy = HEIGHT - (y - WORLD_Y[0]) / (WORLD_Y[1] - WORLD_Y[0]) * HEIGHT
    return sx, sy


def make_dataset():
    """Two roughly-linearly-separable Gaussian blobs, with a little overlap
    so the model has real mistakes to learn from (keeps the demo interesting)."""
    angle = random.uniform(0, math.pi)
    dx, dy = math.cos(angle), math.sin(angle)
    sep = 2.6

    c0 = np.random.randn(N_POINTS_PER_CLASS, 2) * 0.85 + np.array([-dx, -dy]) * sep
    c1 = np.random.randn(N_POINTS_PER_CLASS, 2) * 0.85 + np.array([dx, dy]) * sep

    X = np.vstack([c0, c1])
    y = np.concatenate([np.zeros(N_POINTS_PER_CLASS), np.ones(N_POINTS_PER_CLASS)])
    return X, y


def sigmoid(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))


class Trainer:
    """Holds dataset + weights and performs one gradient-descent step at a time."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.X, self.y = make_dataset()
        # Small random init so the boundary visibly moves into place.
        self.w = np.random.randn(2) * 0.3
        self.b = 0.0
        self.epoch = 0
        self.loss_history = []
        self.smoothed_w = self.w.copy()
        self.smoothed_b = self.b

    def step(self):
        z = self.X @ self.w + self.b
        p = sigmoid(z)
        eps = 1e-9
        loss = -np.mean(self.y * np.log(p + eps) + (1 - self.y) * np.log(1 - p + eps))

        grad_z = (p - self.y) / len(self.y)
        grad_w = self.X.T @ grad_z
        grad_b = np.sum(grad_z)

        self.w -= LEARNING_RATE * grad_w
        self.b -= LEARNING_RATE * grad_b
        self.epoch += 1
        self.loss_history.append(loss)
        if len(self.loss_history) > 400:
            self.loss_history.pop(0)
        return loss, p

    def accuracy(self, p):
        preds = (p >= 0.5).astype(float)
        return float(np.mean(preds == self.y))


def build_field_lut():
    """Precompute the world coordinates for every cell in the low-res field,
    flattened, so each frame we just do one vectorized sigmoid over them."""
    xs = np.linspace(WORLD_X[0], WORLD_X[1], FIELD_W)
    ys = np.linspace(WORLD_Y[1], WORLD_Y[0], FIELD_H)  # flip so row 0 = top of screen
    gx, gy = np.meshgrid(xs, ys)
    return gx, gy


def render_field(surface, gx, gy, w, b, boundary_pulse):
    """Compute the sigmoid confidence field and paint it as a smooth glowing
    cyan<->magenta gradient with a bright seam at the decision boundary."""
    z = gx * w[0] + gy * w[1] + b
    p = sigmoid(z)

    c0 = np.array(COLOR_CLASS0, dtype=np.float32)
    c1 = np.array(COLOR_CLASS1, dtype=np.float32)

    # Base color: linear blend between class colors by probability.
    pf = p[..., None]
    rgb = c0 * (1 - pf) + c1 * pf

    # Glow term: brightest exactly at p=0.5, fading with distance from boundary.
    dist_from_boundary = np.abs(p - 0.5) * 2.0  # 0 at boundary, 1 far away
    glow = np.clip(1.0 - dist_from_boundary, 0.0, 1.0) ** 3.5
    glow *= (0.55 + 0.25 * boundary_pulse)  # gentle pulsing intensity

    white = np.array(COLOR_BOUNDARY_GLOW, dtype=np.float32)
    rgb = rgb * (1 - glow[..., None]) + white * glow[..., None]

    # Darken overall field so points/HUD pop, then clip.
    rgb *= 0.55
    rgb = np.clip(rgb, 0, 255).astype(np.uint8)

    # rgb currently shaped (FIELD_H, FIELD_W, 3); pygame wants (W, H, 3) for surfarray.
    small = pygame.surfarray.make_surface(np.transpose(rgb, (1, 0, 2)))
    scaled = pygame.transform.smoothscale(small, (WIDTH, HEIGHT))
    surface.blit(scaled, (0, 0))


def draw_glow_circle(surface, pos, radius, color, intensity=1.0):
    """Draw a soft additive-blended glowing circle at pos (screen coords)."""
    glow_r = int(radius * 3.2)
    glow_surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
    for i in range(4, 0, -1):
        alpha = int(28 * intensity * (i / 4))
        pygame.draw.circle(glow_surf, (*color, alpha), (glow_r, glow_r), int(glow_r * i / 4))
    surface.blit(glow_surf, (pos[0] - glow_r, pos[1] - glow_r), special_flags=pygame.BLEND_RGBA_ADD)
    pygame.draw.circle(surface, color, (int(pos[0]), int(pos[1])), radius)
    pygame.draw.circle(surface, (255, 255, 255), (int(pos[0]), int(pos[1])), max(1, radius - 3))


def draw_panel(surface, rect, alpha=170):
    panel = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA)
    pygame.draw.rect(panel, (*COLOR_PANEL, alpha), panel.get_rect(), border_radius=10)
    pygame.draw.rect(panel, (*COLOR_HUD_ACCENT, 90), panel.get_rect(), width=1, border_radius=10)
    surface.blit(panel, (rect[0], rect[1]))


def main():
    pygame.init()
    pygame.display.set_caption("Gradient Descent: Learning a Linear Separator")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    font_small = pygame.font.SysFont("consolas", 16)
    font_big = pygame.font.SysFont("consolas", 20, bold=True)

    trainer = Trainer()
    gx, gy = build_field_lut()

    paused = False
    t = 0.0
    converged_hold = 0
    misclass_flash = np.zeros(len(trainer.y))

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        t += dt

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_r:
                    trainer.reset()
                    misclass_flash = np.zeros(len(trainer.y))
                    converged_hold = 0
                elif event.key == pygame.K_SPACE:
                    paused = not paused

        # ---- Training step(s) ----
        if not paused and trainer.loss_history[-1:] != [] or not trainer.loss_history:
            pass
        if not paused:
            loss = None
            for _ in range(STEPS_PER_FRAME):
                loss, p = trainer.step()
            acc = trainer.accuracy(p)
            # Auto-restart with a fresh dataset once well converged, so the
            # demo keeps demonstrating the "settling" motion in a loop.
            if acc >= 0.97 and loss < 0.12:
                converged_hold += 1
            else:
                converged_hold = 0
            if converged_hold > 90:
                trainer.reset()
                misclass_flash = np.zeros(len(trainer.y))
                converged_hold = 0
        else:
            z = trainer.X @ trainer.w + trainer.b
            p = sigmoid(z)
            loss = trainer.loss_history[-1] if trainer.loss_history else 0.0
            acc = trainer.accuracy(p)

        preds = (p >= 0.5).astype(float)
        wrong = (preds != trainer.y).astype(float)
        misclass_flash = np.clip(misclass_flash * 0.85 + wrong * 1.0, 0, 1)

        # ---- Render ----
        boundary_pulse = 0.5 + 0.5 * math.sin(t * 2.2)
        render_field(screen, gx, gy, trainer.w, trainer.b, boundary_pulse)

        for i, (x, y_) in enumerate(trainer.X):
            sx, sy = world_to_screen(x, y_)
            base_color = COLOR_CLASS0 if trainer.y[i] == 0 else COLOR_CLASS1
            flash = misclass_flash[i]
            color = tuple(
                int(base_color[c] * (1 - flash) + COLOR_MISCLASS[c] * flash)
                for c in range(3)
            )
            pulse = 1.0 + 0.15 * math.sin(t * 4 + i)
            draw_glow_circle(screen, (sx, sy), int(5 * pulse), color, intensity=0.8 + 0.6 * flash)

        # ---- HUD ----
        draw_panel(screen, (14, 14, 250, 118))
        lines = [
            ("EPOCH", f"{trainer.epoch}"),
            ("LOSS", f"{loss:.4f}"),
            ("ACCURACY", f"{acc*100:5.1f}%"),
            ("WEIGHTS", f"w=({trainer.w[0]:+.2f}, {trainer.w[1]:+.2f})  b={trainer.b:+.2f}"),
        ]
        y_off = 22
        title = font_big.render("GRADIENT DESCENT", True, COLOR_HUD_ACCENT)
        screen.blit(title, (26, y_off))
        y_off += 26
        for label, val in lines:
            txt = font_small.render(f"{label:<9} {val}", True, COLOR_HUD_TEXT)
            screen.blit(txt, (26, y_off))
            y_off += 20

        hint = font_small.render(
            "R: new dataset   SPACE: pause   ESC: quit", True, (140, 160, 180)
        )
        screen.blit(hint, (14, HEIGHT - 26))

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
