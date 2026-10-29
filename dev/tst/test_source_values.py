"""Canonical calendar dates reject ambiguous spellings and non-text input."""

from datetime import date
import unittest

from yap.source_values import canonical_date


class SourceValueTests(unittest.TestCase):
    def test_canonical_dates_include_leap_days_and_calendar_limits(self):
        for text, expected in (
            ('0001-01-01', date(1, 1, 1)),
            ('2000-02-29', date(2000, 2, 29)),
            ('2026-10-29', date(2026, 10, 29)),
            ('9999-12-31', date(9999, 12, 31)),
        ):
            with self.subTest(text=text):
                self.assertEqual(canonical_date(text, 'example: deadline'), expected)

    def test_invalid_values_have_a_source_specific_validation_error(self):
        for value in (
            None, True, 20261029, 1.0, [], {}, date(2026, 10, 29), '',
            '20261029', '2026-W44-4', '2026-10-29T00:00:00',
            '2026-10-29 ', ' 2026-10-29', '2026-1-1',
            '1900-02-29', '2026-02-29', '0000-01-01',
        ):
            with self.subTest(value=value), self.assertRaisesRegex(
                    ValueError, 'example: deadline.*YYYY-MM-DD'):
                canonical_date(value, 'example: deadline')


if __name__ == '__main__':
    unittest.main()
