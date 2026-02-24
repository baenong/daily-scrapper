import sys
from PySide6.QtWidgets import QApplication

# ui 폴더 안의 main_window.py에서 CityHallApp 클래스를 불러옵니다.
from ui.main_window import DailyScraper

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DailyScraper()
    window.show()
    sys.exit(app.exec())
