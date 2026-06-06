import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database import get_engine
from src.genre_analysis import parse_genres_json
import pandas as pd

engine = get_engine()

print("=" * 70)
print("GENRE DATA VERIFICATION")
print("=" * 70)

# Get sample data
df = pd.read_sql(
    "SELECT scrobble_id, Artist, Track, Genres FROM lastfm_scrobbles LIMIT 10",
    engine
)

print("\n1. RAW DATA FROM DATABASE:")
print("-" * 70)
for idx, row in df.iterrows():
    genres_raw = row['Genres']
    print("\nRow {}:".format(idx))
    print("  Artist: {}".format(row['Artist']))
    print("  Track: {}".format(row['Track']))
    print("  Genres (raw type): {}".format(type(genres_raw).__name__))
    if genres_raw:
        print("  Genres (first 100 chars): {}".format(str(genres_raw)[:100]))
    else:
        print("  Genres: (empty/None)")

print("\n\n2. PARSED DATA:")
print("-" * 70)
for idx, row in df.iterrows():
    parsed = parse_genres_json(row['Genres'])
    print("\nRow {}:".format(idx))
    print("  Artist: {}".format(row['Artist']))
    print("  Parsed genres: {}".format(parsed))
    print("  Parsed type: {}".format(type(parsed).__name__))
    if parsed and isinstance(parsed, list):
        print("  Genre count: {}".format(len(parsed)))
        print("  First genre: {}".format(parsed[0] if parsed else "N/A"))

print("\n\n3. CHECKING FOR DATA QUALITY ISSUES:")
print("-" * 70)

# Check for empty genres
try:
    empty_count = pd.read_sql(
        "SELECT COUNT(*) as cnt FROM lastfm_scrobbles WHERE Genres IS NULL OR Genres = '[]'",
        engine
    )
    print("Rows with empty/null genres: {}".format(empty_count['cnt'].iloc[0]))
except Exception as e:
    print("Error checking empty genres: {}".format(e))

# Count total rows
try:
    total_count = pd.read_sql(
        "SELECT COUNT(*) as cnt FROM lastfm_scrobbles",
        engine
    )
    print("Total rows in database: {}".format(total_count['cnt'].iloc[0]))
except Exception as e:
    print("Error counting rows: {}".format(e))

# Get sample of actual stored values
print("\n4. SAMPLE STORED GENRE VALUES:")
print("-" * 70)
try:
    sample = pd.read_sql(
        "SELECT Genres FROM lastfm_scrobbles WHERE Genres IS NOT NULL LIMIT 5",
        engine
    )
    for i, genres in enumerate(sample['Genres']):
        print("\nSample {}: {}".format(i, str(genres)[:150]))
except Exception as e:
    print("Error getting samples: {}".format(e))

print("\n" + "=" * 70)