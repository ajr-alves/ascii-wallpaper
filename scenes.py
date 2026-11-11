"""ASCII scenes. Each scene draws into a Grid every frame.

Levels (the second char per cell) pick a colour from the theme:
  '0' = empty, '1'..'5' = dim -> bright, '6' = accent, '7' = bright accent.
"""
import math
import time

TAU = math.tau


class Grid:
    def __init__(self, cols, rows):
        self.cols, self.rows = cols, rows
        self._bc = [" "] * cols
        self._bl = ["0"] * cols
        self.clear()

    def clear(self):
        self.ch = [self._bc[:] for _ in range(self.rows)]
        self.lv = [self._bl[:] for _ in range(self.rows)]

    def put(self, x, y, c, lv):
        if 0 <= x < self.cols and 0 <= y < self.rows:
            self.ch[y][x] = c
            self.lv[y][x] = lv

    def text(self, x, y, s, lv):
        for i, c in enumerate(s):
            if c != " ":
                self.put(x + i, y, c, lv)

    def erase(self, x0, y0, x1, y1):
        for y in range(max(0, y0), min(self.rows, y1)):
            rc, rl = self.ch[y], self.lv[y]
            for x in range(max(0, x0), min(self.cols, x1)):
                rc[x] = " "
                rl[x] = "0"

    def out(self):
        return ["".join(r) for r in self.ch], ["".join(r) for r in self.lv]


class Scene:
    def __init__(self, cols, rows, rng, aspect):
        self.cols, self.rows, self.rng, self.aspect = cols, rows, rng, aspect
        self.setup()

    def setup(self):
        pass

    def frame(self, g, t, dt):
        raise NotImplementedError


def make_stars(rng, cols, rows, per_cell):
    n = max(8, int(cols * rows * per_cell))
    return [(rng.randrange(cols), rng.randrange(max(1, rows)), rng.uniform(0, TAU),
             rng.uniform(0.4, 2.2)) for _ in range(n)]


def draw_stars(g, stars, t, below=None):
    for x, y, ph, sp in stars:
        if below is not None and y >= below[x] - 1:
            continue
        v = math.sin(ph + t * sp)
        if v > 0.92:
            g.put(x, y, "*", "5")
        elif v > 0.55:
            g.put(x, y, "+", "3")
        elif v > -0.2:
            g.put(x, y, ".", "2")
        else:
            g.put(x, y, ".", "1")


def draw_disc(g, cx, cy, r, aspect, fn):
    """Call fn(x, y, nx, ny) for each cell inside an ellipse-corrected circle."""
    for dy in range(-int(r), int(r) + 1):
        hw = math.sqrt(max(0.0, r * r - dy * dy)) * aspect
        for dx in range(-int(hw), int(hw) + 1):
            fn(int(cx + dx), int(cy + dy), dx / (r * aspect), dy / r)


# --------------------------------------------------------------------------- rain

class Rain(Scene):
    """Rainy night over a city skyline, windows flickering on and off."""

    def setup(self):
        c, r, rng = self.cols, self.rows, self.rng
        self.top = [r] * c
        self.buildings = []
        self.windows = []
        x = rng.randint(-4, 0)
        while x < c:
            w = rng.randint(7, 17)
            h = rng.randint(max(4, r // 6), max(6, int(r * 0.55)))
            top = r - h
            self.buildings.append((x, x + w, top, rng.random() < 0.25))
            for xx in range(max(0, x), min(c, x + w)):
                self.top[xx] = top
            for wy in range(top + 2, r - 1, 2):
                for wx in range(x + 2, x + w - 2, 3):
                    if 0 <= wx < c:
                        self.windows.append((wx, wy, rng.uniform(0, TAU),
                                             rng.uniform(0.01, 0.12), rng.random()))
            x += w + rng.randint(1, 4)
        n = max(30, c * r // 22)
        self.drops = [self._new_drop(rng.uniform(-r, r)) for _ in range(n)]
        self.splashes = []
        self.moon = (int(c * 0.8), int(r * 0.2), max(2.0, r * 0.09))
        mr = self.moon[2]
        self.craters = set()
        for _ in range(4):
            cx = rng.randint(-int(mr * self.aspect * 0.5), int(mr * self.aspect * 0.5))
            cy = rng.randint(-int(mr * 0.5), int(mr * 0.5))
            self.craters.update({(cx, cy), (cx + 1, cy)})

    def _new_drop(self, y):
        rng = self.rng
        speed = rng.uniform(18, 46)
        return [rng.uniform(0, self.cols + self.rows * 0.4), y, speed]

    def frame(self, g, t, dt):
        mx, my, mr = self.moon

        def moon(x, y, nx, ny):
            if (x - mx, y - my) in self.craters:
                g.put(x, y, "o", "3")
            elif nx * nx + ny * ny < 0.55:
                g.put(x, y, "@", "4")
            else:
                g.put(x, y, "O", "3")
        draw_disc(g, mx, my, mr, self.aspect, moon)

        top = self.top
        for d in self.drops:
            d[1] += d[2] * dt
            d[0] -= d[2] * dt * 0.35
            x, y = int(d[0]), int(d[1])
            if 0 <= x < self.cols and y >= top[x] - 1:
                self.splashes.append([x, top[x] - 1, 0.0])
                d[:] = self._new_drop(self.rng.uniform(-6, 0))
                continue
            if x < 0 or y >= self.rows:
                d[:] = self._new_drop(self.rng.uniform(-6, 0))
                continue
            lv = "3" if d[2] > 36 else ("2" if d[2] > 26 else "1")
            g.put(x, y, "/", lv)
            if d[2] > 32:
                g.put(x + 1, y - 1, "/", "1")

        alive = []
        for s in self.splashes:
            s[2] += dt
            if s[2] < 0.25:
                g.put(s[0], s[1], "o" if s[2] < 0.1 else ".", "2")
                alive.append(s)
        self.splashes = alive

        for x0, x1, tp, antenna in self.buildings:
            for xx in range(x0, x1):
                g.put(xx, tp, "_", "2")
            for yy in range(tp + 1, self.rows):
                g.put(x0, yy, "|", "2")
                g.put(x1 - 1, yy, "|", "2")
                for xx in range(x0 + 1, x1 - 1):
                    g.put(xx, yy, " ", "0")
            if antenna:
                ax = (x0 + x1) // 2
                g.put(ax, tp - 1, "|", "2")
                g.put(ax, tp - 2, "*", "7" if int(t * 1.5) % 2 else "1")

        for wx, wy, ph, sp, bias in self.windows:
            v = math.sin(ph + t * sp) + bias - 0.5
            if v > 0.25:
                g.put(wx, wy, "#", "7" if v > 0.8 else "6")
            else:
                g.put(wx, wy, ".", "1")


# --------------------------------------------------------------------------- night

class Night(Scene):
    """Stars over layered mountains, a crescent moon and shooting stars."""

    def setup(self):
        c, r, rng = self.cols, self.rows, self.rng
        p = [rng.uniform(0, TAU) for _ in range(6)]
        self.far = [int(r * 0.6 + r * 0.08 * math.sin(x * 0.031 + p[0])
                        + r * 0.04 * math.sin(x * 0.093 + p[1])
                        + r * 0.012 * math.sin(x * 0.27 + p[2])) for x in range(c)]
        self.near = [int(r * 0.8 + r * 0.06 * math.sin(x * 0.022 + p[3])
                         + r * 0.03 * math.sin(x * 0.11 + p[4])
                         + r * 0.01 * math.sin(x * 0.33 + p[5])) for x in range(c)]
        self.stars = make_stars(rng, c, int(r * 0.75), 1 / 45)
        self.trees = {x for x in range(c) if rng.random() < 0.18}
        self.moon = (int(c * rng.choice([0.2, 0.75])), int(r * 0.2), max(2.0, r * 0.1))
        self.shooter = None

    @staticmethod
    def _slope(h, x):
        a = h[x - 1] if x > 0 else h[x]
        b = h[x + 1] if x + 1 < len(h) else h[x]
        if b < a:
            return "/"
        if b > a:
            return "\\"
        return "_"

    def frame(self, g, t, dt):
        c, r, rng = self.cols, self.rows, self.rng
        draw_stars(g, self.stars, t, self.far)

        mx, my, mr = self.moon

        def moon(x, y, nx, ny):
            ex = nx - 0.45
            if ex * ex + ny * ny > 0.95:
                g.put(x, y, "@" if nx < -0.5 else "o", "7" if nx < -0.6 else "6")
        draw_disc(g, mx, my, mr, self.aspect, moon)

        if self.shooter is None and rng.random() < dt * 0.12:
            self.shooter = [rng.uniform(c * 0.3, c), rng.uniform(0, r * 0.25),
                            -rng.uniform(40, 70), rng.uniform(8, 16), 0.0]
        if self.shooter:
            s = self.shooter
            s[0] += s[2] * dt
            s[1] += s[3] * dt
            s[4] += dt
            for i, lv in enumerate("54321"):
                k = i * 1.4
                x = int(s[0] - s[2] / 40 * k)
                y = int(s[1] - s[3] / 40 * k)
                g.put(x, y, "*" if i == 0 else "-", lv)
            if s[4] > 1.6 or s[0] < 0:
                self.shooter = None

        far, near = self.far, self.near
        for x in range(c):
            g.erase(x, far[x], x + 1, r)
            g.put(x, far[x], self._slope(far, x), "2")
            for y in range(far[x] + 1, near[x]):
                if (x * 7 + y * 13) % 11 == 0:
                    g.put(x, y, ".", "1")
            g.erase(x, near[x], x + 1, r)
            g.put(x, near[x], self._slope(near, x), "3")
            if x in self.trees:
                g.put(x, near[x] - 1, "^", "2")
            for y in range(near[x] + 1, r):
                if (x * 3 + y * 5) % 9 == 0:
                    g.put(x, y, ":", "1")


# --------------------------------------------------------------------------- waves

class Waves(Scene):
    """Striped sun sinking into a moving ocean."""

    def setup(self):
        c, r, rng = self.cols, self.rows, self.rng
        self.horizon = int(r * 0.5)
        self.stars = make_stars(rng, c, self.horizon - 2, 1 / 70)
        self.R = max(3, int(r * 0.24))
        rows = []
        for y in range(self.horizon + 1, r):
            d = (y - self.horizon) / max(1, r - self.horizon)
            rows.append((y, d, 0.35 / (0.25 + d * 1.6), y * 0.9))
        self.water = rows

    def frame(self, g, t, dt):
        c, aspect, R, hz = self.cols, self.aspect, self.R, self.horizon
        cx = c // 2
        draw_stars(g, self.stars, t)

        for dy in range(1, R + 1):
            y = hz - dy
            frac = dy / R
            if frac < 0.55:
                gap = 2 + int(frac * 8)
                if (dy + int(t * 2)) % gap == 0:
                    continue
            hw = int(math.sqrt(max(0.0, R * R - (dy - 0.5) ** 2)) * aspect)
            ch, lv = ("#", "7") if frac > 0.5 else ("=", "6")
            for x in range(cx - hw, cx + hw + 1):
                g.put(x, y, ch, lv)
        for x in range(c):
            g.put(x, hz, "_", "2")

        sin = math.sin
        put_c, put_l = g.ch, g.lv
        rw = R * aspect
        for y, d, kx, ph in self.water:
            rc, rl = put_c[y], put_l[y]
            half = rw * (1.0 - 0.55 * d)
            a = t * 1.3 + ph
            b = -t * 1.7 + ph * 1.9
            k2 = kx * 2.3
            for x in range(c):
                v = sin(x * kx + a) + 0.6 * sin(x * k2 + b)
                if abs(x - cx) < half and v > 0.2:
                    rc[x] = "=" if v > 0.9 else "-"
                    rl[x] = "7" if v > 0.9 else "6"
                elif v > 1.15:
                    rc[x] = "~"
                    rl[x] = "4" if d > 0.5 else "3"
                elif v > 0.5:
                    rc[x] = "-"
                    rl[x] = "2"
                elif v > -0.1:
                    rc[x] = "."
                    rl[x] = "1"


# --------------------------------------------------------------------------- donut

class Donut(Scene):
    """The classic spinning ASCII torus."""

    SHADE = ".,-~:;=!*#$@"
    LEVELS = "112233445677"

    def setup(self):
        r = self.rows
        self.scale_y = r * 0.2 / 3.0
        nt = max(40, int(r * 1.4))
        np_ = max(110, int(r * 3.6))
        self.ct = [(math.cos(i * TAU / nt), math.sin(i * TAU / nt)) for i in range(nt)]
        self.cp = [(math.cos(i * TAU / np_), math.sin(i * TAU / np_)) for i in range(np_)]
        self.stars = make_stars(self.rng, self.cols, self.rows, 1 / 120)
        self.A = self.B = 0.0

    def frame(self, g, t, dt):
        draw_stars(g, self.stars, t)
        self.A += dt * 0.9
        self.B += dt * 0.45
        cA, sA, cB, sB = math.cos(self.A), math.sin(self.A), math.cos(self.B), math.sin(self.B)
        cols, rows = self.cols, self.rows
        cx, cy = cols / 2, rows / 2
        K2 = 5.0
        ky = self.scale_y * K2
        kx = ky * self.aspect
        zbuf = {}
        shade, levels = self.SHADE, self.LEVELS
        for ct, st in self.ct:
            cx2 = 2.0 + ct
            for cp, sp in self.cp:
                ox = cx2 * (cB * cp + sA * sB * sp) - st * cA * sB
                oy = cx2 * (sB * cp - sA * cB * sp) + st * cA * cB
                ooz = 1.0 / (K2 + cA * cx2 * sp + st * sA)
                xp = int(cx + kx * ooz * ox)
                yp = int(cy - ky * ooz * oy)
                key = yp * cols + xp
                if ooz > zbuf.get(key, 0.0):
                    zbuf[key] = ooz
                    L = (cp * ct * sB - cA * ct * sp - sA * st
                         + cB * (cA * st - ct * sA * sp))
                    i = int(L * 8)
                    if i < 0:
                        i = 0
                    if 0 <= xp < cols and 0 <= yp < rows:
                        g.ch[yp][xp] = shade[i]
                        g.lv[yp][xp] = levels[i]


# --------------------------------------------------------------------------- plasma

class Plasma(Scene):
    """Slow flowing interference field, like ink in water."""

    RAMP = " .:-=+*#%@"

    def setup(self):
        c, r, a = self.cols, self.rows, self.aspect
        cx, cy = c / 2, r / 2
        self.sinD, self.cosD = [], []
        for y in range(r):
            srow, crow = [], []
            for x in range(c):
                d = math.hypot((x - cx) / a, y - cy) * 0.22
                srow.append(math.sin(d))
                crow.append(math.cos(d))
            self.sinD.append(srow)
            self.cosD.append(crow)
        self.lvmap = "0112236775"

    def frame(self, g, t, dt):
        c, r, a = self.cols, self.rows, self.aspect
        sin = math.sin
        tt = t * 0.35
        colt = [sin(x * 0.07 + tt * 0.9) for x in range(c)]
        rowt = [sin(y * 0.07 * a - tt * 0.7) for y in range(r)]
        diag = [sin(i * 0.05 + tt * 0.5) for i in range(c + r)]
        ct, st = math.cos(tt * 1.3), math.sin(tt * 1.3)
        ramp, lvmap = self.RAMP, self.lvmap
        n1 = len(ramp) - 1
        for y in range(r):
            rt = rowt[y]
            sD, cD = self.sinD[y], self.cosD[y]
            rc, rl = g.ch[y], g.lv[y]
            for x in range(c):
                v = colt[x] + rt + diag[x + y] + sD[x] * ct - cD[x] * st
                # only the crests of the field are drawn; the rest stays empty
                if v > 1.3:
                    i = int((v - 1.3) * 0.45 * n1) + 1
                    if i > n1:
                        i = n1
                    rc[x] = ramp[i]
                    rl[x] = lvmap[i]


# --------------------------------------------------------------------------- fire

class Campfire(Scene):
    """A campfire crackling under the stars, embers drifting up."""

    STEP = 1 / 24

    def setup(self):
        c, r, rng = self.cols, self.rows, self.rng
        self.cx = c // 2
        self.hw = max(6, int(c * 0.1))
        self.maxh = max(10, int(r * 0.34))
        self.heat = [[0] * c for _ in range(r)]
        self.x0 = max(1, self.cx - self.hw * 3)
        self.x1 = min(c - 1, self.cx + self.hw * 3)
        self.ytop = max(1, int(r * 0.2))
        self.acc = 0.0
        self.embers = []
        self.stars = make_stars(rng, c, int(r * 0.5), 1 / 55)

    def step(self):
        rnd = self.rng.random
        heat, r = self.heat, self.rows
        src = r - 2
        mh, cx, hw = self.maxh, self.cx, self.hw
        row = heat[src]
        for x in range(self.x0, self.x1):
            d = (x - cx) / hw
            row[x] = int(mh * max(0.0, 1 - d * d) * (0.75 + 0.25 * rnd())) if abs(d) < 1 else 0
        for y in range(src, self.ytop, -1):
            below, above = heat[y], heat[y - 1]
            for x in range(self.x0, self.x1):
                h = below[x]
                if h <= 0:
                    above[x] = 0
                    continue
                k = rnd()
                dx = 1 if k < 0.3 else (-1 if k > 0.7 else 0)
                above[x + dx] = h - (1 if rnd() < 0.62 else 0)
        if rnd() < 0.5:
            self.embers.append([cx + self.rng.uniform(-hw, hw), r - 2 - mh * 0.8,
                                self.rng.uniform(4, 9), self.rng.uniform(0, TAU), 0.0])

    def frame(self, g, t, dt):
        draw_stars(g, self.stars, t)
        self.acc += dt
        n = 0
        while self.acc >= self.STEP and n < 4:
            self.step()
            self.acc -= self.STEP
            n += 1
        mh = self.maxh
        for y in range(self.ytop, self.rows - 1):
            row = self.heat[y]
            for x in range(self.x0, self.x1):
                f = row[x] / mh
                if f < 0.1:
                    continue
                if f < 0.2:
                    g.put(x, y, ".", "1")
                elif f < 0.32:
                    g.put(x, y, ":", "2")
                elif f < 0.47:
                    g.put(x, y, "+", "6")
                elif f < 0.65:
                    g.put(x, y, "*", "7")
                elif f < 0.85:
                    g.put(x, y, "#", "7")
                else:
                    g.put(x, y, "@", "5")
        alive = []
        for e in self.embers:
            e[4] += dt
            e[1] -= e[2] * dt
            x = int(e[0] + math.sin(e[3] + e[4] * 2) * 2)
            if e[4] < 3.5 and e[1] > 0:
                g.put(x, int(e[1]), "*" if e[4] < 1 else ".", "7" if e[4] < 2 else "6")
                alive.append(e)
        self.embers = alive[-60:]
        by = self.rows - 1
        cx, hw = self.cx, self.hw
        g.text(cx - hw - 3, by, "\\" + "=" * (hw * 2 + 4) + "/", "2")
        g.put(cx - hw - 4, by, "_", "1")
        g.put(cx + hw + 3, by, "_", "1")


# --------------------------------------------------------------------------- aurora

class Aurora(Scene):
    """Glowing aurora curtains over mountains, mirrored in a still lake."""

    def setup(self):
        c, r, rng = self.cols, self.rows, self.rng
        self.lake = int(r * 0.74)
        p = [rng.uniform(0, TAU) for _ in range(4)]
        self.ridge = [int(self.lake - 1 - r * 0.07 - r * 0.05 * math.sin(x * 0.04 + p[0])
                          - r * 0.03 * math.sin(x * 0.13 + p[1])) for x in range(c)]
        self.stars = make_stars(rng, c, self.lake, 1 / 50)
        self.curtains = [(r * (0.16 + 0.1 * k), rng.uniform(0, TAU), rng.uniform(0, TAU),
                          rng.uniform(0, TAU), 1.0 - 0.3 * k) for k in range(2)]

    def frame(self, g, t, dt):
        c, r, lake = self.cols, self.rows, self.lake
        sin = math.sin
        draw_stars(g, self.stars, t, self.ridge)
        for base, p1, p2, p3, gain in self.curtains:
            for x in range(c):
                y0 = base + r * 0.07 * sin(x * 0.021 + t * 0.12 + p1) \
                    + r * 0.035 * sin(x * 0.057 - t * 0.21 + p2)
                inten = (0.55 + 0.45 * sin(x * 0.033 + t * 0.35 + p3)) \
                    * (0.65 + 0.35 * sin(x * 0.009 - t * 0.08 + p1)) * gain
                # fine vertical rays that shimmer sideways
                rays = 0.75 + 0.25 * sin(x * 0.5 + t * 0.9 + p2) * sin(x * 0.17 - t * 0.4)
                inten *= rays
                if inten < 0.15:
                    continue
                length = int(r * 0.32 * inten) + 2
                yb = int(y0 + (1 - rays) * r * 0.04)
                for i in range(length):
                    f = inten * ((i + 1) / length) ** 1.2
                    y = yb + i
                    if f > 0.75:
                        g.put(x, y, "|", "5")
                    elif f > 0.55:
                        g.put(x, y, "|", "7")
                    elif f > 0.38:
                        g.put(x, y, "|", "6")
                    elif f > 0.22:
                        g.put(x, y, ":", "2")
                    elif (x + y) % 2 == 0:
                        g.put(x, y, ".", "1")
        ridge = self.ridge
        for x in range(c):
            g.erase(x, ridge[x], x + 1, lake)
            a = ridge[x - 1] if x else ridge[x]
            b = ridge[x + 1] if x + 1 < c else ridge[x]
            g.put(x, ridge[x], "/" if b < a else "\\" if b > a else "_", "2")
        for x in range(c):
            g.put(x, lake, "-", "2")
        # reflection: mirror the sky into the lake, dimmer and rippling
        dim = {"5": "4", "7": "6", "6": "6", "4": "2", "3": "2", "2": "1", "1": "1"}
        for y in range(lake + 1, r):
            d = y - lake
            sy = lake - int(d * 1.7) - 1
            if sy < 0:
                break
            src_c, src_l = g.ch[sy], g.lv[sy]
            shift = int(1.5 * sin(t * 1.4 + y * 0.9))
            for x in range(c):
                xs = x + shift
                if 0 <= xs < c:
                    lv = src_l[xs]
                    if lv != "0" and lv in dim and sin(x * 0.4 + t * 2 + y) > -0.3:
                        g.ch[y][x] = "~" if lv in "567" else "-"
                        g.lv[y][x] = dim[lv]


# --------------------------------------------------------------------------- ribbons

class Ribbons(Scene):
    """Glowing sine ribbons breathing like a slow radio signal."""

    def setup(self):
        c, r, rng = self.cols, self.rows, self.rng
        self.ribbons = []
        for k, lv in enumerate("23467"):    # back to front
            self.ribbons.append({
                "cy": r * (0.5 + rng.uniform(-0.06, 0.06)),
                "a1": r * rng.uniform(0.14, 0.24), "f1": rng.uniform(0.022, 0.04),
                "s1": rng.uniform(0.25, 0.6) * rng.choice([-1, 1]),
                "a2": r * rng.uniform(0.05, 0.1), "f2": rng.uniform(0.05, 0.09),
                "s2": rng.uniform(0.5, 1.1) * rng.choice([-1, 1]),
                "ph": rng.uniform(0, TAU), "lv": lv, "glow": k >= 3,
            })
        self.taper = [math.sin(math.pi * (x + 0.5) / c) ** 0.6 for x in range(c)]
        self.stars = make_stars(rng, c, r, 1 / 140)

    def frame(self, g, t, dt):
        c = self.cols
        sin = math.sin
        draw_stars(g, self.stars, t)
        taper = self.taper
        for rb in self.ribbons:
            env = 0.6 + 0.4 * sin(t * 0.23 + rb["ph"])
            ys = [rb["cy"] + taper[x] * env * (
                rb["a1"] * sin(x * rb["f1"] + t * rb["s1"] + rb["ph"])
                + rb["a2"] * sin(x * rb["f2"] + t * rb["s2"] + rb["ph"] * 2)) for x in range(c)]
            lv, glow = rb["lv"], rb["glow"]
            pulse = (t * 22 + rb["ph"] * 30) % (c + 40) - 20
            for x in range(c):
                y = ys[x]
                yi = int(round(y))
                nxt = ys[x + 1] if x + 1 < c else y
                sl = nxt - (ys[x - 1] if x else y)
                ch = "-" if abs(sl) < 0.5 else ("\\" if sl > 0 else "/")
                if glow:
                    for gy in (yi - 1, yi + 1):
                        if 0 <= gy < g.rows and g.lv[gy][x] == "0":
                            g.put(x, gy, ".", "1")
                hot = glow and abs(x - pulse) < 4
                g.put(x, yi, "*" if hot and abs(x - pulse) < 1.5 else ch, "5" if hot else lv)
                if abs(nxt - y) > 1.2:   # fill steep gaps
                    step = 1 if nxt > y else -1
                    for yy in range(yi + step, int(round(nxt)), step):
                        g.put(x, yy, "|", lv)


# --------------------------------------------------------------------------- glowtide

class GlowTide(Scene):
    """Night sea with bioluminescent wave crests drifting in glowing patches."""

    def setup(self):
        c, r, rng = self.cols, self.rows, self.rng
        self.horizon = int(r * 0.36)
        self.stars = make_stars(rng, c, self.horizon - 1, 1 / 40)
        self.moon = (int(c * rng.uniform(0.2, 0.8)), int(self.horizon * 0.4),
                     max(1.5, r * 0.05))
        self.water = []
        for y in range(self.horizon + 1, r):
            d = (y - self.horizon) / max(1, r - self.horizon)
            self.water.append((y, d, 0.3 / (0.2 + d * 1.5), rng.uniform(0, TAU)))

    def frame(self, g, t, dt):
        c, hz = self.cols, self.horizon
        sin = math.sin
        draw_stars(g, self.stars, t)
        mx, my, mr = self.moon
        draw_disc(g, mx, my, mr, self.aspect,
                  lambda x, y, nx, ny: g.put(x, y, "@" if nx * nx + ny * ny < 0.5 else "o", "4"))
        for x in range(c):
            g.put(x, hz, "_", "1")
        mw = mr * self.aspect
        for y, d, kx, ph in self.water:
            rc, rl = g.ch[y], g.lv[y]
            a, b = t * 0.9 + ph, -t * 1.3 + ph * 1.7
            k2 = kx * 2.1
            gy = y * 0.15 - t * 0.25
            half = mw * (0.8 + 2.5 * d)
            for x in range(c):
                v = sin(x * kx + a) + 0.6 * sin(x * k2 + b)
                if v < 0.35:
                    continue
                patch = sin(x * 0.03 + gy) + 0.6 * sin(x * 0.071 - t * 0.17 + y * 0.25)
                if abs(x - mx) < half and v > 0.7:
                    rc[x], rl[x] = "-", "4" if v > 1.1 else "3"
                elif patch > 0.2 and v > 0.75:
                    if v > 1.52:
                        rc[x], rl[x] = "*", "5"
                    else:
                        rc[x], rl[x] = "~", "7" if v > 1.15 else "6"
                elif v > 1.2:
                    rc[x], rl[x] = "~", "2"
                elif v > 0.7:
                    rc[x], rl[x] = "-", "1"


# --------------------------------------------------------------------------- swell

class Swell(Scene):
    """Layers of rolling swells seen side-on, glowing foam on the crests."""

    def setup(self):
        c, r, rng = self.cols, self.rows, self.rng
        self.layers = []
        n = 4
        for k in range(n):
            self.layers.append({
                "base": r * (0.5 + 0.13 * k), "amp": r * (0.05 + 0.03 * k),
                "f": 0.06 - 0.01 * k, "s": 0.5 + 0.25 * k, "ph": rng.uniform(0, TAU),
                "line": "2345"[k], "foam": "6677"[k],
            })
        self.sun = (int(c * rng.uniform(0.3, 0.7)), int(r * 0.4), max(3.0, r * 0.1))
        self.stars = make_stars(rng, c, int(r * 0.4), 1 / 60)
        self.tex = [[(x * 7 + y * 13) % 9 == 0 for x in range(c)] for y in range(r)]

    def frame(self, g, t, dt):
        c, r = self.cols, self.rows
        sin = math.sin
        draw_stars(g, self.stars, t)
        sx, sy, sr = self.sun

        def sun(x, y, nx, ny):
            d = nx * nx + ny * ny
            if d < 0.3:
                g.put(x, y, "@", "5")
            elif d < 0.55:
                g.put(x, y, "O", "7")
            elif d < 0.8:
                g.put(x, y, "o", "6")
            elif (x + y) % 2 == 0:
                g.put(x, y, ".", "2")
        draw_disc(g, sx, sy, sr * 1.6, self.aspect, sun)

        surfs = []
        for L in self.layers:
            a, f, s, ph = L["amp"], L["f"], L["s"], L["ph"]
            surfs.append([L["base"] + a * (sin(x * f - t * s + ph)
                                           + 0.45 * sin(x * f * 2.3 - t * s * 1.4 + ph * 2))
                          for x in range(c)])
        layers = self.layers
        top = min(min(sv) for sv in surfs)
        for x in range(c):
            ys = [sv[x] for sv in surfs]
            for y in range(max(0, int(top)), r):
                k = -1
                for i in range(len(ys) - 1, -1, -1):
                    if y >= int(ys[i]):
                        k = i
                        break
                if k < 0:
                    continue
                L = layers[k]
                depth = y - int(ys[k])
                if depth == 0:
                    crest = (ys[k] - L["base"]) < -L["amp"] * 0.9
                    xa = surfs[k][x - 1] if x else ys[k]
                    xb = surfs[k][x + 1] if x + 1 < c else ys[k]
                    sl = xb - xa
                    if crest:
                        g.put(x, y, "~", L["foam"])
                    else:
                        g.put(x, y, "-" if abs(sl) < 0.5 else ("\\" if sl > 0 else "/"), L["line"])
                elif depth == 1 and (ys[k] - L["base"]) < -L["amp"] * 0.7:
                    g.put(x, y, ".", "6" if k >= 2 else "2")
                elif self.tex[y][x]:
                    g.put(x, y, ":" if depth < 3 else ".", "1")
                else:
                    g.put(x, y, " ", "0")


# --------------------------------------------------------------------------- big text

_FONT5 = {
    "A": [" ### ", "#   #", "#####", "#   #", "#   #"],
    "D": ["#### ", "#   #", "#   #", "#   #", "#### "],
    "E": ["#####", "#    ", "#### ", "#    ", "#####"],
    "G": [" ####", "#    ", "#  ##", "#   #", " ### "],
    "H": ["#   #", "#   #", "#####", "#   #", "#   #"],
    "I": ["###", " # ", " # ", " # ", "###"],
    "K": ["#   #", "#  # ", "###  ", "#  # ", "#   #"],
    "L": ["#    ", "#    ", "#    ", "#    ", "#####"],
    "M": ["#   #", "## ##", "# # #", "#   #", "#   #"],
    "N": ["#   #", "##  #", "# # #", "#  ##", "#   #"],
    "O": [" ### ", "#   #", "#   #", "#   #", " ### "],
    "P": ["#### ", "#   #", "#### ", "#    ", "#    "],
    "S": [" ####", "#    ", " ### ", "    #", "#### "],
    "T": ["#####", "  #  ", "  #  ", "  #  ", "  #  "],
    " ": ["  ", "  ", "  ", "  ", "  "],
}


def big_text_cells(text, cols, rows, aspect, width_frac=0.7, cy_frac=0.42):
    """Lay out text in the 5-row block font, scaled to the grid.
    Returns ([(x, y, v, top_edge)], (x0, y0, w, h)); v = 0 at top .. 1 at bottom."""
    glyphs = [_FONT5[ch] for ch in text.upper() if ch in _FONT5]
    wpx = sum(len(gl[0]) for gl in glyphs) + len(glyphs) - 1
    sx = max(1, int(cols * width_frac / wpx))
    sy = max(2, round(sx / aspect * 2.0))
    w, h = wpx * sx, 5 * sy
    x0, y0 = (cols - w) // 2, int(rows * cy_frac - h / 2)
    cells = []
    px = 0
    for gl in glyphs:
        for gy, line in enumerate(gl):
            for gx, p in enumerate(line):
                if p != "#":
                    continue
                above = gy > 0 and gl[gy - 1][gx] == "#"
                for sy_ in range(sy):
                    for sx_ in range(sx):
                        y = y0 + gy * sy + sy_
                        cells.append((x0 + (px + gx) * sx + sx_, y, (y - y0) / max(1, h - 1),
                                      sy_ == 0 and not above))
        px += len(gl[0]) + 1
    return cells, (x0, y0, w, h)


# --------------------------------------------------------------------------- slipknot

class Slipknot(Scene):
    """Industrial static, barbed wire and rising sparks around a glitching name."""

    BEAT = 0.8

    def setup(self):
        c, r, rng = self.cols, self.rows, self.rng
        self.cells, self.box = big_text_cells("SLIPKNOT", c, r, self.aspect)
        self.streams = [[rng.randrange(c), rng.uniform(-r, r), rng.uniform(6, 18),
                         rng.randint(3, 9)] for _ in range(max(10, c // 5))]
        self.sparks = []
        self.next_glitch = 2.0
        self.glitch_until = 0.0
        self.shift = {}

    def frame(self, g, t, dt):
        c, r, rng = self.cols, self.rows, self.rng
        for _ in range(c * r // 300):   # faint static
            g.put(rng.randrange(c), rng.randrange(r), rng.choice(".:'`"), "1")
        for s in self.streams:   # falling industrial drips
            s[1] += s[2] * dt
            if s[1] - s[3] > r:
                s[0], s[1] = rng.randrange(c), -rng.uniform(0, r * 0.5)
            for i in range(s[3]):
                g.put(s[0], int(s[1]) - i, "|" if i == 0 else ":", "2" if i == 0 else "1")

        if rng.random() < dt * 14:
            self.sparks.append([rng.uniform(0, c), r - 1.0, rng.uniform(5, 12),
                                rng.uniform(-2, 2), 0.0])
        alive = []
        for p in self.sparks:
            p[4] += dt
            p[1] -= p[2] * dt
            p[0] += p[3] * dt
            if p[4] < 2.5 and p[1] > 0:
                g.put(int(p[0]), int(p[1]), "*" if p[4] < 0.8 else ".",
                      "7" if p[4] < 1.2 else "6")
                alive.append(p)
        self.sparks = alive[-150:]

        x0, y0, w, h = self.box
        for yy, ch in ((y0 - 2, "-x-"), (y0 + h + 1, "-x-")):   # barbed wire
            for x in range(x0 - 6, x0 + w + 6):
                k = (x + int(t * 3)) % 9
                g.put(x, yy, "x" if k == 0 else ("/" if k == 1 else "-"), "2" if k else "3")

        if t >= self.next_glitch:
            self.glitch_until = t + rng.uniform(0.12, 0.4)
            self.next_glitch = t + rng.uniform(3, 8)
            self.shift = {y: rng.randint(-6, 6) for y in range(y0, y0 + h) if rng.random() < 0.35}
        glitching = t < self.glitch_until
        pulse = math.exp(-((t % self.BEAT) / 0.12))
        tex = "###%##@###&#"
        tick = int(t * 5)
        for x, y, v, edge in self.cells:
            k = (x * 7 + y * 13 + tick) % len(tex)
            lv = "5" if edge and pulse > 0.4 else ("7" if v < 0.5 else "6")
            if glitching:
                x += self.shift.get(y, 0)
                if rng.random() < 0.06:
                    g.put(x, y, rng.choice("01/\\"), "5")
                    continue
            g.put(x, y, tex[k], lv)
        if glitching:
            ty = rng.randint(0, r - 1)
            for x in range(c):
                if rng.random() < 0.7:
                    g.put(x, ty, "=", "2")


# --------------------------------------------------------------------------- megadeth

class Megadeth(Scene):
    """Thrash storm: lightning over a ruined skyline and a chrome name."""

    def setup(self):
        c, r, rng = self.cols, self.rows, self.rng
        self.cells, self.box = big_text_cells("MEGADETH", c, r, self.aspect, cy_frac=0.45)
        self.top = [r] * c
        x = 0
        while x < c:
            w = rng.randint(4, 12)
            h = rng.randint(2, max(3, int(r * 0.18)))
            for i in range(w):
                if x + i < c:
                    self.top[x + i] = r - h - (rng.randint(0, 2) if rng.random() < 0.4 else 0)
            x += w + rng.randint(0, 2)
        self.embers = [(rng.randrange(c), rng.uniform(0, TAU)) for _ in range(c // 6)]
        self.bolt = None
        self.next_bolt = 1.5
        self.flash = 0.0
        self.drops = [[rng.uniform(0, c * 1.3), rng.uniform(0, r), rng.uniform(25, 40)]
                      for _ in range(c * r // 60)]

    def _make_bolt(self):
        c, r, rng = self.cols, self.rows, self.rng
        x = rng.uniform(c * 0.1, c * 0.9)
        y = int(r * 0.2)
        path = []
        main_end = self.top[max(0, min(c - 1, int(x)))]
        while y < main_end:
            dx = rng.choice((-1, -1, 0, 1, 1))
            path.append((int(x), y, "/" if dx < 0 else ("\\" if dx > 0 else "|")))
            x += dx
            y += 1
            if rng.random() < 0.07:
                bx, by = x, y
                for _ in range(rng.randint(3, 8)):
                    d = rng.choice((-1, 1))
                    path.append((int(bx), by, "/" if d < 0 else "\\"))
                    bx += d
                    by += 1
        return path

    def frame(self, g, t, dt):
        c, r, rng = self.cols, self.rows, self.rng
        sin = math.sin
        if t >= self.next_bolt:
            self.bolt = (self._make_bolt(), t)
            self.next_bolt = t + rng.uniform(2.5, 7)
        age = t - self.bolt[1] if self.bolt else 99
        lit = age < 0.12 or 0.22 < age < 0.3
        cloud_rows = int(r * 0.22)
        boost = "3" if lit else ("2" if age < 0.6 else None)
        for y in range(cloud_rows):
            rc, rl = g.ch[y], g.lv[y]
            for x in range(c):
                v = sin(x * 0.045 + t * 0.25 + y * 0.5) + sin(x * 0.11 - t * 0.15 + y * 0.3)
                if v > 0.6:
                    rc[x] = "~" if v > 1.3 else "-"
                    rl[x] = boost or ("2" if v > 1.3 else "1")
        for d in self.drops:
            d[1] += d[2] * dt
            d[0] -= d[2] * dt * 0.3
            if d[1] >= r or d[0] < 0:
                d[0], d[1] = rng.uniform(0, c * 1.3), rng.uniform(-5, 0)
            g.put(int(d[0]), int(d[1]), "/", "1")
        if self.bolt and age < 0.6:
            lv = "5" if lit else ("4" if age < 0.35 else "2")
            for x, y, ch in self.bolt[0]:
                g.put(x, y, ch, lv)
        for x, y, v, edge in self.cells:
            if lit:
                g.put(x, y, "█", "5")
            elif edge or v < 0.3:
                g.put(x, y, "█", "5")
            elif v < 0.65:
                g.put(x, y, "▓", "4")
            else:
                g.put(x, y, "▒", "3")
        for x in range(c):
            tp = self.top[x]
            a = self.top[x - 1] if x else tp
            g.erase(x, tp, x + 1, r)
            g.put(x, tp, "_" if a == tp else ("|" if abs(a - tp) > 1 else ("/" if a > tp else "\\")),
                  "4" if lit else "2")
            for y in range(tp + 1, r):
                if (x * 5 + y * 3) % 7 == 0:
                    g.put(x, y, ".", "1")
        for x, ph in self.embers:
            y = self.top[x] + 1 + int((x * 7) % 3)
            if y < r and sin(ph + t * 1.5) > 0.4:
                g.put(x, y, "#", "6" if sin(ph + t * 3) > 0.7 else "7")


# --------------------------------------------------------------------------- space

class BlackHole(Scene):
    """A black hole with a glowing accretion disk bent over its shadow."""

    def setup(self):
        c, r, rng = self.cols, self.rows, self.rng
        self.cx, self.cy = c / 2, r * 0.46
        self.R = max(3.0, r * 0.12)
        R = self.R
        self.parts = []
        for _ in range(max(500, c * r // 6)):
            rad = R * (1.7 + 2.2 * rng.random() ** 1.8)
            self.parts.append([rad, rng.uniform(0, TAU), rng.random()])
        self.stars = make_stars(rng, c, r, 1 / 55)

    def frame(self, g, t, dt):
        cx, cy, R, a = self.cx, self.cy, self.R, self.aspect
        cos, sin = math.cos, math.sin
        draw_stars(g, self.stars, t)
        tilt = 0.2
        back, front = [], []
        for p in self.parts:
            rad, th, j = p
            p[1] = th + dt * 2.6 * (R / rad) ** 1.5
            th = p[1]
            ct, st = cos(th), sin(th)
            heat = R * 1.7 / rad
            doppler = 0.5 - 0.5 * ct          # left side comes toward us: brighter
            b = heat * (0.55 + 0.6 * doppler) + j * 0.1
            lv = "5" if b > 0.95 else "7" if b > 0.7 else "6" if b > 0.45 else "3" if b > 0.3 else "2"
            ch = "=" if b > 0.7 else "-" if b > 0.4 else "."
            x, y = int(cx + rad * ct * a), int(cy + rad * st * tilt)
            (back if st < 0 else front).append((x, y, ch, lv))
            if st < 0:   # far side of the disk, lensed over the top of the shadow
                rl = R * 1.3 + (rad - R * 1.7) * 0.3
                ang = th
                back.append((int(cx + rl * cos(ang) * a), int(cy - rl * abs(sin(ang)) - 0.5),
                             "~" if b > 0.5 else "-", lv))
            else:        # faint lensed image below
                rl = R * 1.28 + (rad - R * 1.7) * 0.15
                if j < 0.35:
                    back.append((int(cx + rl * ct * a), int(cy + rl * abs(st) + 0.5), ".", "2"))
        for x, y, ch, lv in back:
            g.put(x, y, ch, lv)
        # the shadow swallows everything behind it
        draw_disc(g, cx, cy, R * 1.15, a, lambda x, y, nx, ny: g.put(x, y, " ", "0"))
        # photon ring
        n = int(R * a * 8)
        for i in range(n):
            ang = TAU * i / n
            bright = sin(ang * 2 - t * 0.7) > 0.3
            g.put(int(cx + R * 1.2 * cos(ang) * a), int(cy + R * 1.2 * sin(ang)),
                  "o", "5" if bright else "4")
        for x, y, ch, lv in front:
            g.put(x, y, ch, lv)


class Galaxy(Scene):
    """A slowly turning spiral galaxy."""

    def setup(self):
        c, r, rng = self.cols, self.rows, self.rng
        self.cx, self.cy = c * 0.45, r * 0.45
        self.size = min(r * 0.75, c / self.aspect * 0.42)
        self.stars = []
        for _ in range(max(800, c * r // 4)):
            arm = rng.randrange(2)
            d = rng.random() ** 1.3
            th = arm * math.pi + 3.2 * math.log(1 + 5 * d) + rng.gauss(0, 0.32 * (1.1 - d))
            self.stars.append((d, th, rng.random()))
        self.bg = make_stars(rng, c, r, 1 / 90)

    def frame(self, g, t, dt):
        cx, cy, S, a = self.cx, self.cy, self.size, self.aspect
        cos, sin = math.cos, math.sin
        draw_stars(g, self.bg, t)
        tilt = 0.55
        for d, th, j in self.stars:
            ang = th + t * 0.05 / (0.25 + d)
            x = int(cx + d * S * cos(ang) * a)
            y = int(cy + d * S * sin(ang) * tilt)
            if d < 0.08:
                g.put(x, y, "@", "5")
            elif d < 0.2:
                g.put(x, y, "*" if j < 0.6 else "o", "5" if j < 0.3 else "7")
            elif j < 0.12:
                g.put(x, y, "*", "4")
            elif d < 0.55:
                g.put(x, y, "+" if j < 0.4 else ".", "6" if j < 0.6 else "3")
            else:
                g.put(x, y, ".", "2" if j < 0.5 else "1")


class Warp(Scene):
    """Gliding through a starfield at a calm warp speed."""

    def setup(self):
        self.stars = [self._new(self.rng.uniform(0.1, 1.0)) for _ in range(max(200, self.cols * 3))]

    def _new(self, z=1.0):
        rng = self.rng
        return [rng.uniform(-1, 1), rng.uniform(-1, 1), z]

    def frame(self, g, t, dt):
        c, r, a = self.cols, self.rows, self.aspect
        cx = c / 2 + math.sin(t * 0.07) * c * 0.08
        cy = r / 2 + math.cos(t * 0.05) * r * 0.08
        sc = r * 0.5
        speed = 0.12 + 0.05 * math.sin(t * 0.1)
        for s in self.stars:
            zp = s[2]
            s[2] -= speed * dt
            if s[2] <= 0.02:
                s[:] = self._new()
                continue
            x1, y1 = cx + s[0] / s[2] * sc * a, cy + s[1] / s[2] * sc
            x0, y0 = cx + s[0] / zp * sc * a, cy + s[1] / zp * sc
            if not (0 <= x1 < c and 0 <= y1 < r):
                s[:] = self._new()
                continue
            z = s[2]
            lv = "5" if z < 0.15 else "4" if z < 0.3 else "3" if z < 0.55 else "2" if z < 0.8 else "1"
            dx, dy = x1 - x0, (y1 - y0) * a
            ch = "-" if abs(dx) > 2 * abs(dy) else ("|" if abs(dy) > 2 * abs(dx) else
                                                    ("\\" if dx * dy > 0 else "/"))
            steps = max(1, int(max(abs(x1 - x0), abs(y1 - y0))))
            for i in range(steps + 1):
                f = i / steps
                g.put(int(x0 + (x1 - x0) * f), int(y0 + (y1 - y0) * f), ch if z < 0.6 else ".", lv)
            if z < 0.2:
                g.put(int(x1), int(y1), "*", "7")


class Planet(Scene):
    """A ringed planet turning in sunlight, with a small moon in orbit."""

    def setup(self):
        c, r, rng = self.cols, self.rows, self.rng
        self.cx, self.cy = c * 0.4, r * 0.52
        self.R = min(r * 0.3, c / self.aspect * 0.18)
        self.stars = make_stars(rng, c, r, 1 / 60)
        L = (-0.55, -0.45, 0.7)
        n = math.sqrt(sum(v * v for v in L))
        self.L = tuple(v / n for v in L)

    def frame(self, g, t, dt):
        cx, cy, R, a = self.cx, self.cy, self.R, self.aspect
        sin, cos = math.sin, math.cos
        draw_stars(g, self.stars, t)
        Lx, Ly, Lz = self.L
        tilt = 0.28
        ring_pts = []
        for k in range(5):
            rr = R * (1.45 + 0.17 * k)
            if k == 2:
                continue    # gap in the rings
            n = int(rr * a * 7)
            for i in range(n):
                ang = TAU * i / n + t * 0.02
                ring_pts.append((cx + rr * cos(ang) * a, cy + rr * sin(ang) * tilt, sin(ang), k))
        for x, y, s, k in ring_pts:
            if s < 0:
                g.put(int(x), int(y), "-", "2" if k > 2 else "3")
        spin = t * 0.06

        def body(x, y, nx, ny):
            d = nx * nx + ny * ny
            if d > 1:
                return
            nz = math.sqrt(1 - d)
            lam = nx * Lx + ny * Ly + nz * Lz
            lon = math.atan2(nx, nz) + spin
            band = sin(ny * 11 + 0.6 * sin(lon * 2)) + 0.4 * sin(lon * 3 + ny * 4)
            if lam < 0.02:
                g.put(x, y, "." if (x + y) % 3 == 0 else " ", "1" if (x + y) % 3 == 0 else "0")
            elif lam < 0.25:
                g.put(x, y, ":" if band > 0 else ".", "2")
            elif lam < 0.5:
                g.put(x, y, "=" if band > 0.3 else "-", "3" if band > 0 else "6")
            elif lam < 0.75:
                g.put(x, y, "#" if band > 0.3 else "=", "4" if band > 0 else "7")
            else:
                g.put(x, y, "@" if band > 0 else "#", "5" if band > -0.3 else "7")
        draw_disc(g, cx, cy, R, a, body)
        for x, y, s, k in ring_pts:
            if s >= 0:
                g.put(int(x), int(y), "=" if k < 2 else "-", "4" if k < 2 else "3")
        ma = t * 0.15
        mx, my = cx + R * 2.6 * cos(ma) * a, cy + R * 0.9 * sin(ma)
        if not (sin(ma) < 0 and (mx - cx) ** 2 / a ** 2 + (my - cy) ** 2 < R * R):
            draw_disc(g, mx, my, max(1.0, R * 0.12), a,
                      lambda x, y, nx, ny: g.put(x, y, "@" if nx < 0.2 else "o", "4"))


SCENE_LABELS = {"glowtide": "Glow Tide", "blackhole": "Black Hole"}

SCENES = {
    "rain": Rain,
    "night": Night,
    "waves": Waves,
    "glowtide": GlowTide,
    "swell": Swell,
    "aurora": Aurora,
    "ribbons": Ribbons,
    "campfire": Campfire,
    "plasma": Plasma,
    "donut": Donut,
    "blackhole": BlackHole,
    "galaxy": Galaxy,
    "warp": Warp,
    "planet": Planet,
    "slipknot": Slipknot,
    "megadeth": Megadeth,
}


# --------------------------------------------------------------------------- clock

_DIGITS = {
    "0": ["###", "# #", "# #", "# #", "###"],
    "1": [" # ", "## ", " # ", " # ", "###"],
    "2": ["###", "  #", "###", "#  ", "###"],
    "3": ["###", "  #", " ##", "  #", "###"],
    "4": ["# #", "# #", "###", "  #", "  #"],
    "5": ["###", "#  ", "###", "  #", "###"],
    "6": ["###", "#  ", "###", "# #", "###"],
    "7": ["###", "  #", "  #", " # ", " # "],
    "8": ["###", "# #", "###", "# #", "###"],
    "9": ["###", "# #", "###", "  #", "###"],
    ":": [" ", "#", " ", "#", " "],
}


def draw_clock(g, position="bottom-right", hour24=True):
    now = time.localtime()
    hh = now.tm_hour if hour24 else (now.tm_hour % 12 or 12)
    s = "%02d:%02d" % (hh, now.tm_min)
    date = time.strftime("%a %d %b", now).lower()
    glyphs = [_DIGITS[ch] for ch in s]
    width = sum(len(gl[0]) * 2 + 2 for gl in glyphs) - 2
    height = 7
    if position == "center":
        x0, y0 = (g.cols - width) // 2, (g.rows - height) // 2
    elif position == "top-right":
        x0, y0 = g.cols - width - 4, 2
    elif position == "bottom-left":
        x0, y0 = 4, g.rows - height - 2
    else:
        x0, y0 = g.cols - width - 4, g.rows - height - 2
    g.erase(x0 - 2, y0 - 1, x0 + width + 2, y0 + height + 1)
    x = x0
    for gl in glyphs:
        for yy, line in enumerate(gl):
            for xx, px in enumerate(line):
                if px == "#":
                    g.put(x + xx * 2, y0 + yy, "█", "4")
                    g.put(x + xx * 2 + 1, y0 + yy, "█", "4")
        x += len(gl[0]) * 2 + 2
    g.text(x0 + width - len(date), y0 + 6, date, "3")
