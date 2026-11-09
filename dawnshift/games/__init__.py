"""Game modules, in the order they run. Each returns a report.GameReport."""
from .arknights import Arknights
from .bluearchive import BlueArchive
from .endfield import Endfield
from .wuthering import WutheringWaves
from .zzz import ZenlessZoneZero

# Blue Archive and ZZZ go last: they may wait for their server's daily reset
GAMES = [Endfield, Arknights, WutheringWaves, BlueArchive, ZenlessZoneZero]
GAMES_BY_ID = {g.id: g for g in GAMES}
