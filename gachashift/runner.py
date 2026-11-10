"""Runs the enabled games in order, collects their reports and sends them.
Used by both the command line (python -m gachashift) and the App."""

import datetime

from . import report as R
from .config import load_config
from .games import GAMES, GAMES_BY_ID
from .i18n import game_name, t
from .system import QuietMode, shutdown, ts, wait_for_reset, wait_for_unlock


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
    except Exception as e:
        print(f"[{ts()}] {game.id} failed: {e}")
        rep.note("note.error", error=f"{type(e).__name__}: {e}")
        return rep


def run_games(cfg, only, lang, opts, log):
    """Run every game that is enabled and due today (or just `only`) and return their reports."""
    reports = []
    with QuietMode(mute=opts.get("mute", True), dim=opts.get("dim_screen", False)):
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
            reports.append(run_game(game_cls, game_cfg, lang, wait_reset=not only))
    return reports


def run_all(cfg=None, only=None, allow_shutdown=True, send=True, log=print):
    """Run the games, then send the report and (optionally) shut down."""
    cfg = cfg or load_config()
    lang = cfg.get("report_language", "en")
    opts = cfg["options"]
    # On the lock screen no tool can see or click anything, so report it instead of hanging
    if not only and not wait_for_unlock():
        rep = R.GameReport("system")
        rep.note("note.locked")
        reports = [rep]
    else:
        reports = run_games(cfg, only, lang, opts, log)

    text = R.render_all(reports, lang)
    log("\n" + text + "\n")
    tg = cfg["telegram"]
    if send and tg.get("enabled") and tg.get("bot_token") and tg.get("chat_id") and reports:
        R.send_telegram(tg["bot_token"], tg["chat_id"], reports, lang)
    if allow_shutdown and opts.get("shutdown", True):
        shutdown()
    return reports