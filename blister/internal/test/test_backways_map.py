# Copyright (c) 2015 The Regents of the University of Michigan.
# All Rights Reserved. Licensed according to the terms of the Revised
# BSD License. See LICENSE.txt for details.
from unittest import TestCase

from blister.internal.backways_map import make_backways_map

class SomeEnum:
    ThingOne    = 1
    ThingTwo    = 2
    ThingThree  = 3
    ThingFive   = 5

class CollisionEnum:
    ThingOne    = 1
    ThingTwo    = 1
    ThingThree  = 3
    ThingFive   = 5

class TestBackwaysMap (TestCase):
    def test_naming (self):
        d = make_backways_map(SomeEnum)

        self.assertEqual(d[1], "ThingOne")
        self.assertEqual(d[2], "ThingTwo")
        self.assertEqual(d[3], "ThingThree")
        self.assertEqual(d[5], "ThingFive")

    def test_collisions (self):
        with self.assertRaises(AssertionError):
            d = make_backways_map(CollisionEnum)
