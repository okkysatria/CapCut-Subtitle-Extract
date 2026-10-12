import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from gui.main_window import MainWindow
from styles.theme import STYLESHEET


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("CapCut Subtitle Extract")
    app.setOrganizationName("CapCutSubtitleExtract")
    app.setStyle("Fusion")
    font = QFont()
    font.setFamilies(["Segoe UI", "Inter", "Noto Sans", "Sans Serif"])
    font.setPointSize(10)
    app.setFont(font)
    app.setStyleSheet(STYLESHEET)

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
