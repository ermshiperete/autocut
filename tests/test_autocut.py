#!/usr/bin/python3
import datetime
import os
from parameterized import parameterized
import tempfile
import time
import unittest
from unittest import mock
from autocut import convert_milliseconds_to_readable, extract_date_from_filename, get_start_in_audio


mock_time = datetime.time()


def mocked_get_now():
    return mock_time


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

    @parameterized.expand([
        [0, 0],
        [5, 180000],
        [-5, 0],
        [2, 0],
        [3, 60000],
    ])
    @mock.patch('autocut.get_now', side_effect=mocked_get_now)
    def test_get_start_in_audio(self, start_min, exepcted, mock_obj):
        # setup
        global mock_time
        temp_file = tempfile.TemporaryFile()
        ctime = time.localtime(os.path.getctime(temp_file.name))
        mock_time = datetime.datetime(ctime.tm_year, ctime.tm_mon,
                                      ctime.tm_mday, ctime.tm_hour,
                                      ctime.tm_min + start_min, ctime.tm_sec)
        info = {'start': f'{mock_time.hour}:{mock_time.minute}'}

        # execute
        start = get_start_in_audio(temp_file.name, info)

        # verify
        self.assertEqual(start, exepcted)


if __name__ == '__main__':
    unittest.main()
