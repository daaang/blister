# Copyright (c) 2015 The Regents of the University of Michigan.
# All Rights Reserved. Licensed according to the terms of the Revised
# BSD License. See LICENSE.txt for details.
from io                     import  BytesIO, BufferedReader
from unittest               import  TestCase

from blister.read.jpeg2000  import  Jpeg2000
from blister.internal       import  *

class TestJpeg2000 (TestCase):
    tinyjp2 = hex_to_bytes("""\
                00 00 00 0c 6a 50 20 20                             \
                            0d 0a 87 0a                             \
                00 00 00 14 66 74 79 70                             \
                            6a 70 32 20 00 00 00 00                 \
                            6a 70 32 20                             \
                00 00 00 47 6a 70 32 68                             \
                            00 00 00 16 69 68 64 72                 \
                                        00 00 0e 19 00 00 0a 2a     \
                                        00 01 07 07 01 00           \
                            00 00 00 0f 63 6f 6c 72                 \
                                        01 00 00    00 00 00 11     \
                            00 00 00 1a 72 65 73 20                 \
                                        00 00 00 12 72 65 73 63     \
                                                    9c 40 00 fe     \
                                                    9c 40 00 fe     \
                                                          02 02     \
                00 00 00 61 75 75 69 64                             \
                            be 7a cf cb 97 a9 42 e8                 \
                            9c 71 99 94 91 e3 af ac                 \
                            3c 3f 78 70 61 63 6b 65 74 20 62 65     \
                            67 69 6e 3d 27 ef bb bf 27 20 69 64     \
                            3d 27 57 35 4d 30 4d 70 43 65 68 69     \
                            48 7a 72 65 53 7a 4e 54 63 7a 6b 63     \
                            39 64 27 3f 3e 0a 3c 3f 78 70 61 63     \
                            6b 65 74 20 65 6e 64 3d 27 77 27 3f     \
                            3e                                      \
                00 00 00 00 6a 70 32 63                             \
                                  ff 4f                             \
                                  ff 51 00 29 00 00                 \
                                        00 00 0a 2a 00 00 0e 19     \
                                        00 00 00 00 00 00 00 00     \
                                        00 00 0a 2a 00 00 0e 19     \
                                        00 00 00 00 00 00 00 00     \
                                        00 01       07 01 01        \
                                  ff 52 00 0c 06 01 00 08 00        \
                                        05 04 04 3e 00              \
                                  ff 5c 00 23 22                    \
                                        77 1e 76 ea 76 ea 76 bc     \
                                        6f 00 6f 00 6e e2 67 4c     \
                                        67 4c 67 64 50 03 50 03     \
                                        50 45 57 d2 57 d2 57 61     \
                                  ff 64 00 0f 00 01                 \
                                        4b 61 6b 61 64 75 2d 76     \
                                        37 2e 32                    \
                                  ff d9""")

    def setUp (self):
        self.jp2_obj = Jpeg2000(BufferedReader(BytesIO(self.tinyjp2)))

    def test_siz_values (self):
        assertions  = (
            ("F1",      0xe19),
            ("F2",      0xa2a),
            ("E1",      0),
            ("E2",      0),
            ("T1",      0xe19),
            ("T2",      0xa2a),
            ("OmegaT1", 0),
            ("OmegaT2", 0),
        )

        self.assertEqual(len(self.jp2_obj["jp2c"]), 1)

        for name, value in assertions:
            self.assertEqual(self.jp2_obj["jp2c"][0]["SIZ"][name],
                              value)
