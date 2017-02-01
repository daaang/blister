# Copyright (c) 2017 The Regents of the University of Michigan.
# All Rights Reserved. Licensed according to the terms of the Revised
# BSD License. See LICENSE.txt for details.
from hamcrest import *
import unittest
from .hamcrest import evaluates_to

from blister.xmp import XMP, XMPNamespace

class GivenEmptyXMP (unittest.TestCase):

    namespaces = (
        "stRef",
        "dc",
        "xmp",
        "xmpRights",
        "xmpMM",
        "xmpidq",
        "exifEX",
        "exif",
        "tiff",
    )

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
        for namespace in self.namespaces:
            assert_that(getattr(self.xmp, namespace), has_length(0))

    def test_namespaces_are_also_accessible_via_getitem (self):
        assert_that(calling(lambda x: x["fake"]).with_args(self.xmp),
                    raises(KeyError))
        assert_that(calling(lambda x: x["bbbbbb"]).with_args(self.xmp),
                    raises(KeyError))

        for namespace in self.namespaces:
            assert_that(self.xmp[namespace], has_length(0))

class XMPNamespaceTest (unittest.TestCase):

    def test_degenerate (self):
        ns = XMPNamespace()
