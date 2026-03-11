from PySide6.QtCore import QThread, Signal


class AsyncTask(QThread):
    result_ready = Signal(object)
    error_occurred = Signal(str)

    def __init__(self, target_func, *args, parent=None, **kwargs):
        super().__init__()
        self.target_func = target_func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            result = self.target_func(*self.args, **self.kwargs)
            self.result_ready.emit(result)
        except Exception as e:
            self.error_occurred.emit(str(e))
