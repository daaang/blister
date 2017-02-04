# Copyright (c) 2017 The Regents of the University of Michigan.
# All Rights Reserved. Licensed according to the terms of the Revised
# BSD License. See LICENSE.txt for details.
from hamcrest import *
import unittest
from ..hamcrest import evaluates_to
does_not = is_not

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

class GivenNamespaceWithOnlyURIWithKeyIsValue (ContextNamespaceWithOnlyURI):

    def setUp (self):
        super().setUp()
        self.ns["key"] = "value"

    def test_instance_has_length_of_one (self):
        assert_that(self.ns, has_length(1))

    def test_instance_is_invalid (self):
        assert_that(self.ns.is_valid(), is_(equal_to(False)))

    def test_instance_contains_key (self):
        assert_that(self.ns, has_key("key"))

    def test_instance_yields_value_if_asked (self):
        assert_that(self.ns["key"], is_(equal_to("value")))

    def test_instance_does_not_have_other_keys (self):
        get_by_key = lambda k: self.ns[k]
        for invalid_key in "yee", "hello", "NOPE":
            assert_that(self.ns, does_not(has_key(invalid_key)))
            assert_that(calling(get_by_key).with_args(invalid_key),
                        raises(KeyError))
