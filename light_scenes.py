"""Scenes made for the off-white (light) mode: ink on paper.

On a light background the levels read as ink: '1' = faint pencil, '5' = black
ink, '6'/'7' = the theme's accent (a red stamp in the claude theme).
"""
import math
import time

from scenes import Scene, TAU, draw_disc


def make_grain(rng, cols, rows, per_cell=1 / 140):
    return [(rng.randrange(cols), rng.randrange(rows)) for _ in range(int(cols * rows * per_cell))]


def draw_grain(g, grain):
    for x, y in grain:
        g.put(x, y, ".", "1")


def stroke_char(dx, dy):
    """Character for a line heading (dx in cols, dy in rows)."""
    if abs(dx) > 2.2 * abs(dy) * 2:
        return "-"
    if abs(dy) * 2 > 2.2 * abs(dx):
        return "|"
    return "\\" if dx * dy > 0 else "/"


def ring_char(ca, sa):
    """Character for a point on a circle at angle with cos=ca, sin=sa (y down)."""
    if abs(sa) > 0.82:
        return "-"
    if abs(ca) > 0.82:
        return ")" if ca > 0 else "("
    return "\\" if ca * sa < 0 else "/"


def draw_ring(g, cx, cy, rr, aspect, lv, dashed=False):
    n = max(8, int(TAU * rr * aspect * 0.8))
    cos, sin = math.cos, math.sin
    for i in range(n):
        if dashed and i % 3 == 2:
            continue
        a = TAU * i / n
        ca, sa = cos(a), sin(a)
        g.put(int(cx + rr * ca * aspect), int(cy + rr * sa), ring_char(ca, sa), lv)


# --------------------------------------------------------------------------- ink mountains

class Sumi(Scene):
    """Ink-wash mountains fading into drifting mist, a red sun and passing birds."""

    WASH = " .:-=+*#%@"

    def setup(self):
        c, r, rng = self.cols, self.rows, self.rng
        self.layers = []
        for k in range(4):   # far -> near
            self.layers.append({
                "base": r * (0.44 + 0.13 * k), "amp": r * (0.2 - 0.03 * k),
                "f1": rng.uniform(0.018, 0.03) * (1 + 0.35 * k),
                "f2": rng.uniform(0.06, 0.1), "p1": rng.uniform(0, TAU),
                "p2": rng.uniform(0, TAU), "depth": r * (0.2 + 0.03 * k),
                "ink": 0.3 + 0.15 * k, "ch": ".:+%"[k], "lv": "2345"[k],
                "speed": 0.08 + 0.25 * k,
            })
        self.noise = [rng.random() for _ in range(4096)]
        self.sun = (c * rng.uniform(0.55, 0.8), r * 0.24, max(2.5, r * 0.1))
        self.mist = [(r * (0.58 + 0.14 * i), rng.uniform(0, TAU), rng.uniform(0.15, 0.35))
                     for i in range(2)]
        self.birds = []
        self.next_flock = 4.0
        self.grain = make_grain(rng, c, r)

    def frame(self, g, t, dt):
        c, r, rng = self.cols, self.rows, self.rng
        sin = math.sin
        draw_grain(g, self.grain)
        sx, sy, sr = self.sun
        draw_disc(g, sx, sy, sr, self.aspect,
                  lambda x, y, nx, ny: g.put(x, y, "█", "6") if nx * nx + ny * ny < 0.9 else None)
        noise = self.noise
        for L in self.layers:
            depth, ink, ch, lv = L["depth"], L["ink"], L["ch"], L["lv"]
            off = t * L["speed"]
            io = int(off)
            tops = []
            for x in range(-1, c + 1):
                xx = x + off
                tops.append(L["base"] - L["amp"] * (
                    0.7 * abs(sin(xx * L["f1"] + L["p1"])) ** 1.5
                    + 0.3 * (0.5 + 0.5 * sin(xx * L["f2"] + L["p2"]))))
            for x in range(c):
                top = tops[x + 1]
                yt = int(top)
                # crisp brush outline along the ridge
                d = tops[x + 2] - tops[x]
                g.put(x, yt, "/" if d < -0.5 else "\\" if d > 0.5 else "_" if abs(d) < 0.2 else "-",
                      lv)
                # ink stipple that thins out into mist below the ridge
                for y in range(max(0, yt + 1), min(r, yt + int(depth))):
                    f = 1.0 - (y - top) / depth
                    if noise[((x + io) * 131 + y * 71) & 4095] < f * f * ink:
                        g.put(x, y, ch, lv)
                    else:
                        g.put(x, y, " ", "0")      # mist hides the layers behind
        for my, ph, sp in self.mist:   # drifting mist bands
            for x in range(c):
                v = sin(x * 0.035 - t * sp + ph) + 0.5 * sin(x * 0.1 + t * 0.2 + ph)
                if v > 0.1:
                    half = 1 + int(v * 1.5)
                    for y in range(int(my) - half, int(my) + half + 1):
                        g.put(x, y, " ", "0")
                    g.put(x, int(my) - half - 1, "-" if v > 0.6 else " ", "1" if v > 0.6 else "0")
        if t >= self.next_flock:
            y0 = rng.uniform(r * 0.12, r * 0.35)
            spd = rng.uniform(5, 9)
            self.birds = [[c + i * 3 + rng.uniform(0, 2), y0 + abs(i - 2) * 0.8, spd,
                           rng.uniform(0, TAU)] for i in range(rng.randint(3, 6))]
            self.next_flock = t + rng.uniform(15, 30)
        for b in self.birds:
            b[0] -= b[2] * dt
            g.put(int(b[0]), int(b[1] + 0.4 * sin(t * 1.3 + b[3])),
                  "v" if sin(t * 6 + b[3]) > 0 else "-", "5")
        self.birds = [b for b in self.birds if b[0] > -2]


# --------------------------------------------------------------------------- koi pond

class Pond(Scene):
    """Koi gliding under lily pads while raindrops ripple the surface."""

    PATTERNS = [
        ["7", "7", "3", "7", "3", "3", "7", "3", "3"],   # red and white
        ["5", "7", "5", "3", "5", "7", "5", "5", "5"],   # black with red
        ["6", "6", "6", "7", "6", "6", "6", "6", "6"],   # all orange
    ]

    def setup(self):
        c, r, rng = self.cols, self.rows, self.rng
        a = self.aspect
        self.pads = []
        for _ in range(max(4, c // 35)):
            rad = rng.uniform(1.6, 3.2)
            self.pads.append((rng.uniform(c * 0.08, c * 0.92), rng.uniform(r * 0.1, r * 0.85),
                              rad, rng.uniform(0, TAU), rng.random() < 0.4))
        self.fish = []
        for k in range(3):
            self.fish.append({
                "cx": c * rng.uniform(0.35, 0.6), "cy": r * rng.uniform(0.35, 0.6),
                "ax": c * rng.uniform(0.22, 0.36), "ay": r * rng.uniform(0.18, 0.3),
                "w": rng.uniform(0.05, 0.09), "p1": rng.uniform(0, TAU), "p2": rng.uniform(0, TAU),
                "pat": self.PATTERNS[k % 3],
            })
        self.drops = []
        self.next_drop = 0.5
        self.grain = make_grain(rng, c, r, 1 / 110)

    def _pos(self, f, t):
        return (f["cx"] + f["ax"] * math.sin(f["w"] * t + f["p1"]),
                f["cy"] + f["ay"] * math.sin(2 * f["w"] * t + f["p2"]))

    def frame(self, g, t, dt):
        c, r, rng, a = self.cols, self.rows, self.rng, self.aspect
        sin, cos = math.sin, math.cos
        for x, y in self.grain:   # faint water texture, drifting
            g.put(int(x + t * 0.3) % c, y, "~" if (x + y) % 3 else ".", "1")
        for f in self.fish:
            segs = []
            px, py = self._pos(f, t)
            segs.append((px, py))
            tt, acc = t, 0.0
            for _ in range(400):
                tt -= 0.03
                nx, ny = self._pos(f, tt)
                acc += math.hypot(nx - px, (ny - py) * a)
                px, py = nx, ny
                if acc >= 1.1:
                    segs.append((nx, ny))
                    acc = 0.0
                    if len(segs) >= 10:
                        break
            pat = f["pat"]
            for i in range(len(segs) - 1, -1, -1):
                x, y = segs[i]
                xi, yi = int(x), int(y)
                if i == len(segs) - 1:
                    hx, hy = segs[i - 1]
                    g.put(xi, yi, "<" if hx > x else ">", pat[-1])
                    continue
                lv = pat[min(i, len(pat) - 1)]
                if i == 0:
                    g.put(xi, yi, "@", lv)
                    g.put(xi + 1, yi, "@", lv)
                elif i < 5:
                    g.put(xi, yi, "O", lv)
                    g.put(xi + 1, yi, "O", lv)
                    if i == 2:
                        bx, by = segs[1]
                        if abs(bx - x) > abs(by - y) * a:
                            g.put(xi, yi - 1, ",", "3")
                            g.put(xi, yi + 1, "'", "3")
                        else:
                            g.put(xi - 1, yi, "(", "3")
                            g.put(xi + 2, yi, ")", "3")
                else:
                    g.put(xi, yi, "o", lv)
        if t >= self.next_drop:
            self.drops.append([rng.uniform(0, c), rng.uniform(0, r), t])
            self.next_drop = t + rng.uniform(0.3, 1.4)
        alive = []
        for d in self.drops:
            age = t - d[2]
            rr = age * 2.4
            if rr > 5:
                continue
            alive.append(d)
            lv = "4" if rr < 1.5 else "3" if rr < 3 else "2" if rr < 4 else "1"
            if rr < 0.5:
                g.put(int(d[0]), int(d[1]), "o", "4")
            else:
                draw_ring(g, d[0], d[1], rr, a, lv)
                if rr > 2:
                    draw_ring(g, d[0], d[1], rr - 1.4, a, "1", dashed=True)
        self.drops = alive
        for px, py, rad, notch, flower in self.pads:
            def pad(x, y, nx, ny):
                ang = math.atan2(ny, nx)
                if abs(((ang - notch + math.pi) % TAU) - math.pi) < 0.35:
                    return
                d = nx * nx + ny * ny
                g.put(x, y, "=" if d < 0.55 else ("(" if nx < 0 else ")") if abs(nx) > 0.75 else "-",
                      "2" if d < 0.55 else "3")
            draw_disc(g, px, py, rad, a, pad)
            if flower:
                fx, fy = int(px - rad * 0.3 * a), int(py - rad * 0.2)
                g.text(fx - 1, fy, "*@*", "7")
                g.put(fx, fy - 1, "*", "6")
                g.put(fx, fy + 1, "*", "6")


# --------------------------------------------------------------------------- topographic

class Contours(Scene):
    """A topographic map whose contour lines slowly drift, with a red trail across it."""

    K = 2.4   # contour bands per unit of height

    def setup(self):
        c, r, rng = self.cols, self.rows, self.rng
        self.terms = []
        for amp in (1.0, 0.7, 0.45):
            ang = rng.uniform(0, TAU)
            fr = rng.uniform(0.035, 0.06) * (1.6 - amp)
            self.terms.append((amp, fr * math.cos(ang), fr * math.sin(ang) * self.aspect,
                               rng.uniform(0, TAU), rng.uniform(0.02, 0.05) * rng.choice([-1, 1])))
        p = rng.uniform(0, TAU)
        self.trail = []
        x0, x1 = int(c * 0.08), int(c * 0.7)
        for x in range(x0, x1):
            self.trail.append((x, r * 0.58 + r * 0.18 * math.sin(x * 0.025 + p)
                               + r * 0.05 * math.sin(x * 0.09 + p * 2)))

    def frame(self, g, t, dt):
        c, r, a = self.cols, self.rows, self.aspect
        sin, cos = math.sin, math.cos
        # separable field: sum of sin(kx*x + ky*y + phase) via angle addition
        V = [[0.0] * (c + 1) for _ in range(r + 1)]
        for amp, kx, ky, ph, sp in self.terms:
            phase = ph + t * sp
            sx = [sin(kx * x + phase) for x in range(c + 1)]
            cx = [cos(kx * x + phase) for x in range(c + 1)]
            for y in range(r + 1):
                sy, cy = sin(ky * y) * amp, cos(ky * y) * amp
                row = V[y]
                for x in range(c + 1):
                    row[x] += sx[x] * cy + cx[x] * sy
        # faint map grid
        for x in range(0, c, 32):
            for y in range(0, r, 2):
                g.put(x, y, ".", "1")
        for y in range(0, r, 12):
            for x in range(0, c, 4):
                g.put(x, y, ".", "1")
        K = self.K
        best, bx, by = -9.0, 0, 0
        for y in range(r):
            row, nrow = V[y], V[y + 1]
            rc, rl = g.ch[y], g.lv[y]
            q = [int(v * K + 100) for v in row]
            qd = [int(v * K + 100) for v in nrow]
            for x in range(c):
                q0 = q[x]
                if q0 != q[x + 1] or q0 != qd[x]:
                    gx = row[x + 1] - row[x]
                    gy = (nrow[x] - row[x]) / a
                    if abs(gx) > 2 * abs(gy):
                        ch = "|"
                    elif abs(gy) > 2 * abs(gx):
                        ch = "-"
                    else:
                        ch = "/" if gx * gy > 0 else "\\"
                    rc[x] = ch
                    rl[x] = "4" if max(q0, q[x + 1], qd[x]) % 5 == 0 else "2"
            m = max(row[:c])
            if m > best:
                best, by, bx = m, y, row.index(m)
        g.put(bx, by, "^", "6")
        g.text(bx + 2, by, "%dm" % int(1200 + best * 260), "3")
        # trail with a walker
        n = len(self.trail)
        for i, (x, y) in enumerate(self.trail):
            if (i // 2) % 2 == 0:
                ny = self.trail[i + 1][1] if i + 1 < n else y
                g.put(x, int(y), stroke_char(1, ny - y), "6")
        wx, wy = self.trail[int(t * 2.5) % n]
        g.put(wx, int(wy), "@", "7")
        sx, sy = self.trail[0]
        ex, ey = self.trail[-1]
        g.put(sx, int(sy), "o", "7")
        g.text(ex, int(ey), "X", "7")
        # compass rose (top right) and scale bar
        rose = ["  N  ", "  ^  ", "W-+-E", "  |  ", "  S  "]
        for i, line in enumerate(rose):
            g.erase(c - 10, 1 + i, c - 3, 2 + i)
            g.text(c - 9, 1 + i, line, "4")
        bar = "|----|----|  2 km"
        g.erase(2, r - 3, 4 + len(bar), r - 1)
        g.text(3, r - 2, bar, "4")


# --------------------------------------------------------------------------- zen garden

class Zen(Scene):
    """A raked zen garden: sand lines flowing around stones, a leaf drifting by."""

    SPACING = 2.0

    def setup(self):
        c, r, rng, a = self.cols, self.rows, self.rng, self.aspect
        spots = [(0.3, 0.38), (0.62, 0.3), (0.5, 0.68), (0.8, 0.55)]
        rng.shuffle(spots)
        self.stones = [(c * (fx + rng.uniform(-0.05, 0.05)), r * (fy + rng.uniform(-0.05, 0.05)),
                        rng.uniform(r * 0.06, r * 0.11)) for fx, fy in spots[:3]]
        self.static = [[None] * c for _ in range(r)]
        for y in range(r):
            for x in range(c):
                best = None
                for sx, sy, R in self.stones:
                    dx, dy = (x - sx) / a, (y - sy) / (R / R)
                    d = math.hypot(dx, dy)
                    if d <= R:
                        nx, ny = dx / R, dy / R
                        lam = -0.55 * nx - 0.6 * ny + 0.6 * math.sqrt(max(0.0, 1 - nx * nx - ny * ny))
                        best = ("@", "5") if lam < 0.3 else ("%", "5") if lam < 0.6 else (
                            "#", "4") if lam < 0.8 else ("+", "3")
                        break
                    infl = R + 3 * self.SPACING + 0.5
                    if d < infl:
                        k = (d - R) / self.SPACING
                        if (k % 1.0) < 0.45 and k > 0.4:
                            best = (ring_char(dx / d, dy / d), "3" if k < 1.5 else "2")
                        else:
                            best = (" ", "0")
                        break
                self.static[y][x] = best
        self.leaves = []
        self.next_leaf = 2.0

    def frame(self, g, t, dt):
        c, r, rng = self.cols, self.rows, self.rng
        sin = math.sin
        wave = [0.8 * sin(x * 0.04 + t * 0.12) + 0.35 * sin(x * 0.11 - t * 0.05)
                for x in range(c + 1)]
        sp = self.SPACING
        static = self.static
        for y in range(r):                       # stones and the rings around them
            st = static[y]
            rc, rl = g.ch[y], g.lv[y]
            for x in range(c):
                s = st[x]
                if s is not None and s[1] != "0":
                    rc[x], rl[x] = s
        nlines = int(r / sp) + 2
        for x in range(c):                       # continuous raked lines across open sand
            w = wave[x]
            dw = wave[x + 1] - w
            ch = "~" if abs(dw) < 0.12 else ("/" if dw > 0 else "\\")
            for k in range(nlines):
                y = int(round(k * sp - w + 1))
                if 0 <= y < r and static[y][x] is None:
                    g.ch[y][x] = ch
                    g.lv[y][x] = "2"
        if t >= self.next_leaf:
            self.leaves.append([c + 2.0, rng.uniform(r * 0.1, r * 0.8), rng.uniform(2, 4),
                                rng.uniform(0, TAU)])
            self.next_leaf = t + rng.uniform(8, 20)
        for lf in self.leaves:
            lf[0] -= lf[2] * dt
            y = lf[1] + 1.5 * sin(t * 0.6 + lf[3])
            g.put(int(lf[0]), int(y), "*" if sin(t * 2 + lf[3]) > 0 else "x", "7")
            g.put(int(lf[0]) + 1, int(y), "-", "6")
        self.leaves = [lf for lf in self.leaves if lf[0] > -3]


# --------------------------------------------------------------------------- orrery

class Orrery(Scene):
    """A drafting-table orrery: dashed orbits, annotated planets and a title block."""

    NAMES = ["ARDEN", "MIRO", "TESSA", "OKKO", "VALE"]

    def setup(self):
        c, r, rng, a = self.cols, self.rows, self.rng, self.aspect
        self.cx, self.cy = c * 0.5, r * 0.47
        amax = min(r * 0.43, c * 0.46 / a)
        self.planets = []
        for k in range(5):
            orb = amax * (0.22 + 0.78 * (k / 4) ** 1.2)
            period = 50 * (orb / amax) ** 1.5 + 12
            self.planets.append({"a": orb, "T": period, "ph": rng.uniform(0, TAU),
                                 "size": [0.6, 0.9, 1.3, 1.0, 0.7][k], "name": self.NAMES[k],
                                 "ringed": k == 3})
        self.amax = amax
        self.comet = None
        self.next_comet = 10.0

    def frame(self, g, t, dt):
        c, r, a, rng = self.cols, self.rows, self.aspect, self.rng
        cos, sin = math.cos, math.sin
        cx, cy = self.cx, self.cy
        for y in range(1, r, 3):                     # drafting dot grid
            for x in range(2, c, 6):
                g.put(x, y, ".", "1")
        for x in range(c):                            # construction axes
            if x % 4 < 2:
                g.put(x, int(cy), "-", "1")
        for y in range(r):
            if y % 2 == 0:
                g.put(int(cx), y, ":", "1")
        for p in self.planets:
            draw_ring(g, cx, cy, p["a"], a, "2", dashed=True)
        draw_disc(g, cx, cy, 1.6, a, lambda x, y, nx, ny: g.put(x, y, "@", "7"))
        for i in range(8):
            ang = TAU * i / 8 + t * 0.05
            g.put(int(cx + 3.0 * cos(ang) * a), int(cy + 3.0 * sin(ang)), "*", "6")
        for p in self.planets:
            ang = p["ph"] + TAU * t / p["T"]
            px, py = cx + p["a"] * cos(ang) * a, cy + p["a"] * sin(ang)
            draw_disc(g, px, py, p["size"], a,
                      lambda x, y, nx, ny: g.put(x, y, "@" if nx < 0 else "O", "5"))
            if p["ringed"]:
                w = int(p["size"] * a * 2.2)
                g.text(int(px) - w, int(py), "-" * (w - 2), "4")
                g.text(int(px) + 3, int(py), "-" * (w - 2), "4")
            lx, ly = int(px + p["size"] * a + 2), int(py - p["size"] - 1)
            g.put(lx - 1, ly + 1, "/", "3")
            g.text(lx, ly, "%s  a=%.1f" % (p["name"], p["a"] / self.amax * 5.2), "3")
        if self.comet is None and t >= self.next_comet:
            y0 = rng.uniform(r * 0.1, r * 0.9)
            self.comet = [-5.0, y0, rng.uniform(5, 9), rng.uniform(-0.8, 0.8)]
        if self.comet:
            cm = self.comet
            cm[0] += cm[2] * dt
            cm[1] += cm[3] * dt
            dx, dy = cm[0] - cx, (cm[1] - cy) * a
            d = math.hypot(dx, dy) or 1
            for i in range(1, 9):
                g.put(int(cm[0] + dx / d * i * 1.3), int(cm[1] + dy / d * i * 1.3 / a),
                      "~" if i < 4 else "-", "4" if i < 3 else "2")
            g.put(int(cm[0]), int(cm[1]), "*", "7")
            if cm[0] > c + 12:
                self.comet = None
                self.next_comet = t + rng.uniform(25, 60)
        # dimension line across the outer orbit
        w = int(self.amax * a)
        line = "|<" + "-" * max(0, w - 10) + " 2a=10.4 " + "-" * max(0, w - 10) + ">|"
        g.text(int(cx - len(line) / 2), 0, line, "3")
        # title block, bottom left
        box = ["+------------------------------+",
               "| ORRERY No.7     SHEET 1 OF 1 |",
               "| SCALE 1:1.5e12  %s |" % time.strftime("%Y-%m-%d"),
               "| DRAWN BY  claude             |",
               "+------------------------------+"]
        y0 = r - len(box) - 1
        g.erase(1, y0, 3 + len(box[0]), y0 + len(box))
        for i, line in enumerate(box):
            g.text(2, y0 + i, line, "4" if i in (0, 4) else "3")


# --------------------------------------------------------------------------- blossoms

class Petals(Scene):
    """An ink branch reaching in from the corner, blossoms shedding petals on the wind."""

    def setup(self):
        c, r, rng, a = self.cols, self.rows, self.rng, self.aspect
        self.cells = {}
        self.tips = []

        def line(x0, y0, x1, y1, lv, thick):
            dx, dy = x1 - x0, y1 - y0
            n = int(max(abs(dx), abs(dy) * 2)) + 1
            ch = stroke_char(dx, dy)
            for i in range(n + 1):
                x, y = int(x0 + dx * i / n), int(y0 + dy * i / n)
                self.cells[(x, y)] = (ch, lv)
                if thick:   # double the stroke for the trunk
                    self.cells[(x + 1, y)] = (ch, lv)

        def grow(x, y, ang, length, depth):
            x1 = x + math.cos(ang) * length * a
            y1 = y + math.sin(ang) * length
            line(x, y, x1, y1, "5" if depth >= 3 else "4", depth >= 4)
            if depth <= 0:
                self.tips.append((x1, y1))
                return
            for _ in range(2 if depth > 1 else rng.randint(1, 2)):
                grow(x1, y1, ang + rng.uniform(-0.65, 0.65), length * rng.uniform(0.6, 0.78),
                     depth - 1)

        grow(c + 1.0, r * 0.02, math.pi - 0.75, r * 0.3, 5)
        self.blossoms = []
        for x, y in self.tips:
            for _ in range(rng.randint(3, 6)):
                self.blossoms.append((int(x + rng.uniform(-2.5, 2.5)), int(y + rng.uniform(-1, 1)),
                                      rng.choice("*o@*"), rng.choice("67")))
        self.petals = []
        self.fallen = []
        self.moon = (c * 0.32, r * 0.36, r * 0.26)

    def frame(self, g, t, dt):
        c, r, rng, a = self.cols, self.rows, self.rng, self.aspect
        sin = math.sin
        mx, my, mr = self.moon
        draw_ring(g, mx, my, mr, a, "2", dashed=True)
        for (x, y), (ch, lv) in self.cells.items():
            g.put(x, y, ch, lv)
        for x, y, ch, lv in self.blossoms:
            g.put(x, y, ch, lv)
        wind = 2.5 + 3.5 * max(0.0, sin(t * 0.13))
        if rng.random() < dt * (1.5 + wind * 0.6) and self.blossoms:
            x, y, _, _ = rng.choice(self.blossoms)
            self.petals.append([float(x), float(y), rng.uniform(1.5, 3.5), rng.uniform(0, TAU)])
        alive = []
        for p in self.petals:
            p[0] -= (wind + 1.5 * sin(t * 1.7 + p[3])) * dt
            p[1] += p[2] * dt
            if p[1] >= r - 1:
                self.fallen.append([int(p[0]), r - 1, t])
                continue
            if p[0] > -2:
                alive.append(p)
                spin = int(t * 3 + p[3]) % 4
                g.put(int(p[0]), int(p[1]), "'`,."[spin], "7" if spin < 2 else "6")
        self.petals = alive[-200:]
        self.fallen = [f for f in self.fallen if t - f[2] < 25][-150:]
        for x, y, born in self.fallen:
            g.put(x, y, "." if t - born > 15 else ",", "6")


def draw_line(g, x0, y0, x1, y1, lv, ch=None):
    dx, dy = x1 - x0, y1 - y0
    n = int(max(abs(dx), abs(dy))) + 1
    c = ch or stroke_char(dx, dy)
    for i in range(n + 1):
        f = i / n
        g.put(int(round(x0 + dx * f)), int(round(y0 + dy * f)), c, lv)


# --------------------------------------------------------------------------- lighthouse

class Lighthouse(Scene):
    """An ink lighthouse on the rocks, sweeping its beam over an engraved sea."""

    CLOUD = ["    .--.     ", " .-(    )-.  ", "(___________)"]

    def setup(self):
        c, r, rng = self.cols, self.rows, self.rng
        self.hz = int(r * 0.62)
        self.lx = int(c * 0.3)
        self.top = max(3, int(r * 0.2))
        self.sea = [(y, (y - self.hz) / max(1, r - self.hz), rng.uniform(0, TAU))
                    for y in range(self.hz + 1, r)]
        self.clouds = [[rng.uniform(0, c), rng.uniform(r * 0.04, r * 0.3), rng.uniform(0.3, 0.9)]
                       for _ in range(3)]
        self.gulls = [[rng.uniform(0, c), rng.uniform(r * 0.08, r * 0.4), rng.uniform(0, TAU),
                       rng.uniform(1.5, 3)] for _ in range(3)]
        self.rocks = {}
        for x in range(self.lx - 16, self.lx + 17):
            h = 4.5 - abs(x - self.lx) / 3.5 + rng.uniform(-0.8, 0.8)
            if h > 0:
                self.rocks[x] = self.hz - int(h)
        self.noise = [rng.random() for _ in range(997)]

    def frame(self, g, t, dt):
        c, a = self.cols, self.aspect
        sin, cos = math.sin, math.cos
        for cl in self.clouds:
            cl[0] += cl[2] * dt
            if cl[0] > c + 2:
                cl[0] = -14
            for i, line in enumerate(self.CLOUD):
                g.text(int(cl[0]), int(cl[1]) + i, line, "2")
        for gl in self.gulls:
            gl[0] -= gl[3] * dt
            if gl[0] < -2:
                gl[0] = c + 2
            g.put(int(gl[0]), int(gl[1] + sin(t * 0.7 + gl[2])),
                  "v" if sin(t * 5 + gl[2]) > 0 else "-", "4")
        for y, d, ph in self.sea:               # engraved sea: hatch lines
            kx = 0.22 / (0.3 + d)
            thr = 0.7 - d * 0.6
            rc, rl = g.ch[y], g.lv[y]
            for x in range(c):
                v = sin(x * kx + t * 0.7 + ph) + 0.3 * sin(x * kx * 2.7 - t * 0.9)
                if v > thr:
                    rc[x] = "~" if v > thr + 0.35 else "-"
                    rl[x] = "3" if d > 0.45 else "2"
        for x in range(c):
            g.put(x, self.hz, "_", "2")
        lx, top, hz = self.lx, self.top, self.hz
        ly = top + 1
        ca = cos(t * 0.6)
        side = 1 if ca > 0 else -1
        noise = self.noise
        for i in range(1, int(c * 0.6 * abs(ca))):   # the beam
            x = lx + side * (3 + i)
            half = 0.4 + i * 0.05
            fade = 1 - i / (c * 0.6)
            yt, yb = int(round(ly - half)), int(round(ly + half))
            lv = "6" if fade > 0.45 else "2"
            g.put(x, yt, "-", lv)
            g.put(x, yb, "-", lv)
            for y in range(yt + 1, yb):
                if noise[(x * 31 + y * 17) % 997] < fade * 0.35:
                    g.put(x, y, ".", "6")
        glow = abs(ca) < 0.3                       # beam pointing at us
        if glow:
            for k in range(8):
                aa = TAU * k / 8
                g.put(int(lx + cos(aa) * 4 * a), int(ly + sin(aa) * 2), "*" if k % 2 else ".", "7")
        prev = None
        for y in range(top + 3, hz + 1):            # tower with painted bands
            f = (y - top) / max(1, hz - top)
            half = int(2 + f * 2.5)
            band = ((y - top) // 3) % 2 == 0
            for x in range(lx - half + 1, lx + half):
                g.put(x, y, "#" if band else " ", "6" if band else "0")
            tapered = prev is not None and half > prev
            g.put(lx - half, y, "/" if tapered else "|", "5")
            g.put(lx + half, y, "\\" if tapered else "|", "5")
            prev = half
        g.put(lx, (top + hz) // 2, "o", "5")
        g.text(lx - 1, hz, "[ ]", "5")
        g.put(lx, top - 1, "|", "5")
        g.text(lx - 1, top, "/^\\", "5")
        g.put(lx - 2, top + 1, "|", "5")
        g.put(lx + 2, top + 1, "|", "5")
        g.text(lx - 1, top + 1, "@@@" if glow else "###", "7" if glow else "5")
        g.text(lx - 3, top + 2, "=======", "5")
        for x, ry in self.rocks.items():            # rocks at the foot
            if abs(x - lx) <= 4:
                continue
            for y in range(ry, hz + 1):
                if y == ry:
                    g.put(x, y, "^", "4")
                elif (x + y) % 2:
                    g.put(x, y, ":", "3")


# --------------------------------------------------------------------------- typewriter

class Typewriter(Scene):
    """A sheet in a typewriter: short original lines typed one key at a time."""

    LINES = [
        "a cidade acorda devagar, uma janela de cada vez.",
        "o café arrefece ao lado do teclado.",
        "há uma música baixa a tocar noutra sala.",
        "o rio leva a luz da tarde até ao mar.",
        "escrevo só para ouvir as teclas.",
        "amanhã talvez chova. hoje não.",
        "as gaivotas discutem em cima dos telhados.",
        "o elétrico sobe a colina sem pressa nenhuma.",
        "guardo esta linha para mais tarde.",
        "o papel aceita tudo, até os erros.",
        "lá fora, o vento muda de ideias.",
        "a tinta seca antes de eu decidir o fim.",
        "conto as horas pelo barulho das chávenas.",
        "uma página em branco também é um começo.",
    ]

    def setup(self):
        c, r = self.cols, self.rows
        self.width = max(30, min(64, int(c * 0.5)))
        self.x0 = max(6, int(c * 0.5 - self.width / 2))
        self.y0 = 2
        self.nlines = max(3, min(12, (r - 14) // 2))
        self.new_page(0.0)

    def new_page(self, t):
        rng = self.rng
        order = self.LINES[:]
        rng.shuffle(order)
        self.page = [ln[:self.width] for ln in order[:self.nlines]]
        self.levels = [["5" if rng.random() < 0.8 else "4" for _ in ln] for ln in self.page]
        self.line, self.col = 0, 0
        self.next_key = t + 1.5
        self.done_at = None
        self.ding = -9.0

    def frame(self, g, t, dt):
        rng = self.rng
        x0, y0, w = self.x0, self.y0, self.width
        g.text(x0 + w - 14, y0, time.strftime("%d . %m . %Y"), "3")
        for x in range(x0 - 4, x0 + w + 4):
            g.put(x, y0 + 1, "_", "2")
        for i in range(self.nlines):
            y = y0 + 3 + i * 2
            for x in range(x0, x0 + w, 2):
                g.put(x, y + 1, ".", "1")
        for y in range(y0 + 2, y0 + 3 + self.nlines * 2):
            g.put(x0 - 2, y, "|", "6")
        n = 0
        while self.done_at is None and t >= self.next_key and n < 6:
            n += 1
            ln = self.page[self.line]
            self.col += 1
            ch = ln[self.col - 1] if self.col <= len(ln) else ""
            gap = rng.uniform(0.05, 0.17) + (rng.uniform(0.1, 0.5) if ch == " " else 0)
            if self.col >= len(ln):
                self.ding = t
                self.line += 1
                self.col = 0
                gap = rng.uniform(1.2, 2.2)
                if self.line >= len(self.page):
                    self.done_at = t
            self.next_key = t + gap
        for i in range(min(self.line + 1, len(self.page))):
            ln = self.page[i]
            k = len(ln) if i < self.line else self.col
            y = y0 + 3 + i * 2
            lvs = self.levels[i]
            for j in range(k):
                if ln[j] != " ":
                    g.put(x0 + j, y, ln[j], lvs[j])
            if i == self.line and self.done_at is None and int(t * 2) % 2 == 0:
                g.put(x0 + k, y, "_", "7")
        if t - self.ding < 0.7:
            g.text(x0 + w + 2, y0 + 3 + max(0, self.line - 1) * 2, "*ding*", "6")
        g.text(x0 + w // 2 - 2, y0 + 4 + self.nlines * 2, "- 1 -", "2")
        if self.done_at is not None and t - self.done_at > 10:
            self.new_page(t)


# --------------------------------------------------------------------------- star chart

class StarChart(Scene):
    """A paper star chart turning slowly, with invented constellations traced in ink."""

    NAMES = ["O FAROL", "A CHAVE", "O MOCHO", "A CHÁVENA", "A BICICLETA", "O GUARDA-CHUVA"]

    def setup(self):
        c, r, rng, a = self.cols, self.rows, self.rng, self.aspect
        self.cx, self.cy = c * 0.5, r * 0.48
        self.R = min(r * 0.42, c * 0.38 / a)
        self.stars = [(math.sqrt(rng.random()) * 0.97, rng.uniform(0, TAU), rng.random())
                      for _ in range(140)]
        self.groups = []
        for k, name in enumerate(self.NAMES):
            gr = rng.uniform(0.3, 0.78)
            ga = k * TAU / len(self.NAMES) + rng.uniform(-0.3, 0.3)
            gx, gy = gr * math.cos(ga), gr * math.sin(ga)
            idx = []
            for _ in range(rng.randint(4, 6)):
                px, py = gx + rng.uniform(-0.13, 0.13), gy + rng.uniform(-0.13, 0.13)
                self.stars.append((math.hypot(px, py), math.atan2(py, px), rng.uniform(0.75, 1.0)))
                idx.append(len(self.stars) - 1)
            edges = [(idx[i], idx[i + 1]) for i in range(len(idx) - 1)]
            if len(idx) > 4:
                edges.append((idx[1], idx[-1]))
            self.groups.append((name, idx, edges))

    def frame(self, g, t, dt):
        cx, cy, R, a = self.cx, self.cy, self.R, self.aspect
        cos, sin = math.cos, math.sin
        rot = t * 0.012
        draw_ring(g, cx, cy, R * 0.33, a, "1", dashed=True)
        draw_ring(g, cx, cy, R * 0.66, a, "1", dashed=True)
        for k in range(12):
            ang = rot + k * TAU / 12
            for i in range(3, int(R * 2), 2):
                f = i / (R * 2)
                g.put(int(cx + cos(ang) * R * f * a), int(cy + sin(ang) * R * f), ".", "1")
        pos = [(cx + rad * R * cos(ang + rot) * a, cy + rad * R * sin(ang + rot))
               for rad, ang, mag in self.stars]
        for name, idx, edges in self.groups:
            for i, j in edges:
                draw_line(g, pos[i][0], pos[i][1], pos[j][0], pos[j][1], "2")
        for (x, y), (rad, ang, mag) in zip(pos, self.stars):
            g.put(int(x), int(y), "*" if mag > 0.85 else "+" if mag > 0.6 else ".",
                  "5" if mag > 0.85 else "4" if mag > 0.6 else "3")
        for name, idx, edges in self.groups:
            mx = sum(pos[i][0] for i in idx) / len(idx)
            my = max(pos[i][1] for i in idx)
            g.text(int(mx - len(name) / 2), int(my + 2), name, "3")
        pa = t * 0.025
        g.put(int(cx + cos(pa) * R * 0.55 * a), int(cy + sin(pa) * R * 0.25), "@", "7")
        draw_ring(g, cx, cy, R, a, "4")
        for k in range(48):
            ang = rot + k * TAU / 48
            g.put(int(cx + cos(ang) * (R + 0.35) * a), int(cy + sin(ang) * (R + 0.35)), "'", "2")
        for h in range(0, 24, 3):
            ang = rot + h * TAU / 24
            lbl = "%dh" % h
            g.text(int(cx + cos(ang) * (R + 2.2) * a - len(lbl) / 2),
                   int(cy + sin(ang) * (R + 1.6)), lbl, "3")


# --------------------------------------------------------------------------- vines

class Vines(Scene):
    """Ink vines climbing from the bottom, unfurling leaves and flowers, then starting over."""

    RATE = 2.5

    def setup(self):
        self.flies = [[self.rng.uniform(0, self.cols), self.rng.uniform(0, self.rows * 0.6),
                       self.rng.uniform(0, TAU)] for _ in range(2)]
        self.restart(0.0)

    def restart(self, t):
        c, r, rng = self.cols, self.rows, self.rng
        self.t0 = t
        self.stems = []
        for _ in range(max(4, c // 26)):
            x0 = rng.uniform(c * 0.04, c * 0.8)
            h = int(rng.uniform(r * 0.4, r * 0.88))
            amp, fr = rng.uniform(1.5, 4), rng.uniform(0.15, 0.3)
            ph, drift = rng.uniform(0, TAU), rng.uniform(-0.15, 0.15)
            pts = [(x0 + amp * math.sin(k * fr + ph) + k * drift, r - 1 - k) for k in range(h)]
            leaves = []
            side = rng.choice([-1, 1])
            k = rng.randint(3, 5)
            while k < h - 2:
                leaves.append((k, side))
                side = -side
                k += rng.randint(3, 5)
            self.stems.append({"pts": pts, "leaves": leaves, "delay": rng.uniform(0, 6)})
        self.end = max(s["delay"] + len(s["pts"]) / self.RATE for s in self.stems) + 30

    def frame(self, g, t, dt):
        el = t - self.t0
        fading = el > self.end - 3
        stem_lv, leaf_lv = ("2", "1") if fading else ("4", "3")
        for s in self.stems:
            pts = s["pts"]
            n = int(min(len(pts), max(0.0, (el - s["delay"]) * self.RATE)))
            for k in range(n):
                x, y = pts[k]
                nx = pts[k + 1][0] if k + 1 < len(pts) else x
                g.put(int(round(x)), y, stroke_char(nx - x, -1), stem_lv)
            for k, side in s["leaves"]:
                if k + 2 < n:
                    x, y = pts[k]
                    xi = int(round(x))
                    g.put(xi + side, y, "-", stem_lv)
                    g.put(xi + 2 * side, y, "%", leaf_lv)
                    g.put(xi + 3 * side, y, ">" if side > 0 else "<", leaf_lv)
            if pts and n >= len(pts):
                x, y = pts[-1]
                xi = int(round(x))
                g.put(xi, y - 1, "@", "2" if fading else "7")
                for dx_, dy_ in ((-1, -1), (1, -1), (0, -2), (-2, -1), (2, -1), (0, 0)):
                    g.put(xi + dx_, y + dy_, "*", "2" if fading else "6")
        for f in self.flies:
            f[0] = (f[0] + math.sin(t * 0.3 + f[2]) * dt * 4) % self.cols
            f[1] = min(max(f[1] + math.cos(t * 0.4 + f[2] * 2) * dt * 2, 1), self.rows - 2)
            g.text(int(f[0]), int(f[1]), "}{" if math.sin(t * 8 + f[2]) > 0 else ")(", "6")
        if el > self.end:
            self.restart(t)


# --------------------------------------------------------------------------- weather

class Weather(Scene):
    """A weather chart: drifting highs and lows, isobars, wind arrows and fronts."""

    def setup(self):
        c, r, rng = self.cols, self.rows, self.rng
        self.centers = [[rng.uniform(c * 0.15, c * 0.85), rng.uniform(r * 0.15, r * 0.8),
                         rng.uniform(-1.2, 1.2), rng.uniform(-0.4, 0.4), kind,
                         rng.uniform(r * 0.22, r * 0.35)] for kind in (-1, -1, 1, 1)]
        self.F = None
        self.n = 0

    def compute(self):
        c, r, a = self.cols, self.rows, self.aspect
        F = [[1013.0] * (c + 1) for _ in range(r + 1)]
        for cx, cy, _, _, kind, s in self.centers:
            s2 = s * s
            dx2 = [((x - cx) / a) ** 2 for x in range(c + 1)]
            amp = 18.0 * kind
            for y in range(r + 1):
                dy2 = (y - cy) ** 2
                row = F[y]
                for x in range(c + 1):
                    row[x] += amp / (1.0 + (dx2[x] + dy2) / s2)
        self.F = F

    def frame(self, g, t, dt):
        c, r, a = self.cols, self.rows, self.aspect
        for cn in self.centers:
            cn[0] += cn[2] * dt
            cn[1] += cn[3] * dt
            if not c * 0.1 < cn[0] < c * 0.9:
                cn[2] = -cn[2]
            if not r * 0.1 < cn[1] < r * 0.85:
                cn[3] = -cn[3]
        if self.F is None or self.n % 4 == 0:
            self.compute()
        self.n += 1
        F = self.F
        for y in range(r):                           # isobars every 6 hPa
            row, nrow = F[y], F[y + 1]
            q = [int(v // 6) for v in row]
            qd = [int(v // 6) for v in nrow]
            rc, rl = g.ch[y], g.lv[y]
            for x in range(c):
                q0 = q[x]
                if q0 != q[x + 1] or q0 != qd[x]:
                    gx = row[x + 1] - row[x]
                    gy = (nrow[x] - row[x]) / a
                    if abs(gx) > 2 * abs(gy):
                        ch = "|"
                    elif abs(gy) > 2 * abs(gx):
                        ch = "-"
                    else:
                        ch = "/" if gx * gy > 0 else "\\"
                    rc[x], rl[x] = ch, "3"
        for y in range(3, r - 2, 6):                 # wind arrows, blowing along the isobars
            for x in range(5, c - 3, 14):
                gx = F[y][x + 1] - F[y][x - 1]
                gy = (F[y + 1][x] - F[y - 1][x]) / a
                if math.hypot(gx, gy) < 0.25:
                    continue
                wx, wy = -gy, gx
                if abs(wx) > abs(wy) * 1.2:
                    g.text(x - 1, y, "->" if wx > 0 else "<-", "2")
                else:
                    g.put(x, y, "v" if wy > 0 else "^", "2")
                    g.put(x, y - 1 if wy > 0 else y + 1, "|", "2")
        for cx, cy, _, _, kind, s in self.centers:
            xi, yi = int(cx), int(cy)
            p = int(round(F[min(r, max(0, yi))][min(c, max(0, xi))]))
            g.erase(xi - 3, yi - 1, xi + 4, yi + 2)
            if kind < 0:
                for k in range(1, 22):              # cold front
                    g.put(int(xi - k * 1.2), int(yi + k * 0.55 + 1.2 * math.sin(k * 0.35)),
                          "^" if k % 3 == 0 else "-", "6")
                for k in range(1, 16):              # warm front
                    g.put(int(xi + k * 1.4), int(yi + 1 + k * 0.25), "o" if k % 3 == 0 else "-", "7")
                g.put(xi, yi, "L", "7")
                g.text(xi - 1, yi + 1, str(p), "6")
            else:
                g.put(xi, yi, "H", "5")
                g.text(xi - 1, yi + 1, str(p), "4")


# --------------------------------------------------------------------------- gears

class Gears(Scene):
    """A blueprint gear train meshing and turning, with dimension notes."""

    def setup(self):
        c, r, rng, a = self.cols, self.rows, self.rng, self.aspect
        R0 = min(r * 0.2, c * 0.13 / a)
        sizes = [1.0, 0.62, 0.85, 0.45, 0.7]
        angles = [None, -0.25, 0.7, -0.6, 0.35]
        self.gears = []
        x, y = c * 0.2, r * 0.48
        omega = 0.25
        prevR = None
        for k, sz in enumerate(sizes):
            R = R0 * sz
            if prevR is not None:
                dist = prevR + R + 1.1
                x, y = x + math.cos(angles[k]) * dist * a, y + math.sin(angles[k]) * dist
                omega = -omega * prevR / R
            if x + (R + 1) * a > c - 2 or y - R < 1 or y + R > r - 2:
                break
            self.gears.append([x, y, R, max(8, int(round(R * 3.0))), rng.uniform(0, TAU), omega])
            prevR = R

    def frame(self, g, t, dt):
        c, r, a = self.cols, self.rows, self.aspect
        cos, sin = math.cos, math.sin
        for y in range(1, r, 3):
            for x in range(2, c, 6):
                g.put(x, y, ".", "1")
        for i in range(len(self.gears) - 1):         # centre lines between gears
            x0, y0 = self.gears[i][0], self.gears[i][1]
            x1, y1 = self.gears[i + 1][0], self.gears[i + 1][1]
            n = int(max(abs(x1 - x0), abs(y1 - y0)))
            for k in range(0, n, 3):
                f = k / max(1, n)
                g.put(int(x0 + (x1 - x0) * f), int(y0 + (y1 - y0) * f), "-", "1")
        for k, (cx, cy, R, teeth, ph, om) in enumerate(self.gears):
            rot = ph + om * t
            accent = k == 1
            draw_ring(g, cx, cy, R, a, "6" if accent else "4")
            for j in range(teeth):
                ang = rot + j * TAU / teeth
                for rad in (R + 0.5, R + 1.0):
                    g.put(int(round(cx + cos(ang) * rad * a)), int(round(cy + sin(ang) * rad)),
                          "#", "7" if accent else "5")
            draw_ring(g, cx, cy, max(0.8, R * 0.22), a, "4")
            for j in range(5):
                ang = rot + j * TAU / 5
                draw_line(g, cx + cos(ang) * R * 0.3 * a, cy + sin(ang) * R * 0.3,
                          cx + cos(ang) * R * 0.88 * a, cy + sin(ang) * R * 0.88, "3")
            g.put(int(cx), int(cy), "+", "5")
            g.text(int(cx + R * a * 0.75), int(cy - R - 1.6), "z=%d  d=%d" % (teeth, int(R * 8)), "2")


# --------------------------------------------------------------------------- seismograph

class Seismo(Scene):
    """A chart recorder: pens tracing quiet signals, and now and then a tremor."""

    SPEED = 5.0

    def setup(self):
        c, r, rng = self.cols, self.rows, self.rng
        self.pen = c - 9
        n = 5 if r >= 34 else 3
        self.chans = [{"y": r * (0.14 + 0.62 * i / max(1, n - 1)),
                       "ph": [rng.uniform(0, TAU) for _ in range(3)],
                       "buf": [0.0] * self.pen, "lv": "6" if i == 1 else "4",
                       "name": "CH%d %s" % (i + 1, ["N-S", "E-W", "Z", "N-S", "E-W"][i])}
                      for i in range(n)]
        self.scale = r * 0.055
        self.acc = 0.0
        self.quakes = []
        self.next_quake = rng.uniform(15, 30)

    def sample(self, ch, i, t):
        ph = ch["ph"]
        v = 0.25 * math.sin(t * 7.3 + ph[0]) + 0.15 * math.sin(t * 13.1 + ph[1]) \
            + 0.2 * (self.rng.random() - 0.5)
        for q0, amp in self.quakes:
            dtq = t - q0 - i * 0.6
            if 0 < dtq < 10:
                v += amp * math.exp(-dtq * 0.55) * math.sin(dtq * (9 + i))
        return v

    def frame(self, g, t, dt):
        c, r, rng = self.cols, self.rows, self.rng
        if t >= self.next_quake:
            self.quakes = (self.quakes + [(t, rng.uniform(2.0, 4.5))])[-3:]
            self.next_quake = t + rng.uniform(25, 60)
        self.acc += dt * self.SPEED
        while self.acc >= 1:
            self.acc -= 1
            for i, ch in enumerate(self.chans):
                ch["buf"].append(self.sample(ch, i, t))
                del ch["buf"][0]
        pen = self.pen
        scroll = t * self.SPEED
        now = time.time()
        for x in range(pen, -1, -1):                # scrolling time grid
            k = int(scroll + x)
            if k % 10 == 0:
                for y in range(2, r - 2, 2):
                    g.put(x, y, ".", "1")
            if k % 50 == 0 and x > 8:
                stamp = time.strftime("%H:%M:%S", time.localtime(now - (pen - x) / self.SPEED))
                g.text(x - 4, 0, stamp, "2")
        sc = self.scale
        for ch in self.chans:
            cy = ch["y"]
            for x in range(0, pen, 3):
                g.put(x, int(cy), "-", "1")
            buf, lv = ch["buf"], ch["lv"]
            prev = int(round(cy - buf[0] * sc))
            for x in range(1, pen):
                y = int(round(cy - buf[x] * sc))
                if y == prev:
                    g.put(x, y, "-", lv)
                elif abs(y - prev) == 1:
                    g.put(x, y, "/" if y < prev else "\\", lv)
                else:
                    step = 1 if y > prev else -1
                    for yy in range(prev, y + step, step):
                        g.put(x, yy, "|", lv)
                prev = y
            g.put(pen, prev, "<", "7")
            for x in range(pen + 1, c - 2):
                g.put(x, prev, "-", "3")
            g.put(c - 2, prev, "o", "4")
            g.text(1, int(cy) - 2, ch["name"], "3")
        g.text(1, r - 1, "estação LX-07   5 mm/s   ganho x20", "3")


# --------------------------------------------------------------------------- marbling

class Marbling(Scene):
    """Suminagashi: rings of ink floating on water, slowly drawn out by the current."""

    SP = 2.4

    def setup(self):
        c, r, rng = self.cols, self.rows, self.rng
        self.maxr = r * 0.32
        self.drops = [[rng.uniform(c * 0.12, c * 0.88) / self.aspect, rng.uniform(r * 0.15, r * 0.85),
                       -rng.uniform(5, 40), rng.randrange(3)] for _ in range(4)]
        self.next_drop = 25.0
        self.cache = None
        self.n = 0

    def frame(self, g, t, dt):
        # the ink moves slowly, so the field is recomputed every other frame
        self.n += 1
        if self.cache is not None and self.n % 2:
            for y, (cs, ls) in enumerate(self.cache):
                for x, ch in cs:
                    g.ch[y][x] = ch
                    g.lv[y][x] = ls[x]
            return
        self.render(g, t)
        self.cache = [([(x, ch) for x, ch in enumerate(g.ch[y]) if g.lv[y][x] != "0"], g.lv[y][:])
                      for y in range(self.rows)]

    def render(self, g, t):
        c, r, a, rng = self.cols, self.rows, self.aspect, self.rng
        sin, sqrt = math.sin, math.sqrt
        if t >= self.next_drop:
            self.drops.pop(0)
            self.drops.append([rng.uniform(c * 0.1, c * 0.9) / a, rng.uniform(r * 0.1, r * 0.9),
                               t, rng.randrange(3)])
            self.next_drop = t + rng.uniform(25, 45)
        wx = [2.0 * sin(y * 0.16 + t * 0.21) + 1.2 * sin(y * 0.05 - t * 0.13) for y in range(r)]
        wy = [0.9 * sin(x * 0.035 + t * 0.17) for x in range(c)]
        sp = self.SP
        # each drop spreads out from a point, then stays put while the current drags it
        drops = [(dx, dy, min(self.maxr, 2.0 + (t - born) * 0.5), off)
                 for dx, dy, born, off in self.drops]
        inv_a = 1.0 / a
        LV, CH = "642", "~=-"
        for y in range(r):
            rc, rl = g.ch[y], g.lv[y]
            sh = wx[y]
            for x in range(c):
                X = (x + sh) * inv_a
                Y = y + wy[x]
                best, bd = 1e18, None
                for d in drops:
                    d2 = (X - d[0]) ** 2 + (Y - d[1]) ** 2
                    if d2 < best:
                        best, bd = d2, d
                dist = sqrt(best)
                if dist > bd[2]:
                    continue
                u = (bd[2] - dist) / sp
                if (u % 1.0) < 0.42:
                    k = (int(u) + bd[3]) % 3
                    rc[x], rl[x] = CH[k], LV[k]


# --------------------------------------------------------------------------- spirograph

class Spirograph(Scene):
    """A spirograph pen tracing a hypotrochoid, loop after loop."""

    def setup(self):
        self.prev = {}
        self.inks = ["6", "5", "4"]
        self.ink_i = 0
        self.new_pattern(0.0)

    def new_pattern(self, t):
        rng = self.rng
        self.R = rng.choice([96, 100, 105, 112, 120])
        self.rr = rng.choice([x for x in range(25, 75) if math.gcd(self.R, x) >= 4])
        self.d = self.rr * rng.uniform(0.55, 1.15)
        self.total = TAU * self.rr / math.gcd(self.R, self.rr)
        ext = self.R - self.rr + self.d
        self.S = min(self.rows * 0.44, self.cols * 0.42 / self.aspect) / ext
        self.speed = self.total / rng.uniform(70, 110)
        self.theta = 0.0
        self.drawn = {}
        self.lv = self.inks[self.ink_i % 3]
        self.ink_i += 1
        self.done_at = None

    def point(self, th):
        R, rr, d, S = self.R, self.rr, self.d, self.S
        k = (R - rr) / rr
        x = (R - rr) * math.cos(th) + d * math.cos(k * th)
        y = (R - rr) * math.sin(th) - d * math.sin(k * th)
        return self.cols / 2 + x * S * self.aspect, self.rows * 0.48 + y * S

    def frame(self, g, t, dt):
        a = self.aspect
        for (x, y), ch in self.prev.items():      # the previous drawing, faded
            g.put(x, y, ch, "1")
        if self.done_at is None:
            target = min(self.total, self.theta + self.speed * dt)
            px, py = self.point(self.theta)
            while self.theta < target:
                self.theta = min(target, self.theta + 0.01)
                nx, ny = self.point(self.theta)
                self.drawn[(int(nx), int(ny))] = stroke_char(nx - px, ny - py)
                px, py = nx, ny
            if self.theta >= self.total:
                self.done_at = t
        for (x, y), ch in self.drawn.items():
            g.put(x, y, ch, self.lv)
        if self.done_at is None:
            th, S, R, rr = self.theta, self.S, self.R, self.rr
            cx, cy = self.cols / 2, self.rows * 0.48
            draw_ring(g, cx, cy, R * S, a, "1", dashed=True)
            wx, wy = cx + (R - rr) * math.cos(th) * S * a, cy + (R - rr) * math.sin(th) * S
            draw_ring(g, wx, wy, rr * S, a, "2", dashed=True)
            px, py = self.point(th)
            draw_line(g, wx, wy, px, py, "2", ".")
            g.put(int(px), int(py), "@", "7")
        elif t - self.done_at > 15:
            self.prev = dict(self.drawn)
            self.new_pattern(t)


# --------------------------------------------------------------------------- maze

class Maze(Scene):
    """A maze carved out of the paper, then solved with a red pencil."""

    def setup(self):
        self.reset()

    def reset(self):
        c, r = self.cols, self.rows
        self.mw, self.mh = max(4, (c - 1) // 4), max(3, (r - 1) // 2)
        mw, mh = self.mw, self.mh
        self.right = [[True] * mw for _ in range(mh)]
        self.down = [[True] * mw for _ in range(mh)]
        self.seen = [[False] * mw for _ in range(mh)]
        self.start, self.goal = (0, mh - 1), (mw - 1, 0)
        self.stack = [self.start]
        self.seen[mh - 1][0] = True
        self.phase = "carve"
        self.rate = mw * mh / 12.0
        self.acc = 0.0
        self.explored = set()
        self.path = []
        self.shown = 0.0
        self.hold = None

    def step_carve(self):
        x, y = self.stack[-1]
        opts = [(nx, ny) for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))
                if 0 <= nx < self.mw and 0 <= ny < self.mh and not self.seen[ny][nx]]
        if not opts:
            self.stack.pop()
            return
        nx, ny = self.rng.choice(opts)
        if nx > x:
            self.right[y][x] = False
        elif nx < x:
            self.right[y][nx] = False
        elif ny > y:
            self.down[y][x] = False
        else:
            self.down[ny][x] = False
        self.seen[ny][nx] = True
        self.stack.append((nx, ny))

    def neighbours(self, x, y):
        if x + 1 < self.mw and not self.right[y][x]:
            yield x + 1, y
        if x > 0 and not self.right[y][x - 1]:
            yield x - 1, y
        if y + 1 < self.mh and not self.down[y][x]:
            yield x, y + 1
        if y > 0 and not self.down[y - 1][x]:
            yield x, y - 1

    def frame(self, g, t, dt):
        self.acc += dt * self.rate
        steps = int(self.acc)
        self.acc -= steps
        if self.phase == "carve":
            for _ in range(steps):
                if not self.stack:
                    self.phase = "solve"
                    self.queue = [self.start]
                    self.parent = {self.start: None}
                    break
                self.step_carve()
        elif self.phase == "solve":
            for _ in range(max(1, steps // 2)):
                if not self.queue:
                    break
                cur = self.queue.pop(0)
                self.explored.add(cur)
                if cur == self.goal:
                    p = cur
                    while p is not None:
                        self.path.append(p)
                        p = self.parent[p]
                    self.path.reverse()
                    self.phase = "path"
                    break
                for nb in self.neighbours(*cur):
                    if nb not in self.parent:
                        self.parent[nb] = cur
                        self.queue.append(nb)
        elif self.phase == "path":
            self.shown += dt * 12
            if self.shown >= len(self.path):
                self.phase = "hold"
                self.hold = t
        elif t - self.hold > 15:
            self.reset()
            return
        for y in range(self.mh):
            for x in range(self.mw):
                X, Y = 4 * x, 2 * y
                if not self.seen[y][x]:
                    g.text(X + 1, Y + 1, "///", "1")
                if y == 0:
                    g.text(X + 1, Y, "---", "4")
                if self.down[y][x]:
                    g.text(X + 1, Y + 2, "---", "4")
                if x == 0:
                    g.put(X, Y + 1, "|", "4")
                if self.right[y][x]:
                    g.put(X + 4, Y + 1, "|", "4")
                for cx_, cy_ in ((X, Y), (X + 4, Y), (X, Y + 2), (X + 4, Y + 2)):
                    g.put(cx_, cy_, "+", "4")
        for x, y in self.explored:
            g.put(4 * x + 2, 2 * y + 1, ".", "2")
        n = min(len(self.path), int(self.shown) if self.phase == "path" else len(self.path))
        for i in range(n):
            x, y = self.path[i]
            g.put(4 * x + 2, 2 * y + 1, "o", "7")
            if i + 1 < n:
                nx, ny = self.path[i + 1]
                if ny == y:
                    g.text(4 * min(x, nx) + 3, 2 * y + 1, "---", "6")
                else:
                    g.put(4 * x + 2, 2 * min(y, ny) + 2, "|", "6")
        g.put(4 * self.start[0] + 2, 2 * self.start[1] + 1, "S", "7")
        g.put(4 * self.goal[0] + 2, 2 * self.goal[1] + 1, "X", "7")


SCENE_LABELS = {"sumi": "Ink Mountains", "pond": "Koi Pond", "contours": "Topographic",
                "zen": "Zen Garden", "orrery": "Orrery", "petals": "Blossoms",
                "lighthouse": "Lighthouse", "typewriter": "Typewriter", "starchart": "Star Chart",
                "vines": "Vines", "weather": "Weather Map", "gears": "Gears",
                "seismo": "Seismograph", "marbling": "Marbling", "spirograph": "Spirograph",
                "maze": "Maze"}

SCENES = {
    "sumi": Sumi,
    "pond": Pond,
    "contours": Contours,
    "zen": Zen,
    "orrery": Orrery,
    "petals": Petals,
    "lighthouse": Lighthouse,
    "typewriter": Typewriter,
    "starchart": StarChart,
    "vines": Vines,
    "weather": Weather,
    "gears": Gears,
    "seismo": Seismo,
    "marbling": Marbling,
    "spirograph": Spirograph,
    "maze": Maze,
}
