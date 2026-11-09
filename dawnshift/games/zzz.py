"""Zenless Zone Zero via OneDragon.

Official client: OneDragon opens the game itself (`-o -c`), which is its documented way.
Steam client: the game refuses to start unless Steam launches it, and Steam opens the
HoYoverse launcher (HYP.exe) that needs a click, so we open the game first and then hand
the running game to OneDragon. Either way OneDragon exits by itself when done."""

import os
import re
import subprocess
import time

from .. import report as R
from ..system import (kill, kill_processes, launch_and_click, log_size, process_running,
                      processes_in, read_since, restart_steam_if_running, ts)
from .base import Game, minutes_since

GAME_EXE = "ZenlessZoneZero.exe"
SERVER_UTC = {"asia": 8, "america": -5, "europe": 1}
LINE = re.compile(r"指令\[ (.+?) \] (?:节点 .*?返回状态 (.*)|执行成功 返回状态 (.*)|执行失败 返回状态 (.*))$")


def parse_od_log(text, rep, minutes):
    """OneDragon logs every operation as 指令[ name ]. The apps of the one-dragon group start
    right after a line from 指令[ 执行应用组 ... ]; anything inside an app (Return to World,
    Teleport, ...) is a sub-step and is ignored. Disabled apps are not reported."""
    results, expect_app, current, overall = {}, False, None, None
    for line in text.splitlines():
        m = LINE.search(line.strip())
        if not m:
            continue
        name, node, ok, fail = m.groups()
        if name.startswith("执行应用组"):
            expect_app = True
            if node and node.startswith("应用已完成 "):
                results[node.split(" ", 1)[1]] = (R.ALREADY, "")
            continue
        if name == "一条龙":
            overall = ("ok", ok) if ok is not None else (("fail", fail) if fail is not None else overall)
            continue
        if expect_app and node is not None:
            current, expect_app = name, False
            results.setdefault(current, (R.WARN, ""))
        elif name == current and ok is not None:
            results[current] = (R.OK, "")
        elif name == current and fail is not None:
            results[current] = (R.FAIL, fail)

    if not results and overall is None:
        rep.note("note.no_records")
        return rep
    for app, (status, detail) in results.items():
        rep.add(app, status, detail)
    if overall and overall[0] == "ok":
        rep.note("note.finished", minutes=minutes)
    elif overall:
        rep.note("note.interrupted", reason=overall[1])
    else:
        rep.note("note.no_done_marker", reason="no end record")
    return rep


class ZenlessZoneZero(Game):
    id = "zzz"
    required = ("od_dir",)

    @property
    def reset(self):
        return (SERVER_UTC.get(self.cfg.get("server"), 8), 4)

    def _open_through_steam(self):
        restart_steam_if_running()
        return launch_and_click(
            lambda: os.startfile(f"steam://rungameid/{self.cfg['steam_appid']}"),
            self.cfg["launcher_exe"], self.cfg["start_button"], GAME_EXE, wait_after=60)

    def run(self, timeout=7200):
        od_dir = self.cfg["od_dir"]
        od_exe = os.path.join(od_dir, "OneDragon-Launcher.exe")
        log = os.path.join(od_dir, ".log", "log.txt")
        steam = self.cfg.get("client") == "steam"
        offset = log_size(log)
        rep = self.new_report()
        start, reason, saw_od, saw_game, game_gone = time.time(), "timeout", False, False, 0
        try:
            if steam:
                if not self._open_through_steam():
                    rep.add("一条龙", R.FAIL)
                    rep.note("note.not_started", hint="hint.steam")
                    return rep
                saw_game = True
            print(f"[{ts()}] starting {od_exe} -o -c")
            subprocess.Popen([od_exe, "-o", "-c"], cwd=od_dir,
                             creationflags=subprocess.CREATE_NEW_CONSOLE)
            while time.time() - start < timeout:
                time.sleep(15)
                procs = processes_in(od_dir)
                saw_od = saw_od or bool(procs)
                if process_running(GAME_EXE):
                    saw_game, game_gone = True, 0
                elif saw_game:
                    game_gone += 1
                if saw_od and not procs:
                    reason = "exited"
                    break
                if game_gone >= 2:  # -c closes the game at the end
                    reason = "game_closed"
                    break
        finally:
            kill_processes(processes_in(od_dir))
            kill([GAME_EXE, self.cfg.get("launcher_exe") if steam else None])
            time.sleep(3)
        print(f"[{ts()}] ZZZ ended: {reason}, OneDragon seen={saw_od}, game seen={saw_game}")
        rep = parse_od_log(read_since(log, offset), rep, minutes_since(start))
        if not rep.tasks:
            rep.note("note.no_done_marker", reason=f"{reason}, OneDragon seen={saw_od}")
        return rep