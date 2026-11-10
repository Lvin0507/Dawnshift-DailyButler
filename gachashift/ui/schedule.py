"""Schedule: create, change or remove the daily Task Scheduler task."""

import os
import tempfile

from PySide6.QtWidgets import QComboBox, QHBoxLayout, QVBoxLayout, QWidget

from ..winutil import TASK_NAME, run_schtasks_elevated, task_xml
from .widgets import button, label, panel, shadowed


def build(app):
    page = QWidget()
    box = QVBoxLayout(page)
    box.setContentsMargins(0, 0, 8, 8)
    box.setSpacing(12)
    box.addWidget(shadowed(label(app.tr("nav.schedule"), "h1")))

    card, inner = panel(spacing=12)
    state = label("", "h2")
    inner.addWidget(state)
    inner.addWidget(label(app.tr("schedule.explain"), "hint", wrap=True))

    def show_state():
        state.setText(app.tr("schedule.current", time=app.schedule) if app.schedule
                      else app.tr("schedule.none"))
        state.setObjectName("ok" if app.schedule else "h2")
        state.style().unpolish(state)
        state.style().polish(state)

    show_state()
    row = QHBoxLayout()
    row.setSpacing(8)
    row.addWidget(label(app.tr("schedule.time"), "muted"))
    hour, minute = (app.schedule or "06:00").split(":")
    hours = QComboBox()
    hours.addItems([f"{h:02d}" for h in range(24)])
    hours.setCurrentText(hour)
    minutes = QComboBox()
    minutes.addItems([f"{m:02d}" for m in range(0, 60, 5)])
    minutes.setCurrentText(minute if int(minute) % 5 == 0 else "00")
    row.addWidget(hours)
    row.addWidget(label(":", "h2"))
    row.addWidget(minutes)
    row.addStretch()
    inner.addLayout(row)

    result = label("", "muted", wrap=True)

    def save_schedule():
        path = os.path.join(tempfile.gettempdir(), "gachashift_task.xml")
        with open(path, "w", encoding="utf-16") as f:
            f.write(task_xml(int(hours.currentText()), int(minutes.currentText())))
        ok = run_schtasks_elevated(f'/create /tn {TASK_NAME} /xml "{path}" /f')
        time_text = f"{hours.currentText()}:{minutes.currentText()}"
        if ok:
            app.schedule = time_text
            show_state()
        result.setText(app.tr("schedule.saved", time=time_text) if ok else app.tr("schedule.failed"))

    def remove_schedule():
        ok = run_schtasks_elevated(f"/delete /tn {TASK_NAME} /f")
        if ok:
            app.schedule = None
            show_state()
        result.setText(app.tr("schedule.removed") if ok else app.tr("schedule.failed"))

    row = QHBoxLayout()
    row.addWidget(button(app.tr("schedule.save"), "primary", save_schedule))
    row.addWidget(button(app.tr("schedule.remove"), None, remove_schedule))
    row.addStretch()
    inner.addLayout(row)
    inner.addWidget(result)
    box.addWidget(card)

    card, inner = panel()
    inner.addWidget(label(app.tr("schedule.notes"), "hint", wrap=True))
    box.addWidget(card)
    box.addStretch()
    return page
