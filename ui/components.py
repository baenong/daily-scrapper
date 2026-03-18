import webbrowser
from PySide6.QtWidgets import (
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
    QCheckBox,
    QComboBox,
    QToolTip,
    QMessageBox,
)
from PySide6.QtGui import (
    QColor,
    QPixmap,
    QIcon,
    QMouseEvent,
    QEnterEvent,
    QContextMenuEvent,
)
from PySide6.QtCore import Qt, Signal, QTimer, QDate, QPoint
from core import db_manager
from core.signals import global_signals
from core.style import DEFAULT_COLORS, COLORS, tw, tw_sheet


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
            final_text_color = text_color if text_color else "black"

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

                final_text_color = COLORS["black-13"] if luminance > 150 else "#FFFFFF"
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
                height: 20px;
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
    def __init__(self, text, size=18):
        super().__init__(text)
        self.setStyleSheet(
            f"font-weight: bold; font-size: {size}px; margin-right: 5px;"
        )


class DescriptionLabel(QLabel):
    def __init__(self, text):
        super().__init__(text)
        self.setStyleSheet("color: #777777; margin-bottom: 10px;")


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

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 8, 5, 8)
        layout.setSpacing(8)

        self.title_label = QLabel(f"{icon} {title}")
        self.title_label.setStyleSheet("font-size: 14px;")

        self.meta_label = QLabel(f"[{source}]  🗓️ {pub_date}")
        self.meta_label.setStyleSheet("font-size: 13px; color: #777777;")

        layout.addWidget(self.title_label)
        layout.addWidget(self.meta_label)


class ClickableColorLabel(QLabel):
    clicked = Signal()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


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
            if self.schedule_data.get("is_law"):
                webbrowser.open(self.schedule_data.get("link", ""))
            else:
                self.doubleClicked.emit(self.schedule_data)
            event.accept()

    def contextMenuEvent(self, event: QContextMenuEvent):
        """우클릭 시 실행되는 컨텍스트 메뉴입니다."""
        menu = QMenu(self)
        menu.setStyleSheet(
            tw_sheet(
                {
                    "QMenu": "bg-white p-5 border-b border-cCC text-13 text-black no-underline",
                    "QMenu::item": "py-6 px-10 no-underline",
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
            self.statusToggled.emit(self.schedule_data)
        elif action == action_edit:
            self.editRequested.emit(self.schedule_data)
        elif action == action_delete:
            self.deleteRequested.emit(self.schedule_data)


class Separator(QLabel):
    def __init__(self, text=""):
        super().__init__(text)
        self.setStyleSheet(tw("border-bb", "border-c33", "text-1", "mb-5", "pt-5"))


class CustomDateEdit(QDateEdit):
    def __init__(self, date_str):
        super().__init__(date_str)
        self.setCalendarPopup(True)
        self.setDisplayFormat("yy.MM.dd (ddd)")
        self.setFixedWidth(125)


class GroupManagerDialog(QDialog):
    """로드맵 그룹을 추가/삭제하는 관리 팝업입니다."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("로드맵 그룹 관리")
        self.setFixedSize(300, 400)

        layout = QVBoxLayout(self)

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        input_layout = QHBoxLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("새 그룹 이름")
        self.add_btn = StyledButton("추가", COLORS["green-500"])
        self.add_btn.clicked.connect(self.add_group)

        input_layout.addWidget(self.name_input)
        input_layout.addWidget(self.add_btn)
        layout.addLayout(input_layout)

        self.del_btn = StyledButton("선택 그룹 삭제", COLORS["red-500 "])
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
        self.setFixedSize(400, 620)
        self.schedule_data = schedule_data

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 25, 20, 15)

        title_layout = QHBoxLayout()
        title_layout.addWidget(TitleLabel("📌 이름", 14))

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("일정 이름을 입력해주세요")
        title_layout.addWidget(self.title_input, stretch=1)

        layout.addLayout(title_layout)
        layout.addWidget(Separator())

        date_layout = QHBoxLayout()
        date_layout.addWidget(TitleLabel("📅 기간", 14))
        self.start_date = CustomDateEdit(QDate.fromString(date_str, "yyyy. MM. dd"))
        date_layout.addWidget(self.start_date)
        date_layout.addWidget(QLabel("  ~ "))
        self.end_date = CustomDateEdit(QDate.fromString(date_str, "yyyy. MM. dd"))
        date_layout.addWidget(self.end_date)

        layout.addLayout(date_layout)
        layout.addWidget(Separator())

        repeat_layout = QHBoxLayout()
        repeat_layout.addWidget(TitleLabel("🔁 반복", 14))

        self.repeat_combo = QComboBox()
        self.repeat_combo.addItems(["반복 없음", "매일", "매주", "매월"])
        self.repeat_combo.setFixedWidth(100)
        repeat_layout.addWidget(self.repeat_combo)
        repeat_layout.addStretch()

        repeat_layout.addWidget(QLabel("종료:"))
        self.repeat_end = CustomDateEdit(QDate.currentDate())
        self.repeat_end.setEnabled(False)
        self.repeat_combo.currentIndexChanged.connect(self.update_repeat_end)
        repeat_layout.addWidget(self.repeat_end)
        layout.addLayout(repeat_layout)
        layout.addWidget(Separator())

        # Color Section
        color_layout = QHBoxLayout()
        color_layout.addWidget(TitleLabel("🎨 색상", 14))

        # 미리 지정된 색 말고도 색을 선택할 수 있도록
        self.color_preview = ClickableColorLabel()
        self.color_preview.setFixedSize(20, 20)
        self.color_preview.setCursor(Qt.CursorShape.PointingHandCursor)
        self.color_preview.setToolTip("클릭하여 다른 색상을 선택하세요")
        self.color_preview.clicked.connect(self.open_color_picker)
        color_layout.addWidget(self.color_preview)
        color_layout.addWidget(QLabel("← 커스텀 색상 선택"))
        color_layout.addStretch()

        self.color_combo = QComboBox()
        self.color_combo.setMinimumWidth(125)
        self.colors = DEFAULT_COLORS

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
        description_layout.addWidget(TitleLabel("✏️ 설명", 14))
        self.description_text = QTextEdit()
        description_layout.addWidget(self.description_text)
        layout.addLayout(description_layout)

        # Road Map
        self.is_roadmap_cb = QCheckBox("⭐ 로드맵에 추가합니다.")
        self.is_roadmap_cb.setStyleSheet(tw("mr-10"))
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
        self.is_completed_cb.setStyleSheet(tw("mt-5"))
        layout.addWidget(self.is_completed_cb)
        layout.addStretch()

        btn_layout = QHBoxLayout()
        self.save_btn = StyledButton("저장", COLORS["green-500"])
        self.cancel_btn = StyledButton("취소", "transparent", "#555555")
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

    def update_repeat_end(self):
        current_date = self.repeat_end.date()
        selected_rtype = self.repeat_combo.currentText()

        if selected_rtype == "매일":
            self.repeat_end.setDate(current_date.addDays(1))
        elif selected_rtype == "매월":
            self.repeat_end.setDate(current_date.addMonths(1))
        elif selected_rtype == "매년":
            self.repeat_end.setDate(current_date.addYears(1))
        else:
            self.repeat_end.setDate(current_date)

        self.repeat_end.setEnabled(self.repeat_combo.currentIndex() != 0)

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
        selected_color = self.colors[self.color_combo.currentText()]
        self.color_preview.setStyleSheet(
            f"background-color: {selected_color}; border-radius: 10px; {tw("border-b", "border-cCC")}"
        )

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

        rtype_map = {0: "none", 1: "daily", 2: "weekly", 3: "monthly"}
        rtype = rtype_map[self.repeat_combo.currentIndex()]
        repeat_end_date = self.repeat_end.date()
        repeat_end_str = ""

        if rtype != "none":
            today = QDate().currentDate()
            if today > repeat_end_date:
                QMessageBox.warning(self, "오류", "반복 종료일이 이미 지났습니다.")
                return

            repeat_end_str = repeat_end_date.toString("yyyy-MM-dd")

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
