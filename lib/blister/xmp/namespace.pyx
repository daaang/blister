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
    types = { }
    required = ( )

    class NoURI (RuntimeError):
        pass

    def __init__ (self):
        if self.uri is None:
            raise XMPNamespace.NoURI

        self.__internal = { }

    def is_valid (self):
        return self.__all_keys_are_valid() \
                and self.__all_required_keys_are_present()

    @property
    def prefix (self):
        words = camel_convert(self.__class__.__name__).split("-")
        return "-".join(s for s in words if s != "namespace")

    def __len__ (self):
        return len(self.__internal)

    def __getitem__ (self, key):
        return self.__internal[key]

    def __setitem__ (self, key, value):
        self.__internal[key] = value

    def __iter__ (self):
        return iter(self.__internal)

    def __delitem__ (self, key):
        del self.__internal[key]

    def __repr__ (self):
        return "<{} {}>".format(self.__class__.__name__,
                                repr(self.__internal))

    def __all_keys_are_valid (self):
        return all(self.__is_valid_key(k) for k in self)

    def __is_valid_key (self, key):
        if key not in self.types:
            return False

        if type(self[key]) == self.types[key]:
            return True

        return self.__can_convert_to_correct_type(key)

    def __can_convert_to_correct_type (self, key):
        try:
            v = self.types[key](self[key])
            return True

        except ValueError:
            return False

    def __all_required_keys_are_present (self):
        return all(k in self for k in self.required)
