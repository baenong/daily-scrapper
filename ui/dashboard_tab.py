from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
)
from PySide6.QtCore import QDate
from datetime import datetime

# 공통 부품 및 코어 모듈 불러오기
from ui.components import TitleLabel, DashboardCard, TrendTickerWidget
from ui.schedule_tab import get_instances
from core import db_manager, news_scraper, law_scraper, policy_scraper
from core.worker import run_async


class DashboardTab(QWidget):
    """오늘의 일정, 뉴스, 법령을 한눈에 보여주는 첫 화면 탭입니다."""

    def __init__(self, settings, go_to_tab_callback):
        super().__init__()
        self.settings = settings
        self.go_to_tab = go_to_tab_callback
        self.is_loaded = False
        self.setup_ui()
        self.load_dashboard_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(100, 40, 100, 40)

        welcome_label = TitleLabel(
            f"👋 환영합니다! 오늘({QDate.currentDate().toString('yyyy.MM.dd')})의 주요 현황을 확인하세요.",
            20,
        )
        layout.addStretch(3)
        layout.addWidget(welcome_label)

        self.trend_ticker = TrendTickerWidget()
        layout.addStretch(1)
        layout.addWidget(TitleLabel(" 🔥 구글 트렌드"))
        layout.addWidget(self.trend_ticker)
        layout.addStretch(1)

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

        cards_layout.addWidget(self.todo_card, 1)
        cards_layout.addWidget(self.news_card, 1)
        cards_layout.addWidget(self.policy_card, 1)
        cards_layout.addWidget(self.law_card, 1)

        layout.addLayout(cards_layout)
        layout.addStretch(6)

    def load_dashboard_data(self):
        if getattr(self, "is_fetching", False):
            return
        self.is_fetching = True

        self.todo_card.clear_items()
        self.news_card.clear_items()
        self.policy_card.clear_items()
        self.law_card.clear_items()

        self.todo_card.add_item("⏳ 데이터 불러오는 중...")
        self.news_card.add_item("⏳ 데이터 불러오는 중...")
        self.policy_card.add_item("⏳ 데이터 불러오는 중...")
        self.law_card.add_item("⏳ 데이터 불러오는 중...")

        # 백그라운드 스레드 생성 및 실행
        run_async(
            self._fetch_data_in_background, self._on_data_loaded, self._on_data_error
        )

    def _fetch_data_in_background(self):
        result = {
            "todos": [],
            "news": [],
            "policy": [],
            "laws": [],
            "trends": [],
            "has_news_kw": False,
            "has_law_kw": False,
        }

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
        result["has_news_kw"] = len(db_news_kws) > 0

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
                result["news"] = news_scraper.get_news_by_query(final_query, 5)
            else:
                result["news"] = news_scraper.get_news_by_or_query(selected_groups, 5)

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
        result["has_law_kw"] = len(db_law_kws) > 0

        law_keywords = [law["text"] for law in db_law_kws if law.get("checked", True)]
        if law_keywords:
            today_laws = []
            all_infos = law_scraper.get_laws_by_keywords(law_keywords)

            for info in all_infos:
                if info["enforce_date"] == today_str_law:
                    today_laws.append(info["name"])

            result["laws"] = list(set(today_laws))

        # 5. 트렌드
        try:
            result["trends"] = news_scraper.get_google_trends()
        except Exception:
            pass

        return result

    def _on_data_loaded(self, data):
        """백그라운드 작업이 끝나면 신호를 받아 UI를 업데이트합니다."""
        # 1. 일정 업데이트
        # self.todo_card.list_widget.clear()
        self.todo_card.clear_items()
        self.is_fetching = False

        if not data["todos"]:
            self.todo_card.add_item("❌ 오늘 등록된 일정이 없습니다.")
        else:
            for t in data["todos"][:5]:
                is_comp = t.get("is_completed", False)
                prefix = "✅ " if is_comp else "✏️ "
                self.todo_card.add_item(
                    text=prefix + t["title"], use_ellipsis=True, is_completed=is_comp
                )

        # 2. 뉴스 업데이트
        # self.news_card.list_widget.clear()
        self.news_card.clear_items()
        if not data["news"] and not data["has_news_kw"]:
            self.news_card.add_item("설정된 뉴스 키워드가 없습니다.")
        elif not data["news"]:
            self.news_card.add_item("관련 뉴스가 없습니다.")
        else:
            for news in data["news"]:
                self.news_card.add_item(f"• {news['title']}", use_ellipsis=True)

        # 3. 정책 브리핑 업데이트
        # self.policy_card.list_widget.clear()
        self.policy_card.clear_items()
        if not data["policy"]:
            self.policy_card.add_item("신규 정책 브리핑이 없습니다.")
        else:
            for policy in data["policy"]:
                self.policy_card.add_item(f"• {policy['title']}", use_ellipsis=True)

        # 4. 법령 업데이트
        # self.law_card.list_widget.clear()
        self.law_card.clear_items()
        if not data["laws"] and not data["has_law_kw"]:
            self.law_card.add_item("설정된 법령 키워드가 없습니다.")
        elif not data["laws"]:
            self.law_card.add_item("❌ 오늘 시행/개정되는 법령이 없습니다.")
        else:
            for name in data["laws"][:5]:
                self.law_card.add_item(f"• {name}", use_ellipsis=True)

        # 5. 트렌드
        if "trends" in data and data["trends"]:
            self.trend_ticker.set_data(data["trends"])

    def _on_data_error(self, error_msg):
        """데이터 로딩 중 에러가 발생했을 때의 처리입니다."""
        self.is_fetching = False

        self.todo_card.clear_items()
        self.news_card.clear_items()
        self.policy_card.clear_items()
        self.law_card.clear_items()

        self.todo_card.add_item("데이터 로드 실패")
        self.news_card.add_item("데이터 로드 실패")
        self.policy_card.add_item("데이터 로드 실패")
        self.law_card.add_item("데이터 로드 실패")
        print(f"대시보드 로딩 에러: {error_msg}")
