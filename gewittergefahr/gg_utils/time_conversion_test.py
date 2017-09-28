"""Unit tests for time_conversion.py."""

import unittest
from gewittergefahr.gg_utils import time_conversion

TIME_FORMAT_YEAR = '%Y'
TIME_FORMAT_NUMERIC_MONTH = '%m'
TIME_FORMAT_3LETTER_MONTH = '%b'
TIME_FORMAT_YEAR_MONTH = '%Y-%m'
TIME_FORMAT_DAY_OF_MONTH = '%d'
TIME_FORMAT_DATE = '%Y-%m-%d'
TIME_FORMAT_HOUR = '%Y-%m-%d-%H00'
TIME_FORMAT_MINUTE = '%Y-%m-%d-%H%M'
TIME_FORMAT_SECOND = '%Y-%m-%d-%H%M%S'

TIME_STRING_YEAR = '2017'
TIME_STRING_NUMERIC_MONTH = '09'
TIME_STRING_3LETTER_MONTH = 'Sep'
TIME_STRING_YEAR_MONTH = '2017-09'
TIME_STRING_DAY_OF_MONTH = '26'
TIME_STRING_DATE = '2017-09-26'
TIME_STRING_HOUR = '2017-09-26-0500'
TIME_STRING_MINUTE = '2017-09-26-0520'
TIME_STRING_SECOND = '2017-09-26-052033'

UNIX_TIME_YEAR_SEC = 1483228800
UNIX_TIME_MONTH_SEC = 1504224000
UNIX_TIME_DATE_SEC = 1506384000
UNIX_TIME_HOUR_SEC = 1506402000
UNIX_TIME_MINUTE_SEC = 1506403200
UNIX_TIME_SEC = 1506403233


class TimeConversionTests(unittest.TestCase):
    """Each method is a unit test for time_conversion.py."""

    def test_string_to_unix_sec_year(self):
        """Ensures correctness of string_to_unix_sec; string = year only."""

        this_time_unix_sec = time_conversion.string_to_unix_sec(
            TIME_STRING_YEAR, TIME_FORMAT_YEAR)
        self.assertTrue(this_time_unix_sec == UNIX_TIME_YEAR_SEC)

    def test_string_to_unix_sec_year_month(self):
        """Ensures correctness of string_to_unix_sec; string = year-month."""

        this_time_unix_sec = time_conversion.string_to_unix_sec(
            TIME_STRING_YEAR_MONTH, TIME_FORMAT_YEAR_MONTH)
        self.assertTrue(this_time_unix_sec == UNIX_TIME_MONTH_SEC)

    def test_string_to_unix_sec_date(self):
        """Ensures correctness of string_to_unix_sec; string = full date."""

        this_time_unix_sec = time_conversion.string_to_unix_sec(
            TIME_STRING_DATE, TIME_FORMAT_DATE)
        self.assertTrue(this_time_unix_sec == UNIX_TIME_DATE_SEC)

    def test_string_to_unix_sec_hour(self):
        """Ensures correctness of string_to_unix_sec; string = full hour."""

        this_time_unix_sec = time_conversion.string_to_unix_sec(
            TIME_STRING_HOUR, TIME_FORMAT_HOUR)
        self.assertTrue(this_time_unix_sec == UNIX_TIME_HOUR_SEC)

    def test_string_to_unix_sec_minute(self):
        """Ensures correctness of string_to_unix_sec; string = full minute."""

        this_time_unix_sec = time_conversion.string_to_unix_sec(
            TIME_STRING_MINUTE, TIME_FORMAT_MINUTE)
        self.assertTrue(this_time_unix_sec == UNIX_TIME_MINUTE_SEC)

    def test_string_to_unix_sec_second(self):
        """Ensures correctness of string_to_unix_sec; string = full second."""

        this_time_unix_sec = time_conversion.string_to_unix_sec(
            TIME_STRING_SECOND, TIME_FORMAT_SECOND)
        self.assertTrue(this_time_unix_sec == UNIX_TIME_SEC)

    def test_unix_sec_to_string_year(self):
        """Ensures correctness of unix_sec_to_string; string = year only."""

        this_time_string = time_conversion.unix_sec_to_string(
            UNIX_TIME_SEC, TIME_FORMAT_YEAR)
        self.assertTrue(this_time_string == TIME_STRING_YEAR)

    def test_unix_sec_to_string_numeric_month(self):
        """Ensures correctness of unix_sec_to_string; string = numeric month."""

        this_time_string = time_conversion.unix_sec_to_string(
            UNIX_TIME_SEC, TIME_FORMAT_NUMERIC_MONTH)
        self.assertTrue(this_time_string == TIME_STRING_NUMERIC_MONTH)

    def test_unix_sec_to_string_3letter_month(self):
        """Ensures correctness of unix_sec_to_string; string = 3-lttr month."""

        this_time_string = time_conversion.unix_sec_to_string(
            UNIX_TIME_SEC, TIME_FORMAT_3LETTER_MONTH)
        self.assertTrue(this_time_string == TIME_STRING_3LETTER_MONTH)

    def test_unix_sec_to_string_year_month(self):
        """Ensures correctness of unix_sec_to_string; string = year-month."""

        this_time_string = time_conversion.unix_sec_to_string(
            UNIX_TIME_SEC, TIME_FORMAT_YEAR_MONTH)
        self.assertTrue(this_time_string == TIME_STRING_YEAR_MONTH)

    def test_unix_sec_to_string_day_of_month(self):
        """Ensures correctness of unix_sec_to_string; string = day of month."""

        this_time_string = time_conversion.unix_sec_to_string(
            UNIX_TIME_SEC, TIME_FORMAT_DAY_OF_MONTH)
        self.assertTrue(this_time_string == TIME_STRING_DAY_OF_MONTH)

    def test_unix_sec_to_string_date(self):
        """Ensures correctness of unix_sec_to_string; string = full date."""

        this_time_string = time_conversion.unix_sec_to_string(
            UNIX_TIME_SEC, TIME_FORMAT_DATE)
        self.assertTrue(this_time_string == TIME_STRING_DATE)

    def test_unix_sec_to_string_hour(self):
        """Ensures correctness of unix_sec_to_string; string = full hour."""

        this_time_string = time_conversion.unix_sec_to_string(
            UNIX_TIME_SEC, TIME_FORMAT_HOUR)
        self.assertTrue(this_time_string == TIME_STRING_HOUR)

    def test_unix_sec_to_string_minute(self):
        """Ensures correctness of unix_sec_to_string; string = full minute."""

        this_time_string = time_conversion.unix_sec_to_string(
            UNIX_TIME_SEC, TIME_FORMAT_MINUTE)
        self.assertTrue(this_time_string == TIME_STRING_MINUTE)

    def test_unix_sec_to_string_second(self):
        """Ensures correctness of unix_sec_to_string; string = full second."""

        this_time_string = time_conversion.unix_sec_to_string(
            UNIX_TIME_SEC, TIME_FORMAT_SECOND)
        self.assertTrue(this_time_string == TIME_STRING_SECOND)


if __name__ == '__main__':
    unittest.main()
