import time
import logging
import requests
import pandas as pd
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

# Shared constants – could be moved to config later
LOCAL_TZ   = ZoneInfo("Asia/Kolkata")
PAGE_LIMIT = 200
RATE_SLEEP = 0.25

log = logging.getLogger(__name__)


def fetch_page(username: str, api_key: str, page: int, from_ts: int | None, base_url: str) -> dict:
    params = {
        "method":       "user.getRecentTracks",
        "user":         username,
        "api_key":      api_key,
        "format":       "json",
        "limit":        PAGE_LIMIT,
        "page":         page,
        "extended":     0,
    }
    if from_ts:
        params["from"] = from_ts + 1   # +1 so we don't re-insert the last known scrobble

    resp = requests.get(base_url, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


def parse_tracks(raw_tracks: list) -> list[dict]:
    """Convert the raw API track list into clean dicts ready for the DB."""
    rows = []
    for t in raw_tracks:
        # Skip the 'now playing' entry — it has no date
        if t.get("@attr", {}).get("nowplaying"):
            continue

        uts = t.get("date", {}).get("uts")
        if not uts:
            continue

        played_utc = datetime.fromtimestamp(int(uts), tz=timezone.utc)
        played_local = played_utc.astimezone(LOCAL_TZ)

        rows.append({
            "Artist":      t.get("artist", {}).get("#text") or None,
            "Album":       t.get("album",  {}).get("#text") or None,
            "Track":       t.get("name")                    or None,
            "Date_played": played_local.date(),
            "Time_played": played_local.time().replace(microsecond=0),
        })
    return rows


def fetch_all_scrobbles(username: str, api_key: str, base_url: str, from_ts: int | None) -> pd.DataFrame:
    """Paginate through user.getRecentTracks and return a deduplicated DataFrame."""
    log.info("Starting fetch for user '%s' (from_ts=%s).", username, from_ts)

    first = fetch_page(username, api_key, page=1, from_ts=from_ts, base_url=base_url)
    total_pages = int(first["recenttracks"]["@attr"]["totalPages"])
    total_tracks = int(first["recenttracks"]["@attr"]["total"])
    log.info("Total scrobbles to fetch: %d across %d page(s).", total_tracks, total_pages)

    all_rows = parse_tracks(first["recenttracks"]["track"])

    for page in range(2, total_pages + 1):
        time.sleep(RATE_SLEEP)
        data = fetch_page(username, api_key, page=page, from_ts=from_ts, base_url=base_url)
        all_rows.extend(parse_tracks(data["recenttracks"]["track"]))
        log.info("  Page %d / %d fetched (%d rows so far).", page, total_pages, len(all_rows))

    df = pd.DataFrame(all_rows).drop_duplicates()
    log.info("Fetch complete. %d unique rows ready for insertion.", len(df))
    return df