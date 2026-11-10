"""Run: run everything now, or test one game, and watch the output as it happens.
The run itself lives in the window (it keeps going when you switch pages)."""

from PySide6.QtWidgets import QHBoxLayout, QPlainTextEdit, QVBoxLayout, QWidget

from ..games import GAMES
from ..system import read_since
from ..winutil import SHORT_NAMES
from .widgets import Choice, button, label, panel, shadowed


def build(app):
    page = QWidget()
    box = QVBoxLayout(page)
    box.setContentsMargins(0, 0, 8, 8)
    box.setSpacing(12)
    box.addWidget(shadowed(label(app.tr("test.heading"), "h1")))
    box.addWidget(shadowed(label(app.tr("test.explain"), "muted", wrap=True)))
    busy = app.run_busy()

    card, inner = panel(spacing=6)
    inner.addWidget(label(app.tr("run.all"), "h2"))
    inner.addWidget(label(app.tr("run.all_explain"), "hint", wrap=True))
    run_all = button(app.tr("run.all"), "primary", lambda: app.start_run("-m gachashift --no-shutdown"))
    run_all.setEnabled(not busy)
    row = QHBoxLayout()
    row.addWidget(run_all)
    row.addStretch()
    inner.addSpacing(6)
    inner.addLayout(row)
    box.addWidget(card)

    card, inner = panel(spacing=6)
    inner.addWidget(label(app.tr("run.one"), "h2"))
    inner.addWidget(label(app.tr("run.one_explain"), "hint", wrap=True))
    short = SHORT_NAMES.get(app.lang, SHORT_NAMES["en"])
    picker = Choice([(g.id, short[g.id]) for g in GAMES], app.test_game)
    one = button(app.tr("test.run", game=short[app.test_game]), None,
                 lambda: app.start_run(f"-m gachashift --only {app.test_game}"))
    one.setEnabled(not busy)

    def pick(gid):
        app.test_game = gid
        one.setText(app.tr("test.run", game=short[gid]))

    picker.changed.connect(pick)
    inner.addSpacing(4)
    inner.addWidget(picker)
    row = QHBoxLayout()
    row.addWidget(one)
    row.addStretch()
    inner.addSpacing(6)
    inner.addLayout(row)
    box.addWidget(card)
    app.run_buttons = [run_all, one]

    app.run_status = shadowed(label(app.tr("test.running") if busy else "", "muted"))
    box.addWidget(app.run_status)
    output = QPlainTextEdit()
    output.setReadOnly(True)
    output.setMinimumHeight(300)
    if app.run_log:
        output.setPlainText(read_since(app.run_log, app.run_start_offset))
        output.verticalScrollBar().setValue(output.verticalScrollBar().maximum())
    app.run_output = output
    box.addWidget(output, 1)
    return page
