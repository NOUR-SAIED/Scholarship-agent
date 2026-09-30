"""Opportunity Radar dashboard.  Run locally:  streamlit run app.py"""
import html
from datetime import date, datetime, timedelta

import streamlit as st

from src import config
from src.storage import get_store

st.set_page_config(page_title="Opportunity Radar", page_icon=":material/radar:", layout="wide")

ELIGIBILITY_COLOR = {"green": "#16875A", "yellow": "#B7791F", "orange": "#8A94A6", "red": "#C2413A"}

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;500;600;700&display=swap');
:root {
  --ink:#15181E; --muted:#667085; --faint:#98A2B3; --line:#E2E6EB; --canvas:#F3F5F7;
  --surface:#FFFFFF; --accent:#0B6E79; --accent-soft:#E6F1F2;
}
html, body, .stApp, p, label, input, textarea, button, h1, h2, h3, h4, li, [data-baseweb="select"], [data-baseweb="tab"] {
  font-family: 'Instrument Sans', system-ui, -apple-system, 'Segoe UI', sans-serif !important;
}
.block-container {padding-top: 2.2rem; padding-bottom: 4rem; max-width: 1180px;}
header[data-testid="stHeader"] {background: transparent;}
[data-testid="stSidebar"] {background: var(--surface); border-right: 1px solid var(--line);}
[data-testid="stSidebar"] .block-container {padding-top: 1.5rem;}

/* header */
.masthead {display:flex; align-items:baseline; justify-content:space-between; gap:1rem; flex-wrap:wrap; margin-bottom:1.4rem;}
.masthead h1 {font-size:1.75rem; font-weight:650; letter-spacing:-0.025em; margin:0; padding:0; color:var(--ink);}
.masthead .sub {color:var(--muted); font-size:0.9rem;}

/* summary strip */
.summary {display:grid; grid-template-columns:repeat(4, minmax(0,1fr)); background:var(--surface);
  border:1px solid var(--line); border-radius:12px; margin-bottom:1.6rem; overflow:hidden;}
.summary div {padding:0.95rem 1.2rem; border-left:1px solid var(--line);}
.summary div:first-child {border-left:none;}
.summary b {display:block; font-size:1.55rem; font-weight:650; font-variant-numeric:tabular-nums; color:var(--ink); line-height:1.1;}
.summary span {color:var(--muted); font-size:0.82rem;}
@media (max-width: 700px) {.summary {grid-template-columns:repeat(2, minmax(0,1fr));}
  .summary div:nth-child(3) {border-left:none;} .summary div:nth-child(n+3) {border-top:1px solid var(--line);}}

/* tabs */
.stTabs [data-baseweb="tab-list"] {gap:1.6rem; border-bottom:1px solid var(--line);}
.stTabs [data-baseweb="tab"] {padding:0.6rem 0; font-weight:500; color:var(--muted);}
.stTabs [aria-selected="true"] {color:var(--ink);}
.stTabs [data-baseweb="tab-highlight"] {background:var(--ink); height:2px;}

/* cards */
.stVerticalBlock:has(> .stElementContainer .opp) {background:var(--surface); border-color:var(--line) !important;
  border-radius:12px !important;}
.opp {display:flex; gap:1.2rem; align-items:flex-start; border-left:3px solid var(--edge); padding-left:1rem; margin-left:-0.2rem;}
.opp .body {flex:1; min-width:0;}
.opp .title {font-size:1.04rem; font-weight:600; line-height:1.35; letter-spacing:-0.005em;}
.opp .title a {color:var(--ink); text-decoration:none;}
.opp .title a:hover {text-decoration:underline; text-underline-offset:3px;}
.opp .org {color:var(--muted); font-size:0.88rem; margin-top:0.15rem;}
.opp .org span + span::before {content:""; display:inline-block; width:3px; height:3px; border-radius:50%;
  background:var(--faint); margin:0 0.55rem; vertical-align:middle;}
.opp .why {color:var(--ink); font-size:0.93rem; line-height:1.5; margin:0.55rem 0 0.6rem; max-width:68ch;}
.pills {display:flex; flex-wrap:wrap; gap:0.35rem;}
.pill {font-size:0.76rem; padding:0.18rem 0.55rem; border-radius:999px; background:#F1F3F6; color:#475467; white-space:nowrap;}
.pill.elig {background:transparent; border:1px solid var(--edge); color:var(--edge); font-weight:600;}
.pill.warn {background:#FDF1F0; color:#A3332C;}
.pill.soon {background:#FFF6E5; color:#8A5A00;}
.blocker {color:#A3332C; font-size:0.84rem; margin-top:0.45rem;}
.gauge {width:58px; height:58px; border-radius:50%; flex:none; display:grid; place-items:center;
  background:conic-gradient(var(--edge) calc(var(--v) * 1%), #EEF0F3 0);}
.gauge div {width:46px; height:46px; border-radius:50%; background:var(--surface); display:grid; place-items:center;
  font-weight:650; font-size:1.02rem; font-variant-numeric:tabular-nums; color:var(--ink);}

/* tracker + lists */
.col-head {font-size:0.8rem; font-weight:600; color:var(--muted); text-transform:none; margin:0 0 0.6rem;
  padding-bottom:0.5rem; border-bottom:1px solid var(--line);}
.col-head b {color:var(--ink); font-variant-numeric:tabular-nums; margin-left:0.3rem;}
.mini {padding:0.6rem 0; border-bottom:1px solid var(--line); font-size:0.9rem; line-height:1.35;}
.mini a {color:var(--ink); font-weight:550; text-decoration:none;}
.mini small {display:block; color:var(--muted); font-size:0.8rem; margin-top:0.15rem;}
.empty {color:var(--muted); font-size:0.92rem; padding:2.2rem 0; text-align:left;}
.health {display:flex; justify-content:space-between; font-size:0.85rem; padding:0.2rem 0;}
.health i {display:inline-block; width:7px; height:7px; border-radius:50%; margin-right:0.5rem; vertical-align:middle;}
.stButton button {border-radius:8px; font-weight:550;}

/* quieter widgets */
span[data-tag] {background:var(--accent-soft) !important; color:var(--accent) !important; border-radius:6px !important;}
span[data-tag] * {color:var(--accent) !important; fill:var(--accent) !important;}
[data-testid="stExpander"] details {border:1px solid var(--line); border-radius:8px; background:var(--surface);}
[data-testid="stExpander"] summary p {font-size:0.88rem; color:var(--muted);}
.stVerticalBlock:has(> .stElementContainer .opp) [data-testid="stSelectbox"] [data-baseweb="select"] {
  box-shadow: inset 0 0 0 1px var(--line); border-radius:8px; background:var(--surface);}
[data-testid="stExpander"] [data-testid="stExpanderDetails"] p {font-size:0.92rem; line-height:1.55; color:#344054;}
.opp {margin-bottom:0.55rem;}

/* keep Streamlit's built-in icons on their icon font (must stay last) */
[data-testid="stIconMaterial"], span[class*="material-symbols"] {
  font-family: 'Material Symbols Rounded' !important;
}
</style>
""", unsafe_allow_html=True)


# ---------- access gate ----------
password = config.get("APP_PASSWORD")
if password and not st.session_state.get("authed"):
    st.markdown("<div class='masthead'><h1>Opportunity Radar</h1></div>", unsafe_allow_html=True)
    if st.text_input("Password", type="password") == password:
        st.session_state.authed = True
        st.rerun()
    st.stop()

store = get_store()
esc = html.escape


@st.cache_data(ttl=300)
def load() -> list[dict]:
    return store.all()


@st.cache_data(ttl=300)
def load_runs() -> list[dict]:
    try:
        return store.runs()
    except Exception:
        return []


def quick_status(opp_id: str, status: str):
    store.update(opp_id, status=status)
    load.clear()


def set_status(opp_id: str, key: str):
    store.update(opp_id, status=st.session_state[key])
    load.clear()


def run_scan():
    """Runs the full daily pipeline from the dashboard and keeps its log to show after reloading."""
    import contextlib
    import io
    from src.pipeline import run
    log = io.StringIO()
    try:
        with st.spinner("Scanning all sources. This takes 1 to 3 minutes."), contextlib.redirect_stdout(log):
            records = run(send_alerts=False)
        new = [r for r in records if r["category"] != "irrelevant" and r.get("status") != "skipped"]
        st.session_state.scan_result = ("success", f"Scan done: {len(new)} new {'opportunity' if len(new) == 1 else 'opportunities'} for you.", log.getvalue())
    except BaseException as e:  # includes sys.exit from the pipeline's safety checks
        st.session_state.scan_result = ("error", f"Scan failed: {e}", log.getvalue())
    load.clear()
    load_runs.clear()
    st.rerun()


def save_notes(opp_id: str, key: str):
    store.update(opp_id, notes=st.session_state[key])
    load.clear()


def draft_application(opp: dict) -> str:
    key = config.get("GEMINI_API_KEY")
    if not key:
        return "Add GEMINI_API_KEY to your secrets to generate drafts."
    prompt = (
        "Write a short, specific cover letter (max 180 words) for this candidate and opportunity. "
        "No generic filler, no invented experience. Open with why this exact role/program, "
        "then 2 concrete matching experiences from the profile, then a one-line close. "
        "If the posting is in French, write in French.\n\n"
        f"PROFILE:\n{config.load_profile()}\n\nOPPORTUNITY:\n{opp['title']} at {opp['organization']}\n"
        f"{opp.get('description', '')[:2500]}"
    )
    try:
        from src.classifier import call_gemini
        return call_gemini(prompt, key, json_mode=False)
    except Exception as e:
        return f"Draft failed: {e}"


def days_left(deadline: str | None) -> int | None:
    if not deadline:
        return None
    try:
        return (date.fromisoformat(deadline) - date.today()).days
    except ValueError:
        return None


def card_html(o: dict) -> str:
    edge = ELIGIBILITY_COLOR.get(o.get("badge"), "#8A94A6")
    org_bits = [o.get("organization", ""), o.get("country") or o.get("location", ""),
                (o.get("seniority") or "").replace("unknown", "").capitalize(), o.get("source", "")]
    org = "".join(f"<span>{esc(b)}</span>" for b in org_bits if b)
    pills = [f"<span class='pill elig'>{config.BADGES.get(o.get('badge'), 'Unclear')}</span>"]
    d = days_left(o.get("deadline"))
    if d is not None:
        pills.append(f"<span class='pill soon'>{d} days left</span>" if 0 <= d <= 14
                     else f"<span class='pill'>Deadline {esc(o['deadline'])}</span>" if d > 14
                     else "<span class='pill warn'>Deadline passed</span>")
    if o.get("paid") == "yes":
        pills.append("<span class='pill'>Paid or funded</span>")
    elif o.get("paid") == "no":
        pills.append("<span class='pill warn'>Unpaid</span>")
    if o.get("visa_sponsorship") == "yes":
        pills.append("<span class='pill'>Visa sponsorship</span>")
    if o.get("timezone_note"):
        pills.append(f"<span class='pill'>{esc(o['timezone_note'])}</span>")
    for s in (o.get("skill_matches") or [])[:5]:
        pills.append(f"<span class='pill'>{esc(s)}</span>")
    blockers = "".join(f"<div class='blocker'>{esc(b)}</div>" for b in (o.get("blockers") or []))
    why = f"<div class='why'>{esc(o['why'])}</div>" if o.get("why") else "<div style='height:.5rem'></div>"
    score = int(o.get("score") or 0)
    return (
        f"<div class='opp' style='--edge:{edge}'>"
        f"<div class='body'><div class='title'><a href='{esc(o.get('url', '#'))}' target='_blank'>{esc(o['title'])}</a></div>"
        f"<div class='org'>{org}</div>{why}<div class='pills'>{''.join(pills)}</div>{blockers}</div>"
        f"<div class='gauge' style='--v:{score}' title='Fit score'><div>{score}</div></div></div>"
    )


def card(o: dict, prefix: str, controls: bool = True):
    with st.container(border=True):
        st.markdown(card_html(o), unsafe_allow_html=True)
        if not controls:
            return
        left, right = st.columns([5, 1.3], vertical_alignment="center")
        with right:
            k = f"{prefix}_status_{o['id']}"
            st.selectbox("Status", config.STATUSES, key=k, label_visibility="collapsed",
                         format_func=str.capitalize,
                         index=config.STATUSES.index(o.get("status", "new")) if o.get("status") in config.STATUSES else 0,
                         on_change=set_status, args=(o["id"], k))
        with left:
            detail_panel(o, prefix)


def detail_panel(o: dict, prefix: str):
    with st.expander("Details, notes and draft"):
        st.write(o.get("description", "")[:1500] or "No description.")
        nk = f"{prefix}_notes_{o['id']}"
        st.text_area("Notes", value=o.get("notes", ""), key=nk, on_change=save_notes, args=(o["id"], nk),
                     placeholder="Contact name, referral, what you sent")
        dk = f"draft_{o['id']}"
        if st.button("Draft an application", key=f"{prefix}_btn_{o['id']}"):
            with st.spinner("Writing"):
                st.session_state[dk] = draft_application(o)
        if dk in st.session_state:
            st.text_area("Draft, edit before sending", st.session_state[dk], height=260, key=f"{prefix}_d_{o['id']}")


# ---------- data ----------
everything = load()
items = [o for o in everything if o.get("category") != "irrelevant"]
filtered_out = [o for o in everything if o.get("category") == "irrelevant"]
runs = load_runs()

last_scan = ""
if runs:
    try:
        t = datetime.fromisoformat(runs[0]["ran_at"])
        last_scan = f"Last scan {t.strftime('%d %b, %H:%M')} UTC, {sum(runs[0].get('sources', {}).values())} postings checked"
    except Exception:
        pass
st.markdown(f"<div class='masthead'><h1>Opportunity Radar</h1><div class='sub'>{esc(last_scan)}</div></div>",
            unsafe_allow_html=True)

# ---------- sidebar ----------
with st.sidebar:
    c1, c2 = st.columns(2)
    if c1.button("Refresh", width="stretch", help="Reload saved results. Doesn't search for new ones."):
        load.clear()
        load_runs.clear()
        st.rerun()
    if c2.button("Scan now", type="primary", width="stretch",
                 help="Search all sources for new opportunities (1 to 3 minutes)."):
        run_scan()
    if "scan_result" in st.session_state:
        kind, message, log = st.session_state.scan_result
        (st.success if kind == "success" else st.error)(message)
        with st.expander("Scan log"):
            st.code(log[-5000:] or "No output.", language=None)

    st.markdown("#### Filters")
    badges = st.multiselect("Eligibility", list(config.BADGES), default=["green", "yellow", "orange"],
                            format_func=lambda b: config.BADGES[b])
    min_score = st.slider("Minimum fit", 0, 100, 40, step=5)
    levels = st.multiselect("Seniority", ["entry", "junior", "mid", "unknown", "senior"],
                            default=["entry", "junior", "mid", "unknown"], format_func=str.capitalize)
    query = st.text_input("Search", placeholder="dbt, Montréal, fellowship")
    sort = st.selectbox("Sort by", ["Best fit", "Deadline", "Newest"])
    only_paid = st.toggle("Paid or funded only")
    hide_done = st.toggle("Hide skipped and rejected", value=True)
    hide_expired = st.toggle("Hide passed deadlines", value=True)

    with st.expander("Source health"):
        if not runs:
            st.caption("No scans logged yet.")
        else:
            rows = []
            for name, n in runs[0].get("sources", {}).items():
                color = "#16875A" if n else "#C2413A"
                rows.append(f"<div class='health'><span><i style='background:{color}'></i>{esc(name)}</span><b>{n}</b></div>")
            st.markdown("".join(rows), unsafe_allow_html=True)
            if any(n == 0 for n in runs[0].get("sources", {}).values()):
                st.caption("Red means the source returned nothing. The site may be blocking requests or its feed moved.")
            if runs[0].get("pending"):
                st.caption(f"{runs[0]['pending']} waiting for the next AI quota.")
    st.caption(f"Storage: {store.name}")

if not items:
    st.markdown("<div class='empty'>Nothing here yet. Press <b>Scan now</b> in the sidebar to search every source, "
                "or run <code>python -m src.pipeline --sample --no-ai</code> to load demo data.</div>",
                unsafe_allow_html=True)
    st.stop()

# ---------- summary ----------
active = [o for o in items if o.get("status") not in ("skipped", "rejected")]
week = (date.today() + timedelta(days=7)).isoformat()
stats = [
    (sum(o.get("status") == "new" for o in active), "new to review"),
    (sum(o.get("badge") == "green" for o in active), "open to you"),
    (sum(1 for o in active if o.get("deadline") and date.today().isoformat() <= o["deadline"] <= week), "deadlines this week"),
    (sum(o.get("status") in ("applied", "interview", "offer") for o in items), "applications out"),
]
st.markdown("<div class='summary'>" + "".join(f"<div><b>{n}</b><span>{label}</span></div>" for n, label in stats) + "</div>",
            unsafe_allow_html=True)


def passes(o: dict) -> bool:
    if o.get("badge") not in badges or o.get("score", 0) < min_score:
        return False
    if o.get("seniority", "unknown") not in levels:
        return False
    if only_paid and o.get("paid") != "yes":
        return False
    if hide_done and o.get("status") in ("skipped", "rejected"):
        return False
    d = days_left(o.get("deadline"))
    if hide_expired and d is not None and d < 0 and o.get("status") in ("new", "saved"):
        return False
    if query:
        hay = " ".join(str(o.get(k, "")) for k in ("title", "organization", "country", "description", "why")).lower()
        if query.lower() not in hay:
            return False
    return True


def ordered(rows: list[dict]) -> list[dict]:
    if sort == "Deadline":
        return sorted(rows, key=lambda o: (o.get("deadline") or "9999", -o.get("score", 0)))
    if sort == "Newest":
        return sorted(rows, key=lambda o: o.get("found_at", ""), reverse=True)
    return sorted(rows, key=lambda o: o.get("score", 0), reverse=True)


shown = [o for o in items if passes(o)]
queue = [o for o in ordered(shown) if o.get("status") == "new"]
tab_names = [f"{label}  {sum(o['category'] == c for o in shown)}" for c, label in config.CATEGORIES.items()]
tabs = st.tabs([f"Triage  {len(queue)}"] + tab_names + ["Tracker"])

with tabs[0]:
    if not queue:
        st.markdown("<div class='empty'>You're all caught up. New matches appear here after the next scan.</div>",
                    unsafe_allow_html=True)
    else:
        pos = st.session_state.get("triage_pos", 0) % len(queue)
        o = queue[pos]
        st.caption(f"{pos + 1} of {len(queue)}, best fit first. Your choices teach the next scan what you like.")
        card(o, "triage", controls=False)
        b1, b2, b3, _ = st.columns([1, 1, 1, 3])
        b1.button("Save", type="primary", width="stretch", key="t_save",
                  on_click=quick_status, args=(o["id"], "saved"))
        b2.button("Skip", width="stretch", key="t_skip", on_click=quick_status, args=(o["id"], "skipped"))
        if b3.button("Later", width="stretch", key="t_later"):
            st.session_state.triage_pos = pos + 1
            st.rerun()
        detail_panel(o, "triage")

for tab, cat in zip(tabs[1:], config.CATEGORIES):
    with tab:
        rows = ordered([o for o in shown if o["category"] == cat])
        if not rows:
            st.markdown("<div class='empty'>Nothing matches the current filters. Lower the minimum fit or include "
                        "Unclear in Eligibility.</div>", unsafe_allow_html=True)
        for o in rows[:100]:
            card(o, cat)

with tabs[-1]:
    cols = st.columns(4, gap="large")
    for col, status in zip(cols, ["saved", "applied", "interview", "offer"]):
        with col:
            rows = sorted([o for o in items if o.get("status") == status], key=lambda o: o.get("deadline") or "9999")
            parts = [f"<div class='col-head'>{status.capitalize()}<b>{len(rows)}</b></div>"]
            for o in rows:
                d = days_left(o.get("deadline"))
                extra = f", {d} days left" if d is not None and d >= 0 else ""
                parts.append(f"<div class='mini'><a href='{esc(o['url'])}' target='_blank'>{esc(o['title'])}</a>"
                             f"<small>{esc(o.get('organization', ''))}{extra}</small></div>")
            if not rows:
                parts.append("<div class='mini'><small>Nothing yet</small></div>")
            st.markdown("".join(parts), unsafe_allow_html=True)

    st.write("")
    with st.expander(f"Filtered out automatically ({len(filtered_out)})"):
        st.caption("Removed before reaching the AI, or marked irrelevant by it. If something here should have "
                   "made it, loosen the rules in src/prefilter.py or profile.json.")
        parts = []
        for o in sorted(filtered_out, key=lambda o: o.get("found_at", ""), reverse=True)[:60]:
            reason = (o.get("blockers") or [""])[0] or o.get("why", "")
            parts.append(f"<div class='mini'><a href='{esc(o['url'])}' target='_blank'>{esc(o['title'])}</a>"
                         f"<small>{esc(o.get('organization', ''))}: {esc(reason)}</small></div>")
        st.markdown("".join(parts) or "<div class='mini'><small>Nothing filtered yet</small></div>", unsafe_allow_html=True)