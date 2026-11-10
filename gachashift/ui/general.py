"""General: languages, what happens while running, and Telegram."""

import requests
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QCheckBox, QGridLayout, QHBoxLayout, QLineEdit, QSlider, QVBoxLayout,
                               QWidget)

from ..system import dim_gamma, restore_gamma
from ..winutil import allow_darker, darker_allowed

from .widgets import Choice, Toggle, button, label, panel, shadowed

LANGUAGES = [("en", "English"), ("zh", "中文")]


def switch_row(text, checked, on_toggle):
    row = QHBoxLayout()
    row.addWidget(label(text), 1)
    toggle = Toggle(checked)
    toggle.toggled.connect(on_toggle)
    row.addWidget(toggle)
    return row


def dim_controls(app, options):
    """Brightness slider, a 5-second preview, and (when Windows caps it) Allow darker."""
    holder = QWidget()
    col = QVBoxLayout(holder)
    col.setContentsMargins(0, 4, 0, 4)
    col.setSpacing(8)
    title = label(app.tr("general.dim_level", n=options.get("dim_level", 30)), "muted")
    col.addWidget(title)
    slider = QSlider(Qt.Horizontal)
    slider.setRange(5, 100)
    slider.setValue(int(options.get("dim_level", 30)))

    def set_level(v):
        title.setText(app.tr("general.dim_level", n=v))
        app.set_option("dim_level", v)

    slider.valueChanged.connect(set_level)
    col.addWidget(slider)

    row = QHBoxLayout()
    preview = button(app.tr("general.preview"))
    unlock = button(app.tr("general.unlock"))
    unlock.setToolTip(app.tr("general.unlock_hint"))
    unlock.setVisible(False)
    row.addWidget(preview)
    row.addWidget(unlock)
    row.addStretch()
    col.addLayout(row)
    result = label("", "hint", wrap=True)
    col.addWidget(result)

    state = {"left": 0, "brightness": None, "reached": None}
    timer = QTimer(holder)

    def finish():
        timer.stop()
        try:
            restore_gamma()
        except Exception:
            pass
        if state["brightness"] is not None:
            try:
                import screen_brightness_control as sbc
                for index, level in enumerate(state["brightness"]):
                    sbc.set_brightness(level, display=index)
            except Exception:
                pass
        preview.setEnabled(True)
        wanted = slider.value() / 100
        reached = state["reached"]
        if reached is None:
            result.setText(app.tr("general.preview_refused"))
        elif reached > wanted + 0.001:
            result.setText(app.tr("general.preview_capped", n=int(reached * 100)))
            unlock.setVisible(not darker_allowed())
        else:
            result.setText(app.tr("general.preview_ok"))

    def tick():
        state["left"] -= 1
        if state["left"] <= 0:
            finish()
        else:
            result.setText(app.tr("general.preview_on", n=state["left"]))

    def start():
        level = slider.value() / 100
        preview.setEnabled(False)
        try:
            import screen_brightness_control as sbc
            state["brightness"] = sbc.get_brightness()
            sbc.set_brightness(int(level * 100))
        except Exception:
            state["brightness"] = None
        try:
            state["reached"] = dim_gamma(level)
        except Exception:
            state["reached"] = None
        state["left"] = 6
        tick()
        timer.start(1000)

    def do_unlock():
        ok = allow_darker()
        result.setText(app.tr("general.unlock_done" if ok else "general.unlock_failed"))
        unlock.setVisible(not ok)

    timer.timeout.connect(tick)
    preview.clicked.connect(start)
    unlock.clicked.connect(do_unlock)
    return holder


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
        if key == "dim_screen":
            inner.addWidget(label(app.tr("general.dim_hint"), "hint", wrap=True))
            inner.addWidget(dim_controls(app, options))
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
