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
from core import db_manager, news_scraper, law_scraper


class EllipsisLabel(QLabel):
    """영역을 벗어나면 자동으로 말줄임표(...) 처리를 해주는 라벨입니다."""

    def __init__(self, text):
        super().__init__()
        self._original_text = text

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setStyleSheet("background: transparent; border: none;")

    def resizeEvent(self, event):
        """위젯의 가로 크기가 변할 때마다 실행되어 글자를 알맞게 자릅니다."""
        metrics = self.fontMetrics()
        elided_text = metrics.elidedText(
            self._original_text, Qt.ElideRight, self.width() - 5
        )

        super().setText(elided_text)
        super().resizeEvent(event)


class DashboardCard(QFrame):
    """대시보드에 들어갈 개별 정보 카드 위젯입니다."""

    def __init__(self, title, btn_text, btn_callback):
        super().__init__()
        # 카드 느낌을 내기 위해 테두리와 배경색을 살짝 줍니다.
        self.setFrameShape(QFrame.StyledPanel)
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
        self.list_widget.setSelectionMode(QListWidget.NoSelection)
        self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        layout.addWidget(self.list_widget)

        # 자세히 보기 버튼
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
        self.go_to_tab = go_to_tab_callback  # 메인 창에서 받아온 탭 이동 '리모컨'

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

        # 1. 일정 카드 (탭 인덱스 3으로 이동)
        self.todo_card = DashboardCard(
            "📅 오늘의 일정", "일정 탭으로 이동 ➔", lambda: self.go_to_tab(3)
        )
        # 2. 뉴스 카드 (탭 인덱스 1로 이동)
        self.news_card = DashboardCard(
            "📰 최신 관심 뉴스", "뉴스 탭으로 이동 ➔", lambda: self.go_to_tab(1)
        )
        # 3. 법령 카드 (탭 인덱스 2로 이동)
        self.law_card = DashboardCard(
            "🚨 오늘 시행되는 관심 법령",
            "법령 탭으로 이동 ➔",
            lambda: self.go_to_tab(2),
        )

        cards_layout.addWidget(self.todo_card)
        cards_layout.addWidget(self.news_card)
        cards_layout.addWidget(self.law_card)

        layout.addLayout(cards_layout)
        layout.addStretch(1)

    def load_dashboard_data(self):
        """각 모듈에서 데이터를 가져와 카드에 요약해서 뿌려줍니다."""
        today_qdate = QDate.currentDate()
        today_str_law = datetime.now().strftime("%Y.%m.%d")

        # 1. 일정 로드 (수정된 부분)
        self.todo_card.list_widget.clear()
        all_schedules = db_manager.get_schedules()
        today_events = []

        # 오늘 날짜에 걸쳐있는 모든 일정을 찾습니다.
        for s in all_schedules:
            instances = get_instances(s, today_qdate, today_qdate)
            if instances:
                today_events.append(s)

        # 미완료 일정이 위로 오도록 정렬합니다.
        today_events.sort(key=lambda x: x.get("is_completed", False))

        if not today_events:
            self.todo_card.add_item("❌ 오늘 등록된 일정이 없습니다.")
        else:
            for t in today_events[:5]:  # 최대 5개만 표시
                is_comp = t.get("is_completed", False)
                prefix = "✅ " if is_comp else "✏️ "

                item = QListWidgetItem(prefix + t["title"])
                if is_comp:
                    item.setForeground(Qt.gray)

                self.todo_card.list_widget.addItem(item)

        # 2. 뉴스 로드
        self.news_card.list_widget.clear()
        db_news_kws = db_manager.load_news_keywords()
        keywords = [kw["text"] for kw in db_news_kws if kw.get("checked", True)]

        if not keywords:
            self.news_card.add_item("설정된 뉴스 키워드가 없습니다.")
        else:
            final_query = " ".join(keywords)  # AND 조건이라 가정
            try:
                news_items = news_scraper.get_news_by_query(final_query, limit=5)
                if news_items:
                    for news in news_items:
                        self.news_card.add_item(f"• {news['title']}", use_ellipsis=True)
                else:
                    self.news_card.add_item("관련 뉴스가 없습니다.")
            except Exception:
                self.news_card.add_item("뉴스 로드 중 오류 발생")

        # 3. 법령 로드
        self.law_card.list_widget.clear()
        db_law_kws = db_manager.load_law_keywords()
        laws = [law["text"] for law in db_law_kws if law.get("checked", True)]

        if not laws:
            self.law_card.add_item("설정된 법령 키워드가 없습니다.")
        else:
            today_laws = []
            for law_name in laws:
                infos = law_scraper.get_law_group_info(law_name)
                if infos:
                    for info in infos:
                        if info["enforce_date"] == today_str_law:
                            today_laws.append(info["name"])

            today_laws = list(set(today_laws))  # 중복 제거
            if today_laws:
                for name in today_laws[:5]:
                    self.law_card.add_item(f"• {name}", use_ellipsis=True)
            else:
                self.law_card.add_item("❌ 오늘 시행/개정되는 법령이 없습니다.")
