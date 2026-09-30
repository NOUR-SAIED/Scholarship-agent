"""Gemini (free tier) decides: which path is this, can a Tunisian actually get it,
how well does it fit. Falls back to rules when there's no key or quota runs out."""
import json
import re
import time
from datetime import date

import requests

from . import config
from .models import Opportunity
from .prefilter import SENIOR_TITLE, has_term

API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

SYSTEM = """You screen opportunities for one candidate. Candidate profile:
{profile}

For EACH opportunity decide:
- category: "remote" (work remotely from Tunisia), "relocation" (move abroad for a job),
  "early_career" (graduate program, traineeship, fellowship, internship, apprenticeship,
  alternance, young professionals program, funded bootcamp), "scholarship" (degree funding),
  or "irrelevant" (not something this candidate would apply to).
- badge: can THIS candidate (Tunisian citizen living in Tunisia) realistically be hired/accepted?
  "green"  = explicitly open worldwide, to Africa/MENA/Tunisia, or to all nationalities.
  "yellow" = probably open: EMEA/Europe-remote, contractor-friendly (Deel, Remote.com, invoicing),
             visa sponsorship or relocation package offered.
  "orange" = not stated either way.
  "red"    = blocked: requires US/UK/EU work authorization or residency, security clearance,
             citizens-only, or nationalization quota (Saudization, Emiratization, "nationals only").
    A US-based company is NOT automatically red. Only an explicit requirement makes it red.
      For relocation jobs, "green" needs an explicit signal (visa sponsorship, relocation package,
  international recruitment, "all nationalities"). An on-site job abroad that says nothing is "orange".
  She graduates in 2026 and will no longer be a student: internships or "stages" that require current
  enrollment (student status, convention de stage) are "orange" with that as a blocker, unless the
  posting explicitly accepts recent graduates.
- blockers: short list of the exact blocking or risky requirements (empty if none).
- seniority: "entry", "junior", "mid", "senior", or "unknown".
- skill_matches: candidate skills that appear in the posting.
- score: 0-100 overall fit for this candidate (eligibility weighs most, then seniority, then skills).
  red badge => score <= 15. senior roles => score <= 35.
- why: ONE sentence, addressed to the candidate ("you"), saying why it fits or doesn't.
- country: where the job/program is, or "Remote".
- deadline: application deadline as YYYY-MM-DD if stated, else null.
- paid: "yes", "no", or "unknown" (salary, stipend, grant, or fully funded counts as yes).
- visa_sponsorship: "yes", "no", or "unknown".
- timezone_note: working-hours requirement if any (e.g. "needs 4h overlap with EST"), else "".

Also: she is available from the date in "availability"; lower the score of anything that must start
clearly before then. Her background includes client-facing requirements gathering, so data/AI
consulting roles are a genuine fit, not a stretch.

Return ONLY a JSON array, one object per opportunity, each including its "id"."""


class GeminiError(RuntimeError):
    pass


_model_cache: dict[str, str] = {}
SKIP_MODEL_WORDS = ("preview", "exp", "image", "tts", "live", "audio", "embedding", "thinking", "robotics", "computer")


def _post(model: str, api_key: str, text: str, json_mode: bool) -> requests.Response:
    body = {"contents": [{"role": "user", "parts": [{"text": text}]}],
            "generationConfig": {"temperature": 0.1 if json_mode else 0.7}}
    if json_mode:
        body["generationConfig"]["responseMimeType"] = "application/json"
    return requests.post(API.format(model=model), params={"key": api_key}, json=body, timeout=90)


def _candidates(api_key: str) -> list[str]:
    """Your GEMINI_MODEL first, then Google's 'latest' aliases, then the newest listed Flash models."""
    names = []
    configured = config.get("GEMINI_MODEL")
    if configured:
        names.append(configured.removeprefix("models/"))
    names += ["gemini-flash-lite-latest", "gemini-flash-latest"]
    try:
        r = requests.get(API.split("/models/")[0] + "/models", params={"key": api_key, "pageSize": 1000}, timeout=30)
        listed = [m["name"].removeprefix("models/") for m in r.json().get("models", [])
                  if "generateContent" in m.get("supportedGenerationMethods", [])]
    except Exception:
        listed = []
    def version(n):
        m = re.search(r"(\d+(?:\.\d+)?)", n)
        return float(m.group(1)) if m else 0.0
    flash = [n for n in listed if "flash" in n and not any(w in n for w in SKIP_MODEL_WORDS)]
    flash.sort(key=lambda n: ("lite" in n, version(n)), reverse=True)  # lite = bigger free quota
    return list(dict.fromkeys(names + flash))


def resolve_model(api_key: str) -> str:
    """Finds a model this key can really use. Google sometimes lists models that return
    404 for new accounts, so each candidate is tested with a tiny request."""
    if api_key in _model_cache:
        return _model_cache[api_key]
    tried = []
    for name in _candidates(api_key)[:8]:
        r = _post(name, api_key, "Reply with OK.", json_mode=False)
        if r.ok:
            if tried:
                print(f"  [gemini] using model '{name}' (unavailable: {', '.join(tried)})")
            _model_cache[api_key] = name
            return name
        if r.status_code in (400, 401, 403) and "API key" in r.text:
            raise GeminiError("GEMINI_API_KEY is invalid. Create a new one in AI Studio.")
        tried.append(f"{name} ({r.status_code})")
    raise GeminiError("No usable Gemini model for this key. Tried: " + ", ".join(tried))


def call_gemini(prompt: str, api_key: str, json_mode: bool = True) -> str:
    model = resolve_model(api_key)
    for attempt in range(4):
        r = _post(model, api_key, prompt, json_mode)
        if r.status_code == 429:
            if "limit: 0" in r.text or "per day" in r.text.lower():
                raise GeminiError("daily quota exhausted")
            wait = 20 * (attempt + 1)
            print(f"  [gemini] rate limited, waiting {wait}s")
            time.sleep(wait)
            continue
        r.raise_for_status()
        parts = r.json()["candidates"][0]["content"]["parts"]
        return "".join(p.get("text", "") for p in parts if not p.get("thought"))
    raise GeminiError("still rate limited after retries")


def _extract_json_array(text: str) -> list:
    """Survives code fences and chatty preambles (a v0 failure point)."""
    text = text.strip()
    try:
        data = json.loads(text)
        return data if isinstance(data, list) else data.get("results", [data])
    except json.JSONDecodeError:
        m = re.search(r"\[.*\]", text, re.S)
        if not m:
            raise
        return json.loads(m.group(0))


def _clean_date(value) -> str | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10]).isoformat()
    except ValueError:
        return None


def _apply(opp: Opportunity, r: dict, by: str) -> Opportunity:
    opp.category = r.get("category") if r.get("category") in (*config.CATEGORIES, "irrelevant") else opp.category_hint
    opp.badge = r.get("badge") if r.get("badge") in config.BADGES else "orange"
    opp.blockers = [str(b) for b in (r.get("blockers") or [])][:5]
    opp.seniority = r.get("seniority") or "unknown"
    opp.skill_matches = [str(s) for s in (r.get("skill_matches") or [])][:10]
    try:
        opp.score = max(0, min(100, int(r.get("score", 0))))
    except (TypeError, ValueError):
        opp.score = 0
    opp.why = str(r.get("why") or "")[:300]
    opp.country = str(r.get("country") or opp.location or "")[:80]
    opp.deadline = _clean_date(r.get("deadline"))
    opp.paid = r.get("paid") or "unknown"
    opp.visa_sponsorship = r.get("visa_sponsorship") or "unknown"
    opp.timezone_note = str(r.get("timezone_note") or "")[:120]
    opp.classified_by = by
    return opp


def classify_rules(opp: Opportunity, profile: dict) -> Opportunity:
    text = f"{opp.title} {opp.location} {opp.description}".lower()
    blockers = []
    patterns = {
        "US work authorization required": r"authorized to work in the (us|united states)|us citizen|green card",
        "Security clearance": r"security clearance",
        "Nationals only": r"nationals only|saudization|emiratization|citizens only",
        "EU work permit required": r"eu (citizens|work permit) only|right to work in the (eu|uk)",
    }
    for label, pat in patterns.items():
        if re.search(pat, text):
            blockers.append(label)
    open_signals = re.search(r"worldwide|anywhere|all nationalities|non-eu|africa|mena|international (hires|candidates)", text)
    likely = re.search(r"visa|relocation|deel|remote\.com|contractor|emea", text)
    badge = "red" if blockers else "green" if open_signals else "yellow" if likely else "orange"
    skills = [s for s in profile["skills"] if has_term(s, text)]
    senior = bool(SENIOR_TITLE.search(opp.title)) or bool(re.search(r"\b([5-9]|1\d)\+? years", text))
    score = 30 + 5 * len(skills) + {"green": 25, "yellow": 15, "orange": 5, "red": -40}[badge]
    score = min(score, 35) if senior else score
    score = min(score, {"green": 70, "yellow": 60, "orange": 50, "red": 10}[badge])  # rules are a rough guess
    m = re.search(r"(20\d\d-\d\d-\d\d)", text)
    return _apply(opp, {
        "category": opp.category_hint or "remote", "badge": badge, "blockers": blockers,
        "seniority": "senior" if senior else "unknown", "skill_matches": skills,
        "score": score, "why": "Rule-based guess (no AI): check eligibility yourself.",
        "deadline": m.group(1) if m else None,
    }, by="rules")


FEEDBACK = """

The candidate's own decisions so far. Use them to calibrate "score" (not "badge"):
rank opportunities like the ones she saved/applied to higher, like the ones she skipped lower.
She was interested in: {liked}
She skipped: {skipped}"""


def feedback_block(history: list[dict]) -> str:
    """Turns past saves/skips into examples so scoring adapts to her taste."""
    def label(o):
        return f"{o.get('title', '')} @ {o.get('organization', '')} ({o.get('category', '')})"
    liked = [label(o) for o in history if o.get("status") in ("saved", "applied", "interview", "offer")]
    skipped = [label(o) for o in history if o.get("status") == "skipped"
               and o.get("classified_by") in ("gemini", "rules")
               and o.get("badge") != "red" and o.get("category") != "irrelevant"]
    if len(liked) + len(skipped) < 3:
        return ""
    return FEEDBACK.format(liked="; ".join(liked[-15:]) or "none yet", skipped="; ".join(skipped[-15:]) or "none yet")


def classify(opps: list[Opportunity], profile: dict, use_ai: bool = True, history: list[dict] | None = None) -> list[Opportunity]:
    api_key = config.get("GEMINI_API_KEY")
    if not (use_ai and api_key):
        if use_ai:
            print("  No GEMINI_API_KEY: using rule-based classification")
        return [classify_rules(o, profile) for o in opps]

    system = SYSTEM.format(profile=json.dumps(profile, ensure_ascii=False)) + feedback_block(history or [])
    if "She skipped" in system:
        print("  Using your saves/skips to personalize scoring")
    results, requests_made = [], 0
    for i in range(0, len(opps), config.AI_BATCH_SIZE):
        batch = opps[i:i + config.AI_BATCH_SIZE]
        if requests_made >= config.AI_MAX_REQUESTS:
            print(f"  Reached AI_MAX_REQUESTS; {len(opps) - i} left for the next run")
            break
        payload = [{
            "id": o.id, "title": o.title, "organization": o.organization, "location": o.location,
            "source": o.source, "source_hint": o.category_hint, "tags": o.tags[:10],
            "seniority_hint": o.seniority_hint, "description": o.description[:1800],
        } for o in batch]
        prompt = system + "\n\nOpportunities:\n" + json.dumps(payload, ensure_ascii=False)
        try:
            raw = call_gemini(prompt, api_key)
            requests_made += 1
            by_id = {str(r.get("id")): r for r in _extract_json_array(raw) if isinstance(r, dict)}
        except GeminiError as e:  # key/model/quota problem: stop, retry these tomorrow
            print(f"  [gemini] {e}. {len(opps) - i} opportunities left for the next run.")
            break
        except Exception as e:  # one bad batch: fall back to rules and keep going
            print(f"  [gemini] batch failed ({e}); using rules for this batch")
            results += [classify_rules(o, profile) for o in batch]
            continue
        for o in batch:
            results.append(_apply(o, by_id[o.id], "gemini") if o.id in by_id else classify_rules(o, profile))
        time.sleep(4)  # stay under the free-tier requests-per-minute limit
    return results
