# Copyright (c) 2016 The Regents of the University of Michigan.
# All Rights Reserved. Licensed according to the terms of the Revised
# BSD License. See LICENSE.txt for details.
from collections.abc import MutableMapping
from unittest import TestCase

from blister.xmp import VanillaXMP

class TestVanillaXMP (TestCase):

    def test_is_mutable_mapping (self):
        xmp = VanillaXMP()
        self.assertTrue(isinstance(xmp, MutableMapping))
