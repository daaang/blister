# Copyright (c) 2017 The Regents of the University of Michigan.
# All Rights Reserved. Licensed according to the terms of the Revised
# BSD License. See LICENSE.txt for details.
from hamcrest.core.base_matcher import BaseMatcher

class Validity (BaseMatcher):

    def __init__ (self, method_name, *args):
        self.method_name = method_name
        self.args = args

    def _matches (self, item):
        return getattr(item, self.method_name)(*self.args) == True

    def describe_to (self, description):
        description.append_text("a valid object")

def a_valid_object():
    return Validity("is_valid")
