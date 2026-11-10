"""General: languages, what happens while running, and Telegram."""

import requests
from PySide6.QtWidgets import QCheckBox, QGridLayout, QHBoxLayout, QLineEdit, QVBoxLayout, QWidget

from .widgets import Choice, Toggle, button, label, panel, shadowed

LANGUAGES = [("en", "English"), ("zh", "中文")]


def switch_row(text, checked, on_toggle):
    row = QHBoxLayout()
    row.addWidget(label(text), 1)
    toggle = Toggle(checked)
    toggle.toggled.connect(on_toggle)
    row.addWidget(toggle)
    return row


def build(app):
    page = QWidget()
    box = QVBoxLayout(page)
    box.setContentsMargins(0, 0, 8, 8)
    box.setSpacing(12)
    box.addWidget(shadowed(label(app.tr("nav.general"), "h1")))

    # languages
    card, inner = panel(spacing=12)
    grid = QGridLayout()
    grid.setHorizontalSpacing(16)
    grid.setVerticalSpacing(10)
    for row, key in enumerate(("language", "report_language")):
        grid.addWidget(label(app.tr(f"general.{key}"), "h2"), row, 0)
        choice = Choice(LANGUAGES, app.cfg.get(key, "en"))
        choice.changed.connect(lambda value, key=key: app.set_language(key, value))
        grid.addWidget(choice, row, 1)
    grid.setColumnStretch(2, 1)
    inner.addLayout(grid)
    box.addWidget(card)

    # while running
    card, inner = panel(spacing=12)
    inner.addWidget(label(app.tr("general.while_running"), "h2"))
    options = app.cfg["options"]
    for key, text in (("mute", "general.mute"), ("dim_screen", "general.dim"),
                      ("shutdown", "general.shutdown")):
        inner.addLayout(switch_row(app.tr(text), bool(options.get(key)),
                                   lambda on, key=key: app.set_option(key, on)))
    box.addWidget(card)

    # Telegram
    tg = app.cfg["telegram"]
    card, inner = panel(spacing=12)

    def set_enabled(on):
        tg["enabled"] = on
        app.changed()

    head = switch_row(app.tr("general.telegram"), bool(tg.get("enabled")), set_enabled)
    head.itemAt(0).widget().setObjectName("h2")
    inner.addLayout(head)

    grid = QGridLayout()
    grid.setHorizontalSpacing(12)
    grid.setVerticalSpacing(8)
    token = QLineEdit(tg.get("bot_token", ""))
    token.setEchoMode(QLineEdit.Password)
    chat = QLineEdit(tg.get("chat_id", ""))
    show = QCheckBox(app.tr("general.show"))
    show.toggled.connect(lambda on: token.setEchoMode(QLineEdit.Normal if on else QLineEdit.Password))
    grid.addWidget(label(app.tr("general.bot_token"), "muted"), 0, 0)
    grid.addWidget(token, 0, 1)
    grid.addWidget(show, 0, 2)
    grid.addWidget(label(app.tr("general.chat_id"), "muted"), 1, 0)
    grid.addWidget(chat, 1, 1)
    grid.setColumnStretch(1, 1)
    inner.addLayout(grid)

    for edit, key in ((token, "bot_token"), (chat, "chat_id")):
        edit.textChanged.connect(lambda text, key=key: (tg.__setitem__(key, text.strip()), app.changed()))

    result = label("", "muted", wrap=True)

    def send_test():
        if not tg.get("bot_token") or not tg.get("chat_id"):
            result.setText(app.tr("telegram.incomplete"))
            return
        try:
            r = requests.post(f"https://api.telegram.org/bot{tg['bot_token']}/sendMessage",
                              json={"chat_id": tg["chat_id"], "text": app.tr("telegram.test_text")},
                              timeout=15)
            ok = r.ok
        except requests.exceptions.RequestException:
            ok = False
        result.setText(app.tr("telegram.sent" if ok else "telegram.failed"))
        result.setObjectName("ok" if ok else "error")
        result.style().unpolish(result)
        result.style().polish(result)

    row = QHBoxLayout()
    row.addWidget(button(app.tr("general.test_telegram"), None, send_test))
    row.addWidget(result, 1)
    inner.addLayout(row)
    box.addWidget(card)
    box.addStretch()
    return page
