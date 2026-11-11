"""Ask GitHub whether a newer release is out. Only reads the public releases list."""

import re

import requests

from . import __version__

REPO = "Lvin0507/Gachashift"
RELEASES = f"https://github.com/{REPO}/releases/latest"


def _parts(version):
    """'v1.10.2' -> (1, 10, 2), so versions compare as numbers, not text."""
    return tuple(int(n) for n in re.findall(r"\d+", version)[:3])


def newer_release(timeout=8):
    """(version, page url) of a release newer than this one, or None (also when offline)."""
    try:
        r = requests.get(f"https://api.github.com/repos/{REPO}/releases/latest", timeout=timeout,
                         headers={"Accept": "application/vnd.github+json"})
        if not r.ok:
            return None
        data = r.json()
        latest = data.get("tag_name", "")
        if latest and _parts(latest) > _parts(__version__):
            return latest.lstrip("v"), data.get("html_url") or RELEASES
    except (requests.exceptions.RequestException, ValueError):
        pass
    return None
