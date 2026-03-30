import os
import sys
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QTabWidget,
    QTextBrowser,
    QHBoxLayout,
)
from PySide6.QtGui import QPixmap
from core.tw_utils import COLORS
from ui.components import TitleLabel, DescriptionLabel, StyledButton


def get_img_tag(filename, max_width=540):
    """
    resources 폴더를 참조할 수 있도록 file:// URL로 변경하고 너비를 조정함
    """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    abs_path = os.path.join(base_path, "resources", "help", filename)
    pixmap = QPixmap(abs_path)

    if pixmap.isNull():
        return f"<div style='text-align: center; color: red;'>[이미지 파일 누락: {filename}]</div>"

    safe_path = abs_path.replace("\\", "/")
    img_url = f"file:///{safe_path}"

    actual_width = pixmap.width()
    final_width = max_width if actual_width > max_width else actual_width

    return f"<div style='text-align: center;'><img src='{img_url}' width='{final_width}'></div>"


class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("G-Daily 사용 설명서")
        self.setMinimumSize(650, 900)

        layout = QVBoxLayout(self)
        layout.addWidget(TitleLabel("📖 G-Daily 사용 설명서"))
        layout.addWidget(DescriptionLabel("G-Daily의 사용법을 알려드립니다."))

        # 탭 위젯 생성
        self.tabs = QTabWidget()

        # 탭별 내용 추가
        self.add_help_tab("1. 메인화면", self.get_main_help())
        self.add_help_tab("2. 뉴스 스크랩", self.get_news_help())
        self.add_help_tab("3. 법령 개정", self.get_law_help())
        self.add_help_tab("4. 정책 브리핑", self.get_policy_help())
        self.add_help_tab("5. 일정 관리", self.get_schedule_help())
        self.add_help_tab("6. 연간 로드맵", self.get_roadmap_help())

        layout.addWidget(self.tabs)

        # 닫기 버튼
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = StyledButton("닫기", "transparent")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def add_help_tab(self, title, html_content):
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setHtml(
            f"""
            <html>
            <head>
                <style>
                    body {{
                        font-family: 'Pretendard Variable', 'Pretendard', 'Malgun Gothic', sans-serif;
                    }}
                    h2 {{
                        margin-bottom: 10px;
                    }}
                    h4 {{
                        font-style: italic;
                        margin: 5px 0;
                    }}
                    div {{
                        margin-top: 25px;
                        font-size: 14px;
                    }}
                    img {{
                        margin-top: 5px;
                        margin-bottom: 10px;
                    }}
                </style>
            </head>
            <body>
                {html_content}
            </body>
            </html>
            """
        )
        self.tabs.addTab(browser, title)

    # ---------------------------------------------------------
    # 아래에 각 탭별 HTML 내용을 리턴하는 함수를 만듭니다. (위에서 정리한 텍스트 반영)
    # ---------------------------------------------------------
    def get_main_help(self):
        return f"""
        <h3>🏠 메인화면 및 기본 기능</h3>
        <div>■ <b>대시보드:</b> 오늘의 일정, 뉴스, 법령 등 핵심 요약 정보를 한눈에 확인합니다.</div>
        {get_img_tag("help_dashboard.png")}
        <div>■ <b>테마전환:</b> 하단의 🌙, ☀️를 체크하여 다크/라이트 모드를 전환할 수 있습니다.</div>
        <div>■ <b>🖥️ 위젯모드: </b> 화면을 작게 만드는 '위젯 모드'를 사용할 수 있습니다.</div>
        <div>■ <b>📌 맨 앞 고정:</b> 핀(📌) 버튼을 누르면 다른 창들에 가려지지 않습니다.</div>
        <div>■ <b>💻 자동실행:</b> 컴퓨터 실행 시 자동으로 실행할 지 선택합니다.</div>
        <div>■ <b>단축키:</b> Ctrl + Shift + Space를 누르면 즉시 화면에 나타납니다.</div>
        """

    def get_news_help(self):
        return f"""
        <h3>📰 뉴스 스크랩 탭</h3>
        <div>■ <b>키워드:</b> 한 키워드 안에 여러 검색어를,(쉼표)로 입력할 수 있습니다. 제외하고 싶은 검색어 앞에는 -(마이너스)를 붙입니다.</div>
        <br>
        <h4>예시 )</h4>
        {get_img_tag("help_news_keyword.png")}
        <h4>[공무원,인사]로 설정하면 '공무원'과 '인사'를 포함한 뉴스들을 불러옵니다.</h4>
        <h4>[공무원,-복무]로 설정하면 '공무원'은 포함되어 있고 '복무'는 제외된 뉴스들을 불러옵니다.</h4>
        <div>■ <b>검색조건 설정:</b> 체크한 키워드들에 대해 AND 조건과 OR 조건을 선택하여 검색할 수 있습니다.</div>
        {get_img_tag("help_news_cond.png")}
        <div>■ <b>결과 내 검색:</b> 우측 검색창을 통해 수집된 기사 중 원하는 내용만 즉시 필터링할 수 있습니다.</div>
        <div>■ 기사를 더블클릭하면 원문 웹페이지로 이동하며, 최근 3일 이내의 기사는 <b>
            <span style='background: red;'>붉은색 배경</span></b>으로 강조됩니다.</div>
        {get_img_tag("help_news_search.png")}
        """

    def get_law_help(self):
        return f"""
        <h3>⚖️ 법령 개정 알림 탭</h3>
        <div>■ <b>조회:</b> 키워드가 포함된 모든 법령을 가져옵니다.</div>
        <div>■ <b>색상 강조:</b> 오늘 시행되는 법령은 <b><span style='background: red; color: #fff;'> 붉은색 </span></b>, 시행 예정인 법령은 <b>
                            <span style='background: darkred; color: #fff;'> 붉은 음영처리 </span></b>되어 표시됩니다.</div>
        <br>
        <h4>예시 )</h4>
        {get_img_tag("help_laws.png")}
        <div>■ <b>원문 조회:</b> 법령을 더블클릭하면 '국가법령정보센터'의 해당 법령 페이지로 즉시 이동합니다.</div>
        """

    def get_policy_help(self):
        return f"""
        <h3>🏛️ 정책 브리핑 탭</h3>
        <div>■ <b>부처 선택:</b> 좌측에서 브리핑을 구독할 정부 부처를 선택합니다.</div>
        <div>■ <b>필터링:</b> 우측 상단 콤보박스와 검색창을 이용해 특정 부처의 브리핑만 골라볼 수 있습니다.</div>
        <div>■ <b>강조 효과:</b> 더블클릭하여 원문을 확인할 수 있으며, 최근 2일 이내의 자료는 <b>
                            <span style='background: {COLORS['blue-500']};'>푸른색 배경</span></b>으로 강조됩니다.</div>
        {get_img_tag("help_policy_brief.png")}
        """

    def get_schedule_help(self):
        return f"""
        <h3>📅 일정 관리 탭</h3>
        <div>■ <b>일정 추가:</b> 달력의 빈칸을 더블클릭하여 일정을 즉시 추가할 수 있습니다.</div>
        {get_img_tag("help_calendar_edit.png")}
        <div>■ <b>반복 일정:</b> 일, 주, 월, 연 단위로 반복하도록 설정할 수 있습니다.</div>
        <div>- 공통사항: 선택한 반복 구분에 따른 주기와 종료일을 지정할 수 있습니다. (지정하지 않으면 계속 반영) 급여일처럼 주말인 경우 직전 평일로 당길 수 있습니다.</div>
        {get_img_tag("help_calendar_repeat_day.png")}
        <div>- 주: 주마다 반복할 요일을 지정할 수 있습니다.</div>
        {get_img_tag("help_calendar_repeat_week.png")}
        <div>- 월: 매월 정해진 일자에 반복할 지(like 급여) 혹은 특정 주의 요일에 반복하도록 할 수 있습니다.</div>
        {get_img_tag("help_calendar_repeat_month.png")}
        <div>- 연: 매년 반복할 일자를 지정할 수 있습니다.</div>
        {get_img_tag("help_calendar_repeat_year.png")}
        <div>■ <b>로드맵 추가:</b> 연간 로드맵에서 확인할 수 있도록 지정합니다. </div>
        {get_img_tag("help_calendar_roadmap.png")}
        <div>■ <b>법령 개정 알림:</b> 시행 예정인 법령을 달력에서 한 눈에 볼 수 있도록 합니다.</div>
        {get_img_tag("help_calendar_cell.png")}
        <div>■ <b>상세 보기:</b> 각 날짜의 숫자(예: '15')나 일정이 많을 때 표시되는 '+N 더보기' 텍스트를 클릭하면 그날의 일정 목록 팝업이 나타납니다.</div>
        {get_img_tag("help_calendar_daily_events.png")}
        <h4>시행예정 법령은 일정에 표시되지는 않습니다.</h4>
        <div>■ <b>우클릭 빠른 메뉴:</b> 일정 막대(Bar)를 <span style='color: {COLORS['blue-500']}'>마우스 우클릭</span>하면
                                [완료 처리], [편집], [삭제]를 빠르게 실행할 수 있습니다.</div>
        {get_img_tag("help_calendar_context.png")}
        """

    def get_roadmap_help(self):
        return f"""
        <h3>🗺️ 연간 로드맵 탭</h3>
        <div>■ <b>로드맵 연동:</b> 일정 관리에서 '★ 로드맵'으로 지정된 핵심 일정들이 연간 간트 차트 형태로 그려집니다.</div>
        {get_img_tag("help_roadmap.png")}
        <div>■ <b>그룹 관리:</b> 상단의 [그룹 관리] 버튼을 눌러 프로젝트 등 관련 업무별로 그룹을 나누고 색상을 지정할 수 있습니다.<br>
                            일정 편집 화면에서도 ⚙️ 버튼을 클릭하여 그룹을 추가할 수 있습니다.</div>
        {get_img_tag("help_roadmap_group.png")}
        <div>■ <b>우클릭 빠른 메뉴:</b> 캘린더와 동일하게 막대나 글자를 우클릭하여 편집, 완료처리 및 삭제가 가능합니다.</div>
        {get_img_tag("help_roadmap_context.png")}
        """
