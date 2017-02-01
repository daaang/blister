# Copyright (c) 2016 The Regents of the University of Michigan.
# All Rights Reserved. Licensed according to the terms of the Revised
# BSD License. See LICENSE.txt for details.
from collections import namedtuple
from collections.abc import MutableMapping

class TwoWayMapping (MutableMapping):

    def __init__ (self, mapping_or_iterable = (), **kwargs):
        """Init a new two-way mapping."""
        # First create new internal dictionaries.
        self.__init_dicts()

        # Then deepcopy any included mapping/iterable as well as any
        # keyword arguments.
        self.__iter_update(mapping_or_iterable, kwargs)

    def __getitem__ (self, key):
        """Return a value given its key.

        Raises KeyError if the key is not present.
        """

        return self.__by_key[key]

    def get_value (self, value):
        """Return a key given its value.

        Raises KeyError if the value is not present.
        """

        return self.__by_value[value]

    def __delitem__ (self, key):
        """Delete a key-value pair given the key.

        Raises KeyError if the key is not present.
        """

        # Rather than simply delete the key from the dict, we pop out
        # the value at the same time.
        value = self.__by_key.pop(key)

        # We need that value to also pop it out from the value dict.
        del self.__by_value[value]

    def del_value (self, value):
        """Delete a key-value pair given the value.

        Raises KeyError if the value is not present.
        """

        # Rather than simply delete the value from the dict, we pop out
        # the key at the same time.
        key = self.__by_value.pop(value)

        # We need that key to also pop it out from the key dict.
        del self.__by_key[key]

    def __setitem__ (self, key, value):
        """Insert a key-value pair by key.

        Raises ValueError if the value is already present in here.
        However, if the key is already present, it will be overridden
        just as in any dict.

        Unlike selection and deletion, I don't allow insertion by value.
        There is no set_value method.
        """

        self.set_dual_value(key, value, value)

    def set_dual_value (self, key, value, value_hash):
        self.__assert_new_value(value_hash)
        self.__assert_new_key(key)

        self.__by_key[key] = value
        self.__by_value[value_hash] = key

    def __len__ (self):
        """Return count of key-value pairs stored."""
        return len(self.__by_key)

    def __iter__ (self):
        """Iterate through keys."""
        return self.keys()

    def __contains__ (self, key):
        """Return true if we contain the key."""
        return key in self.__by_key

    def contains_value (self, value):
        """Return true if we contain the value."""
        return value in self.__by_value

    def keys (self):
        """Iterate through keys."""
        return iter(self.__by_key)

    def values (self):
        """Iterate through values."""
        return iter(self.__by_value)

    def items (self):
        """Iterate through key-value pairs."""
        return self.__by_key.items()

    def __init_dicts (self):
        # Our internals are two dicts: one keyed on keys, another on
        # values.
        self.__by_key = { }
        self.__by_value = { }

    def __iter_update (self, *args):
        for mapping_or_iterable in args:
            # Each argument must be either a mapping or an iterable of
            # duples.
            self.update(mapping_or_iterable)

    def __assert_new_value (self, value):
        if value in self.__by_value:
            # If we already have this value in the reverse dictionary,
            # we raise a ValueError.
            raise ValueError("value already in mapping: " + repr(value))

    def __assert_new_key (self, key):
        if key in self:
            # If we already have this key, that's actually fine. All we
            # have to do is delete it. We use our own containment test
            # and deletion because we want to fully remove the key and
            # value from both internal dicts.
            del self[key]

    def __insert_new_keypair (self, key, value):
        # This assumes I'm not worried about collisions or anything
        # weird. This method is unsafe and does no checking.
        self.__by_key[key] = value
        self.__by_value[value] = key

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

    def compare (self, rhs):
        """Raise NotImplementedError.

        This should be overwritten to return an integer: 0 if this
        instance is "equal" to the right-hand side, a negative number if
        this instance is "less," or a positive number if this instance
        is "greater."

        What "equal," "less," and "greater" mean will be up to you.
        """
        self.__not_implemented()

    def is_equal (self, rhs):
        """Return true if the compare method returns 0.

        It can usually be simpler to check equality than to run a full
        compare, so you should probably overwrite this, but you don't
        have to.
        """
        return self.compare(rhs) == 0

    def __eq__ (self, rhs):
        """Return true if this is equal to the right-hand side."""
        if self.__is_same_class(rhs):
            # We'll only actually test equality if the right hand side
            # is a valid type.
            return self.is_equal(rhs)

        else:
            # If it's not a valid type, it's not equal. No need to raise
            # TypeError.
            return False

    def __ne__ (self, rhs):
        """Return false if this is equal to the right-hand side."""
        if self.__is_same_class(rhs):
            # We'll only actually test equality if the right hand side
            # is a valid type.
            return not self.is_equal(rhs)

        else:
            # If it's not a valid type, it's not equal. No need to raise
            # TypeError.
            return True

    def __lt__ (self, rhs):
        """Return true if this is less than the right-hand side."""
        if self.__is_same_class(rhs):
            # We'll only compare the values if the right hand side is a
            # valid type.
            return self.compare(rhs) < 0

        else:
            # If it's not a valid type, we'll raise an exception.
            self.__raise_cant_compare(rhs, "<")

    def __gt__ (self, rhs):
        """Return true if this is greater than the right-hand side."""
        if self.__is_same_class(rhs):
            # We'll only compare the values if the right hand side is a
            # valid type.
            return self.compare(rhs) > 0

        else:
            # If it's not a valid type, we'll raise an exception.
            self.__raise_cant_compare(rhs, ">")

    def __le__ (self, rhs):
        """Return true if this is less than or equal to the right-hand
        side."""
        if self.__is_same_class(rhs):
            # We'll only compare the values if the right hand side is a
            # valid type.
            return self.compare(rhs) <= 0

        else:
            # If it's not a valid type, we'll raise an exception.
            self.__raise_cant_compare(rhs, "<=")

    def __ge__ (self, rhs):
        """Return true if this is greater than or equal to the
        right-hand side."""
        if self.__is_same_class(rhs):
            # We'll only compare the values if the right hand side is a
            # valid type.
            return self.compare(rhs) >= 0

        else:
            # If it's not a valid type, we'll raise an exception.
            self.__raise_cant_compare(rhs, ">=")

    def __bool__ (self):
        """Return truthiness."""
        self.__not_implemented()

    def raise_invalid_init (self, expected, actual):
        """Raise an error that the init value is invalid.

        Both arguments should be str objects.
        """

        raise TypeError("Init value must be {}, not {}".format(
                expected, actual))

    def __is_same_class (self, rhs):
        return self.__class__ is rhs.__class__

    def __raise_cant_compare (self, rhs, op):
        raise TypeError("unorderable types: {}() {} {}()".format(
                self.__class__.__name__, op, rhs.__class__.__name__))

    def __not_implemented (self):
        raise NotImplementedError("{} isn't meant to ever be " \
                "implemented directly".format(self.__class__.__name__))

class XmpBaseSimpleValue (XmpBaseValue):

    @property
    def py_value (self):
        """Return a pythonic value."""
        return self.value

    def compare (self, rhs):
        """Return a comparison integer."""
        if self.is_equal(rhs):
            return 0

        elif self.value < rhs.value:
            return -1

        else:
            return 1

    def is_equal (self, rhs):
        """Return true if both values are equal."""
        return self.value == rhs.value

    def __repr__ (self):
        """Return an unambiguous representation."""
        if str(self):
            return "<{} {}>".format(self.__class__.__name__, str(self))

        else:
            return "<{}>".format(self.__class__.__name__)

    def __bool__ (self):
        """Return the same truthiness as our value."""
        return bool(self.value)

class XmpURI (XmpBaseSimpleValue):
    """XMP URI value"""

    def __init__ (self, uri):
        """Set the internal value."""

        if isinstance(uri, str):
            # We expect a str object.
            self.__init_from_str(uri)

        else:
            # It's also possible that the value is an XMP value. Or
            # maybe it's just not a valid init value at all.
            self.__init_maybe_from_xmp_value(uri)

    def __init_from_str (self, uri):
        if isinstance(uri, URI):
            # We know we have a str object, and if that str is a URI, we
            # don't even need to init a new object. We can just set it.
            self.value = uri

        else:
            # Ok it's some other sort of str object, so we need to
            # create an actual URI object from it.
            self.value = URI(uri)

    def __init_maybe_from_xmp_value (self, uri):
        if isinstance(uri, XmpURI):
            # Cool! It's already an XMP URI. We can just take its value
            # as-is.
            self.value = uri.value

        else:
            # Oh no! It's some other thing that I can't deal with.
            self.raise_invalid_init("URI", uri.__class__.__name__)

    def __str__ (self):
        """Return the URI value itself."""
        return self.value

class XmpText (XmpBaseSimpleValue):
    """Simple XMP Value"""

    # This is the basic type I expect for the internal value. Also, the
    # py_value property should return something of this type.
    py_type = str

    def __init__ (self, value):
        """Set the internal value."""

        if isinstance(value, self.__class__):
            self.value = value.value

        else:
            self.__init_from_py_value(value)

    def __str__ (self):
        """Return a string representation as would appear in XML."""
        return str(self.value)

    def is_valid_init_value (self, value):
        """Return true if the value is of a valid init format."""
        return isinstance(value, self.py_type)

    def format_valid_init_value (self, value):
        """Return the value we should store."""
        return value

    def __init_from_py_value (self, value):
        # Check that the init value is something we can work with.
        if not self.is_valid_init_value(value):
            # If it's not valid, raise TypeError.
            self.raise_invalid_init(self.py_type.__name__,
                    value.__class__.__name__)

        # Cool! Set our internal value.
        self.value = self.format_valid_init_value(value)

class XmpInteger (XmpText):
    """XMP Integer"""

    py_type = int

    def __str__ (self):
        return "{:d}".format(self.value)

class XmpNamespace (MutableMapping):

    def __init__ (self, uri, mapping_or_iterable = (), **kwargs):
        self.__uri = uri
        self.__dict = { }

        self.update(mapping_or_iterable)
        self.update(kwargs)

    def __str__ (self):
        return self.__uri

    @property
    def uri (self):
        return self.__uri

    def __getitem__ (self, key):
        return self.__dict[key]
    def __setitem__ (self, key, value):
        assert issubclass(value, XmpBaseValue)
        self.__dict[key] = value
    def __delitem__ (self, key):
        del self.__dict[key]
    def __iter__ (self):
        return iter(self.__dict)
    def __len__ (self):
        return len(self.__dict)
    def __contains__ (self, key):
        return key in self.__dict

class NamespaceMapping (TwoWayMapping):

    def __setitem__ (self, key, value):
        assert isinstance(value, XmpNamespace)
        self.set_dual_value(key, value, URI(value))

    def get_value (self, value):
        return super(NamespaceMapping, self).get_value(URI(value))

    def del_value (self, value):
        super(NamespaceMapping, self).del_value(URI(value))

    def contains_value (self, value):
        return super(NamespaceMapping, self).contains_value(URI(value))

    def values (self):
        for key, value in self.items():
            yield value

RdfNamespace = XmpNamespace(
        URI("http://www.w3.org/1999/02/22-rdf-syntax-ns#"))

XNamespace = XmpNamespace(URI("adobe:ns:meta/"))

XmlNamespace = XmpNamespace(URI("http://www.w3.org/XML/1998/namespace"),
        lang=XmpText)

UriTag = namedtuple("UriTag", ("uri", "name"))

class XmpBaseCollection (XmpBaseValue):
    """XMP Collection"""

    @property
    def py_value (self):
        return self

class XmpStructure (XmpBaseCollection):

    prefixes = NamespaceMapping(
            rdf = RdfNamespace,
            x   = XNamespace,
            xml = XmlNamespace)

    def __init__ (self, mapping_or_iterable = ()):
        self.value = { }

    def __getitem__ (self, key):
        prefix, name = self.__split_key(key)

        # Get the namespace dict.
        ns_dict = self.__get_namespace_dict(prefix)

        # Get the value from the namespace dict.
        return self.__get_from_namespace_dict(ns_dict, prefix, name)

    def __setitem__ (self, key, value):
        prefix, name = self.__split_key(key)
        uri = self.__get_uri(prefix, name)

    def __split_key (self, key):
        if self.__is_valid_key(key):
            return key

        else:
            raise KeyError(key)

    def __is_valid_key (self, key):
        # A key is valid if it's a duple of str objects.
        return isinstance(key, tuple)       \
                and len(key) == 2           \
                and isinstance(key[0], str) \
                and isinstance(key[1], str)

    def __get_namespace_dict (self, prefix):
        if prefix in self.value:
            # If we have values under this particular namespace as-is,
            # then we can just return that dict of values.
            return self.value[prefix]

        else:
            # Otherwise, we need to check whether this prefix has a
            # corresponding URI first.
            return self.__get_namespace_dict_from_prefix(prefix)

    def __get_namespace_dict_from_prefix (self, prefix):
        # Get the corresponding URI. If there isn't one, we'll use a
        # value that is guaranteed not to be a valid URI (i.e. None).
        uri = self.prefixes.get(prefix, None)

        # If the URI is represented in our main dict, we return its
        # value. Otherwise, we return an empty dict.
        return self.value.get(uri, { })

    def __get_from_namespace_dict (self, ns_dict, prefix, name):
        if name in ns_dict:
            # Return the pythonic value if it's in there.
            return ns_dict[name].py_value

        else:
            # If we don't have it, we should raise the KeyError with the
            # full key (not just with the name itself).
            raise KeyError((prefix, name))

    def __get_uri (self, prefix, name):
        if self.prefixes.contains_value(prefix):
            # If the prefix is already a URI, we're all set.
            return prefix

        else:
            # If not, try to get a URI from our prefix dict.
            return self.__get_uri_from_prefix_dict(prefix, name)

    def __get_uri_from_prefix_dict (self, prefix, name):
        # Normally, I'd prefer testing over exception handling (to avoid
        # the overhead of generating a traceback), but, in this case,
        # the result on failure will be to raise an exception anyway, so
        # there's no reason to fear that traceback. It is, in fact,
        # cheaper to skip the containment test.
        try:
            # This could raise a KeyError.
            return self.prefixes[prefix]

        except KeyError:
            # If it does, it won't be quite right, as it'll be raised on
            # only the prefix. I want the user to receive a KeyError
            # based on the full key given.
            raise KeyError((prefix, name))

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
