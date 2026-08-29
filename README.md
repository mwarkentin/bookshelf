# Bookshelf

A static website generator that turns [Book Tracker](https://booktrack.app) CSV exports into a personal reading log, hosted at [bookshelf.michaelwarkentin.com](https://bookshelf.michaelwarkentin.com).

## Features

- Generates a responsive, light/dark themed HTML page from a Book Tracker CSV export
- Groups books by reading status: Currently Reading, Read, To Read, and Did Not Finish
- Organizes read books by year with most recently finished first
- Displays reading stats: total pages read, average days per book, average pages per day, and per-year breakdowns
- Estimates reading time for unread books based on your historical pace
- Filters out books tagged as private
- Supports cover images, series info, categories, and external links
- Zero dependencies beyond Python 3.10+ (runs as a [uv script](https://docs.astral.sh/uv/guides/scripts/))

## Usage

```sh
./generate_bookshelf.py "Book Tracker.csv" -o bookshelf.html
```

Or with uv explicitly:

```sh
uv run generate_bookshelf.py "Book Tracker.csv" -o bookshelf.html
```

### Options

| Flag | Description | Default |
|------|-------------|---------|
| `csv_file` | Path to the Book Tracker CSV export | (required) |
| `-o`, `--output` | Output HTML file path | `bookshelf.html` |

## Exporting Data from Book Tracker

This project uses CSV exports from [Book Tracker](https://booktrack.app). To export your library:

1. Open **Book Tracker** on your device
2. Go to **Settings** > **Export**
3. Select **CSV** as the export format
4. Optionally apply a filter to export a subset of your library
5. Save or share the file (via Files, AirDrop, Mail, etc.)

The CSV export includes book metadata like titles, authors, page counts, reading dates, status, categories, and cover image URLs. Note that CSV exports do not include all data (such as quotes or reading progress logs) -- only full backups contain the complete database.

For more details, see the official tutorial: [How to export your library from Book Tracker](https://booktrack.app/tutorial/how-to-export-your-library-from-book-tracker/).

## Running Tests

```sh
python -m unittest test_generate_bookshelf.py
```

## How It Works

The script reads the exported CSV, filters out private books (those tagged with excluded tags), computes reading statistics, and generates a single self-contained HTML file with all styles inlined. The generated page is deployed to GitHub Pages via the `CNAME` configuration.

## License

MIT
