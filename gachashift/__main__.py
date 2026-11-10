"""Command line entry point:

    python -m gachashift                      # scheduled run (asks first if someone is at the PC)
    python -m gachashift --no-shutdown        # run everything now, keep the PC on
    python -m gachashift --only zzz           # one game, no Telegram, no shutdown
    python -m gachashift --dry-run-endfield logs\\go-service_....log
"""

import argparse
import datetime
import sys
import time

from .config import app_dir, load_config
from .games import GAMES_BY_ID
from .report import render_game
from .runner import run_all
from .system import read_since


class _Tee:
    """Send everything printed to both the console and a dated log file, so runs started
    by Task Scheduler (where nobody sees the console) can still be diagnosed."""

    def __init__(self, stream, path):
        self.stream = stream
        self.file = open(path, "a", encoding="utf-8")

    def write(self, text):
        if self.stream:
            self.stream.write(text)
        self.file.write(text)
        self.file.flush()

    def flush(self):
        if self.stream:
            self.stream.flush()
        self.file.flush()


def start_run_log(keep_days=14):
    folder = app_dir() / "logs"
    folder.mkdir(exist_ok=True)
    path = folder / f"gachashift_{datetime.date.today():%Y-%m-%d}.log"
    sys.stdout = _Tee(sys.stdout, path)
    sys.stderr = _Tee(sys.stderr, path)
    cutoff = time.time() - keep_days * 86400
    for old in folder.glob("gachashift_*.log"):
        if old.stat().st_mtime < cutoff:
            old.unlink()


def main():
    p = argparse.ArgumentParser(prog="gachashift", description="Gachashift - daily game butler")
    p.add_argument("--no-shutdown", action="store_true", help="run now and keep the PC on afterwards")
    p.add_argument("--only", choices=sorted(GAMES_BY_ID), help="run one game; no Telegram, no shutdown")
    p.add_argument("--dry-run-endfield", metavar="LOG", help="parse a MaaEnd log and print the report")
    p.add_argument("--lang", choices=["en", "zh"], help="report language for this run")
    args = p.parse_args()

    start_run_log()
    cfg = load_config()
    if args.lang:
        cfg["report_language"] = args.lang

    if args.dry_run_endfield:
        from .games.endfield import parse_endfield_log
        rep = parse_endfield_log(read_since(args.dry_run_endfield, 0),
                                 GAMES_BY_ID["endfield"](cfg["games"]["endfield"]).new_report())
        print(render_game(rep, cfg["report_language"]))
        return

    if args.only:
        run_all(cfg, only=args.only, allow_shutdown=False, send=False)
    elif args.no_shutdown:
        run_all(cfg, allow_shutdown=False)  # started by hand, so no need to ask
    else:
        run_all(cfg, ask_first=True)        # the scheduled morning run


if __name__ == "__main__":
    main()
