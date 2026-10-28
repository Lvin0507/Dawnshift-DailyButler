# Manual test: run only the Arknights part, no shutdown, no Telegram
import os
import sys

# Make the parent folder (Daily) importable so we can import agentv2
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import run_until_log_marker, parse_maa_log, MAA_ARK_PATH, MAA_ARK_LOG, MAA_DONE_MARKERS, ARK_GAME_EXE

reason, maa_log = run_until_log_marker(MAA_ARK_PATH, "MAA.exe", MAA_ARK_LOG, MAA_DONE_MARKERS, ARK_GAME_EXE)
print(parse_maa_log(maa_log, reason))