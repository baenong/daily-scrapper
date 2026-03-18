from PySide6.QtCore import QSettings

ORG_NAME = "Insa"
APP_NAME = "G-Daily"


class SettingsManager:
    @staticmethod
    def load() -> dict:
        settings = QSettings(ORG_NAME, APP_NAME)

        return {
            "dark_mode": settings.value("dark_mode", True, type=bool),
            "news_limit": settings.value("news_limit", 15, type=int),
            "news_cond_and": settings.value("news_cond_and", True, type=bool),
            "window_opacity": settings.value("window_opacity", 100, type=int),
            "always_on_top": settings.value("always_on_top", False, type=bool),
            "window_geometry": settings.value("window_geometry", None),
        }

    @staticmethod
    def save(settings_dict: dict):
        settings = QSettings(ORG_NAME, APP_NAME)

        for key, value in settings_dict.items():
            if value is not None:
                settings.setValue(key, value)
