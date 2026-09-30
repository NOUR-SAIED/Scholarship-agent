"""Jobicy public API, no key needed. Docs: https://github.com/Jobicy/remote-jobs-api"""
from ..models import Opportunity, make_id
from ._http import get, strip_html

URL = "https://jobicy.com/api/v2/remote-jobs"
# Pull a few focused slices instead of one generic list.
QUERIES = [
    {"count": 50, "industry": "data-science"},
    {"count": 50, "industry": "engineering", "tag": "python"},
    {"count": 30, "tag": "machine learning"},
]


def fetch_jobicy() -> list[Opportunity]:
    seen, out = set(), []
    for params in QUERIES:
        try:
            jobs = get(URL, params=params).json().get("jobs", [])
        except Exception as e:
            print(f"  [jobicy] {params} failed: {e}")
            continue
        for j in jobs:
            key = str(j.get("id") or j.get("url"))
            if key in seen:
                continue
            seen.add(key)
            out.append(Opportunity(
                id=make_id("jobicy", key),
                source="Jobicy",
                title=j.get("jobTitle", "").strip(),
                organization=j.get("companyName", ""),
                url=j.get("url", ""),
                description=strip_html(j.get("jobDescription") or j.get("jobExcerpt", "")),
                location=j.get("jobGeo", ""),
                posted_at=j.get("pubDate", ""),
                category_hint="remote",
                tags=[t for t in (j.get("jobIndustry") or []) if isinstance(t, str)],
                seniority_hint=j.get("jobLevel", ""),
            ))
    return out
