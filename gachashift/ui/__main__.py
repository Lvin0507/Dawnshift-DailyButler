"""Start the app:  python -m gachashift.ui"""

import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from .window import MainWindow


def icon_path():
    """assets/gachashift.ico from source, or the copy bundled inside the exe."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent.parent))
    path = base / "assets" / "gachashift.ico"
    return str(path) if path.exists() else None


def main():
    app = QApplication(sys.argv)
    icon = icon_path()
    if icon:
        app.setWindowIcon(QIcon(icon))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
