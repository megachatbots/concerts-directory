"""
Update Concerts Pipeline
Runs the Songkick scraper and copies output to the docs directory.
Designed to be called from GitHub Actions or manually.
"""
import shutil
import sys
from pathlib import Path

# Add scrapers dir to path so we can import
SCRIPT_DIR = Path(__file__).parent
ROOT_DIR = SCRIPT_DIR.parent

sys.path.insert(0, str(SCRIPT_DIR))
from songkick_scraper import run_scraper


def main():
    # Run the scraper
    print("Running Songkick scraper...")
    result = run_scraper()

    if not result or result.get("total_concerts", 0) == 0:
        print("ERROR: Scraper returned no concerts. Aborting update.", file=sys.stderr)
        sys.exit(1)

    total = result["total_concerts"]
    print(f"\nScraper finished: {total} concerts")

    # Safety check — don't publish a suspiciously small result
    if total < 100:
        print(
            f"WARNING: Only {total} concerts found (expected 500+). "
            "Possible scraping issue. Aborting to protect existing data.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Copy JSON to docs/data/ for GitHub Pages
    src = ROOT_DIR / "data" / "songkick_concerts.json"
    dst_dir = ROOT_DIR / "docs" / "data"
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / "songkick_concerts.json"

    shutil.copy2(src, dst)
    print(f"Copied to {dst}")
    print("Done.")


if __name__ == "__main__":
    main()
