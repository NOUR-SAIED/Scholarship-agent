"""Remotive public API, no key needed. https://remotive.com/api/remote-jobs"""
from ..models import Opportunity, make_id
from ._http import get, strip_html

URL = "https://remotive.com/api/remote-jobs"
CATEGORIES = ["data", "software-dev", "ai-ml"]


def fetch_remotive() -> list[Opportunity]:
    seen, out = set(), []
    for cat in CATEGORIES:
        try:
            jobs = get(URL, params={"category": cat, "limit": 60}).json().get("jobs", [])
        except Exception as e:
            print(f"  [remotive] {cat} failed: {e}")
            continue
        for j in jobs:
            key = str(j.get("id"))
            if key in seen:
                continue
            seen.add(key)
            out.append(Opportunity(
                id=make_id("remotive", key),
                source="Remotive",
                title=j.get("title", "").strip(),
                organization=j.get("company_name", ""),
                url=j.get("url", ""),
                description=strip_html(j.get("description", "")),
                location=j.get("candidate_required_location", ""),
                posted_at=j.get("publication_date", ""),
                category_hint="remote",
                tags=j.get("tags") or [],
            ))
    return out
