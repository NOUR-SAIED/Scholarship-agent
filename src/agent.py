"""
ScholarAgent — Fully automated scholarship finder for Tunisian students
Runs daily via GitHub Actions. Free. No server needed.

Sources: Scholars4Dev, Euraxess, AfterSchool Africa, Opportunities Circle, DAAD, and more.
Filtering: Google Gemini 1.5 Flash (free tier)
Notifications: Telegram Bot API (free)
Storage: JSON file committed to repo (or Google Sheets if configured)
"""

import os
import json
import time
import hashlib
import logging
import datetime
import requests
import feedparser
from typing import Optional
from bs4 import BeautifulSoup

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("ScholarAgent")

# ── Load profile from environment / profile.json ───────────────────────────────
def load_profile() -> dict:
    """Load profile from profile.json (committed to repo, no secrets there)."""
    path = os.path.join(os.path.dirname(__file__), "..", "profile.json")
    with open(path) as f:
        return json.load(f)

# ── Data sources ───────────────────────────────────────────────────────────────
RSS_FEEDS = [
    {
        "name": "Scholars4Dev",
        "url": "https://www.scholars4dev.com/feed/",
        "tags": ["masters", "phd", "scholarship", "fellowship"],
    },
    {
        "name": "Opportunities for Africans",
        "url": "https://www.opportunitiesforafricans.com/feed/",
        "tags": ["africa", "scholarship", "fully funded"],
    },
    {
        "name": "AfterSchool Africa",
        "url": "https://afterschoolafrica.com/feed/",
        "tags": ["alternance", "apprenticeship", "scholarship"],
    },
    {
        "name": "Opportunities Circle",
        "url": "https://opportunitiescircle.com/feed/",
        "tags": ["masters", "scholarship", "internship"],
    },
    {
        "name": "UN Jobs & Fellowships",
        "url": "https://www.unjoblist.org/feed/",
        "tags": ["fellowship", "internship", "un"],
    },
]

SCRAPE_TARGETS = [
    {
        "name": "Euraxess",
        "url": "https://euraxess.ec.europa.eu/jobs/search",
        "note": "Requires Selenium — skipped in basic mode",
        "skip": True,
    },
]

# Keywords that strongly suggest full funding
FUNDED_KEYWORDS = [
    "fully funded", "full scholarship", "full funding", "tuition waiver",
    "stipend", "monthly allowance", "living allowance", "travel grant",
    "all expenses", "bourse complète", "بورسة كاملة",
]

# Keywords that indicate partial or no funding (filter out)
UNFUNDED_KEYWORDS = [
    "partial scholarship", "tuition only", "no funding", "self-funded",
    "not funded", "unpaid",
]

# ── RSS Feed fetcher ───────────────────────────────────────────────────────────
def fetch_rss(feed: dict) -> list[dict]:
    """Parse an RSS feed and return normalized opportunity dicts."""
    log.info(f"  Fetching {feed['name']} ...")
    try:
        parsed = feedparser.parse(feed["url"])
        items = []
        for entry in parsed.entries[:30]:  # cap at 30 per source
            text = (entry.get("title", "") + " " + entry.get("summary", "")).lower()

            # Basic pre-filter: must mention scholarship/funding keywords
            if not any(kw in text for kw in ["scholarship", "fellowship", "bourse",
                                              "funded", "grant", "alternance",
                                              "apprenticeship", "master"]):
                continue

            opp = {
                "id": hashlib.md5(entry.get("link", entry.get("title", "")).encode()).hexdigest()[:12],
                "title": entry.get("title", "Untitled").strip(),
                "link": entry.get("link", ""),
                "summary": BeautifulSoup(entry.get("summary", ""), "html.parser").get_text()[:600],
                "published": entry.get("published", ""),
                "source": feed["name"],
                "raw_text": text,
            }
            items.append(opp)

        log.info(f"  → {len(items)} candidates from {feed['name']}")
        return items

    except Exception as e:
        log.warning(f"  Failed to fetch {feed['name']}: {e}")
        return []


def fetch_all_sources() -> list[dict]:
    """Fetch from all RSS sources and deduplicate."""
    all_items = []
    seen_ids = set()

    for feed in RSS_FEEDS:
        items = fetch_rss(feed)
        for item in items:
            if item["id"] not in seen_ids:
                seen_ids.add(item["id"])
                all_items.append(item)
        time.sleep(1)  # be polite

    log.info(f"Total raw candidates: {len(all_items)}")
    return all_items

# ── Pre-filter (fast, no API call) ────────────────────────────────────────────
def pre_filter(opportunity: dict, profile: dict) -> tuple[bool, str]:
    text = opportunity["raw_text"]

    # Still block explicitly unfunded ones
    if any(kw in text for kw in UNFUNDED_KEYWORDS):
        return False, "Mentions partial/no funding"

    # Allow anything that mentions "scholarship" or "fellowship"
    if "scholarship" in text or "fellowship" in text:
        return True, "Passes relaxed filter"

    # Otherwise, let it through anyway for testing
    return True, "Passes relaxed filter"


# ── Gemini AI filter ───────────────────────────────────────────────────────────
def filter_with_gemini(opportunity: dict, profile: dict, api_key: str) -> dict:
    """
    Use Gemini 1.5 Flash to check eligibility against profile.
    Returns dict with keys: eligible, score, reason, highlights, deadline.
    """
    prompt = f"""You are a scholarship eligibility checker for a Tunisian student.

STUDENT PROFILE:
- Nationality: {profile['nationality']}
- Current degree: {profile['current_degree']}
- Field of study: {profile['field']}
- GPA: {profile['gpa']}/20
- Languages: {', '.join(profile['languages'])}
- Target programs: {', '.join(profile['target_degrees'])}
- Preferred countries: {', '.join(profile.get('countries', ['Any']))}

OPPORTUNITY:
Title: {opportunity['title']}
Source: {opportunity['source']}
Link: {opportunity['link']}
Summary: {opportunity['summary'][:500]}

TASK: Analyze eligibility carefully. Check:
1. Is this opportunity open to Tunisian nationals?
2. Is it fully funded (tuition + living allowance)?
3. Does it match the target degree type?
4. Is the field relevant or open to all fields?
5. Extract the application deadline if mentioned.

Respond ONLY with valid JSON, no markdown:
{{"eligible": true/false, "score": 0-100, "reason": "1-2 sentences", "highlights": ["benefit1", "benefit2"], "deadline": "YYYY-MM-DD or null", "country": "country name or null", "funding_type": "Fully Funded / Partially Funded / Unknown"}}"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 400},
    }

    try:
        resp = requests.post(url, json=payload, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        text = text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)

    except json.JSONDecodeError:
        log.warning(f"  Gemini returned non-JSON for: {opportunity['title'][:40]}")
        return _rule_based_filter(opportunity, profile)
    except Exception as e:
        log.warning(f"  Gemini API error: {e} — falling back to rules")
        return _rule_based_filter(opportunity, profile)


def _rule_based_filter(opportunity: dict, profile: dict) -> dict:
    """Fallback when Gemini is unavailable."""
    text = opportunity["raw_text"]
    nat = profile["nationality"].lower()

    nat_ok = (
        nat in text or
        "all nationalities" in text or
        "international students" in text or
        "developing countries" in text or
        "africa" in text or
        "mena" in text
    )
    funded = any(kw in text for kw in FUNDED_KEYWORDS)
    type_match = any(t.lower() in text for t in profile["target_degrees"])

    eligible = nat_ok and funded and type_match
    score = sum([nat_ok * 40, funded * 40, type_match * 20])

    return {
        "eligible": eligible,
        "score": score,
        "reason": "Rule-based: " + (
            "Matches nationality, funding, and degree type." if eligible
            else f"Missing: {'nationality' if not nat_ok else ''} {'funding' if not funded else ''} {'degree type' if not type_match else ''}".strip()
        ),
        "highlights": ["Fully funded" if funded else "Check funding", "Open to your nationality" if nat_ok else ""],
        "deadline": None,
        "country": None,
        "funding_type": "Fully Funded" if funded else "Unknown",
    }

# ── Storage ────────────────────────────────────────────────────────────────────
RESULTS_FILE = os.path.join(os.path.dirname(__file__), "..", "results", "opportunities.json")
SEEN_FILE = os.path.join(os.path.dirname(__file__), "..", "results", "seen_ids.json")

def load_seen_ids() -> set:
    os.makedirs(os.path.dirname(SEEN_FILE), exist_ok=True)
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f:
            return set(json.load(f))
    return set()

def save_seen_ids(ids: set):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(ids), f)

def load_results() -> list:
    if os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE) as f:
            return json.load(f)
    return []

def save_results(results: list):
    os.makedirs(os.path.dirname(RESULTS_FILE), exist_ok=True)
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

# ── Telegram notification ──────────────────────────────────────────────────────
def send_telegram(token: str, chat_id: str, eligible: list, profile: dict):
    """Send a Telegram message summarizing new eligible opportunities."""
    if not eligible:
        return

    date_str = datetime.date.today().strftime("%d %b %Y")
    lines = [f"🎓 *ScholarAgent Report — {date_str}*\n"]
    lines.append(f"Found *{len(eligible)} new eligible opportunities* for {profile['name']}:\n")

    for i, opp in enumerate(eligible[:5], 1):
        score = opp.get("score", "?")
        deadline = opp.get("deadline") or "Check site"
        lines.append(f"*{i}. {opp['title'][:60]}*")
        lines.append(f"   📍 {opp.get('country', opp['source'])}  |  Score: {score}/100")
        lines.append(f"   ⏰ Deadline: {deadline}")
        lines.append(f"   🔗 {opp['link'][:80]}\n")

    if len(eligible) > 5:
        lines.append(f"_...and {len(eligible) - 5} more. Check results/opportunities.json in your repo._")

    lines.append("\n_Powered by ScholarAgent — 100% free_")
    message = "\n".join(lines)

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown", "disable_web_page_preview": True}

    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        log.info("✓ Telegram notification sent")
    except Exception as e:
        log.error(f"Telegram failed: {e}")

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    log.info("=" * 55)
    log.info("  ScholarAgent starting")
    log.info(f"  {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log.info("=" * 55)

    # Load config
    profile = load_profile()
    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

    if not gemini_key:
        log.warning("No GEMINI_API_KEY found — using rule-based filtering")

    log.info(f"Profile: {profile['name']} | {profile['nationality']} | {profile['field']}")
    log.info(f"Targets: {', '.join(profile['target_degrees'])}")

    # Load already-seen IDs to avoid re-notifying
    seen_ids = load_seen_ids()
    existing_results = load_results()
    existing_ids = {r["id"] for r in existing_results}

    log.info(f"Previously seen: {len(seen_ids)} opportunities")

    # Fetch all sources
    log.info("\n── Fetching sources ──────────────────────────────────")
    raw = fetch_all_sources()

    # Filter to only NEW ones
    new_opps = [o for o in raw if o["id"] not in seen_ids]
    log.info(f"New (unseen) candidates: {len(new_opps)}")

    if not new_opps:
        log.info("No new opportunities found. Done.")
        return

    # Pre-filter
    log.info("\n── Pre-filtering ─────────────────────────────────────")
    pre_passed = []
    for opp in new_opps:
        passed, reason = pre_filter(opp, profile)
        if passed:
            pre_passed.append(opp)
        else:
            log.debug(f"  ✗ {opp['title'][:50]} — {reason}")

    log.info(f"Passed pre-filter: {len(pre_passed)} / {len(new_opps)}")

    # AI filter
    log.info("\n── AI eligibility check ──────────────────────────────")
    newly_eligible = []
    all_filtered = []

    for i, opp in enumerate(pre_passed):
        log.info(f"  [{i+1}/{len(pre_passed)}] {opp['title'][:55]}")

        if gemini_key:
            result = filter_with_gemini(opp, profile, gemini_key)
            time.sleep(0.5)  # respect rate limits
        else:
            result = _rule_based_filter(opp, profile)

        enriched = {
            **opp,
            "eligible": result["eligible"],
            "score": result.get("score", 0),
            "reason": result.get("reason", ""),
            "highlights": result.get("highlights", []),
            "deadline": result.get("deadline"),
            "country": result.get("country"),
            "funding_type": result.get("funding_type", "Unknown"),
            "checked_at": datetime.datetime.now().isoformat(),
        }

        all_filtered.append(enriched)

        if result["eligible"]:
            log.info(f"  ✓ ELIGIBLE — score {result.get('score', '?')}/100")
            newly_eligible.append(enriched)
        else:
            log.info(f"  ✗ Not eligible — {result.get('reason', '')[:60]}")

        seen_ids.add(opp["id"])

    log.info(f"\nNewly eligible: {len(newly_eligible)}")

    # Save
    log.info("\n── Saving results ────────────────────────────────────")
    updated_results = existing_results + all_filtered
    save_results(updated_results)
    save_seen_ids(seen_ids)
    log.info(f"Saved {len(updated_results)} total results to results/opportunities.json")

    # Notify
    if telegram_token and telegram_chat_id and newly_eligible:
        log.info("\n── Sending Telegram notification ─────────────────────")
        send_telegram(telegram_token, telegram_chat_id, newly_eligible, profile)
    elif newly_eligible:
        log.info("\nℹ  Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to receive notifications")

    # Summary
    log.info("\n" + "=" * 55)
    log.info(f"  DONE — {len(newly_eligible)} new eligible opportunities")
    log.info("=" * 55)

    # Print top results to GitHub Actions log
    if newly_eligible:
        log.info("\nTop matches:")
        for opp in sorted(newly_eligible, key=lambda x: x["score"], reverse=True)[:5]:
            log.info(f"  [{opp['score']:3d}] {opp['title'][:60]}")
            log.info(f"        {opp['link']}")

if __name__ == "__main__":
    main()
