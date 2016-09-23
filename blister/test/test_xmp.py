# Copyright (c) 2016 The Regents of the University of Michigan.
# All Rights Reserved. Licensed according to the terms of the Revised
# BSD License. See LICENSE.txt for details.
from collections.abc import MutableMapping
from unittest import TestCase

from blister.xmp import VanillaXMP, URI

class TestVanillaXMP (TestCase):

    def test_is_mutable_mapping (self):
        xmp = VanillaXMP()
        self.assertTrue(isinstance(xmp, MutableMapping))

class TestURI (TestCase):

    def setUp (self):
        self.eg_str = "meaningless example"
        self.eg_uri = URI("meaningless example")

    def test_is_str_instance (self):
        self.assertTrue(isinstance(self.eg_uri, str))

    def test_str_is_not_uri (self):
        self.assertFalse(isinstance(self.eg_str, URI))

    def test_equal_to_str (self):
        self.assertEqual(self.eg_str, self.eg_uri)
        self.assertEqual(self.eg_uri, self.eg_str)

    def test_hash_into_dict (self):
        d = { }
        d[URI("a")] = "hi"

        self.assertIn("a", d)
        self.assertIn(URI("a"), d)

        self.assertEqual(d["a"], "hi")

    def test_repr (self):
        self.assertEqual(repr(self.eg_uri),
                "<URI {}>".format(self.eg_str))
