# Copyright (c) 2015 The Regents of the University of Michigan.
# All Rights Reserved. Licensed according to the terms of the Revised
# BSD License. See LICENSE.txt for details.
from unittest import TestCase

from blister.internal.deflatten import deflatten

class TestDeflatten (TestCase):
    def setUp (self):
        self.twelve     = list(range(12))

    def test_default (self):
        self.assertEqual(list(deflatten(self.twelve)), [
                (0,     1),
                (2,     3),
                (4,     5),
                (6,     7),
                (8,     9),
                (10,    11)])

    def test_two (self):
        self.assertEqual(list(deflatten(2, self.twelve)), [
                (0,     1),
                (2,     3),
                (4,     5),
                (6,     7),
                (8,     9),
                (10,    11)])

    def test_three (self):
        self.assertEqual(list(deflatten(3, self.twelve)), [
                (0, 1,  2),
                (3, 4,  5),
                (6, 7,  8),
                (9, 10, 11)])

    def test_four (self):
        self.assertEqual(list(deflatten(4, self.twelve)), [
                (0, 1,  2,  3),
                (4, 5,  6,  7),
                (8, 9,  10, 11)])

    def test_kwargs (self):
        self.assertEqual(list(deflatten(self.twelve, size = 4)), [
                (0, 1,  2,  3),
                (4, 5,  6,  7),
                (8, 9,  10, 11)])

    def test_five (self):
        self.assertEqual(list(deflatten(5, self.twelve)), [
                (0, 1,  2,  3,  4),
                (5, 6,  7,  8,  9)])

    def test_padding (self):
        self.assertEqual(list(deflatten(5, self.twelve, "sup")), [
                (0, 1,  2,  3,  4),
                (5, 6,  7,  8,  9),
                (10, 11, "sup", "sup", "sup")])
