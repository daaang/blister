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

class ContextNamespaceWithOnlyURIWithOneValue (ContextNamespaceWithOnlyURI):

    def setUp (self):
        super().setUp()
        self.ns[self.key] = self.value

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

class TestsGivenOnlyURIAndOneValue:

    key = None
    value = None
    other_keys = "yee", "hello", "Nope"

    def test_instance_has_length_of_one (self):
        assert_that(self.ns, has_length(1))

    def test_instance_is_invalid (self):
        assert_that(self.ns.is_valid(), is_(equal_to(False)))

    def test_instance_contains_key (self):
        assert_that(self.ns, has_key(self.key))

    def test_instance_yields_value_if_asked (self):
        assert_that(self.ns[self.key], is_(equal_to(self.value)))

    def test_instance_does_not_have_other_keys (self):
        get_by_key = lambda k: self.ns[k]
        for invalid_key in self.other_keys:
            assert_that(self.ns, does_not(has_key(invalid_key)))
            assert_that(calling(get_by_key).with_args(invalid_key),
                        raises(KeyError))

    def test_when_key_is_removed_length_is_zero (self):
        del self.ns[self.key]
        assert_that(self.ns, has_length(0))

    def test_when_key_is_removed_it_is_no_longer_there (self):
        del self.ns[self.key]
        assert_that(self.ns, does_not(has_key(self.key)))

    def test_when_second_key_is_added_length_is_two (self):
        self.ns["second_key"] = "second_value"
        assert_that(self.ns, has_length(2))

class GivenOnlyURIAndKeyEqualsValue (
        ContextNamespaceWithOnlyURIWithOneValue,
        TestsGivenOnlyURIAndOneValue):

    key = "key"
    value = "value"

class GivenOnlyURIAndMattEqualsGreat (
        ContextNamespaceWithOnlyURIWithOneValue,
        TestsGivenOnlyURIAndOneValue):

    key = "matt"
    value = "great"

class GivenOnlyURIAndThirdThingEqualsYes (
        ContextNamespaceWithOnlyURIWithOneValue,
        TestsGivenOnlyURIAndOneValue):

    key = "third thing"
    value = "yes"

class GivenNamespaceWithURIAndPrefixOnly (unittest.TestCase):

    def test_namespace_with_prefix_uses_custom_prefix (self):
        class URIAndPrefixNamespace (XMPNamespace):
            uri = "any old uri"
            prefix = "abc"

        ns = URIAndPrefixNamespace()
        assert_that(ns.prefix, is_(equal_to("abc")))

class GivenNamespaceWithOptionalValues (unittest.TestCase):

    def setUp (self):
        class OptionalValuesNamespace (XMPNamespace):
            uri = "uri"
            types = {
                "counter": int,
                "name": str,
            }

        self.ns = OptionalValuesNamespace()

    def test_empty_instance_is_valid (self):
        assert_that(self.ns.is_valid(), is_(equal_to(True)))

    def test_adding_expected_values_dont_invalidate (self):
        self.ns["name"] = "matt"
        assert_that(self.ns.is_valid(), is_(equal_to(True)))

    def test_adding_unexpected_values_still_invalidates (self):
        self.ns["what"] = 0
        assert_that(self.ns.is_valid(), is_(equal_to(False)))
