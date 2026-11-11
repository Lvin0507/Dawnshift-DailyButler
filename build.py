"""Build the release: dist/Gachashift/ (Gachashift.exe plus its files) and a zip of it.

    pip install pyinstaller
    python build.py

Run it with the 64-bit Python that has the requirements installed."""

import shutil
import sys
from pathlib import Path

import PyInstaller.__main__

from gachashift import __version__

ROOT = Path(__file__).resolve().parent
ICON = ROOT / "assets" / "gachashift.ico"

args = [
    str(ROOT / "Gachashift.py"),
    "--name", "Gachashift",
    "--windowed",               # no console window; runs log to logs/ instead
    "--noconfirm", "--clean",
    # loaded indirectly, so PyInstaller can't see them on its own
    "--collect-submodules", "pycaw",
    "--collect-submodules", "comtypes",
    "--collect-submodules", "screen_brightness_control",
    # not used by the app; leaving them out keeps the download smaller
    "--exclude-module", "tkinter",
    "--exclude-module", "customtkinter",
]
if ICON.exists():
    # the exe's own icon, plus a copy the app window can use
    args += ["--icon", str(ICON), "--add-data", f"{ICON};assets"]
PyInstaller.__main__.run(args)

dist = ROOT / "dist" / "Gachashift"
# licences travel with the program
for name in ("LICENSE", "THIRD_PARTY_NOTICES.txt", "config.example.json"):
    if (ROOT / name).exists():
        shutil.copy(ROOT / name, dist / name)
    else:
        print(f"warning: {name} not found, not included")
archive = shutil.make_archive(str(ROOT / "dist" / f"Gachashift-{__version__}"), "zip", dist.parent, "Gachashift")
print(f"\nBuilt {archive}")
