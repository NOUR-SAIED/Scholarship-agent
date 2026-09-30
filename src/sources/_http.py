import time

import requests

from ..config import HTTP_HEADERS


def get(url: str, params: dict | None = None, retries: int = 3, timeout: int = 30) -> requests.Response:
    last_error = None
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, headers=HTTP_HEADERS, timeout=timeout)
            if r.status_code == 429 or r.status_code >= 500:
                raise requests.HTTPError(f"HTTP {r.status_code}")
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            last_error = e
            time.sleep(2 * (attempt + 1))
    raise last_error


def strip_html(html: str, limit: int = 4000) -> str:
    import re
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html or "", flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;|&#160;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]
