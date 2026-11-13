"""Game modules, in the order they run. Each returns a report.GameReport."""
from .arknights import Arknights
from .bluearchive import BlueArchive
from .endfield import Endfield
from .genshin import Genshin
from .wuthering import WutheringWaves
from .zzz import ZenlessZoneZero

# Blue Archive, ZZZ and Genshin go last: they may wait for their server's daily reset.
# Genshin is the slowest and least predictable, so a timeout there can't hold up the rest.
GAMES = [Endfield, Arknights, WutheringWaves, BlueArchive, ZenlessZoneZero, Genshin]
GAMES_BY_ID = {g.id: g for g in GAMES}
