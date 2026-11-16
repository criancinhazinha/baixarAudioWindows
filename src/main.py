from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from src.ui.main_window import MainWindow
from src.ui.theme import DARK_STUDIO_QSS


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("SonicFetch Desktop")
    app.setOrganizationName("SonicFetch")
    app.setStyle("Fusion")
    app.setStyleSheet(DARK_STUDIO_QSS)

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
