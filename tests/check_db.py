import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database import get_engine
import pandas as pd

engine = get_engine()

print("=" * 60)
print("Database Diagnostic")
print("=" * 60)

# Check if Genres column exists
print("\n1. Checking table structure...")
try:
    schema = pd.read_sql("DESCRIBE lastfm_scrobbles", engine)
    print(schema[['Field', 'Type', 'Null']])
    
    if 'Genres' in schema['Field'].values:
        print("✓ Genres column exists")
    else:
        print("✗ Genres column MISSING - need to add it!")
except Exception as e:
    print(f"✗ Error: {e}")

# Check data
print("\n2. Checking data...")
try:
    count = pd.read_sql("SELECT COUNT(*) as cnt FROM lastfm_scrobbles", engine)
    print(f"Total rows: {count['cnt'].iloc[0]:,}")
    
    genres_count = pd.read_sql(
        "SELECT COUNT(*) as cnt FROM lastfm_scrobbles WHERE Genres IS NOT NULL AND Genres != '[]'",
        engine
    )
    print(f"Rows with non-empty Genres: {genres_count['cnt'].iloc[0]:,}")
    
    # Show sample
    print("\n3. Sample data:")
    sample = pd.read_sql(
        "SELECT Artist, Track, Genres FROM lastfm_scrobbles LIMIT 5",
        engine
    )
    print(sample.to_string())
    
except Exception as e:
    print(f"✗ Error: {e}")

print("\n" + "=" * 60)
