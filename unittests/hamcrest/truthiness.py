# Copyright (c) 2017 The Regents of the University of Michigan.
# All Rights Reserved. Licensed according to the terms of the Revised
# BSD License. See LICENSE.txt for details.
from hamcrest.core.base_matcher import BaseMatcher

class evaluates_to (BaseMatcher):

    def __init__ (self, expected):
        self.expected = expected

    def _matches (self, item):
        return self.__get_bool_for(item) == self.expected

    def describe_to (self, description):
        description.append_text("an object with {} truthiness".format(
                repr(self.expected)))

    def describe_mismatch (self, item, description):
        actual = self.__get_bool_for(item)

        if actual is None:
            description.append_text("no truthiness ") \
                    .append_description_of(item)

        else:
            description.append_text("was {} ".format(actual)) \
                    .append_description_of(item)

    def __get_bool_for (self, item):
        try:
            result = bool(item)
            if result is True or result is False:
                return result

        except:
            pass
