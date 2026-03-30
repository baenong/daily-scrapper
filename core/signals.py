from PySide6.QtCore import QObject, Signal


class GlobalSignals(QObject):
    schedule_updated = Signal()
    # schedule id, acrion
    schedule_modified = Signal(int, str)
    roadmap_group_updated = Signal()
    law_keyword_updated = Signal()

    # Font
    font_size_changed = Signal()


global_signals = GlobalSignals()
