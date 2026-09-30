"""Himalayas public API, no key needed. Each job carries a structured
locationRestrictions list (empty = hire from anywhere): the best eligibility
signal of all our sources."""
from ..models import Opportunity, make_id
from ._http import get, strip_html

URL = "https://himalayas.app/jobs/api/search"
QUERIES = ["data engineer", "data analyst", "machine learning", "python", "analytics engineer", "llm"]


def fetch_himalayas() -> list[Opportunity]:
    seen, out = set(), []
    for q in QUERIES:
        try:
            jobs = get(URL, params={"q": q, "sort": "recent"}).json().get("jobs", [])
        except Exception as e:
            print(f"  [himalayas] '{q}' failed: {e}")
            continue
        for j in jobs:
            key = str(j.get("guid") or j.get("applicationLink") or j.get("title"))
            if key in seen:
                continue
            seen.add(key)
            restrictions = [str(x) for x in (j.get("locationRestrictions") or [])]
            seniority = j.get("seniority") or []
            out.append(Opportunity(
                id=make_id("himalayas", key),
                source="Himalayas",
                title=(j.get("title") or "").strip(),
                organization=j.get("companyName", ""),
                url=j.get("applicationLink") or j.get("guid") or "",
                description=strip_html(j.get("description") or j.get("excerpt", "")),
                location=", ".join(restrictions) if restrictions else "Worldwide",
                allowed_countries=restrictions,
                posted_at=str(j.get("pubDate", "")),
                category_hint="remote",
                tags=[str(c) for c in (j.get("categories") or [])][:10],
                seniority_hint=", ".join(seniority) if isinstance(seniority, list) else str(seniority),
            ))
    return out
