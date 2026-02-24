import requests
import urllib.parse
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
API_KEY = ""


def format_date(date_str):
    if date_str and len(date_str) == 8 and date_str.isdigit():
        return f"{date_str[:4]}.{date_str[4:6]}.{date_str[6:]}"
    return date_str


def get_law_group_info(law_name):
    if not API_KEY:
        return []

    encoded_query = urllib.parse.quote(law_name)
    url = f"https://www.law.go.kr/DRF/lawSearch.do?OC={API_KEY}&target=eflaw&type=json&query={encoded_query}&nw=2,3"

    try:
        response = requests.get(url, verify=False)
        response.raise_for_status()
        data = response.json()

        results = []
        if "LawSearch" in data and "law" in data["LawSearch"]:
            law_list = data["LawSearch"]["law"]

            for item in law_list:
                item_name = item.get("법령명한글", "정보 없음")
                results.append(
                    {
                        "name": item_name,
                        "enforce_date": format_date(item.get("시행일자", "정보 없음")),
                        "link": "https://www.law.go.kr/법령/" + item_name,
                    }
                )
            return results

        print(f"'{law_name}'에 대한 검색 결과가 없거나 JSON 구조가 다릅니다.")
        print(f"참고용 서버 응답 데이터: {data}")
        return []

    except Exception as e:
        print(f"법령 정보를 가져오는 중 오류 발생: {e}")
        return []
