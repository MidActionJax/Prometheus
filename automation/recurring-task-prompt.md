# Prometheus recurring demo task

You are running unattended (no human watching), twice a week, inside the `Prometheus` repo at `E:\Linkedin` for Jax (jaxonjdoolittle@gmail.com). This repo holds small, visual Python demos about AI/algorithms/software engineering that Jax screen-records and posts to LinkedIn.

Your job this run: build ONE new demo, verify it, write supporting docs, update the README, then handle the full git/GitHub workflow yourself (branch, commit, push, open a PR with a detailed description, and merge it). You are running with a scoped permission allowlist (see `.claude/settings.local.json`) covering git, gh, python, and file operations — if something you need is denied, say so plainly in your final output rather than guessing around it.

## Step 0 — sync
From the repo root (`E:\Linkedin`):
```
git checkout main
git pull
```

## Step 1 — pick a topic
List existing dated subfolders (`YYYY-MM-DD_topic-slug`) to see what's already been built. Do NOT repeat: A* pathfinding maze solver, BFS maze solver, LIDAR-style self-driving car sensor simulation, CNN layer-by-layer visualization, AI drone canyon navigation, K-means clustering with animated data points, feedforward neural network forward-pass visualization, boids flocking simulation, plus anything else already present as a subfolder.

Rotate across three buckets, picking something both visually striking AND genuinely educational:
1. **Algorithms/pathfinding** — Dijkstra's with animated edge relaxation, maze generation via recursive backtracking, a sorting-algorithm bar-chart race, traveling salesman via genetic algorithm, convex hull construction, a DP table filling in live.
2. **ML/AI concepts** — a decision tree splitting a 2D dataset as it grows, a perceptron/gradient descent finding a separator line, a small RL agent in a grid world with a Q-value heatmap, simplified attention weights glowing between tokens, a genetic algorithm evolving creatures toward a goal.
3. **Simulations/physics** — Conway's Game of Life with neon trails, an n-body gravity sim, ant colony optimization with fading pheromone trails, procedural dungeon/terrain generation.

## Step 2 — build it
A single-file Python script (pygame or tkinter):
- Dark background, bright/neon accent colors (cyan, magenta, green, yellow).
- Real-time motion/animation/step-by-step reveal — not a static chart.
- A small on-screen live-stats HUD where it fits naturally (steps, decisions, distance, time).
- Well-commented, since Jax screen-records the code editor alongside the running app.
- Runnable standalone with `python filename.py`. Check `python -c "import pygame"` first; if missing, `pip install pygame`.

## Step 3 — verify it
Run `python -m py_compile <file>.py` for a syntax check. Then, since a real display is available on this machine, also write a small throwaway test that stubs pygame in `sys.modules` and runs the core simulation logic (not the rendering) for a few hundred iterations checking for exceptions and sane bounds — same approach regardless of whether pygame is installed. Delete the throwaway test file afterward. State which checks you ran and the result in your final summary.

## Step 4 — write supporting files
In a new folder `YYYY-MM-DD_topic-slug` (today's actual date), create exactly four files:
- the tested `.py` script
- `caption.txt` — LinkedIn caption in this shape: a hook line, one bridging sentence ("I built a demo that..."), 2-3 substantive teaching beats explaining the real mechanism, a closing line + nod to the video, and 5-6 tight relevant hashtags max. Light emoji use. Vary the structural framing each time — don't reuse the same gimmick.
- `HOW_TO_RUN.txt` — plain-language instructions: installing Python/pygame if needed, the exact run command, on-screen controls, how to screen-record (Win+G / Xbox Game Bar or OBS), a suggested 10-20s clip length, and a reminder to post natively with caption.txt.
- `PR_DESCRIPTION.md` — Summary, What's included, How it was verified (state the real method/result), What it teaches, and a "To do before posting" checklist (run it locally, record a clip, review the caption, post to LinkedIn).

## Step 5 — update the README
Add a new entry at the TOP of the `## Demos` list in the root `README.md`:
`- [YYYY-MM-DD — Title](YYYY-MM-DD_topic-slug/) — one-sentence description.`
Don't reorder or remove existing entries.

## Step 6 — git workflow (do this yourself)
```
git checkout -b demo/<topic-slug>
git add .
git commit -m "Add <Title> demo"
git push -u origin demo/<topic-slug>
gh pr create --title "Add <Title> demo" --body-file <path-to-PR_DESCRIPTION.md> --base main --head demo/<topic-slug>
gh pr merge demo/<topic-slug> --squash --delete-branch
git checkout main
git pull
```
If any step is denied by the permission allowlist or fails for another reason, stop and report exactly what happened rather than working around it.

## Final output
Summarize: the folder/filename, what it demonstrates in one sentence, the verification method and result, the full caption text, the PR URL, and confirmation it was merged.
