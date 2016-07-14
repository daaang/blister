# Copyright (c) 2016 The Regents of the University of Michigan.
# All Rights Reserved. Licensed according to the terms of the Revised
# BSD License. See LICENSE.txt for details.
import unittest
from fractions import Fraction

from blister.xmp import VanillaXMP

class TestXMP (unittest.TestCase):

    def test_can_write_and_read_metadata_from_obj (self):
        # Christopher decides to create an XMP stream by hand for an
        # image he has. He starts with the vanilla XMP stream class
        # because he doesn't need to deal with custom namespaces.
        xmp = VanillaXMP()

        # He adds some basic TIFF tags about image dimensions and
        # resolution.
        xmp["tiff", "ImageWidth"] = 1024
        xmp["tiff", "ImageLength"] = 768

        # A little nervous about whether this will work, he checks to
        # see that the class stored things as he wrote them.
        self.assertEqual(xmp["tiff", "ImageWidth"], 1024)
        self.assertEqual(xmp["tiff", "ImageLength"], 768)

        # He's pretty sure it's a bitonal image, so he sets it to 1 bit
        # per sample and 1 sample per pixel.
        xmp["tiff"] = {
                "BitsPerSample": 1,
                "SamplesPerPixel": 1}

        # Again, he checks to make sure it stuck. He understands that,
        # no matter how it's defined, tiff:BitsPerSample is a sequence
        # of integers.
        self.assertEqual(xmp["tiff", "BitsPerSample"], [1])
        self.assertEqual(xmp["tiff", "SamplesPerPixel"], 1)

        # Whoops! Turns out it's a color image with 8 bits per sample
        # and 3 samples per pixel, so Christopher has to modify those
        # value.
        xmp["tiff", "BitsPerSample"] = [8, 8, 8]
        xmp["tiff", "SamplesPerPixel"] = 3

        # Knowing that resolution is a fraction, Christopher checks that
        # it automatically converts to a fraction for him.
        xmp["tiff", "XResolution"] = 400
        xmp["tiff", "YResolution"] = 400

        self.assertEqual(xmp["tiff", "XResolution"], 400)
        self.assertEqual(xmp["tiff", "YResolution"], 400)
        self.assertTrue(isinstance(xmp["tiff", "XResolution"],
                                   Fraction))
        self.assertTrue(isinstance(xmp["tiff", "YResolution"],
                                   Fraction))

        # He looks at a representation of the entire stream.
        self.assertEqual(repr(xmp), "<VanillaXMP {" \
                + "tiff:BitsPerSample: [8, 8, 8], ",
                + "tiff:ImageLength: 768, ",
                + "tiff:ImageWidth: 1024, ",
                + "tiff:SamplesPerPixel: 3, ",
                + "tiff:XResolution: 400/1, ",
                + "tiff:YResolution: 400/1}>")

        # Satisfied, he exits.

if __name__ == "__main__":
    unittest.main()
