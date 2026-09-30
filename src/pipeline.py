"""Daily run: fetch -> skip known -> prefilter -> classify -> store -> alert.

  python -m src.pipeline --sample --no-ai   # offline demo, no keys needed
  python -m src.pipeline --dry-run          # real sources, prints, saves nothing
  python -m src.pipeline                    # the real thing
"""
import argparse
import os
import sys
from datetime import datetime, timezone

from . import config
from .classifier import classify
from .notifier import notify
from .prefilter import prefilter
from .sources import LIVE_SOURCES, fetch_sample
from .storage import get_store

# Windows terminals sometimes choke on emoji; never crash over printing.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")


def run(sample=False, use_ai=True, dry_run=False, only=None, send_alerts=True):
    profile = config.load_profile()
    store = get_store()
    if os.environ.get("GITHUB_ACTIONS") and store.name != "Supabase" and not (dry_run or sample):
        # Actions machines are wiped after each run: a local JSON file would forget
        # everything and re-send the same alerts every morning.
        sys.exit("SUPABASE_URL / SUPABASE_KEY secrets are missing. Add them in the repo settings.")
    print(f"Storage: {store.name}\n\nFetching")

    raw, source_counts = [], {}
    fetchers = {"sample": fetch_sample} if sample else LIVE_SOURCES
    for name, fetch in fetchers.items():
        if only and name not in only:
            continue
        try:
            items = fetch()
        except Exception as e:  # a broken source must never kill the run
            print(f"  [{name}] crashed: {e}")
            items = []
        source_counts[name] = len(items)
        flag = "   <-- check this source" if not items else ""
        print(f"  {name:10s} {len(items):4d}{flag}")
        raw += items

    history = store.all()
    known = {r["id"] for r in history}
    fresh = [o for o in raw if o.id not in known]
    candidates, dropped, stats = prefilter(fresh, profile)
    print(f"\nFetched {len(raw)} | already known {len(raw) - len(fresh)} | new {len(fresh)}")
    print(f"  dropped for free: {stats['duplicate']} duplicates, {stats['location']} not open to Tunisia, "
          f"{stats['language']} need German, {stats['off_profile']} off-profile")
    if stats.get("deferred"):
        print(f"  {stats['deferred']} extra roles from companies with many openings wait for the next run")
    print(f"  sending to classifier: {len(candidates)}\n")

    classified = classify(candidates, profile, use_ai=use_ai, history=history)
    records = [o.to_record() for o in classified]
    relevant = [r for r in records if r["category"] != "irrelevant"]
    by_ai = sum(r["classified_by"] == "gemini" for r in records)
    print(f"Classified {len(records)} ({by_ai} by Gemini) | relevant: {len(relevant)} | "
          f"left for next run: {len(candidates) - len(records)}")

    for r in sorted(relevant, key=lambda r: r["score"], reverse=True)[:10]:
        print(f"  {config.BADGE_ICONS[r['badge']]} {r['score']:3d}  [{r['category']}] {r['title'][:55]} - {r['organization'][:25]}")

    if dry_run:
        print("\nDry run: nothing saved, no alerts sent.")
        return records

    for r in records:  # auto-hide what isn't for her, but keep it so it's never re-classified
        if r["category"] == "irrelevant" or r["badge"] == "red":
            r["status"] = "skipped"
    store.upsert(records + [o.to_record() for o in dropped])
    pruned = store.prune()
    store.log_run({
        "ran_at": datetime.now(timezone.utc).isoformat(), "sources": source_counts,
        "new": len(fresh), "dropped": stats, "classified": len(records), "by_ai": by_ai,
        "relevant": len(relevant), "pending": len(candidates) - len(records), "pruned": pruned,
    })
    if send_alerts:
        notify(relevant, store.all(), config.get("DASHBOARD_URL"))
    print("\nSaved.")
    return records


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--sample", action="store_true", help="use built-in fake data")
    p.add_argument("--no-ai", action="store_true", help="rule-based classification only")
    p.add_argument("--dry-run", action="store_true", help="don't save or alert")
    p.add_argument("--only", nargs="*", help="only these sources, e.g. --only himalayas rss")
    a = p.parse_args()
    run(sample=a.sample, use_ai=not a.no_ai, dry_run=a.dry_run, only=a.only)
