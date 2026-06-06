import logging
import pandas as pd
import json
from collections import Counter

log = logging.getLogger(__name__)


def parse_genres_json(genres_str):
    """Parse genres from JSON string or list representation.
    
    Handles:
    - None/NaN values
    - Already-parsed lists
    - Valid JSON strings: ["rock", "pop"]
    - Double-encoded JSON: "[\"rock\", \"pop\"]" (MySQL JSON columns)
    - Fallback for malformed data
    """
    if not genres_str or pd.isna(genres_str):
        return []
    
    # Already a list
    if isinstance(genres_str, list):
        return genres_str
    
    # String that needs parsing
    if isinstance(genres_str, str):
        # Handle empty strings or empty JSON arrays
        if genres_str.strip() in ['', '[]', 'None']:
            return []
        
        try:
            # First parse attempt - handles both single and double-encoded JSON
            parsed = json.loads(genres_str)
            
            # If result is a list, we're done
            if isinstance(parsed, list):
                return parsed
            
            # If result is a string (double-encoded JSON), parse again
            if isinstance(parsed, str):
                try:
                    double_parsed = json.loads(parsed)
                    return double_parsed if isinstance(double_parsed, list) else []
                except json.JSONDecodeError:
                    return []
            
            return []
            
        except json.JSONDecodeError:
            # Fallback: try to handle Python string representation with single quotes
            try:
                json_str = genres_str.replace("'", '"')
                parsed = json.loads(json_str)
                return parsed if isinstance(parsed, list) else []
            except json.JSONDecodeError:
                return []
    
    return []


def calculate_genre_stats(engine) -> dict:
    """Calculate genre statistics from scrobbles.
    
    Returns:
    - Top genres overall
    - Genre distribution by artist
    - Artist -> genres mapping
    """
    query = "SELECT Artist, Track, Genres FROM lastfm_scrobbles"
    df = pd.read_sql(query, engine)
    
    if df.empty:
        log.warning("No scrobbles found in DB — skipping stats calculation.")
        return {}
    
    # Parse genres from JSON
    df["Genres_parsed"] = df["Genres"].apply(parse_genres_json)
    
    # Flatten genres across all scrobbles
    all_genres = []
    for genres_list in df["Genres_parsed"]:
        all_genres.extend(genres_list)
    
    genre_counts = Counter(all_genres)
    
    return {
        "top_genres": genre_counts.most_common(20),
        "total_unique_genres": len(genre_counts),
        "genre_distribution": dict(genre_counts),
    }


def get_artist_genres(engine) -> pd.DataFrame:
    """Get primary genres for each artist based on their most common tags.
    
    Returns a DataFrame with:
    - Artist
    - Primary genres (comma-separated top genres)
    - Genre count
    """
    query = "SELECT Artist, Genres FROM lastfm_scrobbles WHERE Artist IS NOT NULL"
    df = pd.read_sql(query, engine)
    
    if df.empty:
        return pd.DataFrame()
    
    df["Genres_parsed"] = df["Genres"].apply(parse_genres_json)
    
    artist_genres = {}
    for _, row in df.iterrows():
        artist = row["Artist"]
        genres = row["Genres_parsed"]
        
        if artist not in artist_genres:
            artist_genres[artist] = []
        artist_genres[artist].extend(genres)
    
    # Get top 3 genres per artist
    artist_genre_list = []
    for artist, genres in artist_genres.items():
        if genres:
            top_genres = Counter(genres).most_common(3)
            primary_genres = ", ".join([g[0] for g in top_genres])
            genre_count = len(set(genres))
        else:
            primary_genres = "Unknown"
            genre_count = 0
        
        artist_genre_list.append({
            "Artist": artist,
            "Primary_Genres": primary_genres,
            "Genre_Count": genre_count,
        })
    
    return pd.DataFrame(artist_genre_list)


def get_genre_trends_by_period(engine, period: str = "Month") -> pd.DataFrame:
    """Get genre distribution trends over time periods.
    
    Args:
        period: "Month", "Week", or "Day"
    
    Returns DataFrame with period, genre, and play count.
    """
    query = "SELECT Date_played, Time_played, Genres FROM lastfm_scrobbles"
    df = pd.read_sql(query, engine)
    
    if df.empty:
        return pd.DataFrame()
    
    df["Played_At"] = pd.to_datetime(
        df["Date_played"].astype(str) + " " + df["Time_played"].astype(str)
    )
    
    if period == "Month":
        df["Period"] = df["Played_At"].dt.to_period("M").astype(str)
    elif period == "Week":
        df["Period"] = df["Played_At"].dt.to_period("W").apply(lambda p: str(p.start_time.date()))
    else:  # Day
        df["Period"] = df["Played_At"].dt.date.astype(str)
    
    df["Genres_parsed"] = df["Genres"].apply(parse_genres_json)
    
    # Expand genres so each genre gets its own row
    expanded = []
    for _, row in df.iterrows():
        for genre in row["Genres_parsed"]:
            expanded.append({"Period": row["Period"], "Genre": genre})
    
    trend_df = pd.DataFrame(expanded)
    
    if not trend_df.empty:
        trend_df = trend_df.groupby(["Period", "Genre"]).size().reset_index(name="Count")
    
    return trend_df