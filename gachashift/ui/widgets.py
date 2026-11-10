"""Small building blocks used across the pages."""

import os

from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (QAbstractButton, QButtonGroup, QFileDialog, QFrame,
                               QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QLineEdit, QPushButton,
                               QVBoxLayout, QWidget)

from . import theme


def label(text, name=None, wrap=False):
    widget = QLabel(text)
    if name:
        widget.setObjectName(name)
    widget.setWordWrap(wrap)
    return widget


def button(text, name=None, on_click=None):
    widget = QPushButton(text)
    if name:
        widget.setObjectName(name)
    widget.setCursor(Qt.PointingHandCursor)
    if on_click:
        widget.clicked.connect(on_click)
    return widget


def panel(name="panel", margins=(20, 16, 20, 16), spacing=10):
    frame = QFrame()
    frame.setObjectName(name)
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(*margins)
    layout.setSpacing(spacing)
    return frame, layout


def shadowed(widget):
    """A soft dark shadow, for text that sits straight on the background image."""
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(14)
    effect.setOffset(0, 1)
    effect.setColor(QColor(0, 0, 0, 200))
    widget.setGraphicsEffect(effect)
    return widget


def restyle(widget):
    """Re-apply the stylesheet after changing a dynamic property such as error=true."""
    widget.style().unpolish(widget)
    widget.style().polish(widget)


class Toggle(QAbstractButton):
    """An on/off switch in the accent colour."""

    def __init__(self, checked=False):
        super().__init__()
        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(46, 26)

    def sizeHint(self):
        return QSize(46, 26)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(theme.current.accent if self.isChecked() else theme.LINE))
        p.drawRoundedRect(QRectF(0, 3, 46, 20), 10, 10)
        p.setBrush(QColor(theme.TEXT))
        p.drawEllipse(QRectF(25 if self.isChecked() else 3, 5, 16, 16))


class ImageBox(QWidget):
    """An image cropped to fill a rounded rectangle, or a soft placeholder when there is none."""

    def __init__(self, path="", width=56, height=56, radius=10, fixed=True):
        super().__init__()
        self.radius = radius
        self.pixmap = QPixmap()
        self.set_path(path)
        if fixed:
            self.setFixedSize(width, height)
        else:
            self.setFixedHeight(height)

    def set_path(self, path):
        self.pixmap = QPixmap(path) if path and os.path.exists(path) else QPixmap()
        self.update()

    def has_image(self):
        return not self.pixmap.isNull()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        rect = QRectF(self.rect())
        clip = QPainterPath()
        clip.addRoundedRect(rect, self.radius, self.radius)
        p.setClipPath(clip)
        if self.pixmap.isNull():
            p.fillRect(rect, QColor(theme.LINE))
            return
        scaled = self.pixmap.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        x = (scaled.width() - self.width()) // 2
        y = (scaled.height() - self.height()) // 2
        p.drawPixmap(0, 0, scaled, x, y, self.width(), self.height())


class Choice(QWidget):
    """A row of joined buttons where exactly one is selected (official / steam, asia / ...)."""

    changed = Signal(str)

    def __init__(self, options, current):
        super().__init__()
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(1)
        self.group = QButtonGroup(self)
        for value, text in options:
            b = button(text, "seg")
            b.setCheckable(True)
            b.setChecked(value == current)
            b.clicked.connect(lambda _=False, v=value: self.changed.emit(v))
            self.group.addButton(b)
            row.addWidget(b)
        row.addStretch()
        buttons = self.group.buttons()
        if buttons:  # round only the outer corners
            buttons[0].setStyleSheet("border-top-left-radius: 8px; border-bottom-left-radius: 8px;")
            buttons[-1].setStyleSheet("border-top-right-radius: 8px; border-bottom-right-radius: 8px;")


class DayChips(QWidget):
    """Seven toggle chips, Monday first."""

    changed = Signal(list)

    def __init__(self, names, days):
        super().__init__()
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        self.chips = []
        for index, name in enumerate(names):
            chip = button(name, "chip")
            chip.setCheckable(True)
            chip.setChecked(index in days)
            chip.toggled.connect(self.emit_days)
            self.chips.append(chip)
            row.addWidget(chip)
        row.addStretch()

    def emit_days(self):
        self.changed.emit([i for i, chip in enumerate(self.chips) if chip.isChecked()])


class Field(QWidget):
    """Label, one-line hint, input box with an optional side button, and an error line."""

    def __init__(self, title, hint, value, side_text=None, on_side=None):
        super().__init__()
        box = QVBoxLayout(self)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(4)
        box.addWidget(label(title, "h2"))
        if hint:
            box.addWidget(label(hint, "hint", wrap=True))
        row = QHBoxLayout()
        row.setSpacing(8)
        self.edit = QLineEdit(value)
        row.addWidget(self.edit, 1)
        if side_text:
            row.addWidget(button(side_text, None, on_side))
        box.addLayout(row)
        self.error = label("", "error")
        self.error.hide()
        box.addWidget(self.error)

    def set_error(self, text):
        self.edit.setProperty("error", "true" if text else "false")
        restyle(self.edit)
        self.error.setText(text)
        self.error.setVisible(bool(text))


def pick_file(parent, kind, start=""):
    """A file or folder chosen by the user, or "" if they cancelled."""
    start = os.path.dirname(start) if start else ""
    if kind == "dir":
        path = QFileDialog.getExistingDirectory(parent, "", start)
    elif kind == "exe":
        path, _ = QFileDialog.getOpenFileName(parent, "", start, "Programs (*.exe)")
    elif kind == "image":
        path, _ = QFileDialog.getOpenFileName(parent, "", start, "Images (*.png *.jpg *.jpeg *.webp *.bmp)")
    else:
        path, _ = QFileDialog.getOpenFileName(parent, "", start)
    return os.path.normpath(path) if path else ""
