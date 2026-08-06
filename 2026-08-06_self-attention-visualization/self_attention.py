"""
Self-Attention Visualization
------------------------------
A visual walkthrough of the mechanism at the heart of every Transformer
model (GPT, BERT, Claude, etc.): self-attention. For one query token at a
time, we compute attention(Q, K) = softmax(Q . K^T / sqrt(d)) against every
other token in the sentence, then draw a glowing line to each token whose
brightness and thickness encode how strongly the current word "looks at"
it. The demo automatically cycles through every word in the sentence.

The sentence used is a classic coreference example: "The cat sat on the
mat because it was tired." Every token gets a fixed KEY vector (its
"content") and a QUERY vector (what it's "looking for"). Most tokens query
mostly for themselves plus a little of their neighbors -- but "it"'s query
is deliberately shaped as a blend of "cat" and "mat" (the way a trained
attention head learns to route a pronoun back to its antecedent), so when
the query token becomes "it" the glow visibly jumps back to "cat". These
vectors are small, hand-seeded, and hand-shaped to make that mechanism
legible on camera -- not weights learned by a trained model -- but the
attention formula itself (dot-product score -> softmax -> weighted focus)
is the real thing.

Controls:
  SPACE            - pause / resume auto-advance
  RIGHT ARROW      - manually step to the next query token
  R                - restart from the first token
  ESC / close       - quit

Run with: python self_attention.py
Requires: pygame  (pip install pygame)
"""

import math
import random
import sys

import pygame

# --- Config -------------------------------------------------------------
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60

TOKENS = ["The", "cat", "sat", "on", "the", "mat", "because", "it", "was", "tired"]
EMBED_DIM = 16
SEED = 7
TEMPERATURE = 0.2  # scales attention scores before softmax; tuned so the
                    # demo's distributions are readably "peaky" rather than
                    # flat (real models learn this scale implicitly)

TWEEN_SECONDS = 0.6     # how long each transition between query tokens takes
HOLD_SECONDS = 1.6      # how long we hold on a finished transition before advancing
TWEEN_FRAMES = int(TWEEN_SECONDS * FPS)
HOLD_FRAMES = int(HOLD_SECONDS * FPS)

# --- Neon color palette ---------------------------------------------------
BG_COLOR = (7, 8, 18)
PANEL_COLOR = (16, 18, 34)
NEON_CYAN = (0, 255, 220)
NEON_YELLOW = (255, 225, 60)
NEON_GREEN = (90, 255, 140)
TEXT_COLOR = (225, 232, 255)
DIM_TEXT = (140, 150, 180)
QUERY_BORDER = (255, 230, 90)


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_color(c1, c2, t):
    return tuple(int(lerp(c1[i], c2[i], t)) for i in range(3))


def ease_in_out_cubic(t):
    """Smooth acceleration/deceleration curve instead of a linear snap."""
    if t < 0.5:
        return 4 * t * t * t
    p = -2 * t + 2
    return 1 - (p ** 3) / 2


def weight_to_color(w):
    """Map an attention weight in [0, 1] to a two-stop neon gradient:
    dim cyan (low) -> bright yellow (high)."""
    w = max(0.0, min(1.0, w))
    if w <= 0.02:
        return (30, 34, 46)
    return lerp_color(NEON_CYAN, NEON_YELLOW, w)


# --- Tiny linear-algebra helpers (no numpy needed) ------------------------
def make_random_vector(rng, dim):
    return [rng.gauss(0, 1) for _ in range(dim)]


def weighted_sum(*pairs):
    """pairs is a sequence of (vector, weight). Returns the weighted sum."""
    dim = len(pairs[0][0])
    out = [0.0] * dim
    for vec, weight in pairs:
        for i in range(dim):
            out[i] += vec[i] * weight
    return out


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def softmax(scores):
    m = max(scores)
    exps = [math.exp(s - m) for s in scores]
    total = sum(exps)
    return [e / total for e in exps]


def entropy_bits(probs):
    """Shannon entropy of the attention distribution, in bits. Low entropy
    means attention is sharply focused on one token; high entropy means it's
    spread out roughly evenly across the sentence."""
    total = 0.0
    for p in probs:
        if p > 1e-9:
            total -= p * math.log2(p)
    return total


def build_key_vectors():
    """Build one fixed KEY vector per token position -- the token's
    'content' representation, used both as K and V. Same word (e.g. 'The'
    and 'the') gets the same vector, since it's the same underlying token.
    These are plain random vectors: nothing about coreference lives here,
    only in the query vectors below."""
    rng = random.Random(SEED)
    unique_words = sorted(set(tok.lower() for tok in TOKENS))
    by_word = {w: make_random_vector(rng, EMBED_DIM) for w in unique_words}
    return [by_word[tok.lower()] for tok in TOKENS]


def build_query_vectors(key_vectors):
    """Build one QUERY vector per token position -- what that token is
    'looking for' in the rest of the sentence. Most tokens query mostly for
    themselves plus a small amount of their immediate neighbors (a simple
    stand-in for local context-sensitivity). The pronoun 'it' is the
    featured exception: its query is hand-shaped as a blend of 'cat' and
    'mat', the way a trained attention head learns to route a pronoun's
    query toward its antecedent. 'tired' gets a smaller nudge toward 'cat'
    for the same reason (it's describing the cat)."""
    n = len(TOKENS)
    cat_i, mat_i, tired_i = TOKENS.index("cat"), TOKENS.index("mat"), TOKENS.index("tired")
    queries = [None] * n
    for i, tok in enumerate(TOKENS):
        if tok == "it":
            queries[i] = weighted_sum((key_vectors[cat_i], 0.6), (key_vectors[mat_i], 0.4))
        elif tok == "tired":
            queries[i] = weighted_sum((key_vectors[tired_i], 0.7), (key_vectors[cat_i], 0.3))
        else:
            pairs = [(key_vectors[i], 0.85)]
            if i - 1 >= 0:
                pairs.append((key_vectors[i - 1], 0.10))
            if i + 1 < n:
                pairs.append((key_vectors[i + 1], 0.05))
            queries[i] = weighted_sum(*pairs)
    return queries


def compute_attention(query_vectors, key_vectors, query_index):
    """Real scaled dot-product attention: score_j = (Q_i . K_j) * temperature,
    weights = softmax(scores). Q and K are distinct vectors (see above),
    which is what lets 'it' attend somewhere other than itself -- with a
    single shared Q=K vector per token, self-similarity always wins."""
    q = query_vectors[query_index]
    scores = [dot(q, key_vectors[j]) * TEMPERATURE for j in range(len(TOKENS))]
    return softmax(scores)


def main():
    pygame.init()
    pygame.display.set_caption("Self-Attention Visualization")
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pygame.time.Clock()

    title_font = pygame.font.SysFont("consolas,menlo,monospace", 30, bold=True)
    formula_font = pygame.font.SysFont("consolas,menlo,monospace", 18)
    token_font = pygame.font.SysFont("consolas,menlo,monospace", 22, bold=True)
    hud_font = pygame.font.SysFont("consolas,menlo,monospace", 18)
    footer_font = pygame.font.SysFont("consolas,menlo,monospace", 16)

    key_vectors = build_key_vectors()
    query_vectors = build_query_vectors(key_vectors)
    n = len(TOKENS)

    # --- token box layout ---
    margin = 70
    spacing = (SCREEN_WIDTH - 2 * margin) / (n - 1)
    token_y = 250
    boxes = []
    for i, tok in enumerate(TOKENS):
        w = max(58, token_font.size(tok)[0] + 26)
        x = margin + i * spacing
        boxes.append(pygame.Rect(0, 0, w, 48))
        boxes[-1].center = (x, token_y)

    bar_top = token_y + 90
    bar_max_h = 150

    # --- animation state machine ---
    query_index = 0
    weights_prev = [0.0] * n
    weights_target = compute_attention(query_vectors, key_vectors, query_index)
    weights_current = list(weights_target)
    phase = "hold"       # "tween" or "hold"
    phase_frame = 0
    paused = False
    step_count = 0
    total_pairs_computed = n  # first query's pairs already computed above

    def advance_to(next_index):
        nonlocal query_index, weights_prev, weights_target, phase, phase_frame
        nonlocal step_count, total_pairs_computed
        weights_prev = list(weights_current)
        query_index = next_index
        weights_target = compute_attention(query_vectors, key_vectors, query_index)
        phase = "tween"
        phase_frame = 0
        step_count += 1
        total_pairs_computed += n

    running = True
    elapsed = 0.0
    while running:
        dt = clock.tick(FPS) / 1000.0
        elapsed += dt

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_RIGHT:
                    advance_to((query_index + 1) % n)
                elif event.key == pygame.K_r:
                    query_index = 0
                    weights_target = compute_attention(query_vectors, key_vectors, query_index)
                    weights_prev = list(weights_target)
                    weights_current = list(weights_target)
                    phase = "hold"
                    phase_frame = 0
                    step_count = 0
                    total_pairs_computed = n
                    paused = False

        # --- advance state machine ---
        if phase == "tween":
            phase_frame += 1
            t = min(1.0, phase_frame / TWEEN_FRAMES)
            eased = ease_in_out_cubic(t)
            weights_current = [lerp(weights_prev[j], weights_target[j], eased) for j in range(n)]
            if t >= 1.0:
                phase = "hold"
                phase_frame = 0
        else:  # hold
            weights_current = list(weights_target)
            if not paused:
                phase_frame += 1
                if phase_frame >= HOLD_FRAMES:
                    advance_to((query_index + 1) % n)

        # ---------------- draw ----------------
        screen.fill(BG_COLOR)

        title = title_font.render("SELF-ATTENTION: HOW TRANSFORMERS FOCUS", True, TEXT_COLOR)
        screen.blit(title, (40, 28))
        formula = formula_font.render(
            "attention(Q, K) = softmax( Q . K^T / sqrt(d) )   -- weight = how much a word 'looks at' another",
            True, DIM_TEXT,
        )
        screen.blit(formula, (40, 68))

        # glow surface for translucent additive-looking lines
        glow = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)

        query_box = boxes[query_index]
        for j, tok in enumerate(TOKENS):
            w = weights_current[j]
            if w < 0.01:
                continue
            key_box = boxes[j]
            start = (query_box.centerx, query_box.bottom)
            end = (key_box.centerx, key_box.top)
            color = weight_to_color(w)
            # outer soft glow pass (wide, low alpha) then a bright core line
            glow_alpha = int(30 + w * 90)
            core_alpha = int(80 + w * 175)
            width_outer = max(2, int(2 + w * 14))
            width_core = max(1, int(1 + w * 5))
            pygame.draw.line(glow, (*color, glow_alpha), start, end, width_outer)
            pygame.draw.line(glow, (*color, core_alpha), start, end, width_core)

        screen.blit(glow, (0, 0))

        # token boxes
        pulse = (math.sin(elapsed * 4.0) + 1) / 2  # 0..1 pulsing value for the active query
        for i, tok in enumerate(TOKENS):
            box = boxes[i]
            is_query = i == query_index
            w = weights_current[i]
            fill = lerp_color(PANEL_COLOR, weight_to_color(w), min(1.0, w * 1.6))
            pygame.draw.rect(screen, fill, box, border_radius=10)
            if is_query:
                glow_rect = box.inflate(10 + pulse * 8, 10 + pulse * 8)
                pygame.draw.rect(screen, QUERY_BORDER, glow_rect, width=3, border_radius=12)
            else:
                pygame.draw.rect(screen, (70, 78, 100), box, width=2, border_radius=10)
            label = token_font.render(tok, True, TEXT_COLOR if not is_query else (25, 20, 5))
            screen.blit(label, label.get_rect(center=box.center))

        # per-token attention weight bar chart beneath the sentence
        for i, tok in enumerate(TOKENS):
            w = weights_current[i]
            bar_h = int(w * bar_max_h)
            bar_w = 18
            x = boxes[i].centerx - bar_w // 2
            y = bar_top + (bar_max_h - bar_h)
            color = weight_to_color(w)
            pygame.draw.rect(screen, color, pygame.Rect(x, y, bar_w, bar_h), border_radius=4)
            pygame.draw.rect(screen, (50, 54, 70), pygame.Rect(x, bar_top, bar_w, bar_max_h), width=1, border_radius=4)
            pct = hud_font.render(f"{w:.2f}", True, DIM_TEXT)
            screen.blit(pct, pct.get_rect(midtop=(boxes[i].centerx, bar_top + bar_max_h + 8)))

        # --- HUD panel (top-right): live stats, the "proof it's running" touch ---
        max_j = max(range(n), key=lambda j: weights_current[j])
        hud_lines = [
            f"Query token:   \"{TOKENS[query_index]}\"",
            f"Top attention: \"{TOKENS[max_j]}\"  ({weights_current[max_j]:.2f})",
            f"Entropy:       {entropy_bits(weights_current):.2f} bits",
            f"Step:          {step_count}",
            f"Pairs scored:  {total_pairs_computed}",
            f"Status:        {'PAUSED' if paused else 'running'}",
        ]
        panel_w, panel_h = 320, 22 * len(hud_lines) + 24
        panel_rect = pygame.Rect(SCREEN_WIDTH - panel_w - 30, 100, panel_w, panel_h)
        panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        pygame.draw.rect(panel_surf, (16, 18, 34, 210), panel_surf.get_rect(), border_radius=10)
        pygame.draw.rect(panel_surf, NEON_GREEN, panel_surf.get_rect(), width=1, border_radius=10)
        screen.blit(panel_surf, panel_rect.topleft)
        for i, line in enumerate(hud_lines):
            surf = hud_font.render(line, True, NEON_GREEN if i < 2 else TEXT_COLOR)
            screen.blit(surf, (panel_rect.x + 14, panel_rect.y + 12 + i * 22))

        footer = footer_font.render(
            "SPACE pause/resume   RIGHT step forward   R restart   ESC quit",
            True, DIM_TEXT,
        )
        screen.blit(footer, (40, SCREEN_HEIGHT - 36))

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
