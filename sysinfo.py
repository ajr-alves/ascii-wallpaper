"""System readings (CPU, RAM, GPU, disk, network, temperature) and the ASCII
panel that shows them in a corner of the wallpaper.

Sampling runs on a background thread once a second, so a slow reading never
stalls a frame. Everything comes from the Windows API (kernel32, PDH); NVIDIA
cards additionally report temperature and power through nvidia-smi, which
ships with the driver. CPU temperature is not exposed to normal (non-admin)
programs on most PCs, so the panel shows the GPU's.
"""
import collections
import ctypes
import math
import shutil
import subprocess
import threading
import time
from ctypes import wintypes as wt

kernel32 = ctypes.WinDLL("kernel32")
pdh = ctypes.WinDLL("pdh")

HISTORY = 40


# --------------------------------------------------------------------------- win32

class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [("dwLength", wt.DWORD), ("dwMemoryLoad", wt.DWORD),
                ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]


class _VAL(ctypes.Union):
    _fields_ = [("longValue", ctypes.c_long), ("doubleValue", ctypes.c_double),
                ("largeValue", ctypes.c_longlong)]


class PDH_FMT_COUNTERVALUE(ctypes.Structure):
    _fields_ = [("CStatus", wt.DWORD), ("u", _VAL)]


class PDH_FMT_COUNTERVALUE_ITEM_W(ctypes.Structure):
    _fields_ = [("szName", wt.LPWSTR), ("FmtValue", PDH_FMT_COUNTERVALUE)]


PDH_FMT_DOUBLE = 0x00000200
PDH_FMT_NOCAP100 = 0x00008000
PDH_MORE_DATA = 0x800007D2

pdh.PdhOpenQueryW.argtypes = [wt.LPCWSTR, ctypes.c_size_t, ctypes.POINTER(wt.HANDLE)]
pdh.PdhAddEnglishCounterW.argtypes = [wt.HANDLE, wt.LPCWSTR, ctypes.c_size_t,
                                      ctypes.POINTER(wt.HANDLE)]
pdh.PdhCollectQueryData.argtypes = [wt.HANDLE]
pdh.PdhGetFormattedCounterArrayW.argtypes = [wt.HANDLE, wt.DWORD, ctypes.POINTER(wt.DWORD),
                                             ctypes.POINTER(wt.DWORD), ctypes.c_void_p]
pdh.PdhCloseQuery.argtypes = [wt.HANDLE]
for f in (pdh.PdhOpenQueryW, pdh.PdhAddEnglishCounterW, pdh.PdhCollectQueryData,
          pdh.PdhGetFormattedCounterArrayW, pdh.PdhCloseQuery):
    f.restype = wt.DWORD

kernel32.GetSystemTimes.argtypes = [ctypes.POINTER(ctypes.c_ulonglong)] * 3
kernel32.GetTickCount64.restype = ctypes.c_ulonglong


class Pdh:
    """A PDH query; each counter path may contain a (*) wildcard, values are summed."""

    def __init__(self, paths):
        self.q = wt.HANDLE()
        self.counters = {}
        if pdh.PdhOpenQueryW(None, 0, ctypes.byref(self.q)):
            self.q = None
            return
        for key, path in paths.items():
            h = wt.HANDLE()
            if pdh.PdhAddEnglishCounterW(self.q, path, 0, ctypes.byref(h)) == 0:
                self.counters[key] = h
        pdh.PdhCollectQueryData(self.q)

    def read(self):
        out = {}
        if not self.q or pdh.PdhCollectQueryData(self.q):
            return out
        for key, h in self.counters.items():
            size, count = wt.DWORD(0), wt.DWORD(0)
            fmt = PDH_FMT_DOUBLE | PDH_FMT_NOCAP100
            if pdh.PdhGetFormattedCounterArrayW(h, fmt, ctypes.byref(size),
                                                ctypes.byref(count), None) != PDH_MORE_DATA:
                continue
            buf = ctypes.create_string_buffer(size.value)
            if pdh.PdhGetFormattedCounterArrayW(h, fmt, ctypes.byref(size),
                                                ctypes.byref(count), buf):
                continue
            items = ctypes.cast(buf, ctypes.POINTER(PDH_FMT_COUNTERVALUE_ITEM_W))
            total = 0.0
            for i in range(count.value):
                it = items[i]
                if it.FmtValue.CStatus in (0, 1) and it.szName != "_Total":
                    total += it.FmtValue.u.doubleValue
            out[key] = total
        return out

    def close(self):
        if self.q:
            pdh.PdhCloseQuery(self.q)
            self.q = None


def _cpu_times():
    idle, kern, user = (ctypes.c_ulonglong() for _ in range(3))
    kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kern), ctypes.byref(user))
    return idle.value, kern.value + user.value      # kernel time includes idle


# --------------------------------------------------------------------------- sampler

class Sampler:
    """Collects readings once a second on a daemon thread. `snapshot()` is cheap."""

    def __init__(self):
        self.data = {}
        self.hist = {"cpu": collections.deque([0.0] * HISTORY, HISTORY),
                     "gpu": collections.deque([0.0] * HISTORY, HISTORY)}
        self.lock = threading.Lock()
        self.active = True
        self._stop = threading.Event()
        self._smi = None
        self._smi_line = None
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    # nvidia-smi in loop mode: one long-lived process instead of one per second
    def _start_smi(self):
        exe = shutil.which("nvidia-smi")
        if not exe:
            return
        try:
            self._smi = subprocess.Popen(
                [exe, "--query-gpu=name,utilization.gpu,memory.used,memory.total,"
                      "temperature.gpu,power.draw",
                 "--format=csv,noheader,nounits", "-lms", "1000"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW)
        except OSError:
            self._smi = None
            return

        def reader(p):
            for line in p.stdout:
                self._smi_line = (time.monotonic(), line.strip())
        threading.Thread(target=reader, args=(self._smi,), daemon=True).start()

    def _nvidia(self):
        if not self._smi_line or time.monotonic() - self._smi_line[0] > 5:
            return None
        parts = [p.strip() for p in self._smi_line[1].split("\n")[0].split(",")]
        if len(parts) < 6:
            return None

        def num(s):
            try:
                return float(s)
            except ValueError:
                return None
        name = parts[0].replace("NVIDIA ", "").replace("GeForce ", "")
        util, used, total, temp, power = (num(p) for p in parts[1:6])
        return {"gpu_name": name, "gpu": util, "vram_used": used and used * 2**20,
                "vram_total": total and total * 2**20, "gpu_temp": temp, "gpu_power": power}

    def _run(self):
        q = Pdh({
            "gpu": r"\GPU Engine(*engtype_3D)\Utilization Percentage",
            "vram": r"\GPU Adapter Memory(*)\Dedicated Usage",
            "net_in": r"\Network Interface(*)\Bytes Received/sec",
            "net_out": r"\Network Interface(*)\Bytes Sent/sec",
        })
        # _Total is skipped when summing wildcards, so read disk idle on its own
        dq = Pdh({"disk": r"\PhysicalDisk(_Total)\% Idle Time"})
        self._start_smi()
        prev = _cpu_times()
        while not self._stop.wait(1.0):
            if not self.active:
                prev = _cpu_times()
                continue
            try:
                d = {}
                idle, total = _cpu_times()
                di, dt = idle - prev[0], total - prev[1]
                prev = (idle, total)
                d["cpu"] = max(0.0, min(100.0, 100.0 * (1 - di / dt))) if dt else 0.0

                ms = MEMORYSTATUSEX()
                ms.dwLength = ctypes.sizeof(ms)
                kernel32.GlobalMemoryStatusEx(ctypes.byref(ms))
                d["ram_total"] = ms.ullTotalPhys
                d["ram_used"] = ms.ullTotalPhys - ms.ullAvailPhys

                r = q.read()
                d["net_in"], d["net_out"] = r.get("net_in"), r.get("net_out")
                disk = _total(dq, "disk")
                d["disk"] = None if disk is None else max(0.0, min(100.0, 100.0 - disk))
                d["gpu"] = min(100.0, r["gpu"]) if "gpu" in r else None
                d["vram_used"] = r.get("vram")

                nv = self._nvidia()
                if nv:
                    d.update({k: v for k, v in nv.items() if v is not None})
                d["uptime"] = kernel32.GetTickCount64() / 1000.0

                with self.lock:
                    self.data = d
                    self.hist["cpu"].append(d["cpu"])
                    self.hist["gpu"].append(d.get("gpu") or 0.0)
            except Exception:
                pass
        q.close()
        dq.close()

    def snapshot(self):
        with self.lock:
            return dict(self.data), {k: list(v) for k, v in self.hist.items()}

    def close(self):
        self._stop.set()
        if self._smi:
            try:
                self._smi.kill()
            except OSError:
                pass
            self._smi = None


def _total(q, key):
    """Read a single non-wildcard counter (its only instance is _Total-like)."""
    if not q.q or key not in q.counters or pdh.PdhCollectQueryData(q.q):
        return None
    size, count = wt.DWORD(0), wt.DWORD(0)
    h = q.counters[key]
    if pdh.PdhGetFormattedCounterArrayW(h, PDH_FMT_DOUBLE, ctypes.byref(size),
                                        ctypes.byref(count), None) != PDH_MORE_DATA:
        return None
    buf = ctypes.create_string_buffer(size.value)
    if pdh.PdhGetFormattedCounterArrayW(h, PDH_FMT_DOUBLE, ctypes.byref(size),
                                        ctypes.byref(count), buf) or not count.value:
        return None
    return ctypes.cast(buf, ctypes.POINTER(PDH_FMT_COUNTERVALUE_ITEM_W))[0].FmtValue.u.doubleValue


# --------------------------------------------------------------------------- panel

def _size(b, per_sec=False):
    units = ["B", "K", "M", "G", "T"]
    i = 0
    while b >= 1000 and i < len(units) - 1:
        b /= 1024.0
        i += 1
    s = ("%.0f" if b >= 100 or i == 0 else "%.1f") % b
    return s + units[i] + ("/s" if per_sec else "")


def _uptime(sec):
    d, sec = divmod(int(sec), 86400)
    h, sec = divmod(sec, 3600)
    m = sec // 60
    return ("%dd %dh" % (d, h)) if d else ("%dh %02dm" % (h, m))


def _load_lv(pct):
    return "4" if pct < 60 else ("5" if pct < 85 else "7")


W = 44            # panel width in cells, borders included
GRAPH_H = 4


def panel_lines(data, hist):
    """Build the panel as a list of rows of (char, level) cells."""
    inner = W - 4
    rows = []

    def row(cells):
        cells = cells[:inner] + [(" ", "0")] * (inner - len(cells))
        rows.append([("|", "2"), (" ", "0")] + cells + [(" ", "0"), ("|", "2")])

    def txt(s, lv):
        return [(c, lv if c != " " else "0") for c in s]

    def meter(label, pct, value_text):
        bar_w = inner - 7                       # "CPU  [" + bar + "]"
        fill = int(round(bar_w * max(0.0, min(100.0, pct)) / 100.0))
        lv = _load_lv(pct)
        cells = [(c, "3") for c in label.ljust(5)] + [("[", "2")]
        bar = [("|", lv)] * fill + [(" ", "0")] * (bar_w - fill)
        vt = value_text[:bar_w]
        start = bar_w - len(vt)
        for i, c in enumerate(vt):
            bar[start + i] = (c, "5")
        row(cells + bar + [("]", "2")])

    title = "[ system ]"
    top = "+-" + title + "-" * (W - 3 - len(title)) + "+"
    rows.append([(c, "2" if c in "+-" else "3") for c in top])

    cpu = data.get("cpu", 0.0)
    meter("CPU", cpu, "%.0f%%" % cpu)

    rt, ru = data.get("ram_total"), data.get("ram_used")
    if rt:
        meter("MEM", 100.0 * ru / rt, "%s/%s" % (_size(ru), _size(rt)))

    gpu = data.get("gpu")
    if gpu is not None:
        temp = data.get("gpu_temp")
        meter("GPU", gpu, ("%.0f%%  %.0fC" % (gpu, temp)) if temp is not None else "%.0f%%" % gpu)

    vu, vt = data.get("vram_used"), data.get("vram_total")
    if vu is not None and vt:
        meter("VRAM", 100.0 * vu / vt, "%s/%s" % (_size(vu), _size(vt)))
    elif vu is not None:
        row(txt("VRAM ", "3") + txt(_size(vu), "5"))

    disk = data.get("disk")
    if disk is not None:
        meter("DISK", disk, "%.0f%%" % disk)

    ni, no = data.get("net_in"), data.get("net_out")
    if ni is not None:
        row(txt("NET  ", "3") + txt("v ", "2") + txt(_size(ni, True).ljust(10), "5")
            + txt("^ ", "2") + txt(_size(no or 0, True), "5"))

    # history graph: CPU as a filled area, GPU as a line on top of it
    rows.append([(c, "2") for c in "|" + " " * (W - 2) + "|"])
    gw = inner
    cpu_h = hist.get("cpu", [])[-gw:]
    gpu_h = hist.get("gpu", [])[-gw:]
    cpu_h = [0.0] * (gw - len(cpu_h)) + cpu_h
    gpu_h = [0.0] * (gw - len(gpu_h)) + gpu_h
    show_gpu = gpu is not None
    steps = GRAPH_H * 2
    for r in range(GRAPH_H):
        cells = []
        base = (GRAPH_H - 1 - r) * 2           # half-steps below this row
        for x in range(gw):
            h = math.ceil(cpu_h[x] / 100.0 * steps - 0.05)   # any load shows a dot
            ch = (":", "3") if h >= base + 2 else ((".", "3") if h == base + 1 else (" ", "0"))
            if show_gpu:
                gh = min(steps - 1, int(gpu_h[x] / 100.0 * steps))
                if gh // 2 == GRAPH_H - 1 - r and ch[1] == "0":
                    ch = ("-" if gh % 2 else "_", "6")
            cells.append(ch)
        row(cells)
    legend = txt("cpu", "3") + txt(" :  ", "2") + (txt("gpu", "6") + txt(" -", "6") if show_gpu else [])
    up = data.get("uptime")
    extra = []
    if data.get("gpu_power") is not None:
        extra.append("%.0fW" % data["gpu_power"])
    if up:
        extra.append("up " + _uptime(up))
    right = "  ".join(extra)
    row(legend + [(" ", "0")] * max(1, inner - len(legend) - len(right)) + txt(right, "3"))

    name = data.get("gpu_name", "")
    bottom = "+" + "-" * (W - 2) + "+"
    if name:
        tag = "[ %s ]" % name[:W - 8]
        bottom = bottom[:W - 2 - len(tag)] + tag + "-+"
    rows.append([(c, "2" if c in "+-" else "3") for c in bottom])
    return rows


CLOCK_BLOCK = 10     # rows the clock (with its margin) takes at the bottom/top


def draw_panel(g, sampler, position, clock_position=None):
    data, hist = sampler.snapshot()
    if not data:
        return
    lines = panel_lines(data, hist)
    h, w = len(lines), W
    if w + 4 > g.cols or h + 2 > g.rows:
        return
    right = position.endswith("right")
    bottom = position.startswith("bottom")
    x0 = g.cols - w - 4 if right else 4
    y0 = g.rows - h - 2 if bottom else 2
    # share a corner with the clock by stacking next to it
    if clock_position == position:
        y0 = y0 - CLOCK_BLOCK if bottom else y0 + CLOCK_BLOCK
    if y0 < 0 or y0 + h > g.rows:
        return
    g.erase(x0 - 2, y0 - 1, x0 + w + 2, y0 + h + 1)
    for yy, cells in enumerate(lines):
        for xx, (c, lv) in enumerate(cells):
            if lv != "0":
                g.put(x0 + xx, y0 + yy, c, lv)
