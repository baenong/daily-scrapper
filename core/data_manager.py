import json
import os

CONFIG_FILE = "settings.json"


def load_settings():
    # 파일이 없으면 기본 구조를 반환합니다.
    if not os.path.exists(CONFIG_FILE):
        return {
            "keywords": ["조례", "행정"],  # 기본 테스트 키워드
            "laws": [],
            "law_api_key": "",
        }

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_settings(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
