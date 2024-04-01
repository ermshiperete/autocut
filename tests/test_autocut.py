#!/usr/bin/python3
import datetime
import unittest

from autocut import convert_milliseconds_to_readable, extract_date_from_filename


class TestAutocut(unittest.TestCase):

    def test_convert_milliseconds(self):
        self.assertEqual(convert_milliseconds_to_readable(      0), '00:00:00.0')
        self.assertEqual(convert_milliseconds_to_readable(   1000), '00:00:01.0')
        self.assertEqual(convert_milliseconds_to_readable(   1300), '00:00:01.3')
        self.assertEqual(convert_milliseconds_to_readable(  60000), '00:01:00.0')
        self.assertEqual(convert_milliseconds_to_readable(3600000), '01:00:00.0')

    def test_extract_date_from_filename(self):
        self.assertEqual(extract_date_from_filename(
            '2024-03-31_foo.mp3'), datetime.date.fromisoformat('2024-03-31'))
        self.assertEqual(extract_date_from_filename(
            '31.03.2024_foo.mp3'), datetime.date.fromisoformat('2024-03-31'))
        self.assertEqual(extract_date_from_filename(
            '31.03.2024 foo.mp3'), datetime.date.fromisoformat('2024-03-31'))
        self.assertEqual(extract_date_from_filename(
            '03.2024_foo.mp3'), datetime.date.today())
        self.assertEqual(extract_date_from_filename(
            'foo.mp3'), datetime.date.today())
        self.assertEqual(extract_date_from_filename(
            '20240331_foo.mp3'), datetime.date.today())


if __name__ == '__main__':
    unittest.main()
