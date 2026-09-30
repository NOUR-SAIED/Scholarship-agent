# 🧭 Opportunity Radar

A personal agent that scans remote jobs, relocation roles, early-career programs and
scholarships every morning, checks whether a **Tunisian candidate can actually get them**,
and puts the results in a dashboard with an application tracker.

Runs for **$0/month**: GitHub Actions (scheduler), Gemini free tier (classification),
Supabase free tier (database), Streamlit Community Cloud (dashboard), Telegram (alerts).

## What it does

```
Himalayas ─┐
Jobicy     │                                     your saves/skips ──┐
Remotive   ├─► skip known ─► free pre-filter ─► Gemini (+feedback) ─► Supabase ─► Streamlit dashboard
Arbeitnow  │               (duplicates, not open   (path, eligibility,              └─► Telegram alerts
RSS feeds ─┘                to Tunisia, off-profile) blockers, fit, deadline)
```

Every opportunity gets an eligibility badge:

| Badge | Meaning |
|---|---|
| 🟢 Open to you | Explicitly worldwide, Africa/MENA, or all nationalities |
| 🟡 Likely open | EMEA-remote, contractor-friendly, visa sponsorship or relocation offered |
| 🟠 Unclear | Not stated. Worth a quick check |
| 🔴 Blocked | US/EU work authorization, clearance, or nationals-only quotas (Saudization, Emiratization) |

A US company is **not** blocked by default. Only an explicit legal requirement is.

## Try it in 2 minutes (no keys)

```bash
pip install -r requirements.txt
python -m src.pipeline --sample --no-ai
streamlit run app.py
```

## Run it for real

1. **Profile:** edit `profile.json` (skills, target roles, languages). The AI scores everything against it.
2. **Gemini key:** get a free key at https://aistudio.google.com/apikey. Copy `.env.example` to `.env` and fill it in.
   Check AI Studio for which models are on the free tier and set `GEMINI_MODEL` accordingly.
3. **Test locally:** `python -m src.pipeline --dry-run` fetches real sources and prints results without saving.
   Then `python -m src.pipeline` and `streamlit run app.py`.

## The dashboard

- **⚡ Triage:** new matches one at a time, best fit first. Save, Skip, or Later. Clearing 30 takes a few minutes.
- **Category tabs:** Remote, Relocation, Early-career programs, Scholarships, with filters for eligibility,
  fit, seniority, paid-only and passed deadlines.
- **📋 Tracker:** Saved → Applied → Interview → Offer, sorted by deadline, plus a list of everything the
  scan filtered out and why, so you can check it isn't throwing away good stuff.
- **Draft an application:** per opportunity, written from your real `experience` in `profile.json`.
- **Source health** (sidebar): how many items each source returned on the last run. ⚠️ means a source
  returned nothing, the kind of silent failure that broke v0.

**It learns from you.** Every save and skip is fed back to Gemini as examples on the next run, so
scores drift toward what you actually go for.

## Put it online

1. **Supabase** (free): create a project, run `supabase_schema.sql` in the SQL editor.
   Copy the project URL and the **service_role** key (Settings → API). Keep that key secret.
2. **GitHub repo secrets** (Settings → Secrets and variables → Actions):
   `GEMINI_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.
   Optional variables: `GEMINI_MODEL`, `DASHBOARD_URL`.
3. **Streamlit Community Cloud:** deploy `app.py` from the repo, and add the same keys plus
   `APP_PASSWORD` in the app's Secrets. The password matters: the dashboard can edit your data.
4. **Actions tab → Daily opportunity scan → Run workflow** to test. It then runs every day at 07:00 Tunis time.

## Commands

| Command | What it does |
|---|---|
| `python -m src.pipeline --sample --no-ai` | Offline demo data |
| `python -m src.pipeline --dry-run` | Real sources, print only |
| `python -m src.pipeline --only himalayas rss` | Just some sources |
| `python -m src.pipeline` | Full run: save + alert |

## Adding a source

Create `src/sources/yoursource.py` with a function returning `list[Opportunity]`, then register it in
`src/sources/__init__.py`. A failing source logs an error and returns `[]`, so it never breaks the run.

## Design notes (what broke in v0 and how it's fixed)

- **Empty feeds:** RSS sites blocked Python's default user agent and returned 0 entries silently.
  Now: browser headers, retries, and a visible warning when a feed returns nothing.
- **Lost alerts:** Telegram Markdown rejected titles containing `_`, `*` or `[`. Now: plain text.
- **AI silently skipped:** JSON parsing broke on any preamble. Now: robust extraction + per-batch rule fallback.
- **Free-tier limits:** opportunities are batched 8 per request, capped per run, and pre-filtered for free
  before reaching Gemini. Unprocessed items are simply picked up the next day.
- **Growing forever:** untouched items older than 60 days are pruned; anything you saved or applied to is kept.

## Roadmap

- Gulf job boards (Bayt, GulfTalent) and La Bonne Alternance
- Telegram buttons (save / skip / draft) that update the dashboard
