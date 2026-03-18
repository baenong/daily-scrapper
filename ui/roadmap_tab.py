from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QScrollArea,
    QComboBox,
    QMessageBox,
)
from PySide6.QtCore import Qt, QDate, QTimer, QRect
from PySide6.QtGui import QPainter, QColor, QPen, QPalette, QFont, QFontMetrics

from core import db_manager
from core.signals import global_signals
from core.style import COLORS, tw
from ui.components import (
    TitleLabel,
    DescriptionLabel,
    StyledButton,
    ClickableEventLabel,
    EventDialog,
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

        font = QFont()
        fm = QFontMetrics(font)

        for s in self.schedules:
            g_id = s.get("group_id")

            if g_id is not None:
                try:
                    g_id = int(g_id)
                except (ValueError, TypeError):
                    g_id = None

            if g_id not in slots:
                g_id = None

            x_start = self._get_x_pos(s["start_date"])
            end_date = QDate.fromString(s["end_date"], "yyyy-MM-dd").addDays(1)
            x_end = self._get_x_pos(end_date.toString("yyyy-MM-dd"))

            bar_w = max(x_end - x_start, 15)

            title_text = f"{s['title']} "
            text_width = len(title_text) * 10
            bar_right_x = x_start + bar_w + 3
            put_inside = bar_w >= text_width + 5

            if put_inside:
                display_text = title_text
                visual_end = bar_right_x
            else:
                space = self.width() - (x_start + bar_w + 3)
                if space < 0:
                    space = 0

                if text_width > space:
                    display_text = fm.elidedText(
                        title_text, Qt.TextElideMode.ElideRight, space
                    )
                    visual_end = self.width() - 5
                else:
                    display_text = title_text
                    visual_end = bar_right_x + text_width + 5

            slot_idx = 0
            while True:
                conflict = False
                if len(slots[g_id]) > slot_idx:
                    for existing_start, existing_end in slots[g_id][slot_idx]:
                        if x_start < existing_end and visual_end > existing_start:
                            conflict = True
                            break
                if not conflict:
                    break
                slot_idx += 1

            # 슬롯 할당
            while len(slots[g_id]) <= slot_idx:
                slots[g_id].append([])
            slots[g_id][slot_idx].append((x_start, visual_end))

            # 라벨 위젯 생성
            y_pos = g_y_map[g_id] + (slot_idx * 26) + 5

            is_completed = s.get("is_completed", False)
            bg_hex = QColor(s["color"])
            bg_color = (
                f"rgba({bg_hex.red()}, {bg_hex.green()}, {bg_hex.blue()}, 0.4)"
                if is_completed
                else s["color"]
            )

            # Bar
            bar_label = ClickableEventLabel(s, display_text if put_inside else "")
            bar_label.setToolTip(f"{s['title']}\n({s['start_date']} ~ {s['end_date']})")
            bar_label.setStyleSheet(
                f"""
                background-color: {bg_color};
                {tw("rounded", "text-13", "p-2")}
                """
            )
            bar_label.setParent(self)
            bar_label.setGeometry(x_start, int(y_pos), bar_w, 22)
            bar_label.show()

            self.overlay_widgets.append(bar_label)

            # Floating Text
            if not put_inside:
                text_label = ClickableEventLabel(s, f" {s['title']}")
                text_label.setStyleSheet(
                    tw("text-windowtext", "bg-transparent", "text-13")
                )
                text_label.setParent(self)
                text_label.setGeometry(bar_right_x, int(y_pos), text_width + 10, 22)
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
        top_layout.addWidget(DescriptionLabel("연간 로드맵을 표시합니다."))

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

            if s_year <= year <= e_year:
                roadmap_schedules.append(s)

        roadmap_schedules.sort(key=lambda x: (x["start_date"], x["end_date"]))
        self.canvas.update_data(year, groups, roadmap_schedules)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(10, self.canvas.draw_bars)
