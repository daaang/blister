# Copyright (c) 2017 The Regents of the University of Michigan.
# All Rights Reserved. Licensed according to the terms of the Revised
# BSD License. See LICENSE.txt for details.
from hamcrest import *
import unittest
from .hamcrest import evaluates_to

from blister.xmp import XMP

class XMPTest (unittest.TestCase):

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

    def test_default_xmp_namespaces_exist (self):
        no_error = self.xmp.stRef
