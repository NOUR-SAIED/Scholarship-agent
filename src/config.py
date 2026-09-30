"""Central settings. Reads .env locally, environment variables in GitHub Actions,
and Streamlit secrets when running on Streamlit Cloud."""
import json
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def get(name: str, default: str = "") -> str:
    value = os.environ.get(name)
    if value:
        return value
    try:  # Streamlit Cloud stores secrets here instead of env vars
        import streamlit as st
        return str(st.secrets.get(name, default))
    except Exception:
        return default


def load_profile() -> dict:
    with open(ROOT / "profile.json", encoding="utf-8") as f:
        return json.load(f)



# Browser-like headers: many WordPress/Cloudflare sites return empty feeds to
# python's default user agent. This was the main silent failure in v0.
HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept": "application/json, application/rss+xml, application/xml, text/html;q=0.9, */*;q=0.8",
}

CATEGORIES = {
    "remote": "🌍 Remote",
    "relocation": "✈️ Relocation",
    "early_career": "🚀 Early-career programs",
    "scholarship": "💰 Scholarships",
}

CATEGORIES = {
    "remote": "Remote",
    "relocation": "Relocation",
    "early_career": "Early-career programs",
    "scholarship": "Scholarships",
}

BADGES = {
    "green": "Open to you",
    "yellow": "Likely open",
    "orange": "Unclear",
    "red": "Blocked",
}

# Terminal and Telegram only; the dashboard uses colors instead.
BADGE_ICONS = {"green": "🟢", "yellow": "🟡", "orange": "🟠", "red": "🔴"}

STATUSES = ["new", "saved", "applied", "interview", "offer", "rejected", "skipped"]

# Tuning
AI_BATCH_SIZE = 8          # opportunities per Gemini request
AI_MAX_REQUESTS = int(os.environ.get("AI_MAX_REQUESTS", "12"))  # per run, stays in free quota
ALERT_MIN_SCORE = 75       # Telegram alert threshold
KEEP_DAYS = 60             # prune untouched items older than this
