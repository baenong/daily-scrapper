from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QScrollArea,
    QRadioButton,
    QButtonGroup,
    QLabel,
    QSpinBox,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QColor, QDesktopServices
from datetime import datetime, timezone

from core import data_manager, news_scraper, db_manager
from ui.components import TitleLabel, DescriptionLabel, StyledButton, EditableRowWidget


class NewsTab(QWidget):
    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.setup_ui()
        self.search_news()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        # --- [왼쪽: 키워드 설정 영역] ---
        left_widget = QWidget()
        left_widget.setMinimumWidth(200)
        left_layout = QVBoxLayout(left_widget)

        left_layout.addWidget(TitleLabel("📌 검색할 키워드 목록"))
        left_layout.addWidget(
            DescriptionLabel("제외할 키워드는 -를 앞에 붙이면 됩니다.")
        )

        cond_layout = QHBoxLayout()
        cond_layout.setContentsMargins(0, 0, 0, 0)
        cond_layout.setSpacing(5)

        self.radio_and = QRadioButton("AND")
        self.radio_or = QRadioButton("OR")
        self.radio_and.setChecked(True)
        self.radio_and.setFixedWidth(55)
        self.radio_or.setFixedWidth(55)

        btn_group = QButtonGroup(self)
        btn_group.addButton(self.radio_and)
        btn_group.addButton(self.radio_or)

        limit_label = QLabel("추출 : ")
        limit_label.setFixedWidth(35)

        self.news_limit = QSpinBox()
        self.news_limit.setRange(1, 50)
        self.news_limit.setValue(self.settings.get("news_limit", 15))
        self.news_limit.valueChanged.connect(self.change_news_limit)
        self.news_limit.setFixedWidth(60)

        search_btn = StyledButton("검색", "#4CAF50")
        search_btn.clicked.connect(self.search_news)

        cond_layout.addWidget(self.radio_and)
        cond_layout.addWidget(self.radio_or)
        cond_layout.addWidget(limit_label)
        cond_layout.addWidget(self.news_limit)
        cond_layout.addWidget(search_btn)
        left_layout.addLayout(cond_layout)

        add_btn = QPushButton("➕ 뉴스 키워드 추가")
        add_btn.clicked.connect(lambda: self.add_keyword_row("", True))
        left_layout.addWidget(add_btn)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.keyword_list_widget = QWidget()
        self.keyword_list_layout = QVBoxLayout(self.keyword_list_widget)
        self.keyword_list_layout.setAlignment(Qt.AlignTop)
        scroll.setWidget(self.keyword_list_widget)
        left_layout.addWidget(scroll)

        for kw_data in db_manager.load_news_keywords():
            self.add_keyword_row(kw_data.get("text", ""), kw_data.get("checked", True))

        # --- [오른쪽: 뉴스 결과 영역] ---
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        right_layout.addWidget(TitleLabel("스크랩 결과"))
        right_layout.addWidget(
            DescriptionLabel(
                "30일 이내 뉴스 기사를 최신순으로 정렬하고 최근 3일 내 기사는 강조합니다."
            )
        )

        # 결과 필터링
        filter_layout = QHBoxLayout()
        self.news_filter_input = QLineEdit()
        self.news_filter_input.setPlaceholderText("🔍 결과 내 검색 (제목, 언론사 등)")
        self.news_filter_input.setStyleSheet("padding: 5px; border-radius: 4px;")
        self.news_filter_input.textChanged.connect(self.filter_news_list)

        filter_layout.addWidget(self.news_filter_input)
        right_layout.addLayout(filter_layout)

        # 검색 결과
        self.news_list_view = QListWidget()
        self.news_list_view.itemDoubleClicked.connect(self.open_news_link)
        right_layout.addWidget(self.news_list_view)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)

        splitter.setSizes([400, 864])

    def add_keyword_row(self, text, is_checked):
        row = EditableRowWidget(text, is_checked, self.save_keywords_to_db)
        self.keyword_list_layout.addWidget(row)
        if not text:
            row.enable_edit()

    def save_keywords_to_db(self):
        """변경된 키워드를 DB에 저장합니다."""
        keywords = []
        for i in range(self.keyword_list_layout.count()):
            item = self.keyword_list_layout.itemAt(i).widget()
            if isinstance(item, EditableRowWidget):
                text = item.line_edit.text().strip()
                is_checked = item.checkbox.isChecked()
                if text:
                    keywords.append({"text": text, "checked": is_checked})

        db_manager.save_news_keywords(keywords)

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
            return

        final_query = ""
        if self.radio_and.isChecked():
            final_query = " ".join(selected_groups)
        else:
            or_parts = [f"({g})" for g in selected_groups]
            final_query = " OR ".join(or_parts)

        self.news_list_view.clear()
        self.news_filter_input.clear()

        try:
            news_items = news_scraper.get_news_by_query(
                final_query, limit=self.news_limit.value()
            )
            if not news_items:
                self.news_list_view.addItem("검색 결과가 없습니다.")
                return

            now = datetime.now(timezone.utc)
            for news in news_items:
                display_text = (
                    f"📰 {news['title']}\n{news['source']} 🗓️ {news['published_str']}"
                )
                item = QListWidgetItem(display_text)
                item.setData(100, news["link"])

                delta = now - news["published_dt"]
                if delta.days <= 3:
                    item.setBackground(QColor(255, 0, 0, 30))

                self.news_list_view.addItem(item)
        except Exception as e:
            return

    def filter_news_list(self):
        keyword = self.news_filter_input.text().strip().lower()
        for i in range(self.news_list_view.count()):
            item = self.news_list_view.item(i)
            item_text = item.text().lower()
            if keyword in item_text:
                item.setHidden(False)
            else:
                item.setHidden(True)

    def change_news_limit(self):
        self.settings["news_limit"] = self.news_limit.value()

    def open_news_link(self, item):
        url = item.data(100)
        if url:
            QDesktopServices.openUrl(QUrl(url))
