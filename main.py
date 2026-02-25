import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase, QFont, QIcon

from ui.main_window import DailyScraper


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    font_path = resource_path(os.path.join("resources", "PretendardVariable.ttf"))
    icon_path = resource_path(os.path.join("resources", "icon.ico"))

    if os.path.exists(font_path):
        font_id = QFontDatabase.addApplicationFont(font_path)
        if font_id != -1:
            font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
            font = QFont(font_family)
            font.setPixelSize(14)
            app.setFont(font)

    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    window = DailyScraper()
    window.show()
    sys.exit(app.exec())
