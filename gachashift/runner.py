"""Runs the enabled games in order, collects their reports and sends them.
Used by both the command line (python -m gachashift) and the App."""

import datetime
import json
import os

from . import report as R
from .config import app_dir, load_config
from .games import GAMES
from .i18n import game_name, t
from .system import (QuietMode, StopRequested, clear_stop, seconds_since_input, shutdown, ts,
                     wait_for_reset, wait_for_unlock)

ACTIVE_SECONDS = 120  # someone used the PC this recently: ask before taking over


def running_file():
    """Present while a run is in progress, so the App can show a Stop button."""
    return app_dir() / "running.json"


def due_today(game_cfg):
    return game_cfg.get("enabled") and datetime.datetime.today().weekday() in game_cfg.get("days", [])


def run_game(game_cls, game_cfg, lang, wait_reset=True):
    """Run one game, turning any unexpected error into a report instead of a crash."""
    game = game_cls(game_cfg)
    rep = R.GameReport(game.id)
    missing = game.missing_settings()
    if missing:
        rep.note("note.error", error="missing settings: " + ", ".join(missing))
        return rep
    try:
        if wait_reset and game.reset and game_cfg.get("wait_for_reset", True):
            offset, hour = game.reset
            wait_for_reset(offset, hour, on_wait=lambda m: print(
                f"[{ts()}] " + t(lang, "log.wait_reset", game=game_name(game.id, lang), minutes=m)))
        return game.run()
    except StopRequested:
        raise  # not an error: the whole run stops
    except Exception as e:
        print(f"[{ts()}] {game.id} failed: {e}")
        rep.note("note.error", error=f"{type(e).__name__}: {e}")
        return rep


def run_games(cfg, only, lang, opts, log, dim=False):
    """Run every game that is enabled and due today (or just `only`) and return their reports."""
    reports = []
    with QuietMode(mute=opts.get("mute", True), dim=dim,
                   dim_level=opts.get("dim_level", 30) / 100):
        for game_cls in GAMES:
            gid = game_cls.id
            game_cfg = cfg["games"].get(gid, {})
            if only:
                if gid != only:
                    continue
            elif not game_cfg.get("enabled"):
                log(t(lang, "log.skip_off", game=game_name(gid, lang)))
                continue
            elif not due_today(game_cfg):
                log(t(lang, "log.skip_day", game=game_name(gid, lang)))
                continue
            # a single-game test run shouldn't sit waiting for a reset
            try:
                reports.append(run_game(game_cls, game_cfg, lang, wait_reset=not only))
            except StopRequested as stop:
                # the game closed its own tool and game on the way out and, where it could,
                # attached what it finished before the stop; keep that and earlier reports
                if getattr(stop, "report", None):
                    reports.append(stop.report)
                reports.append(stopped_report())
                return reports, True
    return reports, False


def stopped_report():
    rep = R.GameReport("system")
    rep.note("note.stopped")
    return rep


def run_all(cfg=None, only=None, allow_shutdown=True, send=True, ask_first=False, log=print):
    """Run the games, then send the report and (optionally) shut down.
    ask_first: for scheduled runs, ask before starting if someone is using the PC."""
    cfg = cfg or load_config()
    lang = cfg.get("report_language", "en")
    opts = cfg["options"]
    clear_stop()  # an old request must not stop this run

    if ask_first and seconds_since_input() < ACTIVE_SECONDS:
        from .prompt import ask_before_start
        if not ask_before_start(lang):
            log(f"[{ts()}] " + t(lang, "log.skipped_by_user"))
            return []

    reports, stopped = [], False
    running_file().write_text(json.dumps({"pid": os.getpid(), "started": ts(), "only": only}))
    try:
        # On the lock screen no tool can see or click anything, so report it instead of hanging
        if not only and not wait_for_unlock():
            rep = R.GameReport("system")
            rep.note("note.locked")
            reports.append(rep)
        else:
            # only the scheduled run darkens the screen; someone is watching any other run
            reports, stopped = run_games(cfg, only, lang, opts, log,
                                         dim=ask_first and opts.get("dim_screen", False))
    except StopRequested:  # stopped while waiting for the lock screen to clear
        stopped = True
        reports.append(stopped_report())
    finally:
        try:
            running_file().unlink()
        except FileNotFoundError:
            pass
        clear_stop()

    text = R.render_all(reports, lang)
    log("\n" + text + "\n")
    tg = cfg["telegram"]
    if send and tg.get("enabled") and tg.get("bot_token") and tg.get("chat_id") and reports:
        R.send_telegram(tg["bot_token"], tg["chat_id"], reports, lang)
    dc = cfg.get("discord", {})
    if send and dc.get("enabled") and dc.get("webhook_url") and reports:
        R.send_discord(dc["webhook_url"], reports, lang)
    if allow_shutdown and opts.get("shutdown", True) and not stopped:
        shutdown()
    return reports
