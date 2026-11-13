"""Wuthering Waves via ok-ww (-t GardenTask -e).

ok-ww exits by itself after a successful run but stays open after a task exception, so we also
watch its log for the end of the task and always close it ourselves. The Steam build opens
Kuro's launcher (launcher_main.exe), which needs a click on its start button, so we open the
game through Steam with admin rights, click the button, and hand the running game to ok-ww."""

import os
import re
import subprocess
import time

from .. import report as R
from ..system import (StopRequested, kill, kill_processes, launch_and_click, log_size, pause,
                      processes_in, read_since, restart_steam_if_running, ts)
from .base import Game

GAME_EXE = "Client-Win64-Shipping.exe"
DONE = "乐园任务完成"
FAILED = "exception stopped"
# progress appears as "本周游历值_1.00, 4400/6000" during a run, or "当前乐园进度：[6000_1.00]" when full
PROGRESS = re.compile(r"本周游历值_[\d.]+, (\d+/\d+|已达到上限)|当前乐园进度：\[(\d+)_")
EXCEPTION = re.compile(r"^Exception: (.+)$", re.M)


def parse_ww_log(text, rep):
    """Decide from ok-ww's own completion and failure lines, not loose keywords."""
    if not text.strip():
        rep.add("garden", R.WARN)
        rep.note("note.no_records")
        return rep
    progress = PROGRESS.findall(text)
    detail = next((a or b for a, b in reversed(progress) if a or b), "")
    if detail in ("已达到上限", "6000"):
        detail = "max"
    if DONE in text:
        rep.add("garden", R.OK, detail)
    elif FAILED in text:
        reasons = EXCEPTION.findall(text)
        rep.add("garden", R.FAIL, reasons[-1].strip() if reasons else "")
    elif "game exited" in text:
        rep.add("garden", R.FAIL, "game closed")
    else:
        rep.add("garden", R.WARN, detail)
    return rep


class WutheringWaves(Game):
    id = "wuthering"
    required = ("okww_path", "log_path")

    def _open_through_steam(self):
        restart_steam_if_running()  # so the game inherits our admin rights
        return launch_and_click(
            lambda: os.startfile(f"steam://rungameid/{self.cfg.get('steam_appid') or '3513350'}"),
            self.cfg.get("launcher_exe") or "launcher_main.exe", self.cfg["start_button"],
            GAME_EXE, wait_after=60)

    def run(self, timeout=5400):
        path, log = self.cfg["okww_path"], self.cfg["log_path"]
        folder = os.path.dirname(path)
        offset = log_size(log)
        start, stop = time.time(), None
        try:
            if self.cfg.get("steam_client") and not self._open_through_steam():
                rep = self.new_report()
                rep.add("garden", R.FAIL)
                rep.note("note.not_started", hint="hint.steam")
                return rep
            print(f"[{ts()}] starting {path}")
            subprocess.Popen([path, "-t", self.cfg.get("task") or "GardenTask", "-e"], cwd=folder)
            pause(15)
            ended_at = None
            while processes_in(folder) and time.time() - start < timeout:
                pause(10)
                text = read_since(log, offset)
                if ended_at is None and (DONE in text or FAILED in text):
                    ended_at = time.time()
                # give ok-ww a minute to exit on its own after the task ends, then close it
                if ended_at and time.time() - ended_at > 60:
                    break
        except StopRequested as e:
            stop = e
        finally:
            # ok-ww stays open after a failure; never leave it running for the next game
            kill_processes(processes_in(folder))
            kill([GAME_EXE, self.cfg.get("launcher_exe") if self.cfg.get("steam_client") else None])
            time.sleep(5)
        text = read_since(log, offset)
        rep = parse_ww_log(text, self.new_report())
        if stop:
            if DONE not in text and FAILED not in text:
                rep = self.new_report()
                rep.add("garden", R.SKIPPED)
            stop.report = rep
            raise stop
        return rep
