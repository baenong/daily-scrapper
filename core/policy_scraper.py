import feedparser
import html
import concurrent.futures
from email.utils import parsedate_to_datetime
from core.network import global_session as session


def _fetch_single_policy_rss(url):
    """단일 RSS Parsing"""
    dept_entries = []
    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
        source_title = feed.feed.get("title", "정책브리핑")

        for entry in feed.entries:
            published_raw = getattr(entry, "published", "")
            if not published_raw:
                continue

            pub_dt = parsedate_to_datetime(published_raw)
            title = html.unescape(getattr(entry, "title", ""))

            dept_entries.append(
                {
                    "title": title,
                    "link": getattr(entry, "link", ""),
                    "published_dt": pub_dt,
                    "published_str": pub_dt.strftime("%Y-%m-%d %H:%M"),
                    "source": source_title,
                }
            )

        dept_entries.sort(key=lambda x: x["published_dt"], reverse=True)
        return dept_entries
    except Exception as e:
        print(f"[{url}] 정책 RSS 가져오는 중 오류 발생: {e}")
        return []


def get_policy_briefings(rss_urls, limit=15):
    if not rss_urls:
        return []

    dept_feeds = []

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=min(len(rss_urls), 10)
    ) as executor:
        futures = [executor.submit(_fetch_single_policy_rss, url) for url in rss_urls]

        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                dept_feeds.append(result)

    if not dept_feeds:
        return []

    guarantee = max(1, limit // len(dept_feeds))
    final_selection = []
    leftover_pool = []

    # 각 부처별 최저 갯수
    for dept_entries in dept_feeds:
        final_selection.extend(dept_entries[:guarantee])
        leftover_pool.extend(dept_entries[guarantee:])

    # 최저 갯수 제외한 나머지 브리핑 자료 추가
    remaining_slots = limit - len(final_selection)
    if remaining_slots > 0:
        leftover_pool.sort(key=lambda x: x["published_dt"], reverse=True)
        final_selection.extend(leftover_pool[:remaining_slots])

    final_selection.sort(key=lambda x: x["published_dt"], reverse=True)
    return final_selection[:limit]
