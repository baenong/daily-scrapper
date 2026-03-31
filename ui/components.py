import json
import webbrowser
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QMenu,
    QDialog,
    QColorDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QLineEdit,
    QDateEdit,
    QListWidget,
    QListWidgetItem,
    QStackedWidget,
    QRadioButton,
    QButtonGroup,
    QScrollArea,
    QCheckBox,
    QComboBox,
    QSpinBox,
    QToolTip,
    QMessageBox,
    QFrame,
    QInputDialog,
    QSizePolicy,
)
from PySide6.QtGui import (
    QColor,
    QPixmap,
    QIcon,
    QMouseEvent,
    QEnterEvent,
    QContextMenuEvent,
)
from PySide6.QtCore import (
    Qt,
    Signal,
    QTimer,
    QDate,
    QPoint,
    QPropertyAnimation,
    QEasingCurve,
)
from core import db_manager
from core.signals import global_signals
from core.tw_utils import DEFAULT_COLORS, COLORS, tw, tw_sheet


class StyledButton(QPushButton):
    """
    버튼의 색상을 입력받아 일관된 스타일의 버튼을 반환하는 클래스

    text: 버튼의 caption
    bg_color_hex: 배경색을 hex로 입력
    text_color: (default: white) 글자색
    """

    def __init__(self, text, bg_color_hex, text_color=None, padding="5px 14px"):
        super().__init__(text)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        if bg_color_hex == "transparent":
            normal_bg = "transparent"
            hover_bg = "rgba(128, 128, 128, 0.15)"
            pressed_bg = "rgba(128, 128, 128, 0.3)"
            final_text_color = text_color if text_color else "palette(window-text)"

        else:
            base_color = QColor(bg_color_hex)
            normal_bg = base_color.name()
            hover_bg = base_color.lighter(115).name()
            pressed_bg = base_color.darker(110).name()

            if not text_color:
                luminance = (
                    base_color.red() * 0.299
                    + base_color.green() * 0.587
                    + base_color.blue() * 0.114
                )

                final_text_color = COLORS["c13"] if luminance > 150 else "#FFFFFF"
            else:
                final_text_color = text_color

        self.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {normal_bg};
                color: {final_text_color};
                border: none;
                border-radius: 4px;
                padding: {padding};
                min-height: 20px;
            }}
            QPushButton:hover {{
                background-color: {hover_bg};
            }}
            QPushButton:pressed {{
                background-color: {pressed_bg};
            }}
        """
        )


class DoubleClickLineEdit(QLineEdit):
    """더블 클릭 이벤트를 가능하게 한 커스텀 QLineEdit"""

    doubleClicked = Signal()
    focusLost = Signal()

    def mouseDoubleClickEvent(self, event):
        super().mouseDoubleClickEvent(event)
        self.doubleClicked.emit()

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        QTimer.singleShot(0, self.focusLost.emit)


class TitleLabel(QLabel):
    def __init__(self, text="", size=14, parent=None):
        super().__init__(text, parent)
        self.base_style = tw("font-bold", "mb-5")
        self.font_size = size
        self.update_font_size()
        global_signals.font_size_changed.connect(self.update_font_size)

    def update_font_size(self):
        app: QApplication = QApplication.instance()
        base_size = app.font().pixelSize()
        target_size = int(base_size * (self.font_size / 10))
        self.setStyleSheet(f"{self.base_style} font-size: {target_size}px;")


class BoldLabel(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(tw("font-bold", "mr-8"))


class DescriptionLabel(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(tw("text-c77", "mb-10"))


class EllipsisLabel(QLabel):
    """영역을 벗어나면 자동으로 말줄임표(...) 처리를 해주는 라벨입니다."""

    def __init__(self, text):
        super().__init__()
        self._original_text = text
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setStyleSheet(tw("bg-transparent", "border-none"))

    def resizeEvent(self, event):
        """위젯의 가로 크기가 변할 때마다 실행되어 글자를 알맞게 자릅니다."""
        metrics = self.fontMetrics()
        elided_text = metrics.elidedText(
            self._original_text, Qt.TextElideMode.ElideRight, self.width() - 5
        )

        super().setText(elided_text)
        super().resizeEvent(event)


class EditableRowWidget(QWidget):
    """뉴스 키워드와 법령 목록 모두에서 재사용 가능한 체크박스+편집 위젯입니다."""

    def __init__(self, text, is_checked, save_callback):
        super().__init__()
        self.save_callback = save_callback

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.checkbox = QCheckBox()
        self.checkbox.setChecked(is_checked)

        self.line_edit = DoubleClickLineEdit(text)
        self.line_edit.setReadOnly(True)

        # 앞서 만든 커스텀 버튼 활용 (파란색 편집, 초록색 저장, 투명배경 빨간글씨 삭제)
        self.btn_edit = StyledButton("편집", "#2196F3")
        self.btn_save = StyledButton("저장", "#4CAF50")
        self.btn_save.hide()
        self.btn_del = StyledButton("❌", "transparent", "#F44336", "5px 10px")

        layout.addWidget(self.checkbox)
        layout.addWidget(self.line_edit, stretch=1)
        layout.addWidget(self.btn_edit)
        layout.addWidget(self.btn_save)
        layout.addWidget(self.btn_del)

        # 이벤트 핸들러
        self.btn_edit.clicked.connect(self.enable_edit)
        self.btn_save.clicked.connect(self.save_edit)
        self.btn_del.clicked.connect(self.delete_row)
        self.line_edit.doubleClicked.connect(self.enable_edit)
        self.line_edit.returnPressed.connect(self.save_edit)
        self.line_edit.focusLost.connect(self.save_edit)

    def enable_edit(self):
        self.line_edit.setReadOnly(False)
        self.line_edit.setStyleSheet("background-color: white; color: black;")
        self.line_edit.setFocus()
        self.btn_edit.hide()
        self.btn_save.show()

    def save_edit(self):
        if self.line_edit.isReadOnly():
            return

        self.line_edit.setReadOnly(True)
        self.line_edit.setStyleSheet("")
        self.btn_save.hide()
        self.btn_edit.show()
        self.save_callback()

    def delete_row(self):
        self.setParent(None)
        self.deleteLater()
        self.save_callback()


class ArticleItemWidget(QWidget):
    """뉴스와 정책브리핑 리스트에 사용할 수 있는 커스템 위젯"""

    def __init__(self, title, source, pub_date, icon=""):
        super().__init__()

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(tw("bg-transparent", "p-5"))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.title_label = QLabel(f"{icon} {title}")
        self.title_label.setStyleSheet(tw("text-14", "bg-transparent"))

        self.meta_label = QLabel(f"[{source}]  🗓️ {pub_date}")
        self.meta_label.setStyleSheet(tw("text-13", "text-c77", "bg-transparent"))

        layout.addWidget(self.title_label)
        layout.addWidget(self.meta_label)

    def set_highligt(self, bg="bg-transparent"):
        self.setStyleSheet(tw(bg, "p-5"))


class DashboardItemWidget(QWidget):
    """대시보드 카드 내부에 들어가는 개별 항목 위젯"""

    def __init__(self, text, use_ellipsis=False, is_completed=False):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(
            tw_sheet({"DashboardItemWidget": "border-bb border-black-5"})
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 8, 5, 8)

        if use_ellipsis:
            self.label = EllipsisLabel(text)
        else:
            self.label = QLabel(text)

        if is_completed:
            self.label.setStyleSheet(tw("text-gray"))

        layout.addWidget(self.label)


class DashboardCard(QFrame):
    """대시보드에 들어갈 개별 정보 카드 위젯입니다."""

    def __init__(self, title, btn_text, btn_callback):
        super().__init__()
        # 카드 느낌을 내기 위해 테두리와 배경색을 살짝 줍니다.
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            tw_sheet({"DashboardCard": "bg-c80-5 rounded-8 border-b border-c80-20"})
        )

        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(25, 25, 25, 25)

        # 타이틀
        self.title_label = TitleLabel(title)
        layout.addWidget(self.title_label)

        # 리스트 (정보가 표시될 영역)
        self.items_container = QWidget()
        self.items_container.setStyleSheet(tw("bg-transparent"))

        self.items_layout = QVBoxLayout(self.items_container)
        self.items_layout.setContentsMargins(0, 0, 0, 0)
        self.items_layout.setSpacing(0)

        layout.addWidget(self.items_container)
        layout.addStretch(1)

        self.detail_btn = StyledButton(btn_text, COLORS["c33"], COLORS["blue-500"])
        self.detail_btn.setFixedHeight(40)
        self.detail_btn.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.detail_btn.clicked.connect(btn_callback)
        layout.addWidget(self.detail_btn)

    def add_item(self, text, use_ellipsis=False, is_completed=False):
        item_widget = DashboardItemWidget(text, use_ellipsis, is_completed)
        self.items_layout.addWidget(item_widget)

    def clear_items(self):
        while self.items_layout.count():
            child = self.items_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()


class TrendRow(QWidget):
    """전광판의 개별 한 줄을 담당하며 좌/우 정렬을 처리하는 위젯입니다."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)  # 위아래 여백을 넉넉히 줍니다
        layout.setSpacing(10)

        self.left_label = QLabel()
        self.left_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )

        self.right_label = QLabel()
        self.right_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        layout.addWidget(self.left_label, 1)
        layout.addWidget(self.right_label, 0)

    def set_data(self, rank_text, keyword, description, traffic):
        desc_text = f" - {description}" if description else ""
        self.left_label.setText(f"{rank_text}{keyword}{desc_text}")
        self.right_label.setText(traffic)

    def set_style(self, mode):
        if mode == "highlight":
            self.setStyleSheet(
                tw_sheet(
                    {
                        "TrendRow": "rounded-4 bg-red-600",
                    }
                )
            )
            self.left_label.setStyleSheet(tw("text-white", "text-16", "pl-15"))
            self.right_label.setStyleSheet(tw("text-white", "text-16", "pr-20"))
        else:
            self.setStyleSheet(tw_sheet({"TrendRow": "border-none bg-transparent"}))
            self.left_label.setStyleSheet(tw("text-c77", "pl-15"))
            self.right_label.setStyleSheet(tw("text-c77", "pr-20"))


class TrendTickerWidget(QFrame):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.trends_data = []
        self.current_index = 0

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        # 내용물: 4개의 Row를 담는 컨테이너 (실제로는 3개만 보이고 1개는 대기열 역할)
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(5)

        self.rows: list[TrendRow] = []
        for _ in range(6):
            row = TrendRow()
            self.rows.append(row)
            self.content_layout.addWidget(row)

        self.scroll_area.setWidget(self.content)
        main_layout.addWidget(self.scroll_area)

        self.anim = QPropertyAnimation(self.scroll_area.verticalScrollBar(), b"value")
        self.anim.setDuration(500)
        self.anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.anim.finished.connect(self._on_animation_finished)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.start_slide)

        global_signals.font_size_changed.connect(self.update_height)

    def set_data(self, trends):
        self.trends_data = trends
        self.current_index = 0
        if self.trends_data:
            self._populate_rows()
            self.timer.start(3000)
            QTimer.singleShot(100, self.update_height)
        else:
            self.rows[2].set_data(
                "🔥", "데이터 없음", "트렌드를 가져오지 못했습니다.", ""
            )
            self.rows[2].set_style("highlight")

    def _get_trend(self, offset):
        if not self.trends_data:
            return None
        idx = (self.current_index + offset) % len(self.trends_data)
        return self.trends_data[idx]

    def _populate_rows(self):
        offsets = [-2, -1, 0, 1, 2, 3]
        for i, offset in enumerate(offsets):
            trend = self._get_trend(offset)
            rank_str = "·  "
            self.rows[i].set_data(
                rank_str, trend["keyword"], trend["description"], trend["traffic"]
            )

        self.rows[0].set_style("dim")
        self.rows[1].set_style("dim")
        self.rows[2].set_style("highlight")
        self.rows[3].set_style("dim")
        self.rows[4].set_style("dim")
        self.rows[5].set_style("dim")

    def start_slide(self):
        if not self.trends_data:
            return

        # 포커스 이동
        self.rows[2].set_style("dim")
        self.rows[3].set_style("highlight")

        # 첫 번째 행의 높이 + 여백만큼 스크롤바를 아래로
        slide_dist = self.rows[0].height() + self.content_layout.spacing()

        self.anim.setStartValue(0)
        self.anim.setEndValue(slide_dist)
        self.anim.start()

    def _on_animation_finished(self):
        self.current_index = (self.current_index + 1) % len(self.trends_data)

        # 밀려 올라간 데이터들을 다음 순서로 덮어씌움 (다시 Row 1이 중앙 데이터가 됨)
        self._populate_rows()
        self.scroll_area.verticalScrollBar().setValue(0)

    def update_height(self):
        if self.content_layout.count() >= 5:
            h = sum(self.rows[i].sizeHint().height() for i in range(5))
            h += self.content_layout.spacing() * 4
            self.scroll_area.setFixedHeight(h)


class ClickableColorLabel(QLabel):
    clicked = Signal()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class ScheduleActionMixin:
    def handle_double_click(self):
        if self.schedule_data.get("is_law"):
            webbrowser.open(self.schedule_data.get("link", ""))
        else:
            self.edit_event()

    def toggle_event(self, checked=None):
        if isinstance(checked, bool):
            new_status = checked
        else:
            new_status = not self.schedule_data.get("is_completed", False)

        s = self.schedule_data
        db_manager.update_schedule(
            s["id"],
            s["title"],
            s["start_date"],
            s["end_date"],
            s["repeat_type"],
            s.get("repeat_rule", ""),
            s["repeat_end"],
            s["color"],
            s.get("description", ""),
            new_status,
            s.get("is_roadmap", False),
            s.get("group_id", None),
        )

        self.schedule_data["is_completed"] = new_status
        global_signals.schedule_updated.emit()

    def edit_event(self):
        dialog = EventDialog(
            self.schedule_data["start_date"],
            schedule_data=self.schedule_data,
            parent=self.window(),
        )
        dialog.exec()

    def delete_event(self):
        reply = QMessageBox.question(
            self,
            "삭제",
            f"'{self.schedule_data['title']}' 일정을 삭제하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            db_manager.delete_schedule(self.schedule_data["id"])
            global_signals.schedule_updated.emit()


class ClickableEventLabel(QLabel, ScheduleActionMixin):
    def __init__(self, schedule_data, text, parent=None):
        super().__init__(text, parent)
        self.schedule_data = schedule_data
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    # ToolTip 관련 Override
    def enterEvent(self, event: QEnterEvent):
        if QToolTip.isVisible() and QToolTip.text() == self.toolTip():
            super().enterEvent(event)
            return

        if self.toolTip():
            widget_bottom_left = self.mapToGlobal(QPoint(0, self.height()))
            widget_bottom_left.setY(widget_bottom_left.y() + 2)
            QToolTip.showText(widget_bottom_left, self.toolTip(), self)

        super().enterEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.handle_double_click()
            event.accept()

    def contextMenuEvent(self, event: QContextMenuEvent):
        """우클릭 시 실행되는 컨텍스트 메뉴입니다."""
        menu = QMenu(self)
        menu.setStyleSheet(
            tw_sheet(
                {
                    "QMenu": "bg-white p-5 border-b border-cCC text-13 text-black no-underline",
                    "QMenu::item": "py-6 px-10 no-underline text-c13",
                    "QMenu::item:selected": "bg-cF0",
                    "QMenu::item:disabled": "text-c33 font-bold bg-cFA",
                    "QMenu::separator": "h-1 bg-cE0 my-2 mx-0",
                }
            )
        )

        title_action = menu.addAction(f"🏷️ {self.schedule_data['title']}")
        title_action.setEnabled(False)
        menu.addSeparator()

        original_style = self.styleSheet()
        pos = event.globalPos()

        def restore_style():
            try:
                self.setStyleSheet(original_style)
            except RuntimeError:
                pass

        menu.aboutToHide.connect(restore_style)
        self.setStyleSheet(
            original_style + tw("border-2", "border-solid", "border-c33")
        )

        # 법령인 경우 링크 열기만 메뉴에 추가
        if self.schedule_data.get("is_law"):
            action_link = menu.addAction("🔗 국가법령정보센터에서 보기")
            action = menu.exec(pos)

            if action == action_link:
                webbrowser.open(self.schedule_data.get("link", ""))
            return

        is_completed = self.schedule_data.get("is_completed", False)
        status_text = "미완료 처리" if is_completed else "완료 처리"

        action_toggle = menu.addAction(f"✅ {status_text}")
        action_edit = menu.addAction("✏️ 편집")
        action_delete = menu.addAction("🗑️ 삭제")

        action = menu.exec(pos)

        if action == action_toggle:
            self.toggle_event()
        elif action == action_edit:
            self.edit_event()
        elif action == action_delete:
            self.delete_event()


class Separator(QFrame):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(11)
        self.setStyleSheet(
            tw_sheet({"QFrame": "border-none border-bb border-c99-30 my-5"})
        )


class CustomDateEdit(QDateEdit):
    def __init__(self, date_str):
        super().__init__(date_str)
        self.setCalendarPopup(True)
        self.setDisplayFormat("yy.MM.dd (ddd)")
        self.setMinimumWidth(125)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)


class GroupManagerDialog(QDialog):
    """로드맵 그룹을 추가/삭제하는 관리 팝업입니다."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("로드맵 그룹 관리")
        self.setFixedSize(300, 400)

        layout = QVBoxLayout(self)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(
            tw_sheet(
                {
                    "QListWidget": "p-5",
                    "QListWidget::item": "p-5",
                }
            )
        )
        layout.addWidget(self.list_widget)

        input_layout = QHBoxLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("새 그룹 이름")
        self.add_btn = StyledButton("추가", COLORS["green-500"])
        self.add_btn.clicked.connect(self.add_group)

        input_layout.addWidget(self.name_input)
        input_layout.addWidget(self.add_btn)
        layout.addLayout(input_layout)

        self.del_btn = StyledButton("선택 그룹 삭제", COLORS["red-500"])
        self.del_btn.clicked.connect(self.delete_group)
        layout.addWidget(self.del_btn)

        self.load_groups()

    def load_groups(self):
        self.list_widget.clear()
        for g in db_manager.get_roadmap_groups():
            item = QListWidgetItem(g["name"])
            item.setData(Qt.ItemDataRole.UserRole, g["id"])
            self.list_widget.addItem(item)

    def add_group(self):
        name = self.name_input.text().strip()
        if name:
            # 색상은 랜덤 배정 또는 기본값 처리 (심화 시 ColorPicker 추가 가능)
            db_manager.add_roadmap_group(name, "#2196F3")
            self.name_input.clear()
            self.load_groups()
            global_signals.roadmap_group_updated.emit()

    def delete_group(self):
        item = self.list_widget.currentItem()
        if item:
            if item.text() == "미지정":
                QMessageBox.warning(
                    self, "삭제 불가", "기본 그룹인 '미지정'은 삭제할 수 없습니다."
                )
                return

            group_id = item.data(Qt.ItemDataRole.UserRole)
            db_manager.delete_roadmap_group(group_id)
            self.load_groups()

            global_signals.roadmap_group_updated.emit()
            global_signals.schedule_updated.emit()


class EventDialog(QDialog):
    """일정 관리 팝업"""

    def __init__(self, date_str, schedule_data=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("일정 관리")
        self.setMinimumWidth(450)
        self.schedule_data = schedule_data

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSizeConstraint(QVBoxLayout.SizeConstraint.SetFixedSize)

        # Title
        title_layout = QHBoxLayout()
        title_layout.addWidget(BoldLabel("📌 이름"))
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("일정 이름을 입력해주세요")
        self.title_input.setStyleSheet(tw("py-5"))
        title_layout.addWidget(self.title_input, stretch=1)
        layout.addLayout(title_layout)
        layout.addWidget(Separator())

        # Period
        date_layout = QHBoxLayout()
        date_layout.addWidget(BoldLabel("📅 기간"))
        self.start_date = CustomDateEdit(QDate.fromString(date_str, "yyyy. MM. dd"))
        date_layout.addWidget(self.start_date)
        date_layout.addWidget(QLabel("  ~ "))
        self.end_date = CustomDateEdit(QDate.fromString(date_str, "yyyy. MM. dd"))
        date_layout.addWidget(self.end_date)
        layout.addLayout(date_layout)
        layout.addWidget(Separator())

        # Repeat
        repeat_layout = QHBoxLayout()
        repeat_layout.addWidget(BoldLabel("🔁 반복"))
        self.repeat_combo = QComboBox()
        self.repeat_combo.addItems(["반복 없음", "일", "주", "월", "연"])
        self.repeat_combo.setFixedWidth(100)
        repeat_layout.addWidget(self.repeat_combo)
        repeat_layout.addStretch()
        layout.addLayout(repeat_layout)

        # Repeat Detail(Hidden default)
        self.repeat_detail_widget = QWidget()
        self.repeat_detail_widget.setStyleSheet(tw_sheet({"QCheckBox": "mt-2"}))
        detail_layout = QVBoxLayout(self.repeat_detail_widget)
        detail_layout.setContentsMargins(5, 5, 5, 5)
        detail_layout.addWidget(Separator())

        # --- [공통 영역: 주기 & 평일 조건 & 종료일] ---
        common_layout = QVBoxLayout()
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("주기 : "))
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 51)
        self.interval_spin.setFixedWidth(60)
        interval_layout.addWidget(self.interval_spin)
        self.interval_unit_label = QLabel("마다")
        interval_layout.addWidget(self.interval_unit_label)
        interval_layout.addStretch()
        common_layout.addLayout(interval_layout)

        end_layout = QHBoxLayout()
        self.has_repeat_end_cb = QCheckBox("종료일 지정 : ")
        end_layout.addWidget(self.has_repeat_end_cb)
        self.repeat_end = CustomDateEdit(QDate.currentDate())
        self.repeat_end.setEnabled(False)
        self.has_repeat_end_cb.toggled.connect(self.repeat_end.setEnabled)
        end_layout.addWidget(self.repeat_end)
        end_layout.addStretch()
        common_layout.addLayout(end_layout)

        self.weekday_only_cb = QCheckBox("휴일(주말/공휴일)일 경우 직전 평일로 앞당김")
        common_layout.addWidget(self.weekday_only_cb)

        detail_layout.addLayout(common_layout)
        detail_layout.addWidget(Separator())

        # --- [타입별 동적 패널 (Stacked Widget)] ---
        self.repeat_stack = QStackedWidget()

        # Page 0: 매일 (추가 설정 없음)
        self.page_daily = QWidget()
        self.repeat_stack.addWidget(self.page_daily)

        # Page 1: 매주 (요일 선택)
        self.page_weekly = QWidget()
        weekly_layout = QHBoxLayout(self.page_weekly)
        weekly_layout.setContentsMargins(0, 0, 0, 0)
        self.week_cbs = []
        for day in ["월", "화", "수", "목", "금", "토", "일"]:
            cb = QCheckBox(day)
            self.week_cbs.append(cb)
            weekly_layout.addWidget(cb)
        self.repeat_stack.addWidget(self.page_weekly)

        # Page 2: 매월 (특정일 vs N번째 요일)
        self.page_monthly = QWidget()
        monthly_layout = QVBoxLayout(self.page_monthly)
        monthly_layout.setContentsMargins(0, 0, 0, 0)

        # 라디오 그룹 묶기
        self.month_radio_group = QButtonGroup(self)

        date_opt_layout = QHBoxLayout()
        self.month_date_radio = QRadioButton("매월")
        self.month_date_radio.setChecked(True)
        self.month_radio_group.addButton(self.month_date_radio)
        self.month_date_spin = QSpinBox()
        self.month_date_spin.setRange(1, 31)
        self.month_date_spin.setFixedWidth(60)
        date_opt_layout.addWidget(self.month_date_radio)
        date_opt_layout.addWidget(self.month_date_spin)
        date_opt_layout.addWidget(QLabel("일"))
        date_opt_layout.addStretch()

        nth_opt_layout = QHBoxLayout()
        self.month_nth_radio = QRadioButton("매월")
        self.month_radio_group.addButton(self.month_nth_radio)
        self.month_nth_combo = QComboBox()
        self.month_nth_combo.addItems(
            ["첫 번째", "두 번째", "세 번째", "네 번째", "마지막"]
        )
        self.month_nth_combo.setFixedWidth(100)
        self.month_day_combo = QComboBox()
        self.month_day_combo.addItems(["월", "화", "수", "목", "금", "토", "일"])
        self.month_day_combo.setFixedWidth(60)
        nth_opt_layout.addWidget(self.month_nth_radio)
        nth_opt_layout.addWidget(self.month_nth_combo)
        nth_opt_layout.addWidget(self.month_day_combo)
        nth_opt_layout.addWidget(QLabel("요일"))
        nth_opt_layout.addStretch()

        monthly_layout.addLayout(date_opt_layout)
        monthly_layout.addLayout(nth_opt_layout)
        self.repeat_stack.addWidget(self.page_monthly)

        # Page 3: 매년 (월, 일 선택)
        self.page_yearly = QWidget()
        yearly_layout = QHBoxLayout(self.page_yearly)
        yearly_layout.setContentsMargins(0, 5, 0, 5)
        yearly_layout.addWidget(QLabel("매년"))
        self.year_month_spin = QSpinBox()
        self.year_month_spin.setRange(1, 12)
        yearly_layout.addWidget(self.year_month_spin)
        yearly_layout.addWidget(QLabel("월"))
        self.year_day_spin = QSpinBox()
        self.year_day_spin.setRange(1, 31)
        yearly_layout.addWidget(self.year_day_spin)
        yearly_layout.addWidget(QLabel("일"))
        yearly_layout.addStretch()
        self.repeat_stack.addWidget(self.page_yearly)

        detail_layout.addWidget(self.repeat_stack)
        layout.addWidget(self.repeat_detail_widget)
        self.repeat_detail_widget.setVisible(False)  # 처음에는 숨김

        # 콤보박스 변경 시 UI 업데이트 연결
        self.repeat_combo.currentIndexChanged.connect(self.update_repeat_ui)

        layout.addWidget(Separator())

        # Color Section
        color_layout = QHBoxLayout()
        color_layout.addWidget(BoldLabel("🎨 색상"))

        # 미리 지정된 색 말고도 색을 선택할 수 있도록
        self.color_preview = ClickableColorLabel()
        self.color_preview.setFixedSize(20, 20)
        self.color_preview.setCursor(Qt.CursorShape.PointingHandCursor)
        self.color_preview.setToolTip("클릭하여 다른 색상을 선택하세요")
        self.color_preview.clicked.connect(self.open_color_picker)
        color_layout.addWidget(self.color_preview)

        self.add_color_label = QLabel("← 다른색상 선택")
        color_layout.addWidget(self.add_color_label)

        self.save_color_btn = StyledButton("선택한 색상 추가", "transparent")
        self.save_color_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_color_btn.setToolTip("현재 색상을 즐겨찾기에 추가합니다")
        self.save_color_btn.clicked.connect(self.save_custom_color)
        color_layout.addWidget(self.save_color_btn)

        self.delete_color_btn = StyledButton(
            "선택한 색상 삭제", "transparent", COLORS["red-500"]
        )
        self.delete_color_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_color_btn.setToolTip("현재 색상을 삭제합니다. (기본색상 제외)")
        self.delete_color_btn.clicked.connect(self.delete_custom_color)
        color_layout.addWidget(self.delete_color_btn)

        color_layout.addStretch()

        self.color_combo = QComboBox()
        self.color_combo.setMinimumWidth(125)
        self.colors = DEFAULT_COLORS.copy()
        custom_colors = db_manager.get_custom_colors()
        self.colors.update(custom_colors)

        for name, hex_color in self.colors.items():
            pixmap = QPixmap(16, 16)
            pixmap.fill(QColor(hex_color))
            self.color_combo.addItem(QIcon(pixmap), name)

        self.color_combo.currentIndexChanged.connect(self.update_color_preview)
        self.update_color_preview()

        color_layout.addWidget(self.color_combo)
        layout.addLayout(color_layout)
        layout.addWidget(Separator())

        description_layout = QVBoxLayout()
        description_layout.addWidget(BoldLabel("✏️ 설명"))
        self.description_text = QTextEdit()
        self.description_text.setFixedHeight(180)
        description_layout.addWidget(self.description_text)
        layout.addLayout(description_layout)

        # Road Map
        self.is_roadmap_cb = QCheckBox("⭐ 로드맵에 추가합니다.")
        self.is_roadmap_cb.setStyleSheet(tw("mt-5"))
        layout.addWidget(self.is_roadmap_cb)

        group_layout = QHBoxLayout()
        group_layout.setContentsMargins(0, 0, 0, 0)
        self.roadmap_group_combo = QComboBox()
        self.roadmap_group_combo.setEnabled(False)

        self.group_mgr_btn = StyledButton("⚙️", "transparent", "#777777", padding="2px")
        self.group_mgr_btn.setFixedSize(30, 30)
        self.group_mgr_btn.setToolTip("로드맵 그룹 추가/삭제")
        self.group_mgr_btn.setEnabled(False)
        self.group_mgr_btn.clicked.connect(self.open_group_manager)

        self.is_roadmap_cb.toggled.connect(self.roadmap_group_combo.setEnabled)
        self.is_roadmap_cb.toggled.connect(self.group_mgr_btn.setEnabled)
        group_layout.addWidget(self.roadmap_group_combo, stretch=1)
        group_layout.addWidget(self.group_mgr_btn)
        layout.addLayout(group_layout)
        self.refresh_groups()

        # Is Completed?
        self.is_completed_cb = QCheckBox("✅ 이 일정을 완료했습니다.")
        self.is_completed_cb.setStyleSheet(tw("my-8"))
        layout.addWidget(self.is_completed_cb)
        layout.addStretch()

        btn_layout = QHBoxLayout()
        self.save_btn = StyledButton("저장", COLORS["green-500"])
        self.cancel_btn = StyledButton("취소", "transparent", COLORS["c77"])
        self.save_btn.clicked.connect(self.save_event)
        self.cancel_btn.clicked.connect(self.reject)

        if self.schedule_data:
            self.delete_btn = StyledButton("삭제", COLORS["red-500"])
            self.delete_btn.clicked.connect(self.delete_event)
            btn_layout.addWidget(self.delete_btn)
            self.load_existing_data()

        btn_layout.addStretch()
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.save_btn)
        layout.addLayout(btn_layout)

    def update_repeat_ui(self):
        idx = self.repeat_combo.currentIndex()
        if idx == 0:
            # '반복 없음' -> 패널 숨기기
            self.description_text.setFixedHeight(180)
            self.repeat_detail_widget.setVisible(False)
            self.has_repeat_end_cb.setChecked(False)
            self.interval_spin.setValue(1)
        else:
            # 반복 선택됨 -> 패널 보이기 및 해당 페이지 전환
            self.description_text.setFixedHeight(80)
            self.repeat_detail_widget.setVisible(True)
            start_date = self.start_date.date()

            if idx == 1:  # 일
                self.interval_unit_label.setText("일 마다")
                self.repeat_stack.setCurrentIndex(0)
                self.repeat_end.setDate(start_date.addDays(1))

            elif idx == 2:  # 주
                self.interval_unit_label.setText("주 마다")
                self.repeat_stack.setCurrentIndex(1)
                self.repeat_end.setDate(start_date.addDays(7))

                target_dow = start_date.dayOfWeek() - 1
                for i, cb in enumerate(self.week_cbs):
                    cb.setChecked(i == target_dow)

            elif idx == 3:  # 월
                self.interval_unit_label.setText("개월 마다")
                self.repeat_stack.setCurrentIndex(2)
                self.repeat_end.setDate(start_date.addMonths(1))

                self.month_date_radio.setChecked(True)
                self.month_date_spin.setValue(start_date.day())

                target_dow = start_date.dayOfWeek() - 1
                nth_occurrence = (start_date.day() - 1) // 7

                self.month_nth_combo.setCurrentIndex(nth_occurrence)
                self.month_day_combo.setCurrentIndex(target_dow)

            elif idx == 4:  # 년
                self.interval_unit_label.setText("년 마다")
                self.repeat_stack.setCurrentIndex(3)
                self.repeat_end.setDate(start_date.addYears(1))

                self.year_month_spin.setValue(start_date.month())
                self.year_day_spin.setValue(start_date.day())

    def open_color_picker(self):
        current_hex = self.colors.get(self.color_combo.currentText(), COLORS["red-300"])
        color = QColorDialog.getColor(QColor(current_hex), self, "색상 선택")

        if color.isValid():
            hex_color = color.name().upper()
            if " 사용자 지정" not in self.colors:
                self.color_combo.addItem(" 사용자 지정")

            self.colors[" 사용자 지정"] = hex_color
            self.color_combo.setCurrentText(" 사용자 지정")
            self.update_color_preview()

    def save_custom_color(self):
        current_name = self.color_combo.currentText()
        current_hex = self.colors.get(current_name)

        if not current_hex:
            return

        text, ok = QInputDialog.getText(
            self,
            "색상 즐겨찾기",
            "새로운 색상의 이름을 입력하세요:\n(예: 중요 업무, 정기 회의 등)",
        )

        if ok and text:
            text = text.strip()
            if not text:
                QMessageBox.warning(self, "경고", "이름을 입력해야 합니다.")
                return
            if text in self.colors:
                QMessageBox.warning(
                    self, "경고", "이미 존재하는 이름입니다. 다른 이름을 사용해주세요."
                )
                return

            # 1. DB에 저장
            db_manager.add_custom_color(text, current_hex)

            # 2. 현재 딕셔너리에 추가
            self.colors[text] = current_hex

            # 3. 콤보박스에 아이템 추가
            pixmap = QPixmap(16, 16)
            pixmap.fill(QColor(current_hex))
            self.color_combo.addItem(QIcon(pixmap), text)

            # 4. 방금 추가한 색상으로 콤보박스 선택 변경
            self.color_combo.setCurrentText(text)

            QMessageBox.information(
                self, "저장 완료", f"'{text}' 색상이 즐겨찾기에 추가되었습니다!"
            )

    def delete_custom_color(self):
        current_name = self.color_combo.currentText()

        if current_name in DEFAULT_COLORS or current_name == " 사용자 지정":
            return

        reply = QMessageBox.question(
            self,
            "색상 삭제",
            f"'{current_name}' 색상을 정말 삭제하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            db_manager.delete_custom_color(current_name)

            if current_name in self.colors:
                del self.colors[current_name]

            current_index = self.color_combo.currentIndex()
            self.color_combo.removeItem(current_index)

            QMessageBox.information(self, "삭제 완료", "색상이 삭제되었습니다.")

    def refresh_groups(self, default_select_id=None):
        self.roadmap_group_combo.clear()
        self.roadmap_groups = db_manager.get_roadmap_groups()

        default_idx = 0
        for i, group in enumerate(self.roadmap_groups):
            self.roadmap_group_combo.addItem(group["name"], group["id"])
            if group["name"] == "미지정":
                default_idx = i

        if default_select_id:
            idx = self.roadmap_group_combo.findData(default_select_id)
            if idx >= 0:
                self.roadmap_group_combo.setCurrentIndex(idx)
            else:
                self.roadmap_group_combo.setCurrentIndex(default_idx)
        else:
            self.roadmap_group_combo.setCurrentIndex(default_idx)

    def open_group_manager(self):
        dialog = GroupManagerDialog(self)
        dialog.exec()

        current_id = self.roadmap_group_combo.currentData()
        self.refresh_groups(default_select_id=current_id)

    def update_color_preview(self):
        current_name = self.color_combo.currentText()
        selected_color = self.colors[current_name]
        self.color_preview.setStyleSheet(
            f"""
            background-color: {selected_color};
            {tw('border-b', 'border-cCC', 'rounded-10')}
            """
        )

        is_default = current_name in DEFAULT_COLORS
        is_temp_custom = current_name == " 사용자 지정"
        is_saved_custom = not is_default and not is_temp_custom

        self.add_color_label.setVisible(is_default)
        self.save_color_btn.setVisible(is_temp_custom)
        self.delete_color_btn.setVisible(is_saved_custom)

    def load_existing_data(self):
        self.title_input.setText(self.schedule_data["title"])

        # Period Section
        self.start_date.setDate(
            QDate.fromString(self.schedule_data["start_date"], "yyyy-MM-dd")
        )
        self.end_date.setDate(
            QDate.fromString(self.schedule_data["end_date"], "yyyy-MM-dd")
        )

        # Repeat Section
        rtype = self.schedule_data.get("repeat_type", "none")
        rtype_index_map = {
            "none": 0,
            "daily": 1,
            "weekly": 2,
            "monthly": 3,
            "yearly": 4,
        }
        self.repeat_combo.setCurrentIndex(rtype_index_map.get(rtype, 0))

        rule_str = self.schedule_data.get("repeat_rule", "")
        if rule_str:
            try:
                rule = json.loads(rule_str)
                self.interval_spin.setValue(rule.get("interval", 1))
                self.weekday_only_cb.setChecked(rule.get("weekday_only", False))

                if rtype == "weekly":
                    days = rule.get("days", [])
                    for i, cb in enumerate(self.week_cbs):
                        cb.setChecked(i in days)

                elif rtype == "monthly":
                    if rule.get("mode") == "date":
                        self.month_date_radio.setChecked(True)
                        self.month_date_spin.setValue(rule.get("date", 1))
                    else:
                        self.month_nth_radio.setChecked(True)
                        nth = rule.get("nth", 1)
                        # DB에서 -1은 마지막 주를 의미하므로 콤보박스 인덱스 4로 매핑
                        self.month_nth_combo.setCurrentIndex(nth - 1 if nth > 0 else 4)
                        self.month_day_combo.setCurrentIndex(rule.get("day", 0))

                elif rtype == "yearly":
                    self.year_month_spin.setValue(rule.get("month", 1))
                    self.year_day_spin.setValue(rule.get("date", 1))
            except json.JSONDecodeError:
                pass

        repeat_end_str = self.schedule_data.get("repeat_end", "")
        if repeat_end_str:
            self.has_repeat_end_cb.setChecked(True)
            self.repeat_end.setDate(QDate.fromString(repeat_end_str, "yyyy-MM-dd"))
        else:
            self.has_repeat_end_cb.setChecked(False)

        # Color Pick Section
        saved_color = self.schedule_data.get("color", "").upper()
        self.color_matched = False

        for key, val in self.colors.items():
            if val.upper() == saved_color:
                self.color_combo.setCurrentText(key)
                self.color_matched = True
                break

        if not self.color_matched and saved_color:
            self.colors[" 사용자 지정"] = saved_color

            pixmap = QPixmap(16, 16)
            pixmap.fill(QColor(saved_color))
            self.color_combo.addItem(QIcon(pixmap), " 사용자 지정")
            self.color_combo.setCurrentText(" 사용자 지정")

        self.update_color_preview()

        # Description
        self.description_text.setPlainText(self.schedule_data.get("description", ""))

        # Road Map Data
        is_roadmap = self.schedule_data.get("is_roadmap", False)
        self.is_roadmap_cb.setChecked(is_roadmap)

        group_id = self.schedule_data.get("group_id")
        if is_roadmap and group_id:
            index = self.roadmap_group_combo.findData(group_id)
            if index >= 0:
                self.roadmap_group_combo.setCurrentIndex(index)

        # Complete Check
        self.is_completed_cb.setChecked(self.schedule_data.get("is_completed", False))

    def save_event(self):
        title = self.title_input.text().strip()

        if not title:
            QMessageBox.warning(self, "오류", "일정 이름을 입력하세요.")
            return

        start_date = self.start_date.date()
        end_date = self.end_date.date()
        if start_date > end_date:
            QMessageBox.warning(self, "오류", "시작일이 종료일보다 이전이어야 합니다.")
            return

        start_str = start_date.toString("yyyy-MM-dd")
        end_str = end_date.toString("yyyy-MM-dd")

        rtype_map = {0: "none", 1: "daily", 2: "weekly", 3: "monthly", 4: "yearly"}
        rtype = rtype_map[self.repeat_combo.currentIndex()]
        repeat_end_date = self.repeat_end.date()
        repeat_end_str = ""
        repeat_rule_str = ""

        if rtype != "none":
            # 종료일 검사
            if self.has_repeat_end_cb.isChecked():
                repeat_end_date = self.repeat_end.date()
                if start_date > repeat_end_date:
                    QMessageBox.warning(
                        self, "오류", "반복 종료일이 일정 시작일보다 빠를 수 없습니다."
                    )
                    return
                repeat_end_str = repeat_end_date.toString("yyyy-MM-dd")

            # JSON 딕셔너리 만들기
            rule = {
                "interval": self.interval_spin.value(),
                "weekday_only": self.weekday_only_cb.isChecked(),
            }

            if rtype == "weekly":
                # 체크된 요일의 인덱스(0:월 ~ 6:일)만 리스트로 수집
                rule["days"] = [
                    i for i, cb in enumerate(self.week_cbs) if cb.isChecked()
                ]
                if not rule["days"]:
                    QMessageBox.warning(
                        self, "오류", "반복할 요일을 하나 이상 선택해주세요."
                    )
                    return

            elif rtype == "monthly":
                if self.month_date_radio.isChecked():
                    rule["mode"] = "date"
                    rule["date"] = self.month_date_spin.value()
                else:
                    rule["mode"] = "nth_day"
                    nth_idx = self.month_nth_combo.currentIndex()
                    # 0~3은 1~4번째, 4는 마지막 주로 규정하므로 -1을 줍니다.
                    rule["nth"] = nth_idx + 1 if nth_idx < 4 else -1
                    rule["day"] = self.month_day_combo.currentIndex()

            elif rtype == "yearly":
                rule["month"] = self.year_month_spin.value()
                rule["date"] = self.year_day_spin.value()

            # 딕셔너리를 문자열로 변환!
            repeat_rule_str = json.dumps(rule, ensure_ascii=False)

        color_hex = self.colors[self.color_combo.currentText()]
        description = self.description_text.toPlainText()
        is_completed = self.is_completed_cb.isChecked()
        is_roadmap = self.is_roadmap_cb.isChecked()
        group_id = self.roadmap_group_combo.currentData() if is_roadmap else None

        if self.schedule_data:
            db_manager.update_schedule(
                self.schedule_data["id"],
                title,
                start_str,
                end_str,
                rtype,
                repeat_rule_str,
                repeat_end_str,
                color_hex,
                description,
                is_completed,
                is_roadmap,
                group_id,
            )
        else:
            db_manager.add_schedule(
                title,
                start_str,
                end_str,
                rtype,
                repeat_rule_str,
                repeat_end_str,
                color_hex,
                description,
                is_completed,
                is_roadmap,
                group_id,
            )
        global_signals.schedule_updated.emit()
        self.accept()

    def delete_event(self):
        db_manager.delete_schedule(self.schedule_data["id"])
        global_signals.schedule_updated.emit()
        self.accept()
