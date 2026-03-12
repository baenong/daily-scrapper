from PySide6.QtWidgets import (
    QVBoxLayout,
    QPushButton,
    QLineEdit,
    QLabel,
    QHBoxLayout,
    QCheckBox,
    QWidget,
)
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt, Signal


class StyledButton(QPushButton):
    """
    버튼의 색상을 입력받아 일관된 스타일의 버튼을 반환하는 클래스

    text: 버튼의 caption
    bg_color_hex: 배경색을 hex로 입력
    text_color: (default: white) 글자색
    """

    def __init__(self, text, bg_color_hex, text_color=None, padding="5px 10px"):
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
                padding: {padding};
            }}
            QPushButton:hover {{
                background-color: {hover_bg};
            }}
            QPushButton:pressed {{
                background-color: {pressed_bg};
            }}
        """
        )


class DoubleClickLineEdit(QLineEdit):
    """더블 클릭 이벤트를 가능하게 한 커스텀 QLineEdit"""

    doubleClicked = Signal()
    focusLost = Signal()

    def mouseDoubleClickEvent(self, event):
        super().mouseDoubleClickEvent(event)
        self.doubleClicked.emit()

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self.focusLost.emit()


class TitleLabel(QLabel):
    def __init__(self, text):
        super().__init__(text)
        self.setStyleSheet(f"font-weight: bold; font-size: 18px;")


class DescriptionLabel(QLabel):
    def __init__(self, text):
        super().__init__(text)
        self.setStyleSheet("color: #777777; margin-bottom: 10px;")


class EditableRowWidget(QWidget):
    """뉴스 키워드와 법령 목록 모두에서 재사용 가능한 체크박스+편집 위젯입니다."""

    def __init__(self, text, is_checked, save_callback):
        super().__init__()
        self.save_callback = save_callback

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.checkbox = QCheckBox()
        self.checkbox.setChecked(is_checked)

        self.line_edit = DoubleClickLineEdit(text)
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

        # 이벤트 핸들러
        self.btn_edit.clicked.connect(self.enable_edit)
        self.btn_save.clicked.connect(self.save_edit)
        self.btn_del.clicked.connect(self.delete_row)
        self.line_edit.doubleClicked.connect(self.enable_edit)
        self.line_edit.returnPressed.connect(self.save_edit)
        self.line_edit.focusLost.connect(self.save_edit)

    def enable_edit(self):
        self.line_edit.setReadOnly(False)
        self.line_edit.setStyleSheet("background-color: white; color: black;")
        self.line_edit.setFocus()
        self.btn_edit.hide()
        self.btn_save.show()

    def save_edit(self):
        if self.line_edit.isReadOnly():
            return

        self.line_edit.setReadOnly(True)
        self.line_edit.setStyleSheet("")
        self.btn_save.hide()
        self.btn_edit.show()
        self.save_callback()

    def delete_row(self):
        self.setParent(None)
        self.deleteLater()
        self.save_callback()


class ArticleItemWidget(QWidget):
    """뉴스와 정책브리핑 리스트에 사용할 수 있는 커스템 위젯"""

    def __init__(self, title, source, pub_date, icon=""):
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 8, 5, 8)
        layout.setSpacing(8)

        self.title_label = QLabel(f"{icon} {title}")
        self.title_label.setStyleSheet("font-size: 14px;")

        self.meta_label = QLabel(f"[{source}]  🗓️ {pub_date}")
        self.meta_label.setStyleSheet("font-size: 13px; color: #777777;")

        layout.addWidget(self.title_label)
        layout.addWidget(self.meta_label)
