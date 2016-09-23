# Copyright (c) 2016 The Regents of the University of Michigan.
# All Rights Reserved. Licensed according to the terms of the Revised
# BSD License. See LICENSE.txt for details.
from collections import namedtuple
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

URI_RDF = URI("http://www.w3.org/1999/02/22-rdf-syntax-ns#")
URI_X   = URI("adobe:ns:meta/")
URI_XML = URI("http://www.w3.org/XML/1998/namespace")

UriTag = namedtuple("UriTag", ("uri", "name"))

class XmpBaseValue:
    """Abstract XMP Value"""

    def __init__ (self):
        """Raise NotImplementedError.

        I don't want these to ever be created directly.
        """
        self.__not_implemented()

    @property
    def py_value (self):
        """Raise NotImplementedError.

        This should be overwritten to return a pythonic value that
        behaves however a user would expect without needing to know
        about XMP's more advanced features.

        For example, if this is an XmpInteger, this property should
        return an int object.
        """
        self.__not_implemented()

    def __not_implemented (self):
        """Raise NotImplementedError."""
        raise NotImplementedError("{} isn't meant to ever be " \
                "implemented directly".format(self.__class__.__name__))

    def raise_invalid_init (self, expected, actual):
        """Raise an error that the init value is invalid.

        Both arguments should be str objects.
        """

        raise TypeError("Init value must be {}, not {}".format(
                expected, actual))

class XmpURI (XmpBaseValue):
    """XMP URI value"""

    def __init__ (self, uri):
        """Set the internal value."""

        if isinstance(uri, URI):
            # We expect a URI.
            self.value = uri

        elif isinstance(uri, str):
            # We also allow a str object, which we'll convert to URI.
            self.value = URI(uri)

        else:
            # But we don't accept anything else.
            self.raise_invalid_init("URI", uri.__class__.__name__)

    @property
    def py_value (self):
        """Return a pythonic value."""
        return self.value

    def __repr__ (self):
        """Return an unambiguous representation."""
        if self.value:
            return "<{} {}>".format(self.__class__.__name__, self.value)

        else:
            return "<{}>".format(self.__class__.__name__)

class XmpText (XmpBaseValue):
    """Simple XMP Value"""

    # This is the basic type I expect for the internal value. Also, the
    # py_value property should return something of this type.
    py_type = str

    def __init__ (self, value):
        """Set the internal value."""

        # Check that the init value is something we can work with.
        if not self.is_valid_init_value(value):
            # If it's not valid, raise TypeError.
            self.raise_invalid_init(self.py_type.__name__,
                    value.__class__.__name__)

        # Cool! Set our internal value.
        self.value = self.format_valid_init_value(value)

    @property
    def py_value (self):
        """Return a pythonic value."""
        return self.value

    def __str__ (self):
        """Return a string representation as would appear in XML."""
        return str(self.value)

    def __repr__ (self):
        """Return an unambiguous representation."""
        if str(self):
            return "<{} {}>".format(self.__class__.__name__, str(self))

        else:
            return "<{}>".format(self.__class__.__name__)

    def is_valid_init_value (self, value):
        """Return true if the value is of a valid init format."""
        return isinstance(value, self.py_type)

    def format_valid_init_value (self, value):
        """Return the value we should store."""
        return value

class XmpInteger (XmpText):
    """XMP Integer"""

    py_type = int

    def __str__ (self):
        return "{:d}".format(self.value)

class XmpBaseCollection (XmpBaseValue):
    """XMP Collection"""

    @property
    def py_value (self):
        return self

class XmpBaseArray (XmpBaseCollection):
    """XMP Array"""

    # This must be a named UriTag duple.
    xmp_tag = None

    # This must be a subclass of XmpBaseValue.
    xmp_type = None

    def __init__ (self, iterable = ( )):
        assert isinstance(self.xmp_tag, UriTag) \
                and issubclass(self.xmp_type, XmpBaseValue)

        self.value = [ ]
        self.extend(iterable)

    def __getitem__ (self, index):
        return self.value[index].py_value

    def __len__ (self):
        return len(self.value)

    def __contains__ (self, value):
        for wrapper in self.value:
            if wrapper.loose_equal(value):
                return True

        return False

    def __iter__ (self):
        for wrapper in self.value:
            yield wrapper.py_value

    def __reversed__ (self):
        for wrapper in reversed(self.value):
            yield wrapper.py_value

    def index (self, value, i = 0, j = None):
        if j is None:
            j = len(self)

        for pos in range(i, j):
            if self.value[pos].loose_equal(value):
                return pos

        raise ValueError("{} is not in array".format(repr(value)))

    def count (self, value):
        count = 0

        for wrapper in self.value:
            if wrapper.loose_equal(value):
                count += 1

        return count

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
