"""A small "about to start" window for scheduled runs, shown only when someone is at the PC.
Built with Qt like the app, so the packaged exe doesn't need a second GUI toolkit."""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from .i18n import t

BG, PANEL, TEXT, MUTED, ACCENT = "#141B2D", "#2D3858", "#E9E7F2", "#98A1BE", "#F4B860"


def ask_before_start(lang, seconds=60):
    """Return True to go ahead, False if the user chose to skip this run. Nobody answering
    means nobody is there after all, so the run starts when the countdown ends."""
    app = QApplication.instance() or QApplication([])
    family = "Microsoft YaHei UI" if lang == "zh" else "Segoe UI"
    dialog = QDialog()
    dialog.setWindowTitle("Gachashift")
    dialog.setWindowFlags(Qt.Dialog | Qt.WindowStaysOnTopHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
    dialog.setStyleSheet(f"""
        QDialog {{ background: {BG}; }}
        * {{ font-family: "{family}"; font-size: 14px; color: {TEXT}; }}
        QLabel#title {{ font-size: 18px; font-weight: 700; }}
        QLabel#text {{ color: {MUTED}; }}
        QPushButton {{ background: {PANEL}; border: none; border-radius: 8px; padding: 8px 18px; }}
        QPushButton#start {{ background: {ACCENT}; color: {BG}; font-weight: 700; }}
    """)
    col = QVBoxLayout(dialog)
    col.setContentsMargins(24, 20, 24, 20)
    col.setSpacing(12)
    title = QLabel(t(lang, "prompt.title"))
    title.setObjectName("title")
    text = QLabel()
    text.setObjectName("text")
    text.setWordWrap(True)
    text.setFixedWidth(400)
    col.addWidget(title)
    col.addWidget(text)
    row = QHBoxLayout()
    skip = QPushButton(t(lang, "prompt.skip"))
    start = QPushButton(t(lang, "prompt.start"))
    start.setObjectName("start")
    row.addWidget(skip)
    row.addStretch()
    row.addWidget(start)
    col.addLayout(row)

    result = {"go": True}
    left = {"n": seconds}

    def tick():
        left["n"] -= 1
        if left["n"] <= 0:
            dialog.accept()
            return
        text.setText(t(lang, "prompt.text", n=left["n"]))

    timer = QTimer(dialog)
    timer.timeout.connect(tick)
    skip.clicked.connect(lambda: (result.update(go=False), dialog.reject()))
    start.clicked.connect(dialog.accept)
    dialog.rejected.connect(lambda: result.update(go=False))  # closing it counts as "skip"
    left["n"] += 1
    tick()
    timer.start(1000)
    dialog.exec()
    timer.stop()
    return result["go"]
