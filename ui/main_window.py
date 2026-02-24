from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QLabel,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QSplitter,
    QScrollArea,
    QLineEdit,
    QCheckBox,
    QRadioButton,
    QButtonGroup,
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QColor, QBrush
from datetime import datetime, timezone

# core 폴더의 모듈들을 불러옵니다.
from core import data_manager
from core import news_scraper
from core import law_scraper


class StyledButton(QPushButton):
    """배경색과 글자색을 인자로 받아 예쁜 CSS 버튼을 만들어주는 클래스입니다."""

    def __init__(self, text, bg_color, text_color="white"):
        super().__init__(text)
        self.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {bg_color};
                color: {text_color};
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
            }}
            QPushButton:hover {{
                background-color: {bg_color}CC;
            }}
            QPushButton:pressed {{
                background-color: {bg_color}99;
            }}
        """
        )


class EditableRowWidget(QWidget):
    """뉴스 키워드와 법령 목록 모두에서 재사용 가능한 체크박스+편집 위젯입니다."""

    def __init__(self, text, is_checked, save_callback):
        super().__init__()
        self.save_callback = save_callback

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.checkbox = QCheckBox()
        self.checkbox.setChecked(is_checked)

        self.line_edit = QLineEdit(text)
        self.line_edit.setReadOnly(True)

        # 앞서 만든 커스텀 버튼 활용 (파란색 편집, 초록색 저장, 투명배경 빨간글씨 삭제)
        self.btn_edit = StyledButton("편집", "#2196F3")
        self.btn_save = StyledButton("저장", "#4CAF50")
        self.btn_save.hide()
        self.btn_del = StyledButton("❌", "transparent", "#F44336")

        layout.addWidget(self.checkbox)
        layout.addWidget(self.line_edit, stretch=1)
        layout.addWidget(self.btn_edit)
        layout.addWidget(self.btn_save)
        layout.addWidget(self.btn_del)

        self.btn_edit.clicked.connect(self.enable_edit)
        self.btn_save.clicked.connect(self.save_edit)
        self.btn_del.clicked.connect(self.delete_row)

    def enable_edit(self):
        self.line_edit.setReadOnly(False)
        # 🚨 흰 배경일 때 글씨가 검은색으로 보이도록 강제 지정
        self.line_edit.setStyleSheet("background-color: white; color: black;")
        self.line_edit.setFocus()
        self.btn_edit.hide()
        self.btn_save.show()

    def save_edit(self):
        self.line_edit.setReadOnly(True)
        self.line_edit.setStyleSheet("")  # 원래 테마로 복구
        self.btn_save.hide()
        self.btn_edit.show()
        self.save_callback()  # 연결된 저장 함수 실행

    def delete_row(self):
        self.setParent(None)
        self.deleteLater()
        self.save_callback()


class DailyScraper(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("시청 업무 보조 프로그램 v1.0")
        self.resize(1264, 800)

        # 설정 데이터 불러오기
        self.settings = data_manager.load_settings()

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # 탭 구성
        self.setup_news_tab()
        self.setup_law_tab()

        self.search_news()
        self.refresh_laws()

    def setup_news_tab(self):
        news_tab = QWidget()
        layout = QVBoxLayout(news_tab)
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        # --- [왼쪽: 키워드 설정 영역] ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.addWidget(QLabel("📌 검색할 키워드 목록"))

        cond_layout = QHBoxLayout()
        self.radio_and = QRadioButton("AND")
        self.radio_or = QRadioButton("OR")
        self.radio_and.setChecked(True)

        btn_group = QButtonGroup(self)
        btn_group.addButton(self.radio_and)
        btn_group.addButton(self.radio_or)

        search_btn = StyledButton("📰 뉴스 검색", "#4CAF50")
        search_btn.clicked.connect(self.search_news)

        cond_layout.addWidget(self.radio_and)
        cond_layout.addWidget(self.radio_or)
        cond_layout.addWidget(search_btn)
        left_layout.addLayout(cond_layout)

        # 키워드 추가 버튼
        add_btn = QPushButton("➕ 새 키워드 추가 (쉼표로 구분)")
        add_btn.clicked.connect(lambda: self.add_keyword_row("", True))
        left_layout.addWidget(add_btn)

        # 스크롤 가능한 키워드 목록 영역
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.keyword_list_widget = QWidget()
        self.keyword_list_layout = QVBoxLayout(self.keyword_list_widget)
        self.keyword_list_layout.setAlignment(Qt.AlignTop)
        scroll.setWidget(self.keyword_list_widget)
        left_layout.addWidget(scroll)

        for kw_data in self.settings.get("keywords", []):
            if isinstance(kw_data, dict):
                self.add_keyword_row(
                    kw_data.get("text", ""), kw_data.get("checked", True)
                )
            else:
                self.add_keyword_row(kw_data, True)

        # --- [오른쪽: 뉴스 결과 영역] ---
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        self.news_list_view = QListWidget()
        self.news_list_view.itemDoubleClicked.connect(self.open_news_link)
        right_layout.addWidget(self.news_list_view)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        # splitter.setStretchFactor(0, 1)
        # splitter.setStretchFactor(1, 2)
        splitter.setSizes([250, 550])

        self.tabs.addTab(news_tab, "뉴스 스크랩")

    def add_keyword_row(self, text, is_checked):
        row = EditableRowWidget(text, is_checked, self.save_keywords_to_settings)
        self.keyword_list_layout.addWidget(row)
        if not text:  # 새 항목 추가 시 바로 편집 모드로
            row.enable_edit()

    def save_keywords_to_settings(self):
        keywords = []
        for i in range(self.keyword_list_layout.count()):
            item = self.keyword_list_layout.itemAt(i).widget()
            if isinstance(item, EditableRowWidget):
                text = item.line_edit.text().strip()
                is_checked = item.checkbox.isChecked()
                if text:
                    keywords.append({"text": text, "checked": is_checked})
        self.settings["keywords"] = keywords
        data_manager.save_settings(self.settings)

    def search_news(self):
        selected_groups = []
        for i in range(self.keyword_list_layout.count()):
            item = self.keyword_list_layout.itemAt(i).widget()
            if isinstance(item, EditableRowWidget) and item.checkbox.isChecked():
                raw_text = item.line_edit.text()
                words = [w.strip() for w in raw_text.split(",") if w.strip()]
                if words:
                    group_query = " ".join(words)
                    selected_groups.append(group_query)

        if not selected_groups:
            QMessageBox.information(self, "알림", "검색할 키워드 묶음을 체크해 주세요.")
            return

        final_query = ""
        if self.radio_and.isChecked():
            final_query = " ".join(selected_groups)
        else:
            or_parts = [f"({g})" for g in selected_groups]
            final_query = " OR ".join(or_parts)

        self.news_list_view.clear()
        try:
            news_items = news_scraper.get_news_by_query(final_query, limit=30)
            if not news_items:
                self.news_list_view.addItem("검색 결과가 없습니다.")
                return

            now = datetime.now(timezone.utc)

            for news in news_items:
                display_text = f"📰 {news['title']}\n🗓️ {news['published_str']}"
                item = QListWidgetItem(display_text)
                item.setData(100, news["link"])

                delta = now - news["published_dt"]
                if delta.days <= 7:
                    item.setBackground(QColor(255, 0, 0, 30))

                self.news_list_view.addItem(item)
        except Exception as e:
            QMessageBox.warning(
                self, "오류", f"뉴스를 검색하는 중 오류가 발생했습니다:\n{e}"
            )

    def open_news_link(self, item):
        url = item.data(100)
        if url:
            QDesktopServices.openUrl(QUrl(url))

    # 법령 탭
    def setup_law_tab(self):
        law_tab = QWidget()
        layout = QVBoxLayout(law_tab)
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        # --- 왼쪽: 법령 목록 관리 ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.addWidget(QLabel("📌 조회할 법령 목록"))

        add_law_btn = QPushButton("➕ 새 법령 추가")
        add_law_btn.clicked.connect(lambda: self.add_law_row(""))
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

        # --- 오른쪽: 법령 조회 결과 ---
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        control_layout = QHBoxLayout()
        self.law_refresh_btn = StyledButton("🔄 선택 법령 정보 조회", "#2196F3")
        self.law_refresh_btn.clicked.connect(self.refresh_laws)

        control_layout.addStretch()
        control_layout.addWidget(self.law_refresh_btn)
        right_layout.addLayout(control_layout)

        self.law_table = QTableWidget()
        self.law_table.setColumnCount(2)
        self.law_table.setHorizontalHeaderLabels(["법령명", "시행일자"])

        self.law_table.setStyleSheet(
            """
            QTableWidget::item {
                padding: 10px; 
            }
        """
        )
        self.law_table.verticalHeader().setDefaultSectionSize(35)

        header = self.law_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)

        self.law_table.itemDoubleClicked.connect(self.open_law_link)
        right_layout.addWidget(self.law_table)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        # splitter.setStretchFactor(0, 1)
        # splitter.setStretchFactor(1, 2)
        splitter.setSizes([250, 550])

        self.tabs.addTab(law_tab, "법령 개정 알림")

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

        for i in range(self.law_list_layout.count()):
            item = self.law_list_layout.itemAt(i).widget()
            if isinstance(item, EditableRowWidget) and item.checkbox.isChecked():
                law_name = item.line_edit.text().strip()
                if not law_name:
                    continue

                infos = law_scraper.get_law_group_info(law_name)
                if infos:
                    all_law_infos.extend(infos)

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
                name_item.setText(f"💥 [오늘시행] {info['name']}")

            self.law_table.setItem(row, 0, name_item)
            self.law_table.setItem(row, 1, date_item)

    def open_law_link(self, item):
        row = item.row()
        name_item = self.law_table.item(row, 0)
        url = name_item.data(Qt.UserRole)

        if url:
            QDesktopServices.openUrl(QUrl(url))
