# Copyright (c) 2015 The Regents of the University of Michigan.
# All Rights Reserved. Licensed according to the terms of the Revised
# BSD License. See LICENSE.txt for details.
from collections    import  namedtuple, Mapping, deque
from fractions      import  Fraction
from generic        import  FileReader
from io             import  BytesIO, BufferedReader

class BoxedFile (FileReader):
    """Boxed File Reader

    This is just like the regular file reader, except that it has an
    additional function for reading boxes and positioning itself after
    the end.

    For example, let's say we have a valid JP2 beginning with a
    signature (12 bytes) followed by a file type box (20 bytes). We'll
    start by initializing the file and seeking to the beginning.

        >>> boxed_file = BoxedFile(jp2_file_stream)
        >>> boxed_file.seek(0)
        >>> boxed_file.pos()
        0

    Next, we'll read a box. Notice how the offset points after the box
    header, and the length refers only to the content (rather than
    including it, as it does in the JP2 itself).

        >>> boxed_file.try_to_read_new_box()
        JP2BoxTuple(name='jP  ', offset=8, length=4)
        >>> boxed_file.pos()
        12

    Pointed at the next box, we have another go:

        >>> boxed_file.try_to_read_new_box()
        JP2BoxTuple(name='ftyp', offset=20, length=12)
        >>> boxed_file.pos()
        32

    It is up to you to capture and interpret this information. The
    entire goal here is to take in the overall structure.
    """

    # The tuples returned by try_to_read_new_box are named according to
    # this format. If length is None, it means the box continues to the
    # end of the file.
    JP2BoxTuple = namedtuple("JP2BoxTuple",
                             ("name", "offset", "length"))

    def try_to_read_new_box (self):
        """Try to read a box.

        Attempts to read a JP2 box from the internal file. If we're at
        the EOF, we return None.

        Otherwise, we'll return a JP2BoxTuple describing the box we
        found.

        Raises errors for unexpected EOFs as well as for too-small
        length values.

        If the returned box length is None, you should stop running this
        method. It means we've read the last box.

        Otherwise, the file pointer will be positioned at the beginning
        of what should be the next box (or just the EOF).
        """
        # Read without asserting anything about the EOF.
        name    = self.quick_read(4)

        if len(name) == 0:
            # If we were already at the EOF, return expected failure.
            return None

        # Collect the length next. It's a 4-byte integer.
        length  = self.read_int(4)

        if length == 0:
            # If the length is zero, it means we read to the end of the
            # file. In other words, this is the last box.
            return self.JP2BoxTuple(name, self.pos(), None)

        if length == 1:
            # If the length is one, it means we need to read an eight
            # byte length instead (XL).
            length  = self.read_int(8)

            if length < 16:
                # Be sure the length at least accounts for the sixteen
                # bytes we've just read.
                self.error(-8, "XL Length must be at least 16")

            # Subtract 8 to make this XL length better match a regular L
            # length.
            length -= 8

        if length < 8:
            # Be sure the length at least accounts for the eight bytes
            # we've just read. (If we had an XL length, we already know
            # that it's larger than 8.)
            self.error(-4, "L Length must be at least 8")

        # Subtract 8 in order to stop factoring in the name and length.
        length -= 8

        # Record where we are and skip to just before the beginning of
        # the next box.
        pos     = self.pos()
        self.seek(pos + length - 1)

        # We skipped to just before the beginning of the next box so
        # that we could assert that we haven't unexpectedly reached the
        # end of the file before the end of the box. Read that one last
        # character now.
        junk = self.read(1)

        # Here's our box!
        return self.JP2BoxTuple(name, pos, length)

class AbstractBox (Mapping):
    # These are all nineteen boxes mentioned in the JPEG2000
    # specification.
    box_mapping = {
        # Main boxes:
        b"jP  ": "JP2SignatureBox",
        b"ftyp": "FileTypeBox",
        b"jp2h": "JP2HeaderBox",
        b"jp2c": "ContiguousCodeStreamBox",
        b"jp2i": "IPRBox",
        b"xml ": "XMLBox",
        b"uuid": "UUIDBox",
        b"uinf": "UUIDInfoBox",

        # Header boxes:
        b"ihdr": "ImageHeaderBox",
        b"bpcc": "BitsPerComponentBox",
        b"colr": "ColorSpecificationBox",
        b"pclr": "PaletteBox",
        b"cmap": "ComponentMappingBox",
        b"cdef": "ChannelDefinitionBox",
        b"res ": "ResolutionBox",

        # Resolution boxes:
        b"resc": "CaptureResolutionBox",
        b"resd": "DefaultDisplayResolutionBox",

        # UUID info boxes
        b"ulst": "UUIDListBox",
        b"url ": "DataEntryURLBox",
    }

    multiple    = set((
        b"jp2c",
        b"xml ",
        b"uuid",
        b"uinf",
        b"colr",
    ))

    def __init__ (self, jp2, box_tuple):
        # Store the file object and initialize an ordered dictionary.
        self.jp2    = jp2
        self.initialize_data()

        # Seek to the beginning of the box and pull its data.
        self.jp2.seek(box_tuple.offset)
        self.pull_box_data(box_tuple.length)

    def pull_box_data (self, length):
        # By default, we just load the entire bytestring into a single
        # entry.
        self.data["value"] = self.jp2[length]

    def __getitem__ (self, key):
        """Get value from internal dict"""
        return self.data[key]

    def __len__ (self):
        """Get length of internal dict"""
        return len(self.order)

    def __iter__ (self):
        """Iterate over internal dict"""
        return self.keys()

    def __contains__ (self, key):
        if key in self.multiple:
            return len(self.data[key]) > 0
        return key in self.data

    def keys (self):
        for key, seq in self.order:
            yield key

    def items (self):
        for key, seq in self.order:
            if seq is None:
                yield (key, self.data[key])
            else:
                yield (key, self.data[key][seq])

    def values (self):
        for key, seq in self.order:
            if seq is None:
                yield self.data[key]
            else:
                yield self.data[key][seq]

    def __repr__ (self):
        if len(self) == 1 and "value" in self:
            return "<{} {}>".format(self.__class__.__name__,
                                    repr(self["value"]))

        pairs   = [ ]
        for key, value in self.data.items():
            pairs.append("{}={}".format(repr(key), repr(value)))

        return "<{} {}>".format(self.__class__.__name__,
                                ", ".join(pairs))

    def __str__ (self):
        # Just go on ahead, starting with no indent.
        return self.to_string()

    def initialize_data (self):
        self.data   = { }
        self.order  = deque()

        for name in self.multiple:
            self.data[name] = [ ]

    def insert (self, key, value):
        if key in multiple:
            self.order.append((name, len(self.data[name])))
            self.data[name].append(value)

        elif key in self.data:
            self.jp2.error("Didn't expect more than one {} key".format(
                            repr(name)))

        else:
            self.order.append((name, None))
            self.data[name] = value

    def assert_length_large_enough (self, length):
        if length < self.min_length:
            self.jp2.error("Expected a box of at least {:d} bytes;" \
                           " {:d} is too few".format(min_length,
                                                     length))

    def to_string (self, indent = ""):
        # We don't actually use the indent directly right away. We just
        # spit out the class name right from the start and increase the
        # indent for our own purposes.
        result = self.__class__.__name__
        indent += "  "

        if len(self) == 1 and "value" in self:
            return "<{} {}>".format(result, repr(self["value"]))

        for key, value in self.data.items():
            if isinstance(value, AbstractBox):
                # If this value is a box, it should be displayed as such
                # with this further indent level.
                value_str = value.to_string(indent)

            else:
                # Otherwise, just use whatever pythonic repr we have.
                value_str = repr(value)

            result += "\n{}{:<7} {}".format(indent,
                                            key + ":",
                                            value_str)

        # The final result will neither begin nor end with its own
        # whitespace.
        return result

class SuperBox (AbstractBox):
    def define_multi_boxes (self):
        self.multi_boxes = set()

    def pull_box_data (self, length):
        self.define_multi_boxes()

        # Iterate through our boxes.
        for box in self.find_boxes(self.jp2.pos() + length):
            # Each box has a name.
            name    = box.name
            value   = globals()[self.box_mapping[name]](self.jp2, box)

            if name in self.multi_boxes:
                if name not in self.data:
                    self.data[name] = [ ]

                self.data[name].append(value)

            else:
                self.data[name] = value

    def find_boxes (self, max_pos):
        # We'll collect a list of boxes.
        boxes = [ ]

        while self.jp2.pos() < max_pos:
            # Get the next one.
            box = self.jp2.try_to_read_new_box()

            if box is None:
                # We shouldn't be at the end of file yet.
                self.jp2.read(1)

            # Add it to the list.
            boxes.append(box)

            if box.length is None:
                # If there's no length, we're done.
                break

        if self.jp2.pos() != max_pos:
            # We *must* be at the ending position.
            self.jp2.error(
                    "Should have completed box at {:08x}".format(
                            max_pos))

        # Cool! It worked!
        return boxes

class Jpeg2000 (SuperBox):
    def __init__ (self, file_object):
        # We'll initialize the file object, since this is our first time
        # looking at it.
        self.jp2    = BoxedFile(file_object)
        self.data   = OrderedDict()

        # Give a junk length that will ultimately be ignored.
        self.pull_box_data(0)

    def define_multi_boxes (self):
        self.multi_boxes = set(("xml ", "uuid", "uinf"))

    def find_boxes (self, max_pos):
        # We'll ignore the max_pos parameter, since, in this case, we're
        # reading to the end of the file. We'll also go ahead and start
        # at the zero offset.
        boxes = [ ]
        self.jp2.seek(0)

        while True:
            # Try to read a box.
            box = self.jp2.try_to_read_new_box()

            if box is not None:
                # If we succeeded, add the box.
                boxes.append(box)

                if box.length is not None:
                    # We only continue the loop (a) if we got a box and
                    # (b) if that box has a length.
                    continue

            # Otherwise, we exit the loop.
            break

        # Return the list.
        return boxes

class JP2SignatureBox (AbstractBox):
    pass

class FileTypeBox (AbstractBox):
    min_length  = 12

    def pull_box_data (self, length):
        self.assert_length_large_enough(length)

        # The brand is a four-byte string.
        self.data["Br"]     = self.jp2[4]

        # The minor version is a 4-byte integer.
        self.data["MV"]     = self.jp2.read_int(4)

        # Remaining entries are the compatibility list.
        compatibility_list  = [ ]
        for i in range(8, length - 3, 4):
            # Each group of four bytes is an entry.
            compatibility_list.append(self.jp2.read_int(4))

        # In a valid box, this will be zero, since each compatibility
        # list entry will be exactly four bytes long, and then the box
        # will be over.
        remaining_bytes     = length % 4

        if remaining_bytes > 0:
            # If it's an invalid box, go ahead and read the remaining
            # bytes. Why the heck not.
            compatibility_list.append(self.jp2[remaining_bytes])

        # Set it.
        self.data["CL"]     = compatibility_list

class JP2HeaderBox (SuperBox):
    pass

class ContiguousCodeStreamBox (AbstractBox):
    header_markers  = {
        b"\xff\x4f": "SOC",
        b"\xff\x51": "SIZ",
        b"\xff\x52": "COD",
        b"\xff\x5c": "QCD",
        b"\xff\x53": "COC",
        b"\xff\x5d": "QCC",
        b"\xff\x5e": "RGN",
        b"\xff\x5f": "POC",
        b"\xff\x60": "PPM",
        b"\xff\x57": "PLM",
        b"\xff\x55": "TLM",
        b"\xff\x63": "CRG",
        b"\xff\x64": "COM",
    }

    def pull_box_data (self, length):
        while True:
            marker = self.header_markers.get(self.jp2[2], None)

            if marker is None:
                break

            if marker == "SOC":
                self.data[marker] = True

            elif marker == "SIZ":


class IPRBox (AbstractBox):
    pass

class XMLBox (AbstractBox):
    pass

class UUIDBox (AbstractBox):
    def pull_box_data (self, length):
        if length <= 16:
            self.data["UUID"] = self.jp2[length]
            self.data["DATA"] = b""

        else:
            self.data["UUID"] = self.jp2[16]
            self.data["DATA"] = self.jp2[length - 16]

class UUIDInfoBox (SuperBox):
    pass

class BaseDiscreteIntsBox (AbstractBox):
    def pull_box_data (self, length):
        self.min_length = 0
        for key, size in ints:
            self.min_length += j

        self.assert_length_large_enough(length)

        for key, size in ints:
            self.data[key] = self.jp2.read_int(size)

        length -= self.min_length
        if length > 0:
            self.data["extra"] = self.jp2[length]

class ImageHeaderBox (BaseDiscreteIntsBox):
    ints = (
        ("H",   4),
        ("W",   4),
        ("C",   2),
        ("B",   1),
        ("CT",  1),
        ("UC",  1),
        ("IP",  1),
    )

class BitsPerComponentBox (AbstractBox):
    def pull_box_data (self, length):
        components = [ ]
        for i in range(length):
            components.append(self.jp2.read_int(1))

        self.data["B"] = components

class ColorSpecificationBox (AbstractBox):
    min_length  = 4
    def pull_box_data (self, length):
        self.assert_length_large_enough(length)

        for key in ("M", "P", "A"):
            self.data[key]  = self.jp2.read_int(1)

        length -= 3

        if self["M"] == 1:
            if length < 4:
                self.data["ECS"] = self.jp2.read_int(length)

            else:
                self.data["ECS"] = self.jp2.read_int(4)

                length -= 4
                if length > 0:
                    self.data["extra"] = self.jp2[length]

        elif self["M"] == 2:
            self.data["ICP"] = self.jp2[length]

        else:
            self.data["extra"] = self.jp2[length]

class PaletteBox (AbstractBox):
    def pull_box_data (self, length):
        ne              = self.jp2.read_int(2)
        nc              = self.jp2.read_int(1)

        self.min_length = 3 + nc + 2*(nc * ne)
        self.assert_length_large_enough(length)

        bit_depths      = [ ]
        for j in range(nc):
            bit_depths.append(self.jp2.read_int(1))

        parameters      = [ ]
        for i in range(ne):
            row         = [ ]
            for j in range(nc):
                row.append(self.jp2.read_int(2))

            parameters.append(row)

        self.data["NE"] = ne
        self.data["NC"] = nc
        self.data["B"]  = bit_depths
        self.data["P"]  = parameters

        length -= self.min_length
        if length > 0:
            self.data["extra"] = self.jp2[length]

class ComponentMappingBox (AbstractBox):
    ChannelMapTuple = namedtuple("ChannelMapTuple", ("c", "T", "j"))

    def pull_box_data (self, length):
        extra       = length % 4
        length     -= extra

        channels    = [ ]
        for i in range(length // 4):
            channels.append(self.ChannelMapTuple(
                    self.jp2.read_int(2),
                    self.jp2.read_int(1),
                    self.jp2.read_int(1)))

        self.data["channels"] = channels

        if extra > 0:
            self.data["extra"] = self.jp2[extra]

class ChannelDefinitionBox (AbstractBox):
    ChannelDefTuple = namedtuple("ChannelDefTuple", ("k", "Ty", "As"))

    def pull_box_data (self, length):
        m               = self.jp2.read_int(2)

        self.min_length = 2 * (1 + m)
        self.assert_length_large_enough(length)

        channels        = [ ]
        for i range(m):
            channels.append(self.ChannelDefTuple(
                    self.jp2.read_int(2),
                    self.jp2.read_int(2),
                    self.jp2.read_int(2)))

        self.data["M"]  = m
        self.data["channels"] = channels

        length -= self.min_length
        if length > 0:
            self.data["extra"] = self.jp2[length]

class ResolutionBox (SuperBox):
    pass

class BaseResolutionBox (BaseDiscreteIntsBox):
    ints = (
        ("RN1", 2),
        ("RD1", 2),
        ("RN2", 2),
        ("RD2", 2),
        ("RE1", 1),
        ("RE2", 1),
    )

    def vertical (self):
        return self.compute_res(1)
    def horizontal (self):
        return self.compute_res(2)

    def compute_res (self, number):
        numerator   = self["RN{:d}".format(number)]
        denominator = self["RD{:d}".format(number)]
        exponent    = self["RE{:d}".format(number)]

        if exponent > 0:
            numerator   *= 10 ** exponent

        elif exponent < 0:
            denominator *= 10 ** (-exponent)

        return Fraction(numerator, denominator)

class CaptureResolutionBox (BaseResolutionBox):
    pass

class DefaultDisplayResolutionBox (BaseResolutionBox):
    pass

class UUIDListBox (AbstractBox):
    pass

class DataEntryURLBox (AbstractBox):
    pass
