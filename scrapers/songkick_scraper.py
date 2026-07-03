"""
Songkick CDMX Concert Scraper
Scrapes all upcoming concerts from Songkick's Mexico City metro area.
Outputs a JSON file with structured concert data.
"""

import requests
from bs4 import BeautifulSoup
import json
import re
import time
import sys
from datetime import datetime
from pathlib import Path

BASE_URL = "https://www.songkick.com/metro-areas/34385-mexico-mexico-city"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
}

def parse_date(date_text):
    """Parse Songkick date header into ISO format.
    Input like 'Tuesday 16 June 2026' -> '2026-06-16'
    """
    date_text = date_text.strip()
    # Remove day name if present
    parts = date_text.split()
    if len(parts) == 4:
        # "Tuesday 16 June 2026"
        day, month_name, year = parts[1], parts[2], parts[3]
    elif len(parts) == 3:
        day, month_name, year = parts[0], parts[1], parts[2]
    else:
        return date_text  # Can't parse, return as-is

    try:
        dt = datetime.strptime(f"{day} {month_name} {year}", "%d %B %Y")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return date_text


def scrape_page(page_num):
    """Scrape a single page of Songkick CDMX concerts."""
    url = f"{BASE_URL}?page={page_num}#metro-area-calendar"
    print(f"  Fetching page {page_num}... ", end="", flush=True)

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"FAILED: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    concerts = []
    current_date = None

    # Find the event listings container
    calendar = soup.find("div", id="metro-area-calendar")
    if not calendar:
        # Try the broader container
        calendar = soup

    # Walk through <li> elements — date headers and event items
    for el in calendar.find_all("li"):
        classes = " ".join(el.get("class", []))

        # Date headers: <li class="date-element"> or <li class="after-ad date-element">
        if "date-element" in classes and "event" not in classes:
            # Try <time> element first (has datetime attr), fall back to text
            time_el = el.find("time")
            if time_el and time_el.get("datetime"):
                # datetime="2026-07-02T20:00:00-0600" -> "2026-07-02"
                current_date = time_el["datetime"][:10]
            elif time_el:
                current_date = parse_date(time_el.get_text(strip=True))
            else:
                current_date = parse_date(el.get_text(strip=True))
            continue

        # Event items: <li class="event-listings-element">
        if "event-listings-element" not in classes:
            continue

        concert = {"date": current_date, "source": "songkick"}

        # Artist name(s)
        artist_el = el.find("p", class_="artists")
        if not artist_el:
            artist_el = el.find("a", class_="event-link")
        if artist_el:
            # Get individual artist links
            artist_links = artist_el.find_all("a")
            if artist_links:
                artists = []
                for a in artist_links:
                    name = a.get_text(strip=True)
                    if name and name.lower() not in ("", "more"):
                        artists.append(name)
                concert["artists"] = artists
                concert["artist_display"] = ", ".join(artists) if artists else artist_el.get_text(strip=True)
            else:
                concert["artist_display"] = artist_el.get_text(strip=True)
                concert["artists"] = [concert["artist_display"]]

        # Concert detail URL
        link_el = el.find("a", href=re.compile(r"/concerts/"))
        if not link_el:
            link_el = el.find("a", href=re.compile(r"/festivals/"))
        if link_el:
            href = link_el.get("href", "")
            if href.startswith("/"):
                href = f"https://www.songkick.com{href}"
            concert["url"] = href

        # Venue — now inside <p class="location"> as <a class="venue-link">
        loc_el = el.find("p", class_="location")
        if loc_el:
            venue_link = loc_el.find("a", class_="venue-link")
            if venue_link:
                concert["venue"] = venue_link.get_text(strip=True)
                venue_href = venue_link.get("href", "")
                if venue_href.startswith("/"):
                    venue_href = f"https://www.songkick.com{venue_href}"
                concert["venue_url"] = venue_href
            concert["location"] = loc_el.get_text(strip=True)

        # Type tag (Outdoor, Festival, etc.)
        tag_el = el.find("span", class_="type-tag") or el.find("p", class_="type")
        if tag_el:
            concert["tags"] = [tag_el.get_text(strip=True)]

        # Only add if we got at least an artist or a URL
        if concert.get("artist_display") or concert.get("url"):
            concerts.append(concert)

    print(f"found {len(concerts)} concerts")
    return concerts


def detect_max_pages(soup=None):
    """Detect the total number of pages from the pagination."""
    if soup is None:
        try:
            resp = requests.get(BASE_URL, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(resp.text, "html.parser")
        except:
            return 14  # Fallback

    pagination = soup.find("div", class_="pagination")
    if pagination:
        page_links = pagination.find_all("a")
        max_page = 1
        for link in page_links:
            text = link.get_text(strip=True)
            if text.isdigit():
                max_page = max(max_page, int(text))
        return max_page
    return 14  # Fallback based on previous observation


def run_scraper():
    """Main scraper entry point."""
    print("=" * 60)
    print("Songkick CDMX Concert Scraper")
    print("=" * 60)

    # Detect pages
    print("\nDetecting pagination...")
    max_pages = detect_max_pages()
    print(f"Found {max_pages} pages to scrape\n")

    all_concerts = []
    for page in range(1, max_pages + 1):
        page_concerts = scrape_page(page)
        all_concerts.extend(page_concerts)
        # Be polite
        if page < max_pages:
            time.sleep(1.5)

    # Deduplicate by URL
    seen_urls = set()
    unique_concerts = []
    for c in all_concerts:
        url = c.get("url", "")
        if url and url in seen_urls:
            continue
        if url:
            seen_urls.add(url)
        unique_concerts.append(c)

    # Sort by date
    unique_concerts.sort(key=lambda c: c.get("date") or "9999-99-99")

    # Build output
    output = {
        "source": "songkick",
        "metro_area": "Mexico City",
        "scraped_at": datetime.utcnow().isoformat() + "Z",
        "total_concerts": len(unique_concerts),
        "concerts": unique_concerts,
    }

    # Write JSON
    out_dir = Path(__file__).parent.parent / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "songkick_concerts.json"

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 60}")
    print(f"Done! {len(unique_concerts)} unique concerts saved to:")
    print(f"  {out_path}")
    print(f"{'=' * 60}")

    return output


if __name__ == "__main__":
    run_scraper()
