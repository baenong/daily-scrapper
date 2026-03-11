import feedparser
import ssl
from email.utils import parsedate_to_datetime

ssl._create_default_https_context = ssl._create_unverified_context


def get_policy_briefings(rss_urls, limit=15, min_guarantee=5):
    if not rss_urls:
        return []

    dept_feeds = []

    for url in rss_urls:
        dept_entries = []
        try:
            feed = feedparser.parse(url)
            source_title = feed.feed.get("title", "정책브리핑")

            for entry in feed.entries:
                try:
                    published_raw = getattr(entry, "published", "")
                    if not published_raw:
                        continue
                    pub_dt = parsedate_to_datetime(published_raw)
                except Exception:
                    continue

                # 특수문자 보정
                title = str(entry.title).replace("&middot;", "·")
                title.replace("&quot;", '"')

                dept_entries.append(
                    {
                        "title": title,
                        "link": entry.link,
                        "published_dt": pub_dt,
                        "published_str": pub_dt.strftime("%Y-%m-%d %H:%M"),
                        "source": source_title,
                    }
                )

            dept_entries.sort(key=lambda x: x["published_dt"], reverse=True)
            dept_feeds.append(dept_entries)

        except Exception as e:
            print(f"RSS 파싱 에러 ({url}): {e}")
            continue

    final_selection = []

    # 각 부처별 최저 갯수
    for dept_entries in dept_feeds:
        guaranteed_chunk = dept_entries[:min_guarantee]
        final_selection.extend(guaranteed_chunk)
        del dept_entries[:min_guarantee]

    # 최저 갯수 제외한 나머지 브리핑 자료 추가
    leftover_pool = []
    for dept_entries in dept_feeds:
        leftover_pool.extend(dept_entries)
    leftover_pool.sort(key=lambda x: x["published_dt"], reverse=True)

    remaining_slots = limit - len(final_selection)
    if remaining_slots > 0:
        final_selection.extend(leftover_pool[:remaining_slots])

    final_selection.sort(key=lambda x: x["published_dt"], reverse=True)

    return final_selection[:limit]
