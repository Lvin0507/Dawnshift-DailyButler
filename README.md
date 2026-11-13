<div align="center">

<img src="assets/gachashift.png" alt="Gachashift" width="160">

# Gachashift

**Clears your game dailies while you sleep.**

[![Release](https://img.shields.io/github/v/release/Lvin0507/Gachashift)](https://github.com/Lvin0507/Gachashift/releases/latest)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
![Windows](https://img.shields.io/badge/platform-Windows-0078D6)

[English](README.md) · [中文](README.zh.md) · [Download](https://github.com/Lvin0507/Gachashift/releases/latest)

</div>

## Download

Get `Gachashift-x.y.z.zip` from [Releases](../../releases), unzip it to a folder you can write to (not Program Files), and open `Gachashift.exe`. The app walks you through the setup.

Windows may say it "protected your PC", because the exe isn't code-signed: choose **More info → Run anyway**.

You also need the automation tool for each game you play (MaaEnd, MAA, ok-ww, BAAS, OneDragon or BetterGI), set up and working on its own first. The app links to each one.

## What it does

| Game | Tool | What runs |
|---|---|---|
| Arknights: Endfield | [MaaEnd](https://github.com/MaaXYZ/MaaEnd) | Launches the game and runs all daily tasks |
| Arknights (PC client) | [MAA](https://github.com/MaaAssistantArknights/MaaAssistantArknights) | Recruitment, base shifts, credit store, rewards |
| Wuthering Waves (official or Steam) | [ok-ww](https://github.com/ok-oldking/ok-wuthering-waves) | Weekly garden task, Mondays by default |
| Blue Archive (JP PC client) | [BAAS](https://github.com/pur1fying/blue_archive_auto_script) | Cafe, lessons, arena, sweeps, crafting, rewards |
| Zenless Zone Zero (official or Steam) | [OneDragon](https://github.com/OneDragon-Anything/ZenlessZoneZero-OneDragon) | Redeem codes, check-in, mail, video store, coffee, rewards |
| Genshin Impact | [BetterGI](https://github.com/babalae/better-genshin-impact) | Mail, daily commissions, commission reward, expeditions |

Each game can be turned on or off and given its own weekdays. When everything is done, Gachashift sends a report (English by default, Chinese optional):

```
🌅 Gachashift report (11-10)

『🪐 Arknights: Endfield』
Launch game: ✅ Done
Base rewards: ✅ Done
Environment monitoring: ❌ Failed
Delivery jobs: ✅ Done (3/3)
...

『🎯 Arknights』
Recruitment: ✅ Done (x4)
Base shifts: ✅ Done
...

『📘 Blue Archive』
BAAS dailies: ✅ Done
✅ Finished in 14 min

『⚡ Zenless Zone Zero』
Daily check-in: ✅ Done
Mail: ✅ Done
✅ Finished in 6 min
```

## How it works

Gachashift doesn't play the games itself. For each game it opens the right tool, waits for it to finish, closes everything it started and then reads the tool's own log. The report comes from fixed rules about each tool's start, success and failure lines, so the same log always gives the same report, and a task the rules don't know yet is shown as a new task instead of being silently ignored.

Around that, it handles the parts the tools leave to you: clicking launcher start buttons, waiting for a server's daily reset, restarting Steam with the right permissions, muting the PC (and optionally dimming the screen) while it runs, and putting everything back afterwards.

If you are using the PC when the scheduled time comes, it asks first and gives you 60 seconds to skip. A run can be stopped from the app at any time: the game in progress closes its tool and game, sound and brightness are restored, the PC stays on, and the report lists what was finished before the stop.

## Requirements

- Windows
- A Telegram bot or a Discord webhook, if you want the report on your phone (optional)
- The tools for your games, installed and working on their own first. Follow each tool's own documentation, then check these settings Gachashift relies on:
  - **MaaEnd**: "Launch Game (PC)" as the first task and "kill process" as the last
  - **MAA**: connection set to PC client, "start game" path set, "run on startup" enabled
  - **ok-ww**: game path set; GardenTask configured
  - **BAAS**: "run on startup" enabled, "start emulator on startup" **disabled** (Gachashift opens the JP launcher and clicks スタート itself), "exit BAAS when done" selected
  - **OneDragon**: game path and account instance set; the apps you want enabled in the one-dragon list
  - **BetterGI**: set the game path, enable the tasks you want in a one-dragon config, and set its finishing action to close the game and BetterGI (not shut down)
- For Steam games: Steam must sign in automatically to the account that owns the game
- The PC must stay on and signed in overnight. Turning the screen off is fine; sleep and the lock screen are not, because no tool can see or click anything on the lock screen
- Leave the PC alone during a run. BAAS and the launcher clicks use the real mouse, and moving it makes BAAS stop

## Run from source

1. Install Python 3.10 or newer (**64-bit**; the app's interface library has no 32-bit version), then the dependencies:
   ```
   pip install -r requirements.txt
   ```
2. Double-click `Gachashift App.bat`.

The app takes it from there. Home shows a short setup checklist with a button for each step: turn on your games, tell Gachashift where each tool is, do one test run, connect Telegram or Discord (optional), and choose when to run. Every setting has a one-line hint under it, and each game's page links to its tool's own documentation. When all five steps are done, the checklist goes away.

Other pages:

- **Run**: run everything now, or test one game; the output appears as it happens
- **Schedule**: the daily Task Scheduler task (highest privileges, never starts late after a missed time)
- **History**: past runs, with the report at the end
- **General**: languages, mute / darken the screen / shut down while running, Telegram and Discord with a test message, the update check
- **Appearance**: a background image, panel opacity, accent colour, and an image for each game. Images are files on your PC; they stay there and are never uploaded or bundled

While a run is going on, a **Stop** button appears on every page.

### Command line

The app runs the same commands, so they also work on their own:

```
python -m gachashift                   # the scheduled run (asks first if someone is at the PC)
python -m gachashift --no-shutdown     # run everything now and keep the PC on
python -m gachashift --only zzz        # one game: endfield, arknights, wuthering, bluearchive, zzz or genshin
python -m gachashift --dry-run-endfield logs\go-service_<date>.log
```

Add `--lang zh` for a Chinese report.

## Logs

- `logs/gachashift_<date>.log`: everything Gachashift printed during a run, kept for 14 days. Scheduled runs have no visible console, so this is the first place to look when a report looks wrong. The app's **History** page shows the same files.
- `logs/go-service_<date>.log`: archived MaaEnd logs, kept for 14 days (MaaEnd overwrites its own log on every launch).

## Known limitations

- **Blue Archive's ✅ means BAAS finished, not that every daily mission is done.** BAAS doesn't write its task log to a file, so Gachashift only knows that BAAS ran and exited normally. Which missions get done depends on the tasks enabled in BAAS.
- **OneDragon updates itself on every start**, and an update that needs a driver installed waits for a click. Open OneDragon by hand once after each game update, so the morning run doesn't stop at that window.
- **Wuthering Waves only runs the weekly garden task** for now.
- **Genshin's commissions depend on BetterGI's community scripts.** Some commissions have no route yet; the commission reward can still be claimed with Adventurer Rank points. Turn off BetterGI's automatic script updates, so an update can't replace a script while it runs.
- **Windows only**, because every tool is Windows-only.

## Project layout

```
gachashift/           The program
  __main__.py         Command line (python -m gachashift)
  ui/                 The desktop app (PySide6; python -m gachashift.ui)
  winutil.py          Elevated runs, the Task Scheduler task, calibration, per-game settings
  runner.py           Picks today's games, waits for resets, stop requests, report, shutdown
  prompt.py           The "about to start" window for scheduled runs
  config.py           config.json, defaults, and migration from the old .env
  system.py           Processes, logs, launcher clicks, Steam, lock screen, mute and brightness
  report.py           Structured results, the Telegram and Discord messages
  updates.py          Asks GitHub whether a newer release is out
  i18n.py             All English and Chinese text
  games/              One module per game
Gachashift.py         Entry point of Gachashift.exe (opens the app, or "run" does a run)
Gachashift App.bat    Opens the app from source
build.py              Builds dist/Gachashift and its zip with PyInstaller
assets/               The app icon
.github/workflows/    Builds and publishes a Release when a version tag is pushed
config.example.json   Template for config.json
logs/                 Run logs and archived MaaEnd logs (git-ignored)
```

## Lessons learned

Problems I hit while building this, and what fixed them:

- **The report said "timed out" when the real error was 503.** A bare `except:` labelled every failure as a timeout. Logging the actual HTTP status showed Gemini was overloaded at peak hours, so I added increasing backoff and a fallback model.
- **The API key could leak through error messages.** The key was in the URL query string, which `requests` includes in exception text that was then sent to Telegram. Moved it to the `x-goog-api-key` header.
- **One noisy log line made the prompt 300k characters.** A delivery task dumped ~2KB of JSON per scan; filtering those lines (and capping line length) cut it to ~13k.
- **A real failure was reported as success.** Some failures are only logged at `debug` level, and my own filter was dropping all debug lines. The fix exposed a bigger issue: asking an LLM to judge success from logs is fragile.
- **So the parsing became deterministic.** Each task has a clear start line and a clear failure line. Gachashift checks those directly, and flags any task it hasn't seen before instead of silently ignoring it. The first version used Gemini to read the logs; the current one needs no API key at all.
- **Keyword checks lie, too.** The first Wuthering Waves check looked for a few words like "completed" and reported success on a run that had failed. It now only trusts ok-ww's exact completion and failure lines.
- **Test runs read the wrong data.** MaaEnd overwrites its log on every launch, so opening it again wiped the morning's log. Each run's log is now archived.
- **MAA never exits on its own.** In PC-client mode there is no "exit when done" option, so Gachashift watches MAA's log for its completion message and closes it, reading only the part of the log written during this run.
- **Secrets started out hard-coded.** Everything sensitive now lives in a git-ignored `config.json`, and GitHub push protection blocks accidental key commits.
- **Not every game can be automated safely.** NIKKE's PC client ignores all synthetic input, and running it on a real phone through ADB earned the account a one-hour ban. I dropped it instead of trying to evade the anti-cheat.
- **The script needs a 1280x720 window, but I play full screen.** Blue Archive (Unity) keeps its window size in the registry, so Gachashift writes a 1280x720 window before launching. Restoring full screen afterwards turned out not to be possible from the registry: the game's full-screen toggle isn't stored in Unity's standard settings, and an earlier save-and-restore approach also broke once an interrupted run left the window values behind. So Gachashift only sets the window it needs, and I press Alt+Enter when I play.
- **"Wait for the process to exit" waited for the wrong process.** BAAS's `.exe` is only a launcher that starts the real script and quits. Gachashift tracks the processes running from inside each tool's folder, matching on the path so it never touches its own `python.exe`. Later BAAS started leaving `adb.exe` running after it quit, so for BAAS the run now ends when its main `pythonw.exe` exits, and the leftovers are closed.
- **Redirecting a tool's output crashed it.** BAAS's launcher prints a banner with block characters. Sent to a file, Python fell back to the system's Japanese code page (cp932), which can't encode them, and the launcher died before starting BAAS. Giving it its own console window fixed it.
- **The JP client can't be started directly.** Running `BlueArchive.exe` by itself crashes at login, and the official launcher has no auto-start option. Gachashift opens the launcher, finds its window by process, and clicks スタート (as a fraction of the window size, so it survives DPI scaling) until the game process appears.
- **A real-mouse click can land on the wrong window.** Windows sometimes refuses to bring a window to the front, and one morning a click meant for Blue Archive's launcher opened Endfield's instead. Gachashift now checks that the launcher really is the foreground window before clicking, and skips the click if it isn't.
- **The Steam build of ZZZ can't be launched directly.** Starting the game exe makes it quit and ask for Steam, and Steam then opens the HoYoverse launcher, which needs a click on its start button. Gachashift starts the game through `steam://rungameid/`, clicks the launcher's button the same way it does for Blue Archive, and only then hands the running game to OneDragon.
- **A UAC prompt nobody can click.** ZZZ needs admin rights. Child processes inherit their parent's privileges, so when the elevated script started Steam, the game launched silently; but if Steam was already running as a normal user (it starts at login), launching the game raised a UAC prompt. UAC prompts run on a separate secure desktop that scripts deliberately can't interact with, so the run just stalled. Gachashift now closes an already-running Steam with `steam://exit` and starts it again itself, so the whole chain inherits admin rights. Wuthering Waves on Steam needed the same treatment: without Steam ready, the game closed itself a minute after ok-ww started it.
- **A tool that only exits on success.** ok-ww's `-e` flag exits after a successful run but leaves the app open after a task exception, still moving the mouse in the background, which then interfered with the next game. Gachashift now watches the tool's log for its own completion and failure lines and always closes the tool afterwards, whatever the outcome.
- **A scheduled run leaves no trace.** Task Scheduler runs have no visible console, so the first time ZZZ silently did nothing there was no way to tell why. Everything Gachashift prints now also goes to a dated log file.
- **The lock screen blinds every tool.** Testing wake-from-sleep, Windows woke up on the lock screen, where screen capture fails, so MaaEnd sat there unable to start the game. Waking without a password would have fixed it at the cost of security, so the PC stays on with the screen off instead, and Gachashift checks for the lock screen first: if it is up, the report says so rather than hanging for hours.
- **A run that starts while you're at the PC.** The first time the schedule fired while I was using the computer, games and tools kept opening and had to be closed one by one. Scheduled runs now ask first if the mouse or keyboard was used in the last two minutes, and every wait in a run checks for a stop request, so a stop takes effect within a second and still cleans up after itself.

## Releasing

Set the version in `gachashift/__init__.py`, commit and push, then push a matching tag such as `v1.0.1`. GitHub Actions builds `Gachashift.exe` on Windows and publishes the Release with the zip attached; it stops if the tag and the version don't match.

## Built on

Gachashift only orchestrates these tools and reads their logs — all the actual game automation is their work:

- [MaaEnd](https://github.com/MaaXYZ/MaaEnd) — Arknights: Endfield
- [MaaAssistantArknights](https://github.com/MaaAssistantArknights/MaaAssistantArknights) — Arknights
- [ok-wuthering-waves](https://github.com/ok-oldking/ok-wuthering-waves) — Wuthering Waves
- [BAAS](https://github.com/pur1fying/blue_archive_auto_script) — Blue Archive
- [ZenlessZoneZero-OneDragon](https://github.com/OneDragon-Anything/ZenlessZoneZero-OneDragon) — Zenless Zone Zero
- [BetterGI](https://github.com/babalae/better-genshin-impact) — Genshin Impact

This repo doesn't include or redistribute any of their code. Each project has its own license; please check them before use.

## Disclaimer

For learning purposes only. Game automation may violate the games' terms of service and can get accounts banned — use at your own risk.

## License

[MIT](LICENSE)