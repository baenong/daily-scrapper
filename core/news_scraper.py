import feedparser
import urllib.parse
import ssl
from email.utils import parsedate_to_datetime

ssl._create_default_https_context = ssl._create_unverified_context


def get_news_by_query(query_string, limit=15):

    if not query_string.strip():
        return []

    encoded_query = urllib.parse.quote(f"{query_string} when:30d")
    rss_url = (
        f"https://news.google.com/rss/search?q={encoded_query}&hl=ko&gl=KR&ceid=KR:ko"
    )

    feed = feedparser.parse(rss_url)
    news_list = []

    for entry in feed.entries:
        try:
            published_raw = getattr(entry, "published", "")

            if not published_raw:
                continue

            pub_dt = parsedate_to_datetime(published_raw)

        except Exception:
            continue

        news_list.append(
            {
                "title": entry.title,
                "link": entry.link,
                "published_dt": pub_dt,
                "published_str": pub_dt.strftime("%Y-%m-%d"),
                "source": entry.source.title,
            }
        )

    news_list.sort(key=lambda x: x["published_dt"], reverse=True)

    return news_list[:limit]
