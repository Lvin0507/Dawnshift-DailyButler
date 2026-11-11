"""The main window: sidebar, pages, the save bar, and the background painted under it all."""

import copy
import ctypes
import datetime
import json
import os

import psutil
import threading

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import (QApplication, QButtonGroup, QFrame, QHBoxLayout, QMessageBox,
                               QScrollArea, QVBoxLayout, QWidget)

from .. import __version__
from ..config import app_dir, load_config, save_config
from ..updates import newer_release
from ..games import GAMES
from ..i18n import t
from ..runner import running_file
from ..system import gamma_marker, log_size, read_since, restore_gamma, stop_file
from ..winutil import (missing_items, plain_name, process_finished, scheduled_time, self_command,
                       start_elevated)
from . import appearance, games, general, history, home, run, schedule, theme
from .widgets import button, label, restyle, shadowed

def veil_strength(pixmap):
    """How much to darken a background image: 60 for a dark picture, up to 190 for a white one."""
    if pixmap.isNull():
        return 0
    image = pixmap.toImage().scaled(24, 24)
    total = 0
    for x in range(24):
        for y in range(24):
            c = image.pixelColor(x, y)
            total += 0.2126 * c.red() + 0.7152 * c.green() + 0.0722 * c.blue()
    brightness = total / (24 * 24 * 255)
    return int(60 + 130 * brightness)


PAGES = ["home", "games", "run", "schedule", "history", "general", "appearance"]


class MainWindow(QWidget):
    update_found = Signal(str, str)  # version, release page; emitted from the checking thread

    def __init__(self):
        super().__init__()
        self.update_info = None  # (version, url) once a newer release is known
        self.cfg = load_config()
        self.saved_cfg = copy.deepcopy(self.cfg)
        self.current_game = GAMES[0].id
        self.page = "home"
        self.schedule = scheduled_time()   # "HH:MM" or None; asking Windows is slow, so cache it
        self._background = (None, None, 0)  # (path, QPixmap, veil alpha) cache
        # a run started from the Run page; it outlives page switches and language changes
        self.test_game = GAMES[0].id
        self.run_handle = None
        self.run_log = None
        self.run_start_offset = self.run_offset = 0
        self.run_output = self.run_status = None
        self.run_buttons = []
        self.stopping = False
        self.run_timer = QTimer(self)
        self.run_timer.timeout.connect(self.poll_run)
        if gamma_marker().exists() and self.running_info() is None:
            try:
                restore_gamma()  # an earlier run ended without putting the screen back
            except Exception:
                pass
        self.setWindowTitle("Gachashift")
        self.resize(1000, 700)
        self.setMinimumSize(860, 560)
        self.build()
        self.watch_timer = QTimer(self)  # shows Stop whenever any run is going on
        self.watch_timer.timeout.connect(self.watch_runs)
        self.watch_timer.start(2000)
        self.update_found.connect(self.on_update_found)
        if self.cfg["options"].get("check_updates", True):
            # in the background, so a slow or missing connection never delays the window
            threading.Thread(target=self.check_updates, daemon=True).start()

    def check_updates(self):
        found = newer_release()
        if found:
            self.update_found.emit(*found)

    def on_update_found(self, version, url):
        self.update_info = (version, url)
        if self.page == "home":
            self.show_page("home")

    # ---------- helpers ----------
    @property
    def lang(self):
        return self.cfg.get("language", "en")

    def tr(self, key, **kwargs):
        return t(self.lang, key, **kwargs)

    def set_status(self, text, kind=""):
        self.status.setText(text)
        self.status.setProperty("kind", kind)
        restyle(self.status)

    def changed(self):
        if getattr(self, "stop_button", None) is not None and self.stop_button.isVisible():
            return  # the bar is showing that a run is going on
        dirty = self.cfg != self.saved_cfg
        self.set_status(self.tr("unsaved") if dirty else "")

    def set_game_value(self, gid, key, value):
        self.cfg["games"][gid][key] = value
        self.changed()

    def set_option(self, key, value):
        self.cfg["options"][key] = value
        self.changed()

    def set_language(self, key, value):
        self.cfg[key] = value
        if key == "language":
            self.build()  # every label changes
        else:
            self.changed()

    def open_game(self, gid):
        self.current_game = gid
        self.show_page("games")

    def setup_steps(self):
        """The first-run checklist, worked out from the settings themselves."""
        enabled = [g.id for g in GAMES if self.cfg["games"][g.id].get("enabled")]
        tg = self.cfg["telegram"]
        setup = self.cfg.setdefault("setup", {"test_run_done": False, "skip_telegram": False})
        not_ready = [g for g in enabled if missing_items(g, self.cfg["games"][g])]

        def skip_telegram():
            setup["skip_telegram"] = True
            self.changed()
            self.show_page("home")

        return [
            {"key": "step1", "done": bool(enabled), "go": lambda: None},
            {"key": "step2", "done": bool(enabled) and not not_ready,
             "go": lambda: self.open_game(not_ready[0] if not_ready else (enabled or ["endfield"])[0])},
            # one finished run from the Run page is enough, however many games are turned on
            {"key": "step3", "done": bool(setup.get("test_run_done")), "go": lambda: self.show_page("run")},
            {"key": "step4", "done": bool(setup.get("skip_telegram")) or bool(
                tg.get("enabled") and tg.get("bot_token") and tg.get("chat_id")),
             "go": lambda: self.show_page("general"), "skip": skip_telegram},
            {"key": "step5", "done": bool(self.schedule), "go": lambda: self.show_page("schedule")},
        ]

    # ---------- appearance ----------
    def apply_theme(self):
        theme.current.load(self.cfg["appearance"])
        QApplication.instance().setStyleSheet(theme.stylesheet(self.lang))
        self.update()
        self.changed()

    def paintEvent(self, _):
        """The background: a plain colour, or the user's image cropped to fill the window
        with a light veil so text on the panels stays readable."""
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(theme.BG))
        path = theme.current.background
        if path and os.path.exists(path):
            if self._background[0] != path:
                pixmap = QPixmap(path)
                self._background = (path, pixmap, veil_strength(pixmap))
            pixmap = self._background[1]
            if not pixmap.isNull():
                p.setRenderHint(QPainter.SmoothPixmapTransform)
                scaled = pixmap.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                x = (scaled.width() - self.width()) // 2
                y = (scaled.height() - self.height()) // 2
                p.drawPixmap(0, 0, scaled, x, y, self.width(), self.height())
                # brighter images get a stronger veil, so white text outside the panels
                # (page titles, the save status) stays readable on any picture
                veil = QColor(theme.BG)
                veil.setAlpha(self._background[2])
                p.fillRect(self.rect(), veil)

    # ---------- layout ----------
    def build(self):
        """(Re)build the whole window, e.g. after the language changes."""
        old = self.layout()
        if old:
            QWidget().setLayout(old)  # detach the old layout and its widgets
        theme.current.load(self.cfg["appearance"])
        QApplication.instance().setStyleSheet(theme.stylesheet(self.lang))

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        side = QFrame()
        side.setObjectName("sidebar")
        side.setFixedWidth(196)
        col = QVBoxLayout(side)
        col.setContentsMargins(12, 22, 12, 16)
        col.setSpacing(4)
        self.nav = {}
        group = QButtonGroup(self)
        for name in PAGES:
            b = button(self.tr(f"nav.{name}"), "nav", lambda _=False, n=name: self.show_page(n))
            b.setCheckable(True)
            group.addButton(b)
            col.addWidget(b)
            self.nav[name] = b
        col.addStretch()
        version = label(f"Gachashift v{__version__}", "hint")
        version.setContentsMargins(14, 0, 0, 0)
        col.addWidget(version)
        root.addWidget(side)

        right = QVBoxLayout()
        right.setContentsMargins(28, 22, 20, 14)
        right.setSpacing(10)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.viewport().setAutoFillBackground(False)
        right.addWidget(self.scroll, 1)

        bar = QHBoxLayout()
        self.status = shadowed(label("", "status"))
        bar.addWidget(self.status, 1)
        self.stop_button = button(self.tr("bar.stop"), "danger", self.stop_run)
        self.stop_button.hide()
        bar.addWidget(self.stop_button)
        bar.addWidget(button(self.tr("save"), "primary", self.save))
        right.addLayout(bar)
        root.addLayout(right, 1)
        self.show_page(self.page)

    def show_page(self, name):
        self.page = name
        self.nav[name].setChecked(True)
        builders = {"home": home.build, "games": games.build, "run": run.build,
                    "schedule": schedule.build, "history": history.build, "general": general.build,
                    "appearance": appearance.build}
        self.run_output = self.run_status = None  # the Run page recreates these
        self.run_buttons = []
        page = builders[name](self) if name in builders else self.placeholder(name)
        self.scroll.setWidget(page)
        self.changed()
        self.watch_runs()

    def placeholder(self, name):
        page = QWidget()
        col = QVBoxLayout(page)
        col.setContentsMargins(0, 0, 0, 0)
        col.addWidget(shadowed(label(self.tr(f"nav.{name}"), "h1")))
        col.addWidget(label(self.tr("soon"), "muted", wrap=True))
        col.addStretch()
        return page

    # ---------- running ----------
    def run_busy(self):
        return self.run_handle is not None or self.running_info() is not None

    def start_run(self, *options):
        if self.cfg != self.saved_cfg:
            self.run_status.setText(self.tr("test.unsaved"))
            return
        # the run writes everything it prints to today's log; the app shows that file as it grows
        self.run_log = str(app_dir() / "logs" / f"gachashift_{datetime.date.today():%Y-%m-%d}.log")
        self.run_start_offset = self.run_offset = log_size(self.run_log)
        program, arguments = self_command(*options)
        handle = start_elevated(arguments, program)
        if not handle:
            self.run_status.setText(self.tr("test.denied"))
            return
        self.run_handle = handle
        for b in self.run_buttons:
            b.setEnabled(False)
        self.run_status.setText(self.tr("test.running"))
        self.run_output.clear()
        self.run_timer.start(700)

    def poll_run(self):
        finished = process_finished(self.run_handle)
        new = read_since(self.run_log, self.run_offset)
        self.run_offset = log_size(self.run_log)
        if new and self.run_output is not None:
            self.run_output.moveCursor(self.run_output.textCursor().MoveOperation.End)
            self.run_output.insertPlainText(new)
            self.run_output.verticalScrollBar().setValue(self.run_output.verticalScrollBar().maximum())
        if not finished:
            return
        self.run_timer.stop()
        ctypes.windll.kernel32.CloseHandle(self.run_handle)
        self.run_handle = None
        # one finished run completes the setup checklist's test step
        for cfg in (self.cfg, self.saved_cfg):
            cfg.setdefault("setup", {})["test_run_done"] = True
        save_config(self.saved_cfg)
        for b in self.run_buttons:
            b.setEnabled(True)
        if self.run_status is not None:
            self.run_status.setText(self.tr("test.done"))

    @staticmethod
    def running_info():
        """Details of a run in progress (from the app or the schedule), or None."""
        try:
            info = json.loads(running_file().read_text())
        except (OSError, ValueError):
            return None
        return info if psutil.pid_exists(info.get("pid", -1)) else None

    def watch_runs(self):
        running = self.running_info() is not None
        self.stop_button.setVisible(running)
        if running:
            self.stop_button.setEnabled(not self.stopping)
            self.set_status(self.tr("bar.stopping" if self.stopping else "bar.running"), "accent")
        elif self.stopping:
            self.stopping = False
            self.changed()

    def stop_run(self):
        stop_file().touch()  # the run checks for this file every second
        self.stopping = True
        self.watch_runs()

    # ---------- save and close ----------
    def save(self):
        save_config(self.cfg)
        self.saved_cfg = copy.deepcopy(self.cfg)
        problems = []
        for game_cls in GAMES:
            game_cfg = self.cfg["games"][game_cls.id]
            if game_cfg.get("enabled"):
                missing = missing_items(game_cls.id, game_cfg)
                if missing:
                    names = ", ".join(self.tr(f"f.{key}") for key in missing)
                    problems.append(f"{plain_name(game_cls.id, self.lang)} ({names})")
        if self.page == "home":
            self.show_page("home")  # statuses may have changed
        if problems:
            self.set_status(self.tr("save.missing", items="; ".join(problems)), "fail")
        else:
            self.set_status(self.tr("saved"), "ok")

    def closeEvent(self, event):
        if self.run_handle is not None:
            self.show_page("run")  # a run started here is still going; keep its output visible
            event.ignore()
            return
        if self.cfg != self.saved_cfg:
            answer = QMessageBox.question(self, self.tr("quit.title"), self.tr("quit.ask"),
                                          QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            if answer == QMessageBox.Cancel:
                event.ignore()
                return
            if answer == QMessageBox.Yes:
                self.save()
        event.accept()
