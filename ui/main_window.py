import qdarktheme
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
    QGraphicsOpacityEffect,
    QSpinBox,
)
from PySide6.QtCore import Qt, QUrl, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QDesktopServices, QColor, QBrush
from datetime import datetime, timezone

# core 폴더의 모듈들을 불러옵니다.
from core import data_manager
from core import news_scraper
from core import law_scraper
from core import startup_manager


class StyledButton(QPushButton):
    """
    버튼의 색상을 입력받아 일관된 스타일의 버튼을 반환하는 클래스

    text: 버튼의 caption
    bg_color_hex: 배경색을 hex로 입력
    text_color: (default: white) 글자색
    """

    def __init__(self, text, bg_color_hex, text_color="white"):
        super().__init__(text)

        self.setCursor(Qt.PointingHandCursor)

        if bg_color_hex == "transparent":
            normal_bg = "transparent"
            hover_bg = "rgba(128, 128, 128, 0.15)"
            pressed_bg = "rgba(128, 128, 128, 0.3)"
            final_text_color = text_color if text_color else "black"

        else:
            base_color = QColor(bg_color_hex)
            normal_bg = base_color.name()
            hover_bg = base_color.lighter(115).name()
            pressed_bg = base_color.darker(110).name()

            if not text_color:
                luminance = (
                    base_color.red() * 0.299
                    + base_color.green() * 0.587
                    + base_color.blue() * 0.114
                )

                final_text_color = "#131313" if luminance > 150 else "#FFFFFF"
            else:
                final_text_color = text_color

        self.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {normal_bg};
                color: {final_text_color};
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
            }}
            QPushButton:hover {{
                background-color: {hover_bg};
            }}
            QPushButton:pressed {{
                background-color: {pressed_bg};
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

        self.setWindowTitle("뉴스 법령 스크래퍼")
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

        bottom_layout = self.setup_footer()

        layout.addLayout(bottom_layout)

    def setup_footer(self):
        """
        Footer : 다크모드, 윈도우 자동실행
        """
        bottom_layout = QHBoxLayout()

        # 테마
        self.theme_checkbox = QCheckBox()
        self.theme_checkbox.setStyleSheet("padding: 5px;")

        is_dark = self.settings.get("dark_mode", True)
        self.theme_checkbox.setChecked(is_dark)
        self.theme_checkbox.toggled.connect(self.toggle_theme)

        bottom_layout.addWidget(self.theme_checkbox)

        # 저작권
        bottom_layout.addStretch()
        copyright_label = QLabel(
            "Copyright 2026. 행정지원과 안민수 All rights reserved."
        )
        copyright_label.setStyleSheet("color: #555555;")
        bottom_layout.addWidget(copyright_label)
        bottom_layout.addStretch()

        # 윈도우 자동실행
        self.startup_checkbox = QCheckBox("💻 윈도우 시작 시 자동 실행")
        self.startup_checkbox.setStyleSheet("color: #777777; padding: 5px;")

        self.startup_checkbox.setChecked(startup_manager.is_startup_enabled())
        self.startup_checkbox.toggled.connect(self.toggle_startup)

        bottom_layout.addWidget(self.startup_checkbox)
        self.toggle_theme(is_dark, animate=False)

        return bottom_layout

    def setup_news_tab(self):
        """
        뉴스 탭
        """
        news_tab = QWidget()
        layout = QVBoxLayout(news_tab)
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        # --- [왼쪽: 키워드 설정 영역] ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        keyword_title = QLabel("📌 검색할 키워드 목록")
        keyword_title.setStyleSheet(
            "font-weight: bold; font-size: 18px; margin-bottom: 10px;"
        )
        left_layout.addWidget(keyword_title)

        cond_layout = QHBoxLayout()

        self.radio_and = QRadioButton("AND")
        self.radio_or = QRadioButton("OR")
        self.radio_and.setChecked(True)
        self.radio_and.setFixedWidth(55)
        self.radio_or.setFixedWidth(55)

        btn_group = QButtonGroup(self)
        btn_group.addButton(self.radio_and)
        btn_group.addButton(self.radio_or)

        limit_label = QLabel("추출 갯수 : ")
        limit_label.setFixedWidth(70)

        self.news_limit = QSpinBox()
        self.news_limit.setRange(1, 50)
        self.news_limit.valueChanged.connect(self.change_news_limit)
        self.news_limit.setValue(self.settings.get("news_limit", 15))
        self.news_limit.setFixedWidth(60)

        search_btn = StyledButton("뉴스 검색", "#4CAF50")
        search_btn.clicked.connect(self.search_news)
        search_btn.setFixedWidth(100)

        cond_layout.addWidget(self.radio_and)
        cond_layout.addWidget(self.radio_or)
        cond_layout.addWidget(limit_label)
        cond_layout.addWidget(self.news_limit)
        cond_layout.addWidget(search_btn)
        left_layout.addLayout(cond_layout)

        # 키워드 추가 버튼
        add_btn = QPushButton("➕ 뉴스 키워드 추가")
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
        splitter.setSizes([400, 864])

        self.tabs.addTab(news_tab, "뉴스 스크랩")

    def add_keyword_row(self, text, is_checked):
        row = EditableRowWidget(text, is_checked, self.save_keywords_to_settings)
        self.keyword_list_layout.addWidget(row)
        if not text:
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
        # 설정된 조건(키워드, AND OR, limit 등)에 따른 뉴스를 검색
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
            news_items = news_scraper.get_news_by_query(
                final_query, limit=self.news_limit.value()
            )
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
        keyword_title = QLabel("📌 조회할 법령 목록")
        keyword_title.setStyleSheet(
            "font-weight: bold; font-size: 18px; margin-bottom: 10px;"
        )
        left_layout.addWidget(keyword_title)

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

        # --- 오른쪽: 법령 조회 결과 ---
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

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
        splitter.setSizes([400, 864])

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

    def change_news_limit(self):
        self.settings["news_limit"] = self.news_limit.value()
        data_manager.save_settings(self.settings)

    def toggle_startup(self, checked):
        success = startup_manager.set_startup(checked)
        if not success:
            QMessageBox.warning(
                self,
                "오류",
                "시작 프로그램 설정에 실패했습니다.\n백신 프로그램이 차단했는지 확인해 주세요.",
            )

    def toggle_theme(self, checked, animate=True):
        if animate:
            overlay = QLabel(self)
            overlay.setPixmap(self.grab())
            overlay.resize(self.size())
            overlay.move(0, 0)
            overlay.show()

        theme = "dark" if checked else "light"
        qdarktheme.setup_theme(theme)

        if checked:
            self.theme_checkbox.setText("🌙")
        else:
            self.theme_checkbox.setText("☀️")

        self.settings["dark_mode"] = checked
        data_manager.save_settings(self.settings)

        if animate:
            self.opacity_effect = QGraphicsOpacityEffect(overlay)
            overlay.setGraphicsEffect(self.opacity_effect)

            self.animation = QPropertyAnimation(self.opacity_effect, b"opacity")
            self.animation.setDuration(400)
            self.animation.setStartValue(1.0)
            self.animation.setEndValue(0.0)
            self.animation.setEasingCurve(QEasingCurve.InOutQuad)
            self.animation.finished.connect(overlay.deleteLater)
            self.animation.start()
