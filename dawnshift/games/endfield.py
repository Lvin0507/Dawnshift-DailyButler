"""Arknights: Endfield via MaaEnd. MaaEnd launches the game itself and exits when done."""

import datetime
import glob
import json
import os
import shutil
import subprocess
import time

from .. import report as R
from ..config import app_dir
from ..system import kill, process_running, read_since, ts
from .base import Game

TASKS = ["LaunchGamePC", "StashBackpackMain", "DijiangRewards", "OutpostTradingSchedule",
         "AutoStockStapleSchedule", "AutoStockpileMain", "DeliveryJobsMain", "AutoSellMain",
         "EnvironmentMonitoringMain", "TrialOfSwordmancyMain", "SeizeDeliveryJobs",
         "VisitFriendsMain", "CreditShoppingMain", "GiftOperatorMain", "DailyRewardStart",
         "MXU_KILLPROC"]
ALIASES = {"SeizeDeliveryJobsMain": "SeizeDeliveryJobs",
           "SeizeDeliveryJobsCheckOngoingJob": "SeizeDeliveryJobs",
           "SellProductSchedule": "AutoSellMain"}
DELIVERY_TARGET = 3


def parse_endfield_log(text, rep):
    """Fill `rep` from MaaEnd's go-service.log (one JSON object per line).
    A run starts at "Checking aspect ratio before task execution"; any "Task failed" line
    marks it failed (some failures are only logged at debug level)."""
    runs, fails = {}, {}
    launch = None
    deliveries = delivery_activity = 0
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
        key = ALIASES.get(entry, entry)
        if entry and msg == "Checking aspect ratio before task execution":
            runs[key] = runs.get(key, 0) + 1
            current = key
        elif entry and "Task failed" in msg:
            fails[key] = fails.get(key, 0) + 1
        elif (current == "SeizeDeliveryJobs" and msg == "item quantity added from recognition"
              and rec.get("item_id") == "item_spaceship_credit"):
            deliveries += 1
        if current == "SeizeDeliveryJobs" and rec.get("component") in (
                "SeizeDeliveryJobs", "AutoDeliveryResolveDestinationAction"):
            delivery_activity += 1

    if launch is None and not runs:
        rep.note("note.no_records")
        return rep
    rep.add("LaunchGamePC", {True: R.OK, False: R.FAIL, None: R.SKIPPED}[launch])
    for key in TASKS[1:]:
        n_runs, n_fails = runs.get(key, 0), fails.get(key, 0)
        if key == "SeizeDeliveryJobs" and n_runs:
            detail = f"{deliveries}/{DELIVERY_TARGET}"
            if n_fails:
                rep.add(key, R.FAIL, detail)
            elif deliveries >= DELIVERY_TARGET:
                rep.add(key, R.OK, detail)
            elif deliveries == 0 and delivery_activity == 0:
                rep.add(key, R.NOTHING)
            else:
                rep.add(key, R.PARTIAL, detail)
            continue
        if n_runs == 0:
            rep.add(key, R.SKIPPED)
        elif n_fails:
            rep.add(key, R.FAIL, f"{n_fails}/{n_runs}" if n_runs > 1 else "")
        else:
            rep.add(key, R.OK)
    for key in runs:
        if key not in TASKS:
            rep.add(key, R.FAIL if fails.get(key) else R.OK, new=True)
    return rep


def archive_log(log_dir, keep_days=14):
    """MaaEnd overwrites go-service.log on every launch, so keep a dated copy."""
    try:
        archive = app_dir() / "logs"
        archive.mkdir(exist_ok=True)
        src = os.path.join(log_dir, "go-service.log")
        if os.path.exists(src):
            stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
            shutil.copy2(src, archive / f"go-service_{stamp}.log")
        cutoff = time.time() - keep_days * 86400
        for f in glob.glob(str(archive / "go-service_*.log")):
            if os.path.getmtime(f) < cutoff:
                os.remove(f)
    except OSError as e:
        print(f"log archive failed: {e}")


class Endfield(Game):
    id = "endfield"
    required = ("maaend_path", "log_dir")

    def run(self, timeout=7200):
        path = self.cfg["maaend_path"]
        print(f"[{ts()}] starting {path}")
        subprocess.Popen([path], cwd=os.path.dirname(path))
        time.sleep(15)
        start = time.time()
        while process_running("MaaEnd.exe") and time.time() - start < timeout:
            time.sleep(10)
        kill(["MaaEnd.exe", "Endfield.exe", "Gryphlink.exe"])
        time.sleep(5)
        archive_log(self.cfg["log_dir"])
        log = read_since(os.path.join(self.cfg["log_dir"], "go-service.log"), 0)
        return parse_endfield_log(log, self.new_report())
