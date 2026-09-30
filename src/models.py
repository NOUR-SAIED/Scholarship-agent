"""One shape for every opportunity, whatever the source."""
import hashlib
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


def make_id(source: str, key: str) -> str:
    return hashlib.sha1(f"{source}:{key}".encode()).hexdigest()[:16]


@dataclass
class Opportunity:
    id: str
    source: str
    title: str
    organization: str
    url: str
    description: str = ""
    location: str = ""
    posted_at: str = ""
    category_hint: str = ""        # what the source suggests: remote / relocation / ...
    tags: list = field(default_factory=list)
    seniority_hint: str = ""
    allowed_countries: list = field(default_factory=list)  # structured restriction, [] = unknown/anywhere

    # Filled by the classifier
    category: str = ""
    badge: str = ""
    blockers: list = field(default_factory=list)
    seniority: str = "unknown"
    skill_matches: list = field(default_factory=list)
    score: int = 0
    why: str = ""
    country: str = ""
    deadline: str | None = None
    paid: str = "unknown"
    visa_sponsorship: str = "unknown"
    timezone_note: str = ""
    classified_by: str = ""

    # Tracking
    status: str = "new"
    notes: str = ""
    found_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_record(self) -> dict:
        d = asdict(self)
        d.pop("category_hint", None)
        d.pop("seniority_hint", None)
        d.pop("allowed_countries", None)
        return d
