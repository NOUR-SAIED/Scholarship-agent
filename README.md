# 🎓 ScholarAgent

Fully automated scholarship finder for Tunisian students. Scans 5+ sources daily,
filters opportunities using Gemini AI, and sends Telegram notifications.
**100% free. No server. No credit card.**

---

## ✨ What it does

- Scans **Scholars4Dev, AfterSchool Africa, Opportunities Circle, Opportunities for Africans, UN Jobs** every day at 08:00 UTC
- Pre-filters by keyword (fully funded, masters, alternance…)
- Sends each candidate to **Gemini 1.5 Flash** (free) for intelligent eligibility checking against your profile
- Falls back to rule-based filtering if no Gemini key is set
- Sends you a **Telegram message** with new eligible opportunities
- Commits results to `results/opportunities.json` in your repo

---

## 🚀 Setup (15 minutes)

### Step 1 — Fork this repository

Click **Fork** at the top right of this page. This creates your own copy where the workflow will run.

---

### Step 2 — Edit your profile

Open `profile.json` and fill in your details:

```json
{
  "name": "Your Name",
  "nationality": "Tunisian",
  "current_degree": "Bachelor",
  "field": "Computer Science",
  "gpa": "15",
  "languages": ["Arabic", "French", "English"],
  "target_degrees": ["Masters", "Alternance", "Apprenticeship"],
  "countries": ["France", "Germany", "Europe", "Turkey"],
  "notes": "Any extra context for the AI filter"
}
```

Commit and push the change.

---

### Step 3 — Get a free Gemini API key

1. Go to [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Click **Create API key**
3. Copy the key (starts with `AIza…`)

> Gemini 1.5 Flash free tier: 15 requests/minute, 1500/day — more than enough.

---

### Step 4 — Set up Telegram notifications (optional but recommended)

**Create a bot:**
1. Open Telegram → search **@BotFather**
2. Send `/newbot` → follow prompts → copy the **bot token** (looks like `123456:ABC-DEF…`)

**Get your chat ID:**
1. Search **@userinfobot** in Telegram → send any message → copy your **id** number

---

### Step 5 — Add secrets to GitHub

In your forked repo: **Settings → Secrets and variables → Actions → New repository secret**

| Secret name | Value |
|---|---|
| `GEMINI_API_KEY` | Your Gemini key (`AIza…`) |
| `TELEGRAM_BOT_TOKEN` | Your bot token (`123456:ABC…`) |
| `TELEGRAM_CHAT_ID` | Your Telegram user ID |

Only `GEMINI_API_KEY` is required. Telegram is optional.

---

### Step 6 — Enable Actions & run manually

1. Go to **Actions** tab in your repo
2. Click **ScholarAgent Daily Scan**
3. Click **Run workflow** → **Run workflow**

The first run may take 2–3 minutes. Check the logs to see results!

After that, it runs **automatically every day at 09:00 Tunisia time** (08:00 UTC).

---

## 📁 Project structure

```
scholarship-agent/
├── .github/
│   └── workflows/
│       └── daily-scan.yml     ← GitHub Actions schedule
├── src/
│   └── agent.py               ← Main agent script
├── results/
│   ├── opportunities.json     ← All results (auto-updated)
│   └── seen_ids.json          ← Tracks already-notified opportunities
├── profile.json               ← YOUR PROFILE — edit this
├── requirements.txt
└── README.md
```

---

## 📊 Understanding results

Results are saved to `results/opportunities.json`. Each entry looks like:

```json
{
  "id": "a3f9d2e1c4b8",
  "title": "Erasmus Mundus Joint Masters",
  "link": "https://...",
  "source": "Scholars4Dev",
  "eligible": true,
  "score": 88,
  "reason": "Open to Tunisian nationals. Fully funded with €1000/month stipend.",
  "highlights": ["Fully funded", "Open to Tunisian nationals", "Monthly stipend"],
  "deadline": "2025-01-15",
  "funding_type": "Fully Funded",
  "checked_at": "2024-12-01T08:12:34"
}
```

`score` is 0–100 match quality. Focus on scores above 65.

---

## 🔍 Sources covered

| Source | Focus |
|---|---|
| **Scholars4Dev** | Developing countries, Masters, PhD, fully funded |
| **AfterSchool Africa** | Africa/MENA, alternance, apprenticeships, internships |
| **Opportunities for Africans** | African continent, all degree types |
| **Opportunities Circle** | Global, Masters, fellowships |
| **UN Jobs** | UN fellowships and internships |

---

## 🇹🇳 Top programs known to accept Tunisians

- **Erasmus Mundus** — EU, full funding, €1000/month stipend
- **DAAD Germany** — Strong for STEM, developing-country track
- **Stipendium Hungaricum** — Bilateral agreement with Tunisia via ministry
- **Türkiye Bursları** — Very accessible, full package, monthly allowance
- **Campus France** — French embassy scholarships for Tunisians
- **Heinrich Böll Foundation** — Germany, social/environment focus
- **OFPPT Alternance** — France, work-study, company pays salary

---

## ⚙️ Customizing

**Add more RSS sources** — edit the `RSS_FEEDS` list in `src/agent.py`:
```python
{
    "name": "My Source",
    "url": "https://example.com/feed/",
    "tags": ["scholarship", "masters"],
},
```

**Change run schedule** — edit `.github/workflows/daily-scan.yml`:
```yaml
- cron: "0 8 * * *"   # daily at 08:00 UTC
- cron: "0 8 * * 1"   # weekly, Mondays only
- cron: "0 8 1 * *"   # monthly, 1st of each month
```

**Stricter funding filter** — in `src/agent.py`, change `pre_filter()` to require "fully funded" explicitly.

---

## 🆓 Cost breakdown

| Component | Cost |
|---|---|
| GitHub Actions | Free (2000 min/month) |
| Gemini 1.5 Flash | Free (1500 calls/day) |
| Telegram Bot API | Free |
| RSS feeds | Free |
| **Total** | **$0/month** |

---

## 🤝 Contributing

Found a good RSS source for Tunisian-eligible scholarships? Open a PR!
