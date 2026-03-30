import traceback
from PySide6.QtCore import Signal, QObject, QRunnable, Slot


class WorkerSignals(QObject):
    result_ready = Signal(object)
    error_occurred = Signal(str)
    finished = Signal()


class AsyncTask(QRunnable):
    def __init__(self, target_func, *args, **kwargs):
        super().__init__()
        self.setAutoDelete(True)
        self.target_func = target_func
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @Slot()
    def run(self):
        try:
            result = self.target_func(*self.args, **self.kwargs)
            self.signals.result_ready.emit(result)
        except Exception as e:
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            self.signals.error_occurred.emit(error_msg)
        finally:
            self.signals.finished.emit()
