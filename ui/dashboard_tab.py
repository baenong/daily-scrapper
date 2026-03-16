from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QListWidget,
    QListWidgetItem,
    QFrame,
    QSizePolicy,
    QLabel,
    QHBoxLayout,
)
from PySide6.QtCore import Qt, QDate
from datetime import datetime

# 공통 부품 및 코어 모듈 불러오기
from ui.components import TitleLabel, StyledButton
from ui.schedule_tab import get_instances
from core import db_manager, news_scraper, law_scraper, policy_scraper
from core.worker import AsyncTask


class EllipsisLabel(QLabel):
    """영역을 벗어나면 자동으로 말줄임표(...) 처리를 해주는 라벨입니다."""

    def __init__(self, text):
        super().__init__()
        self._original_text = text
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setStyleSheet("background: transparent; border: none;")

    def resizeEvent(self, event):
        """위젯의 가로 크기가 변할 때마다 실행되어 글자를 알맞게 자릅니다."""
        metrics = self.fontMetrics()
        elided_text = metrics.elidedText(
            self._original_text, Qt.TextElideMode.ElideRight, self.width() - 5
        )

        super().setText(elided_text)
        super().resizeEvent(event)


class DashboardCard(QFrame):
    """대시보드에 들어갈 개별 정보 카드 위젯입니다."""

    def __init__(self, title, btn_text, btn_callback):
        super().__init__()
        # 카드 느낌을 내기 위해 테두리와 배경색을 살짝 줍니다.
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            """
            DashboardCard {
                background-color: rgba(128, 128, 128, 0.05); 
                border-radius: 12px; 
                border: 1px solid rgba(128, 128, 128, 0.2);
            }
        """
        )

        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(25, 25, 25, 25)

        # 타이틀
        self.title_label = TitleLabel(title)
        layout.addWidget(self.title_label)

        # 리스트 (정보가 표시될 영역)
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(
            """
            QListWidget {
                border: none;
                background: transparent;
            }
            QListWidget::item {
                padding: 4px 0; /* 항목 위아래 간격을 넓혀서 시원하게 */
                border-bottom: 1px solid rgba(0, 0, 0, 0.05); /* 항목 사이에 옅은 구분선 추가 */}
            """
        )
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.list_widget.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        layout.addWidget(self.list_widget)

        self.detail_btn = StyledButton(btn_text, "#333333", "#2196F3")
        self.detail_btn.setFixedHeight(40)
        self.detail_btn.clicked.connect(btn_callback)
        layout.addWidget(self.detail_btn)

    def add_item(self, text, use_ellipsis=False):
        item = QListWidgetItem(self.list_widget)

        if use_ellipsis:
            label = EllipsisLabel(text)
            self.list_widget.setItemWidget(item, label)
        else:
            item.setText(text)


class DashboardTab(QWidget):
    """오늘의 일정, 뉴스, 법령을 한눈에 보여주는 첫 화면 탭입니다."""

    def __init__(self, settings, go_to_tab_callback):
        super().__init__()
        self.settings = settings
        self.go_to_tab = go_to_tab_callback

        self.setup_ui()
        self.load_dashboard_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)

        welcome_label = TitleLabel(
            f"👋 환영합니다! 오늘({QDate.currentDate().toString('yyyy.MM.dd')})의 주요 현황을 확인하세요."
        )
        welcome_label.setStyleSheet(
            "font-size: 20px; font-weight: bold; margin-bottom: 20px;"
        )
        layout.addStretch(1)
        layout.addWidget(welcome_label)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(15)

        self.todo_card = DashboardCard(
            "📅 오늘의 일정", "일정 탭으로 이동 ➔", lambda: self.go_to_tab(4)
        )

        self.news_card = DashboardCard(
            "📰 최신 관심 뉴스", "뉴스 탭으로 이동 ➔", lambda: self.go_to_tab(1)
        )

        self.policy_card = DashboardCard(
            "🏛️ 최신 정책 브리핑", "브리핑 탭으로 이동 →", lambda: self.go_to_tab(3)
        )

        self.law_card = DashboardCard(
            "🚨 오늘 시행 법령", "법령 탭으로 이동 ➔", lambda: self.go_to_tab(2)
        )

        cards_layout.addWidget(self.todo_card)
        cards_layout.addWidget(self.news_card)
        cards_layout.addWidget(self.policy_card)
        cards_layout.addWidget(self.law_card)

        layout.addLayout(cards_layout)
        layout.addStretch(1)

    def load_dashboard_data(self):
        """데이터 로딩을 시작하고 UI를 로딩 상태로 변경합니다."""
        self.todo_card.list_widget.clear()
        self.news_card.list_widget.clear()
        self.policy_card.list_widget.clear()
        self.law_card.list_widget.clear()

        self.todo_card.add_item("⏳ 데이터 불러오는 중...")
        self.news_card.add_item("⏳ 데이터 불러오는 중...")
        self.policy_card.add_item("⏳ 데이터 불러오는 중...")
        self.law_card.add_item("⏳ 데이터 불러오는 중...")

        # 백그라운드 스레드 생성 및 실행
        self.worker = AsyncTask(self._fetch_data_in_background, parent=self)
        self.worker.result_ready.connect(self._on_data_loaded)
        self.worker.error_occurred.connect(self._on_data_error)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.start()

    def _fetch_data_in_background(self):
        """이 함수는 UI를 건드리지 않고 오직 데이터만 수집하여 딕셔너리로 반환합니다."""
        result = {"todos": [], "news": [], "policy": [], "laws": []}

        today_dt = datetime.now()
        today_qdate = QDate.currentDate()
        today_str_law = today_dt.strftime("%Y.%m.%d")

        # 1. 일정 데이터 수집
        all_schedules = db_manager.get_schedules()
        for s in all_schedules:
            if get_instances(s, today_qdate, today_qdate):
                result["todos"].append(s)
        result["todos"].sort(key=lambda x: x.get("is_completed", False))

        # 2. 뉴스 데이터 수집
        db_news_kws = db_manager.load_news_keywords()

        selected_groups = []
        for kw in db_news_kws:
            if kw.get("checked", True):
                words = [w.strip() for w in kw["text"].split(",") if w.strip()]
                if words:
                    selected_groups.append(" ".join(words))

        if selected_groups:
            is_and_cond = self.settings.get("news_cond_and", True)

            if is_and_cond:
                final_query = " ".join(selected_groups)
            else:
                or_parts = [f"({g})" for g in selected_groups]
                final_query = " OR ".join(or_parts)

            try:
                result["news"] = news_scraper.get_news_by_query(final_query, limit=5)
            except Exception:
                pass

        # 3. 정책 브리핑 데이터 수집
        db_policy_kws = db_manager.load_departments()
        rss_urls = [kw["rss_url"] for kw in db_policy_kws if kw.get("checked", True)]

        if rss_urls:
            try:
                result["policy"] = policy_scraper.get_policy_briefings(
                    rss_urls, limit=5
                )
            except Exception:
                pass

        # 4. 법령 데이터 수집
        db_law_kws = db_manager.load_law_keywords()
        law_keywords = [law["text"] for law in db_law_kws if law.get("checked", True)]
        if law_keywords:
            today_laws = []
            for law_name in law_keywords:
                infos = law_scraper.get_law_group_info(law_name)
                if infos:
                    for info in infos:
                        if info["enforce_date"] == today_str_law:
                            today_laws.append(info["name"])
            result["laws"] = list(set(today_laws))

        return result

    def _on_data_loaded(self, data):
        """백그라운드 작업이 끝나면 신호를 받아 UI를 업데이트합니다."""
        # 1. 일정 업데이트
        self.todo_card.list_widget.clear()
        if not data["todos"]:
            self.todo_card.add_item("❌ 오늘 등록된 일정이 없습니다.")
        else:
            for t in data["todos"][:5]:
                is_comp = t.get("is_completed", False)
                prefix = "✅ " if is_comp else "✏️ "
                item = QListWidgetItem(prefix + t["title"])
                if is_comp:
                    item.setForeground(Qt.GlobalColor.gray)
                self.todo_card.list_widget.addItem(item)

        # 2. 뉴스 업데이트
        self.news_card.list_widget.clear()
        if not data["news"] and not db_manager.load_news_keywords():
            self.news_card.add_item("설정된 뉴스 키워드가 없습니다.")
        elif not data["news"]:
            self.news_card.add_item("관련 뉴스가 없습니다.")
        else:
            for news in data["news"]:
                self.news_card.add_item(f"• {news['title']}", use_ellipsis=True)

        # 3. 정책 브리핑 업데이트
        self.policy_card.list_widget.clear()
        if not data["policy"]:
            self.policy_card.add_item("신규 정책 브리핑이 없습니다.")
        else:
            for policy in data["policy"]:
                self.policy_card.add_item(f"• {policy['title']}", use_ellipsis=True)

        # 4. 법령 업데이트
        self.law_card.list_widget.clear()
        if not data["laws"] and not db_manager.load_law_keywords():
            self.law_card.add_item("설정된 법령 키워드가 없습니다.")
        elif not data["laws"]:
            self.law_card.add_item("❌ 오늘 시행/개정되는 법령이 없습니다.")
        else:
            for name in data["laws"][:5]:
                self.law_card.add_item(f"• {name}", use_ellipsis=True)

    def _on_data_error(self, error_msg):
        """데이터 로딩 중 에러가 발생했을 때의 처리입니다."""
        self.todo_card.list_widget.clear()
        self.news_card.list_widget.clear()
        self.law_card.list_widget.clear()

        self.todo_card.add_item("데이터 로드 실패")
        self.news_card.add_item("데이터 로드 실패")
        self.law_card.add_item("데이터 로드 실패")
        print(f"대시보드 로딩 에러: {error_msg}")
