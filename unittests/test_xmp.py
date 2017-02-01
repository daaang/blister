# Copyright (c) 2017 The Regents of the University of Michigan.
# All Rights Reserved. Licensed according to the terms of the Revised
# BSD License. See LICENSE.txt for details.
from hamcrest import *
import unittest
from .hamcrest import evaluates_to

from blister.xmp import XMP

class XMPTest (unittest.TestCase):

    def test_degenerate (self):
        xmp = XMP()
        assert_that(xmp, evaluates_to(False))
        assert_that(xmp, has_length(0))
        assert_that(list(xmp), is_(equal_to([])))

    def test_not_all_attrs_exist (self):
        xmp = XMP()
        assert_that(calling(getattr).with_args(xmp, "fake_namespace"),
                    raises(AttributeError))

    def test_default_xmp_namespaces_exist (self):
        xmp = XMP()
        no_error = xmp.stRef
