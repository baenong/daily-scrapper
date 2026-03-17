import sys
import os
import ctypes
import time

from dotenv import load_dotenv

if getattr(sys, "frozen", False):
    base_dir = sys._MEIPASS
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))

load_dotenv(os.path.join(base_dir, ".env"))

from PySide6.QtWidgets import QApplication, QSplashScreen
from PySide6.QtGui import QFontDatabase, QFont, QIcon, QColor, QPainter, QPixmap
from PySide6.QtCore import Qt, QRect

from ui.main_window import DailyScraper
from core import db_manager


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


class CustomSplashScreen(QSplashScreen):
    def __init__(self, pixmap):
        super().__init__(pixmap)
        self.setFont(QFont("Malgun Gothic", 10, QFont.Weight.Bold))

    def drawContents(self, painter: QPainter):
        pixmap = self.pixmap()
        painter.drawPixmap(0, 0, pixmap)

        text = self.message()
        if not text:
            return

        rect = self.rect()  # 전체 크기
        text_rect = QRect(0, rect.height() - 50, rect.width(), 30)
        painter.fillRect(text_rect, QColor(0, 0, 0, 180))
        painter.setPen(Qt.GlobalColor.white)  # 글씨 색상
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, text)

        # copyright part
        copyright_font = QFont("Arial", 8)
        painter.setFont(copyright_font)
        rect = self.rect()
        copyright_rect = QRect(0, rect.height() - 20, rect.width(), 20)
        painter.fillRect(copyright_rect, QColor(0, 0, 0, 180))
        painter.setPen(QColor(200, 200, 200))
        copyright_text = "Copyright 2026. 행정지원과 안민수 All rights reserved."
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        painter.drawText(copyright_rect, Qt.AlignmentFlag.AlignCenter, copyright_text)

    def showMessage(self, text):
        super().showMessage(
            text,
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter,
            Qt.GlobalColor.black,
        )


if __name__ == "__main__":
    if sys.platform == "win32":
        myappid = "ahnminsoo.daily-scraper.v1.0"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    app = QApplication(sys.argv)
    db_manager.init_db()

    splash_path = resource_path(os.path.join("resources", "logo.png"))
    splash_pix = QPixmap(splash_path)

    if splash_pix.isNull():
        splash_pix = QPixmap(500, 300)
        splash_pix.fill(Qt.GlobalColor.white)

    splash = CustomSplashScreen(splash_pix)
    splash.showMessage("프로그램 초기화 중...")
    splash.show()
    app.processEvents()

    font_path = resource_path(os.path.join("resources", "PretendardVariable.ttf"))
    icon_path = resource_path(os.path.join("resources", "icon.ico"))

    splash.showMessage("리소스 로드 중...")
    app.processEvents()
    time.sleep(0.5)

    if os.path.exists(font_path):
        font_id = QFontDatabase.addApplicationFont(font_path)

        if font_id != -1:
            font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
            font = QFont(font_family)
            font.setPixelSize(14)
            app.setFont(font)

    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    splash.showMessage("사용자 인터페이스 구성 중...")
    app.processEvents()

    window = DailyScraper()
    window.show()
    splash.finish(window)

    sys.exit(app.exec())
