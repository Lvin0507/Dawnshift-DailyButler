"""Windows plumbing and settings knowledge shared by the app: elevated runs, the Task Scheduler
task, launcher-button calibration, and what each game needs to be set up."""

import ctypes
import datetime
import os
import re
import subprocess
import sys
from ctypes import wintypes
from xml.sax.saxutils import escape

import psutil

from .config import app_dir
from .games import GAMES_BY_ID
from .i18n import game_name

SHORT_NAMES = {
    "en": {"endfield": "Endfield", "arknights": "Arknights", "wuthering": "Wuthering Waves",
           "bluearchive": "Blue Archive", "zzz": "ZZZ"},
    "zh": {"endfield": "终末地", "arknights": "明日方舟", "wuthering": "鸣潮",
           "bluearchive": "蔚蓝档案", "zzz": "绝区零"},
}
# ZZZ settings that only matter for the Steam client
STEAM_ONLY = {"steam_appid", "launcher_exe", "start_button"}

DAY_KEYS_EN = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
DAY_KEYS_ZH = ["一", "二", "三", "四", "五", "六", "日"]

TOOLS = {
    "endfield": ("MaaEnd", "https://github.com/MaaXYZ/MaaEnd"),
    "arknights": ("MAA", "https://github.com/MaaAssistantArknights/MaaAssistantArknights"),
    "wuthering": ("ok-ww", "https://github.com/ok-oldking/ok-wuthering-waves"),
    "bluearchive": ("BAAS", "https://github.com/pur1fying/blue_archive_auto_script"),
    "zzz": ("OneDragon", "https://github.com/OneDragon-Anything/ZenlessZoneZero-OneDragon"),
}

# Per-game form: (config key, kind, extra). Kinds: exe, file, dir, text, bool, choice, point
FIELDS = {
    "endfield": [("maaend_path", "exe", None), ("log_dir", "dir", None)],
    "arknights": [("maa_path", "exe", None), ("maa_log", "file", None), ("game_exe", "text", None)],
    "wuthering": [("okww_path", "exe", None), ("log_path", "file", None),
                  ("steam_client", "bool", None), ("task", "text", None)],
    "bluearchive": [("launcher_path", "exe", None), ("baas_dir", "dir", None),
                    ("baas_exe", "exe", None), ("start_button", "point", None),
                    ("wait_for_reset", "bool", None)],
    "zzz": [("client", "choice", ["official", "steam"]), ("server", "choice", ["asia", "america", "europe"]),
            ("od_dir", "dir", None), ("steam_appid", "text", None), ("launcher_exe", "text", None),
            ("start_button", "point", None), ("wait_for_reset", "bool", None)],
}
PATH_KINDS = ("exe", "file", "dir")


def plain_name(gid, lang):
    """Game name without the report's emoji, for the app's lists and headings."""
    name = game_name(gid, lang)
    return name.split(" ", 1)[1] if " " in name and not name[0].isalnum() else name


def parse_point(text):
    """'0.85, 0.86' -> [0.85, 0.86], or None if it isn't two fractions."""
    try:
        x, y = (float(part) for part in text.replace("，", ",").split(","))
    except ValueError:
        return None
    return [x, y] if 0 <= x <= 1 and 0 <= y <= 1 else None


def missing_items(gid, game_cfg):
    """Settings an enabled game still needs: empty required keys and paths that don't exist."""
    missing = list(GAMES_BY_ID[gid](game_cfg).missing_settings())
    for key, kind, _ in FIELDS[gid]:
        value = game_cfg.get(key)
        if kind in PATH_KINDS and value and not os.path.exists(value) and key not in missing:
            missing.append(key)
    return missing


# ---------- Windows helpers for the test run and calibration ----------
class SHELLEXECUTEINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("fMask", ctypes.c_ulong), ("hwnd", wintypes.HWND),
                ("lpVerb", wintypes.LPCWSTR), ("lpFile", wintypes.LPCWSTR),
                ("lpParameters", wintypes.LPCWSTR), ("lpDirectory", wintypes.LPCWSTR),
                ("nShow", ctypes.c_int), ("hInstApp", wintypes.HINSTANCE), ("lpIDList", ctypes.c_void_p),
                ("lpClass", wintypes.LPCWSTR), ("hkeyClass", wintypes.HKEY), ("dwHotKey", wintypes.DWORD),
                ("hIconOrMonitor", wintypes.HANDLE), ("hProcess", wintypes.HANDLE)]


def start_elevated(args, program=None, show=7):
    """Start a program (default: this Python) with admin rights, after one UAC prompt, and return
    the process handle, or None if the user declined. The games need admin rights; the app doesn't.
    show=7 keeps its console minimised; show=0 hides it."""
    info = SHELLEXECUTEINFO()
    info.cbSize = ctypes.sizeof(info)
    info.fMask = 0x40                 # SEE_MASK_NOCLOSEPROCESS: give us the process handle
    info.lpVerb = "runas"
    info.lpFile = program or sys.executable
    info.lpParameters = args
    info.lpDirectory = str(app_dir())
    info.nShow = show
    if not ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(info)):
        return None
    return info.hProcess


def process_finished(handle):
    return ctypes.windll.kernel32.WaitForSingleObject(handle, 0) != 0x102  # WAIT_TIMEOUT


def window_under_cursor():
    """(exe name, x fraction, y fraction) of the top-level window under the mouse."""
    user32 = ctypes.windll.user32
    user32.WindowFromPoint.argtypes = [wintypes.POINT]
    user32.WindowFromPoint.restype = wintypes.HWND
    user32.GetAncestor.restype = wintypes.HWND
    cursor = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(cursor))
    hwnd = user32.GetAncestor(user32.WindowFromPoint(cursor), 2)  # GA_ROOT
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    try:
        exe = psutil.Process(pid.value).name()
    except psutil.Error:
        exe = "?"
    rect = wintypes.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(rect))
    local = wintypes.POINT(cursor.x, cursor.y)
    user32.ScreenToClient(hwnd, ctypes.byref(local))
    if rect.right <= 0 or rect.bottom <= 0:
        return exe, None, None
    return exe, round(local.x / rect.right, 3), round(local.y / rect.bottom, 3)


def launcher_of(gid, game_cfg):
    """The launcher process the start button belongs to."""
    if gid == "bluearchive":
        return os.path.basename(game_cfg.get("launcher_path") or "") or "launcher"
    return game_cfg.get("launcher_exe") or "launcher"


TASK_NAME = "Gachashift"


def task_xml(hour, minute):
    """A Task Scheduler task: daily at hh:mm, highest privileges, wakes the PC, needs a
    logged-on user (the games need a real desktop), and never starts late after a missed time,
    so turning the PC on at noon doesn't suddenly take over the mouse."""
    start = f"{datetime.date.today():%Y-%m-%d}T{hour:02d}:{minute:02d}:00"
    user = f"{os.environ.get('USERDOMAIN', '')}\\{os.environ.get('USERNAME', '')}"
    return f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo><Description>Gachashift morning run</Description></RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>{start}</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay><DaysInterval>1</DaysInterval></ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>{escape(user)}</UserId>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <StartWhenAvailable>false</StartWhenAvailable>
    <WakeToRun>true</WakeToRun>
    <ExecutionTimeLimit>PT6H</ExecutionTimeLimit>
    <Enabled>true</Enabled>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{escape(sys.executable)}</Command>
      <Arguments>-m gachashift</Arguments>
      <WorkingDirectory>{escape(str(app_dir()))}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"""


def run_schtasks_elevated(args, timeout_ms=20000):
    """Run schtasks.exe with admin rights and return True if it succeeded."""
    handle = start_elevated(args, program="schtasks.exe", show=0)
    if not handle:
        return False
    kernel32 = ctypes.windll.kernel32
    kernel32.WaitForSingleObject(handle, timeout_ms)
    code = wintypes.DWORD()
    kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
    kernel32.CloseHandle(handle)
    return code.value == 0


def scheduled_time():
    """'HH:MM' of the existing Gachashift task, or None if there isn't one."""
    try:
        result = subprocess.run(["schtasks", "/query", "/tn", TASK_NAME, "/xml"], capture_output=True,
                                text=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), timeout=15)
    except (OSError, subprocess.SubprocessError):
        return None
    match = re.search(r"<StartBoundary>[^T]*T(\d{2}:\d{2})", result.stdout or "")
    return match.group(1) if result.returncode == 0 and match else None


