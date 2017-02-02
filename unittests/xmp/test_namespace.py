# Copyright (c) 2017 The Regents of the University of Michigan.
# All Rights Reserved. Licensed according to the terms of the Revised
# BSD License. See LICENSE.txt for details.
from hamcrest import *
import unittest
from ..hamcrest import evaluates_to

from blister.xmp import XMPNamespace

class GivenNamespaceWithNoSettings (unittest.TestCase):

    def test_no_uri_raises_error (self):
        class DefaultNamespace (XMPNamespace):
            pass

        assert_that(calling(DefaultNamespace),
                    raises(XMPNamespace.NoURI))

class GivenNamespaceWithOnlyURI (unittest.TestCase):

    def setUp (self):
        class URIOnlyNamespace (XMPNamespace):
            uri = "some uri"

        self.ns = URIOnlyNamespace()

    def test_instance_evaluates_to_false (self):
        assert_that(self.ns, evaluates_to(False))

    def test_instance_is_valid (self):
        assert_that(self.ns.is_valid(), is_(equal_to(True)))

    def test_can_autogen_xml_prefix (self):
        assert_that(self.ns.prefix, is_(equal_to("uri-only")))
