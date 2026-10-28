# Manual test: show which task entries survive the log filter, then run the AI report
import os
import re
import sys

# Make the parent folder (Daily) importable so we can import agentv2
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import read_tail_log_endfield, ai_analyze_logs, MAA_LOG_DIR

log = read_tail_log_endfield(MAA_LOG_DIR)
print(f"Log size: {len(log)} chars")
print("Entries found:", sorted(set(re.findall(r'"entry":"(\w+)"', log))))
print(ai_analyze_logs(log))