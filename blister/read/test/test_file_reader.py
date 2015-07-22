# Copyright (c) 2015 The Regents of the University of Michigan.
# All Rights Reserved. Licensed according to the terms of the Revised
# BSD License. See LICENSE.txt for details.
from random     import randrange
from unittest   import TestCase

from blister.exceptions         import UnexpectedEOF
from blister.read.file_reader   import FileReader

class TestFileReader (TestCase):
    def generate_random_bytes (self):
        bytelist        = [ ]
        self.length     = randrange(0xf00) + 0x100

        for i in range(self.length):
            bytelist.append(randrange(0x100))

        self.bytelist   = bytes(bytelist)
        self.reader     = FileReader(self.bytelist)

    def setUp (self):
        self.generate_random_bytes()

    def test_samestrings (self):
        for i in range(10):
            self.generate_random_bytes()
            self.assertEqual(self.reader.read(), self.bytelist)

    def test_eof (self):
        with self.assertRaises(UnexpectedEOF):
            self.reader.read(self.length + 1)
