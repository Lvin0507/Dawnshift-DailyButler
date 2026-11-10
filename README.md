# Gachashift — Daily Butler

Clears my game dailies before I wake up. Gachashift is a Windows program that runs five game-automation tools one after another at dawn, checks each tool's log to see what actually got done, sends a short report to Telegram and shuts the PC down.

## What it does

| Game | Tool | What runs |
|---|---|---|
| Arknights: Endfield | [MaaEnd](https://github.com/MaaXYZ/MaaEnd) | Launches the game and runs all daily tasks |
| Arknights (PC client) | [MAA](https://github.com/MaaAssistantArknights/MaaAssistantArknights) | Recruitment, base shifts, credit store, rewards |
| Wuthering Waves (official or Steam) | [ok-ww](https://github.com/ok-oldking/ok-wuthering-waves) | Weekly garden task, Mondays by default |
| Blue Archive (JP PC client) | [BAAS](https://github.com/pur1fying/blue_archive_auto_script) | Cafe, lessons, arena, sweeps, crafting, rewards |
| Zenless Zone Zero (official or Steam) | [OneDragon](https://github.com/OneDragon-Anything/ZenlessZoneZero-OneDragon) | Redeem codes, check-in, mail, video store, coffee, rewards |

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

『🌊 Wuthering Waves』
Weekly garden: ✅ Done (max)

『📘 Blue Archive』
BAAS dailies: ✅ Done
✅ Finished in 14 min

『⚡ Zenless Zone Zero』
Daily check-in: ✅ Done
Mail: ✅ Done
Video store: ✅ Done
✅ Finished in 6 min
```

## How it works

Gachashift doesn't play the games itself. For each game it opens the right tool, waits for it to finish, closes everything it started and then reads the tool's own log. The report comes from fixed rules about each tool's start, success and failure lines, so the same log always gives the same report, and a task the rules don't know yet is shown as a new task instead of being silently ignored.

Around that, it handles the parts the tools leave to you: clicking launcher start buttons, waiting for a server's daily reset, restarting Steam with the right permissions, muting the PC (and optionally dimming the screen) while it runs, and putting everything back afterwards.

## Requirements

- Windows, Python 3.10 or newer
- Run as Administrator (MAA's PC-client mode and several games require it)
- A Telegram bot, if you want the report on your phone (optional)
- The tools for your games, installed and working on their own first. Follow each tool's own documentation, then check these settings Gachashift relies on:
  - **MaaEnd**: "Launch Game (PC)" as the first task and "kill process" as the last
  - **MAA**: connection set to PC client, "start game" path set, "run on startup" enabled
  - **ok-ww**: game path set; GardenTask configured
  - **BAAS**: "run on startup" enabled, "start emulator on startup" **disabled** (Gachashift opens the JP launcher and clicks スタート itself), "exit BAAS when done" selected
  - **OneDragon**: game path and account instance set; the apps you want enabled in the one-dragon list
- For Steam games: Steam must sign in automatically to the account that owns the game
- Leave the PC alone during a run. BAAS and the launcher clicks use the real mouse, and moving it makes BAAS stop
- Blue Archive is left in a 1280x720 window after a run (BAAS needs it); press Alt+Enter to go back to full screen

## Setup

1. Install the dependencies:
   ```
   pip install -r requirements.txt
   ```
2. Copy `config.example.json` to `config.json` and fill in your paths, enable your games and (optionally) add your Telegram bot token and chat id. If you used the old `pagent.py`, your `.env` is converted to `config.json` automatically the first time Gachashift runs.
3. If a game needs a launcher click (Blue Archive, Steam ZZZ), open the launcher, run `python scripts\measure_click.py`, hover over the start button and press Enter. Put the printed numbers in that game's `start_button`.
4. Test one game at a time (no Telegram, no shutdown, no weekday check):
   ```
   python -m gachashift --only zzz
   ```
   Use `endfield`, `arknights`, `wuthering`, `bluearchive` or `zzz`. Add `--lang zh` for a Chinese report.
5. Run everything once, keeping the PC on afterwards:
   ```
   python -m gachashift --no-shutdown
   ```
6. Schedule it with Windows Task Scheduler:
   - Program: your `python.exe`; Arguments: `-m gachashift`; Start in: this folder
   - Tick "Run with highest privileges"
   - Keep "Run only when user is logged on" (the games need a real desktop)
   - Add a trigger at the time you want and allow it to wake the computer

To check a MaaEnd log without launching anything: `python -m gachashift --dry-run-endfield logs\go-service_<date>.log`.

## Configuration

Everything lives in `config.json` (git-ignored, because it holds your Telegram token).

| Setting | Meaning |
|---|---|
| `language`, `report_language` | `en` or `zh` |
| `telegram` | `enabled`, `bot_token`, `chat_id` |
| `options.mute` | Mute while running, restore afterwards |
| `options.dim_screen` | Lowest brightness while running, restore afterwards (external monitors need DDC/CI) |
| `options.shutdown` | Shut the PC down when done |
| `games.<id>.enabled` | Run this game at all |
| `games.<id>.days` | Weekdays to run, Monday = 0 (Wuthering Waves defaults to `[0]`) |
| `games.<id>.wait_for_reset` | Blue Archive and ZZZ: wait for the server's daily reset if it is less than two hours away, so the run counts for the right day |
| `games.wuthering.steam_client` | `true` for the Steam build; Steam is started with admin rights before ok-ww |
| `games.zzz.client` | `official` (OneDragon opens the game) or `steam` (Gachashift opens it through Steam first) |
| `games.zzz.server` | `asia`, `america` or `europe`, for the reset time |

To skip a whole morning, disable the task in Task Scheduler.

## Logs

- `logs/gachashift_<date>.log`: everything Gachashift printed during a run, kept for 14 days. Runs started by Task Scheduler have no visible console, so this is the first place to look when a report looks wrong.
- `logs/go-service_<date>.log`: archived MaaEnd logs, kept for 14 days (MaaEnd overwrites its own log on every launch).

## Known limitations

- **Blue Archive's ✅ means BAAS finished, not that every daily mission is done.** BAAS doesn't write its task log to a file, so Gachashift only knows that BAAS ran and exited normally. Which missions get done depends on the tasks enabled in BAAS.
- **Wuthering Waves only runs the weekly garden task** for now.
- **Windows only**, because every tool is Windows-only.

## Project layout

```
gachashift/            The program
  __main__.py         Command line (python -m gachashift)
  runner.py           Picks today's games, waits for resets, quiet mode, report, shutdown
  config.py           config.json, defaults, and migration from the old .env
  system.py           Processes, logs, launcher clicks, Steam, mute and brightness
  report.py           Structured results and the Telegram message
  i18n.py             All English and Chinese text
  games/              One module per game
scripts/              Helpers (measure_click.py) and old test scripts
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
- **"Wait for the process to exit" waited for the wrong process.** BAAS's `.exe` is only a launcher that starts the real script and quits. Gachashift tracks every process running from inside the tool's folder, matching on the path so it never touches its own `python.exe`. The same approach now covers ok-ww and OneDragon.
- **Redirecting a tool's output crashed it.** BAAS's launcher prints a banner with block characters. Sent to a file, Python fell back to the system's Japanese code page (cp932), which can't encode them, and the launcher died before starting BAAS. Giving it its own console window fixed it.
- **The JP client can't be started directly.** Running `BlueArchive.exe` by itself crashes at login, and the official launcher has no auto-start option. Gachashift opens the launcher, finds its window by process, and clicks スタート (as a fraction of the window size, so it survives DPI scaling) until the game process appears.
- **A real-mouse click can land on the wrong window.** Windows sometimes refuses to bring a window to the front, and one morning a click meant for Blue Archive's launcher opened Endfield's instead. Gachashift now checks that the launcher really is the foreground window before clicking, and skips the click if it isn't.
- **The Steam build of ZZZ can't be launched directly.** Starting the game exe makes it quit and ask for Steam, and Steam then opens the HoYoverse launcher, which needs a click on its start button. Gachashift starts the game through `steam://rungameid/`, clicks the launcher's button the same way it does for Blue Archive, and only then hands the running game to OneDragon.
- **A UAC prompt nobody can click.** ZZZ needs admin rights. Child processes inherit their parent's privileges, so when the elevated script started Steam, the game launched silently; but if Steam was already running as a normal user (it starts at login), launching the game raised a UAC prompt. UAC prompts run on a separate secure desktop that scripts deliberately can't interact with, so the run just stalled. Gachashift now closes an already-running Steam with `steam://exit` and starts it again itself, so the whole chain inherits admin rights. Wuthering Waves on Steam needed the same treatment: without Steam ready, the game closed itself a minute after ok-ww started it.
- **A tool that only exits on success.** ok-ww's `-e` flag exits after a successful run but leaves the app open after a task exception, still moving the mouse in the background, which then interfered with the next game. Gachashift now watches the tool's log for its own completion and failure lines and always closes the tool afterwards, whatever the outcome.
- **A scheduled run leaves no trace.** Task Scheduler runs have no visible console, so the first time ZZZ silently did nothing there was no way to tell why. Everything Gachashift prints now also goes to a dated log file.

## Roadmap

- A desktop app (CustomTkinter) to pick games, fill in paths, calibrate launcher buttons, run a test and set the schedule, without editing `config.json`
- A packaged `.exe`, so Python isn't needed

## Built on

Gachashift only orchestrates these tools and reads their logs — all the actual game automation is their work:

- [MaaEnd](https://github.com/MaaXYZ/MaaEnd) — Arknights: Endfield
- [MaaAssistantArknights](https://github.com/MaaAssistantArknights/MaaAssistantArknights) — Arknights
- [ok-wuthering-waves](https://github.com/ok-oldking/ok-wuthering-waves) — Wuthering Waves
- [BAAS](https://github.com/pur1fying/blue_archive_auto_script) — Blue Archive
- [ZenlessZoneZero-OneDragon](https://github.com/OneDragon-Anything/ZenlessZoneZero-OneDragon) — Zenless Zone Zero

This repo doesn't include or redistribute any of their code. Each project has its own license; please check them before use.

## Disclaimer

For learning purposes only. Game automation may violate the games' terms of service and can get accounts banned — use at your own risk.

## License

[MIT](LICENSE)