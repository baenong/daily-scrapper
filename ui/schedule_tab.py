import os
import requests
import webbrowser
import xml.etree.ElementTree as ET
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QLabel,
    QHeaderView,
    QDialog,
    QLineEdit,
    QComboBox,
    QDateEdit,
    QCheckBox,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QMenu,
)
from PySide6.QtCore import Qt, QDate, Signal, QTimer
from PySide6.QtGui import QColor, QPixmap, QIcon
from ui.components import TitleLabel, StyledButton
from core import db_manager, law_scraper
from core.worker import AsyncTask


def get_holidays(year, month):
    api_key = os.environ.get("HOLIDAY_API_KEY", "")

    if not api_key:
        return {}

    url = (
        "http://apis.data.go.kr/B090041/openapi/service/SpcdeInfoService/getRestDeInfo"
    )
    params = {
        "solYear": str(year),
        "solMonth": f"{month:02d}",
        "ServiceKey": requests.utils.unquote(api_key),
    }
    try:
        res = requests.get(url, params=params, timeout=3)
        root = ET.fromstring(res.text)
        return {
            f"{item.find('locdate').text[:4]}-{item.find('locdate').text[4:6]}-{item.find('locdate').text[6:]}": item.find(
                "dateName"
            ).text
            for item in root.findall(".//item")
        }
    except:
        return {}


def get_instances(schedule, view_start, view_end):
    """반복 일정을 전개하여 현재 화면(월)에 표시될 '실제 날짜 구간(인스턴스)'들을 계산합니다."""
    instances = []
    ev_start = QDate.fromString(schedule["start_date"], "yyyy-MM-dd")
    ev_end = QDate.fromString(schedule["end_date"], "yyyy-MM-dd")
    duration = ev_start.daysTo(ev_end)
    rtype = schedule.get("repeat_type", "none")
    rep_end_str = schedule.get("repeat_end", "")
    rep_end = QDate.fromString(rep_end_str, "yyyy-MM-dd") if rep_end_str else view_end

    if rtype == "none":
        if ev_start <= view_end and ev_end >= view_start:
            instances.append((ev_start, ev_end))
    elif rtype == "daily":
        actual_end = min(rep_end, view_end)
        if ev_start <= view_end and actual_end >= view_start:
            instances.append((ev_start, actual_end))
    elif rtype == "weekly":
        curr = ev_start
        while curr <= rep_end and curr <= view_end:
            inst_end = curr.addDays(duration)
            if inst_end >= view_start and curr <= view_end:
                instances.append((curr, inst_end))
            curr = curr.addDays(7)
    elif rtype == "monthly":
        curr = ev_start
        while curr <= rep_end and curr <= view_end:
            inst_end = curr.addDays(duration)
            if inst_end >= view_start and curr <= view_end:
                instances.append((curr, inst_end))
            curr = curr.addMonths(1)
    return instances


class PopUpTitle(QLabel):
    def __init__(self, text):
        super().__init__(text)
        self.setStyleSheet(f"font-weight:bold; font-size: 18px; margin: 15px 0 5px 0;")


class EventDialog(QDialog):
    """일정 관리 팝업"""

    def __init__(self, date_str, schedule_data=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("일정 관리")
        self.setFixedSize(380, 450)
        self.schedule_data = schedule_data

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("일정 제목")
        layout.addWidget(PopUpTitle("📌 일정 제목"))
        layout.addWidget(self.title_input)

        date_layout = QHBoxLayout()
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.fromString(date_str, "yyyy. MM. dd"))
        self.start_date.setMinimumWidth(160)

        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.fromString(date_str, "yyyy. MM. dd"))
        self.end_date.setMinimumWidth(160)

        date_layout.addWidget(self.start_date)
        date_layout.addWidget(QLabel("~"))
        date_layout.addWidget(self.end_date)
        layout.addWidget(PopUpTitle("📅 기간 설정"))
        layout.addLayout(date_layout)

        repeat_layout = QHBoxLayout()
        self.repeat_combo = QComboBox()
        self.repeat_combo.addItems(["반복 없음", "매일", "매주", "매월"])
        self.repeat_combo.setMinimumWidth(120)

        self.repeat_end = QDateEdit()
        self.repeat_end.setCalendarPopup(True)
        self.repeat_end.setDate(QDate.currentDate().addYears(1))
        self.repeat_end.setEnabled(False)
        self.repeat_combo.currentIndexChanged.connect(
            lambda: self.repeat_end.setEnabled(self.repeat_combo.currentIndex() != 0)
        )
        self.repeat_end.setMinimumWidth(170)

        repeat_layout.addWidget(self.repeat_combo)
        repeat_layout.addStretch()
        repeat_layout.addWidget(QLabel("종료일:"))
        repeat_layout.addWidget(self.repeat_end)
        layout.addWidget(PopUpTitle("🔁 반복 설정"))
        layout.addLayout(repeat_layout)

        # Color Section
        layout.addWidget(PopUpTitle("🎨 일정 색상"))

        color_layout = QHBoxLayout()
        self.color_combo = QComboBox()
        self.color_combo.setMinimumWidth(110)
        self.colors = {
            "빨간색": "#FF968A",
            "주황색": "#FFAD60",
            "노란색": "#F4D980",
            "초록색": "#B2FBA5",
            "파란색": "#A9CBD7",
            "보라색": "#C4BEE2",
        }
        self.color_preview = QLabel()
        self.color_preview.setFixedSize(20, 20)

        for name, hex_color in self.colors.items():
            pixmap = QPixmap(16, 16)
            pixmap.fill(QColor(hex_color))
            self.color_combo.addItem(QIcon(pixmap), name)

        self.color_combo.currentIndexChanged.connect(self.update_color_preview)
        self.update_color_preview()

        color_layout.addWidget(self.color_combo)
        color_layout.addWidget(self.color_preview)
        color_layout.addStretch()
        layout.addLayout(color_layout)

        # 완료 여부 체크
        self.is_completed_cb = QCheckBox("✅ 이 일정을 완료했습니다.")
        self.is_completed_cb.setStyleSheet("margin-top: 10px;")
        layout.addWidget(self.is_completed_cb)
        layout.addStretch()

        btn_layout = QHBoxLayout()
        self.save_btn = StyledButton("저장", "#4CAF50")
        self.cancel_btn = StyledButton("취소", "transparent", "#555555")
        self.save_btn.clicked.connect(self.save_event)
        self.cancel_btn.clicked.connect(self.reject)

        if self.schedule_data:
            self.delete_btn = StyledButton("삭제", "#F44336")
            self.delete_btn.clicked.connect(self.delete_event)
            btn_layout.addWidget(self.delete_btn)
            self.load_existing_data()

        btn_layout.addStretch()
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.save_btn)
        layout.addLayout(btn_layout)

    def update_color_preview(self):
        selected_color = self.colors[self.color_combo.currentText()]
        self.color_preview.setStyleSheet(
            f"background-color: {selected_color}; border-radius: 10px; border: 1px solid #CCCCCC;"
        )

    def load_existing_data(self):
        self.title_input.setText(self.schedule_data["title"])
        self.start_date.setDate(
            QDate.fromString(self.schedule_data["start_date"], "yyyy-MM-dd")
        )
        self.end_date.setDate(
            QDate.fromString(self.schedule_data["end_date"], "yyyy-MM-dd")
        )
        self.is_completed_cb.setChecked(self.schedule_data.get("is_completed", False))
        rtype = self.schedule_data["repeat_type"]
        self.repeat_combo.setCurrentIndex(
            1
            if rtype == "daily"
            else 2 if rtype == "weekly" else 3 if rtype == "monthly" else 0
        )
        if self.schedule_data["repeat_end"]:
            self.repeat_end.setDate(
                QDate.fromString(self.schedule_data["repeat_end"], "yyyy-MM-dd")
            )
        for key, val in self.colors.items():
            if val == self.schedule_data["color"]:
                self.color_combo.setCurrentText(key)

    def save_event(self):
        title = self.title_input.text().strip()
        if not title:
            return
        start_str = self.start_date.date().toString("yyyy-MM-dd")
        end_str = self.end_date.date().toString("yyyy-MM-dd")
        rtype_map = {0: "none", 1: "daily", 2: "weekly", 3: "monthly"}
        repeat_type = rtype_map[self.repeat_combo.currentIndex()]
        repeat_end_str = (
            self.repeat_end.date().toString("yyyy-MM-dd")
            if repeat_type != "none"
            else ""
        )
        color_hex = self.colors[self.color_combo.currentText()]
        is_completed = self.is_completed_cb.isChecked()

        if self.schedule_data:
            db_manager.update_schedule(
                self.schedule_data["id"],
                title,
                start_str,
                end_str,
                repeat_type,
                repeat_end_str,
                color_hex,
                is_completed,
            )
        else:
            db_manager.add_schedule(
                title,
                start_str,
                end_str,
                repeat_type,
                repeat_end_str,
                color_hex,
                is_completed,
            )
        self.accept()

    def delete_event(self):
        db_manager.delete_schedule(self.schedule_data["id"])
        self.accept()


class DailyEventRowWidget(QWidget):
    """더보기 팝업 내부에 들어갈 개별 일정(체크박스+제목+삭제버튼) 위젯"""

    def __init__(self, schedule_data, parent_dialog):
        super().__init__()
        self.schedule_data = schedule_data
        self.parent_dialog = parent_dialog
        is_law = schedule_data.get("is_law", False)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(1, 1, 1, 1)

        container = QWidget()
        container.setAttribute(Qt.WA_StyledBackground, True)

        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        main_layout.addWidget(container)

        # 1. 완료 체크박스
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(schedule_data.get("is_completed", False))
        self.checkbox.toggled.connect(self.on_toggle)
        if is_law:
            self.checkbox.hide()

        # 2. 제목 라벨 (더블클릭 편집 지원)
        self.title_label = QLabel(schedule_data["title"])
        self.title_label.setCursor(Qt.PointingHandCursor)

        base_style = "padding: 5px;"
        base_container_style = "border-radius: 4px; padding: 10px 0 10px 5px;"

        if self.checkbox.isChecked():
            self.title_label.setStyleSheet(
                f"{base_style} color: gray; text-decoration: line-through;"
            )
            container.setStyleSheet(base_container_style)
        else:
            self.title_label.setStyleSheet(f"{base_style} color: #131313;")

            base_color = QColor(schedule_data["color"]).lighter(110).name()
            container.setStyleSheet(
                f"{base_container_style} background-color: {base_color};"
            )

        # 3. 삭제 버튼
        self.btn_del = StyledButton("❌", "transparent", "#F44336", padding="2px")
        self.btn_del.setFixedWidth(35)
        self.btn_del.setFixedHeight(30)
        self.btn_del.clicked.connect(self.on_delete)

        layout.addWidget(self.checkbox)
        layout.addWidget(self.title_label, stretch=1)
        layout.addWidget(self.btn_del)

    def mouseDoubleClickEvent(self, event):
        if self.schedule_data.get("is_law"):
            webbrowser.open(self.schedule_data.get("link", ""))
        else:
            dialog = EventDialog(
                self.schedule_data["start_date"],
                schedule_data=self.schedule_data,
                parent=self.parent_dialog,
            )
            if dialog.exec():
                self.parent_dialog.refresh_data()

    def on_toggle(self, checked):
        s = self.schedule_data
        db_manager.update_schedule(
            s["id"],
            s["title"],
            s["start_date"],
            s["end_date"],
            s["repeat_type"],
            s["repeat_end"],
            s["color"],
            checked,
        )
        self.parent_dialog.refresh_data()

    def on_delete(self):
        reply = QMessageBox.question(
            self, "삭제", "일정을 삭제하시겠습니까?", QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            db_manager.delete_schedule(self.schedule_data["id"])
            self.parent_dialog.refresh_data()


class DailyEventsDialog(QDialog):
    """특정 날짜의 일정을 체크박스 형태로 보여주는 팝업 창"""

    def __init__(self, date_obj, parent_tab=None):
        super().__init__(parent_tab)
        self.date_obj = date_obj
        self.parent_tab = parent_tab
        self.date_str = date_obj.toString("yyyy. MM. dd")

        self.setWindowTitle(f"{self.date_str} 일정 목록")
        self.setFixedSize(320, 500)

        self.layout = QVBoxLayout(self)
        self.layout.addWidget(TitleLabel(f"{date_obj.toString("yy. MM. dd.")}"))

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(
            """
            QListWidget { border: 1px solid #999999;
                          border-radius: 5px;
                          margin: 10px 0;
                          padding: 3px; }
            """
        )
        self.layout.addWidget(self.list_widget)

        btn_layout = QHBoxLayout()

        self.add_btn = StyledButton("신규 일정", "#2196F3", padding="10px")
        self.add_btn.clicked.connect(self.add_new_event)

        btn_layout.addStretch()
        btn_layout.addWidget(self.add_btn)

        self.layout.addLayout(btn_layout)
        self.load_events()

    def add_new_event(self):
        dialog = EventDialog(self.date_str, parent=self)
        if dialog.exec():
            self.refresh_data()

    def load_events(self):
        self.list_widget.clear()
        day_events = []

        source_schedules = (
            self.parent_tab.schedules_cache
            if self.parent_tab
            else db_manager.get_schedules()
        )

        for s in source_schedules:
            if get_instances(s, self.date_obj, self.date_obj):
                day_events.append(s)

        day_events.sort(key=lambda x: x.get("is_completed", False))

        for ev in day_events:
            item = QListWidgetItem(self.list_widget)
            row_widget = DailyEventRowWidget(ev, self)
            item.setSizeHint(row_widget.sizeHint())
            self.list_widget.setItemWidget(item, row_widget)

    def refresh_data(self):
        """데이터 변경 시 팝업 내용과 뒤에 있는 달력 화면을 즉시 동기화합니다."""
        if self.parent_tab:
            self.parent_tab.fetch_data()

        self.load_events()

        if self.parent_tab:
            self.parent_tab.draw_overlays()


class ClickableEventLabel(QLabel):
    """뷰포트 위에 둥둥 떠다닐 클릭 가능한 막대 위젯"""

    # Signals
    doubleClicked = Signal(dict)
    statusToggled = Signal(dict)
    deleteRequested = Signal(dict)
    editRequested = Signal(dict)

    def __init__(self, schedule_data, text, parent=None):
        super().__init__(text, parent)
        self.schedule_data = schedule_data
        self.setCursor(Qt.PointingHandCursor)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.schedule_data.get("is_law"):
                webbrowser.open(self.schedule_data.get("link", ""))
            else:
                self.doubleClicked.emit(self.schedule_data)
            event.accept()

    def contextMenuEvent(self, event):
        """우클릭 시 실행되는 컨텍스트 메뉴입니다."""
        menu = QMenu(self)
        menu.setStyleSheet(
            """
            QMenu { 
                background-color: white; 
                border: 1px solid #CCCCCC; 
                padding: 5px;
                font-size: 13px; 
                color: black;
                text-decoration: none; /* 핵심: 부모의 취소선 상속을 차단합니다! */
            } 
            QMenu::item { 
                padding: 6px 20px; 
                text-decoration: none; /* 아이템에도 취소선 차단 */
            } 
            QMenu::item:selected { 
                background-color: #F0F0F0; 
            }
            QMenu::item:disabled {
                color: #333333;
                font-weight: bold;
                background-color: #FAFAFA; /* 제목 영역 배경을 살짝 다르게 */
            }
            QMenu::separator {
                height: 1px;
                background: #E0E0E0;
                margin: 2px 0px;
            }
        """
        )

        title_action = menu.addAction(f"🏷️ {self.schedule_data['title']}")
        title_action.setEnabled(False)

        menu.addSeparator()

        if self.schedule_data.get("is_law"):
            action_link = menu.addAction("🔗 국가법령정보센터에서 보기")

            original_style = self.styleSheet()
            self.setStyleSheet(original_style + "border: 2px solid #333333;")
            action = menu.exec(event.globalPos())
            self.setStyleSheet(original_style)

            if action == action_link:
                webbrowser.open(self.schedule_data.get("link", ""))
            return

        is_completed = self.schedule_data.get("is_completed", False)
        status_text = "미완료 처리" if is_completed else "완료 처리"

        action_toggle = menu.addAction(f"✅ {status_text}")
        action_edit = menu.addAction("✏️ 편집")
        action_delete = menu.addAction("🗑️ 삭제")

        original_style = self.styleSheet()
        self.setStyleSheet(original_style + "border: 2px solid #333333;")
        action = menu.exec(event.globalPos())
        self.setStyleSheet(original_style)

        if action == action_toggle:
            self.statusToggled.emit(self.schedule_data)
        elif action == action_edit:
            self.editRequested.emit(self.schedule_data)
        elif action == action_delete:
            self.deleteRequested.emit(self.schedule_data)


class ClickableMoreLabel(QLabel):
    """'+N개 더보기' 텍스트를 클릭할 수 있게 만든 커스텀 라벨입니다."""

    clicked = Signal(QDate)

    def __init__(self, date_obj, parent=None):
        super().__init__(parent)
        self.date_obj = date_obj
        self.setCursor(Qt.PointingHandCursor)  # 마우스 오버 시 손가락 모양으로 변경

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.date_obj)


class ClickableDateLabel(QLabel):
    clicked = Signal(QDate)

    def __init__(self, date_obj, text, parent=None):
        super().__init__(text, parent)
        self.date_obj = date_obj
        self.setCursor(Qt.PointingHandCursor)  # 마우스 오버 시 손가락 모양

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.date_obj)


class CustomCalendarCell(QWidget):
    """표의 배경을 담당하는 셀 (날짜와 '+N 더보기'만 표시)"""

    def __init__(self, date_obj, parent_tab):
        super().__init__()
        self.setAttribute(Qt.WA_StyledBackground, True)

        self.date_obj = date_obj
        self.parent_tab = parent_tab
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 2, 0, 2)

        self.date_label = ClickableDateLabel(date_obj, str(date_obj.day()))
        self.date_label.setAlignment(Qt.AlignRight | Qt.AlignTop)
        self.date_label.setContentsMargins(0, 0, 5, 0)
        self.date_label.clicked.connect(self.parent_tab.show_daily_events)

        if date_obj.dayOfWeek() == 7:
            self.date_label.setStyleSheet("color: red;")
        elif date_obj.dayOfWeek() == 6:
            self.date_label.setStyleSheet("color: blue;")
        self.layout.addWidget(self.date_label)

        self.more_label = ClickableMoreLabel(date_obj)
        self.more_label.setStyleSheet("color: gray; font-size: 12px;")
        self.more_label.setAlignment(Qt.AlignCenter)
        self.more_label.clicked.connect(self.parent_tab.show_daily_events)
        self.more_label.hide()
        self.layout.addStretch()
        self.layout.addWidget(self.more_label)

    def set_more_count(self, count):
        if count > 0:
            self.more_label.setText(f"+ {count}개 더보기")
            self.more_label.show()
        else:
            self.more_label.hide()


class OverlayTableWidget(QTableWidget):
    """창 크기가 변할 때 오버레이 막대들의 위치도 재계산하도록 시그널을 보내는 커스텀 테이블"""

    resized = Signal()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.resized.emit()


class ScheduleTab(QWidget):
    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.current_date = QDate.currentDate()
        self.holidays_cache = {}
        self.schedules_cache = []
        self.overlay_widgets = []  # 띄워놓은 막대들을 추적
        self.date_to_cell = {}  # 날짜 -> (row, col) 매핑

        self.setup_ui()
        self.build_calendar()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        nav_layout = QHBoxLayout()

        # 오늘 버튼
        self.today_btn = StyledButton("오늘", "#E3F2FD", "#1976D2")

        # 이전 달 버튼
        self.prev_btn = StyledButton("◀ 이전 달", "transparent", "#777777")

        self.year_combo = QComboBox()
        self.month_combo = QComboBox()

        self.year_combo.addItems([f"{y}년" for y in range(2000, 2051)])
        self.month_combo.addItems([f"{m}월" for m in range(1, 13)])

        combo_style = """
            QComboBox { 
                font-size: 16px; 
                border: 1px solid #DDDDDD; 
                border-radius: 5px; 
                padding: 2px 10px; 
                background-color: white;
                color: #555555;
            }
            QComboBox::drop-down { border: none; }
        """
        self.year_combo.setStyleSheet(combo_style)
        self.month_combo.setStyleSheet(combo_style)

        self.year_combo.currentIndexChanged.connect(self.on_date_combo_changed)
        self.month_combo.currentIndexChanged.connect(self.on_date_combo_changed)

        # 다음 달 버튼
        self.next_btn = StyledButton("다음 달 ▶", "transparent", "#777777")

        self.today_btn.clicked.connect(self.go_today)
        self.prev_btn.clicked.connect(self.go_prev_month)
        self.next_btn.clicked.connect(self.go_next_month)

        nav_layout.addStretch()
        nav_layout.addWidget(self.today_btn)
        nav_layout.addWidget(self.prev_btn)
        nav_layout.addWidget(self.year_combo)
        nav_layout.addWidget(self.month_combo)
        nav_layout.addWidget(self.next_btn)
        nav_layout.addStretch()
        layout.addLayout(nav_layout)

        # 커스텀 OverlayTableWidget 사용
        self.calendar_table = OverlayTableWidget()
        self.calendar_table.setColumnCount(7)
        self.calendar_table.setHorizontalHeaderLabels(
            ["일", "월", "화", "수", "목", "금", "토"]
        )
        self.calendar_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.calendar_table.setSelectionMode(QTableWidget.NoSelection)
        self.calendar_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.calendar_table.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.calendar_table.verticalHeader().setVisible(False)
        self.calendar_table.setStyleSheet(
            """
            QTableWidget { border: none;
                           gridline-color: #777777;
                           background-color: transparent; }
            QTableWidget::item { background-color: transparent; }
            """
        )
        self.calendar_table.viewport().setStyleSheet("background-color: transparent;")
        self.calendar_table.cellDoubleClicked.connect(self.on_cell_double_clicked)
        self.calendar_table.resized.connect(
            lambda: QTimer.singleShot(10, self.draw_overlays)
        )
        layout.addWidget(self.calendar_table)

    def build_calendar(self):
        """달력을 그리기 위한 시작점: 이전 데이터를 지우고 비동기로 데이터를 요청합니다."""
        self.calendar_table.clearContents()
        self.date_to_cell.clear()

        for w in self.overlay_widgets:
            w.setParent(None)
            w.deleteLater()
        self.overlay_widgets.clear()

        year, month = self.current_date.year(), self.current_date.month()

        self.year_combo.blockSignals(True)
        self.month_combo.blockSignals(True)
        self.year_combo.setCurrentText(f"{self.current_date.year()}년")
        self.month_combo.setCurrentText(f"{self.current_date.month()}월")
        self.year_combo.blockSignals(False)
        self.month_combo.blockSignals(False)

        cache_key = f"{year}-{month:02d}"
        needs_holiday = cache_key not in self.holidays_cache
        needs_laws = not hasattr(self, "laws_schedules")

        if needs_holiday or needs_laws:
            self.worker = AsyncTask(
                self._fetch_missing_data,
                year,
                month,
                needs_holiday,
                needs_laws,
                parent=self,
            )
            self.worker.result_ready.connect(self._on_missing_data_loaded)
            self.worker.start()
        else:
            self._render_calendar()

    def _fetch_missing_data(self, year, month, needs_holiday, needs_laws):
        """백그라운드에서는 캐시에 없는 데이터만 가져옵니다."""
        result = {}
        if needs_holiday:
            result["cache_key"] = f"{year}-{month:02d}"
            result["holidays"] = get_holidays(year, month)

        if needs_laws:
            laws_schedules = []
            try:
                keywords = db_manager.load_law_keywords()
                for kw in keywords:
                    if kw.get("checked", False):
                        laws = law_scraper.get_law_group_info(kw["text"])
                        for law in laws:
                            date_str = law.get("enforce_date", "")
                            if (
                                date_str
                                and len(date_str) == 10
                                and date_str != "정보 없음"
                            ):
                                formatted_date = date_str.replace(".", "-")
                                laws_schedules.append(
                                    {
                                        "id": f"law_{law['serial']}",
                                        "title": f"⚖️ {law['name']}",
                                        "start_date": formatted_date,
                                        "end_date": formatted_date,
                                        "repeat_type": "none",
                                        "color": "#673AB7",
                                        "is_law": True,
                                        "link": law.get("link", ""),
                                    }
                                )
            except Exception:
                pass
            result["laws_schedules"] = laws_schedules
        return result

    def _on_missing_data_loaded(self, data):
        """비동기 로딩이 끝나면 캐시에 저장하고 렌더링을 시작합니다."""
        if "holidays" in data:
            self.holidays_cache[data["cache_key"]] = data["holidays"]
        if "laws_schedules" in data:
            self.laws_schedules = data["laws_schedules"]

        self._render_calendar()

    def fetch_data(self):
        """DB 일정과 로드된 법령 데이터를 합칩니다 (DB는 속도가 매우 빠르므로 동기 처리)"""
        db_schedules = db_manager.get_schedules()
        laws = getattr(self, "laws_schedules", [])

        self.schedules_cache = db_schedules + laws
        self.schedules_cache.sort(
            key=lambda x: (
                x["start_date"],
                x.get("is_completed", False),
                -QDate.fromString(x["start_date"], "yyyy-MM-dd").daysTo(
                    QDate.fromString(x["end_date"], "yyyy-MM-dd")
                ),
            )
        )

    def _render_calendar(self):
        """실제 달력 그리드(배경)를 그리는 함수입니다."""
        self.fetch_data()

        year, month = self.current_date.year(), self.current_date.month()
        cache_key = f"{year}-{month:02d}"
        monthly_holidays = self.holidays_cache.get(cache_key, {})

        first_day = QDate(year, month, 1)
        days_in_month = self.current_date.daysInMonth()
        start_day_of_week = first_day.dayOfWeek()
        if start_day_of_week == 7:
            start_day_of_week = 0

        rows = (start_day_of_week + days_in_month + 6) // 7
        self.calendar_table.setRowCount(rows)

        current_day = 1
        for row in range(rows):
            for col in range(7):
                if row == 0 and col < start_day_of_week:
                    continue
                if current_day > days_in_month:
                    break

                date_obj = QDate(year, month, current_day)
                date_str = date_obj.toString("yyyy-MM-dd")
                self.date_to_cell[date_str] = (row, col)

                cell_widget = CustomCalendarCell(date_obj, self)
                bg_color = "transparent"
                is_holiday = date_str in monthly_holidays

                if is_holiday:
                    bg_color = "rgba(255, 193, 204, 0.8)"
                    cell_widget.date_label.setStyleSheet(
                        "color: red; font-weight: bold;"
                    )
                    cell_widget.date_label.setText(
                        f"{cell_widget.date_label.text()} {monthly_holidays[date_str]}"
                    )
                elif date_obj.dayOfWeek() == 7:
                    bg_color = "rgba(255, 193, 204, 0.8)"
                elif date_obj.dayOfWeek() == 6:
                    bg_color = "rgba(166, 218, 244, 0.8)"

                cell_widget.setStyleSheet(
                    f"CustomCalendarCell {{ background-color: {bg_color}; }}"
                )
                self.calendar_table.setCellWidget(row, col, cell_widget)
                current_day += 1

        QTimer.singleShot(10, self.draw_overlays)

    def draw_overlays(self):
        """계산된 좌표 위에 일정 막대를 둥둥 띄웁니다! (구글 캘린더 알고리즘)"""
        # 1. 기존 오버레이 모두 제거
        for w in self.overlay_widgets:
            w.setParent(None)
            w.deleteLater()
        self.overlay_widgets.clear()

        if not self.date_to_cell:
            return

        if not self.isVisible() or self.calendar_table.viewport().width() <= 0:
            return

        view_start = QDate.fromString(min(self.date_to_cell.keys()), "yyyy-MM-dd")
        view_end = QDate.fromString(max(self.date_to_cell.keys()), "yyyy-MM-dd")

        # 2. 이번 달에 표시될 모든 일정 인스턴스 추출
        instances = []
        for schedule in self.schedules_cache:
            for inst_start, inst_end in get_instances(schedule, view_start, view_end):
                instances.append(
                    {"schedule": schedule, "start": inst_start, "end": inst_end}
                )

        # 3. 슬롯(줄) 겹침 방지
        slot_map = {d: [] for d in self.date_to_cell.keys()}
        hidden_counts = {d: 0 for d in self.date_to_cell.keys()}

        table_height = self.calendar_table.viewport().height()
        rows = self.calendar_table.rowCount()

        if rows > 0:
            cell_height = table_height / rows
            available_height = cell_height - 45
            max_slots = max(1, int(available_height // 24))
        else:
            max_slots = 3

        for inst in instances:
            s_qdate, e_qdate = inst["start"], inst["end"]

            # 현재 일정이 차지할 구간의 날짜 리스트
            date_range = []
            curr = s_qdate
            while curr <= e_qdate and curr <= view_end:
                d_str = curr.toString("yyyy-MM-dd")
                if d_str in self.date_to_cell:
                    date_range.append(d_str)
                curr = curr.addDays(1)

            if not date_range:
                continue

            # 빈 슬롯 찾기
            slot_idx = 0
            while True:
                conflict = False
                for d_str in date_range:
                    if len(slot_map[d_str]) > slot_idx and slot_map[d_str][slot_idx]:
                        conflict = True
                        break
                if not conflict:
                    break
                slot_idx += 1

            # 슬롯 채우기
            for d_str in date_range:
                while len(slot_map[d_str]) <= slot_idx:
                    slot_map[d_str].append(False)
                slot_map[d_str][slot_idx] = True

            # 슬롯이 3 이상이면 안 그리고 +N 카운트만 증가
            if slot_idx >= max_slots:
                for d_str in date_range:
                    hidden_counts[d_str] += 1
                continue

            # 4. 막대 그리기 (주가 바뀌면 막대를 잘라서 새로 그립니다)
            schedule = inst["schedule"]
            segments = []
            current_seg = []
            last_row = -1

            for d_str in date_range:
                r, c = self.date_to_cell[d_str]
                if r != last_row and current_seg:
                    segments.append(current_seg)
                    current_seg = []
                current_seg.append((d_str, r, c))
                last_row = r
            if current_seg:
                segments.append(current_seg)

            is_completed = schedule.get("is_completed", False)
            if is_completed:
                bg_color = "rgba(168, 168, 168, 0.6)"
            else:
                c = QColor(schedule["color"])
                bg_color = f"rgb({c.red()}, {c.green()}, {c.blue()})"
            text_color = "#999999" if is_completed else "#131313"
            text_decor = "line-through" if is_completed else "none"

            for seg in segments:
                start_r, start_c = seg[0][1], seg[0][2]
                end_r, end_c = seg[-1][1], seg[-1][2]

                # QTableWidget 내의 셀 좌표를 계산
                rect_start = self.calendar_table.visualRect(
                    self.calendar_table.model().index(start_r, start_c)
                )
                rect_end = self.calendar_table.visualRect(
                    self.calendar_table.model().index(end_r, end_c)
                )

                # 여백과 높이 설정
                x = rect_start.x() + 2
                y = rect_start.y() + 25 + (slot_idx * 24)
                w = rect_end.right() - rect_start.left() - 4
                h = 22

                is_first_seg = seg == segments[0]
                is_last_seg = seg == segments[-1]
                r_left = "4px" if is_first_seg else "0px"
                r_right = "4px" if is_last_seg else "0px"

                display_text = f" {schedule['title']}" if is_first_seg else " "
                label = ClickableEventLabel(schedule, display_text)

                style = f"""
                    background-color: {bg_color}; color: {text_color}; text-decoration: {text_decor};
                    font-size: 14px; padding: 2px;
                    border-radius: {r_left} {r_right} {r_right} {r_left};
                """
                label.setStyleSheet(style)
                label.setParent(self.calendar_table.viewport())
                label.setGeometry(x, y, w, h)

                label.doubleClicked.connect(self.edit_existing_event)
                label.editRequested.connect(self.edit_existing_event)
                label.statusToggled.connect(self.toggle_event_status)
                label.deleteRequested.connect(self.delete_event_from_calendar)

                label.show()
                self.overlay_widgets.append(label)

        # 5. 숨겨진 일정 개수(+N 더보기) 업데이트
        for d_str, count in hidden_counts.items():
            r, c = self.date_to_cell[d_str]
            cell_widget = self.calendar_table.cellWidget(r, c)
            if cell_widget:
                cell_widget.set_more_count(count)

    def on_cell_double_clicked(self, row, col):
        cell_widget = self.calendar_table.cellWidget(row, col)
        if cell_widget:
            date_str = cell_widget.date_obj.toString("yyyy. MM. dd")
            dialog = EventDialog(date_str, parent=self)
            if dialog.exec():
                self.fetch_data()
                self.draw_overlays()

    def edit_existing_event(self, schedule_data):
        dialog = EventDialog(
            schedule_data["start_date"], schedule_data=schedule_data, parent=self
        )
        if dialog.exec():
            self.fetch_data()
            self.draw_overlays()

    def toggle_event_status(self, schedule_data):
        """막대 우클릭으로 완료 상태를 토글합니다."""
        new_status = not schedule_data.get("is_completed", False)
        s = schedule_data
        db_manager.update_schedule(
            s["id"],
            s["title"],
            s["start_date"],
            s["end_date"],
            s["repeat_type"],
            s["repeat_end"],
            s["color"],
            new_status,
        )
        self.fetch_data()
        self.draw_overlays()

    def delete_event_from_calendar(self, schedule_data):
        """막대 우클릭으로 일정을 즉시 삭제합니다."""
        reply = QMessageBox.question(
            self,
            "삭제",
            f"'{schedule_data['title']}' 일정을 삭제하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            db_manager.delete_schedule(schedule_data["id"])
            self.fetch_data()
            self.draw_overlays()

    def on_date_combo_changed(self):
        year_str = self.year_combo.currentText().replace("년", "")
        month_str = self.month_combo.currentText().replace("월", "")

        self.current_date = QDate(int(year_str), int(month_str), 1)
        self.build_calendar()

    def go_today(self):
        self.current_date = QDate.currentDate()
        self.build_calendar()

    def go_prev_month(self):
        self.current_date = self.current_date.addMonths(-1)
        self.build_calendar()

    def go_next_month(self):
        self.current_date = self.current_date.addMonths(1)
        self.build_calendar()

    def show_daily_events(self, date_obj):
        dialog = DailyEventsDialog(date_obj, parent_tab=self)
        dialog.exec()

        # 팝업을 닫고 나왔을 때 달력 데이터를 최신화해 줍니다.
        self.fetch_data()
        self.draw_overlays()
