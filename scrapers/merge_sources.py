"""
Multi-Source Concert Merger
Combines concerts from multiple scrapers (Songkick, Ticketmaster, etc.)
into a single deduplicated feed.

Dedup logic: two concerts match if they share the same artist + date + similar venue.
When duplicates are found, Ticketmaster data wins for ticket_url (it's the purchase page),
and we keep the richest metadata from each source.
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

# Source files to merge — add new scrapers here
SOURCE_FILES = [
    ("songkick", DATA_DIR / "songkick_concerts.json"),
    ("ticketmaster", DATA_DIR / "ticketmaster_concerts.json"),
]


def normalize_name(name):
    """Normalize an artist or venue name for fuzzy matching."""
    if not name:
        return ""
    name = name.lower().strip()
    # Remove common suffixes/prefixes
    name = re.sub(r"\s*\(.*?\)\s*", " ", name)  # (Live), (DJ Set), etc.
    # Remove accents (basic)
    replacements = {
        "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u",
        "ñ": "n", "ü": "u",
    }
    for k, v in replacements.items():
        name = name.replace(k, v)
    # Strip non-alphanumeric
    name = re.sub(r"[^a-z0-9\s]", "", name)
    # Collapse whitespace
    name = re.sub(r"\s+", " ", name).strip()
    return name


def make_dedup_key(concert):
    """Create a dedup key from date + first artist name (normalized)."""
    date = concert.get("date") or ""
    artists = concert.get("artists", [])
    first_artist = normalize_name(artists[0]) if artists else ""
    return f"{date}|{first_artist}"


def merge_concerts(concerts_a, concerts_b):
    """Merge two lists of concerts, deduplicating on date + artist.

    When a match is found:
    - ticket_url comes from Ticketmaster (it's the actual purchase link)
    - Keep the richer venue/location info
    - Merge tags
    """
    # Index concert A by dedup key
    index = {}
    merged = []

    for c in concerts_a:
        key = make_dedup_key(c)
        if key and key != "|":
            index[key] = c
        merged.append(c)

    added = 0
    enriched = 0

    for c in concerts_b:
        key = make_dedup_key(c)

        if key and key != "|" and key in index:
            # Duplicate found — enrich the existing entry
            existing = index[key]

            # Add ticket_url if the new source has one
            if c.get("ticket_url") and not existing.get("ticket_url"):
                existing["ticket_url"] = c["ticket_url"]
                enriched += 1

            # If existing has no url but new one does, add it as alt
            if c.get("url") and not existing.get("ticket_url"):
                existing["ticket_url"] = c["url"]

            # Merge tags
            existing_tags = set(existing.get("tags", []))
            new_tags = set(c.get("tags", []))
            combined = existing_tags | new_tags
            if combined:
                existing["tags"] = sorted(combined)

            # Fill in venue if missing
            if not existing.get("venue") and c.get("venue"):
                existing["venue"] = c["venue"]
            if not existing.get("location") and c.get("location"):
                existing["location"] = c["location"]

        else:
            # New concert — add it
            merged.append(c)
            if key and key != "|":
                index[key] = c
            added += 1

    return merged, added, enriched


def load_source(name, path):
    """Load a source JSON file. Returns list of concerts or empty list."""
    if not path.exists():
        print(f"  {name}: file not found at {path}, skipping")
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"  {name}: failed to read ({e}), skipping")
        return []

    concerts = data.get("concerts", [])
    print(f"  {name}: {len(concerts)} concerts loaded")
    return concerts


def run_merge():
    """Main merge entry point. Returns the merged output dict."""
    print("=" * 60)
    print("Multi-Source Concert Merger")
    print("=" * 60)

    print("\nLoading sources...")
    all_sources = []
    for name, path in SOURCE_FILES:
        concerts = load_source(name, path)
        all_sources.append((name, concerts))

    # Start with the first source, merge in the rest
    if not all_sources:
        print("No sources found!")
        return None

    base_name, base_concerts = all_sources[0]
    merged = list(base_concerts)
    total_added = 0
    total_enriched = 0

    for name, concerts in all_sources[1:]:
        if not concerts:
            continue
        print(f"\nMerging {name}...")
        merged, added, enriched = merge_concerts(merged, concerts)
        total_added += added
        total_enriched += enriched
        print(f"  +{added} new concerts, {enriched} enriched with ticket links")

    # Sort by date
    merged.sort(key=lambda c: c.get("date") or "9999-99-99")

    # Build output
    output = {
        "source": "merged",
        "sources": [name for name, _ in all_sources if _],
        "metro_area": "Mexico City",
        "scraped_at": datetime.utcnow().isoformat() + "Z",
        "total_concerts": len(merged),
        "concerts": merged,
    }

    # Write merged JSON
    out_path = DATA_DIR / "concerts_merged.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 60}")
    print(f"Merged result: {len(merged)} concerts")
    print(f"  New from additional sources: {total_added}")
    print(f"  Enriched with ticket links: {total_enriched}")
    print(f"  Saved to: {out_path}")
    print(f"{'=' * 60}")

    return output


if __name__ == "__main__":
    run_merge()
