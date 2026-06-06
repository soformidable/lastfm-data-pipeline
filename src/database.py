import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, Table, MetaData
from sqlalchemy.dialects.mysql import insert
import pandas as pd
import logging

load_dotenv()

log = logging.getLogger(__name__)

def _load_schema_sql() -> str:
    """Load and return the SQL schema file contents."""
    schema_path = Path(__file__).resolve().parent.parent / "sql" / "schema.sql"
    return schema_path.read_text()

def get_engine():
    return create_engine(
        "mysql+pymysql://{u}:{p}@{h}:{port}/{db}".format(
            u    = os.getenv("DB_USERNAME"),
            p    = os.getenv("DB_PASSWORD"),
            h    = os.getenv("DB_HOST"),
            port = os.getenv("DB_PORT"),
            db   = os.getenv("DB_NAME"),
        )
    )


def ensure_tables(engine):
    schema_sql = _load_schema_sql()
    with engine.begin() as conn:
        for statement in schema_sql.split(";"):
            stripped = statement.strip()
            if stripped:
                conn.execute(text(stripped))
    log.info("Tables verified / created.")


def get_latest_scrobble_ts(engine) -> int | None:
    """Return the Unix timestamp (UTC) of the most recent scrobble in the DB,
    or None if the table is empty."""
    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT UNIX_TIMESTAMP(CONVERT_TZ(
                CONCAT(Date_played, ' ', Time_played),
                'Asia/Kolkata', 'UTC'
            ))
            FROM lastfm_scrobbles
            ORDER BY Date_played DESC, Time_played DESC
            LIMIT 1
        """)).fetchone()
    return int(row[0]) if row and row[0] else None


def upsert_scrobbles(engine, df: pd.DataFrame):
    if df.empty:
        log.info("No new scrobbles to insert.")
        return

    metadata = MetaData()
    table    = Table("lastfm_scrobbles", metadata, autoload_with=engine)
    records  = df.to_dict(orient="records")

    stmt = insert(table).values(records).prefix_with("IGNORE")
    with engine.begin() as conn:
        result = conn.execute(stmt)
    log.info("Inserted %d new scrobble row(s).", result.rowcount)

# Update function to set the null albums to correct values
def update_albums(engine):
    sql = text("""
                    UPDATE lastfm_scrobbles T
            INNER JOIN (
                SELECT
                    U.Artist,
                    U.Track,
                    U.Date_played,
                    U.Time_played,
                    MIN(S.Album) AS Album,
                    MIN(U.scrobble_id) AS min_id   -- ← pull the MIN id up here instead
                FROM lastfm_scrobbles U
                INNER JOIN (
                    SELECT Artist, Track, MIN(Album) AS Album
                    FROM lastfm_scrobbles
                    WHERE Album IS NOT NULL
                    GROUP BY Artist, Track
                ) S ON U.Artist = S.Artist AND U.Track = S.Track
                WHERE U.Album IS NULL
                GROUP BY U.Artist, U.Track, U.Date_played, U.Time_played
            ) S ON T.scrobble_id = S.min_id       -- ← join on the ID directly, no subquery needed
            SET T.Album = S.Album
            WHERE T.Album IS NULL;
               """)
    with engine.begin() as conn:
        conn.execute(sql)
    log.info("Album update completed.")
    

       
# Upsert the stats row (there's only one) with the latest calculated stats.
def upsert_stats(engine, stats: dict):
    if not stats:
        return

    sql = text("""
        INSERT INTO Last_fm_stats (
            stat_id, latest_scrobble_time, latest_scrobble_track, latest_scrobble_artist,
            top_track, top_track_count, top_artist, top_artist_count,
            top_date, top_date_count, best_day_of_week, best_day_avg, saturated_track
        ) VALUES (
            :stat_id, :latest_scrobble_time, :latest_scrobble_track, :latest_scrobble_artist,
            :top_track, :top_track_count, :top_artist, :top_artist_count,
            :top_date, :top_date_count, :best_day, :best_day_avg, :saturated_track
        )
        ON DUPLICATE KEY UPDATE
            latest_scrobble_time   = VALUES(latest_scrobble_time),
            latest_scrobble_track  = VALUES(latest_scrobble_track),
            latest_scrobble_artist = VALUES(latest_scrobble_artist),
            top_track              = VALUES(top_track),
            top_track_count        = VALUES(top_track_count),
            top_artist             = VALUES(top_artist),
            top_artist_count       = VALUES(top_artist_count),
            top_date               = VALUES(top_date),
            top_date_count         = VALUES(top_date_count),
            best_day_of_week       = VALUES(best_day_of_week),
            best_day_avg           = VALUES(best_day_avg),
            saturated_track        = VALUES(saturated_track)
    """)

    with engine.begin() as conn:
        conn.execute(sql, stats)
    log.info("Stats table refreshed.")