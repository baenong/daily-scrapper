from PySide6.QtCore import QSettings

ORG_NAME = "Insa"
APP_NAME = "G-Daily"


class SettingsManager:

    DEFAULT_SETTINGS = {
        "dark_mode": (True, bool),
        "news_limit": (15, int),
        "news_cond_and": (True, bool),
        "window_opacity": (100, int),
        "always_on_top": (False, bool),
        "window_geometry": (None, None),
        "zoom_level": (100, int),
    }

    @staticmethod
    def load() -> dict:
        settings = QSettings(ORG_NAME, APP_NAME)
        loaded_settings = {}
        for key, (default_val, val_type) in SettingsManager.DEFAULT_SETTINGS.items():
            if val_type:
                loaded_settings[key] = settings.value(key, default_val, type=val_type)
            else:
                loaded_settings[key] = settings.value(key, default_val)

        return loaded_settings

    @staticmethod
    def save(settings_dict: dict):
        settings = QSettings(ORG_NAME, APP_NAME)

        for key, value in settings_dict.items():
            if value is not None:
                settings.setValue(key, value)
