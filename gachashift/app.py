"""Gachashift desktop app: turn games on, fill in their paths and options, save to config.json.

Run with:  python -m gachashift.app
The app only edits settings; the morning run itself is still `python -m gachashift`.
"""

import copy
import ctypes
import datetime
import os
import re
import subprocess
import sys
import tempfile
import webbrowser
from ctypes import wintypes
from xml.sax.saxutils import escape
from tkinter import filedialog, messagebox

import customtkinter as ctk
import psutil
import requests

from .config import app_dir, load_config, save_config
from .games import GAMES, GAMES_BY_ID
from .i18n import game_name, t
from .system import log_size, read_since

# Pre-dawn palette: the app lives in the hour before sunrise
NIGHT = "#141B2D"      # window background, deep indigo
PANEL = "#1C2540"      # sidebar and grouped sections
LINE = "#2D3858"       # borders and inactive controls
TEXT = "#E9E7F2"
MUTED = "#98A1BE"
DAWN = "#F4B860"       # the single accent: first light
DAWN_HOVER = "#E0A24A"
PICKED = "#46557F"     # selected segment: lighter indigo keeps the text readable
OK_COLOR = "#7BD3A0"
FAIL_COLOR = "#EF7D7D"

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


class GachashiftApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        self.cfg = load_config()
        self.saved_cfg = copy.deepcopy(self.cfg)
        self.page = "home"
        self.current_game = GAMES[0].id
        self.test_game = GAMES[0].id
        self.run_handle = None        # a test run in progress
        self.run_log = None
        self.run_offset = 0
        self.geometry("880x620")
        self.minsize(760, 520)
        self.configure(fg_color=NIGHT)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.build()

    # ---------- helpers ----------
    @property
    def lang(self):
        return self.cfg.get("language", "en")

    def tr(self, key, **kwargs):
        return t(self.lang, key, **kwargs)

    def font(self, size=14, weight="normal"):
        family = "Microsoft YaHei UI" if self.lang == "zh" else "Segoe UI"
        return ctk.CTkFont(family=family, size=size, weight=weight)

    def changed(self):
        dirty = self.cfg != self.saved_cfg
        self.status.configure(text=self.tr("unsaved") if dirty else "", text_color=MUTED)

    # ---------- layout ----------
    def build(self):
        """(Re)build the whole window, e.g. after the app language changes."""
        for child in self.winfo_children():
            child.destroy()
        self.title("Gachashift")
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        side = ctk.CTkFrame(self, width=190, corner_radius=0, fg_color=PANEL)
        side.grid(row=0, column=0, rowspan=2, sticky="nsw")
        side.pack_propagate(False)  # keep the sidebar at its set width
        # The horizon: a strip that goes from night to first light
        horizon = ctk.CTkCanvas(side, width=10, height=6, highlightthickness=0, bg=PANEL)
        horizon.pack(fill="x")
        horizon.bind("<Configure>", lambda e: self.draw_horizon(horizon, e.width))
        ctk.CTkLabel(side, text="Gachashift", font=self.font(22, "bold"),
                     text_color=TEXT).pack(anchor="w", padx=22, pady=(22, 28))
        self.nav_buttons = {}
        for page in ("home", "games", "test", "schedule", "history", "general"):
            button = ctk.CTkButton(side, text=self.tr(f"nav.{page}"), anchor="w", height=38,
                                   font=self.font(15), corner_radius=8, fg_color="transparent",
                                   hover_color=LINE, text_color=TEXT,
                                   command=lambda p=page: self.show(p))
            button.pack(fill="x", padx=12, pady=2)
            self.nav_buttons[page] = button

        self.content = ctk.CTkScrollableFrame(self, fg_color=NIGHT, corner_radius=0)
        self.content.grid(row=0, column=1, sticky="nsew", padx=(28, 16), pady=(24, 0))

        bar = ctk.CTkFrame(self, fg_color=NIGHT, corner_radius=0)
        bar.grid(row=1, column=1, sticky="ew", padx=28, pady=16)
        self.status = ctk.CTkLabel(bar, text="", font=self.font(13), text_color=MUTED,
                                   wraplength=480, justify="left")
        self.status.pack(side="left")
        ctk.CTkButton(bar, text=self.tr("save"), width=110, height=36, font=self.font(15, "bold"),
                      fg_color=DAWN, hover_color=DAWN_HOVER, text_color=NIGHT,
                      command=self.save).pack(side="right")
        self.show(self.page)
        self.changed()

    @staticmethod
    def draw_horizon(canvas, width):
        canvas.delete("all")
        start, end = (0x14, 0x1B, 0x2D), (0xF4, 0xB8, 0x60)
        steps = max(width, 1)
        for x in range(steps):
            mix = x / steps
            color = "#%02x%02x%02x" % tuple(int(a + (b - a) * mix) for a, b in zip(start, end))
            canvas.create_line(x, 0, x, 6, fill=color)

    def show(self, page):
        self.page = page
        for name, button in self.nav_buttons.items():
            button.configure(fg_color=LINE if name == page else "transparent")
        for child in self.content.winfo_children():
            child.destroy()
        {"home": self.page_home, "games": self.page_games, "test": self.page_test,
         "schedule": self.page_schedule, "history": self.page_history,
         "general": self.page_general}[page]()

    def heading(self, text):
        ctk.CTkLabel(self.content, text=text, font=self.font(24, "bold"),
                     text_color=TEXT).pack(anchor="w", pady=(0, 6))

    def section(self):
        frame = ctk.CTkFrame(self.content, fg_color=PANEL, corner_radius=12)
        frame.pack(fill="x", pady=(10, 4))
        return frame

    # ---------- Home ----------
    def page_home(self):
        self.heading(self.tr("home.heading"))
        ctk.CTkLabel(self.content, text=self.tr("home.hint"), font=self.font(14), text_color=MUTED,
                     wraplength=560, justify="left").pack(anchor="w", pady=(0, 14))
        for game_cls in GAMES:
            gid = game_cls.id
            game_cfg = self.cfg["games"][gid]
            row = self.section()
            row.grid_columnconfigure(1, weight=1)
            var = ctk.BooleanVar(value=bool(game_cfg.get("enabled")))

            def toggle(gid=gid, var=var):
                self.cfg["games"][gid]["enabled"] = var.get()
                self.changed()
                self.show("home")

            ctk.CTkSwitch(row, text="", variable=var, command=toggle, width=48,
                          progress_color=DAWN, button_color=TEXT,
                          fg_color=LINE).grid(row=0, column=0, rowspan=2, padx=(16, 8), pady=14)
            name = ctk.CTkLabel(row, text=game_name(gid, self.lang), font=self.font(16, "bold"),
                                text_color=TEXT if game_cfg.get("enabled") else MUTED, cursor="hand2")
            name.grid(row=0, column=1, sticky="w", pady=(12, 0))
            name.bind("<Button-1>", lambda e, gid=gid: self.open_game(gid))
            ctk.CTkLabel(row, text=self.days_summary(game_cfg.get("days", [])), font=self.font(13),
                         text_color=MUTED).grid(row=1, column=1, sticky="w", pady=(0, 12))

            if not game_cfg.get("enabled"):
                state, color = self.tr("home.off"), MUTED
            elif missing_items(gid, game_cfg):
                state, color = self.tr("home.setup"), FAIL_COLOR
            else:
                state, color = self.tr("home.ready"), OK_COLOR
            status = ctk.CTkLabel(row, text=state, font=self.font(14, "bold"), text_color=color,
                                  cursor="hand2")
            status.grid(row=0, column=2, rowspan=2, padx=18)
            status.bind("<Button-1>", lambda e, gid=gid: self.open_game(gid))

    def days_summary(self, days):
        if len(days) == 7:
            return self.tr("home.every_day")
        if not days:
            return self.tr("home.no_days")
        names = DAY_KEYS_ZH if self.lang == "zh" else DAY_KEYS_EN
        return ("周" if self.lang == "zh" else "") + ("、" if self.lang == "zh" else ", ").join(
            names[d] for d in sorted(days))

    def open_game(self, gid):
        self.current_game = gid
        self.show("games")

    # ---------- Games ----------
    def page_games(self):
        short = SHORT_NAMES.get(self.lang, SHORT_NAMES["en"])
        names = {short[g.id]: g.id for g in GAMES}
        picker = ctk.CTkSegmentedButton(
            self.content, values=list(names), font=self.font(13),
            selected_color=PICKED, selected_hover_color=PICKED, unselected_color=PANEL,
            unselected_hover_color=LINE, fg_color=PANEL, text_color=TEXT,
            command=lambda label: self.open_game(names[label]))
        picker.set(short[self.current_game])
        picker.pack(anchor="w", pady=(0, 18))

        gid = self.current_game
        game_cfg = self.cfg["games"][gid]
        self.heading(game_name(gid, self.lang))
        tool, url = TOOLS[gid]
        ctk.CTkButton(self.content, text=self.tr("games.tool_page", tool=tool), width=0, height=28,
                      font=self.font(13), fg_color="transparent", hover_color=PANEL,
                      text_color=DAWN, anchor="w",
                      command=lambda: webbrowser.open(url)).pack(anchor="w", pady=(0, 6))

        box = self.section()
        enabled = ctk.BooleanVar(value=bool(game_cfg.get("enabled")))
        ctk.CTkSwitch(box, text=self.tr("games.enabled"), variable=enabled, font=self.font(15),
                      text_color=TEXT, progress_color=DAWN, fg_color=LINE, button_color=TEXT,
                      command=lambda: self.set_value(gid, "enabled", enabled.get())
                      ).pack(anchor="w", padx=18, pady=(16, 10))
        self.days_row(box, gid)

        form = self.section()
        form.grid_columnconfigure(1, weight=1)
        fields = FIELDS[gid]
        if gid == "zzz" and game_cfg.get("client") != "steam":
            fields = [f for f in fields if f[0] not in STEAM_ONLY]
        for row, (key, kind, extra) in enumerate(fields):
            self.field(form, row, gid, key, kind, extra)

    def days_row(self, parent, gid):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(anchor="w", padx=18, pady=(0, 16))
        ctk.CTkLabel(row, text=self.tr("games.days"), font=self.font(14),
                     text_color=MUTED, width=60, anchor="w").pack(side="left")
        names = DAY_KEYS_ZH if self.lang == "zh" else DAY_KEYS_EN
        days = set(self.cfg["games"][gid].get("days", []))
        variables = []

        def update():
            self.cfg["games"][gid]["days"] = [d for d, v in enumerate(variables) if v.get()]
            self.changed()

        for index, label in enumerate(names):
            var = ctk.BooleanVar(value=index in days)
            variables.append(var)
            ctk.CTkCheckBox(row, text=label, variable=var, command=update, width=58,
                            font=self.font(13), text_color=TEXT, fg_color=DAWN,
                            hover_color=DAWN_HOVER, border_color=LINE,
                            checkmark_color=NIGHT).pack(side="left", padx=2)

    def set_value(self, gid, key, value):
        self.cfg["games"][gid][key] = value
        self.changed()

    def pick_choice(self, gid, key, value):
        self.set_value(gid, key, value)
        if key == "client":
            self.show("games")  # Steam-only fields appear or disappear

    def field(self, parent, row, gid, key, kind, extra):
        game_cfg = self.cfg["games"][gid]
        pad = {"padx": (18, 10), "pady": 8}
        if kind == "bool":
            var = ctk.BooleanVar(value=bool(game_cfg.get(key)))
            ctk.CTkCheckBox(parent, text=self.tr(f"f.{key}"), variable=var, font=self.font(14),
                            text_color=TEXT, fg_color=DAWN, hover_color=DAWN_HOVER,
                            border_color=LINE, checkmark_color=NIGHT,
                            command=lambda: self.set_value(gid, key, var.get())
                            ).grid(row=row, column=0, columnspan=3, sticky="w", **pad)
            return

        ctk.CTkLabel(parent, text=self.tr(f"f.{key}"), font=self.font(14), text_color=MUTED,
                     anchor="w").grid(row=row, column=0, sticky="w", **pad)

        if kind == "choice":
            labels = {self.tr(f"choice.{v}"): v for v in extra}
            picker = ctk.CTkSegmentedButton(
                parent, values=list(labels), font=self.font(13), selected_color=PICKED,
                selected_hover_color=PICKED, unselected_color=LINE, unselected_hover_color=LINE,
                fg_color=LINE, text_color=TEXT,
                command=lambda label: self.pick_choice(gid, key, labels[label]))
            picker.set(self.tr(f"choice.{game_cfg.get(key, extra[0])}"))
            picker.grid(row=row, column=1, columnspan=2, sticky="w", pady=8)
            return

        value = game_cfg.get(key, "")
        if kind == "point":
            value = ", ".join(str(v) for v in value) if isinstance(value, list) else str(value)
        var = ctk.StringVar(value=value or "")
        cell = ctk.CTkFrame(parent, fg_color="transparent")
        cell.grid(row=row, column=1, sticky="ew", pady=8)
        entry = ctk.CTkEntry(cell, textvariable=var, font=self.font(13), height=34,
                             fg_color=NIGHT, border_color=LINE, text_color=TEXT)
        entry.pack(fill="x")
        # a short message under the entry, shown only when something is wrong
        note = ctk.CTkLabel(cell, text="", font=self.font(12), text_color=FAIL_COLOR, height=18)

        def on_change(*_):
            text = var.get().strip()
            message = ""
            if kind == "point":
                point = parse_point(text)
                if point:
                    game_cfg[key] = point
                else:
                    message = self.tr("button.invalid")
            else:
                game_cfg[key] = text
                if kind in PATH_KINDS and text and not os.path.exists(text):
                    message = self.tr("path.missing")
            entry.configure(border_color=FAIL_COLOR if message else LINE)
            note.configure(text=message)
            if message:
                note.pack(anchor="w")
            else:
                note.pack_forget()
            self.changed()

        var.trace_add("write", on_change)
        if kind == "point":
            ctk.CTkButton(parent, text=self.tr("calib.button"), width=78, height=34, font=self.font(13),
                          fg_color=LINE, hover_color=PANEL, text_color=TEXT,
                          command=lambda: self.calibrate(gid, var)
                          ).grid(row=row, column=2, sticky="n", padx=(8, 18), pady=8)
        if kind in PATH_KINDS:
            ctk.CTkButton(parent, text=self.tr("browse"), width=78, height=34, font=self.font(13),
                          fg_color=LINE, hover_color=PANEL, text_color=TEXT,
                          command=lambda: self.browse(var, kind)
                          ).grid(row=row, column=2, sticky="n", padx=(8, 18), pady=8)
        if value:
            on_change()  # show problems with the saved value right away

    @staticmethod
    def browse(var, kind):
        start = os.path.dirname(var.get()) if var.get() else None
        if kind == "dir":
            path = filedialog.askdirectory(initialdir=start)
        elif kind == "exe":
            path = filedialog.askopenfilename(initialdir=start, filetypes=[("Programs", "*.exe")])
        else:
            path = filedialog.askopenfilename(initialdir=start)
        if path:
            var.set(os.path.normpath(path))

    # ---------- Test run ----------
    def page_test(self):
        self.heading(self.tr("test.heading"))
        ctk.CTkLabel(self.content, text=self.tr("test.explain"), font=self.font(14), text_color=MUTED,
                     wraplength=580, justify="left").pack(anchor="w", pady=(0, 14))
        short = SHORT_NAMES.get(self.lang, SHORT_NAMES["en"])
        names = {short[g.id]: g.id for g in GAMES}
        row = ctk.CTkFrame(self.content, fg_color="transparent")
        row.pack(anchor="w", fill="x")
        picker = ctk.CTkSegmentedButton(
            row, values=list(names), font=self.font(13), selected_color=PICKED,
            selected_hover_color=PICKED, unselected_color=PANEL, unselected_hover_color=LINE,
            fg_color=PANEL, text_color=TEXT,
            command=lambda label: self.pick_test_game(names[label]))
        picker.set(short[self.test_game])
        picker.pack(side="left")
        busy = self.run_handle is not None
        self.run_button = ctk.CTkButton(
            self.content, text=self.tr("test.run", game=short[self.test_game]), height=38,
            font=self.font(14, "bold"), fg_color=DAWN, hover_color=DAWN_HOVER, text_color=NIGHT,
            state="disabled" if busy else "normal", command=self.start_test)
        self.run_button.pack(anchor="w", pady=(14, 0))
        self.run_status = ctk.CTkLabel(self.content, text=self.tr("test.running") if busy else "",
                                       font=self.font(13), text_color=MUTED)
        self.run_status.pack(anchor="w", pady=(10, 4))
        self.output = ctk.CTkTextbox(self.content, height=360, font=self.font(13),
                                     fg_color=PANEL, text_color=TEXT, border_color=LINE, border_width=1)
        self.output.pack(fill="both", expand=True)
        if self.run_log:
            self.output.insert("end", read_since(self.run_log, self.run_start_offset))
            self.output.see("end")

    def pick_test_game(self, gid):
        self.test_game = gid
        if self.run_handle is None:
            short = SHORT_NAMES.get(self.lang, SHORT_NAMES["en"])
            self.run_button.configure(text=self.tr("test.run", game=short[gid]))

    def start_test(self):
        if self.cfg != self.saved_cfg:
            self.run_status.configure(text=self.tr("test.unsaved"), text_color=FAIL_COLOR)
            return
        # The run writes everything it prints to today's log; the app shows that file as it grows
        self.run_log = str(app_dir() / "logs" / f"gachashift_{datetime.date.today():%Y-%m-%d}.log")
        self.run_start_offset = self.run_offset = log_size(self.run_log)
        handle = start_elevated(f"-m gachashift --only {self.test_game}")
        if not handle:
            self.run_status.configure(text=self.tr("test.denied"), text_color=FAIL_COLOR)
            return
        self.run_handle = handle
        self.run_button.configure(state="disabled")
        self.run_status.configure(text=self.tr("test.running"), text_color=MUTED)
        self.output.delete("1.0", "end")
        self.after(700, self.poll_test)

    def poll_test(self):
        finished = process_finished(self.run_handle)
        new = read_since(self.run_log, self.run_offset)
        self.run_offset = log_size(self.run_log)
        if self.page == "test" and self.output.winfo_exists():
            if new:
                self.output.insert("end", new)
                self.output.see("end")
        if not finished:
            self.after(700, self.poll_test)
            return
        ctypes.windll.kernel32.CloseHandle(self.run_handle)
        self.run_handle = None
        if self.page == "test":
            self.run_button.configure(state="normal")
            self.run_status.configure(text=self.tr("test.done"), text_color=OK_COLOR)

    # ---------- Schedule ----------
    def page_schedule(self):
        self.heading(self.tr("nav.schedule"))
        ctk.CTkLabel(self.content, text=self.tr("schedule.explain"), font=self.font(14), text_color=MUTED,
                     wraplength=580, justify="left").pack(anchor="w", pady=(0, 14))
        current = scheduled_time()
        box = self.section()
        state = ctk.CTkLabel(box, text=self.tr("schedule.current", time=current) if current
                             else self.tr("schedule.none"), font=self.font(15, "bold"),
                             text_color=OK_COLOR if current else MUTED)
        state.pack(anchor="w", padx=18, pady=(16, 10))

        row = ctk.CTkFrame(box, fg_color="transparent")
        row.pack(anchor="w", padx=18, pady=(0, 16))
        ctk.CTkLabel(row, text=self.tr("schedule.time"), font=self.font(14), text_color=MUTED
                     ).pack(side="left", padx=(0, 12))
        hour, minute = (current or "06:00").split(":")
        hours = ctk.CTkOptionMenu(row, values=[f"{h:02d}" for h in range(24)], width=70,
                                  font=self.font(14), fg_color=LINE, button_color=LINE,
                                  button_hover_color=PICKED, text_color=TEXT)
        hours.set(hour)
        hours.pack(side="left")
        ctk.CTkLabel(row, text=":", font=self.font(16, "bold"), text_color=TEXT).pack(side="left", padx=4)
        minutes = ctk.CTkOptionMenu(row, values=[f"{m:02d}" for m in range(0, 60, 5)], width=70,
                                    font=self.font(14), fg_color=LINE, button_color=LINE,
                                    button_hover_color=PICKED, text_color=TEXT)
        minutes.set(minute if int(minute) % 5 == 0 else "00")
        minutes.pack(side="left")

        result = ctk.CTkLabel(self.content, text="", font=self.font(13), text_color=MUTED,
                              wraplength=580, justify="left")

        def save_schedule():
            path = os.path.join(tempfile.gettempdir(), "gachashift_task.xml")
            with open(path, "w", encoding="utf-16") as f:
                f.write(task_xml(int(hours.get()), int(minutes.get())))
            ok = run_schtasks_elevated(f'/create /tn {TASK_NAME} /xml "{path}" /f')
            time_text = f"{hours.get()}:{minutes.get()}"
            result.configure(text=self.tr("schedule.saved", time=time_text) if ok
                             else self.tr("schedule.failed"), text_color=OK_COLOR if ok else FAIL_COLOR)
            if ok:
                state.configure(text=self.tr("schedule.current", time=time_text), text_color=OK_COLOR)

        def remove_schedule():
            ok = run_schtasks_elevated(f"/delete /tn {TASK_NAME} /f")
            result.configure(text=self.tr("schedule.removed") if ok else self.tr("schedule.failed"),
                             text_color=OK_COLOR if ok else FAIL_COLOR)
            if ok:
                state.configure(text=self.tr("schedule.none"), text_color=MUTED)

        buttons = ctk.CTkFrame(self.content, fg_color="transparent")
        buttons.pack(anchor="w", pady=(14, 6))
        ctk.CTkButton(buttons, text=self.tr("schedule.save"), height=38, font=self.font(14, "bold"),
                      fg_color=DAWN, hover_color=DAWN_HOVER, text_color=NIGHT,
                      command=save_schedule).pack(side="left")
        ctk.CTkButton(buttons, text=self.tr("schedule.remove"), height=38, font=self.font(14),
                      fg_color=LINE, hover_color=PANEL, text_color=TEXT,
                      command=remove_schedule).pack(side="left", padx=10)
        result.pack(anchor="w", pady=(4, 10))
        ctk.CTkLabel(self.content, text=self.tr("schedule.notes"), font=self.font(13), text_color=MUTED,
                     wraplength=580, justify="left").pack(anchor="w")

    # ---------- History ----------
    def page_history(self):
        self.heading(self.tr("nav.history"))
        folder = app_dir() / "logs"
        runs = sorted(folder.glob("gachashift_*.log"), reverse=True) if folder.exists() else []
        if not runs:
            ctk.CTkLabel(self.content, text=self.tr("history.empty"), font=self.font(14),
                         text_color=MUTED).pack(anchor="w")
            return
        dates = {path.stem.replace("gachashift_", ""): path for path in runs}
        output = ctk.CTkTextbox(self.content, height=420, font=self.font(13), fg_color=PANEL,
                                text_color=TEXT, border_color=LINE, border_width=1)

        def show_run(date):
            output.configure(state="normal")
            output.delete("1.0", "end")
            output.insert("end", read_since(str(dates[date]), 0))
            output.see("end")  # the report is at the end
            output.configure(state="disabled")

        row = ctk.CTkFrame(self.content, fg_color="transparent")
        row.pack(anchor="w", pady=(4, 12))
        ctk.CTkLabel(row, text=self.tr("history.pick"), font=self.font(14), text_color=MUTED
                     ).pack(side="left", padx=(0, 12))
        picker = ctk.CTkOptionMenu(row, values=list(dates), command=show_run, width=150,
                                   font=self.font(14), fg_color=LINE, button_color=LINE,
                                   button_hover_color=PICKED, text_color=TEXT)
        picker.pack(side="left")
        output.pack(fill="both", expand=True)
        first = next(iter(dates))
        picker.set(first)
        show_run(first)

    # ---------- Calibration ----------
    def calibrate(self, gid, var):
        """Read the start button position from wherever the mouse rests after a countdown."""
        expected = launcher_of(gid, self.cfg["games"][gid])
        dialog = ctk.CTkToplevel(self, fg_color=NIGHT)
        dialog.title(self.tr("calib.title"))
        dialog.geometry("+40+40")
        dialog.attributes("-topmost", True)
        ctk.CTkLabel(dialog, text=self.tr("calib.explain", launcher=expected), font=self.font(14),
                     text_color=TEXT, wraplength=380, justify="left").pack(padx=20, pady=(18, 10))
        message = ctk.CTkLabel(dialog, text="", font=self.font(14, "bold"), text_color=DAWN,
                               wraplength=380, justify="left")
        message.pack(padx=20, pady=4)
        buttons = ctk.CTkFrame(dialog, fg_color="transparent")
        buttons.pack(padx=20, pady=(6, 18), fill="x")
        found = {}

        def use():
            var.set(f"{found['x']}, {found['y']}")
            dialog.destroy()

        use_button = ctk.CTkButton(buttons, text=self.tr("calib.use"), font=self.font(14, "bold"),
                                   fg_color=DAWN, hover_color=DAWN_HOVER, text_color=NIGHT, command=use)

        def countdown(n):
            if not dialog.winfo_exists():
                return
            if n > 0:
                message.configure(text=self.tr("calib.countdown", n=n), text_color=DAWN)
                dialog.after(1000, countdown, n - 1)
                return
            exe, x, y = window_under_cursor()
            if x is None:
                message.configure(text=self.tr("calib.wrong", exe=exe, expected=expected),
                                  text_color=FAIL_COLOR)
            elif exe.lower() != expected.lower():
                message.configure(text=self.tr("calib.wrong", exe=exe, expected=expected),
                                  text_color=FAIL_COLOR)
            else:
                found.update(x=x, y=y)
                message.configure(text=self.tr("calib.found", exe=exe, x=x, y=y), text_color=OK_COLOR)
                use_button.pack(side="right")
            start_button.configure(text=self.tr("calib.again"), state="normal")

        def start():
            use_button.pack_forget()
            start_button.configure(state="disabled")
            countdown(5)

        start_button = ctk.CTkButton(buttons, text=self.tr("calib.start"), font=self.font(14),
                                     fg_color=LINE, hover_color=PANEL, text_color=TEXT, command=start)
        start_button.pack(side="left")

    # ---------- General ----------
    def page_general(self):
        self.heading(self.tr("nav.general"))
        languages = {"English": "en", "中文": "zh"}

        box = self.section()
        box.grid_columnconfigure(1, weight=1)
        for row, key in enumerate(("language", "report_language")):
            ctk.CTkLabel(box, text=self.tr(f"general.{key}"), font=self.font(14), text_color=MUTED
                         ).grid(row=row, column=0, sticky="w", padx=18, pady=10)
            picker = ctk.CTkSegmentedButton(
                box, values=list(languages), font=self.font(13), selected_color=PICKED,
                selected_hover_color=PICKED, unselected_color=LINE, unselected_hover_color=LINE,
                fg_color=LINE, text_color=TEXT,
                command=lambda label, key=key: self.set_language(key, languages[label]))
            picker.set({v: k for k, v in languages.items()}[self.cfg.get(key, "en")])
            picker.grid(row=row, column=1, sticky="w", pady=10)

        box = self.section()
        ctk.CTkLabel(box, text=self.tr("general.while_running"), font=self.font(15, "bold"),
                     text_color=TEXT).pack(anchor="w", padx=18, pady=(14, 4))
        for key, label in (("mute", "general.mute"), ("dim_screen", "general.dim"),
                           ("shutdown", "general.shutdown")):
            var = ctk.BooleanVar(value=bool(self.cfg["options"].get(key)))
            ctk.CTkSwitch(box, text=self.tr(label), variable=var, font=self.font(14),
                          text_color=TEXT, progress_color=DAWN, fg_color=LINE, button_color=TEXT,
                          command=lambda key=key, var=var: self.set_option(key, var.get())
                          ).pack(anchor="w", padx=18, pady=6)
        ctk.CTkFrame(box, height=8, fg_color="transparent").pack()

        self.telegram_section()

    def set_language(self, key, value):
        self.cfg[key] = value
        if key == "language":
            self.build()  # every label changes, so rebuild the window
        else:
            self.changed()

    def set_option(self, key, value):
        self.cfg["options"][key] = value
        self.changed()

    def telegram_section(self):
        tg = self.cfg["telegram"]
        box = self.section()
        box.grid_columnconfigure(1, weight=1)
        enabled = ctk.BooleanVar(value=bool(tg.get("enabled")))

        def toggle():
            tg["enabled"] = enabled.get()
            self.changed()

        ctk.CTkSwitch(box, text=self.tr("general.telegram"), variable=enabled, command=toggle,
                      font=self.font(15, "bold"), text_color=TEXT, progress_color=DAWN,
                      fg_color=LINE, button_color=TEXT
                      ).grid(row=0, column=0, columnspan=3, sticky="w", padx=18, pady=(14, 8))

        entries = {}
        for row, (key, label, secret) in enumerate((("bot_token", "general.bot_token", True),
                                                    ("chat_id", "general.chat_id", False)), start=1):
            ctk.CTkLabel(box, text=self.tr(label), font=self.font(14), text_color=MUTED
                         ).grid(row=row, column=0, sticky="w", padx=18, pady=8)
            var = ctk.StringVar(value=tg.get(key, ""))
            entry = ctk.CTkEntry(box, textvariable=var, show="•" if secret else "", height=34,
                                 font=self.font(13), fg_color=NIGHT, border_color=LINE, text_color=TEXT)
            entry.grid(row=row, column=1, sticky="ew", pady=8)
            var.trace_add("write", lambda *_, key=key, var=var: (tg.__setitem__(key, var.get().strip()),
                                                                 self.changed()))
            entries[key] = entry

        shown = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(box, text=self.tr("general.show"), variable=shown, width=60,
                        font=self.font(13), text_color=TEXT, fg_color=DAWN, hover_color=DAWN_HOVER,
                        border_color=LINE, checkmark_color=NIGHT,
                        command=lambda: entries["bot_token"].configure(show="" if shown.get() else "•")
                        ).grid(row=1, column=2, padx=(8, 18))

        result = ctk.CTkLabel(box, text="", font=self.font(13), text_color=MUTED)
        result.grid(row=3, column=1, sticky="w", pady=(4, 14))
        ctk.CTkButton(box, text=self.tr("general.test_telegram"), height=34, font=self.font(13),
                      fg_color=LINE, hover_color=NIGHT, text_color=TEXT,
                      command=lambda: self.test_telegram(result)
                      ).grid(row=3, column=0, sticky="w", padx=18, pady=(4, 14))

    def test_telegram(self, result):
        tg = self.cfg["telegram"]
        if not tg.get("bot_token") or not tg.get("chat_id"):
            result.configure(text=self.tr("telegram.incomplete"), text_color=FAIL_COLOR)
            return
        try:
            r = requests.post(f"https://api.telegram.org/bot{tg['bot_token']}/sendMessage",
                              json={"chat_id": tg["chat_id"], "text": self.tr("telegram.test_text")},
                              timeout=15)
            ok = r.ok
        except requests.exceptions.RequestException:
            ok = False
        result.configure(text=self.tr("telegram.sent" if ok else "telegram.failed"),
                         text_color=OK_COLOR if ok else FAIL_COLOR)

    # ---------- Save and close ----------
    def save(self):
        save_config(self.cfg)
        self.saved_cfg = copy.deepcopy(self.cfg)
        problems = []
        for game_cls in GAMES:
            game_cfg = self.cfg["games"][game_cls.id]
            if game_cfg.get("enabled"):
                missing = missing_items(game_cls.id, game_cfg)
                if missing:
                    labels = ", ".join(self.tr(f"f.{key}") for key in missing)
                    problems.append(f"{game_name(game_cls.id, self.lang)} ({labels})")
        if problems:
            self.status.configure(text=self.tr("save.missing", items="; ".join(problems)),
                                  text_color=FAIL_COLOR)
        else:
            self.status.configure(text=self.tr("saved"), text_color=OK_COLOR)
        if self.page == "home":
            self.show("home")

    def on_close(self):
        if self.run_handle is not None:
            self.show("test")
            return  # a test run is still going; closing would hide its output
        if self.cfg != self.saved_cfg:
            answer = messagebox.askyesnocancel(self.tr("quit.title"), self.tr("quit.ask"))
            if answer is None:
                return
            if answer:
                self.save()
        self.destroy()


def main():
    GachashiftApp().mainloop()


if __name__ == "__main__":
    main()