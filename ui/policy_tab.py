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
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QColor, QDesktopServices
from datetime import datetime, timezone

from core import db_manager, policy_scraper
from core.worker import AsyncTask
from ui.components import TitleLabel, DescriptionLabel, StyledButton


class PolicyTab(QWidget):
    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.department_checkboxes = []  # 체크박스 객체 보관용
        self.setup_ui()
        self.search_policy()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Horizontal)
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
        self.search_btn = StyledButton("선택 부처 브리핑 조회", "#4CAF50")
        self.search_btn.clicked.connect(self.search_policy)
        control_layout.addStretch()
        control_layout.addWidget(self.search_btn)
        left_layout.addLayout(control_layout)

        # 부처 목록 스크롤 영역
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.dept_list_widget = QWidget()
        self.dept_list_layout = QVBoxLayout(self.dept_list_widget)
        self.dept_list_layout.setAlignment(Qt.AlignTop)
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
        self.policy_filter_input = QLineEdit()
        self.policy_filter_input.setPlaceholderText("🔍 결과 내 검색 (제목 등)")
        self.policy_filter_input.setStyleSheet("padding: 5px; border-radius: 4px;")
        self.policy_filter_input.textChanged.connect(self.filter_policy_list)

        filter_layout.addWidget(self.policy_filter_input)
        right_layout.addLayout(filter_layout)

        self.policy_list_view = QListWidget()
        self.policy_list_view.itemDoubleClicked.connect(self.open_link)
        right_layout.addWidget(self.policy_list_view)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([400, 1200])

    def load_department_checkboxes(self):
        departments = db_manager.load_departments()
        for dept in departments:
            cb = QCheckBox(dept["name"])
            cb.setChecked(dept["checked"])
            # 체크박스 상태 변경 시 즉시 DB에 저장
            cb.toggled.connect(
                lambda checked, d_id=dept["id"]: db_manager.update_department_status(
                    d_id, checked
                )
            )

            # 나중에 파싱을 위해 객체에 url 정보를 몰래 담아둡니다
            cb.setProperty("rss_url", dept["rss_url"])

            self.dept_list_layout.addWidget(cb)
            self.department_checkboxes.append(cb)

    def search_policy(self):
        # 1. 체크된 부처의 RSS URL들만 수집
        selected_urls = [
            cb.property("rss_url")
            for cb in self.department_checkboxes
            if cb.isChecked()
        ]

        self.policy_list_view.clear()

        if not selected_urls:
            self.policy_list_view.addItem("선택된 부처가 없습니다.")
            return

        self.search_btn.setEnabled(False)
        self.search_btn.setText("⏳ 조회 중...")
        self.policy_list_view.addItem(
            "⏳ 선택한 부처들의 정책브리핑을 모아오고 있습니다..."
        )

        # 2. 🚀 비동기 백그라운드 호출
        self.worker = AsyncTask(self._fetch_policy_in_background, selected_urls)
        self.worker.result_ready.connect(self._on_policy_loaded)
        self.worker.error_occurred.connect(self._on_policy_error)
        self.worker.start()

    def _fetch_policy_in_background(self, rss_urls):
        return policy_scraper.get_policy_briefings(rss_urls, limit=50)

    def _on_policy_loaded(self, entries):
        self.search_btn.setEnabled(True)
        self.search_btn.setText("선택 부처 브리핑 조회")
        self.policy_list_view.clear()

        if not entries:
            self.policy_list_view.addItem("조회된 브리핑이 없습니다.")
            return

        now = datetime.now(timezone.utc)
        for entry in entries:
            display_text = (
                f"📢 {entry['title']}\n[{entry['source']}] 🗓️ {entry['published_str']}"
            )
            item = QListWidgetItem(display_text)
            item.setData(100, entry["link"])

            try:
                delta = now - entry["published_dt"]
                if delta.days <= 2:  # 2일 이내의 매우 최신 브리핑은 배경색 강조
                    item.setBackground(QColor(33, 150, 243, 30))  # 연한 파란색
            except TypeError:
                pass

            self.policy_list_view.addItem(item)

    def _on_policy_error(self, error_msg):
        self.search_btn.setEnabled(True)
        self.search_btn.setText("선택 부처 브리핑 조회")
        self.policy_list_view.clear()
        self.policy_list_view.addItem("❌ 브리핑 조회 중 오류가 발생했습니다.")
        print(f"정책브리핑 로딩 에러: {error_msg}")

    def filter_policy_list(self):
        keyword = self.policy_filter_input.text().strip().lower()
        for i in range(self.policy_list_view.count()):
            item = self.policy_list_view.item(i)
            item_text = item.text().lower()
            if keyword in item_text:
                item.setHidden(False)
            else:
                item.setHidden(True)

    def open_link(self, item):
        url = item.data(100)
        if url:
            QDesktopServices.openUrl(QUrl(url))
