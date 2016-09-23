# Copyright (c) 2016 The Regents of the University of Michigan.
# All Rights Reserved. Licensed according to the terms of the Revised
# BSD License. See LICENSE.txt for details.
from collections.abc import MutableMapping
from unittest import TestCase

from blister.xmp import VanillaXMP, URI, XmpBaseValue, XmpURI, \
        XmpText, XmpInteger, XmpCollection

class TestVanillaXMP (TestCase):

    def test_is_mutable_mapping (self):
        xmp = VanillaXMP()
        self.assertTrue(isinstance(xmp, MutableMapping))

class TestXMPValues (TestCase):

    def test_abstract_value_wont_init (self):
        with self.assertRaises(NotImplementedError):
            a = XmpBaseValue()

    def test_abstract_value_has_no_py_value (self):
        class FakeXmp (XmpBaseValue):
            def __init__ (self):
                pass
        a = FakeXmp()

        with self.assertRaises(NotImplementedError):
            value = a.py_value

    def test_uri_value (self):
        uri = XmpURI(URI("hello"))
        self.assertTrue(isinstance(uri, XmpBaseValue))
        self.assertEqual(uri.py_value, URI("hello"))
        self.assertEqual(repr(uri), "<XmpURI hello>")

    def test_empty_uri (self):
        uri = XmpURI(URI(""))
        self.assertEqual(repr(uri), "<XmpURI>")

    def test_uri_only_accepts_uri_objects (self):
        with self.assertRaises(TypeError):
            uri = XmpURI("hello")

        with self.assertRaises(TypeError):
            uri = XmpURI(44)

    def test_text_value (self):
        text = XmpText("hello")
        self.assertTrue(isinstance(text, XmpBaseValue))
        self.assertEqual(text.py_value, "hello")
        self.assertEqual(repr(text), "<XmpText hello>")

    def test_empty_text (self):
        uri = XmpText("")
        self.assertEqual(repr(uri), "<XmpText>")

    def test_text_only_accepts_str (self):
        with self.assertRaisesRegex(TypeError, "must be str.*not int"):
            nope = XmpText(44)

    def test_int_value (self):
        i = XmpInteger(44)

        self.assertTrue(isinstance(i, XmpText))
        self.assertEqual(i.py_value, 44)
        self.assertEqual(repr(i), "<XmpInteger 44>")
        self.assertEqual(str(i), "44")

    def test_integer_only_accepts_int (self):
        with self.assertRaisesRegex(TypeError, "must be int.*not str"):
            nope = XmpInteger("oh no oh no")

    def test_abstract_xmp_collection_cant_init (self):
        with self.assertRaises(NotImplementedError):
            nope = XmpCollection()

    def test_abstract_xmp_collection_py_value (self):
        class FakeCollection (XmpCollection):
            def __init__ (self):
                pass

        col = FakeCollection()
        self.assertIs(col.py_value, col)

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
