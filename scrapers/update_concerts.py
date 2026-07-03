"""
Update Concerts Pipeline
Runs all scrapers, merges results, and copies output to the docs directory.
Designed to be called from GitHub Actions or manually.

Songkick always runs (primary source).
Ticketmaster runs only if TICKETMASTER_API_KEY is set.
"""
import os
import shutil
import sys
from pathlib import Path

# Add scrapers dir to path so we can import
SCRIPT_DIR = Path(__file__).parent
ROOT_DIR = SCRIPT_DIR.parent

sys.path.insert(0, str(SCRIPT_DIR))
from songkick_scraper import run_scraper as run_songkick


def main():
    # --- 1. Run Songkick (always) ---
    print("Running Songkick scraper...")
    songkick_result = run_songkick()

    if not songkick_result or songkick_result.get("total_concerts", 0) == 0:
        print("ERROR: Songkick scraper returned no concerts. Aborting.", file=sys.stderr)
        sys.exit(1)

    sk_total = songkick_result["total_concerts"]
    print(f"\nSongkick finished: {sk_total} concerts")

    if sk_total < 100:
        print(
            f"WARNING: Only {sk_total} Songkick concerts (expected 500+). "
            "Possible scraping issue. Aborting to protect existing data.",
            file=sys.stderr,
        )
        sys.exit(1)

    # --- 2. Run Ticketmaster (if API key available) ---
    tm_result = None
    if os.environ.get("TICKETMASTER_API_KEY", "").strip():
        print("\n" + "-" * 60)
        print("Running Ticketmaster scraper...")
        try:
            from ticketmaster_scraper import run_scraper as run_ticketmaster
            tm_result = run_ticketmaster()
            tm_total = tm_result.get("total_concerts", 0) if tm_result else 0
            print(f"\nTicketmaster finished: {tm_total} concerts")
        except Exception as e:
            print(f"WARNING: Ticketmaster scraper failed: {e}", file=sys.stderr)
            print("Continuing with Songkick data only.")
    else:
        print("\nTICKETMASTER_API_KEY not set — skipping Ticketmaster scraper.")

    # --- 3. Merge sources ---
    if tm_result and tm_result.get("total_concerts", 0) > 0:
        print("\n" + "-" * 60)
        print("Merging sources...")
        from merge_sources import run_merge
        merged = run_merge()
        output_file = "concerts_merged.json"
    else:
        print("\nSingle source — using Songkick data directly.")
        output_file = "songkick_concerts.json"

    # --- 4. Copy to docs/data/ for GitHub Pages ---
    src = ROOT_DIR / "data" / output_file
    dst_dir = ROOT_DIR / "docs" / "data"
    dst_dir.mkdir(parents=True, exist_ok=True)

    # Always copy as concerts.json (the frontend reads this name)
    dst = dst_dir / "concerts.json"
    shutil.copy2(src, dst)
    print(f"\nCopied {output_file} → {dst}")

    # Also keep the legacy songkick copy for backward compat
    sk_src = ROOT_DIR / "data" / "songkick_concerts.json"
    sk_dst = dst_dir / "songkick_concerts.json"
    shutil.copy2(sk_src, sk_dst)

    print("Done.")


if __name__ == "__main__":
    main()
