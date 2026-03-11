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
    QSlider,
    QPushButton,
    QApplication,
)
from PySide6.QtCore import QPropertyAnimation, QEasingCurve, Qt

# core module
from core import data_manager
from core import startup_manager

# Components
from ui.dashboard_tab import DashboardTab
from ui.news_tab import NewsTab
from ui.law_tab import LawTab
from ui.schedule_tab import ScheduleTab
from ui.policy_tab import PolicyTab


class DailyScraper(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("뉴스 법령 스크래퍼")
        # self.resize(1600, 900)

        # 설정 데이터 불러오기
        self.settings = data_manager.load_settings()

        if self.settings.get("window_geometry"):
            self.restoreGeometry(self.settings["window_geometry"])

        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self.main_widget = QWidget()
        self.main_widget.setObjectName("AppBackground")
        self.setCentralWidget(self.main_widget)
        layout = QVBoxLayout(self.main_widget)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # 탭 구성
        self.dashboard_tab = DashboardTab(self.settings, self.go_to_tab)
        self.news_tab = NewsTab(self.settings)
        self.law_tab = LawTab(self.settings)
        self.policy_tab = PolicyTab(self.settings)
        self.schedule_tab = ScheduleTab(self.settings)

        self.tabs.addTab(self.dashboard_tab, "🏠 대시보드")
        self.tabs.addTab(self.news_tab, "📰 뉴스 스크랩")
        self.tabs.addTab(self.law_tab, "⚖️ 법령 개정 알림")
        self.tabs.addTab(self.policy_tab, "🏛️ 정책 브리핑")
        self.tabs.addTab(self.schedule_tab, "📅 일정 관리")

        if self.settings.get("always_on_top", False):
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        self.footer_widget = self.setup_footer()
        layout.addWidget(self.footer_widget)
        self.tabs.currentChanged.connect(self.on_tab_changed)

        self.update_background_opacity()

    def update_background_opacity(self, value=None):
        if value is None:
            value = self.opacity_slider.value()

        is_widget = getattr(self, "is_widget_mode", False)

        if is_widget:
            alpha = value / 100.0
            self.settings["window_opacity"] = value
        else:
            alpha = 1.0

        is_dark = self.settings.get("dark_mode", True)

        if is_dark:
            bg_color = f"rgba(32, 33, 36, {alpha})"
        else:
            bg_color = f"rgba(255, 255, 255, {alpha})"

        style = f"""
            QWidget#AppBackground {{
                background-color: {bg_color};
            }}
            QWidget#FooterContainer {{
                background-color: transparent;
            }}
            QTabWidget::pane {{
                background-color: transparent;
                border: none;
            }}
            QTabWidget > QWidget {{
                background-color: transparent;
            }}
        """
        self.setStyleSheet(style)

    def closeEvent(self, event):
        """위젯 등으로 인한 좀비 프로세스가 남지 않도록 Override"""

        settings_to_save = {
            "window_geometry": self.saveGeometry(),
            "window_opacity": self.opacity_slider.value(),
            "always_on_top": self.top_checkbox.isChecked(),
            "dark_mode": self.settings.get("dark_mode", True),
            "news_limit": self.settings.get("news_limit", 15),
            "news_cond_and": self.settings.get("news_cond_and", True),
        }
        data_manager.save_settings(settings_to_save)

        event.accept()

        app = QApplication.instance()
        if app:
            app.quit()

    def on_tab_changed(self, index):
        if index == 0:
            self.dashboard_tab.load_dashboard_data()
        elif index == 3:
            self.schedule_tab.fetch_data()
            self.schedule_tab.draw_overlays()

    def go_to_tab(self, index):
        self.tabs.setCurrentIndex(index)

    def setup_footer(self):
        footer_container = QWidget()
        footer_container.setObjectName("FooterContainer")
        bottom_layout = QHBoxLayout(footer_container)
        bottom_layout.setContentsMargins(5, 5, 5, 5)

        # 테마 변경
        self.theme_checkbox = QCheckBox()
        self.theme_checkbox.setStyleSheet("padding: 5px;")

        is_dark = self.settings.get("dark_mode", True)
        self.theme_checkbox.setText(" 🌙 " if is_dark else " ☀️ ")
        qdarktheme.setup_theme("dark" if is_dark else "light")
        self.theme_checkbox.setChecked(is_dark)
        self.theme_checkbox.toggled.connect(self.toggle_theme)

        bottom_layout.addWidget(self.theme_checkbox)

        # 3. 바탕화면 위젯 모드 버튼
        self.btn_base_style = """
        border: none; padding: 5px 10px; border-radius: 5px; margin-left: 10px;
        """
        self.widget_btn = QPushButton("🖥️ 바탕화면 위젯 모드")
        self.widget_btn.setCursor(Qt.PointingHandCursor)
        self.widget_btn.setStyleSheet(
            f"background: #E3F2FD; color: #1976D2; {self.btn_base_style}"
        )
        self.widget_btn.clicked.connect(self.toggle_widget_mode)

        self.top_checkbox = QCheckBox("📌 맨 앞 고정")
        self.top_checkbox.setStyleSheet("color: #777;")
        self.top_checkbox.setChecked(self.settings.get("always_on_top", False))
        self.top_checkbox.toggled.connect(self.toggle_always_on_top)

        # 창 투명도 조절
        self.opacity_label = QLabel("  투명도:")

        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(30, 100)  # 30% ~ 100%
        self.opacity_slider.setValue(self.settings.get("window_opacity", 100))
        self.opacity_slider.setFixedWidth(80)
        self.opacity_slider.setCursor(Qt.PointingHandCursor)
        self.opacity_slider.valueChanged.connect(self.update_background_opacity)

        bottom_layout.addWidget(self.widget_btn)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.top_checkbox)
        bottom_layout.addWidget(self.opacity_label)
        bottom_layout.addWidget(self.opacity_slider)

        self.opacity_label.hide()
        self.opacity_slider.hide()

        # 기존 자동 실행 및 설정 버튼
        self.startup_checkbox = QCheckBox("💻 자동 실행")
        self.startup_checkbox.setChecked(startup_manager.is_startup_enabled())
        self.startup_checkbox.toggled.connect(self.toggle_startup)
        bottom_layout.addWidget(self.startup_checkbox)

        return footer_container

    def toggle_always_on_top(self, checked):
        flags = self.windowFlags()
        self.settings["always_on_top"] = checked

        if checked:
            self.setWindowFlags(flags | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(flags & ~Qt.WindowStaysOnTopHint)
        self.show()

    def toggle_widget_mode(self):
        self.is_widget_mode = getattr(self, "is_widget_mode", False)

        if not self.is_widget_mode:
            self.is_widget_mode = True

            self.saved_geometry = self.saveGeometry()

            self.tabs.tabBar().hide()
            # 다른 탭도 위젯화하면 좋을 지 고민해볼 것
            self.tabs.setCurrentIndex(4)  # 탭 추가되면 여기도 수정할 것
            self.setWindowFlags(
                Qt.FramelessWindowHint | Qt.WindowStaysOnBottomHint | Qt.Tool
            )

            self.widget_btn.setText("🔙 창 모드 복귀")
            self.widget_btn.setStyleSheet(
                f"background: #FFEBEE; color: #D32F2F; {self.btn_base_style}"
            )

            self.opacity_label.show()
            self.opacity_slider.show()
            self.update_background_opacity()

            self.show()
        else:
            self.is_widget_mode = False
            self.tabs.tabBar().show()

            flags = Qt.Window
            if self.top_checkbox.isChecked():
                flags |= Qt.WindowStaysOnTopHint
            self.setWindowFlags(flags)

            self.widget_btn.setText("🖥️ 바탕화면 위젯 모드")
            self.widget_btn.setStyleSheet(
                f"background: #E3F2FD; color: #1976D2; {self.btn_base_style}"
            )

            self.opacity_label.hide()
            self.opacity_slider.hide()
            self.update_background_opacity()

            self.show()
            QApplication.processEvents()

            if hasattr(self, "saved_geometry"):
                self.restoreGeometry(self.saved_geometry)

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

        self.theme_checkbox.setText(" 🌙 " if checked else " ☀️ ")
        self.settings["dark_mode"] = checked

        self.update_background_opacity()

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
