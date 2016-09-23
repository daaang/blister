# Copyright (c) 2016 The Regents of the University of Michigan.
# All Rights Reserved. Licensed according to the terms of the Revised
# BSD License. See LICENSE.txt for details.
from collections.abc import MutableMapping

class URI (str):
    """URI string

    This is exactly like a str object (and will even test as equal to
    strings of identical value). It is a literal instance of str.

    The only difference is that these also return true as instances of
    URI, which is a distinct type of XMP value.

        >>> isinstance(URI("hello"), str)
        True
        >>> isinstance(URI("hello"), URI)
        True
        >>> isinstance("hello", URI)
        False
        >>> URI("hello") == "hello"
        True
        >>> "hello" == URI("hello")
        True

    Other than pass the "is this a URI" test, URI objects can't do
    anything that str objects can't do.
    """

    def __new__ (cls, *args, **kwargs):
        """Return a new str object."""
        return str.__new__(cls, *args, **kwargs)

    def __repr__ (self):
        """Return a str representing a URI (rather than a str)."""
        return "<{} {}>".format(self.__class__.__name__, self)

class VanillaXMP (MutableMapping):

    def __delitem__ (self, key):
        pass

    def __getitem__ (self, key):
        pass

    def __iter__ (self):
        pass

    def __len__ (self):
        pass

    def __setitem__ (self, key, value):
        pass
