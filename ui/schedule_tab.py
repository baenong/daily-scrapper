import os
import requests
import json
import xml.etree.ElementTree as ET
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QLabel,
    QHeaderView,
    QDialog,
    QComboBox,
    QCheckBox,
    QListWidget,
    QListWidgetItem,
)
from PySide6.QtCore import Qt, QDate, Signal, QTimer, QThreadPool
from PySide6.QtGui import QColor, QMouseEvent, QFont, QFontMetrics
from ui.components import (
    BoldLabel,
    StyledButton,
    ClickableEventLabel,
    EventDialog,
    ScheduleActionMixin,
)
from core import db_manager, law_scraper
from core.worker import AsyncTask
from core.signals import global_signals
from core.style import tw, tw_sheet, COLORS


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
    except Exception:
        return {}


def get_instances(schedule, view_start, view_end, holidays=None):
    """반복 일정을 전개하여 현재 화면(월)에 표시될 '실제 날짜 구간(인스턴스)'들을 계산합니다."""
    instances = []
    ev_start = QDate.fromString(schedule["start_date"], "yyyy-MM-dd")
    ev_end = QDate.fromString(schedule["end_date"], "yyyy-MM-dd")
    duration = ev_start.daysTo(ev_end)

    rtype = schedule.get("repeat_type", "none")
    rep_end_str = schedule.get("repeat_end", "")
    rep_end = QDate.fromString(rep_end_str, "yyyy-MM-dd") if rep_end_str else view_end

    rule_str = schedule.get("repeat_rule", "")
    rule = {}
    if rule_str:
        try:
            rule = json.loads(rule_str)
        except json.JSONDecodeError:
            pass

    interval = rule.get("interval", 1)
    weekday_only = rule.get("weekday_only", False)
    holiday_set = holidays if holidays else set()

    def apply_weekday_only(d):
        if not weekday_only:
            return d

        while True:
            dow = d.dayOfWeek()  # 1~7 : 월~일
            d_str = d.toString("yyyy-MM-dd")

            if dow > 5 or d_str in holiday_set:
                d = d.addDays(-1)
            else:
                break

        return d

    if rtype == "none":
        if ev_start <= view_end and ev_end >= view_start:
            instances.append((ev_start, ev_end))

    elif rtype == "daily":
        curr = ev_start
        while curr <= rep_end and curr <= view_end:
            inst_start = apply_weekday_only(curr)
            inst_end = inst_start.addDays(duration)
            if inst_end >= view_start and inst_start <= view_end:
                instances.append((inst_start, inst_end))
            curr = curr.addDays(interval)

    elif rtype == "weekly":
        days = rule.get("days", [])
        if not days:
            days = [ev_start.dayOfWeek() - 1]

        curr_week_start = ev_start.addDays(-(ev_start.dayOfWeek() - 1))

        while curr_week_start <= rep_end and curr_week_start <= view_end:
            for d in days:
                inst_start = curr_week_start.addDays(d)

                if inst_start < ev_start or inst_start > rep_end:
                    continue

                inst_start = apply_weekday_only(inst_start)
                inst_end = inst_start.addDays(duration)

                if inst_end >= view_start and inst_start <= view_end:
                    instances.append((inst_start, inst_end))

            curr_week_start = curr_week_start.addDays(7 * interval)

    elif rtype == "monthly":
        mode = rule.get("mode", "date")
        curr = ev_start

        while curr <= rep_end and curr <= view_end:
            inst_start = None

            # [A] 특정 일자 반복 (예: 매월 25일)
            if mode == "date":
                target_day = rule.get("date", ev_start.day())
                # 말일 보정
                days_in_month = curr.daysInMonth()
                actual_day = min(target_day, days_in_month)
                inst_start = QDate(curr.year(), curr.month(), actual_day)

            # [B] N번째 요일 반복 (예: 매월 첫 번째 금요일)
            elif mode == "nth_day":
                nth = rule.get("nth", 1)
                target_dow = rule.get("day", 0) + 1  # UI(0~6) -> QDate(1~7) 매핑

                if nth == -1:  # 마지막 주일 경우
                    # 해당 월의 마지막 날부터 거꾸로 계산
                    last_day = QDate(curr.year(), curr.month(), curr.daysInMonth())
                    offset = (last_day.dayOfWeek() - target_dow) % 7
                    inst_start = last_day.addDays(-offset)
                else:
                    # 첫째 날부터 계산
                    first_day = QDate(curr.year(), curr.month(), 1)
                    offset = (target_dow - first_day.dayOfWeek()) % 7
                    first_occurrence = first_day.addDays(offset)
                    inst_start = first_occurrence.addDays((nth - 1) * 7)

                    # 계산된 날짜가 달을 넘어가면 제외 (예: 5번째 금요일이 없는 달)
                    if inst_start.month() != curr.month():
                        inst_start = None

            if inst_start and inst_start >= ev_start and inst_start <= rep_end:
                inst_start = apply_weekday_only(inst_start)
                inst_end = inst_start.addDays(duration)
                if inst_end >= view_start and inst_start <= view_end:
                    instances.append((inst_start, inst_end))

            curr = curr.addMonths(interval)

    elif rtype == "yearly":
        curr = ev_start

        while curr <= rep_end and curr <= view_end:
            target_month = rule.get("month", ev_start.month())
            target_day = rule.get("date", ev_start.day())

            # 윤달 방어 (2월 29일을 설정했는데 윤년이 아닌 해인 경우 28일로)
            temp_date = QDate(curr.year(), target_month, 1)
            actual_day = min(target_day, temp_date.daysInMonth())

            inst_start = QDate(curr.year(), target_month, actual_day)

            if inst_start >= ev_start and inst_start <= rep_end:
                inst_start = apply_weekday_only(inst_start)
                inst_end = inst_start.addDays(duration)
                if inst_end >= view_start and inst_start <= view_end:
                    instances.append((inst_start, inst_end))

            curr = curr.addYears(interval)

    return instances


class DailyEventRowWidget(QWidget, ScheduleActionMixin):
    def __init__(self, schedule_data, parent=None):
        super().__init__(parent)
        self.schedule_data = schedule_data
        is_law = schedule_data.get("is_law", False)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(1, 1, 1, 1)

        container = QWidget()
        container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        main_layout.addWidget(container)

        # 1. 완료 체크박스
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(schedule_data.get("is_completed", False))
        self.checkbox.toggled.connect(self.toggle_event)
        if is_law:
            self.checkbox.hide()

        # 2. 제목 라벨
        self.title_label = QLabel(schedule_data["title"])
        self.title_label.setCursor(Qt.CursorShape.PointingHandCursor)

        base_container_style = tw("rounded", "py-10", "pl-5")

        if self.checkbox.isChecked():
            self.title_label.setStyleSheet(tw("p-5", "text-gray", "line-through"))
            container.setStyleSheet(base_container_style)
        else:
            self.title_label.setStyleSheet(tw("p-5", "text-c13"))

            base_color = QColor(schedule_data["color"]).lighter(110).name()
            container.setStyleSheet(
                f"{base_container_style} background-color: {base_color};"
            )

        # 3. 삭제 버튼
        self.btn_del = StyledButton(
            "❌", "transparent", COLORS["red-500"], padding="2px"
        )
        self.btn_del.setFixedWidth(35)
        self.btn_del.setFixedHeight(30)
        self.btn_del.clicked.connect(self.delete_event)

        layout.addWidget(self.checkbox)
        layout.addWidget(self.title_label, stretch=1)
        layout.addWidget(self.btn_del)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.handle_double_click()


class DailyEventsDialog(QDialog):
    """특정 날짜의 일정을 체크박스 형태로 보여주는 팝업 창"""

    def __init__(self, date_obj: QDate, parent_tab=None):
        super().__init__(parent_tab)
        self.date_obj = date_obj
        self.parent_tab = parent_tab
        self.date_str = date_obj.toString("yyyy. MM. dd")

        self.setWindowTitle(f"{self.date_str} 일정 목록")
        self.setFixedSize(320, 500)

        layout = QVBoxLayout(self)
        layout.addWidget(BoldLabel(f"{date_obj.toString('yy. MM. dd')}"))

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(
            tw_sheet({"QListWidget": "border-b border-c99 rounded my-10 p-3"})
        )
        layout.addWidget(self.list_widget)

        btn_layout = QHBoxLayout()

        self.add_btn = StyledButton("신규 일정", COLORS["blue-500"], padding="5px 10px")
        self.add_btn.clicked.connect(self.add_new_event)

        btn_layout.addStretch()
        btn_layout.addWidget(self.add_btn)

        layout.addLayout(btn_layout)
        self.layout = layout
        self.load_events()

        global_signals.schedule_updated.connect(self.load_events)

    def add_new_event(self):
        dialog = EventDialog(self.date_str, parent=self)
        dialog.exec()

    def load_events(self):
        self.list_widget.clear()
        day_events = []

        source_schedules = db_manager.get_schedules()
        if self.parent_tab and hasattr(self.parent_tab, "laws_schedules"):
            source_schedules += self.parent_tab.laws_schedules

        for s in source_schedules:
            if get_instances(s, self.date_obj, self.date_obj):
                day_events.append(s)

        day_events.sort(key=lambda x: x.get("is_completed", False))

        for ev in day_events:
            item = QListWidgetItem(self.list_widget)
            row_widget = DailyEventRowWidget(ev, self)
            item.setSizeHint(row_widget.sizeHint())
            self.list_widget.setItemWidget(item, row_widget)


class ClickableLabel(QLabel):
    clicked = Signal(QDate)

    def __init__(self, date_obj, text="", parent=None):
        super().__init__(text, parent)
        self.date_obj = date_obj
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.date_obj)


class CustomCalendarCell(QWidget):
    """표의 배경을 담당하는 셀 (날짜와 '+N 더보기'만 표시)"""

    def __init__(self, date_obj: QDate, parent_tab):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.date_obj = date_obj
        self.parent_tab = parent_tab
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)

        self.date_label = ClickableLabel(date_obj, str(date_obj.day()))
        self.date_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop
        )
        self.date_label.setContentsMargins(0, 0, 5, 0)
        self.date_label.clicked.connect(self.parent_tab.show_daily_events)

        if date_obj.dayOfWeek() == 7:
            self.date_label.setStyleSheet(tw("text-red"))
        elif date_obj.dayOfWeek() == 6:
            self.date_label.setStyleSheet(tw("text-blue"))
        layout.addWidget(self.date_label)

        self.more_label = ClickableLabel(date_obj)
        self.more_label.setStyleSheet(tw("text-gray", "text-12"))
        self.more_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.more_label.clicked.connect(self.parent_tab.show_daily_events)
        self.more_label.hide()
        layout.addStretch()
        layout.addWidget(self.more_label)
        self.layout = layout

    def set_more_count(self, count):
        if count > 0:
            self.more_label.setText(f"+ {count}개 더보기")
            self.more_label.show()
        else:
            self.more_label.hide()


class OverlayTableWidget(QTableWidget):
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
        self.overlay_widgets = []
        self.date_to_cell = {}

        self.setup_ui()
        self.build_calendar()
        global_signals.schedule_updated.connect(self.refresh_all_data)
        global_signals.law_keyword_updated.connect(self.invalidate_law_cache)
        global_signals.font_size_changed.connect(self.on_font_changed)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        nav_layout = QHBoxLayout()

        # 오늘 버튼
        self.today_btn = StyledButton("오늘", COLORS["blue-300"], COLORS["blue-700"])

        # 이전 달 버튼
        self.prev_btn = StyledButton("◀ 이전 달", "transparent", COLORS["c77"])

        self.year_combo = QComboBox()
        self.month_combo = QComboBox()

        self.year_combo.addItems([f"{y}년" for y in range(2024, 2035)])
        self.month_combo.addItems([f"{m}월" for m in range(1, 13)])

        self.year_combo.currentIndexChanged.connect(self.on_date_combo_changed)
        self.month_combo.currentIndexChanged.connect(self.on_date_combo_changed)

        # 다음 달 버튼
        self.next_btn = StyledButton("다음 달 ▶", "transparent", COLORS["c77"])

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
        self.calendar_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.calendar_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.calendar_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.calendar_table.verticalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.calendar_table.verticalHeader().setVisible(False)
        self.calendar_table.setStyleSheet(
            tw_sheet(
                {
                    "QTableWidget": "grid-c77 border-none bg-transparent",
                    "QTableWidget::item": "bg-transparent",
                }
            )
        )
        self.calendar_table.viewport().setStyleSheet(tw("bg-transparent"))
        self.calendar_table.cellDoubleClicked.connect(self.on_cell_double_clicked)
        self.calendar_table.resized.connect(
            lambda: QTimer.singleShot(10, self.draw_overlays)
        )
        layout.addWidget(self.calendar_table)

    def build_calendar(self):
        self.calendar_table.clearContents()
        self.date_to_cell.clear()

        for w in self.overlay_widgets:
            w.setParent(None)
            w.deleteLater()
        self.overlay_widgets.clear()

        year, month = self.current_date.year(), self.current_date.month()

        self.year_combo.blockSignals(True)
        self.month_combo.blockSignals(True)
        self.year_combo.setCurrentText(f"{year}년")
        self.month_combo.setCurrentText(f"{month}월")
        self.year_combo.blockSignals(False)
        self.month_combo.blockSignals(False)

        cache_key = f"{year}-{month:02d}"
        needs_holiday = cache_key not in self.holidays_cache
        needs_laws = not hasattr(self, "laws_schedules")

        self._render_calendar()

        if needs_holiday or needs_laws:
            worker = AsyncTask(
                self._fetch_missing_data, year, month, needs_holiday, needs_laws
            )
            worker.signals.result_ready.connect(self._on_missing_data_loaded)
            QThreadPool.globalInstance().start(worker)

    def _fetch_missing_data(self, year, month, needs_holiday, needs_laws):
        result = {}
        if needs_holiday:
            result["cache_key"] = f"{year}-{month:02d}"
            result["holidays"] = get_holidays(year, month)

        if needs_laws:
            laws_schedules = []
            try:
                keywords = [
                    kw["text"]
                    for kw in db_manager.load_law_keywords()
                    if kw.get("checked", False)
                ]
                if keywords:
                    all_laws = law_scraper.get_laws_by_keywords(keywords)
                    for law in all_laws:
                        date_str = law.get("enforce_date", "")
                        if date_str and len(date_str) == 10 and date_str != "정보 없음":
                            formatted_date = date_str.replace(".", "-")
                            laws_schedules.append(
                                {
                                    "id": f"law_{law['serial']}",
                                    "title": f"⚖️ {law['name']}",
                                    "start_date": formatted_date,
                                    "end_date": formatted_date,
                                    "repeat_type": "none",
                                    "color": COLORS["purple"],
                                    "is_law": True,
                                    "link": law.get("link", ""),
                                }
                            )
            except Exception:
                pass
            result["laws_schedules"] = laws_schedules
        return result

    def _on_missing_data_loaded(self, data):
        if "holidays" in data:
            self.holidays_cache[data["cache_key"]] = data["holidays"]
        if "laws_schedules" in data:
            self.laws_schedules = data["laws_schedules"]
        self._render_calendar()

    def fetch_data(self):
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
        actual_today = QDate.currentDate()

        for row in range(rows):
            for col in range(7):
                if row == 0 and col < start_day_of_week:
                    continue
                if current_day > days_in_month:
                    break

                date_obj = QDate(year, month, current_day)
                date_str = date_obj.toString("yyyy-MM-dd")
                cell_widget = CustomCalendarCell(date_obj, self)
                date_day_str = cell_widget.date_label.text()

                self.date_to_cell[date_str] = (row, col)
                bg_color = "transparent"
                is_holiday = date_str in monthly_holidays

                if is_holiday:
                    bg_color = "red-400-80"
                    cell_widget.date_label.setStyleSheet(tw("text-red", "font-bold"))
                    cell_widget.date_label.setText(
                        f"{date_day_str} {monthly_holidays[date_str]}"
                    )
                elif date_obj.dayOfWeek() == 7:
                    bg_color = "red-400-80"
                elif date_obj.dayOfWeek() == 6:
                    bg_color = "blue-600-80"

                cell_qss = "bg-" + bg_color
                if date_obj == actual_today:
                    cell_qss += (
                        " border-2 border-solid border-green-500 bg-green-300-30"
                    )
                    cell_widget.date_label.setText(f"{date_day_str} (오늘)")

                cell_widget.setStyleSheet(tw_sheet({"CustomCalendarCell": cell_qss}))
                self.calendar_table.setCellWidget(row, col, cell_widget)
                current_day += 1

        QTimer.singleShot(10, self.draw_overlays)

    def _calculate_instances_bg(self, start_str, end_str, schedules, flat_holidays):
        view_start = QDate.fromString(start_str, "yyyy-MM-dd")
        view_end = QDate.fromString(end_str, "yyyy-MM-dd")

        instances = []
        for schedule in schedules:
            for inst_start, inst_end in get_instances(
                schedule, view_start, view_end, flat_holidays
            ):
                instances.append(
                    {"schedule": schedule, "start": inst_start, "end": inst_end}
                )
        return instances

    def _render_overlay_widgets(self, instances):
        slot_map = {d: [] for d in self.date_to_cell.keys()}
        hidden_counts = {d: 0 for d in self.date_to_cell.keys()}

        view_end = QDate.fromString(max(self.date_to_cell.keys()), "yyyy-MM-dd")
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

            # 4. 막대 그리기
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
            inst_start_str = s_qdate.toString("yyyy-MM-dd")

            # 반복일 경우 완료일을 개별 저장해서 비교한 후 완료여부를 판별한다.
            if schedule.get("repeat_type", "none") != "none":
                try:
                    rule = json.loads(schedule.get("repeat_rule", ""))
                    if inst_start_str in rule.get("completed_dates", []):
                        is_completed = True
                except Exception:
                    pass

            if is_completed:
                bg_color = "rgba(168, 168, 168, 0.15)"
            else:
                c_val = QColor(schedule["color"])
                bg_color = f"rgb({c_val.red()}, {c_val.green()}, {c_val.blue()})"
            text_color = "c99" if is_completed else "c13"
            text_decor = "line-through" if is_completed else ""

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
                w = rect_end.right() - rect_start.left() - 2
                h = 22

                is_first_seg = seg == segments[0]
                is_last_seg = seg == segments[-1]
                r_left = "4px" if is_first_seg else "0px"
                r_right = "4px" if is_last_seg else "0px"

                is_roadmap = schedule.get("is_roadmap", False)
                prefix = "★ " if is_roadmap else ""

                fm = QFontMetrics(QFont())
                display_text = (
                    fm.elidedText(
                        f"{prefix} {schedule['title']}", Qt.TextElideMode.ElideRight, w
                    )
                    if is_first_seg
                    else " "
                )
                label = ClickableEventLabel(schedule, display_text, render_date=inst_start_str)

                style = f"""
                        background-color: {bg_color};
                        {tw("text-14", "p-2", text_decor, "text-" + text_color)}
                        border-top-left-radius: {r_left};
                        border-top-right-radius: {r_right};
                        border-bottom-right-radius: {r_right};
                        border-bottom-left-radius: {r_left};
                        """
                label.setStyleSheet(style)
                label.setParent(self.calendar_table.viewport())
                label.setGeometry(x, y, w, h)
                label.show()

                self.overlay_widgets.append(label)

        # 5. 숨겨진 일정 개수(+N 더보기) 업데이트
        for d_str, count in hidden_counts.items():
            r, c = self.date_to_cell[d_str]
            cell_widget = self.calendar_table.cellWidget(r, c)
            if cell_widget:
                cell_widget.set_more_count(count)

    def draw_overlays(self):
        # 1. 기존 오버레이 모두 제거
        for w in self.overlay_widgets:
            w.setParent(None)
            w.deleteLater()
        self.overlay_widgets.clear()

        if not self.date_to_cell:
            return

        if not self.isVisible() or self.calendar_table.viewport().width() <= 0:
            return

        view_start = min(self.date_to_cell.keys())
        view_end = max(self.date_to_cell.keys())

        # 2. 이번 달에 표시될 모든 일정 인스턴스 추출
        flat_holidays = set()
        for month_data in self.holidays_cache.values():
            flat_holidays.update(month_data.keys())

        calc_worker = AsyncTask(
            self._calculate_instances_bg,
            view_start,
            view_end,
            self.schedules_cache,
            flat_holidays,
        )
        calc_worker.signals.result_ready.connect(self._render_overlay_widgets)
        QThreadPool.globalInstance().start(calc_worker)

    def refresh_all_data(self):
        self.fetch_data()
        self.draw_overlays()

    def invalidate_law_cache(self):
        if hasattr(self, "laws_schedules"):
            del self.laws_schedules
        self.build_calendar()

    def on_cell_double_clicked(self, row, col):
        cell_widget = self.calendar_table.cellWidget(row, col)
        if cell_widget:
            date_str = cell_widget.date_obj.toString("yyyy. MM. dd")
            dialog = EventDialog(date_str, parent=self)
            dialog.exec()

    def on_date_combo_changed(self):
        year_str = self.year_combo.currentText().replace("년", "")
        month_str = self.month_combo.currentText().replace("월", "")

        self.current_date = QDate(int(year_str), int(month_str), 1)
        self.build_calendar()

    def on_font_changed(self):
        if self.isVisible():
            QTimer.singleShot(10, self.draw_overlays)

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
        dialog = DailyEventsDialog(date_obj, parent_tab=self.window())
        dialog.exec()
