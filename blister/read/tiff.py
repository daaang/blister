# Copyright (c) 2015 The Regents of the University of Michigan.
# All Rights Reserved. Licensed according to the terms of the Revised
# BSD License. See LICENSE.txt for details.
from bisect         import  bisect_left
from collections    import  namedtuple, Mapping, Sequence
from fractions      import  Fraction
from io             import  BytesIO, BufferedReader
from itertools      import  count
from numpy          import  nan as NaN, inf as infinity
from random         import  randrange
import unittest

# This is kinda an enumeration of TIFF data types.
class TiffType:
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

IEEE_754_Parameters = {
    4:  (0x80000000,
         0x7f800000,
         0x007fffff),
    8:  (0x8000000000000000,
         0x7ff0000000000000,
         0x000fffffffffffff),
}

class Float:
    def __init__ (self, numerator, denominator, exponent):
        # We keep a fraction and an exponent.
        self.fraction   = Fraction(numerator, denominator)
        self.exponent   = exponent

    def __float__ (self):
        if self.exponent < 0:
            # Negative exponents invoke division.
            return float(self.fraction) / (float(2)**(-self.exponent))

        # Positive exponents are for multiplying.
        return float(self.fraction) * (float(2)**self.exponent)

class RangedList (Mapping):
    def __init__ (self):
        self.sorted_list    = [(0, 0, None)]

    def __getitem__ (self, key):
        # Have a look at the given key.
        if isinstance(key, int):
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
                return [(key, value)]

            # Otherwise, we need to keep going.
            result.append((slice(key.start, high), value))

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
            result.append((slice(low, high), value))

        # Finally, get the values at the final index.
        low, high, value = self.sorted_list[stop]
        result.append((slice(low, min(high, key.stop)), value))

        # Our result list is complete.
        return result

    def __contains__ (self, key):
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
        # For our purposes, the length is the slice stop value in the
        # very last section.
        return self.sorted_list[-1][1]

    def __iter__ (self):
        # Mapping types are supposed to iterate over keys by default.
        return self.keys()

    def keys (self):
        for i, j, k in self.sorted_list[1:]:
            yield slice(i, j)

    def values (self):
        for i, j, k in self.sorted_list[1:]:
            yield k

    def items (self):
        for i, j, k in self.sorted_list[1:]:
            yield (slice(i, j), k)

    def first_after_or_at (self, key):
        if key in self:
            return key

        if key >= len(self):
            return None

        return self.sorted_list[self.get_internal_index(key) + 1][0]

    def key_to_slice (self, key):
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

        if isinstance(key, int):
            # It's an int! For my purposes, it's a slice with a length
            # of one.
            return slice(key, key + 1)

        # Uh oh! I don't recognize this junk!
        raise KeyError("Need int or slice, not {}".format(
                                repr(key)))

    def get_internal_index (self, x, lo = 0):
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

class Tiff:
    # Bytes are base 256.
    byte_base               = 0x100

    expected_byte_orders    = {
        b"II":  "little",
        b"MM":  "big",
    }

    magic_check_number      = 42

    signed_types            = set((
        TiffType.SBYTE,
        TiffType.SSHORT,
        TiffType.SLONG,
        TiffType.SRATIONAL,
    ))

    strip_tags              = (
        (0x111, 0x117),
    )

    NUL                     = b"\0"

    class TiffError (Exception):
        def __init__ (self, position, message):
            # Every tiff error comes with a position inside the tiff and
            # an error message.
            self.position   = position
            self.message    = message

        def __str__ (self):
            # And here's how we display the error by default.
            return "{msg} (0x{pos:08x})".format(
                    pos = self.position,
                    msg = str(self.message))

    class Err (Exception):
        # I use this as a quick-and-dirty exception that will be fed to
        # the more clear exception classes.
        pass

    OutOfOrderEntry     = namedtuple("OutOfOrderEntry",
                            ("ifd", "tag", "prev_max"))
    UnknownTypeEntry    = namedtuple("UnknownTypeEntry",
                            ("ifd", "tag", "code", "offset"))
    InvalidStringEntry  = namedtuple("InvalidStringEntry",
                            ("ifd", "tag", "suggestions"))
    IFDEntry            = namedtuple("IFDEntry",
                            ("value", "tifftype", "offset"))

    def __init__ (self, file_object):
        if not isinstance(file_object, BufferedReader):
            # Assert that we have an "rb" file.
            raise TypeError("Expected a file with mode 'rb'")

        # We should start at the beginning.
        file_object.seek(0)

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
        return self.ifds[key]

    def __len__ (self):
        return len(self.ifds)

    def __iter__ (self):
        for ifd in self.ifds:
            yield ifd

    def read_header (self):
        try:
            # Try to get the byte order.
            self.byte_order = self.expected_byte_orders[
                                            self.tiff.read(2)]

        except KeyError as e:
            # If it didn't work, raise an error.
            self.raise_error(-2, "Unknown byte order: {}".format(
                str(e)))

        # Read the magic number (it's 42).
        forty_two   = self.read_int(2)

        if forty_two != self.magic_check_number:
            # Uh oh! It's something other than 42 oh no oh no!
            self.raise_error(-2, "Expected {:d}; found {:d}".format(
                                    self.magic_check_number,
                                    forty_two))

        # Cool. Next is the IFD offset. How many bytes have we read so
        # far? (The answer is absolutely going to be 8.)
        ifd_offset                      = self.read_int(4)
        header_length                   = self.tiff.tell()

        if ifd_offset < header_length:
            # Be sure the offset doesn't point to anywhere in the tiff
            # header.
            self.raise_error(-4, "IFD offset must be at least {:d};" \
                             " you gave me {:d}".format(header_length,
                                                        ifd_offset))

        # Add the header bytes to the byte range.
        self.add_bytes(0, header_length, (None, None, None))

        # Return the first IFD offset.
        return ifd_offset

    def read_ifds (self, ifd_offset):
        # We'll be collecting IFDs as well as info about problem
        # entries.
        ifds                    = [ ]
        self.out_of_order_ifds  = [ ]

        while ifd_offset != 0:
            # Go to the IFD and read the entry count.
            self.tiff.seek(ifd_offset)
            entry_count = self.read_int(2)

            if entry_count < 1:
                # Be sure that we have at least one entry.
                self.raise_error(-2,
                        "IFD{:d} must have at least one entry".format(
                                len(ifds)))

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
                offset          = self.tiff.tell()
                tag             = self.read_int(2)
                valtype         = self.read_int(2)
                listlen         = self.read_int(4)
                value           = self.tiff.read(4)

                if tag in entries:
                    # No duplicate entries are allowed.
                    self.raise_error(offset,
                            "Tag {tag:d} (0x{tag:x}) is already in" \
                            " IFD{ifd:d}; no duplicates allowed".format(
                                    tag = tag,
                                    ifd = len(ifds)))

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
        # We'll be returning a more-complicated list of IFDs.
        ifds                    = [ ]

        # I'll keep track of unknown types and invalid strings.
        self.unknown_types      = [ ]
        invalid_strings         = [ ]

        for simple_entries in simple_ifds:
            # We'll construct a new entry dictionary.
            entries             = { }

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
                    self.add_bytes(self.tiff.tell(),
                                   length,
                                   (len(ifds), tag, None))

                    # That seemed to work ok. Read in our new, improved
                    # value.
                    value       = self.tiff.read(length)

                if valtype.pytype is bytes:
                    value       = value[:length]

                    if valtype.tifftype == TiffType.ASCII:
                        if value[-1] == 0:
                            # If it's a valid string, strip the trailing
                            # NUL byte.
                            value = value[:-1]

                        else:
                            # If it's an invalid string, add its info to
                            # the invalid string list. No need to error
                            # out just yet, as this might be fixible.
                            invalid_strings.append(
                                    self.InvalidStringEntry(
                                            len(ifds), tag, [ ]))

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
                entries[tag] = self.IFDEntry(value,
                                             valtype.tifftype,
                                             offset)

            # These entries comprise an IFD. Append to our new IFD list.
            ifds.append(entries)

        # Now that we have complete info, add bytes for strips (I'm
        # considering any tag pairs known to contain offsets and lengths
        # as strips). Now we have all necessary bytes accounted-for.
        self.add_strip_bytes(ifds)

        # Now that all the valid (ish?) bytes are accounted for, it's
        # time to see if we can make sense of any and all invalid
        # strings.
        self.invalid_strings = self.try_to_fix_strings(ifds,
                                                       invalid_strings)

        # The IFD list is ready.
        return ifds

    def add_strip_bytes (self, ifds):
        for ifd_number, ifd in enumerate(ifds):
            # For each IFD, check the known strip tags.
            for offset, length in self.strip_tags:
                # Are these present?
                if offset in ifd:
                    # This IFD has offsets in this strip type.
                    if length not in ifd:
                        # But it doesn't have bytecounts! Whoooops!
                        self.raise_error(ifd[offset].offset,
                                "Can't have tag {:d} without also" \
                                " having tag {:d}".format(offset,
                                                          length))

                    # Ok cool, it has both. Get the value arrays.
                    offsets = ifd[offset].value
                    lengths = ifd[length].value

                    if len(offsets) != len(lengths):
                        # Uh oh, the arrays have different lengths. I
                        # can't match them up!
                        self.raise_error(ifd[offset].offset,
                                "Array lengths must match between" \
                                " tags {:d} and {:d}".format(offset,
                                                             length))

                    for strip_i, pos_i, len_i in zip(count(),
                                                     offsets,
                                                     lengths):
                        # Try to add the bytes for each strip.
                        self.add_bytes(pos_i, len_i, (ifd_number,
                                                      offset,
                                                      strip_i))

    def try_to_fix_strings (self, ifds, invalid_strings):
        # We'll return the same list but with suggestions this time.
        with_suggestions = [ ]

        for ifd, tag, junk in invalid_strings:
            # I'll put my suggestions here.
            suggestions = [ ]
            entry       = ifds[ifd][tag]
            main_guess  = entry.value

            # Go to the IFD entry. Skip the first four bytes (tag and
            # type).
            self.tiff.seek(entry.offset + 4)

            # The next four bytes are the byte count.
            strlen      = self.read_int(4)

            # I know this'll be in scope even if I don't declare it
            # here, but I'm paranoid.
            full        = b""

            if strlen <= 4:
                # If the string is no more than four bytes long, all I
                # can do is read all four bytes.
                full    = self.tiff.read(4)

            else:
                # Go to the string and read it in again.
                self.tiff.seek(self.read_int(4))
                full    = self.tiff.read(strlen)

                # Where are we? Where are we going?
                pos     = self.tiff.tell()
                nextpos = self.tiff_bytes.first_after_or_at(pos)

                if nextpos is None:
                    # If there's nothing after this, we can just read to
                    # the end of the file.
                    full += self.tiff.read()

                else:
                    # We found something else in the tiff, so we can't
                    # read anything after that point (since it belongs
                    # to some other part of the file).
                    full += self.tiff.read(nextpos - pos)

            # Search for a NUL byte.
            index = full.find(self.NUL)
            while index != -1:
                # We found one! That means we have an alternate guess.
                guess   = full[:index]

                if guess == main_guess:
                    # This guess actually matches our main guess! That
                    # makes it far-and-away the best candidate. No need
                    # to even keep track of anything else, really.
                    suggestions = None
                    break

                # Otherwise, add this guess to the suggestion list. See
                # if we can find another NUL byte.
                suggestions.append(guess)
                index = full.find(self.NUL, index + 1)

            if suggestions is None:
                # We found a valid string that matches the one given
                # exactly. The TIFF is still invalid, but at least we
                # basically know what the answer is. Nice! Just give the
                # main guess again, to reinforce its probability.
                suggestions = main_guess

            elif strlen < len(full) and full[-1] != self.NUL:
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
        # This is just a shortcut for a commonly-run thing.
        self.tiff_bytes[start:start + length] = value

    def read_int (self, length):
        # This is a shortcut for reading in an int from the tiff.
        return self.bytes_to_int(self.tiff.read(length))

    def raise_error (self, pos, message = None):
        if message is None:
            # It's actually the position that I want to be optional. If
            # there's no position, correctly label the message, and get
            # the position from the file.
            message = pos
            pos     = self.tiff.tell()

        if pos < 0:
            # If the position is a relative negative, add the actual
            # position.
            pos    += self.tiff.tell()

        # Let's be nice and close the file.
        self.tiff.close()

        # Yayyy!
        raise self.TiffError(pos, message)

    def int_to_bytes (self, integer, length):
        return integer.to_bytes(length, self.byte_order)

    def bytes_to_int (self, bytestring):
        return int.from_bytes(bytestring, self.byte_order)

    def bytes_to_sint (self, bytestring):
        # We'll get the unsigned result, and we'll calculate the
        # smallest integer too large to fit in this bytestring's length.
        result      = self.bytes_to_int(bytestring)
        one_more    = int.from_bytes(
                        b"\1" + (0).to_bytes(len(bytestring), "big"),
                        "big")

        if result < one_more // 2:
            # As long as the sign bit is not set, leave it as-is.
            return result

        # Otherwise, we subtract one_more to assert negativity.
        return result - one_more

    def general_bytes_to_rational (self, bytestring, to_int):
        # Rather than look anything up, just go ahead and take half.
        numlength   = len(bytestring) // 2

        # We return a fraction.
        return Fraction(to_int(bytestring[:numlength]),
                        to_int(bytestring[numlength:]))

    def bytes_to_rational (self, bytestring):
        return self.general_bytes_to_rational(bytestring,
                                              self.bytes_to_int)

    def bytes_to_srational (self, bytestring):
        return self.general_bytes_to_rational(bytestring,
                                              self.bytes_to_sint)

    def bytes_to_float (self, bytestring):
        # The length of the bytestring matters.
        bytecount   = len(bytestring)

        if bytecount not in IEEE_754_Parameters:
            # If we don't know how to handle a float of this size, we
            # give up.
            raise self.Err("I don't know how to make a float {:d}" \
                    " byte{} long".format(bytecount,
                        "" if bytecount == 1 else "s"))

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

########################################################################
############################### Testing ################################
########################################################################

class TestRangedList (unittest.TestCase):
    def setUp (self):
        self.ranged_list = RangedList()

        self.ranged_list[0:10]      = "the first ten bytes"
        self.ranged_list[90:100]    = "ninety through ninety-nine"
        self.ranged_list[44]        = "forty-four"

    def test_length (self):
        self.assertEqual(len(self.ranged_list), 100,
                         "length should be 100")

    def test_bad_insert_left (self):
        with self.assertRaisesRegex(KeyError,
                                    r"Can't reassign values"):
            self.ranged_list[85:95]     = "uh oh"

    def test_bad_insert_right (self):
        with self.assertRaisesRegex(KeyError,
                                    r"Can't reassign values"):
            self.ranged_list[95:105]    = "uh oh"

    def test_bad_insert_inside (self):
        with self.assertRaisesRegex(KeyError,
                                    r"Can't reassign values"):
            self.ranged_list[92:98]     = "uh oh"

    def test_bad_insert_outside (self):
        with self.assertRaisesRegex(KeyError,
                                    r"Can't reassign values"):
            self.ranged_list[85:105]    = "uh oh"

    def test_bad_insert_zero_slice (self):
        with self.assertRaisesRegex(KeyError,
                                    r"Can't insert empty slice"):
            self.ranged_list[20:20]     = "uh oh"

    def test_bad_insert_stepped (self):
        with self.assertRaisesRegex(KeyError,
                                    r"Invalid step [0-9]+ \(if set" \
                                    r" at all, it must be 1\)"):
            self.ranged_list[30:50:2]   = "uh oh"

    def test_bad_insert_nonslice (self):
        with self.assertRaisesRegex(KeyError,
                                    r"Need int or slice, not"):
            self.ranged_list["hey"]     = "uh oh"

    def test_bad_insert_negative (self):
        with self.assertRaisesRegex(KeyError,
                                    r"Negative indeces are not" \
                                    r" allowed \(you gave me"):
            self.ranged_list[-5:5]      = "uh oh"

    def test_accessors_ints (self):
        # Test each int accessor.
        for i in range(10):
            self.assertEqual(self.ranged_list[i], "the first ten bytes",
                             "wrong values from the first insertion")

        for i in range(90, 100):
            self.assertEqual(self.ranged_list[i],
                             "ninety through ninety-nine",
                             "wrong values from the second insertion")

    def test_accessors_slice (self):
        # Test some slices.
        self.assertEqual(self.ranged_list[5:8],
                         [(slice(5, 8), "the first ten bytes")])

        self.assertEqual(self.ranged_list[5:20],
                         [(slice(5, 10), "the first ten bytes")])

        self.assertEqual(self.ranged_list[:95],
                         [(slice(0, 10), "the first ten bytes"),
                         (slice(44, 45), "forty-four"),
                         (slice(90, 95), "ninety through ninety-nine")])

    def test_iteration (self):
        items   = [
            (slice(0, 10),      "the first ten bytes"),
            (slice(44, 45),     "forty-four"),
            (slice(90, 100),    "ninety through ninety-nine"),
        ]

        # We'll be able to infer the keys and values from the items.
        # Since iteration is by keys by default, we'll need two
        # different arrays of keys.
        keys    = [[ ], [ ]]
        values  = [ ]

        # Autofill.
        for i, j in items:
            for k in range(2):
                # Once again, we have two arrays of keys, to test both
                # generators.
                keys[k].append(i)

            # We'll also fill the values.
            values.append(j)

        for x in self.ranged_list:
            # Check the __iter__ generator first.
            self.assertEqual(x, keys[0].pop(0))

        for x in self.ranged_list.keys():
            # Check the explicit keys next.
            self.assertEqual(x, keys[1].pop(0))

        for x in self.ranged_list.values():
            self.assertEqual(x, values.pop(0))

        for x in self.ranged_list.items():
            self.assertEqual(x, items.pop(0))

    def test_containment_ints (self):
        # Test some basic containment operations.
        self.assertTrue(   0 in self.ranged_list)
        self.assertTrue(   5 in self.ranged_list)
        self.assertFalse( 10 in self.ranged_list)
        self.assertFalse( 50 in self.ranged_list)
        self.assertTrue(  90 in self.ranged_list)
        self.assertTrue(  95 in self.ranged_list)
        self.assertFalse(100 in self.ranged_list)

    def test_containment_slices (self):
        self.assertTrue(slice(0,    10)     in self.ranged_list)
        self.assertTrue(slice(0,    15)     in self.ranged_list)
        self.assertFalse(slice(10,  20)     in self.ranged_list)
        self.assertTrue(slice(9,    28)     in self.ranged_list)
        self.assertTrue(slice(3,     7)     in self.ranged_list)
        self.assertTrue(slice(80,   91)     in self.ranged_list)
        self.assertFalse(slice(80,  90)     in self.ranged_list)

class TestTiff (unittest.TestCase):
    # This is a valid tiff with CCITT Group4 compression.
    tinytiff    = bytes.fromhex("""\
                    49 49  2a 00  08 00 00 00               \
                                                            \
                    0c 00                                   \
                    00 01  03 00  01 00 00 00  6c 00 00 00  \
                    01 01  03 00  01 00 00 00  24 00 00 00  \
                    02 01  03 00  01 00 00 00  01 00 00 00  \
                    03 01  03 00  01 00 00 00  04 00 00 00  \
                    06 01  03 00  01 00 00 00  00 00 00 00  \
                    0a 01  03 00  01 00 00 00  01 00 00 00  \
                    11 01  04 00  01 00 00 00  9e 00 00 00  \
                    15 01  03 00  01 00 00 00  01 00 00 00  \
                    17 01  04 00  01 00 00 00  50 00 00 00  \
                    1c 01  03 00  01 00 00 00  01 00 00 00  \
                    28 01  03 00  01 00 00 00  02 00 00 00  \
                    3b 01  02 00  06 00 00 00  ee 00 00 00  \
                                               00 00 00 00  \
                                                            \
                    f3 6c 90 cc c3 99 86 83                 \
                    61 a0 db ff ff ff ff ff                 \
                    91 6e 6d 92 19 21 91 0f                 \
                    ff ff ff ff ff fe 5d 97                 \
                    7f ff ff ff ff ff ff ff                 \
                    f1 e3 ff ff ff ff ff ff                 \
                    e5 91 ff ff ff ff ff ff                 \
                    ff ff 1f ff ff ff ff ff                 \
                    ff 24 3f ff ff ff ff ff                 \
                    c4 44 44 47 c0 04 00 40                 \
                                                            \
                    4d 61 74 74 21 00""")

    def setUp (self):
        self.tiff_obj = Tiff(BufferedReader(BytesIO(self.tinytiff)))

    def test_file_is_mode_rb (self):
        # Be sure we won't accept any files that aren't binary
        # read-only.
        for i in ("r", "w", "wb", "a", "ab"):
            with open("/dev/null", i) as dev_null:
                with self.assertRaisesRegex(TypeError,
                        r"Expected a file with mode 'rb'"):
                    tiff = Tiff(dev_null)

    def test_invalid_byte_orders (self):
        valid = set((b"II", b"MM"))

        for i in range(0x100):
            # We'll try a bunch of random bad bytestrings.
            randbytes = b"II"
            while randbytes in valid:
                randbytes = randrange(0x10000).to_bytes(2, "big")

            with self.assertRaisesRegex(Tiff.TiffError,
                    r"Unknown byte order: .*0x00000000"):
                tiff = Tiff(BufferedReader(BytesIO(randbytes)))

    def test_forty_two (self):
        orders  = {b"II": "little", b"MM": "big"}
        regex   = r"Expected 42; found {:d} .0x00000002".format

        for head, order in orders.items():
            # Let's start with 0x2a00 just to be sure it's doing the
            # right thing with the endienness.
            j = 0x100 * 42
            for i in range(0x100):
                while j == 42:
                    j = randrange(0x10000)

                with self.assertRaisesRegex(Tiff.TiffError, regex(j)):
                    tiff = Tiff(BufferedReader(BytesIO(
                                head + j.to_bytes(2, order))))

                j = randrange(0x10000)

    def test_ifd_min (self):
        regex   = r"IFD offset must be at least 8; you gave me {:d}"
        for i in range(8):
            with self.assertRaisesRegex(Tiff.TiffError,
                    regex.format(i)):
                tiff = Tiff(BufferedReader(BytesIO(self.tinytiff[:4]
                            + i.to_bytes(4, "little"))))

    def test_ifd_entry_count (self):
        with self.assertRaisesRegex(Tiff.TiffError,
                r"IFD0 must have at least one entry .0x00000008"):
            tiff = Tiff(BufferedReader(BytesIO(self.tinytiff[:8]
                        + b"\0\0")))

    def test_ifd_no_duplicate_entries (self):
        with self.assertRaisesRegex(Tiff.TiffError,
                r"Tag 256 \(0x100\) is already in IFD0;" \
                r" no duplicates allowed .0x00000016"):
            tiff = Tiff(BufferedReader(BytesIO(self.tinytiff[:0x16]
                        + b"\0" + self.tinytiff[0x17:])))

    def test_valid_ifdlen (self):
        self.assertEqual(1, len(self.tiff_obj))
        self.assertEqual(0xc, len(self.tiff_obj[0]))

    def test_valid_single_numbers (self):
        for tag, value, message in (
                (256, 108,  "width"),
                (257, 36,   "height"),
                (258, 1,    "bits/sample"),
                (277, 1,    "samples/pixel"),
                (259, 4,    "group4 compression"),
                (262, 0,    "zero-is-white colorspace")):
            self.assertEqual(1, len(self.tiff_obj[0][tag].value),
                             message)
            self.assertEqual(value, self.tiff_obj[0][tag].value[0],
                             message)

    def test_artist (self):
        self.assertEqual(b"Matt!", self.tiff_obj[0][315].value)

if __name__ == "__main__":
    # If this is accessed directly, test everything.
    unittest.main()
