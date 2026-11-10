"""Settings live in config.json next to the program (git-ignored, holds the Telegram token).
The App edits this file; the command line just reads it.

On first run, an existing .env from the old pagent.py is migrated automatically.
"""

import copy
import json
import os
import sys
from pathlib import Path

ALL_DAYS = [0, 1, 2, 3, 4, 5, 6]  # Monday = 0

DEFAULT_CONFIG = {
    "language": "en",            # app language
    "report_language": "en",     # Telegram / console report language
    "telegram": {"enabled": False, "bot_token": "", "chat_id": ""},
    "options": {
        "mute": True,            # mute while running, restore afterwards
        "dim_screen": False,     # darken the screen during the scheduled run, restore afterwards
        "dim_level": 30,         # screen brightness (%) while darkened
        "shutdown": True,        # shut the PC down when everything is done
    },
    "appearance": {
        "accent": "#F4B860",
        "background": "",        # an image on this PC, or empty for a plain background
        "panel_opacity": 82,     # 30-100: how solid the panels are over the background
        "game_images": {},       # game id -> image on this PC
    },
    "setup": {"test_run_done": False, "skip_telegram": False},
    "games": {
        "endfield": {"enabled": False, "days": ALL_DAYS,
                     "maaend_path": "", "log_dir": ""},
        "arknights": {"enabled": False, "days": ALL_DAYS,
                      "maa_path": "", "maa_log": "", "game_exe": "Arknights.exe"},
        "wuthering": {"enabled": False, "days": [0], "steam_client": False,
                      "okww_path": "", "log_path": "", "task": "GardenTask"},
        "bluearchive": {"enabled": False, "days": ALL_DAYS, "wait_for_reset": True,
                        "baas_dir": "", "baas_exe": "", "launcher_path": "",
                        "start_button": [0.852, 0.859]},
        "zzz": {"enabled": False, "days": ALL_DAYS, "wait_for_reset": True,
                "server": "asia",          # asia / america / europe
                "client": "official",      # official / steam
                "od_dir": "", "steam_appid": "4162040",
                "launcher_exe": "HYP.exe", "start_button": [0.85, 0.86]},
    },
}


def app_dir():
    """Folder of the .exe when frozen by PyInstaller, otherwise the project folder."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


CONFIG_PATH = app_dir() / "config.json"


def _merge(defaults, saved):
    """Fill in keys added in newer versions without touching the user's values."""
    out = copy.deepcopy(defaults)
    for key, value in saved.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


def load_config(path=CONFIG_PATH):
    path = Path(path)
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return _merge(DEFAULT_CONFIG, json.load(f))
    cfg = migrate_from_env(path.with_name(".env"))
    if cfg:
        save_config(cfg, path)
        print(f"Migrated settings from .env to {path.name}")
        return cfg
    return copy.deepcopy(DEFAULT_CONFIG)


def save_config(cfg, path=CONFIG_PATH):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def migrate_from_env(env_path):
    """Build a config from the old pagent.py .env, so existing setups keep working."""
    if not Path(env_path).exists():
        return None
    try:
        from dotenv import dotenv_values
    except ImportError:
        return None
    env = dotenv_values(env_path)
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    off = lambda key: bool(env.get(key)) and os.path.exists(env[key])
    g = cfg["games"]

    if env.get("TG_BOT_TOKEN"):
        cfg["telegram"] = {"enabled": True, "bot_token": env["TG_BOT_TOKEN"],
                           "chat_id": env.get("TG_CHAT_ID", "")}
    if env.get("MAA_END_PATH"):
        g["endfield"].update(enabled=True, maaend_path=env["MAA_END_PATH"],
                             log_dir=env.get("MAA_LOG_DIR", ""))
    if env.get("MAA_ARK_PATH"):
        g["arknights"].update(enabled=not off("ARK_SWITCH_FILE"), maa_path=env["MAA_ARK_PATH"],
                              maa_log=env.get("MAA_ARK_LOG", ""))
    if env.get("OK_WW_PATH"):
        g["wuthering"].update(enabled=not off("WW_SWITCH_FILE"), okww_path=env["OK_WW_PATH"],
                              log_path=env.get("WW_LOG_PATH", ""))
    if env.get("BAAS_DIR"):
        g["bluearchive"].update(enabled=not off("BA_SWITCH_FILE"), baas_dir=env["BAAS_DIR"],
                                baas_exe=env.get("BAAS_EXE", ""),
                                launcher_path=env.get("BA_LAUNCHER_PATH", ""))
    if env.get("ZZZ_OD_DIR"):
        g["zzz"].update(enabled=not off("ZZZ_SWITCH_FILE"), od_dir=env["ZZZ_OD_DIR"],
                        client="steam" if env.get("ZZZ_STEAM_APPID") else "official",
                        steam_appid=env.get("ZZZ_STEAM_APPID") or "4162040")
    return cfg
