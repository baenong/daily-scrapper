from core import db_manager


def load_settings():
    dark_mode_str = db_manager.get_setting("dark_mode", "1")
    is_dark_mode = True if dark_mode_str == "1" else False

    news_limit_str = db_manager.get_setting("news_limit", "15")
    news_limit = int(news_limit_str)

    return {"dark_mode": is_dark_mode, "news_limit": news_limit}


def save_settings(settings_dict):
    if "dark_mode" in settings_dict:
        db_value = "1" if settings_dict["dark_mode"] else "0"
        db_manager.set_setting("dark_mode", db_value)

    if "news_limit" in settings_dict:
        db_manager.set_setting("news_limit", str(settings_dict["news_limit"]))
