// === SONGKICK CONCERT EXTRACTOR BOOKMARKLET ===
//
// HOW TO USE:
// 1. Go to https://www.songkick.com/metro-areas/34385-mexico-mexico-city?page=6
// 2. Open browser console (Cmd+Option+J on Mac, F12 on Windows)
// 3. Paste this entire script and press Enter
// 4. The markdown will be copied to your clipboard
// 5. Repeat for pages 7, 8, 9, 10
//
// Or create a bookmarklet: new bookmark with URL set to:
// javascript:void(fetch('https://raw.githubusercontent.com/YOUR_REPO/main/scrapers/bookmarklet.js').then(r=>r.text()).then(eval))
//
// The output matches Format A that parse_markdown.py expects.

(function() {
  const events = document.querySelectorAll('[class*="event-listing"]') .length > 0
    ? document.querySelectorAll('[class*="event-listing"]')
    : document.querySelectorAll('.event-listings li, .events-summary li, ul.event-listings > li');

  // Fallback: grab from the page structure
  const dateHeaders = document.querySelectorAll('h3, .date-header, [class*="date"]');

  let md = '';
  let currentDate = '';

  // Walk through all elements in the concert listing area
  const container = document.querySelector('.event-listings, .events-summary, [class*="metro-area-events"], main, #content, .container');
  if (!container) {
    alert('Could not find concert listing container. Try running on a Songkick metro area page.');
    return;
  }

  // Strategy: find all date groups and their events
  // Songkick uses <h3> or date containers with event lists under them
  const allElements = container.querySelectorAll('*');
  let output = [];
  let curDate = null;

  // Try the structured approach first: look for date + event pairs
  const dateEls = container.querySelectorAll('h3');

  if (dateEls.length > 0) {
    dateEls.forEach(dateEl => {
      const dateText = dateEl.textContent.trim();
      // Check if it looks like a date
      if (/(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+\d{1,2}\s+\w+\s+\d{4}/i.test(dateText)) {
        curDate = dateText;

        // Find sibling event items
        let next = dateEl.nextElementSibling;
        while (next && next.tagName !== 'H3') {
          const links = next.querySelectorAll('a[href*="/concerts/"], a[href*="/festivals/"]');
          links.forEach(link => {
            const href = link.href;
            const artistText = link.textContent.trim();

            // Find venue - look for venue link nearby
            const parent = link.closest('li') || link.closest('[class*="event"]') || link.parentElement;
            const venueLink = parent ? parent.querySelector('a[href*="/venues/"]') : null;

            let venueName = '';
            let venueUrl = '';
            let location = '';

            if (venueLink) {
              venueName = venueLink.textContent.trim();
              venueUrl = venueLink.href;
              // Get location text after venue
              const venueParent = venueLink.parentElement;
              if (venueParent) {
                const fullText = venueParent.textContent.trim();
                const afterVenue = fullText.split(venueName).pop();
                location = afterVenue.replace(/^[\s,]+/, '').trim();
              }
            } else if (parent) {
              // Try to find venue from text
              const spans = parent.querySelectorAll('span, p, div');
              spans.forEach(s => {
                const t = s.textContent.trim();
                if (t.includes('Mexico') && !t.includes(artistText)) {
                  const parts = t.split(',').map(p => p.trim());
                  if (parts.length >= 2) {
                    venueName = parts[0];
                    location = parts.slice(1).join(', ');
                  }
                }
              });
            }

            output.push({ date: curDate, artist: artistText, url: href, venue: venueName, venueUrl, location });
          });
          next = next.nextElementSibling;
        }
      }
    });
  }

  // If structured approach found nothing, try a flat scan
  if (output.length === 0) {
    const allLinks = container.querySelectorAll('a[href*="/concerts/"], a[href*="/festivals/"]');
    allLinks.forEach(link => {
      const href = link.href;
      const artistText = link.textContent.trim();
      if (!artistText || artistText.length < 2) return;

      // Walk up to find date context
      let el = link;
      let dateFound = '';
      for (let i = 0; i < 10 && el; i++) {
        el = el.parentElement;
        if (!el) break;
        const prevH3 = el.querySelector('h3');
        if (prevH3) {
          const dt = prevH3.textContent.trim();
          if (/\d{4}/.test(dt)) { dateFound = dt; break; }
        }
      }

      // Find venue
      const parent = link.closest('li') || link.closest('[class*="event"]') || link.parentElement;
      const venueLink = parent ? parent.querySelector('a[href*="/venues/"]') : null;
      let venueName = '', venueUrl = '', location = '';
      if (venueLink) {
        venueName = venueLink.textContent.trim();
        venueUrl = venueLink.href;
        const vp = venueLink.parentElement;
        if (vp) {
          const ft = vp.textContent.replace(venueName, '').replace(/^[\s,]+/, '').trim();
          location = ft;
        }
      }

      output.push({ date: dateFound || 'Unknown Date', artist: artistText, url: href, venue: venueName, venueUrl, location });
    });
  }

  // Generate Format A markdown
  const page = new URLSearchParams(window.location.search).get('page') || '1';
  let markdown = '';
  let lastDate = '';

  output.forEach(c => {
    if (c.date !== lastDate) {
      lastDate = c.date;
      markdown += `\n- ${c.date}\n`;
    }

    let line = `- [**${c.artist}**](${c.url})`;

    if (c.venue) {
      if (c.venueUrl) {
        line += ` - [${c.venue}](${c.venueUrl})`;
      } else {
        line += ` - ${c.venue}`;
      }
      if (c.location) {
        line += `, ${c.location}`;
      }
    }

    markdown += line + '\n';
  });

  // Copy to clipboard
  navigator.clipboard.writeText(markdown).then(() => {
    const msg = `Extracted ${output.length} concerts from page ${page}.\nMarkdown copied to clipboard!\n\nSave as page${page.padStart(2,'0')}.md`;
    console.log(msg);
    console.log(markdown);
    alert(msg);
  }).catch(() => {
    // Fallback: log to console
    console.log(`=== PAGE ${page} - ${output.length} concerts ===`);
    console.log(markdown);
    alert(`Extracted ${output.length} concerts. Check console for output (clipboard failed).`);
  });
})();
