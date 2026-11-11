"""Home: the setup checklist (until everything is done) and the list of games."""

import webbrowser

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QVBoxLayout, QWidget

from ..games import GAMES
from ..winutil import DAY_KEYS_EN, DAY_KEYS_ZH, missing_items, plain_name
from .theme import FAIL
from .widgets import ImageBox, Toggle, button, label, panel, shadowed


def days_summary(app, days):
    if len(days) == 7:
        return app.tr("home.every_day")
    if not days:
        return app.tr("home.no_days")
    names = DAY_KEYS_ZH if app.lang == "zh" else DAY_KEYS_EN
    if app.lang == "zh":
        return "周" + "、".join(names[d] for d in sorted(days))
    return ", ".join(names[d] for d in sorted(days))


def setup_card(app, steps):
    card, box = panel("setup", spacing=12)
    done = sum(1 for s in steps if s["done"])
    head = QHBoxLayout()
    head.addWidget(label(app.tr("setup.title"), "h2"))
    head.addStretch()
    head.addWidget(label(app.tr("setup.progress", done=done, total=len(steps)), "muted"))
    box.addLayout(head)

    grid = QGridLayout()
    grid.setHorizontalSpacing(14)
    grid.setVerticalSpacing(10)
    grid.setColumnStretch(1, 1)
    first_open = next((i for i, s in enumerate(steps) if not s["done"]), None)
    for row, step in enumerate(steps):
        mark = label("✓" if step["done"] else str(row + 1), "stepdone" if step["done"] else "steptodo")
        mark.setFixedWidth(22)
        mark.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        grid.addWidget(mark, row, 0, Qt.AlignTop)
        text = QVBoxLayout()
        text.setSpacing(2)
        title = label(app.tr(f"setup.{step['key']}"), "gamename")
        title.setProperty("off", "true" if step["done"] else "false")
        text.addWidget(title)
        if not step["done"]:
            text.addWidget(label(app.tr(f"setup.{step['key']}.hint"), "hint", wrap=True))
        grid.addLayout(text, row, 1)
        if not step["done"]:
            actions = QHBoxLayout()
            actions.setSpacing(6)
            if step.get("skip"):
                actions.addWidget(button(app.tr("setup.skip"), None, step["skip"]))
            # the next step to do stands out; the rest stay quiet
            go = button(app.tr("setup.go"), "primary" if row == first_open else None, step["go"])
            actions.addWidget(go)
            grid.addLayout(actions, row, 2, Qt.AlignTop)
    box.addLayout(grid)
    return card


def update_card(app):
    version, url = app.update_info
    card, inner = panel("setup", spacing=6)
    row = QHBoxLayout()
    text = QVBoxLayout()
    text.addWidget(label(app.tr("update.available", version=version), "h2"))
    text.addWidget(label(app.tr("update.hint"), "hint", wrap=True))
    row.addLayout(text, 1)

    def later():
        app.update_info = None
        app.show_page("home")

    row.addWidget(button(app.tr("update.later"), None, later))
    row.addWidget(button(app.tr("update.download"), "primary", lambda: webbrowser.open(url)))
    inner.addLayout(row)
    return card


def game_row(app, gid):
    game_cfg = app.cfg["games"][gid]
    enabled = bool(game_cfg.get("enabled"))
    card, box = panel(margins=(16, 12, 18, 12))
    row = QHBoxLayout()
    row.setSpacing(14)
    image = app.cfg["appearance"].get("game_images", {}).get(gid, "")
    thumb = ImageBox(image, 52, 52, 10)
    if thumb.has_image():
        row.addWidget(thumb)
    else:
        thumb.deleteLater()

    text = QVBoxLayout()
    text.setSpacing(2)
    name = label(plain_name(gid, app.lang), "gamename")
    name.setProperty("off", "false" if enabled else "true")
    text.addWidget(name)
    text.addWidget(label(days_summary(app, game_cfg.get("days", [])), "muted"))
    row.addLayout(text, 1)

    if not enabled:
        state = label(app.tr("home.off"), "off")
    elif missing_items(gid, game_cfg):
        state = button(app.tr("home.setup_detail"), "link", lambda: app.open_game(gid))
        state.setStyleSheet(f"color: {FAIL}; font-weight: 600;")
    else:
        state = label(app.tr("home.ready_detail"), "ok")
    row.addWidget(state)

    toggle = Toggle(enabled)

    def flip(on):
        game_cfg["enabled"] = on
        app.changed()
        app.show_page("home")

    toggle.toggled.connect(flip)
    row.addWidget(toggle)
    box.addLayout(row)
    for widget in (card, name):
        widget.setCursor(Qt.PointingHandCursor)
    card.mousePressEvent = lambda e, gid=gid: app.open_game(gid)
    return card


def build(app):
    page = QWidget()
    box = QVBoxLayout(page)
    box.setContentsMargins(0, 0, 8, 8)
    box.setSpacing(12)
    box.addWidget(shadowed(label(app.tr("home.heading"), "h1")))
    if app.update_info:
        box.addWidget(update_card(app))

    steps = app.setup_steps()
    if all(s["done"] for s in steps):
        box.addWidget(shadowed(label(app.tr("setup.all_done", time=app.schedule), "ok")))
    else:
        box.addWidget(setup_card(app, steps))

    for game_cls in GAMES:
        box.addWidget(game_row(app, game_cls.id))
    box.addStretch()
    return page
