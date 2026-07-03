import re
import sys

# This script reads the raw web_fetch markdown files (passed as page content via stdin or files)
# and extracts just the concert listing section for Format A parsing.

def extract_concert_section(raw_content):
    """Extract concert listings between '## 686 upcoming concerts' and pagination links."""
    # Find the start marker - the "upcoming concerts" heading
    start_match = re.search(r'^## \d+ upcoming concerts\s*$', raw_content, re.MULTILINE)
    if not start_match:
        print("WARNING: Could not find 'upcoming concerts' heading", file=sys.stderr)
        return None
    
    start_pos = start_match.end()
    
    # Find the end marker - pagination links
    end_match = re.search(r'^\[← Previous\]', raw_content[start_pos:], re.MULTILINE)
    if end_match:
        end_pos = start_pos + end_match.start()
    else:
        # Try alternate end markers
        end_match = re.search(r'^\- \[Home\]', raw_content[start_pos:], re.MULTILINE)
        if end_match:
            end_pos = start_pos + end_match.start()
        else:
            end_pos = len(raw_content)
    
    section = raw_content[start_pos:end_pos].strip()
    return section

if __name__ == '__main__':
    print("Extract script loaded successfully")
