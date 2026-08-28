import unittest
from generate_bookshelf import (
    format_author,
    reading_duration,
    is_private,
    compute_stats,
    generate_html,
    escape,
)


def make_book(**overrides):
    defaults = {
        "title": "Test Book",
        "subtitle": "",
        "authors": "Doe,Jane",
        "readingStatus": "read",
        "pages": "300",
        "startReading": "2025-01-01",
        "endReading": "2025-01-11",
        "series": "",
        "seriesNumber": "",
        "types": "Paperback",
        "categories": "Fiction",
        "tags": "",
        "thumbnailRemoteImageUrl": "",
        "remoteImageUrl": "",
        "externalLink": "",
    }
    defaults.update(overrides)
    return defaults


class TestFormatAuthor(unittest.TestCase):
    def test_single_author(self):
        self.assertEqual(format_author("Sanderson,Brandon"), "Brandon Sanderson")

    def test_multiple_authors(self):
        self.assertEqual(
            format_author("Doe,Jane;Smith,John"), "Jane Doe, John Smith"
        )

    def test_empty(self):
        self.assertEqual(format_author(""), "")

    def test_no_comma(self):
        self.assertEqual(format_author("Mononym"), "Mononym")


class TestReadingDuration(unittest.TestCase):
    def test_normal(self):
        self.assertEqual(reading_duration("2025-01-01", "2025-01-11"), 10)

    def test_same_day(self):
        self.assertEqual(reading_duration("2025-01-01", "2025-01-01"), 1)

    def test_missing_start(self):
        self.assertIsNone(reading_duration("", "2025-01-11"))

    def test_missing_end(self):
        self.assertIsNone(reading_duration("2025-01-01", ""))

    def test_invalid_date(self):
        self.assertIsNone(reading_duration("not-a-date", "2025-01-11"))


class TestIsPrivate(unittest.TestCase):
    def test_not_private(self):
        self.assertFalse(is_private({"tags": "scifi|||#ff0000"}))

    def test_private_tag(self):
        self.assertTrue(is_private({"tags": "private|||#000000"}))

    def test_excluded_tag_case_insensitive(self):
        self.assertTrue(is_private({"tags": "Private|||#000"}))

    def test_empty_tags(self):
        self.assertFalse(is_private({"tags": ""}))

    def test_multiple_tags_one_excluded(self):
        self.assertTrue(is_private({"tags": "scifi|||#fff;caleb|||#000"}))


class TestComputeStats(unittest.TestCase):
    def setUp(self):
        self.books = [
            make_book(title="A", readingStatus="read", pages="300",
                      startReading="2025-01-01", endReading="2025-01-11"),
            make_book(title="B", readingStatus="read", pages="200",
                      startReading="2025-06-01", endReading="2025-06-11"),
            make_book(title="C", readingStatus="reading", pages="400"),
            make_book(title="D", readingStatus="unread", pages="500"),
            make_book(title="E", readingStatus="read", pages="100",
                      startReading="2026-03-01", endReading="2026-03-06"),
        ]

    def test_counts(self):
        stats = compute_stats(self.books)
        self.assertEqual(stats["read"], 3)
        self.assertEqual(stats["reading"], 1)
        self.assertEqual(stats["unread"], 1)

    def test_total_pages(self):
        stats = compute_stats(self.books)
        self.assertEqual(stats["total_pages"], 600)

    def test_avg_duration(self):
        stats = compute_stats(self.books)
        # durations: 10, 10, 5 -> avg 8.3
        self.assertAlmostEqual(stats["avg_duration"], 8.3, places=1)

    def test_avg_pages_per_day(self):
        stats = compute_stats(self.books)
        # 300/10 + 200/10 + 100/5 -> 600 pages / 25 days = 24.0
        self.assertAlmostEqual(stats["avg_pages_per_day"], 24.0, places=1)

    def test_books_by_year(self):
        stats = compute_stats(self.books)
        self.assertEqual(stats["books_by_year"], {"2026": 1, "2025": 2})

    def test_no_read_books(self):
        stats = compute_stats([make_book(readingStatus="unread")])
        self.assertEqual(stats["read"], 0)
        self.assertEqual(stats["total_pages"], 0)
        self.assertEqual(stats["avg_pages_per_day"], 0)

    def test_read_book_without_dates(self):
        books = [make_book(startReading="", endReading="", pages="200")]
        stats = compute_stats(books)
        self.assertEqual(stats["total_pages"], 200)
        self.assertEqual(stats["avg_pages_per_day"], 0)
        self.assertEqual(stats["books_by_year"], {})


class TestGenerateHTML(unittest.TestCase):
    def setUp(self):
        self.books = [
            make_book(title="Read 2025", readingStatus="read", pages="300",
                      startReading="2025-01-01", endReading="2025-01-11"),
            make_book(title="Read 2026", readingStatus="read", pages="200",
                      startReading="2026-03-01", endReading="2026-03-11"),
            make_book(title="Now Reading", readingStatus="reading", pages="400",
                      startReading="2025-05-01", endReading=""),
            make_book(title="Want to Read", readingStatus="unread", pages="500",
                      startReading="", endReading=""),
            make_book(title="Gave Up", readingStatus="dnf", pages="150",
                      startReading="", endReading=""),
        ]
        self.stats = compute_stats(self.books)
        self.html = generate_html(self.books, self.stats)

    def test_section_ids(self):
        self.assertIn('id="section-reading"', self.html)
        self.assertIn('id="section-read"', self.html)
        self.assertIn('id="section-unread"', self.html)
        self.assertIn('id="section-dnf"', self.html)

    def test_stat_links(self):
        self.assertIn('href="#section-reading" class="stat"', self.html)
        self.assertIn('href="#section-read" class="stat"', self.html)
        self.assertIn('href="#section-unread" class="stat"', self.html)

    def test_stats_order(self):
        reading_pos = self.html.index("#section-reading")
        read_pos = self.html.index('#section-read"')
        unread_pos = self.html.index("#section-unread")
        self.assertLess(reading_pos, read_pos)
        self.assertLess(read_pos, unread_pos)

    def test_year_headings_in_read_section(self):
        self.assertIn('class="year-heading">2026', self.html)
        self.assertIn('class="year-heading">2025', self.html)

    def test_year_heading_order(self):
        pos_2026 = self.html.index('class="year-heading">2026')
        pos_2025 = self.html.index('class="year-heading">2025')
        self.assertLess(pos_2026, pos_2025)

    def test_estimated_reading_time(self):
        self.assertIn("Est. ~", self.html)
        self.assertIn("to read", self.html)

    def test_estimated_reading_time_on_unread_only(self):
        read_section_start = self.html.index('id="section-read"')
        read_section_end = self.html.index('id="section-unread"')
        read_section = self.html[read_section_start:read_section_end]
        self.assertNotIn("Est. ~", read_section)

    def test_avg_pages_per_day_stat(self):
        self.assertIn("Avg Pages/Day", self.html)

    def test_avg_days_per_book_stat(self):
        self.assertIn("Avg Days/Book", self.html)

    def test_finished_dates_in_read_section(self):
        self.assertIn("Finished 2025-01-11", self.html)
        self.assertIn("Finished 2026-03-11", self.html)

    def test_started_date_in_reading_section(self):
        self.assertIn("Started 2025-05-01", self.html)

    def test_valid_html_structure(self):
        self.assertIn("<!DOCTYPE html>", self.html)
        self.assertIn("</html>", self.html)
        self.assertIn("<title>Bookshelf</title>", self.html)

    def test_book_titles_present(self):
        self.assertIn("Read 2025", self.html)
        self.assertIn("Read 2026", self.html)
        self.assertIn("Now Reading", self.html)
        self.assertIn("Want to Read", self.html)
        self.assertIn("Gave Up", self.html)

    def test_sections_in_correct_order(self):
        reading_pos = self.html.index('id="section-reading"')
        read_pos = self.html.index('id="section-read"')
        unread_pos = self.html.index('id="section-unread"')
        dnf_pos = self.html.index('id="section-dnf"')
        self.assertLess(reading_pos, read_pos)
        self.assertLess(read_pos, unread_pos)
        self.assertLess(unread_pos, dnf_pos)


class TestGenerateHTMLEdgeCases(unittest.TestCase):
    def test_read_books_without_dates_grouped_as_unknown(self):
        books = [
            make_book(title="No Date", readingStatus="read", pages="100",
                      startReading="", endReading=""),
        ]
        stats = compute_stats(books)
        html = generate_html(books, stats)
        self.assertIn('class="year-heading">Unknown', html)

    def test_no_estimated_time_when_no_pages(self):
        books = [
            make_book(title="No Pages", readingStatus="unread", pages=""),
        ]
        stats = compute_stats(books)
        html = generate_html(books, stats)
        self.assertNotIn("Est. ~", html)

    def test_empty_section_omitted(self):
        books = [make_book(readingStatus="read")]
        stats = compute_stats(books)
        html = generate_html(books, stats)
        self.assertNotIn('id="section-reading"', html)
        self.assertNotIn('id="section-unread"', html)
        self.assertNotIn('id="section-dnf"', html)


if __name__ == "__main__":
    unittest.main()
