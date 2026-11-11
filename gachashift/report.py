"""Structured results, so each game's outcome can be rendered in any language later."""

import datetime
import html
import re
from dataclasses import dataclass, field

import requests

from .i18n import game_name, t, task_label

OK, FAIL, SKIPPED, ALREADY, PARTIAL, WARN, NOTHING = (
    "ok", "fail", "skipped", "already", "partial", "warn", "nothing")


@dataclass
class TaskResult:
    key: str              # raw task name from the tool's log (or our own id)
    status: str           # one of the constants above
    detail: str = ""      # language-neutral extra info, e.g. "3/3" or "x4"
    new: bool = False     # task the label table doesn't know yet


@dataclass
class GameReport:
    game: str
    tasks: list = field(default_factory=list)
    notes: list = field(default_factory=list)   # (string key, params) pairs

    def add(self, key, status, detail="", new=False):
        self.tasks.append(TaskResult(key, status, detail, new))

    def note(self, key, **params):
        self.notes.append((key, params))


def render_game(report, lang):
    lines = [f"『{game_name(report.game, lang)}』"]
    for task in report.tasks:
        label = task_label(report.game, task.key, lang)
        if task.new:
            label += " " + t(lang, "note.new_task")
        status = t(lang, f"status.{task.status}")
        if task.detail:
            status += f" ({task.detail})"
        lines.append(f"{label}: {status}" if lang == "en" else f"{label}：{status}")
    for key, params in report.notes:
        # params that are themselves string keys (e.g. "hint.steam") get translated too
        params = {k: t(lang, v) if isinstance(v, str) and v.startswith("hint.") else v
                  for k, v in params.items()}
        lines.append(t(lang, key, **params))
    return "\n".join(lines)


def render_all(reports, lang):
    return "\n\n".join(render_game(r, lang) for r in reports)


def send_telegram(token, chat_id, reports, lang):
    """Send the report; fall back to plain text if Telegram rejects the HTML."""
    title = t(lang, "report.title", date=datetime.datetime.now().strftime("%m-%d"))
    body = render_all(reports, lang)
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    text = f"<b>{html.escape(title)}</b>\n\n{html.escape(body)}"
    try:
        r = requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"}, timeout=15)
        if r.ok:
            return True
        plain = html.unescape(re.sub(r"</?b>", "", text))
        return requests.post(url, json={"chat_id": chat_id, "text": plain}, timeout=15).ok
    except requests.exceptions.RequestException as e:
        print(f"Telegram failed: {type(e).__name__}")
        return False


def send_discord(webhook_url, reports, lang):
    """Send the report to a Discord channel through a webhook. Discord caps a message at 2000
    characters, so a long report goes out in several messages, split between lines."""
    title = t(lang, "report.title", date=datetime.datetime.now().strftime("%m-%d"))
    chunks, current = [], ""
    for line in f"**{title}**\n\n{render_all(reports, lang)}".splitlines():
        line = line[:1900]
        if current and len(current) + len(line) + 1 > 1900:
            chunks.append(current)
            current = line
        else:
            current = f"{current}\n{line}" if current else line
    if current.strip():
        chunks.append(current)
    try:
        for chunk in chunks:
            r = requests.post(webhook_url, json={"content": chunk[:2000]}, timeout=15)
            if not r.ok:
                print(f"Discord failed: HTTP {r.status_code}")
                return False
        return True
    except requests.exceptions.RequestException as e:
        print(f"Discord failed: {type(e).__name__}")
        return False
