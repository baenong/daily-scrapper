import json
import os

CONFIG_FILE = "settings.json"


def load_settings():
    if not os.path.exists(CONFIG_FILE):
        return {
            "keywords": ["조례", "행정"],
            "laws": [],
            "law_api_key": "",
        }

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_settings(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
