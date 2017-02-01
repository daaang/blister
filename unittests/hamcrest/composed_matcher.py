# Copyright (c) 2017 The Regents of the University of Michigan.
# All Rights Reserved. Licensed according to the terms of the Revised
# BSD License. See LICENSE.txt for details.
from hamcrest.core.base_matcher import BaseMatcher

class ComposedMatcher (BaseMatcher):

    def _matches (self, item):
        self.failed_matcher = None
        self.mismatch_item = None
        self.extra_message = None

        for true_item, matcher, extra_message in \
                self.__assertion_triples(item):
            if not matcher.matches(true_item):
                self.failed_matcher = matcher
                self.mismatch_item = true_item
                self.extra_message = extra_message
                return False

        return True

    def describe_to (self, description):
        if self.extra_message is not None:
            description.append_text("{} ".format(self.extra_message))

        self.failed_matcher.describe_to(description)

    def describe_mismatch (self, item, description):
        self.failed_matcher.describe_mismatch(self.mismatch_item,
                                              description)

    def __assertion_triples (self, item):
        return (self.__get_triple(x, item)
                        for x in self.assertion(item))

    def __get_triple (self, possible_tuple, item):
        if isinstance(possible_tuple, tuple):
            return self.__get_triple_from_tuple(possible_tuple, item)

        else:
            return item, possible_tuple, None

    def __get_triple_from_tuple (self, definite_tuple, item):
        if len(definite_tuple) == 3:
            return definite_tuple

        else:
            assert len(definite_tuple) == 2
            return definite_tuple + (None,)
