import requests
import urllib.parse
import urllib3

# 내부망 SSL 인증서 경고 메시지를 숨깁니다.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
API_KEY = ""


def get_law_info(law_name):
    """
    국가법령정보센터 API(JSON 방식)를 사용하여 법령의 시행일자와 개정 정보를 가져옵니다.
    """
    if not API_KEY:
        print("API 키가 설정되지 않았습니다.")
        return None

    # 법령명을 URL에 맞게 인코딩합니다.
    encoded_query = urllib.parse.quote(law_name)
    url = f"https://www.law.go.kr/DRF/lawSearch.do?OC={API_KEY}&target=law&type=json&query={encoded_query}"

    try:
        response = requests.get(url, verify=False)
        response.raise_for_status()
        data = response.json()

        if "LawSearch" in data and "law" in data["LawSearch"]:
            law_list = data["LawSearch"]["law"]

            if len(law_list) > 0:
                first_law = law_list[0]

                info = {
                    "name": first_law.get("법령명한글", "정보 없음"),
                    "enforce_date": first_law.get("시행일자", "정보 없음"),
                    "revision_type": first_law.get("제개정구분명", "정보 없음"),
                    "link": "https://www.law.go.kr/법령/"
                    + first_law.get("법령명한글", "정보 없음"),
                }
                return info

        print(f"'{law_name}'에 대한 검색 결과가 없거나 JSON 구조가 다릅니다.")
        print(f"참고용 서버 응답 데이터: {data}")
        return None

    except Exception as e:
        print(f"법령 정보를 가져오는 중 오류 발생: {e}")
        return None
