"""Common shape of a game module."""

import time

from ..report import GameReport


class Game:
    id = ""
    # (utc offset, reset hour) of the server's daily reset, or None
    reset = None
    # config keys that must be filled in before the game can run
    required = ()

    def __init__(self, cfg):
        self.cfg = cfg

    def missing_settings(self):
        return [key for key in self.required if not self.cfg.get(key)]

    def new_report(self):
        return GameReport(self.id)

    def run(self):
        raise NotImplementedError


def minutes_since(start):
    return round((time.time() - start) / 60)
