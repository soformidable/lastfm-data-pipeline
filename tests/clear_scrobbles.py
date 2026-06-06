import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database import get_engine
from sqlalchemy import text

engine = get_engine()

print("=" * 60)
print("WARNING: This will DELETE all scrobbles and re-fetch them")
print("=" * 60)

confirm = input("\nType 'YES' to proceed: ").strip().upper()

if confirm != "YES":
    print("Cancelled.")
    sys.exit(0)

print("\nDeleting all scrobbles...")
try:
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM lastfm_scrobbles"))
    print("✓ All scrobbles deleted")
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)

print("\nNow run your main.py with fetch_genres=True")
print("This will fetch everything fresh with genres included.")
print("\nIn src/main.py, change:")
print("  fetch_all_scrobbles(..., fetch_genres=True)")
print("\nThen run: python src/main.py")
