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

class ContextNamespaceWithOnlyURI (unittest.TestCase):

    def setUp (self):
        class URIOnlyNamespace (XMPNamespace):
            uri = "some uri"

        self.ns = URIOnlyNamespace()

class GivenNamespaceWithOnlyURI (ContextNamespaceWithOnlyURI):

    def test_instance_evaluates_to_false (self):
        assert_that(self.ns, evaluates_to(False))

    def test_instance_has_no_length (self):
        assert_that(self.ns, has_length(0))

    def test_instance_is_valid (self):
        assert_that(self.ns.is_valid(), is_(equal_to(True)))

    def test_can_autogen_xml_prefix (self):
        assert_that(self.ns.prefix, is_(equal_to("uri-only")))

    def test_autogen_prefix_is_based_on_class_name (self):
        class JustAnotherNamespace (XMPNamespace):
            uri = "another one"

        ns = JustAnotherNamespace()
        assert_that(ns.prefix, is_(equal_to("just-another")))

class GivenNamespaceWithOnlyURIWithOneElt (ContextNamespaceWithOnlyURI):

    def setUp (self):
        super().setUp()
        self.ns["key"] = "value"

    def test_can_add_an_element (self):
        pass
