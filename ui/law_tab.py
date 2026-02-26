from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QScrollArea,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QColor, QBrush, QDesktopServices
from datetime import datetime

from ui.components import TitleLabel, DescriptionLabel, StyledButton, EditableRowWidget
from core import data_manager, law_scraper


class LawTab(QWidget):
    """법령 정보 조회 탭 위젯입니다."""

    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.setup_ui()
        self.refresh_laws()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Horizontal)
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
        self.law_refresh_btn = StyledButton("선택 법령 정보 조회", "#4CAF50")
        self.law_refresh_btn.clicked.connect(self.refresh_laws)

        control_layout.addStretch()
        control_layout.addWidget(self.law_refresh_btn)
        left_layout.addLayout(control_layout)

        add_law_btn = QPushButton("➕ 법령 키워드 추가")
        add_law_btn.clicked.connect(lambda: self.add_law_row("", True))
        left_layout.addWidget(add_law_btn)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.law_list_widget = QWidget()
        self.law_list_layout = QVBoxLayout(self.law_list_widget)
        self.law_list_layout.setAlignment(Qt.AlignTop)
        scroll.setWidget(self.law_list_widget)
        left_layout.addWidget(scroll)

        for law_data in self.settings.get("laws", []):
            if isinstance(law_data, dict):
                self.add_law_row(
                    law_data.get("text", ""), law_data.get("checked", True)
                )
            else:
                self.add_law_row(law_data, True)

        # --- [오른쪽: 법령 조회 결과] ---
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        right_layout.addWidget(TitleLabel("법령 목록"))
        right_layout.addWidget(
            DescriptionLabel("현행 및 시행 예정 법령을 일자순으로 정렬합니다.")
        )

        self.law_table = QTableWidget()
        self.law_table.setColumnCount(2)
        self.law_table.setHorizontalHeaderLabels(["법령명", "시행(예정)일자"])
        self.law_table.setStyleSheet("QTableWidget::item { padding: 10px; }")
        self.law_table.verticalHeader().setDefaultSectionSize(35)

        header = self.law_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)

        self.law_table.itemDoubleClicked.connect(self.open_law_link)
        right_layout.addWidget(self.law_table)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([400, 864])

    def add_law_row(self, text, is_checked):
        row = EditableRowWidget(text, is_checked, self.save_laws_to_settings)
        self.law_list_layout.addWidget(row)
        if not text:
            row.enable_edit()

    def save_laws_to_settings(self):
        laws = []
        for i in range(self.law_list_layout.count()):
            item = self.law_list_layout.itemAt(i).widget()
            if isinstance(item, EditableRowWidget):
                text = item.line_edit.text().strip()
                is_checked = item.checkbox.isChecked()
                if text:
                    laws.append({"text": text, "checked": is_checked})
        self.settings["laws"] = laws
        data_manager.save_settings(self.settings)

    def refresh_laws(self):
        self.law_table.setRowCount(0)
        all_law_infos = []
        law_keys = set()

        for i in range(self.law_list_layout.count()):
            item = self.law_list_layout.itemAt(i).widget()
            if isinstance(item, EditableRowWidget) and item.checkbox.isChecked():
                law_name = item.line_edit.text().strip()
                if not law_name:
                    continue

                infos = law_scraper.get_law_group_info(law_name)
                if infos:
                    for info in infos:
                        unique_key = info.get("serial")
                        if unique_key not in law_keys:
                            law_keys.add(unique_key)
                            all_law_infos.append(info)

        all_law_infos.sort(key=lambda x: x["enforce_date"], reverse=True)
        today_str = datetime.now().strftime("%Y.%m.%d")

        future_color = QColor(255, 0, 0, 30)
        now_color = QColor(255, 0, 0)

        for info in all_law_infos:
            row = self.law_table.rowCount()
            self.law_table.insertRow(row)

            name_item = QTableWidgetItem(info["name"])
            date_item = QTableWidgetItem(info["enforce_date"])

            date_item.setTextAlignment(Qt.AlignCenter)
            name_item.setData(Qt.UserRole, info["link"])

            enforce_date = info["enforce_date"]

            if enforce_date > today_str and enforce_date != "정보 없음":
                name_item.setBackground(QBrush(future_color))
                date_item.setBackground(QBrush(future_color))
                name_item.setText(f"🚀 [시행예정] {info['name']}")

            if enforce_date == today_str and enforce_date != "정보 없음":
                name_item.setBackground(QBrush(now_color))
                date_item.setBackground(QBrush(now_color))
                name_item.setText(f"🚨 [오늘시행] {info['name']}")

            self.law_table.setItem(row, 0, name_item)
            self.law_table.setItem(row, 1, date_item)

    def open_law_link(self, item):
        row = item.row()
        name_item = self.law_table.item(row, 0)
        url = name_item.data(Qt.UserRole)
        if url:
            QDesktopServices.openUrl(QUrl(url))
