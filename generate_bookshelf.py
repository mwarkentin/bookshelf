#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# ///
"""
Generate a static bookshelf HTML page from a Book Tracker CSV export.

Usage:
    ./generate_bookshelf.py "Book Tracker.csv" -o bookshelf.html
"""

import argparse
import csv
import html
import io
from datetime import datetime
from collections import defaultdict


STATUS_ORDER = ["reading", "read", "unread", "dnf"]
STATUS_LABELS = {
    "reading": "Currently Reading",
    "read": "Read",
    "unread": "To Read",
    "dnf": "Did Not Finish",
}
STATUS_EMOJI = {
    "reading": "📖",
    "read": "✅",
    "unread": "📋",
    "dnf": "🚫",
}


EXCLUDED_TAGS = {"private", "caleb", "zachary", "lindsay"}


def is_private(book):
    """Return True if the book has any excluded tag (case-insensitive)."""
    tags = book.get("tags", "") or ""
    # Tags use format "name|||#color;name|||#color" or just "name;name"
    for tag in tags.split(";"):
        label = tag.split("|||")[0].strip()
        if label.lower() in EXCLUDED_TAGS:
            return True
    return False


def parse_csv(path):
    books = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not is_private(row):
                books.append(row)
    return books


def sort_key(book):
    """Sort by end date descending (most recent first), then start date, then title."""
    end = book.get("endReading", "") or ""
    start = book.get("startReading", "") or ""
    title = book.get("title", "") or ""
    # Invert dates for descending sort
    return (end == "", end, start == "", start, title)


def format_author(raw):
    """Convert 'Last,First' or 'Last,First;Last2,First2' to readable names."""
    if not raw:
        return ""
    parts = raw.split(";")
    names = []
    for p in parts:
        p = p.strip()
        if "," in p:
            last, first = p.split(",", 1)
            names.append(f"{first.strip()} {last.strip()}")
        else:
            names.append(p)
    return ", ".join(names)


def reading_duration(start, end):
    """Return number of days between start and end date strings."""
    if not start or not end:
        return None
    try:
        s = datetime.strptime(start, "%Y-%m-%d")
        e = datetime.strptime(end, "%Y-%m-%d")
        delta = (e - s).days
        return max(delta, 1)
    except ValueError:
        return None


def compute_stats(books):
    stats = {}
    read_books = [b for b in books if b.get("readingStatus") == "read"]
    stats["total"] = len(books)
    stats["read"] = len(read_books)
    stats["reading"] = sum(1 for b in books if b.get("readingStatus") == "reading")
    stats["unread"] = sum(1 for b in books if b.get("readingStatus") == "unread")
    stats["dnf"] = sum(1 for b in books if b.get("readingStatus") == "dnf")

    total_pages = 0
    durations = []
    years = defaultdict(int)
    for b in read_books:
        pages = b.get("pages", "")
        if pages:
            try:
                total_pages += int(pages)
            except ValueError:
                pass
        d = reading_duration(b.get("startReading", ""), b.get("endReading", ""))
        if d is not None:
            durations.append(d)
        end = b.get("endReading", "")
        if end:
            years[end[:4]] += 1

    stats["total_pages"] = total_pages
    stats["avg_duration"] = round(sum(durations) / len(durations), 1) if durations else 0
    stats["books_by_year"] = dict(sorted(years.items(), reverse=True))
    return stats


def escape(text):
    return html.escape(text or "", quote=True)


def generate_html(books, stats):
    grouped = defaultdict(list)
    for b in books:
        status = b.get("readingStatus", "unread") or "unread"
        grouped[status].append(b)

    # Sort each group
    for status in grouped:
        if status == "read":
            # Most recently finished first
            grouped[status].sort(key=lambda b: b.get("endReading", "") or "", reverse=True)
        elif status == "reading":
            grouped[status].sort(key=lambda b: b.get("startReading", "") or "", reverse=True)
        else:
            grouped[status].sort(key=lambda b: (b.get("title", "") or "").lower())

    out = io.StringIO()
    w = out.write

    w("<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n")
    w("<meta charset=\"utf-8\">\n")
    w("<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n")
    w("<title>Bookshelf</title>\n")
    w("<style>\n")
    w(CSS)
    w("\n</style>\n</head>\n<body>\n")

    # Header
    w("<header>\n")
    w("  <h1>Bookshelf</h1>\n")
    w("  <p class=\"subtitle\">A personal reading log</p>\n")
    w("</header>\n\n")

    # Stats bar
    w("<section class=\"stats\">\n")
    w(f"  <div class=\"stat\"><span class=\"stat-num\">{stats['read']}</span><span class=\"stat-label\">Read</span></div>\n")
    w(f"  <div class=\"stat\"><span class=\"stat-num\">{stats['reading']}</span><span class=\"stat-label\">Reading</span></div>\n")
    w(f"  <div class=\"stat\"><span class=\"stat-num\">{stats['unread']}</span><span class=\"stat-label\">To Read</span></div>\n")
    w(f"  <div class=\"stat\"><span class=\"stat-num\">{stats['total_pages']:,}</span><span class=\"stat-label\">Pages Read</span></div>\n")
    w(f"  <div class=\"stat\"><span class=\"stat-num\">{stats['avg_duration']}</span><span class=\"stat-label\">Avg Days/Book</span></div>\n")
    w("</section>\n\n")

    # Year breakdown
    if stats["books_by_year"]:
        w("<section class=\"year-bar\">\n")
        for year, count in stats["books_by_year"].items():
            w(f"  <span class=\"year-chip\">{year}: {count} book{'s' if count != 1 else ''}</span>\n")
        w("</section>\n\n")

    # Book sections
    for status in STATUS_ORDER:
        section_books = grouped.get(status, [])
        if not section_books:
            continue
        label = STATUS_LABELS.get(status, status)
        emoji = STATUS_EMOJI.get(status, "")
        w(f"<section class=\"book-section\">\n")
        w(f"  <h2>{emoji} {label} <span class=\"count\">({len(section_books)})</span></h2>\n")
        w(f"  <div class=\"book-grid\">\n")

        for b in section_books:
            title = escape(b.get("title", ""))
            subtitle = escape(b.get("subtitle", ""))
            author = escape(format_author(b.get("authors", "")))
            cover = b.get("thumbnailRemoteImageUrl", "") or b.get("remoteImageUrl", "")
            pages = b.get("pages", "")
            series = escape(b.get("series", ""))
            series_num = escape(b.get("seriesNumber", ""))
            start = b.get("startReading", "")
            end = b.get("endReading", "")
            categories = b.get("categories", "")
            book_type = b.get("types", "")
            link = b.get("externalLink", "")

            duration = reading_duration(start, end)

            w(f"    <div class=\"book-card\">\n")

            # Cover
            if cover:
                w(f"      <div class=\"book-cover\"><img src=\"{escape(cover)}\" alt=\"{title}\" loading=\"lazy\"></div>\n")
            else:
                w(f"      <div class=\"book-cover no-cover\"><span>{title[:2].upper()}</span></div>\n")

            w(f"      <div class=\"book-info\">\n")

            # Title
            if link:
                w(f"        <h3 class=\"book-title\"><a href=\"{escape(link)}\" rel=\"noopener\">{title}</a></h3>\n")
            else:
                w(f"        <h3 class=\"book-title\">{title}</h3>\n")

            if subtitle:
                w(f"        <p class=\"book-subtitle\">{subtitle}</p>\n")

            if author:
                w(f"        <p class=\"book-author\">{author}</p>\n")

            # Meta line
            meta_parts = []
            if pages:
                meta_parts.append(f"{pages} pp")
            if series:
                s = series
                if series_num:
                    s += f" #{series_num}"
                meta_parts.append(s)
            if book_type:
                type_display = book_type.replace(";", ", ").replace("_", " ").title()
                meta_parts.append(type_display)
            if meta_parts:
                w(f"        <p class=\"book-meta\">{' · '.join(meta_parts)}</p>\n")

            # Dates
            if status == "read" and end:
                date_str = f"Finished {end}"
                if duration:
                    date_str += f" ({duration} day{'s' if duration != 1 else ''})"
                w(f"        <p class=\"book-dates\">{date_str}</p>\n")
            elif status == "reading" and start:
                w(f"        <p class=\"book-dates\">Started {start}</p>\n")

            # Categories as small tags
            if categories:
                cats = [c.strip() for c in categories.split(";") if c.strip()]
                if cats:
                    w(f"        <div class=\"book-tags\">\n")
                    for cat in cats[:4]:  # limit to 4 tags
                        w(f"          <span class=\"tag\">{escape(cat)}</span>\n")
                    w(f"        </div>\n")

            w(f"      </div>\n")  # book-info
            w(f"    </div>\n")  # book-card

        w(f"  </div>\n")  # book-grid
        w(f"</section>\n\n")

    # Footer
    w("<footer>\n")
    now = datetime.now().strftime("%Y-%m-%d")
    w(f"  <p>Generated on {now}</p>\n")
    w("</footer>\n")

    w("</body>\n</html>\n")
    return out.getvalue()


CSS = """
:root {
  --bg: #fafaf9;
  --fg: #1c1917;
  --muted: #78716c;
  --border: #e7e5e4;
  --card-bg: #ffffff;
  --accent: #292524;
  --tag-bg: #f5f5f4;
  --tag-fg: #57534e;
  --link: #1d4ed8;
  --stat-bg: #f5f5f4;
}

@media (prefers-color-scheme: dark) {
  :root {
    --bg: #1c1917;
    --fg: #fafaf9;
    --muted: #a8a29e;
    --border: #292524;
    --card-bg: #292524;
    --accent: #e7e5e4;
    --tag-bg: #44403c;
    --tag-fg: #d6d3d1;
    --link: #93b4fd;
    --stat-bg: #292524;
  }
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background: var(--bg);
  color: var(--fg);
  line-height: 1.5;
  max-width: 960px;
  margin: 0 auto;
  padding: 2rem 1rem;
}

a { color: var(--link); text-decoration: none; }
a:hover { text-decoration: underline; }

header { margin-bottom: 2rem; }
header h1 { font-size: 1.75rem; font-weight: 700; letter-spacing: -0.02em; }
.subtitle { color: var(--muted); font-size: 0.95rem; }

/* Stats */
.stats {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
  margin-bottom: 1rem;
}
.stat {
  background: var(--stat-bg);
  border-radius: 8px;
  padding: 0.75rem 1rem;
  display: flex;
  flex-direction: column;
  min-width: 100px;
}
.stat-num { font-size: 1.5rem; font-weight: 700; }
.stat-label { font-size: 0.75rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; }

/* Year chips */
.year-bar {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-bottom: 2rem;
}
.year-chip {
  font-size: 0.8rem;
  color: var(--muted);
  background: var(--tag-bg);
  padding: 0.25rem 0.6rem;
  border-radius: 999px;
}

/* Sections */
.book-section { margin-bottom: 2.5rem; }
.book-section h2 {
  font-size: 1.15rem;
  font-weight: 600;
  margin-bottom: 1rem;
  border-bottom: 1px solid var(--border);
  padding-bottom: 0.5rem;
}
.book-section h2 .count { color: var(--muted); font-weight: 400; }

/* Grid */
.book-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1rem;
}

/* Card */
.book-card {
  display: flex;
  gap: 0.75rem;
  padding: 0.75rem;
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 8px;
}

.book-cover {
  flex-shrink: 0;
  width: 64px;
  height: 96px;
  border-radius: 4px;
  overflow: hidden;
  background: var(--tag-bg);
}
.book-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.book-cover.no-cover {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--muted);
}

.book-info {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  min-width: 0;
  overflow: hidden;
}

.book-title {
  font-size: 0.9rem;
  font-weight: 600;
  line-height: 1.3;
}
.book-title a { color: inherit; }
.book-title a:hover { color: var(--link); }

.book-subtitle { font-size: 0.8rem; color: var(--muted); font-style: italic; }
.book-author { font-size: 0.8rem; color: var(--muted); }
.book-meta { font-size: 0.75rem; color: var(--muted); }
.book-dates { font-size: 0.75rem; color: var(--muted); }

.book-tags { display: flex; flex-wrap: wrap; gap: 0.25rem; margin-top: 0.2rem; }
.tag {
  font-size: 0.65rem;
  background: var(--tag-bg);
  color: var(--tag-fg);
  padding: 0.1rem 0.4rem;
  border-radius: 999px;
  white-space: nowrap;
}

footer {
  margin-top: 3rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border);
  font-size: 0.8rem;
  color: var(--muted);
}

@media (max-width: 600px) {
  .stats { gap: 0.5rem; }
  .stat { min-width: 80px; padding: 0.5rem 0.75rem; }
  .stat-num { font-size: 1.2rem; }
  .book-grid { grid-template-columns: 1fr; }
}
"""


def main():
    parser = argparse.ArgumentParser(description="Generate a static bookshelf page from Book Tracker CSV.")
    parser.add_argument("csv_file", help="Path to the Book Tracker CSV export")
    parser.add_argument("-o", "--output", default="bookshelf.html", help="Output HTML file (default: bookshelf.html)")
    args = parser.parse_args()

    books = parse_csv(args.csv_file)
    stats = compute_stats(books)
    html_content = generate_html(books, stats)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"Generated {args.output} with {len(books)} books.")


if __name__ == "__main__":
    main()
