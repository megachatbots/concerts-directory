# Songkick Concert Extractor — Bookmarklet

## Quick Method (Console)

1. Open a Songkick page, e.g.:
   `https://www.songkick.com/metro-areas/34385-mexico-mexico-city?page=6`
2. Open DevTools → Console (Cmd+Option+J)
3. Paste the contents of `bookmarklet.js` and press Enter
4. The markdown gets copied to your clipboard
5. Replace the matching `data/raw/pageNN.md` file with the clipboard content
6. Repeat for pages 7–10

## After All Pages Are Updated

Run the parser to regenerate the JSON with URLs:

```bash
cd OUTPUTS/concerts-directory
python scrapers/parse_markdown.py
cp data/songkick_concerts.json site/data/
```

## What It Extracts

- Concert URL (`/concerts/...` or `/festivals/...`)
- Venue URL (`/venues/...`)
- Artist name
- Venue name and location
- Date grouping

Output is in Format A markdown (same as pages 1–5), so the existing parser handles it directly.
