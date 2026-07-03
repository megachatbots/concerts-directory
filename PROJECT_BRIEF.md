# CDMX Concerts Directory — Project Brief

## What It Is

A self-contained concert directory for the Mexico City metro area, scraped from Songkick. Opens as a single HTML file — no server, no install, no dependencies.

**concerts.html** — double-click to open. 671 concerts from Jun 24, 2026 through May 22, 2027, with search, month filter, and venue dropdown.

---

## What Was Built

### Data Pipeline

1. **Scraping** — 14 pages of Songkick listings fetched via `web_fetch` and saved as markdown files (`data/raw/page01.md` through `page14.md`).

2. **Parsing** — `scrapers/parse_markdown.py` converts three markdown formats into a single normalized JSON:
   - **Format A** (pages 01–10): Full markdown with concert URLs, venue URLs, and structured artist/venue data. This is the target format.
   - **Format B** (original pages 06–10, now converted): Multi-line entries without URLs. These were re-fetched and overwritten with Format A.
   - **Format C** (pages 11–14): Simpler format without URLs. Not yet converted — 171 concerts with venue names but no links.

3. **Output** — `data/songkick_concerts.json`: 671 concerts, each with date, artists, artist_display, venue, location, and (where available) concert URL and venue URL.

### Frontend

- `site/index.html` — Dark-themed single-page app. Fetches JSON from `site/data/`. Requires an HTTP server (or localhost) to work.
- `concerts.html` — Standalone version with JSON embedded inline. Works from `file://` — just open from Finder.

Both versions have: text search across artists and venues, month picker, venue dropdown, sticky date headers, mobile-responsive layout, and links to Songkick concert/venue pages.

---

## Key Numbers

| Metric | Value |
|---|---|
| Total concerts | 671 |
| With concert URL | 500 |
| With venue URL | 500 |
| Without URLs (Format C, pages 11–14) | 171 |
| Unique venues | 102 |
| Date range | Jun 24, 2026 – May 22, 2027 |

---

## File Structure

```
concerts-directory/
├── concerts.html              # Standalone — open this (264K)
├── data/
│   ├── raw/
│   │   ├── page01.md … page14.md   # Raw scraped markdown
│   │   └── test.txt, test2.txt
│   └── songkick_concerts.json       # Parsed JSON (256K)
├── scrapers/
│   ├── parse_markdown.py            # Main parser (3 formats → JSON)
│   ├── songkick_scraper.py          # Scraper script
│   ├── extract_and_save.py          # Extraction helper
│   ├── bookmarklet.js               # Browser bookmarklet
│   └── BOOKMARKLET_INSTRUCTIONS.md
└── site/
    ├── index.html                   # Server-dependent version
    ├── data/songkick_concerts.json  # Copy for site
    └── vercel.json                  # Deploy config
```

---

## Bugs Fixed

- **Venue off-by-one** — `parse_format_a()` venue look-ahead started at `i+1` instead of `i`, assigning every concert the *next* concert's venue. Fixed by starting the search at `i`.
- **JSON field name** — Code referenced `concert_url` but the actual field is `url`.
- **CORS on file://** — `fetch()` fails when HTML is opened via `file://` protocol. Solved by creating `concerts.html` with embedded JSON data.

---

## What's Left

- **Pages 11–14 (Format C)**: 171 concerts without Songkick URLs. Could be re-fetched in Format A to add links.
- **Deployment**: `site/` folder has a `vercel.json` ready for hosting if needed.
- **Auto-refresh**: The scraper pipeline could be scheduled to re-fetch and regenerate periodically.
