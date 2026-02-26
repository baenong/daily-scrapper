from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QCalendarWidget,
    QLabel,
    QLineEdit,
    QScrollArea,
    QCheckBox,
    QMessageBox,
)
from PySide6.QtCore import Qt, QDate, QRect
from PySide6.QtGui import QColor, QBrush

from ui.components import TitleLabel, DescriptionLabel, StyledButton
from core import db_manager


class TodoCalendar(QCalendarWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.todo_status = {}

    def set_todo_status(self, status_dict):
        """DB에서 계산된 날짜별 완료 상태 딕셔너리를 받아와 달력을 갱신합니다."""
        self.todo_status = status_dict
        self.updateCells()

    def paintCell(self, painter, rect, date):
        super().paintCell(painter, rect, date)

        date_str = date.toString("yyyy-MM-dd")
        if date_str in self.todo_status:
            is_all_completed = self.todo_status[date_str]

            painter.save()
            painter.setPen(Qt.NoPen)

            if is_all_completed:
                painter.setBrush(QBrush(QColor("#BDBDBD")))  # 완료: 연한 회색
            else:
                painter.setBrush(QBrush(QColor("#2196F3")))  # 미완료: 강조 파란색

            dot_size = 6
            x = rect.center().x() - (dot_size / 2)
            y = rect.bottom() - 10

            painter.drawEllipse(QRect(int(x), int(y), int(dot_size), int(dot_size)))
            painter.restore()


class TodoRowWidget(QWidget):
    """개별 할 일(Todo) 항목을 표시하는 커스텀 위젯입니다."""

    def __init__(
        self, todo_id, content, is_completed, toggle_callback, delete_callback
    ):
        super().__init__()
        self.todo_id = todo_id
        self.toggle_callback = toggle_callback
        self.delete_callback = delete_callback

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.checkbox = QCheckBox(content)
        self.checkbox.setChecked(is_completed)
        font = self.checkbox.font()
        font.setPointSize(11)

        # 완료된 항목은 취소선을 그어줍니다.
        font.setStrikeOut(is_completed)
        self.checkbox.setFont(font)

        # 체크박스 상태가 변할 때 이벤트 연결
        self.checkbox.toggled.connect(self.on_toggled)

        self.btn_del = StyledButton("❌", "transparent", "#F44336")
        self.btn_del.setFixedWidth(40)
        self.btn_del.clicked.connect(lambda: self.delete_callback(self.todo_id))

        layout.addWidget(self.checkbox, stretch=1)
        layout.addWidget(self.btn_del)

    def on_toggled(self, checked):
        font = self.checkbox.font()
        font.setStrikeOut(checked)
        self.checkbox.setFont(font)
        self.toggle_callback(self.todo_id, checked)


class ScheduleTab(QWidget):
    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.current_date_str = QDate.currentDate().toString("yyyy-MM-dd")

        self.setup_ui()
        self.load_todos()
        self.refresh_calendar_dots()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        # --- [왼쪽: Todo 영역] ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        self.date_title = TitleLabel(f"📌 {self.current_date_str} 일정")
        left_layout.addWidget(self.date_title)
        left_layout.addWidget(DescriptionLabel("날짜를 선택한 후 할 일을 입력하세요"))

        # 일정 추가 입력창 및 버튼
        input_layout = QHBoxLayout()
        self.todo_input = QLineEdit()
        self.todo_input.setPlaceholderText("새로운 할 일을 입력하고 엔터를 누르세요.")
        self.todo_input.setStyleSheet("padding: 8px; font-size: 14px;")
        self.todo_input.returnPressed.connect(self.add_todo)  # 엔터키 지원

        add_btn = StyledButton("일정 추가", "#2196F3")
        add_btn.setFixedWidth(80)
        add_btn.clicked.connect(self.add_todo)

        input_layout.addWidget(self.todo_input)
        input_layout.addWidget(add_btn)
        left_layout.addLayout(input_layout)

        # 일정 목록이 표시될 스크롤 영역
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.todo_list_widget = QWidget()
        self.todo_list_layout = QVBoxLayout(self.todo_list_widget)
        self.todo_list_layout.setAlignment(Qt.AlignTop)
        scroll.setWidget(self.todo_list_widget)

        left_layout.addWidget(scroll)

        # --- [오른쪽: Calendar 영역] ---
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        right_layout.addWidget(TitleLabel("📅 날짜 선택"))
        right_layout.addWidget(DescriptionLabel("일정을 확인할 날짜를 선택해 주세요."))

        self.calendar = TodoCalendar()
        self.calendar.setGridVisible(True)
        self.calendar.setMinimumHeight(600)
        self.calendar.setMinimumWidth(350)

        self.calendar.setStyleSheet(
            """
            /* 1. 상단 네비게이션 바(연/월 텍스트 영역) 전체 높이 조절 */
            QWidget#qt_calendar_navigationbar {
                background-color: #F5F5F5;
                min-height: 40px;
                border-bottom: 1px solid #E0E0E0;
            }
            
            /* 2. 상단 헤더 안에 있는 버튼들(연/월, 이전/다음 화살표) 글자 크기 조절 */
            QToolButton {
                font-size: 16px;
                font-weight: bold;
                color: #131313;
                padding: 5px;
            }
            
            QToolButton:hover {
                background-color: #777777;
                border-radius: 4px;
            }
            
            QTableView {
                selection-background-color: rgba(33, 150, 243, 0.2); 
                selection-color: #cccccc;
            }
        """
        )
        self.calendar.clicked.connect(self.on_date_changed)

        right_layout.addWidget(self.calendar)
        right_layout.addStretch()

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([400, 864])  # 달력이 있으므로 왼쪽 비율을 조금 더 줍니다.

    def on_date_changed(self, qdate):
        """달력에서 날짜를 클릭했을 때 실행됩니다."""
        self.current_date_str = qdate.toString("yyyy-MM-dd")
        self.date_title.setText(f"📌 {self.current_date_str} 일정")
        self.load_todos()

    def refresh_calendar_dots(self):
        """DB를 뒤져서 일정이 1개라도 있는 날짜들의 목록을 뽑아 달력에 전달합니다."""
        all_todos = db_manager.get_todos()
        status_dict = {}

        for todo in all_todos:
            date_str = todo["date"]
            is_completed = todo["is_completed"]

            # 처음 발견된 날짜면 일단 "모두 완료(True)"라고 가정합니다.
            if date_str not in status_dict:
                status_dict[date_str] = True

            # 해당 날짜의 일정 중 하나라도 미완료(False)가 발견되면, 전체 상태를 미완료(False)로 바꿉니다!
            if not is_completed:
                status_dict[date_str] = False

        self.calendar.set_todo_status(status_dict)

    def load_todos(self):
        """선택된 날짜의 일정을 DB에서 불러와 화면에 그려줍니다."""
        for i in reversed(range(self.todo_list_layout.count())):
            widget = self.todo_list_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()

        todos = db_manager.get_todos(self.current_date_str)

        if not todos:
            empty_label = QLabel("등록된 일정이 없습니다.")
            empty_label.setStyleSheet("color: #999999; padding: 10px;")
            self.todo_list_layout.addWidget(empty_label)
            return

        for todo in todos:
            row = TodoRowWidget(
                todo_id=todo["id"],
                content=todo["content"],
                is_completed=todo["is_completed"],
                toggle_callback=self.toggle_todo,
                delete_callback=self.delete_todo,
            )
            self.todo_list_layout.addWidget(row)

    def add_todo(self):
        """입력창의 텍스트를 DB에 저장하고 목록을 새로고침합니다."""
        content = self.todo_input.text().strip()
        if not content:
            return

        db_manager.add_todo(self.current_date_str, content)
        self.todo_input.clear()
        self.load_todos()
        self.refresh_calendar_dots()

    def toggle_todo(self, todo_id, is_completed):
        """체크박스를 누르면 DB의 완료 상태를 업데이트합니다."""
        db_manager.update_todo_status(todo_id, is_completed)
        self.refresh_calendar_dots()

    def delete_todo(self, todo_id):
        """X 버튼을 누르면 DB에서 삭제하고 목록을 새로고침합니다."""
        reply = QMessageBox.question(
            self,
            "확인",
            "일정을 삭제하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            db_manager.delete_todo(todo_id)
            self.load_todos()
            self.refresh_calendar_dots()
