"""Each source returns a list[Opportunity]. A failing source logs and returns []
so one broken site never kills the whole run."""
from .arbeitnow import fetch_arbeitnow
from .himalayas import fetch_himalayas
from .jobicy import fetch_jobicy
from .remotive import fetch_remotive
from .rss_feeds import fetch_rss
from .sample import fetch_sample

LIVE_SOURCES = {
    "jobicy": fetch_jobicy,
    "remotive": fetch_remotive,
    "himalayas": fetch_himalayas,
    "arbeitnow": fetch_arbeitnow,
    "rss": fetch_rss,
}
