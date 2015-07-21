# Copyright (c) 2015 The Regents of the University of Michigan.
# All Rights Reserved. Licensed according to the terms of the Revised
# BSD License. See LICENSE.txt for details.
from unittest import TestCase

from blister.internal.byte_handlers import int_to_bytes, bytes_to_int, \
                                           hex_to_bytes

class TestBytes (TestCase):
    def setUp (self):
        self.four_forty_four    = 444
        self.big_fff            = b"\1\274"
        self.little_fff         = b"\274\1"
        self.big_hex            = "01bc"
        self.little_hex         = "bc01"

    def test_int_to_bytes (self):
        self.assertEqual(int_to_bytes(self.four_forty_four, 2, "big"),
                         self.big_fff)
        self.assertEqual(int_to_bytes(self.four_forty_four, 2, "little"),
                         self.little_fff)

    def test_bytes_to_int (self):
        self.assertEqual(bytes_to_int(self.big_fff, "big"),
                         self.four_forty_four)
        self.assertEqual(bytes_to_int(self.little_fff, "little"),
                         self.four_forty_four)

    def test_hex_to_bytes (self):
        self.assertEqual(hex_to_bytes(self.big_hex),
                         self.big_fff)
        self.assertEqual(hex_to_bytes(self.little_hex),
                         self.little_fff)
