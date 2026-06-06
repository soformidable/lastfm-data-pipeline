import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, Table, MetaData
from sqlalchemy.dialects.mysql import insert
import pandas as pd
import logging

load_dotenv()

log = logging.getLogger(__name__)


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
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS lastfm_scrobbles (
                scrobble_id  BIGINT AUTO_INCREMENT PRIMARY KEY,
                Artist       VARCHAR(255),
                Album        VARCHAR(255),
                Track        VARCHAR(255),
                Date_played  DATE,
                Time_played  TIME,
                UNIQUE KEY uq_scrobble (Artist, Album, Track, Date_played, Time_played)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS Last_fm_stats (
                stat_id                INT PRIMARY KEY,
                latest_scrobble_time   DATETIME,
                latest_scrobble_track  VARCHAR(255),
                latest_scrobble_artist VARCHAR(255),
                top_track              VARCHAR(255),
                top_track_count        INT,
                top_artist             VARCHAR(255),
                top_artist_count       INT,
                top_date               DATE,
                top_date_count         INT,
                best_day_of_week       VARCHAR(50),
                best_day_avg           FLOAT,
                saturated_track        VARCHAR(255)
            )
        """))
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