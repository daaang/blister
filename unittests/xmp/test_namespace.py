# Copyright (c) 2017 The Regents of the University of Michigan.
# All Rights Reserved. Licensed according to the terms of the Revised
# BSD License. See LICENSE.txt for details.
from hamcrest import *
import unittest
from ..hamcrest import evaluates_to

from blister.xmp import XMPNamespace

class GivenNamespaceWithNoSettings (unittest.TestCase):

    def setUp (self):
        class DefaultNamespace (XMPNamespace):
            pass

        self.ns = DefaultNamespace()

    def test_instance_evaluates_to_false (self):
        assert_that(self.ns, evaluates_to(False))

    def test_instance_is_valid (self):
        assert_that(self.ns.is_valid(), is_(equal_to(True)))
