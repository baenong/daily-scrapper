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
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from datetime import datetime, timezone

from core import news_scraper, db_manager
from core.worker import run_async
from core.tw_utils import COLORS, tw, tw_sheet
from core.signals import global_signals
from ui.components import (
    TitleLabel,
    DescriptionLabel,
    StyledButton,
    EditableRowWidget,
    ArticleItemWidget,
)

ROLE_URL = Qt.ItemDataRole.UserRole + 1
ROLE_FILTER = Qt.ItemDataRole.UserRole + 2


class NewsTab(QWidget):
    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.is_loaded = False
        self.setup_ui()
        global_signals.font_size_changed.connect(self.update_list_item_sizes)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)
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
        is_and_checked = self.settings.get("news_cond_and", True)

        self.radio_and.setChecked(is_and_checked)
        self.radio_or.setChecked(not is_and_checked)
        self.radio_and.setFixedWidth(75)
        self.radio_or.setFixedWidth(75)

        self.radio_and.toggled.connect(self.change_news_condition)

        btn_group = QButtonGroup(self)
        btn_group.addButton(self.radio_and)
        btn_group.addButton(self.radio_or)

        limit_label = QLabel("추출 : ")
        limit_label.setFixedWidth(35)

        self.news_limit = QSpinBox()
        self.news_limit.setRange(1, 50)
        self.news_limit.setValue(self.settings.get("news_limit", 30))
        self.news_limit.valueChanged.connect(self.change_news_limit)
        self.news_limit.setFixedWidth(80)

        self.search_btn = StyledButton("🔍 검색  ", COLORS["green-500"])
        self.search_btn.clicked.connect(self.search_news)

        cond_layout.addWidget(self.radio_and)
        cond_layout.addWidget(self.radio_or)
        cond_layout.addWidget(limit_label)
        cond_layout.addWidget(self.news_limit)
        cond_layout.addWidget(QLabel(""), stretch=1)
        cond_layout.addWidget(self.search_btn)
        left_layout.addLayout(cond_layout)

        add_btn = StyledButton("➕ 뉴스 키워드 추가", COLORS["c33"])
        add_btn.clicked.connect(lambda: self.add_keyword_row("", True))
        left_layout.addWidget(add_btn)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.keyword_list_widget = QWidget()
        self.keyword_list_layout = QVBoxLayout(self.keyword_list_widget)
        self.keyword_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
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
        self.news_filter_input.setStyleSheet(tw("p-5", "rounded"))
        self.news_filter_input.textChanged.connect(self.filter_news_list)

        filter_layout.addWidget(self.news_filter_input)
        right_layout.addLayout(filter_layout)

        # 검색 결과
        self.news_list_view = QListWidget()
        self.news_list_view.setStyleSheet(tw_sheet({"QListWidget::item": "p-2"}))
        self.news_list_view.itemDoubleClicked.connect(self.open_news_link)
        right_layout.addWidget(self.news_list_view)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)

        splitter.setSizes([400, 1200])

    def change_news_condition(self, checked):
        self.settings["news_cond_and"] = checked

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
        self.news_list_view.clear()
        self.news_filter_input.clear()

        for i in range(self.keyword_list_layout.count()):
            item = self.keyword_list_layout.itemAt(i).widget()
            if isinstance(item, EditableRowWidget) and item.checkbox.isChecked():
                raw_text = item.line_edit.text()
                words = [w.strip() for w in raw_text.split(",") if w.strip()]
                if words:
                    selected_groups.append(" ".join(words))

        if not selected_groups:
            self.news_list_view.addItem("⚠️ 검색할 키워드를 추가하거나 체크해주세요.")
            return

        is_and_cond = self.radio_and.isChecked()
        self.search_btn.setEnabled(False)
        self.search_btn.setText("⏳ 검색 중...")
        self.news_list_view.addItem(
            "⏳ 구글 뉴스를 검색 중입니다. 잠시만 기다려주세요..."
        )

        run_async(
            self._fetch_news_in_background,
            self._on_news_loaded,
            self._on_news_error,
            selected_groups,
            is_and_cond,
            self.news_limit.value(),
        )

    def _fetch_news_in_background(self, selected_groups, is_and_cond, limit):
        if is_and_cond:
            final_query = " ".join(selected_groups)
            return news_scraper.get_news_by_query(final_query, limit=limit)
        else:
            return news_scraper.get_news_by_or_query(selected_groups, limit=limit)

    def _on_news_loaded(self, news_items):
        """뉴스 로드가 완료되면 UI에 뿌려줍니다."""
        self.search_btn.setEnabled(True)
        self.search_btn.setText("🔍 검색")
        self.news_list_view.clear()

        if not news_items:
            self.news_list_view.addItem("⚠️ 검색 결과가 없습니다.")
            return

        now = datetime.now(timezone.utc)
        for news in news_items:
            item = QListWidgetItem(self.news_list_view)
            item.setData(ROLE_URL, news["link"])

            filter_text = f"{news['title']} {news['source']}".lower()
            item.setData(ROLE_FILTER, filter_text)

            custom_widget = ArticleItemWidget(
                news["title"], news["source"], news["published_str"], "📰"
            )

            try:
                delta = now - news["published_dt"]
                if delta.days <= 3:
                    custom_widget.set_highligt("bg-blue-500-30")

            except TypeError:
                pass

            item.setSizeHint(custom_widget.sizeHint())
            self.news_list_view.setItemWidget(item, custom_widget)

    def _on_news_error(self, error_msg):
        self.news_list_view.clear()
        self.search_btn.setEnabled(True)
        self.news_list_view.addItem("❌ 뉴스 검색 중 오류가 발생했습니다.")
        print(f"뉴스 로딩 에러: {error_msg}")

    def filter_news_list(self):
        keyword = self.news_filter_input.text().strip().lower()

        for i in range(self.news_list_view.count()):
            item = self.news_list_view.item(i)
            item_text = item.data(ROLE_FILTER)

            if item_text is None:
                continue

            if item_text and keyword in item_text:
                item.setHidden(False)
            else:
                item.setHidden(True)

    def update_list_item_sizes(self):
        if not hasattr(self, "news_list_view") or self.news_list_view.count() == 0:
            return

        for i in range(self.news_list_view.count()):
            item = self.news_list_view.item(i)
            widget = self.news_list_view.itemWidget(item)

            if widget:
                new_size = widget.sizeHint()
                item.setSizeHint(new_size)

    def change_news_limit(self):
        self.settings["news_limit"] = self.news_limit.value()

    def open_news_link(self, item):
        url = item.data(ROLE_URL)
        if url:
            QDesktopServices.openUrl(QUrl(url))
