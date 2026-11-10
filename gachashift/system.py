"""Windows helpers shared by every game: processes, logs, windows, real-mouse clicks,
and the quiet mode (mute + dim) used while a run is in progress."""

import ctypes
import datetime
import os
import subprocess
import time
from ctypes import wintypes

import psutil

from .config import app_dir


def ts():
    return datetime.datetime.now().strftime("%H:%M:%S")


# ---------- stopping a run ----------
class StopRequested(Exception):
    """Raised inside a run when the user asked Gachashift to stop."""


def stop_file():
    """Creating this file (from the App or the Stop shortcut) asks a running Gachashift to stop."""
    return app_dir() / "stop.request"


def stop_requested():
    return stop_file().exists()


def clear_stop():
    try:
        stop_file().unlink()
    except FileNotFoundError:
        pass


def pause(seconds):
    """Sleep, but give up at once with StopRequested if the user asked to stop. Every wait in a
    run goes through here, so a stop takes effect within a second wherever the run is."""
    end = time.time() + seconds
    while True:
        if stop_requested():
            raise StopRequested()
        left = end - time.time()
        if left <= 0:
            return
        time.sleep(min(1.0, left))


def seconds_since_input():
    """How long ago the keyboard or mouse was last used in this session."""
    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]

    info = LASTINPUTINFO()
    info.cbSize = ctypes.sizeof(info)
    ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info))
    return (ctypes.windll.kernel32.GetTickCount() - info.dwTime) / 1000


# ---------- processes ----------
def process_running(exe_name):
    """Exact name check via psutil (tasklist truncates long names)."""
    exe_name = exe_name.lower()
    return any((p.info.get("name") or "").lower() == exe_name for p in psutil.process_iter(["name"]))


def kill(exe_names):
    for name in exe_names:
        if name:
            subprocess.run(["taskkill", "/F", "/IM", name],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def processes_in(folder):
    """Processes whose executable lives inside `folder` (e.g. a tool's bundled python).
    Matching on the path keeps us from touching our own python.exe or anyone else's."""
    root = os.path.normcase(os.path.abspath(folder)) + os.sep
    found = []
    for p in psutil.process_iter(["exe", "name"]):
        exe = p.info.get("exe")
        if exe and os.path.normcase(exe).startswith(root):
            found.append(p)
    return found


def kill_processes(procs):
    for p in procs:
        try:
            p.kill()
        except psutil.Error:
            pass


# ---------- logs ----------
def log_size(path):
    return os.path.getsize(path) if path and os.path.exists(path) else 0


def read_since(path, offset):
    """Everything written to `path` after byte `offset` (handles truncation/rotation)."""
    if not path or not os.path.exists(path):
        return ""
    if os.path.getsize(path) < offset:
        offset = 0
    with open(path, "rb") as f:
        f.seek(offset)
        return f.read().decode("utf-8", errors="ignore")


# ---------- windows and clicks ----------
def _user32():
    user32 = ctypes.windll.user32
    user32.GetForegroundWindow.restype = wintypes.HWND
    return user32


def make_dpi_aware():
    """Use real pixel coordinates even with 125%/150% display scaling."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def main_window_of(exe_name):
    """The largest visible top-level window owned by a process with this exe name, or None."""
    user32 = _user32()
    pids = {p.pid for p in psutil.process_iter(["name"])
            if (p.info.get("name") or "").lower() == exe_name.lower()}
    best, best_area = None, 0
    enum_proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def callback(hwnd, _):
        nonlocal best, best_area
        if user32.IsWindowVisible(hwnd):
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value in pids:
                rect = wintypes.RECT()
                user32.GetClientRect(hwnd, ctypes.byref(rect))
                if rect.right * rect.bottom > best_area:
                    best, best_area = hwnd, rect.right * rect.bottom
        return True

    user32.EnumWindows(enum_proc(callback), 0)
    return best


def click_in_window(hwnd, fx, fy):
    """Bring the window to the front and click with the real mouse at a fraction of its client
    area. Skips the click if the window won't come to the front, so a click never lands on
    some other window that happens to be on top. Returns True if it clicked."""
    user32 = _user32()
    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.5)
    if user32.GetForegroundWindow() != hwnd:
        # Windows sometimes refuses focus changes; minimizing and restoring usually works
        user32.ShowWindow(hwnd, 6)  # SW_MINIMIZE
        time.sleep(0.3)
        user32.ShowWindow(hwnd, 9)
        user32.SetForegroundWindow(hwnd)
        time.sleep(0.5)
    if user32.GetForegroundWindow() != hwnd:
        print(f"[{ts()}] launcher window is not in front; not clicking this time")
        return False
    rect = wintypes.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(rect))
    point = wintypes.POINT(int(rect.right * fx), int(rect.bottom * fy))
    user32.ClientToScreen(hwnd, ctypes.byref(point))
    user32.SetCursorPos(point.x, point.y)
    time.sleep(0.1)
    user32.mouse_event(0x0002, 0, 0, 0, 0)  # left down
    time.sleep(0.05)
    user32.mouse_event(0x0004, 0, 0, 0, 0)  # left up
    return True


def launch_and_click(open_launcher, launcher_exe, button, game_exe, wait_after=30, timeout=600):
    """Open a game launcher, then keep clicking its start button until the game process appears.
    Clicking repeats because the launcher may still be checking for updates at first."""
    make_dpi_aware()
    open_launcher()
    start = time.time()
    while time.time() - start < timeout:
        pause(10)
        if process_running(game_exe):
            print(f"[{ts()}] game started, waiting for it to load...")
            pause(wait_after)
            return True
        hwnd = main_window_of(launcher_exe)
        if hwnd:
            print(f"[{ts()}] clicking the start button in {launcher_exe}")
            click_in_window(hwnd, *button)
    return False


def wait_for_reset(utc_offset_hours, reset_hour=4, margin_minutes=5, max_wait_hours=2, on_wait=None):
    """Wait until just after a server's daily reset (if it is due within max_wait_hours),
    so the run counts for today rather than yesterday. Returns the minutes waited."""
    tz = datetime.timezone(datetime.timedelta(hours=utc_offset_hours))
    now = datetime.datetime.now(tz)
    reset = now.replace(hour=reset_hour, minute=margin_minutes, second=0, microsecond=0)
    wait = (reset - now).total_seconds()
    if 0 < wait <= max_wait_hours * 3600:
        if on_wait:
            on_wait(round(wait / 60))
        pause(wait)
        return round(wait / 60)
    return 0


# ---------- screen gamma ----------
class _DISPLAY_DEVICE(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("DeviceName", wintypes.WCHAR * 32),
                ("DeviceString", wintypes.WCHAR * 128), ("StateFlags", wintypes.DWORD),
                ("DeviceID", wintypes.WCHAR * 128), ("DeviceKey", wintypes.WCHAR * 128)]


_RAMP = wintypes.WORD * 768  # 256 steps each for red, green and blue


def gamma_marker():
    """Present while the screens are darkened, so a run that died can be cleaned up later."""
    return app_dir() / "gamma.dim"


def _displays():
    names, i = [], 0
    while True:
        device = _DISPLAY_DEVICE()
        device.cb = ctypes.sizeof(device)
        if not ctypes.windll.user32.EnumDisplayDevicesW(None, i, ctypes.byref(device), 0):
            return names
        if device.StateFlags & 1:  # attached to the desktop
            names.append(device.DeviceName)
        i += 1


def _set_ramp(name, ramp):
    gdi32 = ctypes.windll.gdi32
    hdc = gdi32.CreateDCW("DISPLAY", name, None, None)
    try:
        return bool(gdi32.SetDeviceGammaRamp(hdc, ctypes.byref(ramp)))
    finally:
        gdi32.DeleteDC(hdc)


def _linear_ramp(level):
    ramp = _RAMP()
    for channel in range(3):
        for i in range(256):
            ramp[channel * 256 + i] = min(65535, int(i * 257 * level))
    return ramp


def dim_gamma(level=0.05):
    """Darken every display by lowering its gamma ramp to `level` (0-1). Only the light the
    monitor gives off changes: screenshots and screen capture still see the normal picture, so
    the tools keep working. Windows refuses very dark ramps unless GdiIcmGammaRange allows them,
    so this steps up from `level` until each display accepts. Returns the level reached, or None."""
    steps = [level] + [s / 100 for s in range(10, 101, 5) if s / 100 > level]
    accepted = None
    for name in _displays():
        for step in steps:
            if _set_ramp(name, _linear_ramp(step)):
                accepted = max(accepted or 0, step)
                break
    if accepted is not None:
        gamma_marker().touch()
    return accepted


def restore_gamma():
    """Put every display back to the normal, linear gamma ramp."""
    for name in _displays():
        _set_ramp(name, _linear_ramp(1.0))
    try:
        gamma_marker().unlink()
    except FileNotFoundError:
        pass


# ---------- quiet mode ----------
class QuietMode:
    """Mute the speakers and/or dim the screens for the duration of a run, then restore
    exactly what was there before. Each part fails soft: a missing library or an external
    monitor without DDC/CI just means that part is skipped."""

    def __init__(self, mute=True, dim=False, dim_level=0.3):
        self.mute, self.dim, self.dim_level = mute, dim, dim_level
        self._volume = self._was_muted = None
        self._brightness = None
        self._gamma = False

    def __enter__(self):
        if self.mute:
            try:
                from ctypes import POINTER, cast
                from comtypes import CLSCTX_ALL
                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                speakers = AudioUtilities.GetSpeakers()
                # newer pycaw exposes the volume control directly; older versions need Activate()
                volume = getattr(speakers, "EndpointVolume", None)
                if volume is None:
                    interface = speakers.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                    volume = cast(interface, POINTER(IAudioEndpointVolume))
                self._volume = volume
                self._was_muted = self._volume.GetMute()
                self._volume.SetMute(1, None)
            except Exception as e:
                print(f"mute skipped: {e}")
        if self.dim:
            # hardware brightness works on laptops and DDC/CI monitors; gamma works almost
            # everywhere else, so use both
            try:
                import screen_brightness_control as sbc
                self._brightness = sbc.get_brightness()
                sbc.set_brightness(int(self.dim_level * 100))
            except Exception as e:
                print(f"brightness not changed (monitor may not support it): {e}")
            try:
                level = dim_gamma(self.dim_level)
                self._gamma = level is not None
                print(f"screen darkened to {int(level * 100)}%" if self._gamma
                      else "screen gamma not changed (the display refused it)")
            except Exception as e:
                print(f"gamma not changed: {e}")
        return self

    def __exit__(self, *exc):
        if self._volume is not None:
            try:
                self._volume.SetMute(self._was_muted, None)
            except Exception:
                pass
        if self._gamma:
            try:
                restore_gamma()
            except Exception:
                pass
        if self._brightness is not None:
            try:
                import screen_brightness_control as sbc
                for index, level in enumerate(self._brightness):
                    sbc.set_brightness(level, display=index)
            except Exception:
                pass
        return False


def shutdown(delay=5):
    time.sleep(delay)
    subprocess.run(["shutdown", "/s", "/t", "0"])


# ---------- Steam ----------
def restart_steam_if_running():
    """A Steam that is already running without admin rights makes admin-only games ask for
    elevation (a UAC prompt no script can click). Close it gracefully so that our elevated
    process starts Steam again and everything it launches inherits admin rights."""
    if not process_running("steam.exe"):
        return
    print(f"[{ts()}] Steam is already running; restarting it with admin rights")
    os.startfile("steam://exit")  # graceful exit
    for _ in range(30):
        pause(2)
        if not process_running("steam.exe"):
            return
    kill(["steam.exe"])
    pause(3)


def start_steam_elevated(wait=45):
    """Make sure Steam is running with our admin rights and signed in before a tool
    launches a Steam game directly (Steam's DRM hands the launch back to Steam)."""
    restart_steam_if_running()
    os.startfile("steam://open/main")
    pause(wait)


# ---------- lock screen ----------
def session_locked():
    """True while the lock or sign-in screen is up. Screen capture and real-mouse clicks don't
    work there, so no tool can do anything until someone signs in."""
    return process_running("LogonUI.exe")


def wait_for_unlock(max_wait=120):
    """Give Windows a moment in case it is just waking up; return False if it is still on the
    lock screen after that."""
    waited = 0
    while session_locked() and waited < max_wait:
        pause(10)
        waited += 10
    return not session_locked()
