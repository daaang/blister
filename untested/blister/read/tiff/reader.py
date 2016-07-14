# Copyright (c) 2015 The Regents of the University of Michigan.
# All Rights Reserved. Licensed according to the terms of the Revised
# BSD License. See LICENSE.txt for details.
from bisect         import  bisect_left, insort_left
from collections    import  namedtuple, Mapping, MutableMapping, \
                            Sequence, Iterable
from fractions      import  Fraction
from itertools      import  count
from sys            import  version_info

from ...exceptions  import  TiffUnknownByteOrder,                      \
                            TiffWrongMagicNumber,                      \
                            TiffFirstIFDOffsetTooLow,                  \
                            TiffEmptyIFD, TiffDuplicateTag,            \
                            TiffOffsetsWithoutBytecounts,              \
                            TiffOffsetsDontMatchBytecounts,            \
                            TiffFloatError
from ...internal    import  int_to_bytes, bytes_to_int
from ..file_reader  import  FileReader
from .tags          import  IFDTag, IFDCompression, IFDExtraSamples,   \
                            IFDFillOrder, IFDOrientation,              \
                            IFDPhotometricInterpretation,              \
                            IFDPlanarConfiguration, IFDResolutionUnit, \
                            IFDSubfileType, IFDThresholding,           \
                            TiffTagNameDict, TiffTagValueDict

if version_info[0] > 2:
    # Python 3 just has the one int type.
    int_types = int

else:
    # Python 2 has a couple int types to take into account.
    int_types = (int, long)

########################################################################
############################# TIFF Classes #############################
########################################################################

# This is kinda an enumeration of TIFF data types.
class TiffType:
    """IFD value types by name"""
    # Everything really should be one of these five types.
    BYTE        = 1
    ASCII       = 2
    SHORT       = 3
    LONG        = 4
    RATIONAL    = 5

    # But each of these is also possible.
    SBYTE       = 6
    UNDEFINED   = 7
    SSHORT      = 8
    SLONG       = 9
    SRATIONAL   = 10
    FLOAT       = 11
    DOUBLE      = 12


# TIFF data types will be stored in a dictionary of named tuples.
TiffTypeDict    = { }
TiffTypeTuple   = namedtuple("TiffTypeTuple", ("tifftype",
                                               "pytype",
                                               "bytecount"))

# Here's all the information specific to each type.
for pytype, bytecount, tifftype in (
        (int,       1,  TiffType.BYTE),
        (bytes,     1,  TiffType.ASCII),
        (int,       2,  TiffType.SHORT),
        (int,       4,  TiffType.LONG),
        (Fraction,  8,  TiffType.RATIONAL),
        (int,       1,  TiffType.SBYTE),
        (bytes,     1,  TiffType.UNDEFINED),
        (int,       2,  TiffType.SSHORT),
        (int,       4,  TiffType.SLONG),
        (Fraction,  8,  TiffType.SRATIONAL),
        (float,     4,  TiffType.FLOAT),
        (float,     8,  TiffType.DOUBLE)):
    # Put this info into the dictionary.
    TiffTypeDict[tifftype] = TiffTypeTuple(tifftype, pytype, bytecount)

# Just in case, I'll want to be able to handle floats in TIFFs. These
# are the bit masks I'll need to apply to such values, in order to
# extract the sign, exponent, and value.
IEEE_754_Parameters = {
    4:  (0x80000000,
         0x7f800000,
         0x007fffff),
    8:  (0x8000000000000000,
         0x7ff0000000000000,
         0x000fffffffffffff),
}

class Float:
    """Lossless float storage.

    This exists to store floats read in from TIFFs without losing any
    data whatsoever.
    """

    def __init__ (self, numerator, denominator, exponent):
        """Initialize float.

        Takes in a numerator, denominator, and exponent. Stores a
        Fraction and the exponent:

            >>> Float(1, 2, 3)
            <Float 2**(3) * 1/2>
            >>> float(Float(1, 2, 3))
            4.0
            >>> float(Float(1, 2, 100))
            6.338253001141147e+29
        """

        # We keep a fraction and an exponent.
        self.fraction   = Fraction(numerator, denominator)
        self.exponent   = exponent

    def __float__ (self):
        """Convert to usable float."""
        if self.exponent < 0:
            # Negative exponents invoke division.
            return float(self.fraction) / (float(2)**(-self.exponent))

        # Positive exponents are for multiplying.
        return float(self.fraction) * (float(2)**self.exponent)

    def __repr__ (self):
        """Represent an instance."""
        return "<{} 2**({:d}) * {:d}/{:d}>".format(
                self.__class__.__name__,
                self.exponent,
                self.fraction.numerator,
                self.fraction.denominator)

class RangedList (Mapping):
    """Ranged List

    This is something between a list and a dict, keyed on ranges.

        >>> a           = RangedList()
        >>> a[0:8]      = "first eight"
        >>> a[32]       = "single value"
        >>> a[64:128]   = "big group"
        >>> a
        <RangedList [0:8]:    'first eight',
                    [32:33]:  'single value',
                    [64:128]: 'big group'>

    It supports everything you would expect from a mutable mapping
    except that values cannot be destroyed or modified. Length is based
    not on actual value count but on highest value recorded.

        >>> len(a)
        128

    Testing for containment works as expected.

        >>> 5 in a
        True
        >>> 10 in a
        False
        >>> 128 in a
        False

    Pulling values also works as expected.

        >>> a[5]
        'first eight'
        >>> a[8]
        Traceback (most recent call last):
          File "<stdin>", line 1, in <module>
          File "./tiff.py", line 418, in __getitem__
            # I return the value only if the key is inside this range.
        KeyError: 'Not yet defined: 8'
        >>> a.get(8, "nothin")
        'nothin'

    You can also retrieve by slice, and you'll receive a list of
    2-tuples. The second value (labelled "value") in each tuple will be
    the value you set; the first value (labelled "key_range") will be
    some subslice of your input slice such that all contained keys
    correspond to the value.

        >>> a[4:5]
        [SliceTuple(key_range=slice(4, 5, None), value='first eight')]
        >>> a[4:70]
        [SliceTuple(key_range=slice(4, 8, None), value='first eight'),
        SliceTuple(key_range=slice(32, 33, None), value='single value'),
        SliceTuple(key_range=slice(64, 70, None), value='big group')]
        >>> a[8:9]
        []

    You can also check for the existence of slices. Watch out though:
    rather than check every value in the slice, it checks for the
    existence of ANY value in the slice.

        >>> slice(8, 10) in a
        False
        >>> slice(7, 10) in a
        True
    """

    SliceTuple = namedtuple("SliceTuple", ("key_range", "value"))

    def __init__ (self):
        """No arguments can be given during initialization."""
        self.sorted_list    = [(0, 0, None)]

    def __getitem__ (self, key):
        """Looks up a single key or a slice of keys."""
        # Have a look at the given key.
        if isinstance(key, int_types):
            # Integers are simple; all there is to do is grab the index.
            i                   = self.get_internal_index(key)
            low, high, value    = self.sorted_list[i]

            # I return the value only if the key is inside this range.
            if key < high:
                return value

            # Otherwise, I'll raise an exception (self.get() will handle
            # that if need be).
            raise KeyError("Not yet defined: {:d}".format(key))

        # Be sure the key is a slice.
        key = self.key_to_slice(key)

        # We want to return a list, since we were given a slice.
        result = [ ]

        if key.start >= key.stop:
            # If the slice has a range length of zero, we surely
            # have no values to return.
            return [ ]

        # We have a range length of at least one, so we may as well
        # check for the start index.
        start               = self.get_internal_index(key.start)
        low, high, value    = self.sorted_list[start]

        if high > key.start:
            # We already know that `low` is less than (or equal to)
            # `key.start`. Now we know that `high` is greater, so
            # `key.start` is actually contained in this range.
            if high >= key.stop:
                # This means the entire slice is contained in this
                # range. That means we're done.
                return [self.SliceTuple(key, value)]

            # Otherwise, we need to keep going.
            result.append(self.SliceTuple(slice(key.start, high),
                                          value))

        # We're done with this start index. Time to increment it and
        # to find the final index to look at.
        start  += 1
        stop    = self.get_internal_index(key.stop - 1, start)

        if start > stop:
            # If the last index comes before the new start index,
            # then we have nothing to do.
            return result

        for low, high, value in self.sorted_list[start:stop]:
            # Beginning with our new start index and stopping before
            # our stop index, we append 2-tuples to our result.
            result.append(self.SliceTuple(slice(low, high), value))

        # Finally, get the values at the final index.
        low, high, value = self.sorted_list[stop]
        result.append(self.SliceTuple(slice(low, min(high, key.stop)),
                                      value))

        # Our result list is complete.
        return result

    def __contains__ (self, key):
        """Checks for existence of a key or slice of keys."""
        key = self.key_to_slice(key)

        if key.start >= key.stop:
            # If there's nothing in this slice, then the answer is easy
            # to give.
            return False

        # Get the start index.
        start = self.get_internal_index(key.start)

        if key.start < self.sorted_list[start][1]:
            # Does the first internal slice actually contain this value?
            # If so, we're done.
            return True

        # If we're beginning outside an internal slice, check where we
        # end. If it's after a different one, then this will result
        # true. Otherwise, we know this particular key is not yet
        # assigned.
        return start < self.get_internal_index(key.stop - 1, start)

    def __setitem__ (self, key, value):
        """Assign some values."""
        key = self.key_to_slice(key)

        if key.start >= key.stop:
            # I won't bother inserting when the length of the slice is
            # zero.
            raise KeyError("Can't insert empty slice " + repr(key))

        start = self.get_internal_index(key.start)

        if key.start >= self.sorted_list[start][1]:
            # We're at least starting outside an internal slice. How are
            # we finishing?
            if start >= self.get_internal_index(key.stop - 1, start):
                # Excellent. We won't be overwriting anything. We also
                # already know exactly where to insert this so that it
                # remains sorted.
                self.sorted_list.insert(start + 1,
                                        (key.start, key.stop, value))

                return

        # Otherwise, there's already some overlap. Error out.
        raise KeyError("Can't reassign values " + repr(key))

    def __len__ (self):
        """Returns the length as if every value through the largest key
        were filled."""
        # For our purposes, the length is the slice stop value in the
        # very last section.
        return self.sorted_list[-1][1]

    def __iter__ (self):
        """Iterate over the keys."""
        # Mapping types are supposed to iterate over keys by default.
        return self.keys()

    def __repr__ (self):
        """Represent an instance."""
        slices = [ ]
        for s, v in self.items():
            slices.append("[{:d}:{:d}]: {}".format(s.start,
                                                   s.stop,
                                                   repr(v)))

        return "<{} {}>".format(self.__class__.__name__,
                                ", ".join(slices))

    def iterate_sorted_list (func):
        """Decorator for iteration.

        Functions this decorates should take three arguments and return
        whatever an iteration will be looking for.
        """

        def result (self):
            # We'll always be iterating over all three values in our
            # sorted list.
            for three_tuple in self.sorted_list[1:]:
                # Yield whatever our particular function returns.
                yield func(*three_tuple)

        return result

    @iterate_sorted_list
    def keys (start, stop, value):
        """Iterate over keys (slices)."""
        return slice(start, stop)

    @iterate_sorted_list
    def values (start, stop, value):
        """Iterate over values."""
        return value

    @iterate_sorted_list
    def items (start, stop, value):
        """Iterate over 2-tuples of keys and values."""
        # I'd use SliceTuples, but everyone using this should be
        # familiar with how items() works.
        return (slice(start, stop), value)

    def first_after_or_at (self, key):
        """Return the smallest key greater than or equal to the
        input."""
        if key >= len(self):
            # If this key comes after the end, then we have nothing to
            # return.
            return None

        # Look for the key.
        i = self.get_internal_index(key)

        if key < self.sorted_list[i][1]:
            # If the key is in the range, return it.
            return key

        # Otherwise, return the beginning of the next range.
        return self.sorted_list[i + 1][0]

    def key_to_slice (self, key):
        """Convert a key to an expected slice style."""
        if isinstance(key, slice):
            # It's already a slice! Make sure the step is one, if it's
            # set at all.
            if key.step is None or key.step == 1:
                # Cool, it's a slice I can work with.
                if key.start is None:
                    # By default, we start at zero.
                    return slice(0, key.stop)

                # Otherwise, just do as you're told!
                return key

            # The step is invalid.
            raise KeyError("Invalid step {:d} (if set at all,"
                           " it must be 1)".format(key.step))

        if isinstance(key, int_types):
            # It's an int! For my purposes, it's a slice with a length
            # of one.
            return slice(key, key + 1)

        # Uh oh! I don't recognize this junk!
        raise KeyError("Need int or slice, not {}".format(
                                repr(key)))

    def get_internal_index (self, x, lo = 0):
        """Get the largest internal index that could possibly point to a
        range containing x."""
        if x < 0:
            # If x is negative, well, I don't have a way to handle that.
            raise KeyError("Negative indeces are not allowed (you"
                           " gave me {:d})".format(x))

        # We want the range that starts as late as possible while also
        # starting at or before x. The value I give to bisect_left is
        # impossible (what with the range ending in zero), but that is
        # ideal, as I only use it to compare.
        #
        # Left to itself, this will give the ideal insertion point for
        # x; I want the value before that point. Dang this is more than
        # I thought, all in one line.
        return bisect_left(self.sorted_list, (x+1, 0, None), lo) - 1

class TiffIFD (MutableMapping):
    """TIFF IFD.

    This is pretty much a dictionary of TIFF entries. It's different in
    a few ways:

    1.  It's sorted. This only matters when iterating. When iterating,
        the keys are already in sorted order. This is a requirement for
        a valid TIFF IFD.

    2.  Any number of fields can be marked as "required." These fields
        will always come up during iteration (and in length
        calculation), even though attempts to access their values will
        result in KeyErrors.

    3.  It stores a number of default values. If you set anything to its
        default, then it's value won't actually be stored, and it will
        only be part of iteration if it's required.
    """

    # Here are default values.
    defaults            = {
        IFDTag.NewSubfileType:      0,
        IFDTag.Compression:         IFDCompression.uncompressed,
        IFDTag.FillOrder:           IFDFillOrder.LeftToRight,
        IFDTag.GrayResponseUnit:    2,
        IFDTag.NewSubfileType:      0,
        IFDTag.Orientation:         IFDOrientation.normal,
        IFDTag.PlanarConfiguration: IFDPlanarConfiguration.Chunky,
        IFDTag.ResolutionUnit:      IFDResolutionUnit.Inch,
        IFDTag.RowsPerStrip:        0xffffffff,
        IFDTag.SamplesPerPixel:     1,
        IFDTag.Thresholding:        IFDThresholding.Nothing,
    }

    # These tags are absolutely required in every IFD.
    always_required     = set((
        IFDTag.ImageWidth,
        IFDTag.ImageLength,
        #IFDTag.BitsPerSample,
        #IFDTag.Compression,
        IFDTag.PhotometricInterpretation,
        IFDTag.StripOffsets,
        #IFDTag.Orientation,
        #IFDTag.SamplesPerPixel,
        IFDTag.StripByteCounts,
    ))

    # This exists as a hierarchy of tag default dependencies.
    tag_dependencies    = {
        IFDTag.SamplesPerPixel: (
            IFDTag.BitsPerSample,
            IFDTag.MinSampleValue,
        ),

        IFDTag.BitsPerSample: (
            IFDTag.MaxSampleValue,
        ),
    }

    # This is a list of tags with more complicated default values than
    # can be expressed in the defaults dictionary, since their defaults
    # depend on other values.
    complex_defaults    = set()
    for tags in tag_dependencies.values():
        complex_defaults.update(tags)

    def __init__ (self, *args, **kwargs):
        """Initialize TIFF IFD.

        You can pass any number of arguments:

        -   Nonkeyworded dictionaries will be updated in as entries.

        -   Other nonkeyworded containers will be treated as lists of
            new required tags.

        -   Nonkeyworded noncontainers will be treated as new required
            tags.

        -   Keyworded arguments will be updated in as entries.
        """

        # I have an internal dictionary and a sorted list of tags.
        self.internal_dict  = { }
        self.ordered_tags   = [ ]

        # Let's initialize our particular list of required tags.
        self.required_tags  = set(self.always_required)

        for tag in self.required_tags:
            # Add every required tag to our ordered list. These are
            # always here, guaranteeing a failure on iteration for any
            # that remain unset (and that have no default).
            insort_left(self.ordered_tags, tag)

        for base_dict in args + (kwargs,):
            if isinstance(base_dict, Mapping):
                # We have a dictionary. Update with it.
                self.update(base_dict)

            else:
                # Otherwise, we're probably adding required tags.
                self.add_required_tags(base_dict)

    def __bool__ (self):
        """Check validity

        Returns true if the IFD has stored values for each required tag.
        Otherwise returns false. If this returns true, it is safe to
        iterate over values.
        """

        for tag in self:
            # Check whether each tag is actually here.
            if tag not in self:
                # If even one tag is not here, this is not a valid IFD.
                return False

        # Every tag was present. We're valid!
        return True

    def __getitem__ (self, key):
        """Read an entry"""
        if key not in self.internal_dict:
            # If this key isn't in the dictionary, see if it has a
            # default value.
            default = self.get_default(key)

            if default is not None:
                # It does! Return it.
                return default

        # Either it's in the dictionary (in which case I'm returning it)
        # or it's not and has no default (in which case this will raise
        # a KeyError).
        return self.internal_dict[key]

    def __setitem__ (self, key, value):
        """Set or update an entry"""
        if not isinstance(value, (bytes, str, list, tuple)):
            # We've been given a single value. We deal in lists of size
            # 1 (never just single values).
            value = [value]

        if value != self.get_default(key):
            # This isn't just the default, so yeah let's store it.
            if key not in self.internal_dict and \
                    key not in self.required_tags:
                # And hey, we haven't added this value before, so let's
                # also add it to our ordered tag list.
                insort_left(self.ordered_tags, key)

            # Add it.
            self.internal_dict[key] = value

        elif key in self.internal_dict:
            # We just tried to replace a nondefault value with a
            # default. Behind the scenes, that just means we remove it.
            if key not in self.required_tags:
                # It's not required either, so seriously, get rid of it.
                del self.ordered_tags[bisect_left(self.ordered_tags,
                                                  key)]

            # Get rid of the value itself regardless of whether we're
            # axing the key.
            del self.internal_dict[key]

        # If anything depends on this value, fix it, just in case.
        self.fix_dependent_tags_if_any(key)

    def __delitem__ (self, key):
        """Remove an entry."""
        if key in self.internal_dict or self.get_default(key) is None:
            # Delete it if it's there. Also attempt to delete it if it
            # doesn't have a default value. If it's not there and has no
            # default, then, naturally, this will raise a KeyError.
            del self.internal_dict[key]

            if key not in self.required_tags:
                # Now that it's gone from the internal dict, be sure
                # it's also gone from the tag list (unless the tag is
                # required, of course).
                del self.ordered_tags[bisect_left(self.ordered_tags,
                                                  key)]

        # If anything depends on this value, fix it, just in case.
        self.fix_dependent_tags_if_any(key)

    def __iter__ (self):
        """Iterate through entries in tag order"""
        # Our keys are our ordered tag list. TIFFs require that they be
        # in order, so there it is.
        return iter(self.ordered_tags)

    def __len__ (self):
        """Count entries.

        Note that there may be entries that are not counted; this will
        not count entries that are set to their defaults (unless they
        are required).
        """

        # Our length should match the count of tags we'll actually
        # iterate on.
        return len(self.ordered_tags)

    def __contains__ (self, key):
        """Check whether we have an entry with this tag"""
        return key in self.internal_dict or \
                self.get_default(key) is not None

    def __repr__ (self):
        """Represent an IFD"""
        pairs = [ ]
        for tag in self:
            if tag in self:
                value = repr(self[tag])
            else:
                value = "None"

            pairs.append("{:d}={}".format(tag, value))

        return "<{} {}>".format(self.__class__.__name__,
                                ", ".join(pairs))

    def __str__ (self):
        """Dump an IFD all pretty"""
        result = "{}:".format(self.__class__.__name__)

        for tag, value in self.items():
            result += "\n  {:4x} {:>28s}: ".format(tag,
                        TiffTagNameDict.get(tag, "(unknown)"))

            if isinstance(value, (str, bytes)):
                result += repr(value)
                continue

            if tag in TiffTagValueDict:
                transform   = lambda x: "{} ({})".format(repr(x),
                                        TiffTagValueDict[tag][x])

            else:
                transform   = lambda x: repr(x)

            result += transform(value[0])

            for another in value[1:]:
                result += "\n" + " " * 37 + transform(another)

        return result

    def add_required_tags (self, *args):
        """Add required tags.

        You can give any number of arguments. Arguments can be
        containers of required tags or required tags themselves.
        """

        for arg in args:
            # Check each argument to see if it's a container.
            if isinstance(arg, Iterable):
                # If it is, run recursively.
                for i in arg:
                    self.add_required_tags(i)

            else:
                # It's not a container, so we can just add it.
                if arg not in self.required_tags:
                    # We only need to add it if it's not already there.
                    if arg not in self.internal_dict:
                        # We only need to add it to our ordered tag list
                        # if it's not already there.
                        insort_left(self.ordered_tags, arg)

                    # Either way though, since it's not already here, it
                    # needs to be put here.
                    self.required_tags.add(arg)

    def add_unrequired_tag (self, *args):
        """Remove required tags.

        You can give any number of arguments. Arguments can be
        containers of required tags or required tags themselves.
        """

        for arg in args:
            if isinstance(arg, Iterable):
                # It's an iterable! Iterate through it!
                for i in arg:
                    self.add_unrequired_tag(i)

            else:
                # It's a real argument.
                if arg in self.required_tags:
                    # And we actually will have to remove it!
                    if arg not in self.internal_dict:
                        # It's not even in the internal dictionary, so
                        # yeah get it get it gone!
                        del self.ordered_tags[
                                bisect_left(self.ordered_tags, arg)]

                    # Don't forget to actually delete it!
                    self.required_tags.discard(arg)

    def fix_dependent_tags_if_any (self, key):
        """Handle complex defaults"""
        # NB This method works only because of an assumption about order
        # of assignment that you should be aware of, if you're messing
        # with any of this:
        #
        # Let's say a key field is going to change value from A to B
        # (and is currently set to A). My assumption is that, given A
        # and B are different, all the current default values for
        # dependent fields (valid for A) are *invalid* values for B.
        #
        # As of current writing, there is only one key field
        # (SamplesPerPixel), and its dependent fields must be lists of
        # values for each sample (i.e. with lengths matching the value).
        #
        # If you're adding dependent defaults, they may not fit in this
        # box. Be careful.
        if key in self.tag_dependencies:
            # We've just modified this key tag, so we need to check all
            # the tags that depend on it, in case they now match their
            # defaults.
            for tag in self.tag_dependencies[key]:
                # Whether it's set or not, this will ensure that values
                # are transferred appropriately.
                self[tag] = self[tag]

    def get_default (self, tag, be_safe = False):
        """Get the default value if any.

        This returns None if there is no default value. Otherwise, it
        returns the exact default value. This won't raise any errors.

        This is meant to be used internally; you'd probably rather just
        access items the usual way.
        """
        if tag in self.complex_defaults:
            if tag == IFDTag.BitsPerSample:
                # The default BPS is 1, and we need an array such that
                # there's a value for each sample.
                return [1] * self[IFDTag.SamplesPerPixel][0]

            if tag == IFDTag.MaxSampleValue:
                # We'll build a new list.
                result = [ ]

                for bitcount in self[IFDTag.BitsPerSample]:
                    # The default max is based on the bitcount for each
                    # sample.
                    result.append(2**bitcount - 1)

                return result

            if tag == IFDTag.MinSampleValue:
                # The default min is zero for each sample.
                return [0] * self[IFDTag.SamplesPerPixel][0]

        if tag in self.defaults:
            # This one isn't special. I must have something in the
            # array.
            value = self.defaults[tag]

            if isinstance(value, (bytes, str, tuple, list)):
                # If it's a string, just return it.
                return value

            if value is not None:
                # Otherwise, it's an array with length 1.
                return [value]

        # Otherotherwise, I got nothing.
        return None

class Tiff (Sequence):
    """Tiff Container

    Once initialized, this is little more than a non-mutable sequence of
    IFDs. It takes in an open "rb" file stream, reads what it can, and
    becomes that sequence (or raises a TiffError if it can't).
    """

    # The first two bytes of the tiff must be in here.
    expected_byte_orders    = {
        b"II":  "little",
        b"MM":  "big",
    }

    # The second two bytes of the tiff must be this integer.
    magic_check_number      = 42

    # These are the types that have a sign bit.
    signed_types            = set((
        TiffType.SBYTE,
        TiffType.SSHORT,
        TiffType.SLONG,
        TiffType.SRATIONAL,
    ))

    # These pairs all are lists of 
    strip_tags              = (
        (IFDTag.StripOffsets,   IFDTag.StripByteCounts),
        (IFDTag.FreeOffsets,    IFDTag.FreeByteCounts),
        (IFDTag.TileOffsets,    IFDTag.TileByteCounts),
    )

    class TiffError (Exception):
        """TiffError

        The purpose of this class is to display an error message along
        with an approximate relevant location inside the tiff.
        """

        def __init__ (self, position, message):
            """Initialize with a position and a message"""
            # Every tiff error comes with a position inside the tiff and
            # an error message.
            self.position   = position
            self.message    = message

        def __str__ (self):
            """Display the message and position"""
            # And here's how we display the error by default.
            return "{msg} (0x{pos:08x})".format(
                    pos = self.position,
                    msg = str(self.message))

    # These are just named tuples. If you don't know what that means,
    # then all you have to know is that these are tuples with more
    # features that you probably don't care about.
    OutOfOrderEntry     = namedtuple("OutOfOrderEntry",
                            ("ifd", "tag", "prev_max"))
    UnknownTypeEntry    = namedtuple("UnknownTypeEntry",
                            ("ifd", "tag", "code", "offset"))
    InvalidStringEntry  = namedtuple("InvalidStringEntry",
                            ("ifd", "tag", "suggestions"))

    def __init__ (self, file_object):
        """Initialize from a file object with mode 'rb'"""
        if not isinstance(file_object, FileReader):
            file_object = FileReader(file_object)

        # This is a list of named 3-tuples, defined by OutOfOrderEntry.
        self.out_of_order_ifds  = [ ]

        # This is a list of named 4-tuples, defined by UnknownTypeEntry.
        self.unknown_types      = [ ]

        # This is a list of named 3-tuples, defined by
        # InvalidStringEntry.
        self.invalid_strings    = [ ]

        # Store the file object, and initialize a ranged list.
        self.tiff       = file_object
        self.tiff_bytes = RangedList()

        # Read the header. This will set some internal parameters and
        # return the offset for the first IFD.
        ifd_offset      = self.read_header()

        # Retrieve a list of all IFDs. This won't actually examine any
        # of the entries yet, but it'll make sure the IFDs are properly
        # structured at least.
        simple_ifds     = self.read_ifds(ifd_offset)

        # Follow any and all offset links in the IFDs.
        self.ifds       = self.internalize_ifds(simple_ifds)

    def __getitem__ (self, key):
        """Get an IFD"""
        return self.ifds[key]

    def __len__ (self):
        """Get a count of IFDs"""
        return len(self.ifds)

    def read_header (self):
        """Read the tiff header.

        This reads the first eight bytes of the tiff. It discerns byte
        order, validates the magic number, and locates the offset of the
        first IFD. The byte order is set in self.byte_order; the first
        IFD offset is returned.
        """

        # We should start at the beginning.
        self.tiff.seek(0)

        try:
            # Try to get the byte order.
            self.byte_order = self.expected_byte_orders[self.read(2)]

        except KeyError as e:
            # If it didn't work, raise an error.
            self.tiff.error(TiffUnknownByteOrder, -2, str(e))

        # Read the magic number (it's 42).
        forty_two   = self.read_int(2)

        if forty_two != self.magic_check_number:
            # Uh oh! It's something other than 42 oh no oh no!
            self.tiff.error(TiffWrongMagicNumber, -2,
                            self.magic_check_number, forty_two)

        # Cool. Next is the IFD offset. How many bytes have we read so
        # far? (The answer is absolutely going to be 8.)
        ifd_offset                      = self.read_int(4)
        header_length                   = self.tiff.pos()

        if ifd_offset < header_length:
            # Be sure the offset doesn't point to anywhere in the tiff
            # header.
            self.tiff.error(TiffFirstIFDOffsetTooLow, -4,
                            header_length, ifd_offset)

        # Add the header bytes to the byte range.
        self.add_bytes(0, header_length, (None, None, None))

        # Return the first IFD offset.
        return ifd_offset

    def read_ifds (self, ifd_offset):
        """Read the IFDs from the tiff without interpretation"""
        # We'll be collecting IFDs into a list.
        ifds                    = [ ]

        while ifd_offset != 0:
            # Go to the IFD and read the entry count.
            self.tiff.seek(ifd_offset)
            entry_count = self.read_int(2)

            if entry_count < 1:
                # Be sure that we have at least one entry.
                self.tiff.error(TiffEmptyIFD, -2, len(ifds))

            # Add the bytes.
            self.add_bytes(ifd_offset,
                           12 * entry_count + 6,
                           (0, None, None))

            # Get all the entries.
            entries = { }
            largest_entry_seen_so_far = 0

            for i in range(entry_count):
                # No need to get fancy just yet; for now, we're just
                # grabbing what we can find within the IFD. We'll start
                # following offsets and interpreting things later.
                offset          = self.tiff.pos()
                tag             = self.read_int(2)
                valtype         = self.read_int(2)
                listlen         = self.read_int(4)
                value           = self.read(4)

                if tag in entries:
                    # No duplicate entries are allowed.
                    self.tiff.error(TiffDuplicateTag, 0, tag,
                                    TiffTagNameDict.get(tag, "unknown"),
                                    len(ifds))

                if tag < largest_entry_seen_so_far:
                    # Keep track of out-of-order entries. They make the
                    # TIFF invalid, but I don't want to be this strict
                    # unless I'm validating.
                    self.out_of_order_ifds.append(self.OutOfOrderEntry(
                        len(ifds), tag, largest_entry_seen_so_far))

                else:
                    # Otherwise, it's in order so far. Update our
                    # largest entry tracker.
                    largest_entry_seen_so_far = tag

                # Put these values into our entry dictionary
                entries[tag]    = (valtype, listlen, value, offset)

            # We're done collecting entries.
            ifds.append(entries)

            # Get the offset for the next IFD. If we're looking at the
            # last one, this will be zero, and this while loop will
            # terminate here.
            ifd_offset = self.read_int(4)

        # Return the list of IFDs.
        return ifds

    def internalize_ifds (self, simple_ifds):
        """Interpret the IFDs.

        This reads the IFDs a second time from a list of dictionaries.
        Unlike the first time, it'll actually interpret the values it
        finds and try to convert them to python values.
        """

        # We'll be returning a more-complicated list of IFDs.
        ifds            = [ ]

        # This is just for now, to track the offsets of particular
        # entries within the tiff file. After this function completes,
        # I'll be discarding this information.
        offsets         = { }

        # I'll keep track of invalid strings.
        invalid_strings = [ ]

        for simple_entries in simple_ifds:
            # We'll construct a new entry dictionary.
            entries             = TiffIFD()

            for tag in simple_entries:
                # Get whatever info we had from before.
                valtype, listlen, value, offset = simple_entries[tag]

                if valtype not in TiffTypeDict:
                    # I don't recognize this type, so I'm ignoring this
                    # entry.
                    self.unknown_types.append(self.UnknownTypeEntry(
                        len(ifds), tag, valtype, offset))

                    continue

                # Cool, we do know the type. Use it with the listlen to
                # figure out the total byte length required by this
                # value.
                valtype         = TiffTypeDict[valtype]
                length          = valtype.bytecount * listlen

                if length > len(value):
                    # Uh oh! I need more than four bytes. That means our
                    # "value" is actually an offset. Go to it.
                    self.tiff.seek(self.bytes_to_int(value))

                    # Before we actually read anything for real, add the
                    # bytes to our ranged list.
                    self.add_bytes(self.tiff.pos(),
                                   length,
                                   (len(ifds), tag, None))

                    # That seemed to work ok. Read in our new, improved
                    # value.
                    value       = self.read(length)

                if valtype.pytype is bytes:
                    value       = value[:length]

                    if valtype.tifftype == TiffType.ASCII:
                        if value[-1] in (0, b"\0"):
                            # If it's a valid string, strip the trailing
                            # NUL byte.
                            value = value[:-1]

                        else:
                            # If it's an invalid string, add its info to
                            # the invalid string list. No need to error
                            # out just yet, as this might be fixible.
                            invalid_strings.append((len(ifds),
                                                    tag,
                                                    offset))

                else:
                    # We expect an array of values.
                    value_array = [ ]

                    if valtype.pytype is int:
                        if valtype.tifftype in self.signed_types:
                            # It's a signed int.
                            convert = self.bytes_to_sint
                        else:
                            # It's an unsigned int.
                            convert = self.bytes_to_int

                    elif valtype.pytype is Fraction:
                        if valtype.tifftype in self.signed_types:
                            # It's a signed rational.
                            convert = self.bytes_to_srational
                        else:
                            # It's an unsigned rational.
                            convert = self.bytes_to_rational

                    elif valtype.pytype is float:
                        # It's a float (these are always signed).
                        convert = self.bytes_to_float

                    else:
                        # I don't know what it is. To make it this far
                        # with an unknown type should never happen.
                        raise Exception("Unexpected pytype: " \
                                        "{}".format(valtype.pytype))

                    for i in range(0, length, valtype.bytecount):
                        # For each slice in the value, append to our
                        # array.
                        value_array.append(convert(
                            value[i:i+valtype.bytecount]))

                    # We actually just want the array, now that it's
                    # complete.
                    value = value_array

                # Yay! We have our value; add it to the new entry
                # dictionary.
                entries[tag] = value
                offsets[(len(ifds), tag)] = offset

            # These entries comprise an IFD. Append to our new IFD list.
            ifds.append(entries)

        # Now that we have complete info, add bytes for strips (I'm
        # considering any tag pairs known to contain offsets and lengths
        # as strips). Now we have all necessary bytes accounted-for.
        self.add_strip_bytes(ifds, offsets)

        # Now that all the valid (ish?) bytes are accounted for, it's
        # time to see if we can make sense of any and all invalid
        # strings.
        self.invalid_strings = self.try_to_fix_strings(ifds,
                                                       invalid_strings)

        # The IFD list is ready.
        return ifds

    def add_strip_bytes (self, ifds, offset_dict):
        """Add remaining bytes from file

        Bytes have been accounted for from the tiff header, each IFD,
        and each overlarge entry within the IFDs. All that's left is to
        handle those entries which always refer to offsets and
        bytecounts.
        """

        for ifd_number, ifd in enumerate(ifds):
            # For each IFD, check the known strip tags.
            for offset, length in self.strip_tags:
                # Are these present?
                if offset in ifd:
                    # This IFD has offsets in this strip type.
                    if length not in ifd:
                        # But it doesn't have bytecounts! Whoooops!
                        self.tiff.error(TiffOffsetsWithoutBytecounts,
                                        offset_dict[(ifd_number,
                                                     offset)],
                                        offset,
                                        TiffTagNameDict.get(offset,
                                                            "unknown"),
                                        length,
                                        TiffTagNameDict.get(length,
                                                            "unknown"))

                    # Ok cool, it has both. Get the value arrays.
                    offsets = ifd[offset]
                    lengths = ifd[length]

                    if len(offsets) != len(lengths):
                        # Uh oh, the arrays have different lengths. I
                        # can't match them up!
                        self.tiff.error(TiffOffsetsWithoutBytecounts,
                                        offset_dict[(ifd_number,
                                                     offset)],
                                        offset,
                                        TiffTagNameDict.get(offset,
                                                            "unknown"),
                                        length,
                                        TiffTagNameDict.get(length,
                                                            "unknown"))

                    for strip_i, pos_i, len_i in zip(count(),
                                                     offsets,
                                                     lengths):
                        # Try to add the bytes for each strip.
                        self.add_bytes(pos_i, len_i, (ifd_number,
                                                      offset,
                                                      strip_i))

    def try_to_fix_strings (self, ifds, invalid_strings):
        """Try to fix invalid strings.

        For the most part, each invalid string is probably just exactly
        right except for lacking the zero byte. All the same, it's not a
        bad idea to collect possibilities, since I know exactly which
        bytes in the file are accounted for.

        This returns a list of 3-tuples, defined by InvalidStringEntry.
        The third value will be either a list of suggestions or a single
        string. In that last case, the string will match the string in
        the IFD. It means I'm rather sure it's correct.
        """

        # We'll return the same list but with suggestions this time.
        with_suggestions = [ ]

        for ifd, tag, offset in invalid_strings:
            # I'll put my suggestions here.
            suggestions = [ ]
            entry       = ifds[ifd][tag]

            # Go to the IFD entry. Skip the first four bytes (tag and
            # type).
            self.tiff.seek(offset + 4)

            # The next four bytes are the byte count.
            strlen      = self.read_int(4)

            # I know this'll be in scope even if I don't declare it
            # here, but I'm paranoid.
            full        = b""

            if strlen <= 4:
                # If the string is no more than four bytes long, all I
                # can do is read all four bytes.
                full    = self.read(4)

            else:
                # Go to the string and read it in again.
                self.tiff.seek(self.read_int(4))
                full    = self.read(strlen)

                # Where are we? Where are we going?
                pos     = self.tiff.pos()
                nextpos = self.tiff_bytes.first_after_or_at(pos)

                if nextpos is None:
                    # If there's nothing after this, we can just read to
                    # the end of the file.
                    full += self.read()

                else:
                    # We found something else in the tiff, so we can't
                    # read anything after that point (since it belongs
                    # to some other part of the file).
                    full += self.read(nextpos - pos)

            # Search for a NUL byte.
            index = full.find(b"\0")
            while index != -1:
                # We found one! That means we have an alternate guess.
                guess   = full[:index]

                if guess == entry:
                    # This guess actually matches our main guess! That
                    # makes it far-and-away the best candidate. No need
                    # to even keep track of anything else, really.
                    suggestions = None
                    break

                # Otherwise, add this guess to the suggestion list. See
                # if we can find another NUL byte.
                suggestions.append(guess)
                index = full.find(b"\0", index + 1)

            if suggestions is None:
                # We found a valid string that matches the one given
                # exactly. The TIFF is still invalid, but at least we
                # basically know what the answer is. Nice! Just give the
                # main guess again, to reinforce its probability.
                suggestions = entry

            elif strlen < len(full) and full[-1] != b"\0":
                # Otherwise, we have a list of suggestions. If our new
                # "full" string is indeed longer than the main guess,
                # then we should probably add it to the suggestion list.
                # Unless, that is, its last byte is NUL, in which case
                # it'll already have been added.
                suggestions.append(full)

            # Add a new entry, this time with whatever suggestions we
            # managed to find.
            with_suggestions.append(
                    self.InvalidStringEntry(ifd, tag, suggestions))

        return with_suggestions

    def add_bytes (self, start, length, value):
        """Account for bytes in the tiff file"""
        # This is just a shortcut for a commonly-run thing.
        self.tiff_bytes[start:start + length] = value

    def read (self, length = None):
        """Read bytes from the tiff file.

        This is just a simple filestream read, except that it raises an
        exception rather than return an unexpected count of bytes. It is
        useful in detecting unexpected end-of-file markers.
        """

        return self.tiff.read(length)

    def read_int (self, length):
        """Read an integer from the tiff file"""
        # This is a shortcut for reading in an int from the tiff.
        return self.bytes_to_int(self.read(length))

    def int_to_bytes (self, integer, length):
        """Convert int to bytes"""
        return int_to_bytes(integer, length, self.byte_order)

    def bytes_to_int (self, bytestring):
        """Convert bytes to int"""
        return bytes_to_int(bytestring, self.byte_order)

    def bytes_to_sint (self, bytestring):
        """Convert bytes to signed int"""
        # We'll get the unsigned result, and we'll calculate the
        # smallest integer too large to fit in this bytestring's length.
        result      = self.bytes_to_int(bytestring)
        one_more    = bytes_to_int(
                        b"\1" + int_to_bytes(0, len(bytestring), "big"),
                        "big")

        if result < one_more // 2:
            # As long as the sign bit is not set, leave it as-is.
            return result

        # Otherwise, we subtract one_more to assert negativity.
        return result - one_more

    def general_bytes_to_rational (self, bytestring, to_int):
        """Convert bytes to rational using a passed bytes to int
        converter"""
        # Rather than look anything up, just go ahead and take half.
        numlength   = len(bytestring) // 2

        # We return a fraction.
        return Fraction(to_int(bytestring[:numlength]),
                        to_int(bytestring[numlength:]))

    def bytes_to_rational (self, bytestring):
        """Convert bytes to unsigned Fraction"""
        return self.general_bytes_to_rational(bytestring,
                                              self.bytes_to_int)

    def bytes_to_srational (self, bytestring):
        """Convert bytes to signed Fraction"""
        return self.general_bytes_to_rational(bytestring,
                                              self.bytes_to_sint)

    def bytes_to_float (self, bytestring):
        """Convert bytes to float using IEEE 754 specs"""
        # The length of the bytestring matters.
        bytecount   = len(bytestring)

        if bytecount not in IEEE_754_Parameters:
            # If we don't know how to handle a float of this size, we
            # give up.
            self.tiff.error(TiffFloatError, 0, bytecount,
                            "" if bytecount == 1 else "s")

        # Get masks for each piece.
        sign_mask, exp_mask, num_mask = IEEE_754_Parameters[bytecount]

        # Work out the denominator for the number part.
        denominator = num_mask + 1

        # We'll also want the maximum exponent and the exponent offset.
        max_exp = exp_mask // denominator
        offset  = max_exp // 2

        # Convert the byte string to an integer.
        as_int  = self.bytes_to_int(bytestring)

        # Get the three separate parameters.
        sign    = (as_int & sign_mask) > 0
        exp     = (as_int & exp_mask) // denominator
        num     = (as_int & num_mask)

        if exp == max_exp:
            # At the exponent's maximum value, there are three possible
            # return values.
            if num == 0:
                # If the numerator is zero, then the return value is
                # infinity (either positive or negative).
                if sign:
                    # If there's a sign, then it's negative infinity.
                    return -infinity

                # Otherwise, it's positive infinity.
                return infinity

            # The numerator is nonzero, which means we return NaN.
            return NaN

        if exp == 0:
            # At the exponent's zero value, we either return zero or a
            # denormal number.
            if numerator == 0:
                # The numerator is zero, so it's zero.
                return 0

            # Denormal numbers treat the exponent as if it were set to 1
            # except that the denominator is not added to the numerator,
            # so our fraction remains between 0 and 1.
            return Float(numerator,
                         denominator,
                         1 - offset)

        # In a normalized value, the numerator and denominator are added
        # together to give a fraction between 1 and 2.
        return Float(numerator + denominator,
                     denominator,
                     exp - offset)
