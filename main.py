import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase, QFont

from ui.main_window import DailyScraper

if __name__ == "__main__":
    app = QApplication(sys.argv)
    font_path = "PretendardVariable.ttf"

    if os.path.exists(font_path):
        font_id = QFontDatabase.addApplicationFont(font_path)
        if font_id != -1:
            font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
            app.setFont(QFont(font_family, 11))
    else:
        print(f"'{font_path}' 폰트 파일을 찾을 수 없어 윈도우 기본 폰트를 사용합니다.")

    window = DailyScraper()
    window.show()
    sys.exit(app.exec())
