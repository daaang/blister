# Copyright (c) 2016 The Regents of the University of Michigan.
# All Rights Reserved. Licensed according to the terms of the Revised
# BSD License. See LICENSE.txt for details.
import unittest

from blister.xmp import VanillaXMP

class TestXMP (unittest.TestCase):

    def test_can_write_and_read_metadata_from_obj (self):
        # Christopher decides to create an XMP stream by hand for an
        # image he has. He starts with the vanilla XMP stream class
        # because he doesn't need to deal with custom namespaces.
        xmp = VanillaXMP()

        # He adds some basic TIFF tags about image dimensions and
        # resolution.

        # A little nervous about whether this will work, he checks to
        # see that the class stored things as he wrote them.

        # He's pretty sure it's a bitonal image, so he sets it to 1 bit
        # per sample and 1 sample per pixel.

        # Again, he checks to make sure it stuck.

        # Whoops! Turns out it's a color image with 8 bits per sample
        # and 3 samples per pixel, so Christopher has to modify those
        # value.

        # He looks at a representation of the entire stream.

        # Satisfied, he exits.

        self.fail("Finish writing the test!")

if __name__ == "__main__":
    unittest.main()
