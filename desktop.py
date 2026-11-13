"""Win32 plumbing: put windows behind the desktop icons and blit text with GDI.

Pure ctypes, no third-party packages.
"""
import ctypes
import re
from ctypes import wintypes as wt

user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

LRESULT = ctypes.c_ssize_t
LONG_PTR = ctypes.c_ssize_t
ULONG_PTR = ctypes.c_size_t
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM)
WNDENUMPROC = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
MONITORENUMPROC = ctypes.WINFUNCTYPE(
    wt.BOOL, wt.HMONITOR, wt.HDC, ctypes.POINTER(wt.RECT), wt.LPARAM)


class WNDCLASSEXW(ctypes.Structure):
    _fields_ = [("cbSize", wt.UINT), ("style", wt.UINT), ("lpfnWndProc", WNDPROC),
                ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int),
                ("hInstance", wt.HINSTANCE), ("hIcon", wt.HICON), ("hCursor", wt.HANDLE),
                ("hbrBackground", wt.HBRUSH), ("lpszMenuName", wt.LPCWSTR),
                ("lpszClassName", wt.LPCWSTR), ("hIconSm", wt.HICON)]


class MONITORINFO(ctypes.Structure):   # MONITORINFOEXW: includes the device name
    _fields_ = [("cbSize", wt.DWORD), ("rcMonitor", wt.RECT),
                ("rcWork", wt.RECT), ("dwFlags", wt.DWORD), ("szDevice", wt.WCHAR * 32)]


class PAINTSTRUCT(ctypes.Structure):
    _fields_ = [("hdc", wt.HDC), ("fErase", wt.BOOL), ("rcPaint", wt.RECT),
                ("fRestore", wt.BOOL), ("fIncUpdate", wt.BOOL),
                ("rgbReserved", ctypes.c_byte * 32)]


def _f(dll, name, restype, *argtypes):
    fn = getattr(dll, name)
    fn.restype = restype
    fn.argtypes = argtypes
    return fn


_I = ctypes.c_int
RegisterClassExW = _f(user32, "RegisterClassExW", wt.ATOM, ctypes.POINTER(WNDCLASSEXW))
CreateWindowExW = _f(user32, "CreateWindowExW", wt.HWND, wt.DWORD, wt.LPCWSTR, wt.LPCWSTR,
                     wt.DWORD, _I, _I, _I, _I, wt.HWND, wt.HMENU, wt.HINSTANCE, wt.LPVOID)
DefWindowProcW = _f(user32, "DefWindowProcW", LRESULT, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM)
DestroyWindow = _f(user32, "DestroyWindow", wt.BOOL, wt.HWND)
IsWindow = _f(user32, "IsWindow", wt.BOOL, wt.HWND)
GetWindow = _f(user32, "GetWindow", wt.HWND, wt.HWND, wt.UINT)
GW_HWNDNEXT = 2
FindWindowW = _f(user32, "FindWindowW", wt.HWND, wt.LPCWSTR, wt.LPCWSTR)
FindWindowExW = _f(user32, "FindWindowExW", wt.HWND, wt.HWND, wt.HWND, wt.LPCWSTR, wt.LPCWSTR)
SendMessageTimeoutW = _f(user32, "SendMessageTimeoutW", LRESULT, wt.HWND, wt.UINT, wt.WPARAM,
                         wt.LPARAM, wt.UINT, wt.UINT, ctypes.POINTER(ULONG_PTR))
PostMessageW = _f(user32, "PostMessageW", wt.BOOL, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM)
EnumWindows = _f(user32, "EnumWindows", wt.BOOL, WNDENUMPROC, wt.LPARAM)
SetWindowPos = _f(user32, "SetWindowPos", wt.BOOL, wt.HWND, wt.HWND, _I, _I, _I, _I, wt.UINT)
GetWindowLongPtrW = _f(user32, "GetWindowLongPtrW", LONG_PTR, wt.HWND, _I)
SetLayeredWindowAttributes = _f(user32, "SetLayeredWindowAttributes", wt.BOOL, wt.HWND,
                                wt.COLORREF, wt.BYTE, wt.DWORD)
PeekMessageW = _f(user32, "PeekMessageW", wt.BOOL, ctypes.POINTER(wt.MSG), wt.HWND,
                  wt.UINT, wt.UINT, wt.UINT)
TranslateMessage = _f(user32, "TranslateMessage", wt.BOOL, ctypes.POINTER(wt.MSG))
DispatchMessageW = _f(user32, "DispatchMessageW", LRESULT, ctypes.POINTER(wt.MSG))
GetDC = _f(user32, "GetDC", wt.HDC, wt.HWND)
ReleaseDC = _f(user32, "ReleaseDC", _I, wt.HWND, wt.HDC)
BeginPaint = _f(user32, "BeginPaint", wt.HDC, wt.HWND, ctypes.POINTER(PAINTSTRUCT))
EndPaint = _f(user32, "EndPaint", wt.BOOL, wt.HWND, ctypes.POINTER(PAINTSTRUCT))
FillRect = _f(user32, "FillRect", _I, wt.HDC, ctypes.POINTER(wt.RECT), wt.HBRUSH)
ScreenToClient = _f(user32, "ScreenToClient", wt.BOOL, wt.HWND, ctypes.POINTER(wt.POINT))
GetForegroundWindow = _f(user32, "GetForegroundWindow", wt.HWND)
GetWindowRect = _f(user32, "GetWindowRect", wt.BOOL, wt.HWND, ctypes.POINTER(wt.RECT))
GetClientRect = _f(user32, "GetClientRect", wt.BOOL, wt.HWND, ctypes.POINTER(wt.RECT))
IsZoomed = _f(user32, "IsZoomed", wt.BOOL, wt.HWND)
IsIconic = _f(user32, "IsIconic", wt.BOOL, wt.HWND)
OpenInputDesktop = _f(user32, "OpenInputDesktop", wt.HANDLE, wt.DWORD, wt.BOOL, wt.DWORD)
CloseDesktop = _f(user32, "CloseDesktop", wt.BOOL, wt.HANDLE)
GetUserObjectInformationW = _f(user32, "GetUserObjectInformationW", wt.BOOL, wt.HANDLE, _I,
                               ctypes.c_void_p, wt.DWORD, ctypes.POINTER(wt.DWORD))
dwmapi = ctypes.WinDLL("dwmapi")
DwmGetWindowAttribute = _f(dwmapi, "DwmGetWindowAttribute", ctypes.c_long, wt.HWND, wt.DWORD,
                           ctypes.c_void_p, wt.DWORD)
DWMWA_CLOAKED = 14
kernel32.GetCurrentProcess.restype = wt.HANDLE
kernel32.SetPriorityClass.argtypes = [wt.HANDLE, wt.DWORD]
kernel32.SetProcessInformation.argtypes = [wt.HANDLE, _I, ctypes.c_void_p, wt.DWORD]
IsWindowVisible = _f(user32, "IsWindowVisible", wt.BOOL, wt.HWND)
GetClassNameW = _f(user32, "GetClassNameW", _I, wt.HWND, wt.LPWSTR, _I)
MonitorFromWindow = _f(user32, "MonitorFromWindow", wt.HMONITOR, wt.HWND, wt.DWORD)
EnumDisplayMonitors = _f(user32, "EnumDisplayMonitors", wt.BOOL, wt.HDC,
                         ctypes.POINTER(wt.RECT), MONITORENUMPROC, wt.LPARAM)
GetMonitorInfoW = _f(user32, "GetMonitorInfoW", wt.BOOL, wt.HMONITOR, ctypes.POINTER(MONITORINFO))
SystemParametersInfoW = _f(user32, "SystemParametersInfoW", wt.BOOL, wt.UINT, wt.UINT,
                           wt.LPVOID, wt.UINT)
GetDpiForWindow = _f(user32, "GetDpiForWindow", wt.UINT, wt.HWND)
SetProcessDpiAwarenessContext = _f(user32, "SetProcessDpiAwarenessContext", wt.BOOL, wt.HANDLE)
GetModuleHandleW = _f(kernel32, "GetModuleHandleW", wt.HMODULE, wt.LPCWSTR)

CreateCompatibleDC = _f(gdi32, "CreateCompatibleDC", wt.HDC, wt.HDC)
CreateCompatibleBitmap = _f(gdi32, "CreateCompatibleBitmap", wt.HBITMAP, wt.HDC, _I, _I)
SelectObject = _f(gdi32, "SelectObject", wt.HGDIOBJ, wt.HDC, wt.HGDIOBJ)
DeleteObject = _f(gdi32, "DeleteObject", wt.BOOL, wt.HGDIOBJ)
DeleteDC = _f(gdi32, "DeleteDC", wt.BOOL, wt.HDC)
BitBlt = _f(gdi32, "BitBlt", wt.BOOL, wt.HDC, _I, _I, _I, _I, wt.HDC, _I, _I, wt.DWORD)
CreateFontW = _f(gdi32, "CreateFontW", wt.HFONT, _I, _I, _I, _I, _I, wt.DWORD, wt.DWORD,
                 wt.DWORD, wt.DWORD, wt.DWORD, wt.DWORD, wt.DWORD, wt.DWORD, wt.LPCWSTR)
SetTextColor = _f(gdi32, "SetTextColor", wt.COLORREF, wt.HDC, wt.COLORREF)
SetBkMode = _f(gdi32, "SetBkMode", _I, wt.HDC, _I)
TextOutW = _f(gdi32, "TextOutW", wt.BOOL, wt.HDC, _I, _I, wt.LPCWSTR, _I)
CreateSolidBrush = _f(gdi32, "CreateSolidBrush", wt.HBRUSH, wt.COLORREF)
GetTextExtentPoint32W = _f(gdi32, "GetTextExtentPoint32W", wt.BOOL, wt.HDC, wt.LPCWSTR, _I,
                           ctypes.POINTER(wt.SIZE))

WS_CHILD, WS_VISIBLE, WS_CLIPSIBLINGS = 0x40000000, 0x10000000, 0x04000000
WS_OVERLAPPEDWINDOW = 0x00CF0000
WS_EX_LAYERED, WS_EX_NOACTIVATE, WS_EX_TOOLWINDOW = 0x00080000, 0x08000000, 0x00000080
WS_EX_TRANSPARENT = 0x00000020
WS_EX_NOREDIRECTIONBITMAP = 0x00200000
GWL_EXSTYLE = -20
SWP_NOSIZE, SWP_NOMOVE, SWP_NOACTIVATE = 0x1, 0x2, 0x10
WM_DESTROY, WM_PAINT, WM_CLOSE, WM_ERASEBKGND, WM_QUIT = 0x2, 0xF, 0x10, 0x14, 0x12
WM_NCHITTEST, HTTRANSPARENT = 0x84, -1
PM_REMOVE = 1
SMTO_NORMAL = 0
LWA_ALPHA = 2
SRCCOPY = 0x00CC0020
TRANSPARENT = 1
CW_USEDEFAULT = -0x80000000
HWND_MESSAGE = wt.HWND(-3)
MONITOR_DEFAULTTONEAREST = 2
SPI_GETDESKWALLPAPER, SPI_SETDESKWALLPAPER = 0x0073, 0x0014

SURFACE_CLASS = "AsciiWallpaperSurface"
CONTROL_CLASS = "AsciiWallpaperControl"
TRAY_CLASS = "AsciiWallpaperTray"

# A run is one colour level plus any empty ('0', always a space) cells between
# its pieces: text is drawn with a transparent background, so the spaces cost
# nothing and one TextOut call covers what used to take several.
_RUNS = re.compile(r"([1-7])(?:0*\1)*")


def set_dpi_aware():
    try:
        SetProcessDpiAwarenessContext(wt.HANDLE(-4))  # per-monitor v2
    except Exception:
        pass


def rgb(hexstr):
    """'#rrggbb' -> COLORREF (0x00bbggrr)."""
    h = hexstr.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return r | (g << 8) | (b << 16)


def class_name(hwnd):
    buf = ctypes.create_unicode_buffer(256)
    GetClassNameW(hwnd, buf, 256)
    return buf.value


# --------------------------------------------------------------------------- windows

_handlers = {}          # hwnd value -> object with on_message(msg, wp, lp)
_registered = False


@WNDPROC
def _wndproc(hwnd, msg, wp, lp):
    obj = _handlers.get(hwnd)
    if obj is not None:
        r = obj.on_message(hwnd, msg, wp, lp)
        if r is not None:
            return r
    return DefWindowProcW(hwnd, msg, wp, lp)


def register_classes():
    global _registered
    if _registered:
        return
    hinst = GetModuleHandleW(None)
    for name in (SURFACE_CLASS, CONTROL_CLASS, TRAY_CLASS):
        wc = WNDCLASSEXW()
        wc.cbSize = ctypes.sizeof(WNDCLASSEXW)
        wc.lpfnWndProc = _wndproc
        wc.hInstance = hinst
        wc.lpszClassName = name
        RegisterClassExW(ctypes.byref(wc))
    _registered = True


def pump_messages():
    msg = wt.MSG()
    while PeekMessageW(ctypes.byref(msg), None, 0, 0, PM_REMOVE):
        TranslateMessage(ctypes.byref(msg))
        DispatchMessageW(ctypes.byref(msg))


def create_control_window(handler):
    """Hidden message-only window so another instance can find and stop us."""
    register_classes()
    hwnd = CreateWindowExW(0, CONTROL_CLASS, "ascii-wallpaper", 0, 0, 0, 0, 0,
                           HWND_MESSAGE, None, GetModuleHandleW(None), None)
    _handlers[hwnd] = handler
    return hwnd


def find_running_instance():
    return FindWindowExW(HWND_MESSAGE, None, CONTROL_CLASS, None)


def find_running_instances():
    found, h = [], None
    while True:
        h = FindWindowExW(HWND_MESSAGE, h, CONTROL_CLASS, None)
        if not h:
            return found
        found.append(h)


CreateMutexW = _f(kernel32, "CreateMutexW", wt.HANDLE, wt.LPVOID, wt.BOOL, wt.LPCWSTR)
WaitForSingleObject = _f(kernel32, "WaitForSingleObject", wt.DWORD, wt.HANDLE, wt.DWORD)
WAIT_OBJECT_0, WAIT_ABANDONED = 0, 0x80


def claim_single_instance(timeout_ms):
    """Hold a named mutex for the life of the process, so only one copy can
    draw. Returns the handle, or None if another copy kept it for timeout_ms
    (two copies launched at the same moment: the other one wins)."""
    h = CreateMutexW(None, False, "Local\\AsciiWallpaper.Instance")
    if not h:
        return None
    if WaitForSingleObject(h, timeout_ms) in (WAIT_OBJECT_0, WAIT_ABANDONED):
        return h
    return None


def refresh_wallpaper():
    """Ask Windows to repaint the normal wallpaper (used when we exit)."""
    buf = ctypes.create_unicode_buffer(520)
    SystemParametersInfoW(SPI_GETDESKWALLPAPER, 520, buf, 0)
    SystemParametersInfoW(SPI_SETDESKWALLPAPER, 0, buf, 0)


# --------------------------------------------------------------------------- desktop

def find_desktop_host():
    """Find the window that sits between the wallpaper and the desktop icons.

    Returns dict(mode, parent, defview, workerw). Handles both the classic layout
    (a WorkerW behind the icons) and the Windows 11 24H2+ layout, where the
    WorkerW is a child of Progman and we slot in under SHELLDLL_DefView.
    """
    progman = FindWindowW("Progman", None)
    if not progman:
        return None
    res = ULONG_PTR()
    # 0x052C asks Progman to spawn the WorkerW behind the icons.
    SendMessageTimeoutW(progman, 0x052C, 0xD, 0x1, SMTO_NORMAL, 1000, ctypes.byref(res))
    SendMessageTimeoutW(progman, 0x052C, 0, 0, SMTO_NORMAL, 1000, ctypes.byref(res))

    # Right after logon Explorer may not have built the desktop yet. Returning None
    # makes the caller retry a second later instead of attaching to a half-made one.
    exstyle = GetWindowLongPtrW(progman, GWL_EXSTYLE)
    if exstyle & WS_EX_NOREDIRECTIONBITMAP:
        defview = FindWindowExW(progman, None, "SHELLDLL_DefView", None)
        workerw = FindWindowExW(progman, None, "WorkerW", None)
        if not defview:
            return None
        return {"mode": "raised", "parent": progman, "defview": defview, "workerw": workerw}

    found, icons = [], []

    @WNDENUMPROC
    def cb(h, _):
        dv = FindWindowExW(h, None, "SHELLDLL_DefView", None)
        if dv:
            icons.append(dv)
            w = FindWindowExW(None, h, "WorkerW", None)
            if w:
                found.append(w)
        return True

    EnumWindows(cb, 0)
    if found:
        return {"mode": "legacy", "parent": found[0], "defview": icons[0], "workerw": found[0]}
    if not icons:
        return None
    return {"mode": "progman", "parent": progman, "defview": icons[0], "workerw": None}


def host_alive(host):
    """False once Explorer has replaced any window the surfaces depend on."""
    return all(IsWindow(host[k]) for k in ("parent", "defview", "workerw") if host.get(k))


def below(hwnd, other):
    """True if `other` comes after `hwnd` among its siblings (is drawn under it)."""
    h = GetWindow(hwnd, GW_HWNDNEXT)
    while h:
        if h == other:
            return True
        h = GetWindow(h, GW_HWNDNEXT)
    return False


def list_monitors():
    mons = []

    @MONITORENUMPROC
    def cb(hmon, _hdc, _rect, _lp):
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        GetMonitorInfoW(hmon, ctypes.byref(mi))
        m, w = mi.rcMonitor, mi.rcWork
        mons.append({"hmon": hmon, "rect": (m.left, m.top, m.right, m.bottom),
                     "work": (w.left, w.top, w.right, w.bottom),
                     "device": mi.szDevice, "primary": bool(mi.dwFlags & 1)})
        return True

    EnumDisplayMonitors(None, None, cb, 0)
    return mons


def monitor_labels(mons):
    """Friendly names in left-to-right order: 'Monitor 1 (left, main)', ..."""
    order = sorted(mons, key=lambda m: (m["rect"][0], m["rect"][1]))
    out = []
    for i, m in enumerate(order):
        tags = []
        if len(order) > 1:
            tags.append("left" if i == 0 else "right" if i == len(order) - 1 else "middle")
        if m["primary"]:
            tags.append("main")
        out.append((m["device"], "Monitor %d%s" % (i + 1, " (%s)" % ", ".join(tags) if tags else ""),
                    m["primary"]))
    return out


_SHELL_CLASSES = {"Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd",
                  "XamlExplorerHostIslandWindow", "Windows.UI.Core.CoreWindow"}


def _cloaked(h):
    # hidden UWP/virtual-desktop windows report as visible but are "cloaked"
    v = wt.DWORD()
    if DwmGetWindowAttribute(h, DWMWA_CLOAKED, ctypes.byref(v), ctypes.sizeof(v)):
        return False
    return bool(v.value)


def covered_monitors():
    """hmon values whose desktop is hidden by a maximized or fullscreen window,
    focused or not, on the current virtual desktop."""
    found = set()

    @WNDENUMPROC
    def cb(h, _):
        if not IsWindowVisible(h) or IsIconic(h) or class_name(h) in _SHELL_CLASSES:
            return True
        hmon = MonitorFromWindow(h, MONITOR_DEFAULTTONEAREST)
        if hmon in found:
            return True
        r = wt.RECT()
        GetWindowRect(h, ctypes.byref(r))
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        GetMonitorInfoW(hmon, ctypes.byref(mi))
        m, w = mi.rcMonitor, mi.rcWork
        full = r.left <= m.left and r.top <= m.top and r.right >= m.right and r.bottom >= m.bottom
        work = r.left <= w.left and r.top <= w.top and r.right >= w.right and r.bottom >= w.bottom
        if (full or (IsZoomed(h) and work)) and not _cloaked(h):
            found.add(hmon)
        return True

    EnumWindows(cb, 0)
    return found


def session_locked():
    """True while the lock screen (or a UAC prompt) owns the input desktop."""
    h = OpenInputDesktop(0, False, 0x0100)  # DESKTOP_SWITCHDESKTOP
    if not h:
        return True
    try:
        buf = ctypes.create_unicode_buffer(64)
        need = wt.DWORD()
        GetUserObjectInformationW(h, 2, buf, ctypes.sizeof(buf), ctypes.byref(need))  # UOI_NAME
        return buf.value.lower() != "default"
    finally:
        CloseDesktop(h)


# --------------------------------------------------------------------------- taskbar
#
# Windows 11 draws its taskbar in XAML and ignores the old per-window
# transparency trick, so this sticks to what Windows supports: the taskbar's
# dark/light setting and auto-hide.

_PERSONALIZE = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"


def taskbar_light():
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _PERSONALIZE) as k:
            return bool(winreg.QueryValueEx(k, "SystemUsesLightTheme")[0])
    except OSError:
        return False


def set_taskbar_light(light):
    """Switch the taskbar/Start/notification colours between light and dark."""
    import winreg
    if taskbar_light() == bool(light):
        return
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _PERSONALIZE, 0, winreg.KEY_SET_VALUE) as k:
        winreg.SetValueEx(k, "SystemUsesLightTheme", 0, winreg.REG_DWORD, int(bool(light)))
    _broadcast_setting("ImmersiveColorSet")
    if FindWindowW("Shell_SecondaryTrayWnd", None):
        _rebuild_secondary_taskbars()


def _broadcast_setting(name):
    msg = ctypes.create_unicode_buffer(name)
    res = ULONG_PTR()
    SendMessageTimeoutW(wt.HWND(0xFFFF), 0x001A, 0, ctypes.addressof(msg),   # WM_SETTINGCHANGE
                        0x0002, 1000, ctypes.byref(res))                    # SMTO_ABORTIFHUNG


def _rebuild_secondary_taskbars():
    """Taskbars on other monitors only pick their colours when created, so a
    dark/light switch leaves them stale. Turning "show taskbar on all displays"
    off and on again makes Explorer recreate them (they blink once)."""
    import time
    import winreg
    key = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key, 0,
                        winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE) as k:
        winreg.SetValueEx(k, "MMTaskbarEnabled", 0, winreg.REG_DWORD, 0)
        _broadcast_setting("TraySettings")
        end = time.monotonic() + 2.0
        while FindWindowW("Shell_SecondaryTrayWnd", None) and time.monotonic() < end:
            time.sleep(0.05)
        winreg.SetValueEx(k, "MMTaskbarEnabled", 0, winreg.REG_DWORD, 1)
        _broadcast_setting("TraySettings")


class APPBARDATA(ctypes.Structure):
    _fields_ = [("cbSize", wt.DWORD), ("hWnd", wt.HWND), ("uCallbackMessage", wt.UINT),
                ("uEdge", wt.UINT), ("rc", wt.RECT), ("lParam", wt.LPARAM)]


shell32 = ctypes.WinDLL("shell32")
SHAppBarMessage = _f(shell32, "SHAppBarMessage", ULONG_PTR, wt.DWORD, ctypes.POINTER(APPBARDATA))
ABM_GETSTATE, ABM_SETSTATE, ABS_AUTOHIDE = 4, 10, 1


def taskbar_autohide():
    abd = APPBARDATA(ctypes.sizeof(APPBARDATA))
    abd.hWnd = FindWindowW("Shell_TrayWnd", None)
    return bool(SHAppBarMessage(ABM_GETSTATE, ctypes.byref(abd)) & ABS_AUTOHIDE)


def set_taskbar_autohide(on):
    abd = APPBARDATA(ctypes.sizeof(APPBARDATA))
    abd.hWnd = FindWindowW("Shell_TrayWnd", None)
    abd.lParam = ABS_AUTOHIDE if on else 0
    SHAppBarMessage(ABM_SETSTATE, ctypes.byref(abd))


def efficiency_mode():
    """Ask Windows to run us as a background task: low priority and EcoQoS
    (efficiency cores / low clocks where the CPU has them)."""
    try:
        kernel32.SetPriorityClass(kernel32.GetCurrentProcess(), 0x4000)  # BELOW_NORMAL

        class PPTS(ctypes.Structure):   # PROCESS_POWER_THROTTLING_STATE
            _fields_ = [("Version", wt.ULONG), ("ControlMask", wt.ULONG),
                        ("StateMask", wt.ULONG)]
        st = PPTS(1, 1, 1)  # EXECUTION_SPEED: throttled
        kernel32.SetProcessInformation(kernel32.GetCurrentProcess(), 4,  # ProcessPowerThrottling
                                       ctypes.byref(st), ctypes.sizeof(st))
    except Exception:
        pass


# --------------------------------------------------------------------------- surface

class Surface:
    """One window covering one monitor, rendering a character grid."""

    def __init__(self, monitor, host, font, font_size, bg, preview=False):
        register_classes()
        self.monitor = monitor
        self.host = host
        self.alive = True
        self.on_close = None
        hinst = GetModuleHandleW(None)
        ml, mt, mr, mb = monitor["rect"]

        if preview:
            self.hwnd = CreateWindowExW(0, SURFACE_CLASS, "ascii wallpaper (preview)",
                                        WS_OVERLAPPEDWINDOW | WS_VISIBLE, 80, 80, 1296, 759,
                                        None, None, hinst, None)
            cr = wt.RECT()
            GetClientRect(self.hwnd, ctypes.byref(cr))
            self.w, self.h = cr.right, cr.bottom
            gx, gy, gw, gh = 0, 0, self.w, self.h
        else:
            self.w, self.h = mr - ml, mb - mt
            pt = wt.POINT(ml, mt)
            ScreenToClient(host["parent"], ctypes.byref(pt))
            ex = WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
            if host["mode"] == "raised":
                ex |= WS_EX_LAYERED
            self.hwnd = CreateWindowExW(ex, SURFACE_CLASS, "ascii wallpaper",
                                        WS_CHILD | WS_VISIBLE | WS_CLIPSIBLINGS,
                                        pt.x, pt.y, self.w, self.h,
                                        host["parent"], None, hinst, None)
            if host["mode"] == "raised":
                SetLayeredWindowAttributes(self.hwnd, 0, 255, LWA_ALPHA)
                flags = SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE
                if host["defview"]:
                    SetWindowPos(self.hwnd, host["defview"], 0, 0, 0, 0, flags)
                if host["workerw"]:
                    # the WorkerW paints the static wallpaper: keep it under every surface
                    SetWindowPos(host["workerw"], wt.HWND(1), 0, 0, 0, 0, flags)  # HWND_BOTTOM
            wl, wt_, wr, wb = monitor["work"]
            gx, gy, gw, gh = wl - ml, wt_ - mt, wr - wl, wb - wt_

        if not self.hwnd:
            raise OSError("CreateWindowExW failed: %d" % ctypes.get_last_error())
        _handlers[self.hwnd] = self

        dpi = GetDpiForWindow(self.hwnd) or 96
        px = max(6, round(font_size * dpi / 96))
        wdc = GetDC(self.hwnd)
        self.memdc = CreateCompatibleDC(wdc)
        self.bmp = CreateCompatibleBitmap(wdc, self.w, self.h)
        ReleaseDC(self.hwnd, wdc)
        self.old_bmp = SelectObject(self.memdc, self.bmp)
        # quality 4 = ANTIALIASED (grayscale); ClearType gives coloured fringes on dark bg
        self.font = CreateFontW(-px, 0, 0, 0, 400, 0, 0, 0, 1, 0, 0, 4, 0x31, font)
        self.old_font = SelectObject(self.memdc, self.font)
        SetBkMode(self.memdc, TRANSPARENT)
        sz = wt.SIZE()
        GetTextExtentPoint32W(self.memdc, "M" * 10, 10, ctypes.byref(sz))
        self.cw, self.ch = max(1, sz.cx // 10), max(1, sz.cy)
        self.cols, self.rows = max(1, gw // self.cw), max(1, gh // self.ch)
        self.ox = gx + (gw - self.cols * self.cw) // 2
        self.oy = gy + (gh - self.rows * self.ch) // 2
        self.aspect = self.ch / self.cw
        self.rect = wt.RECT(0, 0, self.w, self.h)
        self.bg_hex = None
        self.brush = None
        self.prev = None                # last frame drawn, for row diffing
        self.set_bg(bg)

    def set_bg(self, bg_hex):
        if bg_hex == self.bg_hex:
            return
        if self.brush:
            DeleteObject(self.brush)
        self.bg_hex = bg_hex
        self.brush = CreateSolidBrush(rgb(bg_hex))

    def on_message(self, hwnd, msg, wp, lp):
        if msg == WM_ERASEBKGND:
            return 1
        if msg == WM_NCHITTEST:
            return HTTRANSPARENT
        if msg == WM_PAINT:
            ps = PAINTSTRUCT()
            hdc = BeginPaint(hwnd, ctypes.byref(ps))
            BitBlt(hdc, 0, 0, self.w, self.h, self.memdc, 0, 0, SRCCOPY)
            EndPaint(hwnd, ctypes.byref(ps))
            return 0
        if msg == WM_CLOSE:
            if self.on_close:
                self.on_close()
            return 0
        if msg == WM_DESTROY:
            self.alive = False
            _handlers.pop(hwnd, None)
            return 0
        return None

    def draw(self, char_rows, level_rows, colors):
        """Render a frame. Only rows that differ from the last frame are redrawn,
        and only the band of screen they cover is copied; most scenes leave
        most rows untouched from one frame to the next."""
        dc = self.memdc
        key = (self.bg_hex, tuple(sorted(colors.items())))
        prev = self.prev
        if prev is None or prev[0] != key or len(prev[1]) != len(char_rows):
            FillRect(dc, ctypes.byref(self.rect), self.brush)
            old_c = old_l = None
        else:
            old_c, old_l = prev[1], prev[2]
        ox, cw, ch = self.ox, self.cw, self.ch
        current = None
        top = bottom = None
        row = wt.RECT(0, 0, self.w, 0)
        for i, (cs, ls) in enumerate(zip(char_rows, level_rows)):
            if old_c is not None and cs == old_c[i] and ls == old_l[i]:
                continue
            y = self.oy + i * ch
            if top is None:
                top = y
            bottom = y + ch
            if old_c is not None:
                row.top, row.bottom = y, y + ch
                FillRect(dc, ctypes.byref(row), self.brush)
            for m in _RUNS.finditer(ls):
                s, e = m.span()
                col = colors[m.group(1)]
                if col != current:
                    SetTextColor(dc, col)
                    current = col
                TextOutW(dc, ox + s * cw, y, cs[s:e], e - s)
        self.prev = (key, list(char_rows), list(level_rows))
        if old_c is None:
            top, bottom = 0, self.h
        if top is None:
            return                      # nothing changed: no copy at all
        hdc = GetDC(self.hwnd)
        BitBlt(hdc, 0, top, self.w, bottom - top, dc, 0, top, SRCCOPY)
        ReleaseDC(self.hwnd, hdc)

    def is_valid(self):
        if not (self.alive and IsWindow(self.hwnd)):
            return False
        host = self.host
        if not host:
            return True
        if not host_alive(host):
            return False
        # When a monitor wakes up, Explorer can move/resize its desktop window
        # after we attached, dragging our child windows off their monitor.
        r = wt.RECT()
        GetWindowRect(self.hwnd, ctypes.byref(r))
        if (r.left, r.top, r.right, r.bottom) != tuple(self.monitor["rect"]):
            return False
        # Explorer sometimes re-stacks its windows while the session is still
        # starting; if the wallpaper WorkerW ends up above us we are hidden.
        if host["mode"] == "raised" and host["workerw"]:
            return below(self.hwnd, host["workerw"])
        return True

    def destroy(self):
        if self.memdc:
            SelectObject(self.memdc, self.old_font)
            SelectObject(self.memdc, self.old_bmp)
            DeleteObject(self.font)
            DeleteObject(self.bmp)
            DeleteDC(self.memdc)
            self.memdc = None
        if self.brush:
            DeleteObject(self.brush)
            self.brush = None
        if self.alive and IsWindow(self.hwnd):
            DestroyWindow(self.hwnd)
        _handlers.pop(self.hwnd, None)
        self.alive = False


# --------------------------------------------------------------------------- tray icon

shell32 = ctypes.WinDLL("shell32", use_last_error=True)


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [("cbSize", wt.DWORD), ("hWnd", wt.HWND), ("uID", wt.UINT),
                ("uFlags", wt.UINT), ("uCallbackMessage", wt.UINT), ("hIcon", wt.HICON),
                ("szTip", wt.WCHAR * 128), ("dwState", wt.DWORD), ("dwStateMask", wt.DWORD),
                ("szInfo", wt.WCHAR * 256), ("uVersion", wt.UINT),
                ("szInfoTitle", wt.WCHAR * 64), ("dwInfoFlags", wt.DWORD),
                ("guidItem", ctypes.c_byte * 16), ("hBalloonIcon", wt.HICON)]


class ICONINFO(ctypes.Structure):
    _fields_ = [("fIcon", wt.BOOL), ("xHotspot", wt.DWORD), ("yHotspot", wt.DWORD),
                ("hbmMask", wt.HBITMAP), ("hbmColor", wt.HBITMAP)]


Shell_NotifyIconW = _f(shell32, "Shell_NotifyIconW", wt.BOOL, wt.DWORD,
                       ctypes.POINTER(NOTIFYICONDATAW))
CreatePopupMenu = _f(user32, "CreatePopupMenu", wt.HMENU)
AppendMenuW = _f(user32, "AppendMenuW", wt.BOOL, wt.HMENU, wt.UINT, ULONG_PTR, wt.LPCWSTR)
TrackPopupMenu = _f(user32, "TrackPopupMenu", _I, wt.HMENU, wt.UINT, _I, _I, _I, wt.HWND,
                    wt.LPVOID)
DestroyMenu = _f(user32, "DestroyMenu", wt.BOOL, wt.HMENU)
GetCursorPos = _f(user32, "GetCursorPos", wt.BOOL, ctypes.POINTER(wt.POINT))
SetForegroundWindow = _f(user32, "SetForegroundWindow", wt.BOOL, wt.HWND)
RegisterWindowMessageW = _f(user32, "RegisterWindowMessageW", wt.UINT, wt.LPCWSTR)
GetSystemMetrics = _f(user32, "GetSystemMetrics", _I, _I)
CreateIconIndirect = _f(user32, "CreateIconIndirect", wt.HICON, ctypes.POINTER(ICONINFO))
DestroyIcon = _f(user32, "DestroyIcon", wt.BOOL, wt.HICON)
CreateBitmap = _f(gdi32, "CreateBitmap", wt.HBITMAP, _I, _I, wt.UINT, wt.UINT, wt.LPVOID)

NIM_ADD, NIM_MODIFY, NIM_DELETE = 0, 1, 2
NIF_MESSAGE, NIF_ICON, NIF_TIP = 1, 2, 4
WM_APP, WM_NULL = 0x8000, 0
WM_TRAY = WM_APP + 1
WM_LBUTTONUP, WM_RBUTTONUP = 0x0202, 0x0205
WS_POPUP = 0x80000000
MF_STRING, MF_GRAYED, MF_CHECKED, MF_POPUP, MF_SEPARATOR = 0, 1, 8, 0x10, 0x800
MFT_RADIOCHECK = 0x200
TPM_RIGHTBUTTON, TPM_BOTTOMALIGN, TPM_NONOTIFY, TPM_RETURNCMD = 0x2, 0x20, 0x80, 0x100
SM_CXSMICON = 49


def make_icon(bg_hex, fg_hex, glyph="~"):
    """Draw a tiny square icon with one character on it."""
    s = max(16, GetSystemMetrics(SM_CXSMICON))
    sdc = GetDC(None)
    dc = CreateCompatibleDC(sdc)
    color = CreateCompatibleBitmap(sdc, s, s)
    ReleaseDC(None, sdc)
    old_bmp = SelectObject(dc, color)
    brush = CreateSolidBrush(rgb(bg_hex))
    FillRect(dc, ctypes.byref(wt.RECT(0, 0, s, s)), brush)
    DeleteObject(brush)
    font = CreateFontW(-int(s * 1.25), 0, 0, 0, 700, 0, 0, 0, 1, 0, 0, 4, 0x31, "Consolas")
    old_font = SelectObject(dc, font)
    SetBkMode(dc, TRANSPARENT)
    SetTextColor(dc, rgb(fg_hex))
    sz = wt.SIZE()
    GetTextExtentPoint32W(dc, glyph, len(glyph), ctypes.byref(sz))
    TextOutW(dc, (s - sz.cx) // 2, (s - sz.cy) // 2, glyph, len(glyph))
    SelectObject(dc, old_font)
    SelectObject(dc, old_bmp)
    DeleteObject(font)
    DeleteDC(dc)
    bits = (ctypes.c_byte * (((s + 15) // 16) * 2 * s))()   # all-zero mask = fully opaque
    mask = CreateBitmap(s, s, 1, 1, bits)
    ii = ICONINFO(True, 0, 0, mask, color)
    hicon = CreateIconIndirect(ctypes.byref(ii))
    DeleteObject(mask)
    DeleteObject(color)
    return hicon


def _build_menu(spec):
    """spec items: None = separator, (text, [subitems]) = submenu,
    (text, cmd_id, checked, enabled, radio) = item (trailing fields optional)."""
    h = CreatePopupMenu()
    for it in spec:
        if it is None:
            AppendMenuW(h, MF_SEPARATOR, 0, None)
        elif isinstance(it[1], list):
            AppendMenuW(h, MF_POPUP, _build_menu(it[1]), it[0])
        else:
            text, cmd, checked, enabled, radio = (tuple(it) + (False, True, False))[:5]
            flags = MF_STRING
            if checked:
                flags |= MF_CHECKED
            if not enabled:
                flags |= MF_GRAYED
            if radio:
                flags |= MFT_RADIOCHECK
            AppendMenuW(h, flags, cmd, text)
    return h


class Tray:
    """Notification-area icon. Clicking it calls on_click()."""

    def __init__(self, icon, tip, on_click):
        register_classes()
        self.on_click = on_click
        self.icon = icon
        self.tip = tip
        self.hwnd = CreateWindowExW(WS_EX_TOOLWINDOW, TRAY_CLASS, "ascii-wallpaper-tray",
                                    WS_POPUP, 0, 0, 0, 0, None, None,
                                    GetModuleHandleW(None), None)
        _handlers[self.hwnd] = self
        self.taskbar_created = RegisterWindowMessageW("TaskbarCreated")
        self._notify(NIM_ADD)

    def _notify(self, op):
        nid = NOTIFYICONDATAW()
        nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        nid.hWnd = self.hwnd
        nid.uID = 1
        nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        nid.uCallbackMessage = WM_TRAY
        nid.hIcon = self.icon
        nid.szTip = self.tip[:127]
        Shell_NotifyIconW(op, ctypes.byref(nid))

    def update(self, icon=None, tip=None):
        if icon is not None:
            self.icon = icon
        if tip is not None:
            self.tip = tip
        self._notify(NIM_MODIFY)

    def popup(self, spec):
        """Show a menu at the cursor; returns the chosen command id (0 if none)."""
        h = _build_menu(spec)
        pt = wt.POINT()
        GetCursorPos(ctypes.byref(pt))
        SetForegroundWindow(self.hwnd)
        cmd = TrackPopupMenu(h, TPM_RETURNCMD | TPM_RIGHTBUTTON | TPM_BOTTOMALIGN | TPM_NONOTIFY,
                             pt.x, pt.y, 0, self.hwnd, None)
        PostMessageW(self.hwnd, WM_NULL, 0, 0)
        DestroyMenu(h)
        return cmd

    def on_message(self, hwnd, msg, wp, lp):
        if msg == WM_TRAY:
            if (lp & 0xFFFF) in (WM_LBUTTONUP, WM_RBUTTONUP):
                self.on_click()
            return 0
        if msg == self.taskbar_created:   # Explorer restarted: put the icon back
            self._notify(NIM_ADD)
            return 0
        return None

    def remove(self):
        self._notify(NIM_DELETE)
        DestroyWindow(self.hwnd)
        _handlers.pop(self.hwnd, None)
