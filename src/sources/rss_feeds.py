"""Scholarship / program / fellowship blogs (WordPress). Fetched with browser
headers, with a fallback feed URL, and a clear message when a site serves a
bot-protection page instead of the feed."""
import feedparser

from ..models import Opportunity, make_id
from ._http import get, strip_html

# (name, [feed URLs, tried in order], category hint)
FEEDS = [
    ("Opportunity Desk", ["https://opportunitydesk.org/feed/"], "early_career"),

    ("Opportunities Circle", ["https://www.opportunitiescircle.com/feed/"], "early_career"),
]
# Blocked from home connections in Sept 2026 (empty feed / bot protection). Uncomment to retry:
# ("Scholars4Dev", ["https://www.scholars4dev.com/feed/"], "scholarship"),
# ("After School Africa", ["https://www.afterschoolafrica.com/feed/"], "scholarship"),


def _fetch_feed(urls: list[str]):
    problem = ""
    for url in urls:
        try:
            r = get(url)
        except Exception as e:
            problem = f"request failed ({e})"
            continue
        parsed = feedparser.parse(r.content)
        if parsed.entries:
            return parsed.entries, ""
        head = r.content[:600].lower()
        if b"<html" in head or b"cloudflare" in head or b"challenge" in head:
            problem = "site returned a web page instead of the feed (bot protection)"
        else:
            problem = f"feed is empty (HTTP {r.status_code})"
    return [], problem


def fetch_rss() -> list[Opportunity]:
    out, seen = [], set()
    for name, urls, hint in FEEDS:
        entries, problem = _fetch_feed(urls)
        if problem:
            print(f"  [rss] {name}: {problem}")
        for e in entries[:30]:
            link = e.get("link", "")
            if link in seen:  # the Africa category repeats some main-feed posts
                continue
            seen.add(link)
            summary = e.get("summary", "") or ""
            if e.get("content"):
                summary = e["content"][0].get("value", summary)
            out.append(Opportunity(
                id=make_id("rss", link or e.get("title", "")),
                source=name.split(" (")[0],
                title=e.get("title", "").strip(),
                organization=name.split(" (")[0],
                url=link,
                description=strip_html(summary),
                posted_at=e.get("published", ""),
                category_hint=hint,
                tags=[t.get("term", "") for t in e.get("tags", [])],
            ))
    return out
