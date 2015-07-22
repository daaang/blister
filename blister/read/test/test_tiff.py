# Copyright (c) 2015 The Regents of the University of Michigan.
# All Rights Reserved. Licensed according to the terms of the Revised
# BSD License. See LICENSE.txt for details.
from io             import  BytesIO, BufferedReader
from random         import  randrange
from unittest       import  TestCase

from blister.exceptions import  UnexpectedEOF, TiffUnknownByteOrder,   \
                                TiffWrongMagicNumber,                  \
                                TiffFirstIFDOffsetTooLow,              \
                                TiffEmptyIFD, TiffDuplicateTag,        \
                                TiffOffsetsWithoutBytecounts,          \
                                TiffOffsetsDontMatchBytecounts,        \
                                TiffFloatError
from blister.read.tiff  import *
from blister.read.tiff.tags import TiffTagNameDict, TiffTagValueDict
from blister.read.file_reader import FileReader
from blister.internal   import *

class TestTiff (TestCase):
    # This is a valid tiff with CCITT Group4 compression.
    tinytiff    = hex_to_bytes("""\
                    49 49  2a 00  08 00 00 00               \
                                                            \
                    0c 00                                   \
                    00 01  03 00  01 00 00 00  6c 00 00 00  \
                    01 01  03 00  01 00 00 00  24 00 00 00  \
                    02 01  03 00  01 00 00 00  01 00 00 00  \
                    03 01  03 00  01 00 00 00  04 00 00 00  \
                    06 01  03 00  01 00 00 00  00 00 00 00  \
                    0a 01  03 00  01 00 00 00  01 00 00 00  \
                    11 01  04 00  01 00 00 00  9e 00 00 00  \
                    15 01  03 00  01 00 00 00  01 00 00 00  \
                    17 01  04 00  01 00 00 00  50 00 00 00  \
                    1c 01  03 00  01 00 00 00  01 00 00 00  \
                    28 01  03 00  01 00 00 00  03 00 00 00  \
                    3b 01  02 00  06 00 00 00  ee 00 00 00  \
                                               00 00 00 00  \
                                                            \
                    f3 6c 90 cc c3 99 86 83                 \
                    61 a0 db ff ff ff ff ff                 \
                    91 6e 6d 92 19 21 91 0f                 \
                    ff ff ff ff ff fe 5d 97                 \
                    7f ff ff ff ff ff ff ff                 \
                    f1 e3 ff ff ff ff ff ff                 \
                    e5 91 ff ff ff ff ff ff                 \
                    ff ff 1f ff ff ff ff ff                 \
                    ff 24 3f ff ff ff ff ff                 \
                    c4 44 44 47 c0 04 00 40                 \
                                                            \
                    4d 61 74 74 21 00""")

    def setUp (self):
        self.tiff_obj = Tiff(BufferedReader(BytesIO(self.tinytiff)))
        for ifd in self.tiff_obj:
            ifd.add_required_tags(
                    IFDTag.BitsPerSample,
                    IFDTag.Compression,
                    IFDTag.Orientation,
                    IFDTag.SamplesPerPixel)

    def test_file_is_mode_rb (self):
        # Be sure we won't accept any files that aren't binary
        # read-only.
        for i in ("r", "w", "wb", "a", "ab"):
            with open("/dev/null", i) as dev_null:
                with self.assertRaisesRegex(TypeError,
                        r"Expected a file with mode 'rb'"):
                    tiff = Tiff(dev_null)

    def test_invalid_eof (self):
        for i in (0, 2, 4, 8, 32, -1):
            with self.assertRaises(UnexpectedEOF):
                tiff = Tiff(BufferedReader(BytesIO(self.tinytiff[:i])))

    def test_invalid_byte_orders (self):
        valid = set((b"II", b"MM"))

        for i in range(0x100):
            # We'll try a bunch of random bad bytestrings.
            randbytes = b"II"
            while randbytes in valid:
                randbytes = int_to_bytes(randrange(0x10000), 2, "big")

            with self.assertRaises(TiffUnknownByteOrder):
                tiff = Tiff(BufferedReader(BytesIO(randbytes)))

    def test_forty_two (self):
        orders  = {b"II": "little", b"MM": "big"}

        for head, order in orders.items():
            # Let's start with 0x2a00 just to be sure it's doing the
            # right thing with the endienness.
            j = 0x100 * 42
            for i in range(0x100):
                while j == 42:
                    j = randrange(0x10000)

                with self.assertRaises(TiffWrongMagicNumber):
                    tiff = Tiff(BufferedReader(BytesIO(
                                head + int_to_bytes(j, 2, order))))

                j = randrange(0x10000)

    def test_ifd_min (self):
        for i in range(8):
            with self.assertRaises(TiffFirstIFDOffsetTooLow):
                tiff = Tiff(BufferedReader(BytesIO(self.tinytiff[:4]
                            + int_to_bytes(i, 4, "little"))))

    def test_ifd_entry_count (self):
        with self.assertRaises(TiffEmptyIFD):
            tiff = Tiff(BufferedReader(BytesIO(self.tinytiff[:8]
                        + b"\0\0")))

    def test_ifd_no_duplicate_entries (self):
        with self.assertRaises(TiffDuplicateTag):
            tiff = Tiff(BufferedReader(BytesIO(self.tinytiff[:0x16]
                        + b"\0" + self.tinytiff[0x17:])))

    def test_valid_ifdlen (self):
        self.assertEqual(1, len(self.tiff_obj))
        self.assertEqual(0xb, len(self.tiff_obj[0]))

    def test_valid_single_numbers (self):
        for tag, value in (
                (IFDTag.ImageWidth,         108),
                (IFDTag.ImageLength,        36),
                (IFDTag.BitsPerSample,      1),
                (IFDTag.SamplesPerPixel,    1),
                (IFDTag.Compression,        IFDCompression.Group4Fax),
                (IFDTag.FillOrder,          IFDFillOrder.LeftToRight),
                (IFDTag.PlanarConfiguration,
                    IFDPlanarConfiguration.Chunky),
                (IFDTag.ResolutionUnit,
                    IFDResolutionUnit.Centimeter),
                (IFDTag.PhotometricInterpretation,
                    IFDPhotometricInterpretation.WhiteIsZero)):
            self.assertEqual(1, len(self.tiff_obj[0][tag]),
                             TiffTagNameDict[tag])
            self.assertEqual(value, self.tiff_obj[0][tag][0],
                             TiffTagNameDict[tag])

    def test_artist (self):
        self.assertEqual(b"Matt!", self.tiff_obj[0][315])

    def assertIteration (self):
        for i, j in self.tiff_obj[0].items():
            pass

    def test_del_default (self):
        del self.tiff_obj[0][IFDTag.Compression]

        self.assertTrue(IFDTag.Compression in self.tiff_obj[0])
        self.assertEqual(0xb, len(self.tiff_obj[0]))

        self.assertEqual(self.tiff_obj[0][IFDTag.Compression],
                         [IFDCompression.uncompressed])

        self.assertIteration()

    def test_del_nodefault (self):
        del self.tiff_obj[0][IFDTag.Artist]

        self.assertFalse(IFDTag.Artist in self.tiff_obj[0])
        self.assertEqual(0xa, len(self.tiff_obj[0]))

        self.assertIteration()

    def test_del_nonreq (self):
        del self.tiff_obj[0][IFDTag.ResolutionUnit]

        self.assertTrue(IFDTag.ResolutionUnit in self.tiff_obj[0])
        self.assertFalse(IFDTag.ResolutionUnit in
                list(self.tiff_obj[0].keys()))
        self.assertEqual(0xa, len(self.tiff_obj[0]))

        self.assertEqual(self.tiff_obj[0][IFDTag.ResolutionUnit],
                         [IFDResolutionUnit.Inch])

        self.assertIteration()

    def test_del_req_nodefault (self):
        del self.tiff_obj[0][IFDTag.ImageWidth]

        self.assertFalse(IFDTag.ImageWidth in self.tiff_obj[0])
        self.assertTrue(IFDTag.ImageWidth in
                list(self.tiff_obj[0].keys()))
        self.assertEqual(0xb, len(self.tiff_obj[0]))

        with self.assertRaisesRegex(KeyError, repr(IFDTag.ImageWidth)):
            a = self.tiff_obj[0][IFDTag.ImageWidth]

        with self.assertRaisesRegex(KeyError, repr(IFDTag.ImageWidth)):
            self.assertIteration()
