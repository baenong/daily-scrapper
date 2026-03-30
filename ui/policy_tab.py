from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QScrollArea,
    QListWidget,
    QListWidgetItem,
    QCheckBox,
    QLineEdit,
    QComboBox,
)
from PySide6.QtCore import Qt, QUrl, QThreadPool
from PySide6.QtGui import QDesktopServices
from datetime import datetime, timezone

from core import db_manager, policy_scraper
from core.worker import AsyncTask, run_async
from core.tw_utils import COLORS, tw, tw_sheet
from ui.components import TitleLabel, DescriptionLabel, StyledButton, ArticleItemWidget

ROLE_LINK = Qt.ItemDataRole.UserRole + 1
ROLE_TITLE_FILTER = Qt.ItemDataRole.UserRole + 2
ROLE_SOURCE_FILTER = Qt.ItemDataRole.UserRole + 3


class PolicyTab(QWidget):
    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.is_loaded = False
        self.departments = db_manager.load_departments()
        self.department_checkboxes = []
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # --- [왼쪽: 부처 선택 영역] ---
        left_widget = QWidget()
        left_widget.setMinimumWidth(200)
        left_layout = QVBoxLayout(left_widget)

        left_layout.addWidget(TitleLabel("🏛️ 조회할 부처 선택"))
        left_layout.addWidget(
            DescriptionLabel("선택된 부처의 최신 정책브리핑을 모아봅니다.")
        )

        # 컨트롤 영역 (조회 버튼)
        control_layout = QHBoxLayout()
        self.search_btn = StyledButton("🔍 정책 브리핑 조회", COLORS["green-500"])
        self.search_btn.clicked.connect(self.search_policy)
        control_layout.addStretch()
        control_layout.addWidget(self.search_btn)
        left_layout.addLayout(control_layout)

        # 부처 목록 스크롤 영역
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.dept_list_widget = QWidget()
        self.dept_list_layout = QVBoxLayout(self.dept_list_widget)
        self.dept_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self.dept_list_widget)
        left_layout.addWidget(scroll)

        # DB에서 부처 목록 불러와서 체크박스 생성
        self.load_department_checkboxes()

        # --- [오른쪽: 정책브리핑 결과 영역] ---
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        right_layout.addWidget(TitleLabel("브리핑 결과"))
        right_layout.addWidget(
            DescriptionLabel("최근 발표된 정책브리핑을 최신순으로 정렬합니다.")
        )

        filter_layout = QHBoxLayout()

        self.dept_combo = QComboBox()
        self.dept_combo.setMinimumWidth(120)
        self.dept_combo.currentTextChanged.connect(self.filter_policy_list)

        self.policy_filter_input = QLineEdit()
        self.policy_filter_input.setPlaceholderText("🔍 결과 내 검색 (제목 등)")
        self.policy_filter_input.setStyleSheet(tw("p-5", "rounded"))
        self.policy_filter_input.textChanged.connect(self.filter_policy_list)

        filter_layout.addWidget(self.dept_combo)
        filter_layout.addWidget(self.policy_filter_input)
        right_layout.addLayout(filter_layout)

        self.policy_list_view = QListWidget()
        self.policy_list_view.setStyleSheet(tw_sheet({"QListWidget::item": "p-2"}))
        self.policy_list_view.itemDoubleClicked.connect(self.open_link)
        right_layout.addWidget(self.policy_list_view)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([400, 1200])

    def load_department_checkboxes(self):
        for dept in self.departments:
            cb = QCheckBox(dept["name"])
            cb.setChecked(dept["checked"])

            cb.toggled.connect(
                lambda checked, d_id=dept["id"]: db_manager.update_department_status(
                    d_id, checked
                )
            )

            cb.setProperty("rss_url", dept["rss_url"])

            self.dept_list_layout.addWidget(cb)
            self.department_checkboxes.append(cb)

    def search_policy(self):
        selected_urls = []
        selected_names = []

        for cb in self.department_checkboxes:
            if cb.isChecked():
                selected_urls.append(cb.property("rss_url"))
                selected_names.append(cb.text())

        self.dept_combo.blockSignals(True)
        self.dept_combo.clear()
        self.dept_combo.addItem("전체")
        self.dept_combo.addItems(selected_names)
        self.dept_combo.blockSignals(False)

        self.policy_list_view.clear()

        if not selected_urls:
            self.policy_list_view.addItem("선택된 부처가 없습니다.")
            return

        self.search_btn.setEnabled(False)
        self.search_btn.setText("⏳ 조회 중...")
        self.policy_list_view.addItem(
            "⏳ 선택한 부처들의 정책브리핑을 모아오고 있습니다..."
        )

        # 2. 비동기 백그라운드 호출
        run_async(
            self._fetch_policy_in_background,
            self._on_policy_loaded,
            self._on_policy_error,
            selected_urls,
        )
        # worker = AsyncTask(self._fetch_policy_in_background, selected_urls)
        # worker.signals.result_ready.connect(self._on_policy_loaded)
        # worker.signals.error_occurred.connect(self._on_policy_error)

        # QThreadPool.globalInstance().start(worker)

    def _fetch_policy_in_background(self, rss_urls):
        return policy_scraper.get_policy_briefings(rss_urls, limit=50)

    def _on_policy_loaded(self, policy_items):
        self.search_btn.setEnabled(True)
        self.search_btn.setText("🔍 정책 브리핑 조회")
        self.policy_list_view.clear()

        if not policy_items:
            self.policy_list_view.addItem("조회된 브리핑이 없습니다.")
            return

        now = datetime.now(timezone.utc)
        for policy in policy_items:
            item = QListWidgetItem(self.policy_list_view)
            item.setData(ROLE_LINK, policy["link"])

            filter_title_text = policy["title"].lower()
            filter_source_text = policy["source"].lower()
            item.setData(ROLE_TITLE_FILTER, filter_title_text)
            item.setData(ROLE_SOURCE_FILTER, filter_source_text)

            custom_widget = ArticleItemWidget(
                policy["title"], policy["source"], policy["published_str"], "📢"
            )

            try:
                delta = now - policy["published_dt"]
                if delta.days <= 2:
                    custom_widget.set_highligt("bg-blue-500-30")
            except TypeError:
                pass

            item.setSizeHint(custom_widget.sizeHint())
            self.policy_list_view.setItemWidget(item, custom_widget)

    def _on_policy_error(self, error_msg):
        self.search_btn.setEnabled(True)
        self.search_btn.setText("🔍 정책 브리핑 조회")
        self.policy_list_view.clear()
        self.policy_list_view.addItem("❌ 브리핑 조회 중 오류가 발생했습니다.")
        print(f"정책브리핑 로딩 에러: {error_msg}")

    def filter_policy_list(self):
        filter_dept = self.dept_combo.currentText()
        if filter_dept == "전체":
            filter_dept = ""
        else:
            filter_dept = filter_dept.lower()

        keyword = self.policy_filter_input.text().strip().lower()

        for i in range(self.policy_list_view.count()):
            item = self.policy_list_view.item(i)
            item_text = item.data(ROLE_TITLE_FILTER)
            item_source = item.data(ROLE_SOURCE_FILTER)

            if item_text is None or item_source is None:
                continue

            if (filter_dept in item_source) and (keyword in item_text):
                item.setHidden(False)
            else:
                item.setHidden(True)

    def open_link(self, item):
        url = item.data(ROLE_LINK)
        if url:
            QDesktopServices.openUrl(QUrl(url))
