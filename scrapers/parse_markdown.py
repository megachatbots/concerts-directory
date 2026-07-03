"""
Parse Songkick markdown (from web_fetch) into structured concert JSON.
Handles three markdown formats:
  Format A (pages 1-5): raw web_fetch with [**Artist**](url) and [Venue](url)
  Format B (pages 6-10): cleaned "### Date" headers, "- Artist - Venue, City" lines
  Format C (pages 11-14): plain text with date on own line, artist on next, venue after
Reads .md files from ../data/raw/ and outputs ../data/songkick_concerts.json
"""
import re
import json
from datetime import datetime
from pathlib import Path

MONTH_MAP = {
    'January': '01', 'February': '02', 'March': '03', 'April': '04',
    'May': '05', 'June': '06', 'July': '07', 'August': '08',
    'September': '09', 'October': '10', 'November': '11', 'December': '12'
}

DAY_NAMES = r'(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)'
DATE_PATTERN = re.compile(
    rf'({DAY_NAMES})\s+(\d{{1,2}})\s+(\w+)\s+(\d{{4}})'
)


def parse_date(date_str):
    """Convert 'Saturday 04 July 2026' -> '2026-07-04'"""
    m = DATE_PATTERN.search(date_str)
    if m:
        day = m.group(2).zfill(2)
        month = MONTH_MAP.get(m.group(3), '00')
        year = m.group(4)
        return f"{year}-{month}-{day}"
    return None


def is_date_line(line):
    return bool(DATE_PATTERN.search(line))


def is_venue_line(line):
    return line.rstrip().endswith(', Mexico')


def detect_format(text):
    if '[**' in text and '](https://www.songkick.com/' in text:
        return 'A'
    if re.search(r'^###\s+' + DAY_NAMES, text, re.MULTILINE):
        return 'B'
    return 'C'


def parse_format_a(text):
    """Raw web_fetch format with markdown links."""
    concerts = []
    lines = text.split('\n')
    current_date = None
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        date_match = re.match(r'^-?\s*' + DAY_NAMES + r'\s+\d{1,2}\s+\w+\s+\d{4}', line)
        if date_match:
            current_date = parse_date(line)
            i += 1
            continue

        artist_match = re.search(
            r'\[\*\*(.+?)\*\*(?:\s*(.*?))?\]\((https://www\.songkick\.com/(?:concerts|festivals)/[^\)]+)\)',
            line
        )
        if artist_match and current_date:
            main_artist = artist_match.group(1).strip()
            other_raw = (artist_match.group(2) or '').strip()
            concert_url = artist_match.group(3)

            artists = [main_artist]
            if other_raw:
                others = re.split(r',\s*|\s+and\s+', other_raw)
                artists.extend([a.strip() for a in others if a.strip()])

            artist_display = f"{main_artist}, {other_raw}" if other_raw else main_artist

            venue = venue_url = location = None
            tags = []
            if 'OUTDOOR' in line or '**Outdoor**' in line:
                tags.append('Outdoor')

            for j in range(i, min(i + 5, len(lines))):
                vline = lines[j].strip()
                vm = re.search(
                    r'\[([^\]]+)\]\((https://www\.songkick\.com/venues/[^\)]+)\),\s*(.+)', vline
                )
                if vm:
                    venue, venue_url, location = vm.group(1), vm.group(2), vm.group(3)
                    break
                sm = re.match(r'^-?\s*(.+),\s+([\w\s]+,\s*Mexico)$', vline)
                if sm and not is_date_line(vline):
                    venue, location = sm.group(1), sm.group(2)
                    break

            c = {
                'date': current_date, 'source': 'songkick',
                'artists': artists, 'artist_display': artist_display,
                'url': concert_url,
            }
            if venue: c['venue'] = venue
            if venue_url: c['venue_url'] = venue_url
            if location: c['location'] = location
            if tags: c['tags'] = tags
            concerts.append(c)

        i += 1
    return concerts


def parse_format_b(text):
    """Cleaned format: ### Date headers, - Artist - Venue, City lines."""
    concerts = []
    current_date = None

    for line in text.split('\n'):
        line = line.strip()

        if line.startswith('###') and is_date_line(line):
            current_date = parse_date(line)
            continue

        if line.startswith('- ') and current_date and ' - ' in line[2:]:
            content = line[2:]
            tags = []
            if '(OUTDOOR)' in content:
                tags.append('Outdoor')
                content = re.sub(r'\s*\(OUTDOOR\)\s*', ' ', content).strip()

            parts = content.rsplit(' - ', 1)
            if len(parts) != 2:
                continue
            artist_part, venue_loc = parts[0].strip(), parts[1].strip()

            venue = venue_loc
            location = None
            # Extract "City, Country" from end
            loc_match = re.match(r'^(.+),\s+([\w\s]+,\s*Mexico)$', venue_loc)
            if loc_match:
                venue = loc_match.group(1).strip()
                location = loc_match.group(2).strip()

            # Handle festival "(artist1, artist2)" in parens
            fest = re.match(r'^(.+?)\s*\(([^)]+)\)$', artist_part)
            if fest:
                artists = [fest.group(1).strip()] + [a.strip() for a in fest.group(2).split(',') if a.strip()]
            elif ' and ' in artist_part:
                artists = [a.strip() for a in re.split(r'\s+and\s+', artist_part)]
            else:
                artists = [artist_part]

            c = {
                'date': current_date, 'source': 'songkick',
                'artists': artists, 'artist_display': artist_part,
            }
            if venue: c['venue'] = venue
            if location: c['location'] = location
            if tags: c['tags'] = tags
            concerts.append(c)

    return concerts


def parse_format_c(text):
    """Plain text: date line, then artist line, then venue line."""
    concerts = []
    lines = text.split('\n')
    current_date = None

    # Skip headers — find "upcoming concerts" or first date
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if 'upcoming concerts' in line.lower():
            i += 1
            break
        if is_date_line(line) and not line.startswith('#'):
            break
        i += 1

    SKIP_LINES = {
        'All', 'Tonight', 'This weekend', 'This month',
        'Your favorite artists', 'Filter by artist',
        'Filter by date', 'Filter by genre', 'Sign up Log in',
        'Search for events or artists',
        'Rock', 'Pop', 'Electronic', 'Hip-Hop & Rap', 'R&B',
        'Country', 'Classical', 'Metal', 'Latin', 'Folk & Blues',
        'Jazz', 'Funk & Soul', 'Reggae', 'Punk', 'Alternative',
        'Indie', 'World',
    }

    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        if is_date_line(line) and not line.startswith('#') and not line.startswith('-'):
            current_date = parse_date(line)
            i += 1
            continue

        if line in SKIP_LINES or line.startswith('Page '):
            i += 1
            continue
        if re.match(r'^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)$', line):
            i += 1
            continue
        if re.match(r'^\d{4}$', line):
            i += 1
            continue
        # Skip footer/nav
        if 'songkick' in line.lower() and ('privacy' in line.lower() or 'terms' in line.lower()):
            i += 1
            continue

        if current_date and not is_venue_line(line):
            # Collect artist lines until we hit a venue line
            artist_parts = [line]
            j = i + 1
            venue_line = None
            while j < len(lines):
                nl = lines[j].strip()
                if not nl:
                    j += 1
                    continue
                if is_venue_line(nl):
                    venue_line = nl
                    j += 1
                    break
                if is_date_line(nl):
                    break
                if nl in SKIP_LINES:
                    j += 1
                    continue
                artist_parts.append(nl)
                j += 1

            if venue_line:
                venue = venue_line
                location = None
                loc_m = re.match(r'^(.+),\s+([\w\s]+,\s*Mexico)$', venue_line)
                if loc_m:
                    venue = loc_m.group(1).strip()
                    location = loc_m.group(2).strip()

                artist_display = ', '.join(artist_parts)
                if len(artist_parts) == 1:
                    artists = [artist_parts[0]]
                else:
                    artists = artist_parts

                c = {
                    'date': current_date, 'source': 'songkick',
                    'artists': artists, 'artist_display': artist_display,
                }
                if venue: c['venue'] = venue
                if location: c['location'] = location
                concerts.append(c)

                i = j
                continue

        i += 1
    return concerts


def extract_concerts(md_text):
    fmt = detect_format(md_text)
    if fmt == 'A':
        return parse_format_a(md_text), fmt
    elif fmt == 'B':
        return parse_format_b(md_text), fmt
    else:
        return parse_format_c(md_text), fmt


def main():
    script_dir = Path(__file__).parent
    raw_dir = script_dir.parent / 'data' / 'raw'
    out_dir = script_dir.parent / 'data'
    out_dir.mkdir(parents=True, exist_ok=True)

    all_concerts = []

    if raw_dir.exists():
        for f in sorted(raw_dir.glob('*.md')):
            text = f.read_text(encoding='utf-8')
            page_concerts, fmt = extract_concerts(text)
            print(f"{f.name}: format {fmt}, {len(page_concerts)} concerts")
            all_concerts.extend(page_concerts)

    # Deduplicate
    seen = set()
    unique = []
    for c in all_concerts:
        key = (c.get('date', ''), c.get('artist_display', ''), c.get('venue', ''))
        url = c.get('url', '')
        if url and url in seen:
            continue
        if url:
            seen.add(url)
        if key in seen:
            continue
        seen.add(key)
        unique.append(c)

    unique.sort(key=lambda c: c.get('date') or '9999-99-99')

    output = {
        'source': 'songkick',
        'metro_area': 'Mexico City',
        'scraped_at': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        'total_concerts': len(unique),
        'concerts': unique,
    }

    out_path = out_dir / 'songkick_concerts.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nTotal: {len(unique)} unique concerts -> {out_path}")


if __name__ == '__main__':
    main()
