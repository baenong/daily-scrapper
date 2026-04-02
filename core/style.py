import sys
import os
from PySide6.QtWidgets import QApplication, QStyleFactory, QProxyStyle, QStyle
from PySide6.QtGui import QPalette, QColor
from PySide6.QtCore import Qt
from core.tw_utils import tw, tw_sheet, COLORS


class GlobalProxyStyle(QProxyStyle):
    def styleHint(self, hint, option=None, widget=None, returnData=None):
        if hint == QStyle.StyleHint.SH_ComboBox_Popup:
            return 0

        if hint == QStyle.StyleHint.SH_ScrollBar_LeftClickAbsolutePosition:
            return 1

        return super().styleHint(hint, option, widget, returnData)

    def drawPrimitive(self, element, option, painter, widget=None):
        if element == QStyle.PrimitiveElement.PE_FrameFocusRect:
            return

        super().drawPrimitive(element, option, painter, widget)


def get_qss_image_path(filename: str) -> str:
    if getattr(sys, "frozen", False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    abs_path = os.path.join(base_path, "resources", "svg", filename)
    return abs_path.replace("\\", "/")


def get_global_qss(is_dark: bool) -> str:

    input_bg = "black-400" if is_dark else "white"
    item_bg = "black-300" if is_dark else "white"
    header_bg = "black-400" if is_dark else "cF0"
    border_color = "c44" if is_dark else "cCC"
    text_color = "white" if is_dark else "c13"
    blue_color = "blue-500"

    hover_bg = "black-300" if is_dark else "cF5"

    tab_selected_bg = "black-300" if is_dark else "white"
    disabled_bg = "black-300" if is_dark else "cF5"
    disabled_text = "c80"
    scrollbar_bg = "c80-5"
    scrollbar_handle = "c80-30"
    scrollbar_handle_hover = "c80-50"

    img_path = get_qss_image_path("")
    base_style = f"bg-{input_bg} border-b border-{border_color} rounded-4 text-{text_color} sel-bg-{blue_color}"

    basic_rules = {
        #
        # Base Style
        #
        "QLineEdit, QTextEdit, QComboBox, QDateEdit, QListWidget": base_style + " p-5",
        "QSpinBox": base_style + " py-3 px-10",
        #
        # Focus
        #
        """
        QLineEdit:focus, 
        QTextEdit:focus, 
        QSpinBox:focus, 
        QComboBox:focus, 
        QDateEdit:focus
        """: f"border-b border-{blue_color}",
        #
        # Disabled
        #
        """
        QLineEdit:disabled, 
        QTextEdit:disabled, 
        QSpinBox:disabled, 
        QComboBox:disabled, 
        QDateEdit:disabled
        """: f"bg-{disabled_bg} text-{disabled_text} border-{border_color}",
        #
        # CheckBox
        #
        "QCheckBox, QRadioButton": "space-8",
        "QCheckBox::indicator, QRadioButton::indicator": "w-16 h-16",
        #
        # HeaderView
        #
        "QHeaderView": "bg-transparent border-none",
        "QHeaderView::section": f"""bg-{header_bg} text-{text_color} font-700 
                                    py-8 px-5 border-b border-{border_color}""",
        #
        # Table
        #
        "QTableWidget": f"""
                            border-none bg-{item_bg} grid-{border_color}
                            sel-bg-{blue_color} text-{text_color}
                        """,
        "QTableWidgetItem": f"bg-{item_bg} text-{text_color}",
        "QTableCornerButton::section": f"bg-{header_bg} border-b border-{border_color}",
        #
        # TabBar
        #
        "QTabBar::tab": f"bg-transparent text-{text_color} px-8 py-6 mr-2 rounded-t-4",
        "QTabBar::tab:selected": f"""bg-{tab_selected_bg} font-700 text-{text_color} 
                                    border-bb-3 border-{blue_color}""",
    }

    qss_base = tw_sheet(basic_rules)

    combo_qss = f"""
        QComboBox QAbstractItemView {{
            {tw(f"border-b", f"border-{border_color}", f"sel-bg-{blue_color}")}
        }}

        QComboBox QAbstractItemView::item {{
            padding: 5px;
        }}

        QComboBox::down-arrow {{
            image: url({img_path}/combo_arrow.svg);
            {tw("w-18", "h-18")}
        }}

        QComboBox::down-arrow:disabled {{ image: none; }}

        QComboBox::drop-down, QDateEdit::drop-down, QDateTimeEdit::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: center right;
            padding-top: 2px;
            width: 18px;

            border-left-style: none;
            border-top-right-radius: 3px;
            border-bottom-right-radius: 3px;
        }}
        """

    cb_qss = f"""
        QCheckBox::indicator:unchecked {{
            image: url({img_path}/cb_unchecked.svg);
            {tw("w-18", "h-18")}
        }}

        QCheckBox::indicator:checked {{
            image: url({img_path}/cb_checked.svg);
            {tw("w-18", "h-18")}
        }}

        QCheckBox::indicator:unchecked:hover {{
            image: url({img_path}/cb_unchecked_hover.svg);
        }}
        """

    abstract_qss = f"""
        QAbstractSpinBox::up-button, 
        QAbstractSpinBox::down-button {{
            border-left: 1px;
            {tw("bg-transparent", "border-solid", f"border-{border_color}")}
        }}

        QAbstractSpinBox::up-button:hover, 
        QAbstractSpinBox::down-button:hover {{
            {tw("bg-c80-10")}
        }}

        QAbstractSpinBox::up-arrow {{
            image: url({img_path}/spin_up.svg);
            {tw("w-10", "h-10")}
        }}

        QAbstractSpinBox::down-arrow {{
            image: url({img_path}/spin_down.svg);
            {tw("w-10", "h-10")}
        }}

        QAbstractSpinBox::up-arrow:disabled, 
        QAbstractSpinBox::down-arrow:disabled {{ image: none; }}

        QTableWidget, QScrollArea QWidget {{
            {tw("bg-transparent")}
        }}

        QScrollArea {{
            {tw("bg-transparent", "border-b", "border-c33", "rounded-4")}
        }}
        """

    listwidget_rules = {
        "QListWidget": "bg-transparent",
        "QListWidget::item": f"text-{text_color} rounded-4",
        "QListWidget::item:hover": f"bg-{hover_bg}",
        "QListWidget::item:selected": f"bg-{blue_color}-50 text-white border-none",
    }
    listwidget_qss = tw_sheet(listwidget_rules)

    calendar_qss = f"""
        QDateEdit::down-arrow, QDateTimeEdit::down-arrow {{
            image: url({img_path}/date_calendar.svg);
            {tw("w-18", "h-18")}
        }}

        QCalendarWidget QWidget {{
            alternate-background-color: {COLORS[item_bg]}; 
            background-color: {COLORS[input_bg]};
        }}

        QCalendarWidget QAbstractItemView:enabled {{
            color: {COLORS[text_color]};
            background-color: {COLORS[input_bg]};
            selection-background-color: {COLORS[blue_color]};
            selection-color: white;
            border-radius: 4px;
        }}
        
        QCalendarWidget QToolButton {{
            {tw(f"text-{text_color}", "bg-transparent", "m-2")}
        }}

        QCalendarWidget QToolButton:hover {{ 
            {tw("bg-c80", "rounded-4")}
        }}
        
        QCalendarWidget QMenu {{ 
            background-color: {COLORS[input_bg]}; 
            color: {COLORS[text_color]}; 
        }}
        """

    menu_rules = {
        "QMenu": f"bg-{item_bg} border-b border-{border_color} rounded-6 py-4",
        "QMenu::item": f"py-6 px-24 bg-transparent text-{text_color}",
        "QMenu::item:selected": f"bg-{blue_color} text-white rounded-4",
        "QMenu::item:disabled": f"text-{disabled_text} bg-transparent",
        "QMenu::separator": f"h-1 my-2 bg-{border_color}",
        #
        # Tray Menu
        "QMenu#TrayMenu": f"bg-gray-900 border-b border-{border_color} rounded-6 py-2 text-12 font-malgun",
        "QMenu#TrayMenu::item": f"py-4 px-16 bg-transparent text-c13 text-12 font-malgun",
        "QMenu#TrayMenu::item:selected": f"bg-{blue_color} text-white rounded-4",
        "QMenu#TrayMenu::separator": f"h-1 my-2 bg-{border_color}",
    }
    menu_qss = tw_sheet(menu_rules)

    scrollbar_rules = {
        # ScrollBar
        "QScrollBar:vertical": f"border-none bg-{scrollbar_bg} w-10 m-0 rounded-5",
        "QScrollBar::handle:vertical": f"bg-{scrollbar_handle} rounded-5 min-h-30",
        "QScrollBar::handle:vertical:hover": f"bg-{scrollbar_handle_hover}",
        "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical": "h-0",
        "QScrollBar:horizontal": f"border-none bg-{scrollbar_bg} h-10 m-0 rounded-5",
        "QScrollBar::handle:horizontal": f"bg-{scrollbar_handle} rounded-5 min-w-30",
        "QScrollBar::handle:horizontal:hover": f"bg-{scrollbar_handle_hover}",
        "QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal": "w-0",
    }
    scrollbar_qss = tw_sheet(scrollbar_rules)

    return (
        qss_base
        + abstract_qss
        + combo_qss
        + cb_qss
        + listwidget_qss
        + calendar_qss
        + menu_qss
        + scrollbar_qss
    )


def setup_theme(app: QApplication, is_dark: bool):
    """애플리케이션 전체의 테마(프록시, 팔레트, QSS)를 한 번에 세팅합니다."""

    base_style = QStyleFactory.create("Fusion")
    app.setStyle(GlobalProxyStyle(base_style))

    palette = QPalette()
    if is_dark:
        palette.setColor(QPalette.ColorRole.Window, QColor(32, 33, 36))
        palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Base, QColor(40, 42, 45))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(50, 52, 55))
        palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.black)
        palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Button, QColor(50, 52, 55))
        palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.white)
    else:
        palette.setColor(QPalette.ColorRole.Window, QColor(245, 245, 245))
        palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.black)
        palette.setColor(QPalette.ColorRole.Base, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(240, 240, 240))
        palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.black)
        palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.black)
        palette.setColor(QPalette.ColorRole.Button, QColor(240, 240, 240))
        palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.black)
        palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.white)

    app.setPalette(palette)
    app.setStyleSheet(get_global_qss(is_dark))
