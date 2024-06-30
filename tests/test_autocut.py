#!/usr/bin/python3
import datetime
import os
from parameterized import parameterized
import tempfile
import time
import unittest
from unittest import mock
from autocut import convert_milliseconds_to_readable, extract_date_from_filename, get_start_in_audio


mock_creation_time = datetime.time()


def mocked_get_creation_time(input_file):
    return mock_creation_time


class TestAutocut(unittest.TestCase):

    def test_convert_milliseconds(self):
        self.assertEqual(convert_milliseconds_to_readable(      0), '00:00:00.0')
        self.assertEqual(convert_milliseconds_to_readable(   1000), '00:00:01.0')
        self.assertEqual(convert_milliseconds_to_readable(   1300), '00:00:01.3')
        self.assertEqual(convert_milliseconds_to_readable(  60000), '00:01:00.0')
        self.assertEqual(convert_milliseconds_to_readable(3600000), '01:00:00.0')

    @parameterized.expand([
        ['2024-06-30 09-36-16.mkv', '2024-06-30T09:36:16'],
        ['2024-6-5 9-8-7.mkv', '2024-06-05T09:08:07'],
        ['2024-06-30 11Foo.mkv', '2024-06-30'],
        ['2024-03-31_foo.mp3', '2024-03-31'],
        ['31.03.2024_foo.mp3', '2024-03-31'],
        ['31.03.2024 foo.mp3', '2024-03-31'],
        ['03.2024_foo.mp3', datetime.date.today().isoformat()],
        ['foo.mp3', datetime.date.today().isoformat()],
        ['20240331_foo.mp3', datetime.date.today().isoformat()]
    ])
    def test_extract_date_from_filename(self, filename, date):
        self.assertEqual(extract_date_from_filename(filename),
                         datetime.datetime.fromisoformat(date))

    @parameterized.expand([
        [0, 0],
        [5, 180000],
        [-5, 0],
        [2, 0],
        [3, 60000],
        [63, 3660000],
    ])
    @mock.patch('autocut.get_creation_time',
                side_effect=mocked_get_creation_time)
    def test_get_start_in_audio(self, start_minute, exepcted, mock_obj):
        # setup
        start_time = datetime.datetime.now().replace(
            hour=10, minute=0, second=0)
        global mock_creation_time
        mock_creation_time = start_time - \
            datetime.timedelta(minutes=start_minute)
        info = {'start': f'{start_time.hour:02d}:{start_time.minute:02d}'}

        # execute
        start = get_start_in_audio('foo.mp3', info, mock_creation_time)

        # verify
        self.assertEqual(start, exepcted)


if __name__ == '__main__':
    unittest.main()
