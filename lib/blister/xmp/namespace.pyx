# Copyright (c) 2017 The Regents of the University of Michigan.
# All Rights Reserved. Licensed according to the terms of the Revised
# BSD License. See LICENSE.txt for details.
from collections.abc import MutableMapping
from re import compile as re_compile

cdef object re_full_word = re_compile(r"(.)([A-Z][a-z]+)")
cdef object re_other_word = re_compile(r"([a-z0-9])([A-Z])")

cdef str camel_convert (str s):
    return re_other_word.sub(r"\1-\2",
                             re_full_word.sub(r"\1-\2", s)).lower()

class XMPNamespace (MutableMapping):

    uri = None

    class NoURI (RuntimeError):
        pass

    def __init__ (self):
        if self.uri is None:
            raise XMPNamespace.NoURI

        self.__internal = True

    @property
    def prefix (self):
        words = camel_convert(self.__class__.__name__).split("-")
        return "-".join(s for s in words if s != "namespace")

    def is_valid (self):
        return self.__internal

    def __len__ (self):
        return 0 if self.__internal else 1

    def __getitem__ (self, key):
        if key == "key":
            return "value"

        else:
            raise KeyError

    def __setitem__ (self, key, value):
        self.__internal = False

    def __iter__ (self):
        return iter(("key",))

    def __delitem__ (self, key):
        self.__internal = True

    def __repr__ (self):
        return "<{}>".format(self.__class__.__name__)
