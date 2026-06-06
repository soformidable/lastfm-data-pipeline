import time
import logging
import requests
import pandas as pd
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

# Shared constants
LOCAL_TZ   = ZoneInfo("Asia/Kolkata")
PAGE_LIMIT = 200
RATE_SLEEP = 0.25

log = logging.getLogger(__name__)

# Cache to avoid redundant API calls for artist/track genres
_genre_cache = {}


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
        params["from"] = from_ts + 1

    resp = requests.get(base_url, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


def fetch_track_tags(artist: str, track: str, api_key: str, base_url: str) -> list[str]:
    """Fetch top tags (genres) for a specific track from Last.fm."""
    cache_key = f"{artist}|{track}"
    if cache_key in _genre_cache:
        return _genre_cache[cache_key]
    
    try:
        params = {
            "method": "track.getInfo",
            "artist": artist,
            "track": track,
            "api_key": api_key,
            "format": "json",
        }
        resp = requests.get(base_url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        tags = []
        if "track" in data and "toptags" in data["track"]:
            tags = [tag["name"] for tag in data["track"]["toptags"]["tag"][:5]]  # Top 5 tags
        
        _genre_cache[cache_key] = tags
        time.sleep(RATE_SLEEP)
        return tags
    except Exception as e:
        log.warning("Failed to fetch tags for %s - %s: %s", artist, track, e)
        _genre_cache[cache_key] = []
        return []


def fetch_artist_tags(artist: str, api_key: str, base_url: str) -> list[str]:
    """Fetch top tags (genres) for an artist from Last.fm."""
    cache_key = f"artist|{artist}"
    if cache_key in _genre_cache:
        return _genre_cache[cache_key]
    
    try:
        params = {
            "method": "artist.getTopTags",
            "artist": artist,
            "api_key": api_key,
            "format": "json",
        }
        resp = requests.get(base_url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        tags = []
        if "toptags" in data:
            tags = [tag["name"] for tag in data["toptags"]["tag"][:5]]  # Top 5 tags
        
        _genre_cache[cache_key] = tags
        time.sleep(RATE_SLEEP)
        return tags
    except Exception as e:
        log.warning("Failed to fetch tags for artist %s: %s", artist, e)
        _genre_cache[cache_key] = []
        return []


def parse_tracks(raw_tracks: list, api_key: str = None, base_url: str = None, fetch_genres: bool = True) -> list[dict]:
    """Convert the raw API track list into clean dicts ready for the DB.
    
    Args:
        raw_tracks: List of raw track data from Last.fm API
        api_key: Last.fm API key (required if fetch_genres=True)
        base_url: Last.fm API base URL (required if fetch_genres=True)
        fetch_genres: Whether to fetch genre tags (slower, makes extra API calls)
    """
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

        artist = t.get("artist", {}).get("#text") or None
        track = t.get("name") or None
        
        # Fetch genres if enabled and we have API credentials
        genres = []
        if fetch_genres and api_key and base_url and artist and track:
            genres = fetch_track_tags(artist, track, api_key, base_url)

        rows.append({
            "Artist":      artist,
            "Album":       t.get("album",  {}).get("#text") or None,
            "Track":       track,
            "Date_played": played_local.date(),
            "Time_played": played_local.time().replace(microsecond=0),
            "Genres":      genres,
        })
    return rows


def fetch_all_scrobbles(username: str, api_key: str, base_url: str, from_ts: int | None, fetch_genres: bool = True) -> pd.DataFrame:
    """Paginate through user.getRecentTracks and return a deduplicated DataFrame.
    
    Args:
        fetch_genres: If True, fetches genre tags (slower due to extra API calls).
                     Set to False for faster initial syncs.
    """
    log.info("Starting fetch for user '%s' (from_ts=%s, fetch_genres=%s).", username, from_ts, fetch_genres)

    first = fetch_page(username, api_key, page=1, from_ts=from_ts, base_url=base_url)
    total_pages = int(first["recenttracks"]["@attr"]["totalPages"])
    total_tracks = int(first["recenttracks"]["@attr"]["total"])
    log.info("Total scrobbles to fetch: %d across %d page(s).", total_tracks, total_pages)

    all_rows = parse_tracks(first["recenttracks"]["track"], api_key, base_url, fetch_genres)

    for page in range(2, total_pages + 1):
        time.sleep(RATE_SLEEP)
        data = fetch_page(username, api_key, page=page, from_ts=from_ts, base_url=base_url)
        all_rows.extend(parse_tracks(data["recenttracks"]["track"], api_key, base_url, fetch_genres))
        log.info("  Page %d / %d fetched (%d rows so far).", page, total_pages, len(all_rows))

    df = pd.DataFrame(all_rows).drop_duplicates()
    # Convert genres list to JSON string for storage
    df["Genres"] = df["Genres"].apply(lambda x: str(x) if isinstance(x, list) else x)
    log.info("Fetch complete. %d unique rows ready for insertion.", len(df))
    return df
