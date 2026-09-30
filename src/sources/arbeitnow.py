"""Arbeitnow public API (mostly Germany/Europe, many relocation roles).
https://www.arbeitnow.com/api/job-board-api"""
from ..models import Opportunity, make_id
from ._http import get, strip_html

URL = "https://www.arbeitnow.com/api/job-board-api"
PAGES = 3


def fetch_arbeitnow() -> list[Opportunity]:
    out = []
    for page in range(1, PAGES + 1):
        try:
            data = get(URL, params={"page": page}).json().get("data", [])
        except Exception as e:
            print(f"  [arbeitnow] page {page} failed: {e}")
            break
        for j in data:
            remote = bool(j.get("remote"))
            out.append(Opportunity(
                id=make_id("arbeitnow", j.get("slug") or j.get("url", "")),
                source="Arbeitnow",
                title=j.get("title", "").strip(),
                organization=j.get("company_name", ""),
                url=j.get("url", ""),
                description=strip_html(j.get("description", "")),
                location=j.get("location", ""),
                posted_at=str(j.get("created_at", "")),
                category_hint="remote" if remote else "relocation",
                tags=(j.get("tags") or []) + (j.get("job_types") or []),
            ))
    return out
