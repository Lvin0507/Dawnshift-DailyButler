"""Colours, the stylesheet, and the user's appearance settings (accent, background, opacity).

Panels use semi-transparent colours, and the window paints the background image underneath,
so the image shows through as much as the panel opacity allows."""

from PySide6.QtGui import QColor

BG = "#141B2D"        # window base, deep indigo
PANEL = "#1C2540"     # panels and sidebar
LINE = "#2D3858"      # borders, inactive controls
PICKED = "#46557F"    # selected nav item or choice
TEXT = "#E9E7F2"
MUTED = "#98A1BE"
OK = "#7BD3A0"
FAIL = "#EF7D7D"

ACCENTS = ["#F4B860", "#7AA2F7", "#9ECE6A", "#F7768E", "#BB9AF7", "#73DACA"]


class Theme:
    """The live appearance. Widgets that paint themselves read it on every repaint."""

    def __init__(self):
        self.accent = ACCENTS[0]
        self.opacity = 82
        self.background = ""

    def load(self, appearance):
        self.accent = appearance.get("accent") or ACCENTS[0]
        self.opacity = int(appearance.get("panel_opacity", 82))
        self.background = appearance.get("background") or ""


current = Theme()


def rgba(color, alpha):
    c = QColor(color)
    return f"rgba({c.red()}, {c.green()}, {c.blue()}, {max(0.0, min(1.0, alpha)):.2f})"


def shade(color, factor):
    """Darker (factor < 1) or lighter (factor > 1) version of a colour."""
    c = QColor(color)
    return c.darker(int(100 / factor)).name() if factor < 1 else c.lighter(int(100 * factor)).name()


def stylesheet(lang):
    a = current.opacity / 100
    accent = current.accent
    family = '"Microsoft YaHei UI", "Segoe UI"' if lang == "zh" else '"Segoe UI", "Microsoft YaHei UI"'
    return f"""
* {{ font-family: {family}; font-size: 14px; color: {TEXT}; }}
QToolTip {{ background: {PANEL}; border: 1px solid {LINE}; padding: 4px; }}

QFrame#sidebar {{ background: {rgba(PANEL, min(1.0, a + 0.08))}; border: none; }}
QPushButton#nav {{ text-align: left; padding: 10px 14px; border: none; border-radius: 9px;
                   background: transparent; font-size: 15px; }}
QPushButton#nav:hover {{ background: {rgba(LINE, 0.7)}; }}
QPushButton#nav:checked {{ background: {rgba(PICKED, 0.95)}; }}

QFrame#panel {{ background: {rgba(PANEL, a)}; border-radius: 14px; }}
QFrame#setup {{ background: {rgba(PANEL, a)}; border-radius: 14px; border: 1px solid {rgba(accent, 0.55)}; }}
QFrame#bar {{ background: transparent; }}

QLabel#h1 {{ font-size: 26px; font-weight: 700; }}
QLabel#h2 {{ font-size: 16px; font-weight: 600; }}
QLabel#gamename {{ font-size: 16px; font-weight: 600; }}
QLabel#gamename[off="true"] {{ color: {MUTED}; }}
QLabel#muted {{ color: {MUTED}; font-size: 13px; }}
QLabel#hint {{ color: {MUTED}; font-size: 12px; }}
QLabel#error {{ color: {FAIL}; font-size: 12px; }}
QLabel#ok {{ color: {OK}; font-weight: 600; }}
QLabel#fail {{ color: {FAIL}; font-weight: 600; }}
QLabel#off {{ color: {MUTED}; font-weight: 600; }}
QLabel#status {{ color: {MUTED}; font-size: 13px; }}
QLabel#status[kind="ok"] {{ color: {OK}; }}
QLabel#status[kind="fail"] {{ color: {FAIL}; }}
QLabel#status[kind="accent"] {{ color: {accent}; }}
QLabel#stepdone {{ color: {OK}; font-size: 16px; }}
QLabel#steptodo {{ color: {MUTED}; font-size: 16px; }}

QPushButton {{ background: {rgba(LINE, 0.95)}; border: none; border-radius: 8px; padding: 7px 14px; }}
QPushButton:hover {{ background: {PICKED}; }}
QPushButton:disabled {{ color: {MUTED}; background: {rgba(LINE, 0.5)}; }}
QPushButton#primary {{ background: {accent}; color: {BG}; font-weight: 700; padding: 8px 22px; }}
QPushButton#primary:hover {{ background: {shade(accent, 0.9)}; }}
QPushButton#danger {{ background: {FAIL}; color: {BG}; font-weight: 700; padding: 8px 22px; }}
QPushButton#link {{ background: transparent; color: {accent}; padding: 0; text-align: left; }}
QPushButton#link:hover {{ text-decoration: underline; }}
QPushButton#chip {{ background: {rgba(LINE, 0.95)}; border-radius: 11px; padding: 4px 12px; }}
QPushButton#chip:checked {{ background: {accent}; color: {BG}; font-weight: 600; }}
QPushButton#seg {{ background: {rgba(LINE, 0.95)}; border-radius: 0; padding: 6px 14px; }}
QPushButton#seg:checked {{ background: {PICKED}; color: {TEXT}; }}
QPushButton#swatch {{ border-radius: 13px; padding: 0; min-width: 28px; min-height: 28px;
                      max-width: 28px; max-height: 28px; }}
QPushButton#swatch:checked {{ border: 3px solid {TEXT}; }}

QLineEdit {{ background: {rgba(BG, 0.85)}; border: 1px solid {LINE}; border-radius: 8px;
             padding: 6px 10px; selection-background-color: {accent}; selection-color: {BG}; }}
QLineEdit:focus {{ border: 1px solid {accent}; }}
QLineEdit[error="true"] {{ border: 1px solid {FAIL}; }}

QCheckBox {{ spacing: 10px; }}
QCheckBox::indicator {{ width: 18px; height: 18px; border-radius: 5px; border: 1px solid {LINE};
                        background: {rgba(BG, 0.7)}; }}
QCheckBox::indicator:checked {{ background: {accent}; border: 1px solid {accent}; }}

QSlider::groove:horizontal {{ height: 6px; background: {rgba(LINE, 0.95)}; border-radius: 3px; }}
QSlider::sub-page:horizontal {{ background: {accent}; border-radius: 3px; }}
QSlider::handle:horizontal {{ background: {TEXT}; width: 16px; height: 16px; margin: -5px 0; border-radius: 8px; }}

QPlainTextEdit {{ background: {rgba(BG, min(1.0, a + 0.05))}; border: 1px solid {LINE}; border-radius: 10px;
                  padding: 8px; font-size: 13px; }}
QComboBox {{ background: {rgba(LINE, 0.95)}; border: none; border-radius: 8px; padding: 6px 12px; min-width: 60px; }}
QComboBox:hover {{ background: {PICKED}; }}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox QAbstractItemView {{ background: {PANEL}; border: 1px solid {LINE}; selection-background-color: {PICKED};
                               outline: none; }}

QScrollArea, QScrollArea > QWidget > QWidget, QStackedWidget {{ background: transparent; border: none; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 4px 2px; }}
QScrollBar::handle:vertical {{ background: {rgba(LINE, 0.95)}; border-radius: 4px; min-height: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
"""
