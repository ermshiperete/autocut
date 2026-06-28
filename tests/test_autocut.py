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

    @parameterized.expand([
        [      0, '00:00:00.0'],
        [   1000, '00:00:01.0'],
        [   1300, '00:00:01.3'],
        [  60000, '00:01:00.0'],
        [3600000, '01:00:00.0'],
    ])
    def test_convert_milliseconds(self, ms, expected):
        self.assertEqual(convert_milliseconds_to_readable(ms), expected)

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
        [0, True, 0],        # 0 min
        [5, True, 180000],   # 3 min
        [-5, True, 0],       # 0 min
        [2, True, 0],        # 0 min
        [3, True, 60000],    # 1 min
        [63, True, 3660000], # 61 min
        [0, False, 0],        # 0 min
        [5, False, 300000],   # 5 min
        [-5, False, 0],       # 0 min
        [2, False, 120000],   # 2 min
        [3, False, 180000],   # 3 min
        [63, False, 3780000], # 63 min
    ])
    @mock.patch('autocut.get_creation_time',
                side_effect=mocked_get_creation_time)
    def test_get_start_in_audio(self, start_minute, detect_intro, exepcted, mock_obj):
        # setup
        start_time = datetime.datetime.now().replace(
            hour=10, minute=0, second=0)
        global mock_creation_time
        mock_creation_time = start_time - \
            datetime.timedelta(minutes=start_minute)
        info = {'start': f'{start_time.hour:02d}:{start_time.minute:02d}'}

        # execute
        start = get_start_in_audio('foo.mp3', info, mock_creation_time, detect_intro)

        # verify
        self.assertEqual(start, exepcted)


if __name__ == '__main__':
    unittest.main()
