# Dawnshift — Daily Butler

Clears my game dailies before I wake up: a Windows script that runs three game-automation tools at dawn, sends a summary to Telegram and shuts the PC down.

## What it does

| Game | Tool | What runs |
|---|---|---|
| Arknights: Endfield | [MaaEnd](https://github.com/MaaXYZ/MaaEnd) | Launches the game and runs all daily tasks |
| Arknights (PC client) | [MAA](https://github.com/MaaAssistantArknights/MaaAssistantArknights) | Recruitment, base shifts, credit store, rewards |
| Wuthering Waves | ok-ww | [ok-ww](https://github.com/ok-oldking/ok-wuthering-waves) | Weekly garden task, Mondays only |

After the games finish, it builds a report and sends it to Telegram:

```
⏰ 早晨游戏日常战报 (10-29)

『🪐 终末地战报』
启动游戏：✅成功
基建任务：✅成功
环境监测：❌失败
抢委托送货：✅成功(3/3)
...

『🎯 明日方舟战报』
自动公招：✅成功(招募4次)
基建换班：✅成功
...
```

## Two versions

| File | Report built by | Notes |
|---|---|---|
| `pagent.py` | Pure Python log parsing | **Recommended.** Deterministic, fast, no API key, no dependency on an LLM being available |
| `agent.py` | Gemini (Endfield/WW) + Python (Arknights) | The original version. Retries with backoff on 503 and falls back to a lighter model |

Both read the same `.env`.

## Requirements

- Windows, Python 3.10+
- Run as Administrator (MAA's PC-client mode requires it)
- MaaEnd, MAA and ok-ww installed and configured separately:
  - MaaEnd: enable "Launch Game (PC)" as the first task, and "kill process" as the last
  - MAA: connection set to PC client, "start game" path set, "run on startup" enabled
- A Telegram bot (and a Gemini API key if you use `agent.py`)

## Setup

1. `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and fill in your token and paths
3. Test without launching anything — parse an existing MaaEnd log:
   ```
   python pagent.py --dry-run
   ```
4. Full test run that keeps the PC on:
   ```
   python pagent.py --no-shutdown
   ```
5. Schedule it with Windows Task Scheduler:
   - Program: your `python.exe`, Arguments: `pagent.py`, Start in: this folder
   - Tick "Run with highest privileges"
   - Keep "Run only when user is logged on" (the games need a real desktop)
   - Add a wake timer trigger at the time you want

## Turning games off

Each game has a switch file path in `.env`. Create that file to skip the game; delete it to turn the game back on. `SWITCH_FILE` skips everything.

## Project layout

```
agent.py            Gemini-assisted version
pagent.py           Full-Python version
scripts/            Manual test helpers (test_ark.py, test_gemini.py) and experiments
logs/               Archived MaaEnd logs, 14 days (git-ignored)
.env                Secrets and local paths (git-ignored)
.env.example        Template for .env
```

## Lessons learned

Problems I hit while building this, and what fixed them:

- **The report said "timed out" when the real error was 503.** A bare `except:` labelled every failure as a timeout. Logging the actual HTTP status showed Gemini was overloaded at peak hours, so I added increasing backoff and a fallback model.
- **The API key could leak through error messages.** The key was in the URL query string, which `requests` includes in exception text that was then sent to Telegram. Moved it to the `x-goog-api-key` header.
- **One noisy log line made the prompt 300k characters.** A delivery task dumped ~2KB of JSON per scan; filtering those lines (and capping line length) cut it to ~13k.
- **A real failure was reported as success.** Some failures are only logged at `debug` level, and my own filter was dropping all debug lines. The fix exposed a bigger issue: asking an LLM to judge success from logs is fragile.
- **So the parsing became deterministic.** Each task has a clear start line and a clear failure line. `pagent.py` checks those directly, and also flags any task it hasn't seen before instead of silently ignoring it.
- **Test runs read the wrong data.** MaaEnd overwrites its log on every launch, so opening it again wiped the morning's log. Each run's log is now archived.
- **MAA never exits on its own.** In PC-client mode there is no "exit when done" option, so the script watches MAA's log for its completion message and closes it, reading only the part of the log written during this run.
- **Secrets started out hard-coded.** Everything sensitive now lives in a git-ignored `.env`, and GitHub push protection blocks accidental key commits.

## Disclaimer

For learning purposes only. Game automation may violate the games' terms of service — use at your own risk.

## License

[MIT](LICENSE)