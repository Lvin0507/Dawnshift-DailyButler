"""Appearance: background image, panel opacity, accent colour and per-game images.
Everything applies immediately and is kept when the user presses Save."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QButtonGroup, QColorDialog, QHBoxLayout, QSlider, QVBoxLayout,
                               QWidget)

from ..games import GAMES
from ..winutil import plain_name
from . import theme
from .widgets import ImageBox, button, label, panel, pick_file, shadowed


def build(app):
    look = app.cfg["appearance"]
    page = QWidget()
    box = QVBoxLayout(page)
    box.setContentsMargins(0, 0, 8, 8)
    box.setSpacing(12)
    box.addWidget(shadowed(label(app.tr("nav.appearance"), "h1")))

    # background image
    card, inner = panel(spacing=10)
    inner.addWidget(label(app.tr("appearance.background"), "h2"))
    inner.addWidget(label(app.tr("appearance.background_hint"), "hint", wrap=True))
    row = QHBoxLayout()
    row.setSpacing(16)
    preview = ImageBox(look.get("background", ""), 240, 135, 12)
    row.addWidget(preview)
    side = QVBoxLayout()
    side.setSpacing(8)
    current = label(look.get("background") or app.tr("appearance.none"), "muted", wrap=True)
    side.addWidget(current)

    def set_background(path):
        look["background"] = path
        preview.set_path(path)
        current.setText(path or app.tr("appearance.none"))
        app.apply_theme()

    buttons = QHBoxLayout()
    buttons.addWidget(button(app.tr("appearance.choose"), None,
                             lambda: (lambda p: p and set_background(p))(
                                 pick_file(app, "image", look.get("background", "")))))
    buttons.addWidget(button(app.tr("appearance.clear"), None, lambda: set_background("")))
    buttons.addStretch()
    side.addLayout(buttons)
    side.addStretch()
    row.addLayout(side, 1)
    inner.addLayout(row)
    box.addWidget(card)

    # panel opacity
    card, inner = panel(spacing=8)
    head = QHBoxLayout()
    head.addWidget(label(app.tr("appearance.opacity"), "h2"))
    head.addStretch()
    value = label(f"{look.get('panel_opacity', 82)}%", "muted")
    head.addWidget(value)
    inner.addLayout(head)
    inner.addWidget(label(app.tr("appearance.opacity_hint"), "hint", wrap=True))
    slider = QSlider(Qt.Horizontal)
    slider.setRange(30, 100)
    slider.setValue(int(look.get("panel_opacity", 82)))

    def set_opacity(v):
        look["panel_opacity"] = v
        value.setText(f"{v}%")
        app.apply_theme()

    slider.valueChanged.connect(set_opacity)
    inner.addWidget(slider)
    box.addWidget(card)

    # accent colour
    card, inner = panel(spacing=10)
    inner.addWidget(label(app.tr("appearance.accent"), "h2"))
    row = QHBoxLayout()
    row.setSpacing(10)
    group = QButtonGroup(page)
    accent = look.get("accent") or theme.ACCENTS[0]
    for color in theme.ACCENTS:
        swatch = button("", "swatch")
        swatch.setCheckable(True)
        swatch.setChecked(color.lower() == accent.lower())
        swatch.setStyleSheet(f"background: {color};")
        swatch.clicked.connect(lambda _=False, c=color: set_accent(c))
        group.addButton(swatch)
        row.addWidget(swatch)

    def set_accent(color):
        look["accent"] = color
        app.apply_theme()

    def custom():
        chosen = QColorDialog.getColor(QColor(look.get("accent") or theme.ACCENTS[0]), app)
        if chosen.isValid():
            set_accent(chosen.name())
            app.show_page("appearance")

    row.addSpacing(6)
    row.addWidget(button(app.tr("appearance.custom"), None, custom))
    row.addStretch()
    inner.addLayout(row)
    box.addWidget(card)

    # game images
    card, inner = panel(spacing=10)
    inner.addWidget(label(app.tr("appearance.game_images"), "h2"))
    inner.addWidget(label(app.tr("appearance.game_images_hint"), "hint", wrap=True))
    images = look.setdefault("game_images", {})
    for game_cls in GAMES:
        gid = game_cls.id
        row = QHBoxLayout()
        row.setSpacing(12)
        thumb = ImageBox(images.get(gid, ""), 44, 44, 8)
        row.addWidget(thumb)
        row.addWidget(label(plain_name(gid, app.lang)), 1)

        def set_image(path, gid=gid, thumb=thumb):
            if path:
                images[gid] = path
            else:
                images.pop(gid, None)
            thumb.set_path(path)
            app.changed()

        row.addWidget(button(app.tr("appearance.choose"), None,
                             lambda _=False, g=gid, f=set_image: (lambda p: p and f(p))(
                                 pick_file(app, "image", images.get(g, "")))))
        row.addWidget(button(app.tr("appearance.clear"), None, lambda _=False, f=set_image: f("")))
        inner.addLayout(row)
    box.addWidget(card)
    box.addStretch()
    return page
