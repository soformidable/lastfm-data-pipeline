import logging
import pandas as pd
from datetime import timedelta

log = logging.getLogger(__name__)


def calculate_stats(engine) -> dict:
    """Read all scrobbles from the DB and compute listening statistics.

    Returns a dict ready to be upserted into the Last_fm_stats table.
    """
    query = "SELECT Artist, Album, Track, Date_played, Time_played FROM lastfm_scrobbles"
    df = pd.read_sql(query, engine)

    if df.empty:
        log.warning("No scrobbles found in DB — skipping stats calculation.")
        return {}

    # Handle both datetime.time and pd.Timedelta (from MySQL TIME column)
    def time_to_str(t):
        if hasattr(t, "strftime"):
            return t.strftime("%H:%M:%S")
        s = str(t)
        if " days " in s:
            return s.split(" days ")[-1]
        return s

    df["Played_At"] = pd.to_datetime(
        df["Date_played"].astype(str) + " " + df["Time_played"].apply(time_to_str)
    )

    latest_row       = df.loc[df["Played_At"].idxmax()]
    latest_time      = latest_row["Played_At"].strftime("%Y-%m-%d %H:%M:%S")
    latest_track     = str(latest_row["Track"])
    latest_artist    = str(latest_row["Artist"])

    track_counts     = df["Track"].value_counts()
    top_track        = str(track_counts.idxmax())
    top_track_count  = int(track_counts.max())

    artist_counts    = df["Artist"].value_counts()
    top_artist       = str(artist_counts.idxmax())
    top_artist_count = int(artist_counts.max())

    date_counts      = df["Date_played"].value_counts()
    top_date         = str(date_counts.idxmax())
    top_date_count   = int(date_counts.max())

    daily_counts     = df.groupby("Date_played").size().reset_index(name="daily_count")
    daily_counts["Date_played"] = pd.to_datetime(daily_counts["Date_played"])
    daily_counts["day_of_week"] = daily_counts["Date_played"].dt.day_name()
    day_avgs         = daily_counts.groupby("day_of_week")["daily_count"].mean()
    best_day         = str(day_avgs.idxmax())
    best_day_avg     = round(float(day_avgs.max()), 2)

    cutoff           = latest_row["Played_At"] - timedelta(days=30)
    recent_tracks    = df[df["Played_At"] >= cutoff]["Track"].unique()
    total_tc         = df["Track"].value_counts()
    candidates       = total_tc[~total_tc.index.isin(recent_tracks)]
    saturated_track  = str(candidates.idxmax()) if not candidates.empty else None

    return {
        "stat_id":               1,
        "latest_scrobble_time":  latest_time,
        "latest_scrobble_track": latest_track,
        "latest_scrobble_artist":latest_artist,
        "top_track":             top_track,
        "top_track_count":       top_track_count,
        "top_artist":            top_artist,
        "top_artist_count":      top_artist_count,
        "top_date":              top_date,
        "top_date_count":        top_date_count,
        "best_day":              best_day,
        "best_day_avg":          best_day_avg,
        "saturated_track":       saturated_track,
    }