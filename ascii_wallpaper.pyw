"""ASCII live wallpaper for Windows.

    pythonw ascii_wallpaper.pyw              run behind the desktop icons (with a tray icon)
    pythonw ascii_wallpaper.pyw --preview    run in a normal window instead
    pythonw ascii_wallpaper.pyw --stop       stop the running instance
    pythonw ascii_wallpaper.pyw --scene rain override the scene from config.json

Starting a new instance replaces the old one. Edits to config.json are picked
up live (within a second). Most settings are also in the tray icon menu.
"""
import argparse
import json
import logging
import os
import random
import subprocess
import sys
import tempfile
import time
import traceback
import winreg

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import desktop  # noqa: E402
import scenes   # noqa: E402
import light_scenes  # noqa: E402
import sysinfo  # noqa: E402

ALL_SCENES = {**scenes.SCENES, **light_scenes.SCENES}

CONFIG_PATH = os.path.join(HERE, "config.json")
LOG_PATH = os.path.join(HERE, "wallpaper.log")
SCRIPT_PATH = os.path.abspath(__file__)
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_NAME = "AsciiWallpaper"

DEFAULTS = {
    "scene": "cycle",
    "cycle_scenes": list(scenes.SCENES),
    "scene_light": "cycle",
    "cycle_scenes_light": list(light_scenes.SCENES),
    "cycle_minutes": 10,
    "theme": "claude",
    "mode": "dark",
    "fps": 15,
    "font": "Consolas",
    "font_size": 16,
    "clock": True,
    "clock_position": "bottom-right",
    "clock_24h": True,
    "pause_when_fullscreen": True,
    "stats": "off",                 # off | top-left | top-right | bottom-left | bottom-right
    "stats_monitor": "primary",     # primary | all
    "taskbar_match": False,         # dark/light taskbar following the wallpaper mode
    "taskbar_restore": None,        # the taskbar setting to put back when matching stops
}

STATS_POSITIONS = ["top-left", "top-right", "bottom-left", "bottom-right"]

THEMES = {
    "claude": {"bg": "#141413",
               "ramp": ["#2b2a26", "#47453f", "#706d64", "#a8a59b", "#ece9df"],
               "accent": ["#c15f3c", "#e08a62"]},
    "amber": {"bg": "#0d0904",
              "ramp": ["#2a1d08", "#4d350f", "#80591a", "#c28a2c", "#ffd27a"],
              "accent": ["#ff9d1c", "#ffe0a0"]},
    "matrix": {"bg": "#030803",
               "ramp": ["#0b2a0d", "#145218", "#1f7a26", "#37b843", "#b4ffbc"],
               "accent": ["#2eff6a", "#d8ffe0"]},
    "ice": {"bg": "#0a0f17",
            "ramp": ["#1a2738", "#2a4058", "#4a6a8c", "#8fb3d9", "#e6f2ff"],
            "accent": ["#3d8bfd", "#9fd0ff"]},
    "sakura": {"bg": "#17101a",
               "ramp": ["#2d2030", "#4a3550", "#7a5a80", "#b894bd", "#f7e6f5"],
               "accent": ["#e05a8a", "#ffb0cc"]},
    "mono": {"bg": "#000000",
             "ramp": ["#262626", "#474747", "#777777", "#b0b0b0", "#f0f0f0"],
             "accent": ["#9a9a9a", "#ffffff"]},
}

# Off-white "light mode" versions. Levels keep their meaning (5 = strongest), so on a
# light background they run from faint grey to dark ink.
LIGHT_THEMES = {
    "claude": {"bg": "#f0eee6",
               "ramp": ["#dcd9cf", "#c3c0b5", "#9a978d", "#5f5d56", "#1f1e1c"],
               "accent": ["#d97757", "#b5502f"]},
    "amber": {"bg": "#f6efe2",
              "ramp": ["#e6d9bf", "#d2bd93", "#b08a4a", "#7a5520", "#3a2508"],
              "accent": ["#e8890c", "#b85f00"]},
    "matrix": {"bg": "#eef4ee",
               "ramp": ["#d3e3d4", "#b0cdb3", "#7aa880", "#3f7a47", "#0f3d16"],
               "accent": ["#1fae4a", "#0b7a2c"]},
    "ice": {"bg": "#eef2f7",
            "ramp": ["#d6dfea", "#b6c6da", "#8aa3c0", "#4d6b8f", "#1a2c44"],
            "accent": ["#3d8bfd", "#1559c4"]},
    "sakura": {"bg": "#f8eff3",
               "ramp": ["#ead8e0", "#d9bccb", "#b98fa6", "#7f5770", "#3a2234"],
               "accent": ["#e05a8a", "#b8325f"]},
    "mono": {"bg": "#f2f2f2",
             "ramp": ["#dddddd", "#c2c2c2", "#969696", "#5a5a5a", "#1a1a1a"],
             "accent": ["#777777", "#000000"]},
}

CYCLE_CHOICES = [1, 2, 5, 10, 15, 30, 60]

# tray menu command ids
(CMD_PAUSE, CMD_NEXT, CMD_CLOCK, CMD_STARTUP, CMD_OPEN, CMD_QUIT, CMD_CYCLE,
 CMD_DARK, CMD_LIGHT, CMD_ROTATION, CMD_TB_MATCH, CMD_TB_HIDE, CMD_STATS_ALL,
 CMD_RESTART) = range(1, 15)
CMD_SCENE, CMD_ROTATE, CMD_MINUTES, CMD_THEME, CMD_STATS = 100, 200, 300, 400, 500
CMD_STATS_SCREEN = 600          # 601+ = show the stats on that monitor


def load_config():
    cfg = dict(DEFAULTS)
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg.update(json.load(f))
    except FileNotFoundError:
        pass
    except Exception:
        logging.exception("config.json is invalid, using defaults")
    return cfg


def resolve_theme(theme, mode="dark"):
    if isinstance(theme, dict):
        t = theme.get("light", theme) if mode == "light" else theme
    else:
        table = LIGHT_THEMES if mode == "light" else THEMES
        t = table.get(theme, table["claude"])
    ramp, accent = t["ramp"], t["accent"]
    colors = {str(i + 1): desktop.rgb(c) for i, c in enumerate(ramp[:5])}
    colors["6"] = desktop.rgb(accent[0])
    colors["7"] = desktop.rgb(accent[1])
    return t, colors


def pythonw_path():
    exe = sys.executable
    cand = os.path.join(os.path.dirname(exe), "pythonw.exe")
    return cand if os.path.exists(cand) else exe


# Startup uses a Task Scheduler "at log on" task: programs in the registry Run key
# are held back by Windows for a minute or more after logon, a logon task is not.
# The Run key stays as a fallback for machines where the task can't be created.

TASK_NAME = "AsciiWallpaper"


def _schtasks(*args):
    try:
        r = subprocess.run(["schtasks", *args], capture_output=True, text=True,
                           creationflags=subprocess.CREATE_NO_WINDOW, timeout=20)
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _task_xml():
    user = "%s\\%s" % (os.environ.get("USERDOMAIN", ""), os.environ.get("USERNAME", ""))
    esc = lambda s: (s.replace("&", "&amp;").replace("<", "&lt;")
                     .replace(">", "&gt;").replace('"', "&quot;"))
    return f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo><Description>ASCII live wallpaper</Description></RegistrationInfo>
  <Triggers>
    <LogonTrigger><Enabled>true</Enabled><UserId>{esc(user)}</UserId></LogonTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>{esc(user)}</UserId>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{esc(pythonw_path())}</Command>
      <Arguments>"{esc(SCRIPT_PATH)}"</Arguments>
      <WorkingDirectory>{esc(os.path.dirname(SCRIPT_PATH))}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"""


def _run_key(value=None, delete=False):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                            winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE) as k:
            if delete:
                winreg.DeleteValue(k, RUN_NAME)
            elif value is not None:
                winreg.SetValueEx(k, RUN_NAME, 0, winreg.REG_SZ, value)
            else:
                winreg.QueryValueEx(k, RUN_NAME)
            return True
    except OSError:
        return False


def startup_enabled():
    return _schtasks("/Query", "/TN", TASK_NAME) or _run_key()


def set_startup(on):
    if not on:
        _schtasks("/Delete", "/TN", TASK_NAME, "/F")
        _run_key(delete=True)
        return
    path = os.path.join(tempfile.gettempdir(), "ascii_wallpaper_task.xml")
    with open(path, "w", encoding="utf-16") as f:
        f.write(_task_xml())
    try:
        ok = _schtasks("/Create", "/TN", TASK_NAME, "/XML", path, "/F")
    finally:
        os.remove(path)
    if ok:
        _run_key(delete=True)   # one launcher is enough
    else:
        logging.warning("could not create logon task, using the Run key instead")
        _run_key('"%s" "%s"' % (pythonw_path(), SCRIPT_PATH))


def label(name):
    return (scenes.SCENE_LABELS.get(name) or light_scenes.SCENE_LABELS.get(name)
            or name.replace("_", " ").title())


class App:
    def __init__(self, preview=False, scene_override=None, light=False):
        self.light_override = light
        self.preview = preview
        self.scene_override = scene_override
        self.quit = False
        self.user_paused = False
        self.surfaces = []
        self.rng = random.Random()
        self.cfg_mtime = self._mtime()
        self.cfg = load_config()
        if light:
            self.cfg["mode"] = "light"
        self.cycle_idx = self.rng.randrange(1000)
        self.next_switch = time.perf_counter() + self.period()
        self.ctl = desktop.create_control_window(self)
        self.tray = None
        self.icons = None
        self.sampler = None
        self.screen_list = []
        if not preview:
            self.make_tray()
        self.build()

    # ---------------------------------------------------------------- basics

    def on_message(self, hwnd, msg, wp, lp):   # control window
        if msg == desktop.WM_CLOSE:
            self.quit = True
            return 0
        return None

    def _mtime(self):
        try:
            return os.path.getmtime(CONFIG_PATH)
        except OSError:
            return 0

    def period(self):
        return max(0.1, float(self.cfg["cycle_minutes"])) * 60

    # dark and light mode each have their own scene library, choice and rotation list
    def light(self):
        return self.cfg.get("mode") == "light"

    def library(self):
        return light_scenes.SCENES if self.light() else scenes.SCENES

    def k_scene(self):
        return "scene_light" if self.light() else "scene"

    def k_rot(self):
        return "cycle_scenes_light" if self.light() else "cycle_scenes"

    def cycling(self):
        return self.cfg[self.k_scene()] == "cycle"

    def pool(self):
        lib = self.library()
        return [n for n in self.cfg[self.k_rot()] if n in lib] or list(lib)

    def save_config(self, **changes):
        self.cfg.update(changes)
        saved = {k: self.cfg[k] for k in DEFAULTS}
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(saved, f, indent=2)
            f.write("\n")
        self.cfg_mtime = self._mtime()

    def apply_theme(self):
        theme, self.colors = resolve_theme(self.cfg["theme"], self.cfg.get("mode", "dark"))
        self.bg = theme["bg"]
        for s in self.surfaces:
            s.set_bg(self.bg)
        if self.preview:
            return
        self.apply_taskbar()
        theme, _ = resolve_theme(self.cfg["theme"], "dark")   # tray icon always dark
        key = (theme["bg"], theme["accent"][1], theme["ramp"][1])
        if self.icons is None or self.icons[2] != key:
            old = self.icons
            self.icons = (desktop.make_icon(theme["bg"], theme["accent"][1]),
                          desktop.make_icon(theme["bg"], theme["ramp"][1]), key)
            self.update_tray()
            if old:
                desktop.DestroyIcon(old[0])
                desktop.DestroyIcon(old[1])

    def apply_taskbar(self):
        """Keep the taskbar dark/light in step with the wallpaper mode while
        matching is on; put the user's own setting back when it goes off."""
        try:
            if self.cfg["taskbar_match"]:
                if self.cfg["taskbar_restore"] is None:
                    self.save_config(taskbar_restore=desktop.taskbar_light())
                desktop.set_taskbar_light(self.light())
            elif self.cfg["taskbar_restore"] is not None:
                desktop.set_taskbar_light(self.cfg["taskbar_restore"])
                self.save_config(taskbar_restore=None)
        except Exception:
            logging.exception("taskbar update failed")

    def stats_on(self):
        return self.cfg["stats"] in STATS_POSITIONS

    def update_sampler(self):
        if self.stats_on() and not self.sampler:
            self.sampler = sysinfo.Sampler()
        elif not self.stats_on() and self.sampler:
            self.sampler.close()
            self.sampler = None
        if self.sampler:
            self.sampler.active = not self.user_paused and any(
                not s.paused for s in self.surfaces)

    def shows_stats(self, s):
        if not self.sampler:
            return False
        where = self.cfg["stats_monitor"]
        if where == "all" or self.preview:
            return True
        devices = [m.get("device") for m in (x.monitor for x in self.surfaces)]
        if where != "primary" and where in devices:
            return s.monitor.get("device") == where
        # "primary", or a screen that is no longer connected: use the main one
        return s.monitor.get("primary", tuple(s.monitor["rect"][:2]) == (0, 0))

    def build(self):
        for s in self.surfaces:
            s.destroy()
        self.surfaces = []
        self.apply_theme()
        if self.user_paused:
            return
        font, size = self.cfg["font"], float(self.cfg["font_size"])
        if self.preview:
            mons = [{"hmon": None, "rect": (0, 0, 1280, 720), "work": (0, 0, 1280, 720)}]
            host = None
        else:
            host = desktop.find_desktop_host()
            if host is None:
                return
            mons = desktop.list_monitors()
            logging.info("desktop host mode=%s, %d monitor(s)", host["mode"], len(mons))
        self.layout = [m["rect"] + m["work"] for m in mons]
        for i, m in enumerate(mons):
            s = desktop.Surface(m, host, font, size, self.bg, preview=self.preview)
            if self.preview:
                s.on_close = self.stop
            s.index = i
            s.scene_name = None
            s.scene = None
            s.grid = scenes.Grid(s.cols, s.rows)
            s.paused = False
            self.surfaces.append(s)

    def stop(self):
        self.quit = True

    def scene_name_for(self, idx):
        if self.scene_override in ALL_SCENES:
            return self.scene_override
        name = self.cfg[self.k_scene()]
        if name in ("cycle", "random"):
            pool = self.pool()
            return pool[(self.cycle_idx + idx) % len(pool)]
        return name if name in self.library() else list(self.library())[0]

    # ---------------------------------------------------------------- tray

    def make_tray(self):
        self.apply_theme()
        self.tray = desktop.Tray(self.icons[0], "ASCII wallpaper", self.on_tray_click)

    def update_tray(self):
        if not self.tray:
            return
        if self.user_paused:
            tip = "ASCII wallpaper - off"
        elif self.cycling():
            names = sorted({label(self.scene_name_for(s.index)) for s in self.surfaces})
            tip = "ASCII wallpaper - %s (rotating every %s min)" % (
                ", ".join(names), self.cfg["cycle_minutes"])
        else:
            tip = "ASCII wallpaper - %s" % label(self.cfg[self.k_scene()])
        self.tray.update(icon=self.icons[1 if self.user_paused else 0], tip=tip)

    def menu_spec(self):
        cfg = self.cfg
        try:
            self.screen_list = desktop.monitor_labels(desktop.list_monitors())
        except Exception:
            self.screen_list = []
        cycling = self.cycling()
        wall = [("Rotate through scenes", CMD_CYCLE, cycling, True, True), None]
        names = list(self.library())
        for i, n in enumerate(names):
            wall.append((label(n), CMD_SCENE + i, cfg[self.k_scene()] == n, True, True))
        rotate = [(label(n), CMD_ROTATE + i, n in cfg[self.k_rot()]) for i, n in enumerate(names)]
        mins = [("%d minute%s" % (m, "" if m == 1 else "s"), CMD_MINUTES + i,
                 float(cfg["cycle_minutes"]) == m, True, True)
                for i, m in enumerate(CYCLE_CHOICES)]
        themes = [(label(n), CMD_THEME + i, cfg["theme"] == n, True, True)
                  for i, n in enumerate(THEMES)]
        stats = [("Off", CMD_STATS, not self.stats_on(), True, True)]
        stats += [(p.replace("-", " ").capitalize(), CMD_STATS + 1 + i, cfg["stats"] == p,
                   True, True) for i, p in enumerate(STATS_POSITIONS)]
        where = cfg["stats_monitor"]
        devices = [dev for dev, _, _ in self.screen_list]
        screens = [("Every monitor", CMD_STATS_ALL, where == "all", True, True), None]
        # "primary" (the default) or a monitor that's gone: the main one is ticked
        screens += [(name, CMD_STATS_SCREEN + 1 + i,
                     where == dev or (where not in devices and where != "all" and main),
                     True, True)
                    for i, (dev, name, main) in enumerate(self.screen_list)]
        stats += [None, ("Show on", screens)]
        try:
            hidden = desktop.taskbar_autohide()
        except Exception:
            hidden = False
        taskbar = [("Match appearance (dark/light)", CMD_TB_MATCH, bool(cfg["taskbar_match"])),
                   ("Auto-hide", CMD_TB_HIDE, hidden)]
        return [
            ("ASCII wallpaper", 0, False, False),
            None,
            ("Turn on" if self.user_paused else "Turn off", CMD_PAUSE),
            ("Next scene", CMD_NEXT, False, not self.user_paused),
            ("Rotate scenes", CMD_ROTATION, cycling),
            None,
            ("Wallpaper (%s)" % ("light" if self.light() else "dark"), wall),
            ("Scenes in rotation", rotate),
            ("Change every", mins),
            ("Theme", themes),
            ("Appearance", [
                ("Dark", CMD_DARK, cfg.get("mode", "dark") != "light", True, True),
                ("Light (off-white)", CMD_LIGHT, cfg.get("mode") == "light", True, True),
            ]),
            ("Show clock", CMD_CLOCK, bool(cfg["clock"])),
            ("System stats", stats),
            ("Taskbar", taskbar),
            None,
            ("Start with Windows", CMD_STARTUP, startup_enabled()),
            ("Restart", CMD_RESTART),
            ("Open settings file", CMD_OPEN),
            ("Quit", CMD_QUIT),
        ]

    def on_tray_click(self):
        try:
            self.run_command(self.tray.popup(self.menu_spec()))
        except Exception:
            logging.exception("menu command failed")

    def run_command(self, cmd):
        names = list(self.library())
        ks, kr = self.k_scene(), self.k_rot()
        now = time.perf_counter()
        if cmd == CMD_PAUSE:
            self.user_paused = not self.user_paused
            self.build()
            if self.user_paused:
                desktop.refresh_wallpaper()
        elif cmd == CMD_NEXT:
            if self.cycling():
                self.cycle_idx += 1
                self.next_switch = now + self.period()
            else:
                cur = names.index(self.cfg[ks]) if self.cfg[ks] in names else -1
                self.save_config(**{ks: names[(cur + 1) % len(names)]})
        elif cmd == CMD_CYCLE:
            self.save_config(**{ks: "cycle"})
            self.next_switch = now + self.period()
        elif CMD_SCENE <= cmd < CMD_SCENE + len(names):
            self.save_config(**{ks: names[cmd - CMD_SCENE]})
        elif CMD_ROTATE <= cmd < CMD_ROTATE + len(names):
            n = names[cmd - CMD_ROTATE]
            rot = [x for x in self.cfg[kr] if x in names]
            if n in rot:
                if len(rot) > 1:
                    rot.remove(n)
            else:
                rot = [x for x in names if x in rot or x == n]
            self.save_config(**{kr: rot})
        elif CMD_MINUTES <= cmd < CMD_MINUTES + len(CYCLE_CHOICES):
            self.save_config(cycle_minutes=CYCLE_CHOICES[cmd - CMD_MINUTES])
            self.next_switch = now + self.period()
        elif CMD_THEME <= cmd < CMD_THEME + len(THEMES):
            self.save_config(theme=list(THEMES)[cmd - CMD_THEME])
            self.apply_theme()
        elif cmd in (CMD_DARK, CMD_LIGHT):
            self.save_config(mode="light" if cmd == CMD_LIGHT else "dark")
            self.apply_theme()
        elif cmd == CMD_CLOCK:
            self.save_config(clock=not self.cfg["clock"])
        elif cmd == CMD_ROTATION:
            if self.cycling():
                # freeze on whatever the main monitor shows right now
                shown = [s.scene_name for s in self.surfaces if s.scene_name in names]
                self.save_config(**{ks: shown[0] if shown else self.scene_name_for(0)})
            else:
                self.save_config(**{ks: "cycle"})
                self.next_switch = now + self.period()
        elif CMD_STATS <= cmd <= CMD_STATS + len(STATS_POSITIONS):
            i = cmd - CMD_STATS
            self.save_config(stats=STATS_POSITIONS[i - 1] if i else "off")
            self.update_sampler()
        elif cmd == CMD_STATS_ALL:
            self.save_config(stats_monitor="all")
        elif CMD_STATS_SCREEN < cmd <= CMD_STATS_SCREEN + len(self.screen_list):
            self.save_config(stats_monitor=self.screen_list[cmd - CMD_STATS_SCREEN - 1][0])
        elif cmd == CMD_TB_MATCH:
            self.save_config(taskbar_match=not self.cfg["taskbar_match"])
            self.apply_taskbar()
        elif cmd == CMD_TB_HIDE:
            desktop.set_taskbar_autohide(not desktop.taskbar_autohide())
        elif cmd == CMD_STARTUP:
            set_startup(not startup_enabled())
        elif cmd == CMD_OPEN:
            os.startfile(CONFIG_PATH)
        elif cmd == CMD_RESTART:
            # a fresh process (also picks up code updates); it closes this one
            logging.info("restart requested from the tray")
            subprocess.Popen([pythonw_path(), SCRIPT_PATH], cwd=HERE,
                             creationflags=subprocess.CREATE_NO_WINDOW)
        elif cmd == CMD_QUIT:
            self.quit = True
        self.update_tray()

    # ---------------------------------------------------------------- loop

    def housekeeping(self):
        m = self._mtime()
        if m != self.cfg_mtime:
            self.cfg_mtime = m
            self.cfg = load_config()
            logging.info("config reloaded")
            self.build()
            self.update_tray()
            self.update_sampler()
            return
        if self.preview or self.user_paused:
            self.update_sampler()
            return
        broken = not self.surfaces or any(not s.is_valid() for s in self.surfaces)
        mons = desktop.list_monitors()
        layout = [mm["rect"] + mm["work"] for mm in mons]
        if broken or layout != self.layout:
            logging.info("desktop changed (broken=%s), rebuilding", broken)
            self.build()
            return
        if desktop.session_locked():
            covered = None                          # lock screen: nobody sees it
        elif self.cfg["pause_when_fullscreen"]:
            covered = desktop.covered_monitors()
        else:
            covered = set()
        for s in self.surfaces:
            s.paused = covered is None or s.monitor["hmon"] in covered
        self.update_sampler()

    def run(self):
        t0 = last = time.perf_counter()
        next_house = 0.0
        while not self.quit:
            desktop.pump_messages()
            if self.quit:
                break
            now = time.perf_counter()
            t, dt = now - t0, min(now - last, 0.25)
            last = now
            if now >= next_house:
                next_house = now + 1.0
                try:
                    self.housekeeping()
                except Exception:
                    logging.exception("housekeeping failed")
            if self.cycling() and now >= self.next_switch:
                self.cycle_idx += 1
                self.next_switch = now + self.period()
                self.update_tray()
            cfg = self.cfg
            for s in self.surfaces:
                if s.paused or not s.alive:
                    continue
                name = self.scene_name_for(s.index)
                if name != s.scene_name:
                    s.scene = ALL_SCENES[name](s.cols, s.rows, self.rng, s.aspect)
                    s.scene_name = name
                    self.update_tray()
                g = s.grid
                g.clear()
                s.scene.frame(g, t, dt)
                if cfg["clock"]:
                    scenes.draw_clock(g, cfg["clock_position"], cfg["clock_24h"])
                if self.shows_stats(s):
                    sysinfo.draw_panel(g, self.sampler, cfg["stats"],
                                       cfg["clock_position"] if cfg["clock"] else None)
                s.draw(*g.out(), self.colors)
            frame = 1.0 / max(1.0, float(cfg["fps"]))
            idle = all(s.paused for s in self.surfaces) if self.surfaces else True
            spent = time.perf_counter() - now
            time.sleep(0.1 if idle else max(0.001, frame - spent))
        self.shutdown()

    def shutdown(self):
        for s in self.surfaces:
            s.destroy()
        self.surfaces = []
        if self.tray:
            self.tray.remove()
            self.tray = None
        if self.sampler:
            self.sampler.close()
            self.sampler = None
        if not self.preview:
            if self.cfg["taskbar_match"] and self.cfg["taskbar_restore"] is not None:
                try:
                    desktop.set_taskbar_light(self.cfg["taskbar_restore"])
                except Exception:
                    pass
            desktop.refresh_wallpaper()


def stop_existing(timeout=4.0):
    """Ask every running copy to close, and wait for them to go."""
    hwnds = desktop.find_running_instances()
    if not hwnds:
        return False
    for hwnd in hwnds:
        desktop.PostMessageW(hwnd, desktop.WM_CLOSE, 0, 0)
    end = time.time() + timeout
    while time.time() < end and desktop.find_running_instances():
        time.sleep(0.05)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--stop", action="store_true")
    ap.add_argument("--scene")
    ap.add_argument("--light", action="store_true", help="preview the off-white mode")
    ap.add_argument("--startup", choices=["on", "off"], help="start with Windows, then exit")
    args = ap.parse_args()

    logging.basicConfig(filename=LOG_PATH, level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    desktop.set_dpi_aware()
    if args.startup:
        set_startup(args.startup == "on")
        print("start with Windows:", "on" if startup_enabled() else "off",
              "(logon task)" if _schtasks("/Query", "/TN", TASK_NAME) else "")
        return
    if args.stop:
        stop_existing()
        return
    if not args.preview:
        stop_existing()
        # the copies just asked to close release this as they exit
        if not desktop.claim_single_instance(8000):
            logging.info("another copy is already running; exiting")
            return
        desktop.efficiency_mode()
    try:
        App(preview=args.preview, scene_override=args.scene, light=args.light).run()
    except Exception:
        logging.error("crashed:\n%s", traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
