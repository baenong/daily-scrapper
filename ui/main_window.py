import keyboard
import qdarktheme
from PySide6.QtGui import QMouseEvent, QCloseEvent, QAction
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
    QApplication,
    QSizeGrip,
    QSystemTrayIcon,
    QMenu,
)
from PySide6.QtCore import QPropertyAnimation, QEasingCurve, Qt, Signal, QObject

# core module
from core import startup_manager
from core.data_manager import SettingsManager
from core.style import COLORS, tw, tw_sheet

# Components
from ui.components import StyledButton
from ui.dashboard_tab import DashboardTab
from ui.news_tab import NewsTab
from ui.law_tab import LawTab
from ui.schedule_tab import ScheduleTab
from ui.policy_tab import PolicyTab
from ui.roadmap_tab import RoadmapTab
from ui.help_dialog import HelpDialog


class HotKeySignal(QObject):
    activated = Signal()


class DailyScraper(QMainWindow):
    def __init__(self):
        super().__init__()

        self.is_widget_mode = False
        self.drag_pos = None
        self.is_quitting = False

        self.setWindowTitle("G-Daily")

        # 설정 데이터 불러오기
        self.settings = SettingsManager.load()

        if self.settings.get("window_geometry"):
            self.restoreGeometry(self.settings["window_geometry"])

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

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
        self.roadmap_tab = RoadmapTab(self.settings)

        self.tabs.addTab(self.dashboard_tab, "🏠 대시보드")
        self.tabs.addTab(self.news_tab, "📰 뉴스 스크랩")
        self.tabs.addTab(self.law_tab, "⚖️ 법령 개정 알림")
        self.tabs.addTab(self.policy_tab, "🏛️ 정책 브리핑")
        self.tabs.addTab(self.schedule_tab, "📅 일정 관리")
        self.tabs.addTab(self.roadmap_tab, "🗺️ 연간 로드맵")

        if self.settings.get("always_on_top", False):
            self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)

        self.footer_widget = self.setup_footer()
        layout.addWidget(self.footer_widget)
        self.tabs.currentChanged.connect(self.on_tab_changed)

        # 투명도 설정
        self.update_background_opacity()

        # 글로벌 단축키
        self.hotkey_signal = HotKeySignal()
        self.hotkey_signal.activated.connect(self.bring_to_front)
        keyboard.add_hotkey("ctrl+shift+space", self.hotkey_signal.activated.emit)

        # 시스템 트레이
        self.setup_tray_icon()

    def setup_footer(self):
        footer_container = QWidget()
        footer_container.setObjectName("FooterContainer")
        bottom_layout = QHBoxLayout(footer_container)
        bottom_layout.setContentsMargins(5, 5, 5, 5)

        # 테마 변경
        self.theme_checkbox = QCheckBox()
        self.theme_checkbox.setStyleSheet(tw("p-5"))

        is_dark = self.settings.get("dark_mode", True)
        self.theme_checkbox.setText(" 🌙 " if is_dark else " ☀️ ")
        qdarktheme.setup_theme("dark" if is_dark else "light")
        self.theme_checkbox.setChecked(is_dark)
        self.theme_checkbox.toggled.connect(self.toggle_theme)

        # 바탕화면 위젯 모드 버튼
        self.widget_btn = StyledButton(
            "🖥️ 위젯 모드", COLORS["blue-300"], COLORS["blue-700"]
        )
        self.widget_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.widget_btn.clicked.connect(self.toggle_widget_mode)

        self.top_checkbox = QCheckBox("📌 맨 앞 고정")
        self.top_checkbox.setStyleSheet(tw("text-c77", "mr-5"))
        self.top_checkbox.setChecked(self.settings.get("always_on_top", False))
        self.top_checkbox.toggled.connect(self.toggle_always_on_top)

        # 창 투명도 조절
        self.opacity_label = QLabel("  투명도:")
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(30, 100)  # 30% ~ 100%
        self.opacity_slider.setValue(self.settings.get("window_opacity", 100))
        self.opacity_slider.setFixedWidth(80)
        self.opacity_slider.setCursor(Qt.CursorShape.PointingHandCursor)
        self.opacity_slider.valueChanged.connect(self.update_background_opacity)

        # 기존 자동 실행 및 설정 버튼
        self.startup_checkbox = QCheckBox("💻 자동실행")
        self.startup_checkbox.setStyleSheet(tw("text-c77", "mr-5"))
        self.startup_checkbox.setChecked(startup_manager.is_startup_enabled())
        self.startup_checkbox.toggled.connect(self.toggle_startup)

        # 도움말
        self.help_btn = StyledButton("도움말", COLORS["green-300"], COLORS["c13"])
        self.help_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.help_btn.clicked.connect(self.show_help_dialog)

        bottom_layout.addWidget(self.theme_checkbox)
        bottom_layout.addWidget(self.widget_btn)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.top_checkbox)
        bottom_layout.addWidget(self.opacity_label)
        bottom_layout.addWidget(self.opacity_slider)
        bottom_layout.addWidget(self.startup_checkbox)
        bottom_layout.addWidget(self.help_btn)

        self.opacity_label.hide()
        self.opacity_slider.hide()

        # Size Grip
        self.size_grip = QSizeGrip(self)
        self.size_grip.setFixedSize(16, 16)
        self.size_grip.setStyleSheet(tw("bg-transparent"))
        bottom_layout.addWidget(
            self.size_grip,
            0,
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight,
        )
        self.size_grip.hide()

        return footer_container

    def setup_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.windowIcon())
        self.tray_icon.setToolTip("G-Daily")

        tray_menu = QMenu()

        open_action = QAction("활성화", self)
        open_action.triggered.connect(self.bring_to_front)

        tray_menu.addAction(open_action)
        tray_menu.addSeparator()

        exit_action = QAction("프로그램 종료", self)
        exit_action.triggered.connect(self.quit_app)

        tray_menu.addAction(exit_action)
        self.tray_icon.setContextMenu(tray_menu)

        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self.is_widget_mode and event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if (
            self.is_widget_mode
            and event.buttons() == Qt.MouseButton.LeftButton
            and self.drag_pos is not None
        ):
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def show_help_dialog(self):
        if not hasattr(self, "help_dialog") or not self.help_dialog.isVisible():
            self.help_dialog = HelpDialog(parent=self)
            self.help_dialog.show()
        else:
            self.help_dialog.raise_()
            self.help_dialog.activateWindow()

        self.help_dialog.tabs.setCurrentIndex(self.tabs.currentIndex())

    def toggle_always_on_top(self, checked):
        flags = self.windowFlags()
        self.settings["always_on_top"] = checked

        if checked:
            self.setWindowFlags(flags | Qt.WindowType.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(flags & ~Qt.WindowType.WindowStaysOnTopHint)
        self.show()

    def toggle_widget_mode(self):
        if not self.is_widget_mode:
            self.is_widget_mode = True
            self.saved_geometry = self.saveGeometry()

            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint
                | Qt.WindowType.WindowStaysOnBottomHint
                | Qt.WindowType.Tool
            )

            self.widget_btn.setText("🔙 창 모드 복귀")

            self.opacity_label.show()
            self.opacity_slider.show()
            self.size_grip.show()
            self.update_background_opacity()

            self.show()
        else:
            self.is_widget_mode = False

            flags = Qt.WindowType.Window
            if self.top_checkbox.isChecked():
                flags |= Qt.WindowType.WindowStaysOnTopHint
            self.setWindowFlags(flags)

            self.widget_btn.setText("🖥️ 위젯 모드")

            self.opacity_label.hide()
            self.opacity_slider.hide()
            self.size_grip.hide()
            self.update_background_opacity()

            self.showNormal()
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
            self.animation.setDuration(200)
            self.animation.setStartValue(1.0)
            self.animation.setEndValue(0.0)
            self.animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
            self.animation.finished.connect(overlay.deleteLater)
            self.animation.start()

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.bring_to_front()

    def on_tab_changed(self, index):
        if index == 0:
            if not getattr(self.news_tab, "is_loaded", False):
                self.dashboard_tab.load_dashboard_data()
                self.news_tab.is_loaded = True

        elif index == 1:  # 뉴스 탭
            if not getattr(self.news_tab, "is_loaded", False):
                self.news_tab.search_news()
                self.news_tab.is_loaded = True

        elif index == 2:  # 법령 탭
            if not getattr(self.law_tab, "is_loaded", False):
                self.law_tab.refresh_laws()
                self.law_tab.is_loaded = True

        elif index == 3:  # 정책 브리핑 탭
            if not getattr(self.policy_tab, "is_loaded", False):
                self.policy_tab.search_policy()
                self.policy_tab.is_loaded = True

        elif index == 4:  # 일정 탭
            self.schedule_tab.fetch_data()
            self.schedule_tab.draw_overlays()

        elif index == 5:  # 로드맵 탭
            if not getattr(self.roadmap_tab, "is_loaded", False):
                self.roadmap_tab.refresh_data()
                self.roadmap_tab.is_loaded = True

    def update_background_opacity(self, value=None):
        if value is None:
            value = self.opacity_slider.value()

        if self.is_widget_mode:
            alpha = value
            self.settings["window_opacity"] = value
        else:
            alpha = 100

        is_dark = self.settings.get("dark_mode", True)
        bg_color = f"bg-c13-{alpha}" if is_dark else f"bg-white-{alpha}"

        self.setStyleSheet(
            tw_sheet(
                {
                    "QWidget#AppBackground": bg_color,
                    "QWidget#FooterContainer": "bg-transparent",
                    "QTabWidget::pane": "bg-transparent border-none",
                    "QTabWidget > QWidget": "bg-transparent",
                }
            )
        )

    def go_to_tab(self, index):
        self.tabs.setCurrentIndex(index)

    def bring_to_front(self):
        if self.is_widget_mode:
            self.toggle_widget_mode()

        if self.isMinimized():
            self.showNormal()

        self.show()
        self.raise_()
        self.activateWindow()

    def quit_app(self):
        self.is_quitting = True
        self.close()

    def closeEvent(self, event: QCloseEvent):
        """
        1. 종료 버튼을 클릭하여 종료 시 시스템 트레이로 내려가도록 설정
        2. 위젯 등으로 인한 좀비 프로세스가 남지 않도록 Override
        """

        if not self.is_quitting:
            event.ignore()
            self.hide()

            # 트레이 최소화 알림
            if hasattr(self, "tray_icon"):
                self.tray_icon.showMessage(
                    "G-Daily",
                    "프로그램 트레이로 최소화되었습니다.\n완전히 종료하려면 아이콘을 우클릭하여 종료해주세요.",
                    QSystemTrayIcon.MessageIcon.Information,
                    2000,
                )
            return

        # 단축키 등록 해제
        try:
            keyboard.unhook_all()
        except:
            pass

        if hasattr(self, "tray_icon"):
            self.tray_icon.hide()

        settings_to_save = {
            "window_geometry": self.saveGeometry(),
            "window_opacity": self.opacity_slider.value(),
            "always_on_top": self.top_checkbox.isChecked(),
            "dark_mode": self.settings.get("dark_mode", True),
            "news_limit": self.settings.get("news_limit", 15),
            "news_cond_and": self.settings.get("news_cond_and", True),
        }
        SettingsManager.save(settings_to_save)

        event.accept()
        app = QApplication.instance()
        if app:
            app.quit()
