import os
import requests
import urllib.parse
import concurrent.futures
from core.network import global_session as session


def format_date(date_str):
    if date_str and len(date_str) == 8 and date_str.isdigit():
        return f"{date_str[:4]}.{date_str[4:6]}.{date_str[6:]}"
    return date_str


def get_law_group_info(law_name):
    api_key = os.environ.get("LAW_API_KEY", "")

    if not api_key:
        print(f"API 오류: KEY가 존재하지 않습니다.")
        return []

    url = "https://www.law.go.kr/DRF/lawSearch.do"
    params = {
        "OC": api_key,
        "target": "eflaw",
        "type": "json",
        "query": law_name,
        "nw": "2,3",
    }

    try:
        response = session.get(url, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()
        if not data or "LawSearch" not in data or "law" not in data["LawSearch"]:
            return []

        law_list = data["LawSearch"]["law"]
        if isinstance(law_list, dict):
            law_list = [law_list]

        results = []

        for item in law_list:
            item_name = item.get("법령명한글", "정보 없음")
            law_serial = item.get("법령일련번호", "")

            encoded_name = urllib.parse.quote(item_name)
            link = f"https://www.law.go.kr/법령/{encoded_name}"

            unique_key = law_serial if law_serial else link

            results.append(
                {
                    "serial": unique_key,
                    "name": item_name,
                    "enforce_date": format_date(item.get("시행일자", "정보 없음")),
                    "link": link,
                }
            )

        return results

    except requests.exceptions.RequestException as e:
        print(f"법령 API 네트워크 오류: {e}")
        return []
    except ValueError:
        print("법령 API 응답이 올바른 JSON 형식이 아닙니다.")
        return []
    except Exception as e:
        print(f"법령 정보를 가져오는 중 예기치 않은 오류 발생: {e}")
        return []


def get_laws_by_keywords(keywords_list):
    """
    여러 개의 법령 키워드를 받아 멀티스레딩으로 빠르게 검색 결과를 취합합니다.
    """
    if not keywords_list:
        return []

    all_results = []

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=min(len(keywords_list), 10)
    ) as executor:
        futures = [executor.submit(get_law_group_info, name) for name in keywords_list]

        for future in concurrent.futures.as_completed(futures):
            try:
                infos = future.result()
                if infos:
                    all_results.extend(infos)
            except Exception as e:
                print(f"법령 그룹 병렬 검색 중 오류: {e}")

    return all_results
