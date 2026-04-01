import json
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QScrollArea,
    QComboBox,
)
from PySide6.QtCore import Qt, QDate, QTimer, QRect
from PySide6.QtGui import QPainter, QColor, QPen, QPalette, QFont, QFontMetrics

from core import db_manager
from core.signals import global_signals
from core.tw_utils import COLORS, tw
from ui.components import (
    TitleLabel,
    StyledButton,
    ClickableEventLabel,
    GroupManagerDialog,
)


class RoadmapCanvas(QWidget):
    """실제 간트 차트(막대)와 배경 그리드가 그려지는 도화지입니다."""

    def __init__(self, parent_tab):
        super().__init__()
        self.parent_tab = parent_tab
        self.setMinimumHeight(500)
        self.setMinimumWidth(1000)
        self.groups = []
        self.schedules = []
        self.target_year = QDate.currentDate().year()
        self.overlay_widgets = []

        self.g_width = 180

    def update_data(self, year, groups, schedules):
        self.target_year = year
        self.groups = groups
        self.schedules = schedules

        # 높이 재계산 및 다시 그리기 요청
        self.setMinimumHeight(max(500, len(self.groups) * 80 + 50))
        self.update()
        QTimer.singleShot(10, self.draw_bars)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()
        chart_width = width - self.g_width

        text_color = self.palette().color(QPalette.ColorRole.WindowText)
        line_color = QColor(192, 192, 192, 90)
        header_bg = QColor(128, 128, 128, 30)
        group_bg = QColor(128, 128, 128, 15)

        # 1. 상단 월(Month) 헤더 그리기
        painter.fillRect(0, 0, width, 30, header_bg)
        painter.setPen(QPen(line_color, 1))

        days_in_year = QDate(self.target_year, 1, 1).daysInYear()

        # 달마다 세로선 긋기
        for month in range(1, 13):
            start_date = QDate(self.target_year, month, 1)
            day_offset = QDate(self.target_year, 1, 1).daysTo(start_date)
            x = self.g_width + int((day_offset / days_in_year) * chart_width)

            painter.drawLine(x, 0, x, height)
            painter.setPen(QPen(text_color, 1))
            painter.drawText(x + 5, 20, f"{month}월")
            painter.setPen(QPen(line_color, 1))

        # 2. 그룹별 가로 구역 그리기
        y_offset = 30
        g_height = (height - 30) / max(1, len(self.groups))

        for g in self.groups:
            painter.fillRect(0, int(y_offset), self.g_width, int(g_height), group_bg)
            painter.setPen(QPen(text_color, 1))
            text_rect = QRect(
                10, int(y_offset + 5), self.g_width - 10, int(g_height - 10)
            )
            painter.drawText(
                text_rect,
                Qt.AlignmentFlag.AlignVCenter
                | Qt.AlignmentFlag.AlignLeft
                | Qt.TextFlag.TextWordWrap,
                g["name"],
            )

            # 가로 구분선
            painter.setPen(QPen(line_color, 1))
            painter.drawLine(0, int(y_offset), width, int(y_offset))
            y_offset += g_height

    def _get_x_pos(self, date_str):
        d = QDate.fromString(date_str, "yyyy-MM-dd")
        if d.year() < self.target_year:
            return self.g_width
        if d.year() > self.target_year:
            return self.width()

        start_of_year = QDate(self.target_year, 1, 1)
        days_in_year = start_of_year.daysInYear()
        chart_width = self.width() - self.g_width

        return self.g_width + int(
            (start_of_year.daysTo(d) / days_in_year) * chart_width
        )

    def draw_bars(self):
        for w in self.overlay_widgets:
            w.setParent(None)
            w.deleteLater()
        self.overlay_widgets.clear()

        if not self.groups:
            return

        height = self.height()
        g_height = (height - 30) / max(1, len(self.groups))

        g_y_map = {g["id"]: 30 + (i * g_height) for i, g in enumerate(self.groups)}
        g_y_map[None] = 30 + (len(self.groups) * g_height)

        slots = {g["id"]: [] for g in self.groups}
        slots[None] = []

        for s in self.schedules:
            g_id = s.get("group_id")

            if g_id is not None:
                try:
                    g_id = int(g_id)
                except (ValueError, TypeError):
                    g_id = None

            if g_id not in slots:
                g_id = None

            # 기본 툴팁
            s_start = s["start_date"]
            s_end = s["end_date"]
            tooltip_date = f"({s_start} ~ {s_end})"

            render_start_str = s.get("render_start", s_start)
            start_date = QDate.fromString(render_start_str, "yyyy-MM-dd").addDays(-1)
            is_underflow = start_date.year() < self.target_year

            render_end_str = s.get("render_end", s_end)
            end_date = QDate.fromString(render_end_str, "yyyy-MM-dd").addDays(1)
            is_overflow = end_date.year() > self.target_year

            # 반복처리
            rtype = s.get("repeat_type", "none")
            repeat_string = ""

            if rtype != "none":
                rule_str = s.get("repeat_rule", "")
                rule = {}
                if rule_str:
                    try:
                        rule = json.loads(rule_str)
                    except json.JSONDecodeError:
                        pass

                interval = rule.get("interval", 1)
                label_base = ""

                if interval == 1:
                    if rtype == "daily":
                        label_base = "매일"
                    elif rtype == "weekly":
                        label_base = "매주"
                    elif rtype == "monthly":
                        label_base = "매월"
                    elif rtype == "yearly":
                        label_base = "매년"
                else:
                    if rtype == "daily":
                        label_base = f"{interval}일마다"
                    elif rtype == "weekly":
                        label_base = f"{interval}주마다"
                    elif rtype == "monthly":
                        label_base = f"{interval}개월마다"
                    elif rtype == "yearly":
                        label_base = f"{interval}년마다"

                detail_label = ""

                if rtype == "weekly":
                    days_map = ["월", "화", "수", "목", "금", "토", "일"]
                    days = rule.get("days", [])
                    if days:
                        detail_label = " " + ",".join([days_map[d] for d in days])

                elif rtype == "monthly":
                    mode = rule.get("mode", "date")
                    if mode == "date":
                        detail_label = f" {rule.get('date', 1)}일"
                    else:
                        nth_map = {
                            1: "첫째",
                            2: "둘째",
                            3: "셋째",
                            4: "넷째",
                            -1: "마지막",
                        }
                        days_map = ["월", "화", "수", "목", "금", "토", "일"]
                        nth = rule.get("nth", 1)
                        day_idx = rule.get("day", 0)
                        detail_label = f" {nth_map.get(nth, '')} {days_map[day_idx]}"

                elif rtype == "yearly":
                    detail_label = f" {rule.get('month', 1)}.{rule.get('date', 1)}"

                if rule.get("weekday_only"):
                    detail_label += "(평일)"

                repeat_end_str = s.get("repeat_end", "")
                if repeat_end_str:
                    tooltip_date = f"({s_start} ~ {render_end_str})"
                    repeat_end_date = QDate.fromString(repeat_end_str, "yyyy-MM-dd")
                    repeat_end = f" ~{repeat_end_date.toString('yy.MM.dd')}"
                else:
                    tooltip_date = f"({s_start} ~ )"
                    repeat_end = " 반복"

                repeat_string = f" ({label_base}{detail_label}{repeat_end})"

            bar_x_start = self._get_x_pos(render_start_str)
            bar_x_end = self._get_x_pos(render_end_str)

            # Bar의 너비 (최소 15 보장)
            bar_width = max(bar_x_end - bar_x_start, 10)
            bar_height = 22

            title_text = f"{s['title']}{repeat_string}"
            display_text = title_text

            app: QApplication = QApplication.instance()
            app_font_size = app.font().pixelSize()
            target_size = max(1, int(app_font_size * (13 / 14)))

            font = QFont("Pretendard Variable", target_size)
            fm = QFontMetrics(font)
            text_width = fm.horizontalAdvance(display_text) + 15

            # Position
            visual_start = bar_x_start  # 기본적으로는 bar의 x 시작점
            bar_x_right = bar_x_start + bar_width + 3  # bar 오른쪽 3px
            text_x_start = bar_x_right  # 기본적으로는 bar 오른쪽 3px 시작

            # 막대 안에 텍스트가 들어갈 수 있는지 판별
            put_inside = bar_width >= text_width

            if put_inside:
                # bar 너비가 더 넓다면 글자가 bar 안에 있으므로 끝이 bar의 끝이다.
                visual_end = bar_x_right
            else:
                # bar가 더 좁다면 남은 공간을 계산한다.
                space = self.width() - bar_x_right

                if space < 0:
                    # 남은 공간이 아예 없다면 텍스트를 왼쪽에 배치해야 한다.
                    visual_start = bar_x_start - text_width - 3
                    text_x_start = visual_start
                    visual_end = bar_x_right
                else:
                    # 남은 공간이 있기는 한데 텍스트가 다 들어가지는 않는 경우
                    if text_width > space:
                        # 남은 공간만큼 자르고 ellipsis 처리
                        display_text = fm.elidedText(
                            title_text, Qt.TextElideMode.ElideRight, space
                        )
                        visual_end = self.width() - 5
                    else:
                        # 남은 공간이 title_text 다 들어갈만큼 충분한 경우
                        visual_end = bar_x_right + text_width

            slot_idx = 0

            while True:
                conflict = False
                if len(slots[g_id]) > slot_idx:
                    for existing_start, existing_end in slots[g_id][slot_idx]:
                        if visual_start < existing_end and visual_end > existing_start:
                            conflict = True
                            break
                if not conflict:
                    break
                slot_idx += 1

            # 슬롯 할당
            while len(slots[g_id]) <= slot_idx:
                slots[g_id].append([])
            slots[g_id][slot_idx].append((visual_start, visual_end))

            # 라벨 위젯 생성
            y_pos = g_y_map[g_id] + (slot_idx * 26) + 5

            is_completed = s.get("is_completed", False)
            text_css = "text-c13"
            bg_hex = QColor(s["color"])
            bg_rgb = f"{bg_hex.red()}, {bg_hex.green()}, {bg_hex.blue()}"

            if is_completed:
                text_css = ""
                bg_color = f"rgba({bg_rgb}, 0.5)"

            else:
                bg_color = s["color"]

            # Bar
            bar_label = ClickableEventLabel(s, display_text if put_inside else "")
            bar_label.setToolTip(f"{s['title']}\n{tooltip_date}")

            rounded_str = ""
            if is_overflow and is_underflow:
                rounded_str = "rounded-0"
            elif is_overflow:
                rounded_str = "rounded-l-4"
            elif is_underflow:
                rounded_str = "rounded-r-4"
            else:
                rounded_str = "rounded"

            bar_label.setStyleSheet(
                f"""
                background-color: {bg_color};
                {tw(rounded_str, text_css, "text-13", "p-2")}
                """
            )
            bar_label.setParent(self)
            bar_label.setGeometry(bar_x_start, int(y_pos), bar_width, bar_height)
            bar_label.show()

            self.overlay_widgets.append(bar_label)

            # Floating Text
            if not put_inside:
                text_label = ClickableEventLabel(s, display_text)
                text_label.setStyleSheet(
                    tw("text-windowtext", "bg-transparent", "text-13")
                )
                text_label.setParent(self)
                text_label.setGeometry(text_x_start, int(y_pos), text_width, bar_height)
                text_label.show()

                self.overlay_widgets.append(text_label)


class RoadmapTab(QWidget):
    """연간 로드맵을 보여주는 탭입니다."""

    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.is_loaded = False
        self.setup_ui()
        global_signals.schedule_updated.connect(self.refresh_data)
        global_signals.roadmap_group_updated.connect(self.refresh_data)
        global_signals.font_size_changed.connect(self.on_font_changed)

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # --- [상단: 컨트롤 영역] ---
        top_layout = QHBoxLayout()
        top_layout.addWidget(TitleLabel("🗺️ 연간 업무 로드맵"))

        self.year_combo = QComboBox()
        self.year_combo.setMinimumWidth(90)
        self.update_year_combo()
        self.year_combo.currentTextChanged.connect(self.refresh_data)

        self.group_mgr_btn = StyledButton("⚙️ 그룹 관리", COLORS["blue-500"])
        self.group_mgr_btn.clicked.connect(self.open_group_manager)

        top_layout.addStretch()
        top_layout.addWidget(self.year_combo)
        top_layout.addWidget(self.group_mgr_btn)
        layout.addLayout(top_layout)

        # --- [메인: 간트 차트 영역] ---
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet(
            tw("border-b", "border-c80-20", "bg-transparent")
        )

        self.canvas = RoadmapCanvas(self)
        self.scroll_area.setWidget(self.canvas)
        layout.addWidget(self.scroll_area)

    def update_year_combo(self):
        current_year = QDate.currentDate().year()

        active_years = set()

        # Default Years
        active_years.add(current_year - 1)
        active_years.add(current_year)
        active_years.add(current_year + 1)

        schedules = db_manager.get_schedules()
        for s in schedules:
            if not s.get("is_roadmap", False):
                continue

            # 시작종료일 추출
            s_year = QDate.fromString(s["start_date"], "yyyy-MM-dd").year()
            e_year = QDate.fromString(s["end_date"], "yyyy-MM-dd").year()

            # 반복 종료일이 있다면 해당 일자도 추출
            rep_end = s.get("repeat_end", "")
            if rep_end:
                r_year = QDate.fromString(rep_end, "yyyy-MM-dd").year()
                e_year = max(e_year, r_year)

            if s_year > 0 and e_year >= s_year:
                for y in range(s_year, e_year + 1):
                    active_years.add(y)

        sorted_years = sorted(list(active_years))
        new_years = [f"{y}년" for y in sorted_years]
        current_items = [
            self.year_combo.itemText(i) for i in range(self.year_combo.count())
        ]

        if current_items != new_years:
            self.year_combo.blockSignals(True)

            selected_text = self.year_combo.currentText()
            if not selected_text:
                selected_text = f"{current_year}년"

            self.year_combo.clear()
            self.year_combo.addItems(new_years)

            if selected_text in new_years:
                self.year_combo.setCurrentText(selected_text)
            else:
                self.year_combo.setCurrentText(f"{current_year}년")

            self.year_combo.blockSignals(False)

    def open_group_manager(self):
        dialog = GroupManagerDialog(self)
        dialog.exec()

    def refresh_data(self):
        self.update_year_combo()

        year_text = self.year_combo.currentText()
        if not year_text:
            return

        year = int(year_text.replace("년", ""))
        groups = db_manager.get_roadmap_groups()
        all_schedules = db_manager.get_schedules()

        roadmap_schedules = []
        for s in all_schedules:
            if not s.get("is_roadmap", False):
                continue

            s_year = QDate.fromString(s["start_date"], "yyyy-MM-dd").year()
            e_year = QDate.fromString(s["end_date"], "yyyy-MM-dd").year()

            rtype = s.get("repeat_type", "none")
            repeat_end_str = s.get("repeat_end", "")

            if rtype == "none":
                if s_year <= year <= e_year:
                    roadmap_schedules.append(s)
            else:
                # 반복을 위한 가짜 날짜(종료일을 지정하지 않을 경우를 대비)
                r_year = 3000
                if repeat_end_str:
                    r_year = QDate.fromString(repeat_end_str, "yyyy-MM-dd").year()

                if s_year <= year <= r_year:
                    virtual_s = s.copy()
                    render_start = f"{year}-01-01" if s_year < year else s["start_date"]
                    render_end = (
                        repeat_end_str if repeat_end_str else f"{year + 1}-12-31"
                    )

                    virtual_s["render_start"] = render_start
                    virtual_s["render_end"] = render_end

                    roadmap_schedules.append(virtual_s)

        roadmap_schedules.sort(key=lambda x: (x["start_date"], x["end_date"]))
        self.canvas.update_data(year, groups, roadmap_schedules)

    def on_font_changed(self):
        if self.isVisible():
            QTimer.singleShot(10, self.canvas.draw_bars)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(100, self.canvas.draw_bars)
