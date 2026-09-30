"""Free, instant filtering before spending any Gemini quota."""
import re

from .models import Opportunity

# Location strings that mean "you can't apply from Tunisia" on remote boards.
EXCLUSIVE_REGIONS = [
    r"\busa?\b( only)?", r"united states", r"\bcanada\b", r"\buk\b( only)?", r"united kingdom",
    r"north america", r"\bamericas\b", r"\blatam\b", r"latin america", r"\bapac\b",
    r"australia", r"new zealand", r"\bindia\b", r"brazil", r"philippines", r"mexico",
]
OPEN_WORDS = [
    "anywhere", "worldwide", "global", "international", "emea", "africa", "tunisia",
    "mena", "middle east", "north africa", "cet", "gmt+1", "utc+1",
]
SENIOR_TITLE = re.compile(r"\b(senior|sr\.?|staff|principal|lead|head of|director|vp|architect|manager)\b", re.I)
PROGRAM_WORDS = re.compile(
    r"scholarship|fellowship|traineeship|internship|graduate|program|programme|bootcamp|"
    r"apprentice|alternance|residency|young professional|funded|grant|master", re.I)


def has_term(term: str, text: str) -> bool:
    """Whole-word match that also works for terms like 'ci/cd' or 'power bi'."""
    return re.search(rf"(?<![a-z0-9]){re.escape(term.lower())}(?![a-z0-9])", text) is not None


GERMAN_WORDS = re.compile(r"\b(und|der|die|das|wir|mit|f\u00fcr|sie|ist|eine?|zu|auf|bei|oder|nicht|unsere?|deine?|ihre?|werden|sowie|du|dich|dein)\b")
ENGLISH_WORDS = re.compile(r"\b(and|the|with|for|you|we|our|to|of|in|is|are|will|your)\b")
REQUIRES_GERMAN = re.compile(
    r"(fluent|native|business|good|very good|excellent|strong|professional)[\s-]+(level\s+)?(of\s+|command of\s+)?german"
    r"|german\s*(language\s*)?\(?\s*(b2|c1|c2)|deutschkenntnisse|verhandlungssicher|flie\u00dfend(e)?\s+deutsch", re.I)


def language_reason(opp: Opportunity, profile: dict) -> str:
    """Drops German-language postings (almost always require German) unless the
    profile lists German above beginner level."""
    if any("german" in l.lower() and "beginner" not in l.lower() for l in profile.get("languages", [])):
        return ""
    text = f"{opp.title} {opp.description[:3000]}"
    if REQUIRES_GERMAN.search(text):
        return "Requires German"
    low = text.lower()
    de, en = len(GERMAN_WORDS.findall(low)), len(ENGLISH_WORDS.findall(low))
    if de >= 12 and de > 1.5 * en:
        return "Posting is in German (likely requires German)"
    return ""


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


REMOTE_WITHIN = re.compile(
    r"remote\s*(?:only\s*)?(?:within|in|from|across)\s+(?:the\s+)?([a-z][a-z .&-]{2,30}?)(?=[),.;:/|]|\s-|$)", re.I)


def location_reason(opp: Opportunity) -> str:
    """Returns why a remote job is out of reach from Tunisia, or '' if it isn't."""
    if opp.category_hint != "remote":
        return ""
    if opp.allowed_countries:  # structured data (Himalayas): trust it
        joined = " ".join(opp.allowed_countries).lower()
        if any(w in joined for w in OPEN_WORDS):
            return ""
        return "Hires only in: " + ", ".join(opp.allowed_countries[:4])
    m = REMOTE_WITHIN.search(f"{opp.title} | {opp.description[:300]}")
    if m:
        place = m.group(1).strip().lower()
        if not any(w in place for w in OPEN_WORDS + ["europe", "eu ", "timezone", "time zone", "the world"]):
            return f"Remote only within {m.group(1).strip().title()}"
    loc = (opp.location or "").lower().strip()
    if not loc or any(w in loc for w in OPEN_WORDS) or "europe" in loc:
        return ""
    if any(re.search(p, loc) for p in EXCLUSIVE_REGIONS):
        return f"Remote only for: {opp.location}"
    return ""


DATA_TITLE = re.compile(
    r"\b(data|analytics?|analyst|bi|business intelligence|etl|elt|ml|machine learning|ai|llm|nlp|genai|"
    r"scientist|dbt|spark|warehouse|lakehouse|insights?|reporting|mlops|dataops|big data|decision)\b", re.I)


def relevance(opp: Opportunity, profile: dict) -> int:
    """Rough keyword score: decides what's worth sending to Gemini, and in what order."""
    text = f"{opp.title} {' '.join(map(str, opp.tags))} {opp.description[:1500]}".lower()
    title = opp.title.lower()
    score = sum(4 for r in profile["target_roles"] if has_term(r, title))
    score += sum(1 for r in profile["target_roles"] if has_term(r, text))
    score += sum(1 for s in profile["skills"] if has_term(s, text))
    if opp.category_hint in ("scholarship", "early_career"):
        score += 4 if PROGRAM_WORDS.search(text) else -5
    elif not (DATA_TITLE.search(opp.title) or any(has_term(r, title) for r in profile["target_roles"])):
        return 0  # a job whose title isn't a data/AI role: skip, however many keywords it mentions
    if re.search(r"\b(junior|entry|graduate|intern|trainee|new grad)\b", text):
        score += 3
    if SENIOR_TITLE.search(opp.title):
        score -= 5
    return score


def prefilter(opps: list[Opportunity], profile: dict):
    """Returns (to_classify, dropped, stats). Dropped items are saved as 'skipped'
    so they aren't re-counted as new on every run."""
    stats = {"duplicate": 0, "location": 0, "language": 0, "off_profile": 0}
    kept, dropped, seen_keys = [], [], set()
    for o in opps:
        if not o.title or not o.url:
            continue
        dup_key = (_norm(o.title), _norm(o.organization))
        if dup_key in seen_keys:  # same job listed on several boards
            stats["duplicate"] += 1
            continue
        seen_keys.add(dup_key)
        reason = location_reason(o)
        if reason:
            stats["location"] += 1
            o.blockers, o.badge = [reason], "red"
            dropped.append(o)
            continue
        reason = language_reason(o, profile)
        if reason:
            stats["language"] += 1
            o.blockers, o.badge = [reason], "red"
            dropped.append(o)
            continue
        r = relevance(o, profile)
        if r <= 0:
            stats["off_profile"] += 1
            o.blockers, o.badge = ["Doesn't match your target roles or skills"], "orange"
            dropped.append(o)
            continue
        kept.append((r, o))
    kept.sort(key=lambda x: x[0], reverse=True)
    per_company, capped, deferred = {}, [], 0
    for r, o in kept:
        org = _norm(o.organization)
        if o.category_hint in ("remote", "relocation") and per_company.get(org, 0) >= 3:
            deferred += 1  # not saved, so it comes back tomorrow
            continue
        per_company[org] = per_company.get(org, 0) + 1
        capped.append((r, o))
    kept, stats["deferred"] = capped, deferred
    for o in dropped:
        o.category, o.status, o.classified_by, o.description = "irrelevant", "skipped", "prefilter", ""
    return [o for _, o in kept], dropped, stats