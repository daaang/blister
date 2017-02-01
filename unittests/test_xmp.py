# Copyright (c) 2017 The Regents of the University of Michigan.
# All Rights Reserved. Licensed according to the terms of the Revised
# BSD License. See LICENSE.txt for details.
from hamcrest import *
import unittest
from .hamcrest import evaluates_to

from blister.xmp import XMP

class XMPTest (unittest.TestCase):

    def test_degenerate (self):
        xmp = XMP()
        assert_that(xmp, evaluates_to(False))
