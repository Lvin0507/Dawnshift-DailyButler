"""History: read past runs, newest first. The report is at the end of each run."""

from PySide6.QtWidgets import QComboBox, QHBoxLayout, QPlainTextEdit, QVBoxLayout, QWidget

from ..config import app_dir
from ..system import read_since
from .widgets import label, panel, shadowed


def build(app):
    page = QWidget()
    box = QVBoxLayout(page)
    box.setContentsMargins(0, 0, 8, 8)
    box.setSpacing(12)
    box.addWidget(shadowed(label(app.tr("nav.history"), "h1")))

    folder = app_dir() / "logs"
    runs = sorted(folder.glob("gachashift_*.log"), reverse=True) if folder.exists() else []
    if not runs:
        card, inner = panel()
        inner.addWidget(label(app.tr("history.empty"), "muted", wrap=True))
        box.addWidget(card)
        box.addStretch()
        return page

    dates = {path.stem.replace("gachashift_", ""): path for path in runs}
    row = QHBoxLayout()
    row.addWidget(shadowed(label(app.tr("history.pick"), "muted")))
    picker = QComboBox()
    picker.addItems(list(dates))
    row.addWidget(picker)
    row.addStretch()
    box.addLayout(row)

    output = QPlainTextEdit()
    output.setReadOnly(True)
    output.setMinimumHeight(420)

    def show(date):
        output.setPlainText(read_since(str(dates[date]), 0))
        output.verticalScrollBar().setValue(output.verticalScrollBar().maximum())

    picker.currentTextChanged.connect(show)
    show(picker.currentText())
    box.addWidget(output, 1)
    return page
