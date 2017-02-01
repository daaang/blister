# Copyright (c) 2017 The Regents of the University of Michigan.
# All Rights Reserved. Licensed according to the terms of the Revised
# BSD License. See LICENSE.txt for details.
from hamcrest import *
import unittest

from blister.tmp import five

class NothingTest (unittest.TestCase):

    def test_working_testing_environment (self):
        assert_that(five, is_(equal_to(5)))
