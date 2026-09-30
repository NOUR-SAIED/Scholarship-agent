"""Telegram alerts in plain text. v0 used Markdown, and any title with _ * [ ]
made Telegram reject the whole message silently."""
from datetime import date, timedelta

import requests

from . import config


def _send(token: str, chat_id: str, text: str):
    r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                      json={"chat_id": chat_id, "text": text[:4000], "disable_web_page_preview": True},
                      timeout=30)
    if not r.ok:
        print(f"  [telegram] {r.status_code}: {r.text[:200]}")


def notify(new_items: list[dict], all_items: list[dict], dashboard_url: str = "") -> None:
    token, chat_id = config.get("TELEGRAM_BOT_TOKEN"), config.get("TELEGRAM_CHAT_ID")
    if not (token and chat_id):
        print("  Telegram not configured, skipping alerts")
        return

    top = sorted((o for o in new_items if o["score"] >= config.ALERT_MIN_SCORE
                  and o["badge"] in ("green", "yellow") and o["category"] != "irrelevant"),
                 key=lambda o: o["score"], reverse=True)[:8]
    soon = date.today() + timedelta(days=7)
    due = [o for o in all_items if o.get("deadline") and o.get("status") in ("new", "saved")
           and date.today().isoformat() <= o["deadline"] <= soon.isoformat()]

    if not top and not due:
        return
    lines = []
    if top:
        lines.append(f"🎯 {len(top)} new strong match(es)\n")
        for o in top:
            lines.append(f"{config.BADGE_ICONS[o['badge']]} {o['score']}  {o['title']}\n"
                         f"{o['organization']} · {config.CATEGORIES.get(o['category'], '')}\n"
                         f"{o['why']}\n{o['url']}\n")
    if due:
        lines.append("⏰ Deadlines within 7 days")
        lines += [f"• {o['deadline']}  {o['title']}" for o in sorted(due, key=lambda o: o["deadline"])]
    if dashboard_url:
        lines.append(f"\nOpen dashboard: {dashboard_url}")
    _send(token, chat_id, "\n".join(lines))
