import concurrent.futures
import feedparser
import urllib.parse
import requests
from email.utils import parsedate_to_datetime
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

session = requests.Session()
session.verify = False


def get_news_by_query(query_string, limit=15):

    if not query_string.strip():
        return []

    encoded_query = urllib.parse.quote(f"{query_string} when:30d")
    rss_url = (
        f"https://news.google.com/rss/search?q={encoded_query}&hl=ko&gl=KR&ceid=KR:ko"
    )

    news_list = []
    try:
        response = session.get(rss_url, timeout=10)
        response.raise_for_status()

        feed = feedparser.parse(response.content)
    except Exception as e:
        print(f"뉴스 RSS를 가져오는 중 오류 발생: {e}")
        return []

    for entry in feed.entries:
        try:
            published_raw = getattr(entry, "published", "")

            if not published_raw:
                continue

            pub_dt = parsedate_to_datetime(published_raw)

            source_info = entry.get("source", {})
            if hasattr(source_info, "title"):
                source_title = source_info.title
            elif isinstance(source_info, dict):
                source_title = source_info.get("title", "알 수 없는 출처")
            else:
                source_title = "알 수 없는 출처"

        except Exception:
            continue

        news_list.append(
            {
                "title": entry.title,
                "link": entry.link,
                "published_dt": pub_dt,
                "published_str": pub_dt.strftime("%Y-%m-%d"),
                "source": source_title,
            }
        )

    news_list.sort(key=lambda x: x["published_dt"], reverse=True)
    return news_list[:limit]


def get_news_by_or_query(selected_groups, limit=15):
    if not selected_groups:
        return []

    all_news = []
    seen_links = set()

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=min(len(selected_groups), 10)
    ) as executor:
        future_to_query = {
            executor.submit(get_news_by_query, query, limit=limit): query
            for query in selected_groups
        }

        for future in concurrent.futures.as_completed(future_to_query):
            try:
                results = future.result()
                if results:
                    for news in results:
                        if news["link"] not in seen_links:
                            seen_links.add(news["link"])
                            all_news.append(news)
            except Exception as e:
                query = future_to_query[future]
                print(f"[{query}] 뉴스 병렬 처리 중 오류 발생: {e}")

    all_news.sort(key=lambda x: x["published_dt"], reverse=True)
    return all_news[:limit]
