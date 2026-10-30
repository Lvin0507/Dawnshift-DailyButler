"""
pagent.py - Dawnshift, full-Python version (no LLM).

Runs Arknights: Endfield (MaaEnd), Arknights (MAA, PC client), Wuthering Waves (ok-ww)
and Blue Archive JP (BAAS, PC client),
parses each tool's log deterministically, sends a Telegram report, then shuts the PC down.

Usage:
    python pagent.py                     # normal morning run
    python pagent.py --no-shutdown       # full run, but keep the PC on afterwards
    python pagent.py --dry-run           # launch nothing; parse the current MaaEnd log and print the report
    python pagent.py --dry-run --endfield-log logs\\go-service_2026-10-29_0712.log
    python pagent.py --only bluearchive  # run one game only; print the report, no Telegram, no shutdown
"""

import argparse
import ctypes
import datetime
import glob
import html
import json
import os
import re
import shutil
import subprocess
import time
import winreg
from ctypes import wintypes
from pathlib import Path

import psutil
import requests
from dotenv import load_dotenv

# ==========================================
# 1. Config - secrets and local paths come from .env (same file as agent.py)
# ==========================================
# Load .env from this script's folder (Task Scheduler may start us from another working dir)
load_dotenv(Path(__file__).with_name(".env"))


def require_env(name):
    """Fail fast with a clear message if a required setting is missing from .env."""
    value = os.getenv(name)
    if not value:
        raise SystemExit(f"Missing required setting in .env: {name}")
    return value


# Switch files (create the file to turn that game OFF)
WW_SWITCH_FILE = require_env("WW_SWITCH_FILE")
ARK_SWITCH_FILE = require_env("ARK_SWITCH_FILE")

# Endfield (MaaEnd) - MaaEnd's "Launch Game (PC)" task starts the game itself
MAA_END_PATH = require_env("MAA_END_PATH")
MAA_LOG_DIR = require_env("MAA_LOG_DIR")

# Wuthering Waves (ok-ww)
OK_WW_PATH = require_env("OK_WW_PATH")
WW_LOG_PATH = require_env("WW_LOG_PATH")

# Arknights (MAA, PC client) - MAA starts the game itself
MAA_ARK_PATH = require_env("MAA_ARK_PATH")
MAA_ARK_LOG = require_env("MAA_ARK_LOG")
MAA_DONE_MARKERS = ["任务已全部完成"]
ARK_GAME_EXE = "Arknights.exe"

# Blue Archive JP (BAAS, PC client) - BAAS starts the game and exits by itself when done
BA_SWITCH_FILE = require_env("BA_SWITCH_FILE")
BAAS_DIR = require_env("BAAS_DIR")
# The BAAS launcher; set BAAS_EXE in .env if yours has a different name
BAAS_EXE = os.getenv("BAAS_EXE") or os.path.join(BAAS_DIR, "BlueArchiveAutoScript.exe")
BA_GAME_EXE = "BlueArchive.exe"
# The JP PC client has to be started from its launcher, which needs a click on スタート
BA_LAUNCHER_PATH = require_env("BA_LAUNCHER_PATH")
BA_LAUNCHER_EXE = os.path.basename(BA_LAUNCHER_PATH)
# Where スタート sits in the launcher window, as a fraction of its client area.
# Measure it with scripts/measure_click.py if the launcher layout ever changes.
BA_START_BUTTON = (0.852, 0.859)
BA_REG_KEY = r"Software\YostarJP\BlueArchive"

# Unity stores screen settings as "<name>_h<hash>"; match on the prefix
# What BAAS needs: a 1280x720 window
UNITY_WINDOWED = {
    "Screenmanager Fullscreen mode": 3,              # 3 = windowed
    "Screenmanager Resolution Width": 1280,
    "Screenmanager Resolution Height": 720,
    "Screenmanager Resolution Window Width": 1280,
    "Screenmanager Resolution Window Height": 720,
    "Screenmanager Resolution Use Native": 0,
    "Screenmanager Window Position X": 0,
    "Screenmanager Window Position Y": 0,
}

# Telegram
TG_BOT_TOKEN = require_env("TG_BOT_TOKEN")
TG_CHAT_ID = require_env("TG_CHAT_ID")

# Archived copies of each run's MaaEnd log (MaaEnd overwrites go-service.log on every launch)
ARCHIVE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")

# Endfield tasks in the order MaaEnd runs them: (log entry name, report label)
ENDFIELD_TASKS = [
    ("LaunchGamePC", "启动游戏"),
    ("StashBackpackMain", "存放背包"),
    ("DijiangRewards", "基建任务"),
    ("OutpostTradingSchedule", "据点贸易"),
    ("AutoStockStapleSchedule", "购买稳定物资"),
    ("AutoStockpileMain", "自动囤货"),
    ("DeliveryJobsMain", "转交委托"),
    ("AutoSellMain", "出售类产品"),
    ("EnvironmentMonitoringMain", "环境监测"),
    ("TrialOfSwordmancyMain", "选剑演武"),
    ("SeizeDeliveryJobs", "抢委托送货"),
    ("VisitFriendsMain", "拜访好友"),
    ("CreditShoppingMain", "信用点购物"),
    ("GiftOperatorMain", "赠送礼物"),
    ("DailyRewardStart", "日常奖励领取"),
    ("MXU_KILLPROC", "结束进程"),
]

# Some tasks show up in the log under more than one entry name
ENTRY_ALIASES = {
    "SeizeDeliveryJobsMain": "SeizeDeliveryJobs",
    "SeizeDeliveryJobsCheckOngoingJob": "SeizeDeliveryJobs",
    "SellProductSchedule": "AutoSellMain",
}

DELIVERY_TARGET = 3


# ==========================================
# 2. Helpers
# ==========================================
def ts():
    return datetime.datetime.now().strftime("%H:%M:%S")


def check_switch(file_path):
    """A game is ON unless its switch file exists."""
    return not os.path.exists(file_path)


def is_running(exe_names):
    output = os.popen("tasklist").read().lower()
    return any(name.lower() in output for name in exe_names)


def kill(exe_names):
    for name in exe_names:
        subprocess.run(["taskkill", "/F", "/IM", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def log_size(path):
    return os.path.getsize(path) if os.path.exists(path) else 0


def read_since(path, offset):
    """Return everything written to `path` after byte `offset` (handles truncation/rotation)."""
    if not os.path.exists(path):
        return ""
    if os.path.getsize(path) < offset:
        offset = 0
    with open(path, "rb") as f:
        f.seek(offset)
        return f.read().decode("utf-8", errors="ignore")


def mute_volume():
    """Press the volume-down key enough times to reach 0 (quiet early-morning runs)."""
    try:
        vk_volume_down = 0xAE
        for _ in range(50):
            ctypes.windll.user32.keybd_event(vk_volume_down, 0, 0, 0)
            ctypes.windll.user32.keybd_event(vk_volume_down, 0, 2, 0)
            time.sleep(0.01)
        print("🔇 物理静音模式已激活")
    except Exception as e:
        print(f"⚠️ 静音模式激活失败: {e}")


def shutdown():
    print("任务全部完成，准备关机。")
    time.sleep(5)
    subprocess.run(["shutdown", "/s", "/t", "0"])


def send_tg_msg(text):
    """Send an HTML-formatted Telegram message; fall back to plain text if Telegram rejects the HTML."""
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={"chat_id": TG_CHAT_ID, "text": text, "parse_mode": "HTML"}, timeout=15)
        if r.ok:
            return True
        print(f"⚠️ Telegram HTML 发送失败: {r.status_code} {r.text[:200]}")
        plain = re.sub(r"</?b>", "", text)
        r = requests.post(url, json={"chat_id": TG_CHAT_ID, "text": html.unescape(plain)}, timeout=15)
        return r.ok
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Telegram 发送失败: {type(e).__name__}")
        return False


def _find_unity_values(key, prefixes):
    """Map each Unity screen-setting prefix to its actual value name in this key."""
    found, i = {}, 0
    while True:
        try:
            name = winreg.EnumValue(key, i)[0]
        except OSError:
            break
        for prefix in prefixes:
            # "_h" excludes look-alikes such as "Screenmanager Fullscreen mode Default_h..."
            if name.startswith(prefix + "_h"):
                found[prefix] = name
        i += 1
    return found


def set_display(key_path, values):
    """Write a fixed set of Unity screen settings (prefix -> value) into the game's registry key."""
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0,
                        winreg.KEY_READ | winreg.KEY_WRITE) as key:
        for prefix, name in _find_unity_values(key, values).items():
            winreg.SetValueEx(key, name, 0, winreg.REG_DWORD, values[prefix])


def baas_processes(baas_dir):
    """Processes whose executable lives inside the BAAS folder (launcher, bundled pythonw, OCR server).
    Matching on the path keeps us from touching our own python.exe or anyone else's pythonw.exe."""
    root = os.path.normcase(os.path.abspath(baas_dir)) + os.sep
    procs = []
    for p in psutil.process_iter(["exe", "name"]):
        exe = p.info.get("exe")
        if exe and os.path.normcase(exe).startswith(root):
            procs.append(p)
    return procs


def kill_processes(procs):
    for p in procs:
        try:
            p.kill()
        except psutil.Error:
            pass


user32 = ctypes.windll.user32


def make_dpi_aware():
    """Use real pixel coordinates even with 125%/150% display scaling (safe to call more than once)."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            user32.SetProcessDPIAware()
        except Exception:
            pass


def process_running(exe_name):
    """Exact process-name check (tasklist truncates long names, so use psutil instead)."""
    exe_name = exe_name.lower()
    return any((p.info.get("name") or "").lower() == exe_name for p in psutil.process_iter(["name"]))


def main_window_of(exe_name):
    """Return the largest visible top-level window owned by a process with this exe name, or None."""
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
                area = rect.right * rect.bottom
                if area > best_area:
                    best, best_area = hwnd, area
        return True

    user32.EnumWindows(enum_proc(callback), 0)
    return best


def click_in_window(hwnd, fx, fy):
    """Bring the window to the front and click with the real mouse at a fraction of its client area."""
    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.5)
    rect = wintypes.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(rect))
    point = wintypes.POINT(int(rect.right * fx), int(rect.bottom * fy))
    user32.ClientToScreen(hwnd, ctypes.byref(point))
    user32.SetCursorPos(point.x, point.y)
    time.sleep(0.1)
    user32.mouse_event(0x0002, 0, 0, 0, 0)  # left down
    time.sleep(0.05)
    user32.mouse_event(0x0004, 0, 0, 0, 0)  # left up


def launch_ba_game(timeout=600):
    """Open the JP launcher and press スタート until the game process appears. Returns True on success.
    Clicking is repeated because the launcher may still be checking for updates the first few times."""
    make_dpi_aware()
    print(f"[{ts()}] 正在启动蔚蓝档案启动器: {BA_LAUNCHER_PATH}")
    subprocess.Popen([BA_LAUNCHER_PATH], cwd=os.path.dirname(BA_LAUNCHER_PATH))
    start = time.time()
    while time.time() - start < timeout:
        time.sleep(10)
        if process_running(BA_GAME_EXE):
            print(f"[{ts()}] 游戏已启动，等待标题画面加载...")
            time.sleep(30)  # let the title screen load before BAAS takes over
            return True
        hwnd = main_window_of(BA_LAUNCHER_EXE)
        if hwnd:
            print(f"[{ts()}] 点击启动器的 スタート")
            click_in_window(hwnd, *BA_START_BUTTON)
    return False


# ==========================================
# 3. Process runners
# ==========================================
def run_and_monitor(exe_path, app_exe_names, game_exe_name=None, timeout=7200, args=None):
    """Start an app that exits on its own, wait for it to exit (or time out), then close the game."""
    if isinstance(app_exe_names, str):
        app_exe_names = [app_exe_names]

    print(f"[{ts()}] 正在启动: {exe_path}")
    try:
        subprocess.Popen([exe_path] + (args or []), cwd=os.path.dirname(exe_path))
    except Exception as e:
        print(f"⚠️ 启动失败: {e}")
        return "launch_failed"

    time.sleep(15)
    start = time.time()
    reason = "exited"
    while is_running(app_exe_names):
        if time.time() - start > timeout:
            print(f"[{ts()}] ⚠ 监控超时，强行结束 {app_exe_names}")
            kill(app_exe_names)
            reason = "timeout"
            break
        time.sleep(10)

    print(f"[{ts()}] 结束原因: {reason}")
    if game_exe_name:
        kill([game_exe_name])
        time.sleep(3)
    return reason


def run_until_log_marker(exe_path, app_exe_names, log_path, done_markers, game_exe_name=None, timeout=1800):
    """Start an app that never exits on its own; stop it once its log prints a completion marker.
    Returns (reason, log_text) where log_text contains only what this run wrote."""
    if isinstance(app_exe_names, str):
        app_exe_names = [app_exe_names]

    offset = log_size(log_path)  # ignore everything written by earlier runs
    print(f"[{ts()}] 正在启动: {exe_path}")
    try:
        subprocess.Popen([exe_path], cwd=os.path.dirname(exe_path))
    except Exception as e:
        print(f"⚠️ 启动失败: {e}")
        return "launch_failed", ""

    start = time.time()
    reason = "timeout"
    missing_count = 0
    while time.time() - start < timeout:
        time.sleep(15)
        if any(m in read_since(log_path, offset) for m in done_markers):
            reason = "done"
            break
        # MAA briefly disappears while self-updating, so require two misses in a row
        if is_running(app_exe_names):
            missing_count = 0
        else:
            missing_count += 1
            if missing_count >= 2:
                reason = "exited"
                break

    print(f"[{ts()}] 结束原因: {reason}")
    time.sleep(10)  # let the app finish writing logs
    kill(app_exe_names + ([game_exe_name] if game_exe_name else []))
    time.sleep(3)
    return reason, read_since(log_path, offset)


def archive_endfield_log(log_dir, archive_dir, keep_days=14):
    """Copy go-service.log into the archive folder and prune copies older than keep_days."""
    try:
        os.makedirs(archive_dir, exist_ok=True)
        src = os.path.join(log_dir, "go-service.log")
        if os.path.exists(src):
            stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
            shutil.copy2(src, os.path.join(archive_dir, f"go-service_{stamp}.log"))
        cutoff = time.time() - keep_days * 86400
        for f in glob.glob(os.path.join(archive_dir, "go-service_*.log")):
            if os.path.getmtime(f) < cutoff:
                os.remove(f)
    except Exception as e:
        print(f"⚠️ 日志存档失败: {e}")


# ==========================================
# 4. Log parsers (deterministic, no AI)
# ==========================================
def parse_endfield_log(text):
    """Build the Endfield report from MaaEnd's go-service.log (one JSON object per line).

    Rules:
      - A task run starts at its "Checking aspect ratio before task execution" line.
      - Any "Task failed ..." line for an entry marks that run as failed
        (some failures, e.g. EnvironmentMonitoringMain, are only logged at debug level).
      - Game launch succeeds when the LaunchGamePC pretask logs "Pretask succeeded".
      - Each delivery pays out credits (item_spaceship_credit) while SeizeDeliveryJobs is running.
    """
    runs, fails = {}, {}
    launch = None  # None = launch task not seen, False = invoked but never succeeded, True = ok
    deliveries = 0
    delivery_activity = 0  # any sign that a delivery job was actually scanned or routed
    current = None

    for raw in text.splitlines():
        raw = raw.strip()
        if not raw.startswith("{"):
            continue
        try:
            rec = json.loads(raw)
        except ValueError:
            continue

        msg = rec.get("message", "")
        if rec.get("task") == "LaunchGamePC":
            if msg == "Pretask succeeded":
                launch = True
            elif launch is None:
                launch = False
            continue

        entry = rec.get("entry")
        key = ENTRY_ALIASES.get(entry, entry)
        if entry and msg == "Checking aspect ratio before task execution":
            runs[key] = runs.get(key, 0) + 1
            current = key
        elif entry and "Task failed" in msg:
            fails[key] = fails.get(key, 0) + 1
        elif (current == "SeizeDeliveryJobs"
              and msg == "item quantity added from recognition"
              and rec.get("item_id") == "item_spaceship_credit"):
            deliveries += 1
        if current == "SeizeDeliveryJobs" and rec.get("component") in (
                "SeizeDeliveryJobs", "AutoDeliveryResolveDestinationAction"):
            delivery_activity += 1

    lines = ["『🪐 终末地战报』"]
    if launch is None and not runs:
        lines.append("⚠️ 日志里没有任何任务记录（MaaEnd 可能没有运行）")
        return "\n".join(lines)

    launch_status = {True: "✅成功", False: "❌失败", None: "⚠️未执行"}[launch]
    lines.append(f"启动游戏：{launch_status}")

    for key, label in ENDFIELD_TASKS[1:]:
        n_runs, n_fails = runs.get(key, 0), fails.get(key, 0)
        if n_runs == 0:
            status = "⚠️未执行"
        elif n_fails:
            status = "❌失败" + (f"({n_fails}/{n_runs}次)" if n_runs > 1 else "")
        else:
            status = "✅成功"

        if key == "SeizeDeliveryJobs" and n_runs:
            if deliveries >= DELIVERY_TARGET and not n_fails:
                status = f"✅成功({deliveries}/{DELIVERY_TARGET})"
            elif deliveries == 0 and delivery_activity == 0 and not n_fails:
                # Task ran but found nothing to pick up - usually already done today
                status = "✅无可接委托（今日可能已送完）"
            elif not n_fails:
                status = f"⚠️部分完成({deliveries}/{DELIVERY_TARGET})"
            else:
                status += f"({deliveries}/{DELIVERY_TARGET})"
        lines.append(f"{label}：{status}")

    # Surface tasks that MaaEnd added but the table doesn't know yet
    known = {k for k, _ in ENDFIELD_TASKS}
    for key in runs:
        if key not in known:
            status = "❌失败" if fails.get(key) else "✅成功"
            lines.append(f"{key}（新任务）：{status}")

    return "\n".join(lines)


def parse_maa_log(text, reason):
    """Build the Arknights report from this run's MAA gui.log lines."""
    started = re.findall(r"开始任务: (\S+)", text)
    finished = set(re.findall(r"完成任务: (\S+)", text))
    recruits = len(re.findall(r"已确认招募", text))

    lines = ["『🎯 明日方舟战报』"]
    if not started:
        lines.append("⚠️ MAA 未开始任何任务（游戏未启动或未连接）")

    seen = []
    for name in started:
        if name in seen:
            continue
        seen.append(name)
        status = "✅成功" if name in finished else "❌失败"
        if name == "自动公招" and name in finished:
            status += f"(招募{recruits}次)"
        lines.append(f"{name}：{status}")

    if reason != "done":
        lines.append(f"⚠️ 未检测到全部完成标记（结束原因: {reason}）")
    return "\n".join(lines)


def parse_ww_log(text, reason):
    """Build the Wuthering Waves report from this run's ok-ww log lines.
    NOTE: keyword-based; verify against a real Monday log and tighten if needed."""
    lines = ["『🌊 鸣潮战报』"]
    low = text.lower()
    if not text.strip():
        lines.append(f"每周花园：⚠️未读取到本次日志（结束原因: {reason}）")
        return "\n".join(lines)

    garden_done = "gardentask" in low and any(k in low for k in ("completed", "完成", "garden current"))
    has_error = any(k in low for k in ("traceback", "exception"))

    if garden_done:
        status = "✅成功" + ("(日志有异常，建议查看)" if has_error else "")
    elif has_error:
        status = "❌失败(日志有异常)"
    else:
        status = "⚠️未确认完成"
    lines.append(f"每周花园：{status}")
    return "\n".join(lines)


# ==========================================
# 5. Game sections
# ==========================================
def run_endfield():
    run_and_monitor(MAA_END_PATH, "MaaEnd.exe", "Endfield.exe")
    kill(["Gryphlink.exe"])  # MaaEnd starts the launcher too
    time.sleep(5)
    archive_endfield_log(MAA_LOG_DIR, ARCHIVE_DIR)
    return parse_endfield_log(read_since(os.path.join(MAA_LOG_DIR, "go-service.log"), 0))


def run_arknights():
    reason, maa_log = run_until_log_marker(MAA_ARK_PATH, "MAA.exe", MAA_ARK_LOG, MAA_DONE_MARKERS, ARK_GAME_EXE)
    return parse_maa_log(maa_log, reason)


def run_wuthering():
    offset = log_size(WW_LOG_PATH)
    reason = run_and_monitor(OK_WW_PATH, ["ok-ww.exe", "pythonw.exe"], "Client-Win64-Shipping.exe",
                             args=["-t", "GardenTask", "-e"])
    time.sleep(5)
    return parse_ww_log(read_since(WW_LOG_PATH, offset), reason)


def run_bluearchive(start_timeout=300, timeout=5400):
    """Switch BA to 1280x720 windowed, open the game through its launcher, run BAAS until it exits
    on its own, then close everything and restore the display.

    BlueArchiveAutoScript.exe is only a launcher: it checks for updates, starts BAAS (pythonw.exe
    inside the BAAS folder) and exits. So we watch every process living in the BAAS folder instead.
    """
    set_display(BA_REG_KEY, UNITY_WINDOWED)
    start = time.time()
    reason = "timeout"
    saw_baas = False  # did the real BAAS (pythonw.exe) ever start?
    try:
        if not launch_ba_game():
            reason = "game_not_started"
            raise TimeoutError("game did not start from the launcher")
        start = time.time()  # time BAAS itself, not the launcher
        print(f"[{ts()}] 正在启动: {BAAS_EXE}")
        # Give the BAAS launcher its own console window so its output doesn't flood ours
        subprocess.Popen([BAAS_EXE], cwd=BAAS_DIR, creationflags=subprocess.CREATE_NEW_CONSOLE)
        while time.time() - start < timeout:
            time.sleep(15)
            procs = baas_processes(BAAS_DIR)
            if any((p.info.get("name") or "").lower() == "pythonw.exe" for p in procs):
                saw_baas = True
            if not procs:
                reason = "exited" if saw_baas else "not_started"
                break
            if not saw_baas and time.time() - start > start_timeout:
                reason = "not_started"
                break
        print(f"[{ts()}] 结束原因: {reason}")
    except TimeoutError as e:
        print(f"⚠️ {e}")
    finally:
        # Always clean up and give the display settings back, even if something above failed
        kill_processes(baas_processes(BAAS_DIR))
        kill([BA_GAME_EXE, BA_LAUNCHER_EXE])
        time.sleep(3)

    minutes = (time.time() - start) / 60
    lines = ["『📘 蔚蓝档案战报』"]
    if reason == "exited" and minutes >= 3:
        lines.append(f"BAAS 日常：✅已运行完毕（用时 {minutes:.0f} 分钟）")
    elif reason == "exited":
        lines.append(f"BAAS 日常：⚠️很快就退出（{minutes:.1f} 分钟），可能没有到期的任务")
    elif reason == "game_not_started":
        lines.append("BAAS 日常：❌游戏没有从启动器打开（スタート 没点到？）")
    elif reason == "not_started":
        lines.append("BAAS 日常：❌BAAS 没有启动（启动器可能更新失败）")
    else:
        lines.append(f"BAAS 日常：⚠️超时，已强制结束（{minutes:.0f} 分钟）")
    return "\n".join(lines)


def safe_section(name, func):
    """Run one game section; an unexpected error is reported instead of crashing the whole morning."""
    try:
        return func()
    except Exception as e:
        print(f"⚠️ {name} 流程出错: {e}")
        return f"⚠️ {name} 流程出错: {type(e).__name__}: {e}"


# ==========================================
# 6. Main
# ==========================================
def parse_args():
    p = argparse.ArgumentParser(description="Dawnshift - daily game butler (full-Python version)")
    p.add_argument("--no-shutdown", action="store_true", help="do not shut down after the run")
    p.add_argument("--dry-run", action="store_true",
                   help="launch nothing; parse an existing MaaEnd log and print the report")
    p.add_argument("--endfield-log", help="MaaEnd log to parse in --dry-run (default: current go-service.log)")
    p.add_argument("--only", choices=["endfield", "arknights", "wuthering", "bluearchive"],
                   help="run one game only; print the report, no Telegram, no shutdown")
    return p.parse_args()


def main():
    args = parse_args()

    if args.dry_run:
        path = args.endfield_log or os.path.join(MAA_LOG_DIR, "go-service.log")
        print(f"解析: {path}\n")
        print(parse_endfield_log(read_since(path, 0)))
        return

    if args.only:
        runners = {"endfield": run_endfield, "arknights": run_arknights,
                   "wuthering": run_wuthering, "bluearchive": run_bluearchive}
        print(safe_section(args.only, runners[args.only]))
        return

    mute_volume()
    print("=== Dawnshift 启动 (pagent) ===")

    sections = [safe_section("终末地", run_endfield)]

    if check_switch(ARK_SWITCH_FILE):
        sections.append(safe_section("明日方舟", run_arknights))
    else:
        print("方舟开关为 [OFF]，跳过。")

    if check_switch(WW_SWITCH_FILE) and datetime.datetime.today().weekday() == 0:
        sections.append(safe_section("鸣潮", run_wuthering))
    else:
        print("今天不跑鸣潮（不是周一或开关为 OFF）。")

    # Blue Archive last: JP daily reset is 04:00 JST (06:00 Melbourne in daylight saving)
    if check_switch(BA_SWITCH_FILE):
        sections.append(safe_section("蔚蓝档案", run_bluearchive))
    else:
        print("蔚蓝档案开关为 [OFF]，跳过。")

    report = "\n\n".join(sections)
    print("\n" + report + "\n")

    title = f"🌅 Dawnshift 战报 ({datetime.datetime.now().strftime('%m-%d')})"
    send_tg_msg(f"<b>{title}</b>\n\n{html.escape(report)}")

    if not args.no_shutdown:
        shutdown()


if __name__ == "__main__":
    main()