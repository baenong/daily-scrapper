import feedparser
import ssl
from email.utils import parsedate_to_datetime

ssl._create_default_https_context = ssl._create_unverified_context


def get_policy_briefings(rss_urls, limit=30):
    all_entries = []

    if not rss_urls:
        return []

    for url in rss_urls:
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

                all_entries.append(
                    {
                        "title": entry.title,
                        "link": entry.link,
                        "published_dt": pub_dt,
                        "published_str": pub_dt.strftime("%Y-%m-%d %H:%M"),
                        "source": source_title,
                    }
                )
        except Exception as e:
            print(f"RSS 파싱 에러 ({url}): {e}")
            continue

    all_entries.sort(key=lambda x: x["published_dt"], reverse=True)

    return all_entries[:limit]
