import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, Table, MetaData
from sqlalchemy.dialects.mysql import insert
import pandas as pd
import logging
import json
import numpy as np

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

    # Make a copy to avoid modifying the original
    df = df.copy()
    
    log.info("Cleaning data before insertion (removing NaN values)...")
    
    # Step 1: Replace ALL NaN/NaT values with None across entire dataframe
    # This works for numeric NaN, string NaN, and NaT (datetime NaN)
    df = df.astype(object)
    df = df.where(pd.notna(df), None)

    
    # Step 2: Also handle numpy nan explicitly
    for col in df.columns:
        df[col] = df[col].apply(
            lambda x: None if (pd.isna(x) or (isinstance(x, float) and np.isnan(x))) else x
        )
    
    # Step 3: Handle Genres column specifically
    if "Genres" in df.columns:
        df["Genres"] = df["Genres"].apply(
            lambda x: None if (x is None or x == '' or x == 'None' or x == '[]') else x
        )

    # Commented the logs as they report None along with np.nan (pasdas.isna() considers both of them as "Missing")
    # Step 4: Verify no NaN values remain
    # nan_count = df.isna().sum().sum()
    # if nan_count > 0:
    #     log.warning("Warning: {} NaN values still present after cleaning".format(nan_count))
    #     # Show which columns have NaN
    #     for col in df.columns:
    #         nan_in_col = df[col].isna().sum()
    #         if nan_in_col > 0:
    #             log.warning("  Column '{}': {} NaN values".format(col, nan_in_col))

    missing_count = df.isna().sum().sum()

    if missing_count:
        log.info(
            "%d SQL NULL values will be inserted.",
            missing_count
    )

    bad_rows = df[df.isna().any(axis=1)]

    if not bad_rows.empty:
        log.error("Rows containing NaN:")
        log.error("\n%s", bad_rows.to_string())

        for col in df.columns:
            if bad_rows[col].isna().any():
                log.error(
                    "%s value=%r type=%s",
                    col,
                    bad_rows.iloc[0][col],
                    type(bad_rows.iloc[0][col])
            )
    
    log.info("Data cleaned. Preparing for insertion...")
    
    metadata = MetaData()
    table    = Table("lastfm_scrobbles", metadata, autoload_with=engine)
    records  = df.to_dict(orient="records")

    stmt = insert(table).values(records).prefix_with("IGNORE")
    
    try:
        with engine.begin() as conn:
            result = conn.execute(stmt)
        log.info("Inserted %d new scrobble row(s).", result.rowcount)
    except Exception as e:
        log.error("Error during insertion: %s", str(e))
        # Log the problematic records
        for i, record in enumerate(records[:5]):  # Log first 5 records
            log.error("Record %d: %s", i, record)
        raise

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
                    MIN(U.scrobble_id) AS min_id
                FROM lastfm_scrobbles U
                INNER JOIN (
                    SELECT Artist, Track, MIN(Album) AS Album
                    FROM lastfm_scrobbles
                    WHERE Album IS NOT NULL
                    GROUP BY Artist, Track
                ) S ON U.Artist = S.Artist AND U.Track = S.Track
                WHERE U.Album IS NULL
                GROUP BY U.Artist, U.Track, U.Date_played, U.Time_played
            ) S ON T.scrobble_id = S.min_id
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