# Dawnshift — Daily Butler

Clears my game dailies before I wake up: a Windows script that runs four game-automation tools at dawn, sends a summary to Telegram and shuts the PC down.

## What it does

| Game | Tool | What runs |
|---|---|---|
| Arknights: Endfield | [MaaEnd](https://github.com/MaaXYZ/MaaEnd) | Launches the game and runs all daily tasks |
| Arknights (PC client) | [MAA](https://github.com/MaaAssistantArknights/MaaAssistantArknights) | Recruitment, base shifts, credit store, rewards |
| Wuthering Waves | [ok-ww](https://github.com/ok-oldking/ok-wuthering-waves) | Weekly garden task, Mondays only |
| Blue Archive (JP, PC client) | [BAAS](https://github.com/pur1fying/blue_archive_auto_script) | Cafe, lessons, arena, sweeps, crafting, rewards |

After the games finish, it builds a report and sends it to Telegram:

```
🌅 Dawnshift 战报 (10-29)

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

『📘 蔚蓝档案战报』
BAAS 日常：✅已运行完毕（用时 25 分钟）
```

## Two versions

| File | Report built by | Notes |
|---|---|---|
| `pagent.py` | Pure Python log parsing | **Recommended.** Deterministic, fast, no API key, no dependency on an LLM being available. The only version that runs Blue Archive |
| `agent.py` | Gemini (Endfield/WW) + Python (Arknights) | The original version. Retries with backoff on 503 and falls back to a lighter model |

Both read the same `.env`.

## Requirements

- Windows, Python 3.10+
- Run as Administrator (MAA's PC-client mode requires it)
- A Telegram bot (and a Gemini API key if you use `agent.py`)
- MaaEnd, MAA, ok-ww and BAAS installed and configured separately:
  - MaaEnd: enable "Launch Game (PC)" as the first task, and "kill process" as the last
  - MAA: connection set to PC client, "start game" path set, "run on startup" enabled
  - BAAS: "run on startup" and "start emulator on startup" enabled (point it at the original game client, not a translated one), "exit BAAS when done" selected
- BAAS clicks with the real mouse, so leave the PC alone while it runs — moving the mouse makes it stop
  - Blue Archive opens in a 1280x720 window after a run (the script needs it); press Alt+Enter to go back to full screen

## Setup

1. `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and fill in your token and paths
3. Test without launching anything — parse an existing MaaEnd log:
   ```
   python pagent.py --dry-run
   ```
4. Test a single game (no Telegram, no shutdown):
   ```
   python pagent.py --only bluearchive
   ```
5. Full test run that keeps the PC on:
   ```
   python pagent.py --no-shutdown
   ```
6. Schedule it with Windows Task Scheduler:
   - Program: your `python.exe`, Arguments: `pagent.py`, Start in: this folder
   - Tick "Run with highest privileges"
   - Keep "Run only when user is logged on" (the games need a real desktop)
   - Add a wake timer trigger at the time you want
   - Blue Archive runs last; the JP daily reset is 04:00 JST, so make sure it starts after that

## Turning games off

Each game except Endfield has a switch file path in `.env`. Create that file to skip the game; delete it to turn the game back on. To skip a whole morning, disable the task in Task Scheduler.

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
- **Not every game can be automated safely.** NIKKE's PC client ignores all synthetic input, and running it on a real phone through ADB earned the account a one-hour ban. I dropped it instead of trying to evade the anti-cheat.
- **The script needs a 1280x720 window, but I play full screen.** Blue Archive (Unity) keeps its window size in the registry, so the script writes a 1280x720 window before launching. Restoring full screen afterwards turned out not to be possible from the registry: the game's full-screen toggle isn't stored in Unity's standard settings, and an earlier save-and-restore approach also broke once an interrupted run left the window values behind. So the script only sets the window it needs, and I press Alt+Enter when I play.
- **"Wait for the process to exit" waited for the wrong process.** BAAS's `.exe` is only a launcher that starts the real script and quits. The script now tracks every process running from inside the BAAS folder, matching on the path so it never touches its own `python.exe`.
- **Redirecting a tool's output crashed it.** BAAS's launcher prints a banner with block characters. Sent to a file, Python fell back to the system's Japanese code page (cp932), which can't encode them, and the launcher died before starting BAAS. Giving it its own console window fixed it.

## Built on

Dawnshift only orchestrates these tools and reads their logs — all the actual game automation is their work:

- [MaaEnd](https://github.com/MaaXYZ/MaaEnd) — Arknights: Endfield
- [MaaAssistantArknights](https://github.com/MaaAssistantArknights/MaaAssistantArknights) — Arknights
- [ok-wuthering-waves](https://github.com/ok-oldking/ok-wuthering-waves) — Wuthering Waves
- [BAAS](https://github.com/pur1fying/blue_archive_auto_script) — Blue Archive

This repo doesn't include or redistribute any of their code. Each project has its own license; please check them before use.

## Disclaimer

For learning purposes only. Game automation may violate the games' terms of service — use at your own risk.

## License

[MIT](LICENSE)