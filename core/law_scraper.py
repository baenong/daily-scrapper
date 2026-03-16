import os
import requests
import urllib.parse
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def format_date(date_str):
    if date_str and len(date_str) == 8 and date_str.isdigit():
        return f"{date_str[:4]}.{date_str[4:6]}.{date_str[6:]}"
    return date_str


def get_law_group_info(law_name):
    api_key = os.environ.get("LAW_API_KEY", "")

    if not api_key:
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
        response = requests.get(url, params=params, verify=False)
        response.raise_for_status()
        data = response.json()
        results = []

        if "LawSearch" in data and "law" in data["LawSearch"]:

            law_list = data["LawSearch"]["law"]

            if isinstance(law_list, dict):
                law_list = [law_list]

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

        print(f"'{law_name}'에 대한 검색 결과가 없거나 JSON 구조가 다릅니다.")
        print(f"참고용 서버 응답 데이터: {data}")
        return []

    except Exception as e:
        print(f"법령 정보를 가져오는 중 오류 발생: {e}")
        return []
