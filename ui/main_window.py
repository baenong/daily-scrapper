import qdarktheme
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QLabel,
    QMessageBox,
    QCheckBox,
    QGraphicsOpacityEffect,
)
from PySide6.QtCore import QPropertyAnimation, QEasingCurve

# core module
from core import data_manager
from core import startup_manager

# Components
from ui.dashboard_tab import DashboardTab
from ui.news_tab import NewsTab
from ui.law_tab import LawTab
from ui.schedule_tab import ScheduleTab


class DailyScraper(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("뉴스 법령 스크래퍼")
        self.resize(1264, 800)

        # 설정 데이터 불러오기
        self.settings = data_manager.load_settings()

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # 탭 구성
        self.dashboard_tab = DashboardTab(self.settings, self.go_to_tab)
        self.news_tab = NewsTab(self.settings)
        self.law_tab = LawTab(self.settings)
        self.schedule_tab = ScheduleTab(self.settings)

        self.tabs.addTab(self.dashboard_tab, "🏠 대시보드")
        self.tabs.addTab(self.news_tab, "📰 뉴스 스크랩")
        self.tabs.addTab(self.law_tab, "⚖️ 법령 개정 알림")
        self.tabs.addTab(self.schedule_tab, "📅 일정 관리")

        bottom_layout = self.setup_footer()
        layout.addLayout(bottom_layout)

        self.tabs.currentChanged.connect(self.on_tab_changed)

    def on_tab_changed(self, index):
        """탭 이동 시 필요한 화면의 데이터를 실시간으로 현행화(새로고침)합니다."""
        if index == 0:
            self.dashboard_tab.load_dashboard_data()
        elif index == 3:
            self.schedule_tab.fetch_data()
            self.schedule_tab.draw_overlays()

    def go_to_tab(self, index):
        self.tabs.setCurrentIndex(index)

    def setup_footer(self):
        """
        Footer : 다크모드, 윈도우 자동실행
        """
        bottom_layout = QHBoxLayout()

        # 테마
        self.theme_checkbox = QCheckBox()
        self.theme_checkbox.setStyleSheet("padding: 5px;")

        is_dark = self.settings.get("dark_mode", True)
        self.theme_checkbox.setChecked(is_dark)
        self.theme_checkbox.toggled.connect(self.toggle_theme)

        bottom_layout.addWidget(self.theme_checkbox)

        # 저작권
        bottom_layout.addStretch()
        copyright_label = QLabel(
            "Copyright 2026. 행정지원과 안민수 All rights reserved."
        )
        copyright_label.setStyleSheet("color: #555555;")
        bottom_layout.addWidget(copyright_label)
        bottom_layout.addStretch()

        # 윈도우 자동실행
        self.startup_checkbox = QCheckBox("💻 윈도우 시작 시 자동 실행")
        self.startup_checkbox.setStyleSheet("color: #777777; padding: 5px;")

        self.startup_checkbox.setChecked(startup_manager.is_startup_enabled())
        self.startup_checkbox.toggled.connect(self.toggle_startup)

        bottom_layout.addWidget(self.startup_checkbox)
        self.toggle_theme(is_dark, animate=False)

        return bottom_layout

    def toggle_startup(self, checked):
        success = startup_manager.set_startup(checked)
        if not success:
            QMessageBox.warning(
                self,
                "오류",
                "시작 프로그램 설정에 실패했습니다.\n백신 프로그램이 차단했는지 확인해 주세요.",
            )

    def toggle_theme(self, checked, animate=True):
        if animate:
            overlay = QLabel(self)
            overlay.setPixmap(self.grab())
            overlay.resize(self.size())
            overlay.move(0, 0)
            overlay.show()

        theme = "dark" if checked else "light"
        qdarktheme.setup_theme(theme)

        if checked:
            self.theme_checkbox.setText("🌙")
        else:
            self.theme_checkbox.setText("☀️")

        self.settings["dark_mode"] = checked
        data_manager.save_settings(self.settings)

        if animate:
            self.opacity_effect = QGraphicsOpacityEffect(overlay)
            overlay.setGraphicsEffect(self.opacity_effect)

            self.animation = QPropertyAnimation(self.opacity_effect, b"opacity")
            self.animation.setDuration(400)
            self.animation.setStartValue(1.0)
            self.animation.setEndValue(0.0)
            self.animation.setEasingCurve(QEasingCurve.InOutQuad)
            self.animation.finished.connect(overlay.deleteLater)
            self.animation.start()
