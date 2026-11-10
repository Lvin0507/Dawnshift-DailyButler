"""Arknights via MAA (PC client). MAA starts the game but never exits on its own, so we
watch its log for the completion message and then close it."""

import os
import re
import subprocess
import time

from .. import report as R
from ..system import StopRequested, kill, log_size, pause, process_running, read_since, ts
from .base import Game

DONE_MARKERS = ["任务已全部完成"]


def parse_maa_log(text, reason, rep):
    started = re.findall(r"开始任务: (\S+)", text)
    finished = set(re.findall(r"完成任务: (\S+)", text))
    recruits = len(re.findall(r"已确认招募", text))
    if not started:
        rep.note("note.no_records")
    for name in dict.fromkeys(started):  # keep order, drop repeats
        detail = f"x{recruits}" if name == "自动公招" and name in finished else ""
        # a task cut short by a stop didn't fail; it just didn't get to finish
        unfinished = R.SKIPPED if reason == "stopped" else R.FAIL
        rep.add(name, R.OK if name in finished else unfinished, detail)
    if reason not in ("done", "stopped"):
        rep.note("note.no_done_marker", reason=reason)
    return rep


class Arknights(Game):
    id = "arknights"
    required = ("maa_path", "maa_log")

    def run(self, timeout=1800):
        path, log = self.cfg["maa_path"], self.cfg["maa_log"]
        offset = log_size(log)
        reason, missing, stop = "timeout", 0, None
        try:
            print(f"[{ts()}] starting {path}")
            subprocess.Popen([path], cwd=os.path.dirname(path))
            start = time.time()
            while time.time() - start < timeout:
                pause(15)
                if any(m in read_since(log, offset) for m in DONE_MARKERS):
                    reason = "done"
                    break
                # MAA disappears briefly while self-updating, so require two misses in a row
                missing = 0 if process_running("MAA.exe") else missing + 1
                if missing >= 2:
                    reason = "exited"
                    break
            pause(10)  # let MAA finish writing its log
        except StopRequested as e:
            stop, reason = e, "stopped"
        finally:
            # the Arknights PC client can bring up GRYPHLINK too
            kill(["MAA.exe", self.cfg.get("game_exe") or "Arknights.exe", "Gryphlink.exe"])
            time.sleep(3)
        rep = parse_maa_log(read_since(log, offset), reason, self.new_report())
        if stop:
            stop.report = rep
            raise stop
        return rep
