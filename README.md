# Game Daily Butler

A Windows script that wakes up early, runs my daily game routines, and sends a summary to Telegram before shutting the PC down.

## What it does
- **Arknights: Endfield** via [MaaEnd](https://github.com/MaaXYZ/MaaEnd) - launches the game and runs all dailies
- **Arknights** via [MAA](https://github.com/MaaAssistantArknights/MaaAssistantArknights) (PC client mode) - stops MAA once its log reports completion
- **Wuthering Waves** via ok-ww - weekly garden task on Mondays only
- Builds a Telegram report: Endfield/WW are summarized by Gemini, Arknights is parsed directly from the MAA log
- Gemini calls retry with backoff on 503 and fall back to a lighter model
- Archives each run's MaaEnd log for 14 days
- Mutes system audio before starting (early-morning quiet mode)

## Requirements
- Windows, Python 3.10+, run as Administrator (MAA's PC mode requires it)
- MaaEnd, MAA and ok-ww installed and configured separately
- A Gemini API key and a Telegram bot

## Setup
1. `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and fill in your keys and paths
3. Test: `python agent.py` (comment out the shutdown line first)
4. Schedule it with Windows Task Scheduler ("Run with highest privileges")

## Turning games off
Create the switch file named in `.env` to skip that game (or `SWITCH_FILE` to skip everything).

## Disclaimer
For learning purposes only. Game automation may violate the games' terms of service; use at your own risk.