"""
One-off: rename the project from Dawnshift to Gachashift.

Run from the project folder (Daily), with the App closed:
    python scripts\\rename_to_gachashift.py

It renames the dawnshift/ package folder to gachashift/ and replaces the name in the code,
README, .bat launchers and config example. It prints every file it changes. Nothing outside
this folder is touched: the Task Scheduler task and the GitHub repo are renamed by hand.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPLACEMENTS = [("Dawnshift", "Gachashift"), ("dawnshift", "gachashift"), ("DAWNSHIFT", "GACHASHIFT")]
TEXT_SUFFIXES = {".py", ".md", ".bat", ".txt", ".json"}
SKIP_DIRS = {".git", "logs", "__pycache__", "legacy"}
SKIP_FILES = {"config.json", Path(__file__).name}


def main():
    old_pkg, new_pkg = ROOT / "dawnshift", ROOT / "gachashift"
    if new_pkg.exists():
        sys.exit("gachashift/ already exists; the rename seems to be done already.")
    if not old_pkg.exists():
        sys.exit("dawnshift/ not found; run this from the project folder.")

    changed = []
    for path in ROOT.rglob("*"):
        if (not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES
                or path.name in SKIP_FILES or SKIP_DIRS & set(path.relative_to(ROOT).parts)):
            continue
        text = path.read_text(encoding="utf-8", errors="strict")
        new = text
        for old, replacement in REPLACEMENTS:
            new = new.replace(old, replacement)
        if new != text:
            path.write_text(new, encoding="utf-8")
            changed.append(path.relative_to(ROOT))

    old_pkg.rename(new_pkg)
    for bat in ROOT.glob("Dawnshift*.bat"):
        bat.rename(bat.with_name(bat.name.replace("Dawnshift", "Gachashift")))

    print("Updated:")
    for path in changed:
        print("  ", path)
    print("Renamed dawnshift/ -> gachashift/")
    print("Next: create the schedule again in the App, then rename the GitHub repo.")


if __name__ == "__main__":
    main()