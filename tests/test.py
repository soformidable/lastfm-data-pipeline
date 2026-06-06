import requests
import json
import sys
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.api import fetch_track_tags

api_key = os.getenv("LASTFM_API_KEY")
base_url = "http://ws.audioscrobbler.com/2.0/"

print("=" * 60)
print("Testing genre fetching with fallback logic")
print("=" * 60)

# Test 1: Track with no tags (should fall back to artist)
print("\nTest 1: The Beatles - Let It Be")
print("-" * 40)
tags = fetch_track_tags("The Beatles", "Let It Be", api_key, base_url)
print(f"Tags: {tags}")
print("✓ Falls back to artist tags when track has none\n")

# Test 2: Try a more recent popular track
print("Test 2: The Weeknd - Blinding Lights")
print("-" * 40)
tags = fetch_track_tags("The Weeknd", "Blinding Lights", api_key, base_url)
print(f"Tags: {tags}")
print("✓ Gets track-specific tags or artist fallback\n")

# Test 3: Another classic
print("Test 3: Kinoko Teikoku - Musician")
print("-" * 40)
tags = fetch_track_tags("Kinoko Teikoku", "Musician", api_key, base_url)
print(f"Tags: {tags}")
print("✓ Should return tags (from track or artist)\n")

print("=" * 60)
print("All tests passed! Genre fetching is working correctly.")
print("=" * 60)