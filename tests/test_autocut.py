#!/usr/bin/python3
import unittest

from autocut import convert_milliseconds_to_readable


class TestAutocut(unittest.TestCase):

    def test_convert_milliseconds(self):
        self.assertEqual(convert_milliseconds_to_readable(      0), '00:00:00.0')
        self.assertEqual(convert_milliseconds_to_readable(   1000), '00:00:01.0')
        self.assertEqual(convert_milliseconds_to_readable(   1300), '00:00:01.3')
        self.assertEqual(convert_milliseconds_to_readable(  60000), '00:01:00.0')
        self.assertEqual(convert_milliseconds_to_readable(3600000), '01:00:00.0')


if __name__ == '__main__':
    unittest.main()
