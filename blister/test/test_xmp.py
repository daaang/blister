# Copyright (c) 2016 The Regents of the University of Michigan.
# All Rights Reserved. Licensed according to the terms of the Revised
# BSD License. See LICENSE.txt for details.
from collections.abc import MutableMapping
import unittest

from blister.xmp import VanillaXMP, URI, XmpBaseValue, XmpURI, \
        XmpText, XmpInteger, XmpBaseCollection

class TestVanillaXMP (unittest.TestCase):

    def test_is_mutable_mapping (self):
        xmp = VanillaXMP()
        self.assertTrue(isinstance(xmp, MutableMapping))

class TestXmpBaseValue (unittest.TestCase):

    def setUp (self):
        class FakeXmp (XmpBaseValue):
            def __init__ (self):
                pass

        self.fake1 = FakeXmp()
        self.fake2 = FakeXmp()

    def assert_not_implemented (self):
        return self.assertRaisesRegex(NotImplementedError,
                "^(XmpBaseValue|FakeXmp) isn't meant to ever be " \
                        "implemented directly$")

    def assert_cant_compare (self, op, other):
        return self.assertRaisesRegex(TypeError,
                r"^unorderable types: FakeXmp\(\) {} {}\(\)$".format(
                        op, other))

    def test_wont_init (self):
        with self.assert_not_implemented():
            a = XmpBaseValue()

    def test_has_no_py_value (self):
        with self.assert_not_implemented():
            value = self.fake1.py_value

    def test_comparisons (self):
        with self.assert_not_implemented():
            result = self.fake1 == self.fake2

        with self.assert_not_implemented():
            result = self.fake1 != self.fake2

        with self.assert_not_implemented():
            result = self.fake1 < self.fake2

        with self.assert_not_implemented():
            result = self.fake1 > self.fake2

        with self.assert_not_implemented():
            result = self.fake1 <= self.fake2

        with self.assert_not_implemented():
            result = self.fake1 >= self.fake2

    def test_working_comparisons (self):
        class Comparible (XmpBaseValue):
            def __init__ (self, result):
                self.result = result

            def compare (self, rhs):
                return self.result

        equal = Comparible(0)
        less = Comparible(-1)
        more = Comparible(1)

        self.assertTrue(equal == less)
        self.assertFalse(less == equal)

        self.assertTrue(less < more)
        self.assertTrue(more > less)

        self.assertTrue(less <= more)
        self.assertTrue(more >= less)

    def test_comparing_with_wrong_type (self):
        self.assertFalse(self.fake1 == 0)
        self.assertTrue(self.fake1 != "hi")

        with self.assert_cant_compare("<", "int"):
            result = self.fake1 < 70

        with self.assert_cant_compare(">", "int"):
            result = self.fake1 > 70

        with self.assert_cant_compare("<=", "int"):
            result = self.fake1 <= 70

        with self.assert_cant_compare(">=", "int"):
            result = self.fake1 >= 70

    def test_truthiness (self):
        with self.assert_not_implemented():
            result = bool(self.fake1)

class SimpleXmpTester:
    """Provide some general value testing functions.

    The idea is to implement this alongside unittest.TestCase.
    """

    def setUp (self):
        """You'll need to overwrite this."""
        self.main = "You need to overwrite setUp."
        self.less = self.main

        self.main_py_value = self.main
        self.main_repr = self.main

    def test_is_xmp_value (self):
        self.assertTrue(isinstance(self.main, XmpBaseValue))

    def test_py_value (self):
        self.assertEqual(self.main.py_value, self.main_py_value)

    def test_repr (self):
        self.assertEqual(repr(self.main), self.main_repr)

    def test_comparisons (self):
        self.assertTrue(self.less < self.main)
        self.assertTrue(self.less <= self.main)
        self.assertTrue(self.less != self.main)
        self.assertFalse(self.less > self.main)
        self.assertFalse(self.less >= self.main)
        self.assertFalse(self.less == self.main)

    def test_create_from_xmp_value (self):
        new_value = self.main.__class__(self.main)
        self.assertEqual(new_value, self.main)

    def test_true_value (self):
        self.assertTrue(bool(self.main))

class TestXmpURI (SimpleXmpTester, unittest.TestCase):

    def setUp (self):
        self.main_py_value = URI("hello")
        self.main_repr = "<XmpURI hello>"

        self.main = XmpURI(self.main_py_value)
        self.less = XmpURI(URI("ay yo"))

    def test_empty_uri (self):
        uri = XmpURI(URI(""))
        self.assertEqual(repr(uri), "<XmpURI>")

    def test_uri_only_accepts_uri_objects (self):
        with self.assertRaises(TypeError):
            uri = XmpURI(44)

    def test_uri_does_convert_str_objects (self):
        uri = XmpURI("hello")
        self.assertTrue(isinstance(uri.py_value, URI))

class TestXmpText (SimpleXmpTester, unittest.TestCase):

    def setUp (self):
        self.main_py_value = "hello"
        self.main_repr = "<XmpText hello>"

        self.main = XmpText(self.main_py_value)
        self.less = XmpText("ay yo")

    def test_empty_text (self):
        uri = XmpText("")
        self.assertEqual(repr(uri), "<XmpText>")

    def test_text_only_accepts_str (self):
        with self.assertRaisesRegex(TypeError, "must be str.*not int"):
            nope = XmpText(44)

class TestXmpInteger (SimpleXmpTester, unittest.TestCase):

    def setUp (self):
        self.main_py_value = 44
        self.main_repr = "<XmpInteger 44>"

        self.main = XmpInteger(self.main_py_value)
        self.less = XmpInteger(12)

    def test_str (self):
        self.assertEqual(str(self.main),
                "{:d}".format(self.main_py_value))

    def test_integer_only_accepts_int (self):
        with self.assertRaisesRegex(TypeError, "must be int.*not str"):
            nope = XmpInteger("oh no oh no")

class TestXMPValues (unittest.TestCase):

    def test_abstract_xmp_collection_cant_init (self):
        with self.assertRaises(NotImplementedError):
            nope = XmpBaseCollection()

    def test_abstract_xmp_collection_py_value (self):
        class FakeCollection (XmpBaseCollection):
            def __init__ (self):
                pass

        col = FakeCollection()
        self.assertIs(col.py_value, col)

class TestURI (unittest.TestCase):

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
