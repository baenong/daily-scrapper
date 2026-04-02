from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QColor, QDesktopServices
from datetime import datetime

from ui.components import TitleLabel, DescriptionLabel, StyledButton, EditableRowWidget
from core import law_scraper, db_manager
from core.tw_utils import COLORS, BASIC_SIZE
from core.signals import global_signals
from core.worker import run_async


class LawTab(QWidget):
    """법령 정보 조회 탭 위젯입니다."""

    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.is_loaded = False
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # --- [왼쪽: 법령 목록 관리] ---
        left_widget = QWidget()
        left_widget.setMinimumWidth(200)
        left_layout = QVBoxLayout(left_widget)

        left_layout.addWidget(TitleLabel("📌 조회할 법령 목록"))
        left_layout.addWidget(
            DescriptionLabel("법령 이름을 입력하면 시행령, 시행규칙도 조회됩니다.")
        )

        control_layout = QHBoxLayout()
        self.law_refresh_btn = StyledButton("🔍 법령 정보 조회 ", COLORS["green-500"])
        self.law_refresh_btn.clicked.connect(self.refresh_laws)

        control_layout.addStretch()
        control_layout.addWidget(self.law_refresh_btn)
        left_layout.addLayout(control_layout)

        add_law_btn = StyledButton("➕ 법령 키워드 추가", COLORS["c33"])
        add_law_btn.clicked.connect(lambda: self.add_law_row("", True))
        left_layout.addWidget(add_law_btn)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.law_list_widget = QWidget()
        self.law_list_layout = QVBoxLayout(self.law_list_widget)
        self.law_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self.law_list_widget)
        left_layout.addWidget(scroll)

        # Load DB data
        for law_data in db_manager.load_law_keywords():
            self.add_law_row(law_data.get("text", ""), law_data.get("checked", True))

        # --- [오른쪽: 법령 조회 결과] ---
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        right_layout.addWidget(TitleLabel("법령 목록"))
        right_layout.addWidget(
            DescriptionLabel("현행 및 시행 예정 법령을 일자순으로 정렬합니다.")
        )

        self.law_table = QTableWidget()
        self.law_table.setColumnCount(2)
        self.law_table.setHorizontalHeaderLabels(["법령명", "시행(예정)일"])

        header = self.law_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)

        self.law_table.itemDoubleClicked.connect(self.open_law_link)
        right_layout.addWidget(self.law_table)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([400, 1200])

        self.update_table_layout()
        global_signals.font_size_changed.connect(self.update_table_layout)

    def add_law_row(self, text, is_checked):
        row = EditableRowWidget(text, is_checked, self.save_laws_to_db)
        self.law_list_layout.addWidget(row)
        if not text:
            row.enable_edit()

    def save_laws_to_db(self):
        laws = []
        for i in range(self.law_list_layout.count()):
            item = self.law_list_layout.itemAt(i).widget()
            if isinstance(item, EditableRowWidget):
                text = item.line_edit.text().strip()
                is_checked = item.checkbox.isChecked()
                if text:
                    laws.append({"text": text, "checked": is_checked})

        db_manager.save_law_keywords(laws)
        global_signals.law_keyword_updated.emit()

    def refresh_laws(self):
        self.law_table.setRowCount(0)
        law_names = []
        for i in range(self.law_list_layout.count()):
            item = self.law_list_layout.itemAt(i).widget()
            if isinstance(item, EditableRowWidget) and item.checkbox.isChecked():
                law_name = item.line_edit.text().strip()
                if law_name:
                    law_names.append(law_name)

        if not law_names:
            return

        self.law_refresh_btn.setEnabled(False)
        self.law_refresh_btn.setText("⏳ 법령 정보 조회 중...")

        # 백그라운드 작업 시작
        run_async(
            self._fetch_laws_in_background,
            self._on_laws_loaded,
            self._on_laws_error,
            law_names,
        )

    def _fetch_laws_in_background(self, law_names):
        raw_infos = law_scraper.get_laws_by_keywords(law_names)

        all_law_infos = []
        law_keys = set()

        for info in raw_infos:
            unique_key = info.get("serial")
            if unique_key not in law_keys:
                law_keys.add(unique_key)
                all_law_infos.append(info)

        all_law_infos.sort(
            key=lambda x: (
                x["enforce_date"] if x["enforce_date"] != "정보 없음" else "0000.00.00"
            ),
            reverse=True,
        )
        return all_law_infos

    def _on_laws_loaded(self, all_law_infos):
        self.law_refresh_btn.setEnabled(True)
        self.law_refresh_btn.setText("🔍 법령 정보 조회")
        self.law_table.setRowCount(0)

        today_str = datetime.now().strftime("%Y.%m.%d")
        future_color = QColor(255, 0, 0, 30)
        now_color = QColor(255, 0, 0, 80)

        for info in all_law_infos:
            row = self.law_table.rowCount()
            self.law_table.insertRow(row)

            name_item = QTableWidgetItem(info["name"])
            date_item = QTableWidgetItem(info["enforce_date"])

            date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            name_item.setData(Qt.ItemDataRole.UserRole, info["link"])

            enforce_date = info["enforce_date"]

            if enforce_date != "정보 없음":
                if enforce_date > today_str:
                    name_item.setBackground(future_color)
                    date_item.setBackground(future_color)
                    name_item.setText(f"🚀 [시행예정] {info['name']}")

                if enforce_date == today_str:
                    name_item.setBackground(now_color)
                    date_item.setBackground(now_color)
                    name_item.setText(f"🚨 [오늘시행] {info['name']}")

            self.law_table.setItem(row, 0, name_item)
            self.law_table.setItem(row, 1, date_item)

    def _on_laws_error(self, error_msg):
        self.law_refresh_btn.setEnabled(True)
        self.law_refresh_btn.setText("🔍 법령 정보 조회")
        print(f"법령 로딩 에러: {error_msg}")

    def open_law_link(self, item):
        row = item.row()
        name_item = self.law_table.item(row, 0)
        url = name_item.data(Qt.ItemDataRole.UserRole)
        if url:
            QDesktopServices.openUrl(QUrl(url))

    def update_table_layout(self):

        app: QApplication = QApplication.instance()
        global_font = app.font()

        self.law_table.setFont(global_font)
        self.law_table.horizontalHeader().setFont(global_font)
        self.law_table.verticalHeader().setFont(global_font)

        current_font_size = global_font.pixelSize()
        if current_font_size <= 0:
            current_font_size = BASIC_SIZE

        new_row_height = int(current_font_size * 2.5)
        self.law_table.verticalHeader().setDefaultSectionSize(new_row_height)
