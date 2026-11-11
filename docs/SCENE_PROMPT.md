You're designing an animated ASCII-art scene for my desktop live wallpaper. The wallpaper is a Python program on Windows. It draws a grid of monospace characters behind my desktop icons, about 15 times per second. I'll describe the scene I want. You build it and we refine it together here, and then I'll take the final version to another Claude session that installs it in the program.

## What I need from you, every time

1. **One self-contained HTML file** (as an artifact) that previews the scene. I'll use it to judge the look and motion.
2. **The same scene as a Python class**, following the API below exactly, in a single code block.

The JavaScript scene in the preview must be a line-for-line mirror of the Python class: same structure, same constants, same maths, same random-number usage. Write the Python first, then translate it. If the two drift apart, what I approve in the preview won't be what I get on my desktop.

## How the program works

The screen is a grid of `cols x rows` character cells. On my 1920x1080 monitors at 16px Consolas that's about **213 x 54** cells, but scenes must adapt to any size: compute positions from `cols` and `rows`, never hard-code them. A cell is about **2.1x taller than it is wide** (`self.aspect`). Multiply horizontal distances by `aspect` when you want circles and correct proportions.

Every frame the grid is cleared to empty, the scene draws into it, and the program renders it. A scene keeps its own state between frames (particles, positions and so on).

Each cell has a character and a **colour level** (a one-character string):

| level | meaning | default "claude" theme colour |
|---|---|---|
| `'0'` | empty (not drawn, background shows) | bg `#141413` |
| `'1'` | dimmest | `#2b2a26` |
| `'2'` | dim | `#47453f` |
| `'3'` | mid | `#706d64` |
| `'4'` | bright | `#a8a59b` |
| `'5'` | brightest (cream) | `#ece9df` |
| `'6'` | accent (terracotta) | `#c15f3c` |
| `'7'` | bright accent | `#e08a62` |

The user can switch themes, so always design with levels, never with literal colours. Levels 1-5 are a dim-to-bright ramp; 6-7 are the accent colour.

**Light (off-white) mode has its own scenes.** If I ask for a light-mode scene, the background is off-white paper (`#f0eee6`) and the levels read as ink: `'1'` is faint pencil (`#dcd9cf`), `'5'` is black ink (`#1f1e1c`), and `'6'`/`'7'` are a red stamp (`#d97757`/`#b5502f`). Glows and starfields don't work on paper. Design for ink instead: line work, hatching, stippling, technical drawings, things that are drawn rather than lit. Light scenes go in `light_scenes.py`, which also has the helpers `draw_ring(g, cx, cy, rr, aspect, lv, dashed=False)`, `draw_line(g, x0, y0, x1, y1, lv, ch=None)` and `stroke_char(dx, dy)` (the right `- | / \` for a line direction).

## The Python API (this is exactly what exists)

```python
import math   # math, random and time are the only modules you may use
TAU = math.tau

class Grid:
    cols: int
    rows: int
    ch: list[list[str]]   # ch[y][x]: character, ' ' when empty
    lv: list[list[str]]   # lv[y][x]: level '0'..'7'
    def put(self, x, y, c, lv)       # one cell; silently ignores out-of-bounds; x, y must be ints
    def text(self, x, y, s, lv)      # a string left-to-right; spaces are skipped
    def erase(self, x0, y0, x1, y1)  # clear a rectangle (x1, y1 exclusive)

class Scene:
    def __init__(self, cols, rows, rng, aspect):
        self.cols, self.rows, self.rng, self.aspect = cols, rows, rng, aspect
        self.setup()
    def setup(self): ...              # build initial state; use self.rng (a random.Random), never the global random
    def frame(self, g, t, dt): ...    # draw one frame into g. t = seconds since start, dt = seconds since last frame (up to 0.25)

# Helpers that already exist and you may call:
def make_stars(rng, cols, rows, per_cell) -> list   # star list for the top `rows` rows (density per_cell, e.g. 1/45)
def draw_stars(g, stars, t, below=None)             # twinkling stars; below[x] = skip stars at y >= below[x]-1
def draw_disc(g, cx, cy, r, aspect, fn)             # calls fn(x, y, nx, ny) for each cell in a circle of radius r rows;
                                                    # nx, ny are normalised -1..1 offsets from the centre
```

A minimal example in the style I want:

```python
class Fireflies(Scene):
    """Fireflies drifting over tall grass."""

    def setup(self):
        c, r, rng = self.cols, self.rows, self.rng
        self.grass = [r - 1 - rng.randint(0, 3) for _ in range(c)]
        self.flies = [[rng.uniform(0, c), rng.uniform(r * 0.3, r - 3),
                       rng.uniform(0, TAU), rng.uniform(0.3, 1.0)] for _ in range(40)]

    def frame(self, g, t, dt):
        for f in self.flies:
            f[0] = (f[0] + math.sin(t * f[3] + f[2]) * dt * 3) % self.cols
            f[1] += math.cos(t * f[3] * 0.7 + f[2]) * dt * 1.5
            glow = math.sin(t * 2 * f[3] + f[2])
            if glow > 0.3:
                g.put(int(f[0]), int(f[1]), "*" if glow > 0.8 else ".", "7" if glow > 0.8 else "6")
        for x, top in enumerate(self.grass):
            for y in range(top, self.rows):
                sway = "/" if math.sin(t + x * 0.3) > 0.5 else "|"
                g.put(x, y, sway if y == top else "|", "2" if y == top else "1")
```

## Hard rules

- **Performance:** `frame()` runs in plain CPython (no numpy) and must take **under ~12 ms** on a 213x54 grid. A full-grid loop with 2-3 `math.sin` calls per cell is about the limit. Prefer sparse things (particles, outlines, a band of the screen). Precompute anything constant in `setup()`. Per-row or per-column sin tables are a good trick.
- **It's a wallpaper:** keep it calm and fairly sparse. My desktop icons sit on top (top-left area), so avoid dense, bright fill over large areas. Most of the screen should be empty or dim (levels 1-3); use 4-5 and 6-7 for highlights. Motion should be slow and pleasant to look at for hours, with nothing flashy or strobing.
- **Clock:** the program draws a big clock in the bottom-right corner (about 40x9 cells) and clears that box. Don't put the scene's main subject there.
- **Characters:** printable ASCII plus, if useful, `█ ░ ▒ ▓ ─ │ ·`. No emoji and no other Unicode; the font is Consolas.
- **Self-contained:** one class, deriving from `Scene`, with a one-line docstring. No imports beyond `math`, `random` and `time`. No files and no globals except constants.
- **Deterministic per instance:** all randomness goes through `self.rng`.
- **Every size:** it must look right from about 120x30 up to 320x80.

## The HTML preview

- A single file with no external dependencies. Dark page in the theme bg colour.
- Render a 213x54 grid in `16px Consolas, monospace` with `line-height` about 2.1x the character width. Use a `<pre>` with coloured spans grouped by runs of the same level, or a canvas with `fillText`. Either is fine.
- Implement the same `Grid` (put/text/erase), `Scene` base, and the three helpers in JS. Run `frame(g, t, dt)` at 15 fps with real `t` and `dt`. Draw a placeholder clock box in the bottom-right so I can see the layout.
- For the JS `rng`, use a small seeded PRNG (e.g. mulberry32) with `random()`, `uniform(a, b)`, `randint(a, b)` (inclusive, like Python), `randrange(n)` and `choice(arr)`, so the code mirrors the Python.
- Small controls: a theme switcher (claude, amber `#0d0904` bg with `#ff9d1c`/`#ffe0a0` accents, matrix green, mono), a button to resize the grid to 120x30 / 213x54 / 320x80, and a "reseed" button.
- Show the measured `frame()` time in ms in a corner (the JS will run faster than Python; anything over ~3 ms in JS is a warning sign).

When I'm happy, give me the final Python class in one clean code block, with the scene's short name (lowercase, e.g. `fireflies`), so I can hand it over.

---

Here's the scene I want:

[DESCRIBE YOUR SCENE HERE]
