import feedparser
import urllib.parse
import ssl

ssl._create_default_https_context = ssl._create_unverified_context


def get_news_by_query(query_string, limit=5):

    # 구글 뉴스 RSS 피드 URL (한국어, 한국 지역 설정)
    if not query_string.strip():
        return []

    encoded_query = urllib.parse.quote(query_string)
    rss_url = (
        f"https://news.google.com/rss/search?q={encoded_query}&hl=ko&gl=KR&ceid=KR:ko"
    )

    # RSS 피드 파싱
    feed = feedparser.parse(rss_url)

    news_list = []
    # 위에서부터 지정한 수(limit)만큼만 기사를 추출합니다.
    for entry in feed.entries[:limit]:
        news_list.append(
            {
                "title": entry.title,
                "link": entry.link,
                "published": getattr(entry, "published", "날짜 없음"),
            }
        )

    return news_list
