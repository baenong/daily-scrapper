from PySide6.QtWidgets import (
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
from core.style import COLORS, tw
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
        line_color = QColor(128, 128, 128, 60)
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

            start_date_str = s["start_date"]
            start_date = QDate.fromString(start_date_str, "yyyy-MM-dd").addDays(-1)
            is_underflow = start_date.year() < self.target_year

            end_date_str = s["end_date"]
            end_date = QDate.fromString(end_date_str, "yyyy-MM-dd").addDays(1)
            is_overflow = end_date.year() > self.target_year

            # 반복처리
            rtype = s.get("repeat_type", "none")
            repeat_label = ""
            repeat_string = ""

            if rtype != "none":
                if rtype == "yearly":
                    repeat_label = "매년"
                elif rtype == "monthly":
                    repeat_label = "매월"
                elif rtype == "weekly":
                    repeat_label = "매주"

                repeat_end_str = s.get("repeat_end", "")
                if repeat_end_str:
                    repeat_end_date = QDate.fromString(repeat_end_str, "yyyy-MM-dd")
                    repeat_end = f"~{repeat_end_date.toString('yy.MM.dd')}"
                else:
                    repeat_end = " 반복"

                repeat_string = f" ({repeat_label} {repeat_end})"

            bar_x_start = self._get_x_pos(start_date_str)
            bar_x_end = self._get_x_pos(end_date_str)

            # Bar의 너비 (최소 15 보장)
            bar_width = max(bar_x_end - bar_x_start, 10)
            bar_height = 22

            title_text = f"{s['title']}{repeat_string}"
            display_text = title_text  # 공간이 없어서 줄이는 경우 아니면 title 그대로

            font = QFont("Pretendard Variable", 10)
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
            is_repeating = rtype != "none"
            text_css = "text-c13"
            bg_hex = QColor(s["color"])
            bg_rgb = f"{bg_hex.red()}, {bg_hex.green()}, {bg_hex.blue()}"

            if is_completed:
                text_css = ""
                bg_color = f"rgba({bg_rgb}, 0.2)"

            elif is_repeating:
                bg_color = f"rgba({bg_rgb}, 0.8)"

            else:
                bg_color = s["color"]

            # Bar
            bar_label = ClickableEventLabel(s, display_text if put_inside else "")
            bar_label.setToolTip(f"{s['title']}\n({start_date_str} ~ {end_date_str})")

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

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # --- [상단: 컨트롤 영역] ---
        top_layout = QHBoxLayout()
        top_layout.addWidget(TitleLabel("🗺️ 연간 업무 로드맵"))

        self.year_combo = QComboBox()
        current_year = QDate.currentDate().year()
        self.year_combo.addItems(
            [f"{y}년" for y in range(current_year - 2, current_year + 2)]
        )
        self.year_combo.setCurrentText(f"{current_year}년")
        self.year_combo.setMinimumWidth(90)
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

    def open_group_manager(self):
        dialog = GroupManagerDialog(self)
        dialog.exec()

    def refresh_data(self):
        year = int(self.year_combo.currentText().replace("년", ""))

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
                r_year = 9999
                if repeat_end_str:
                    r_year = QDate.fromString(repeat_end_str, "yyyy-MM-dd").year()

                if s_year <= year <= r_year:
                    virtual_s = s.copy()

                    if s_year < year:
                        virtual_s["start_date"] = f"{year}-01-01"

                    if repeat_end_str:
                        virtual_s["end_date"] = repeat_end_str
                    else:
                        virtual_s["end_date"] = f"{year + 1}-12-31"

                    roadmap_schedules.append(virtual_s)

        roadmap_schedules.sort(key=lambda x: (x["start_date"], x["end_date"]))
        self.canvas.update_data(year, groups, roadmap_schedules)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(10, self.canvas.draw_bars)
