# Copyright (c) 2017 The Regents of the University of Michigan.
# All Rights Reserved. Licensed according to the terms of the Revised
# BSD License. See LICENSE.txt for details.
from hamcrest import *
import unittest
from .hamcrest import evaluates_to

from blister.xmp import XMP

class GivenEmptyXMP (unittest.TestCase):

    def setUp (self):
        self.xmp = XMP()

    def test_degenerate (self):
        assert_that(self.xmp, evaluates_to(False))
        assert_that(self.xmp, has_length(0))
        assert_that(list(self.xmp), is_(equal_to([])))

    def test_not_all_attrs_exist (self):
        assert_that(calling(getattr).with_args(self.xmp,
                                               "fake_namespace"),
                    raises(AttributeError))
        assert_that(calling(getattr).with_args(self.xmp, "also_fake"),
                    raises(AttributeError))

    def test_default_xmp_namespaces_are_empty (self):
        assert_that(self.xmp.stRef, has_length(0))
        assert_that(self.xmp.dc, has_length(0))
        assert_that(self.xmp.xmp, has_length(0))
        assert_that(self.xmp.xmpRights, has_length(0))
        assert_that(self.xmp.xmpMM, has_length(0))
        assert_that(self.xmp.xmpidq, has_length(0))
        assert_that(self.xmp.exifEX, has_length(0))
        assert_that(self.xmp.exif, has_length(0))
        assert_that(self.xmp.tiff, has_length(0))
