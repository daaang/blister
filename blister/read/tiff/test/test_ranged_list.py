# Copyright (c) 2015 The Regents of the University of Michigan.
# All Rights Reserved. Licensed according to the terms of the Revised
# BSD License. See LICENSE.txt for details.
from unittest import TestCase

from blister.read.tiff.reader import RangedList

class TestRangedList (TestCase):
    def setUp (self):
        self.ranged_list = RangedList()

        self.ranged_list[0:10]      = "the first ten bytes"
        self.ranged_list[90:100]    = "ninety through ninety-nine"
        self.ranged_list[44]        = "forty-four"

    def test_length (self):
        self.assertEqual(len(self.ranged_list), 100,
                         "length should be 100")

    def test_bad_insert_left (self):
        with self.assertRaisesRegex(KeyError,
                                    r"Can't reassign values"):
            self.ranged_list[85:95]     = "uh oh"

    def test_bad_insert_right (self):
        with self.assertRaisesRegex(KeyError,
                                    r"Can't reassign values"):
            self.ranged_list[95:105]    = "uh oh"

    def test_bad_insert_inside (self):
        with self.assertRaisesRegex(KeyError,
                                    r"Can't reassign values"):
            self.ranged_list[92:98]     = "uh oh"

    def test_bad_insert_outside (self):
        with self.assertRaisesRegex(KeyError,
                                    r"Can't reassign values"):
            self.ranged_list[85:105]    = "uh oh"

    def test_bad_insert_zero_slice (self):
        with self.assertRaisesRegex(KeyError,
                                    r"Can't insert empty slice"):
            self.ranged_list[20:20]     = "uh oh"

    def test_bad_insert_stepped (self):
        with self.assertRaisesRegex(KeyError,
                                    r"Invalid step [0-9]+ \(if set" \
                                    r" at all, it must be 1\)"):
            self.ranged_list[30:50:2]   = "uh oh"

    def test_bad_insert_nonslice (self):
        with self.assertRaisesRegex(KeyError,
                                    r"Need int or slice, not"):
            self.ranged_list["hey"]     = "uh oh"

    def test_bad_insert_negative (self):
        with self.assertRaisesRegex(KeyError,
                                    r"Negative indeces are not" \
                                    r" allowed \(you gave me"):
            self.ranged_list[-5:5]      = "uh oh"

    def test_accessors_ints (self):
        # Test each int accessor.
        for i in range(10):
            self.assertEqual(self.ranged_list[i], "the first ten bytes",
                             "wrong values from the first insertion")

        for i in range(90, 100):
            self.assertEqual(self.ranged_list[i],
                             "ninety through ninety-nine",
                             "wrong values from the second insertion")

    def test_accessors_slice (self):
        # Test some slices.
        self.assertEqual(self.ranged_list[5:8],
                         [(slice(5, 8), "the first ten bytes")])

        self.assertEqual(self.ranged_list[5:20],
                         [(slice(5, 10), "the first ten bytes")])

        self.assertEqual(self.ranged_list[:95],
                         [(slice(0, 10), "the first ten bytes"),
                         (slice(44, 45), "forty-four"),
                         (slice(90, 95), "ninety through ninety-nine")])

    def test_iteration (self):
        items   = [
            (slice(0, 10),      "the first ten bytes"),
            (slice(44, 45),     "forty-four"),
            (slice(90, 100),    "ninety through ninety-nine"),
        ]

        # We'll be able to infer the keys and values from the items.
        # Since iteration is by keys by default, we'll need two
        # different arrays of keys.
        keys    = [[ ], [ ]]
        values  = [ ]

        # Autofill.
        for i, j in items:
            for k in range(2):
                # Once again, we have two arrays of keys, to test both
                # generators.
                keys[k].append(i)

            # We'll also fill the values.
            values.append(j)

        for x in self.ranged_list:
            # Check the __iter__ generator first.
            self.assertEqual(x, keys[0].pop(0))

        for x in self.ranged_list.keys():
            # Check the explicit keys next.
            self.assertEqual(x, keys[1].pop(0))

        for x in self.ranged_list.values():
            self.assertEqual(x, values.pop(0))

        for x in self.ranged_list.items():
            self.assertEqual(x, items.pop(0))

    def test_containment_ints (self):
        # Test some basic containment operations.
        self.assertTrue(   0 in self.ranged_list)
        self.assertTrue(   5 in self.ranged_list)
        self.assertFalse( 10 in self.ranged_list)
        self.assertFalse( 50 in self.ranged_list)
        self.assertTrue(  90 in self.ranged_list)
        self.assertTrue(  95 in self.ranged_list)
        self.assertFalse(100 in self.ranged_list)

    def test_containment_slices (self):
        self.assertTrue(slice(0,    10)     in self.ranged_list)
        self.assertTrue(slice(0,    15)     in self.ranged_list)
        self.assertFalse(slice(10,  20)     in self.ranged_list)
        self.assertTrue(slice(9,    28)     in self.ranged_list)
        self.assertTrue(slice(3,     7)     in self.ranged_list)
        self.assertTrue(slice(80,   91)     in self.ranged_list)
        self.assertFalse(slice(80,  90)     in self.ranged_list)
