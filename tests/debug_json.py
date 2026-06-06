import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database import get_engine
import pandas as pd

engine = get_engine()

print("=" * 70)
print("JSON PARSING DEBUG")
print("=" * 70)

# Get one sample
df = pd.read_sql(
    "SELECT Genres FROM lastfm_scrobbles WHERE Genres IS NOT NULL LIMIT 1",
    engine
)

if df.empty:
    print("No data found!")
    sys.exit(1)

genres_str = df['Genres'].iloc[0]

print("\n1. RAW STRING INFORMATION:")
print("-" * 70)
print("Value: {}".format(genres_str))
print("Type: {}".format(type(genres_str)))
print("Length: {}".format(len(genres_str)))
print("First 50 chars: {}".format(genres_str[:50]))
print("Last 50 chars: {}".format(genres_str[-50:]))

print("\n2. HEX/BYTE REPRESENTATION (first 100 bytes):")
print("-" * 70)
bytes_repr = genres_str.encode('utf-8')[:100]
print(bytes_repr)

print("\n3. TESTING json.loads() DIRECTLY:")
print("-" * 70)
try:
    result = json.loads(genres_str)
    print("✓ json.loads() succeeded!")
    print("Result: {}".format(result))
    print("Result type: {}".format(type(result)))
    print("Is list? {}".format(isinstance(result, list)))
except json.JSONDecodeError as e:
    print("✗ json.loads() failed!")
    print("Error: {}".format(e))
    print("Error at position: {}".format(e.pos))

print("\n4. TESTING AFTER REPLACING QUOTES:")
print("-" * 70)
try:
    replaced = genres_str.replace("'", '"')
    print("After replace: {}".format(replaced[:100]))
    result = json.loads(replaced)
    print("✓ json.loads() on replaced string succeeded!")
    print("Result: {}".format(result))
except json.JSONDecodeError as e:
    print("✗ Still failed!")
    print("Error: {}".format(e))

print("\n5. CHARACTER-BY-CHARACTER CHECK (first 50 chars):")
print("-" * 70)
for i, char in enumerate(genres_str[:50]):
    print("  [{}] {} (ord: {})".format(i, repr(char), ord(char)))

print("\n" + "=" * 70)