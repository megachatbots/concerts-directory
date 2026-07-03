# CDMX Concerts

A daily-updated directory of upcoming concerts in the Mexico City metro area, scraped from [Songkick](https://www.songkick.com/metro-areas/34385-mexico-mexico-city).

**Live site:** _[add your GitHub Pages URL here]_

## How it works

A GitHub Action runs daily at midnight CDMX time (6 AM UTC). It scrapes Songkick for all upcoming concerts, outputs structured JSON, and commits the updated data. GitHub Pages serves the `docs/` folder automatically.

```
Songkick → scraper → JSON → git push → GitHub Pages serves docs/
```

## Features

- Search by artist or venue
- Filter by month
- Filter by venue (dropdown)
- Sticky date headers
- Links to Songkick concert and venue pages
- Dark theme, mobile-responsive
- Manual trigger available from the GitHub Actions tab

## Project structure

```
├── .github/workflows/
│   └── update-concerts.yml     # Daily cron + manual trigger
├── scrapers/
│   ├── songkick_scraper.py     # Scrapes Songkick HTML directly
│   ├── update_concerts.py      # Pipeline wrapper (safety checks + file copy)
│   └── parse_markdown.py       # Legacy parser for raw markdown files
├── data/
│   ├── songkick_concerts.json  # Scraper output
│   └── raw/                    # Original scraped markdown (reference)
├── docs/                       # ← GitHub Pages root directory
│   ├── index.html              # Frontend (fetches JSON at runtime)
│   ├── data/songkick_concerts.json
│   └── vercel.json             # Deploy config (legacy)
├── concerts.html               # Standalone version (embedded JSON, works offline)
└── requirements.txt            # Python deps
```

## JSON schema

```json
{
  "source": "songkick",
  "metro_area": "Mexico City",
  "scraped_at": "2026-07-02T06:00:00Z",
  "total_concerts": 671,
  "concerts": [
    {
      "date": "2026-07-03",
      "source": "songkick",
      "artists": ["Artist Name"],
      "artist_display": "Artist Name",
      "url": "https://www.songkick.com/concerts/...",
      "venue": "Foro Sol",
      "venue_url": "https://www.songkick.com/venues/...",
      "location": "Mexico City, Mexico",
      "tags": ["Festival"]
    }
  ]
}
```

## Setup

### Deploy

1. Push this repo to GitHub
2. Go to **Settings → Pages → Source** and select **Deploy from a branch**
3. Set branch to `main` and folder to `/docs`
4. The Action runs daily. You can also trigger it manually from the Actions tab.

### Run locally

```bash
pip install -r requirements.txt
python scrapers/update_concerts.py
```

Then open `docs/index.html` via a local server, or open `concerts.html` directly in a browser.

## Safety checks

The pipeline aborts and preserves existing data if:

- The scraper returns 0 concerts (site down or blocked)
- Fewer than 100 concerts found (partial scrape)

## Data source

All concert data is from [Songkick](https://www.songkick.com). This project is for personal use.
