from PySide6.QtCore import QObject, Signal


class GlobalSignals(QObject):
    schedule_updated = Signal()
    roadmap_group_updated = Signal()


global_signals = GlobalSignals()
