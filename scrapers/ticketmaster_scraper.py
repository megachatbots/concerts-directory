"""
Ticketmaster CDMX Concert Scraper
Fetches upcoming concerts in Mexico City via the Ticketmaster Discovery API.
Outputs a JSON file with the same schema as the Songkick scraper.

Requires a TICKETMASTER_API_KEY environment variable.
Get one free at https://developer.ticketmaster.com/
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests

API_BASE = "https://app.ticketmaster.com/discovery/v2/events.json"
CDMX_LATLONG = "19.4326,-99.1332"
SEARCH_RADIUS = "60"  # miles — covers greater CDMX metro
COUNTRY_CODE = "MX"
CLASSIFICATION = "music"
PAGE_SIZE = 200  # max allowed by the API


def get_api_key():
    """Get Ticketmaster API key from environment."""
    key = os.environ.get("TICKETMASTER_API_KEY", "").strip()
    if not key:
        print(
            "ERROR: TICKETMASTER_API_KEY environment variable not set.\n"
            "Get a free key at https://developer.ticketmaster.com/",
            file=sys.stderr,
        )
        sys.exit(1)
    return key


def fetch_page(api_key, page=0, start_date=None, end_date=None):
    """Fetch a single page of events from the Discovery API."""
    params = {
        "apikey": api_key,
        "countryCode": COUNTRY_CODE,
        "latlong": CDMX_LATLONG,
        "radius": SEARCH_RADIUS,
        "unit": "miles",
        "classificationName": CLASSIFICATION,
        "size": PAGE_SIZE,
        "page": page,
        "sort": "date,asc",
        "locale": "en-us,es",
    }
    if start_date:
        params["startDateTime"] = f"{start_date}T00:00:00Z"
    if end_date:
        params["endDateTime"] = f"{end_date}T23:59:59Z"

    resp = requests.get(API_BASE, params=params, timeout=20)
    resp.raise_for_status()
    return resp.json()


def parse_event(event):
    """Convert a Ticketmaster event object to our normalized schema."""
    # Date
    date_info = event.get("dates", {}).get("start", {})
    date_str = date_info.get("localDate")  # "2026-07-15"

    # Artists / attractions
    attractions = event.get("_embedded", {}).get("attractions", [])
    artists = [a["name"] for a in attractions if a.get("name")]
    if not artists:
        # Fall back to event name
        artists = [event.get("name", "Unknown")]
    artist_display = ", ".join(artists)

    # Venue
    venues = event.get("_embedded", {}).get("venues", [])
    venue_name = ""
    venue_city = ""
    if venues:
        v = venues[0]
        venue_name = v.get("name", "")
        city_info = v.get("city", {})
        state_info = v.get("state", {})
        country_info = v.get("country", {})
        city_parts = [
            city_info.get("name", ""),
            state_info.get("name", ""),
            country_info.get("name", ""),
        ]
        venue_city = ", ".join(p for p in city_parts if p)

    # URLs
    event_url = event.get("url", "")  # Ticketmaster purchase page

    # Tags / classification
    tags = []
    classifications = event.get("classifications", [])
    if classifications:
        c = classifications[0]
        genre = c.get("genre", {}).get("name", "")
        subgenre = c.get("subGenre", {}).get("name", "")
        if genre and genre.lower() != "undefined":
            tags.append(genre)
        if subgenre and subgenre.lower() != "undefined" and subgenre != genre:
            tags.append(subgenre)

    concert = {
        "date": date_str,
        "source": "ticketmaster",
        "artists": artists,
        "artist_display": artist_display,
        "url": event_url,
        "ticket_url": event_url,  # Ticketmaster URLs ARE the ticket purchase page
        "venue": venue_name,
        "location": venue_city,
    }
    if tags:
        concert["tags"] = tags

    return concert


def run_scraper():
    """Main scraper entry point. Returns the output dict."""
    print("=" * 60)
    print("Ticketmaster CDMX Concert Scraper")
    print("=" * 60)

    api_key = get_api_key()

    # Search window: today through 12 months out
    today = datetime.utcnow().strftime("%Y-%m-%d")
    end = (datetime.utcnow() + timedelta(days=365)).strftime("%Y-%m-%d")
    print(f"\nDate range: {today} to {end}")

    all_events = []
    page = 0

    while True:
        print(f"  Fetching page {page}... ", end="", flush=True)
        try:
            data = fetch_page(api_key, page=page, start_date=today, end_date=end)
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 429:
                print("rate limited, waiting 2s...")
                time.sleep(2)
                continue
            print(f"FAILED: {e}")
            break
        except requests.RequestException as e:
            print(f"FAILED: {e}")
            break

        embedded = data.get("_embedded", {})
        events = embedded.get("events", [])
        print(f"found {len(events)} events")

        if not events:
            break

        all_events.extend(events)

        # Check pagination
        page_info = data.get("page", {})
        total_pages = page_info.get("totalPages", 1)
        total_elements = page_info.get("totalElements", 0)
        print(
            f"    (page {page + 1}/{total_pages}, "
            f"{total_elements} total events in API)"
        )

        page += 1
        if page >= total_pages:
            break

        # The API caps deep paging at page * size <= 1000
        if page * PAGE_SIZE >= 1000:
            print("  Reached API deep-paging limit (1000 events)")
            break

        # Rate limit courtesy: ~2 req/sec
        time.sleep(0.6)

    # Parse into normalized schema
    print(f"\nParsing {len(all_events)} raw events...")
    concerts = []
    seen_ids = set()

    for ev in all_events:
        ev_id = ev.get("id", "")
        if ev_id in seen_ids:
            continue
        seen_ids.add(ev_id)

        concert = parse_event(ev)
        if concert.get("date") and concert.get("artist_display"):
            concerts.append(concert)

    # Sort by date
    concerts.sort(key=lambda c: c.get("date") or "9999-99-99")

    # Build output
    output = {
        "source": "ticketmaster",
        "metro_area": "Mexico City",
        "scraped_at": datetime.utcnow().isoformat() + "Z",
        "total_concerts": len(concerts),
        "concerts": concerts,
    }

    # Write JSON
    out_dir = Path(__file__).parent.parent / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "ticketmaster_concerts.json"

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 60}")
    print(f"Done! {len(concerts)} concerts saved to:")
    print(f"  {out_path}")
    print(f"{'=' * 60}")

    return output


if __name__ == "__main__":
    run_scraper()
