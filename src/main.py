import os
import logging
from dotenv import load_dotenv

from database import get_engine, ensure_tables, get_latest_scrobble_ts, upsert_scrobbles, upsert_stats
from api import fetch_all_scrobbles
from stats import calculate_stats

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

LASTFM_API_KEY  = os.getenv("LASTFM_API_KEY")
LASTFM_USERNAME = os.getenv("LASTFM_USERNAME", "soformidable")
LASTFM_BASE_URL = "http://ws.audioscrobbler.com/2.0/"

# Main execution flow
def main():
    if not LASTFM_API_KEY:
        raise EnvironmentError("LASTFM_API_KEY is not set in your .env file.")

    engine = get_engine()
    ensure_tables(engine)

    # Incremental fetch: only pull scrobbles newer than what's already in the DB
    from_ts = get_latest_scrobble_ts(engine)
    if from_ts:
        log.info("Incremental mode — fetching scrobbles after Unix timestamp %d.", from_ts)
    else:
        log.info("Empty DB detected — performing full historical fetch.")

    df = fetch_all_scrobbles(LASTFM_USERNAME, LASTFM_API_KEY, LASTFM_BASE_URL, from_ts)
    upsert_scrobbles(engine, df)

    stats = calculate_stats(engine)
    upsert_stats(engine, stats)

    log.info("All done.")


if __name__ == "__main__":
    main()