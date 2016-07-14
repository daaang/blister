# Copyright (c) 2015 The Regents of the University of Michigan.
# All Rights Reserved. Licensed according to the terms of the Revised
# BSD License. See LICENSE.txt for details.
from collections    import  namedtuple, Mapping, deque
from fractions      import  Fraction

from ...exceptions  import  Jpeg2000DuplicateKey,           \
                            Jpeg2000CodeStreamError,        \
                            Jpeg2000NoSOCMarker,            \
                            Jpeg2000NoSIZMarker,            \
                            Jpeg2000UnknownSubBlock,        \
                            Jpeg2000SIZIncorrectLength,     \
                            Jpeg2000SIZParameterTooSmall,   \
                            Jpeg2000SIZParameterTooLarge

class HeaderMarker:
    # Required main header markers and marker segments.
    SOC = b"\xff\x4f"   # Start of code-stream
    SIZ = b"\xff\x51"   # Image and tile size
    COD = b"\xff\x52"   # Coding style default
    QCD = b"\xff\x5c"   # Quantization default

    # Optional main header markers and marker segments.
    COC = b"\xff\x53"   # Coding style component
    QCC = b"\xff\x5d"   # Quantization component
    RGN = b"\xff\x5e"   # Region of interest
    POC = b"\xff\x5f"   # Progression order change
    PPM = b"\xff\x60"   # Packed packet headers: main header
    PLM = b"\xff\x57"   # Packet lengths: main header
    TLM = b"\xff\x55"   # Tile-part lengths: main header
    CRG = b"\xff\x63"   # Component registration
    COM = b"\xff\x64"   # Comment

    # Required tile header markers and marker segments.
    SOT = b"\xff\x90"   # Start of tile
    SOD = b"\xff\x93"   # Start of data

    # Optional tile header markers and marker segments.
    PPT = b"\xff\x61"   # Packed packet headers: tile-part
    PLT = b"\xff\x58"   # Packed lengths: tile-part

    # Tile-part header markers and marker segments.
    SOP = b"\xff\x91"   # Start of packet
    EPH = b"\xff\x92"   # End of packet header

    # This doesn't appear until the very end.
    EOC = b"\xff\xd9"   # End of code-stream

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
        self.insert(b"value", self.jp2[length])

    def __getitem__ (self, key):
        """Get value from internal dict"""
        if key not in self.data and isinstance(key, str):
            # If we don't have this key, then maybe the user
            # accidentally asked for a string when it should actually be
            # bytes. We encode the string with latin1 for the most
            # faithful character-by-character reproduction of the
            # requested string.
            return self.data[key.encode("latin1")]

        # Otherwise, either we've found it, or the user requested a key
        # of some type that I'm not about to make exceptions for.
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
        for key, value in self.items():
            pairs.append("{}={}".format(repr(key), repr(value)))

        return "<{} {}>".format(self.__class__.__name__,
                                ", ".join(pairs))

    def __str__ (self):
        # Just go on ahead, starting with no indent.
        return self.to_string()

    def initialize_data (self):
        # We track the data itself as well as the order it appears.
        self.data   = { }
        self.order  = deque()

        for name in self.multiple:
            # Prepare for multiple counts of anything in the multiple
            # set.
            self.data[name] = [ ]

    def insert (self, key, value):
        if key in self.multiple:
            # This one may have already appeared. Either way, it's a
            # list that we can append to.
            self.order.append((key, len(self.data[key])))
            self.data[key].append(value)

        elif key in self.data:
            # This one should not have already appeared, but it has. So
            # we error on out.
            self.jp2.error(Jpeg2000DuplicateKey, 0, repr(key))

        else:
            # This one can only appear once, and it has! So far.
            self.order.append((key, None))
            self.data[key] = value

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
    def pull_box_data (self, length):
        # Iterate through our boxes.
        for box in self.find_boxes(self.jp2.pos() + length):
            # Each box has a name.
            name        = box.name
            box_class   = globals()[self.box_mapping[name]]
            value       = box_class(self.jp2, box)

            self.insert(name, value)

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

class JP2SignatureBox (AbstractBox):
    pass

class FileTypeBox (AbstractBox):
    min_length  = 12

    def pull_box_data (self, length):
        self.assert_length_large_enough(length)

        # The brand is a four-byte string.
        self.insert(b"Br", self.jp2[4])

        # The minor version is a 4-byte integer.
        self.insert(b"MV", self.jp2.read_int(4))

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
        self.insert(b"CL", compatibility_list)

class JP2HeaderBox (SuperBox):
    pass

class ContiguousCodeStreamBox (AbstractBox):
    blocks  = {
        HeaderMarker.SIZ:   (
            ("Lsiz",    2),
            ("CA",      2),
            ("F2",      4),
            ("F1",      4),
            ("E2",      4),
            ("E1",      4),
            ("T2",      4),
            ("T1",      4),
            ("OmegaT2", 4),
            ("OmegaT1", 4),
            ("C",       2),
            ("Clist",   (("B",  1),
                         ("S2", 1),
                         ("S1", 1))),
        ),
    }

    def pull_box_data (self, length):
        # Track our starting position.
        pos     = self.jp2.pos()

        if self.jp2[2] != HeaderMarker.SOC:
            # The first two bytes should be the SOC marker.
            self.jp2.error(Jpeg2000NoSOCMarker, -2)

        if self.jp2[2] != HeaderMarker.SIZ:
            # The next two bytes should be the SIZ marker.
            self.jp2.error(Jpeg2000NoSIZMarker, -2)

        self.insert(b"SIZ", self.pull_block(HeaderMarker.SIZ))

    def pull_block (self, block_code):
        # We'll be returning a dictionary.
        result  = { }

        # There could be some variable-length sub-blocks. Track them
        # with this. We should also track the number of bytes read so
        # far.
        bytes_read      = 0

        for name, bytecount in self.blocks[block_code]:
            if isinstance(bytecount, int):
                # If we have an integral bytecount, read that many
                # bytes.
                result[name]    = self.jp2.read_int(bytecount)
                bytes_read     += bytecount

            else:
                # Otherwise, we have a sub-block segment that could
                # repeat any number of times. Get that number of times.
                sub_block_range = self.get_sub_block_range(block_code,
                                                           name,
                                                           result,
                                                           bytes_read)

                # The value will be in the form of a list of
                # dictionaries. Here's the list.
                var_length_list = [ ]

                for junk in range(sub_block_range):
                    # And here's one of the dictionaries in the list.
                    sub_block   = { }

                    # Remember that, in this special case, the bytecount
                    # is not a bytecount but is instead an iterable of
                    # 2-tuples.
                    for sub_name, sub_bytecount in bytecount:
                        # Set the value for this particular sub-dict.
                        sub_block[sub_name] = self.jp2.read_int(
                                                    sub_bytecount)
                        bytes_read         += sub_bytecount

                    # Add the sub-dict to the list.
                    var_length_list.append(sub_block)

                # Finally, set the list as our value.
                result[name]    = var_length_list

        # Be sure the data we've collected looks exactly as expected.
        self.validate_block(block_code, result, bytes_read)

        return result

    def get_sub_block_range (self,
                             block_code,
                             name,
                             result,
                             bytes_read):
        if block_code == HeaderMarker.SIZ:
            if name == "Clist":
                return result["C"]

        # If we haven't returned anything by now, then we've been given
        # an unrecognized sub-block.
        self.jp2.error(Jpeg2000UnknownSubBlock, 0,
                       repr(block_code), repr(name))

    def validate_block (self, block_code, block_dict, bytes_read):
        if block_code == HeaderMarker.SIZ:
            # Be sure our block length is as expected.
            if block_dict["Lsiz"] != bytes_read:
                self.jp2.error(Jpeg2000SIZIncorrectLength, -bytes_read,
                               block_dict["Lsiz"], bytes_read)

            for vmin, vmax, key_list in ((0, 2**32-1, ("E1", "E2",
                                                       "OmegaT1",
                                                       "OmegaT2")),
                                         (1, 2**32,   ("F1", "F2",
                                                       "T1", "T2"))):
                for key in key_list:
                    if block_dict[key] < vmin:
                        self.jp2.error(Jpeg2000SIZParameterTooSmall,
                                       -bytes_read, key, vmin,
                                       block_dict[key])

                    if block_dict[key] >= vmax:
                        self.jp2.error(Jpeg2000SIZParameterTooLarge,
                                       -bytes_read, key, vmax,
                                       block_dict[key])

class IPRBox (AbstractBox):
    pass

class XMLBox (AbstractBox):
    pass

class UUIDBox (AbstractBox):
    def pull_box_data (self, length):
        if length <= 16:
            self.insert(b"UUID", self.jp2[length])
            self.insert(b"DATA", b"")

        else:
            self.insert(b"UUID", self.jp2[16])
            self.insert(b"DATA", self.jp2[length - 16])

class UUIDInfoBox (SuperBox):
    pass

class BaseDiscreteIntsBox (AbstractBox):
    def pull_box_data (self, length):
        self.min_length = 0
        for key, size in self.ints:
            self.min_length += size

        self.assert_length_large_enough(length)

        for key, size in self.ints:
            self.insert(key, self.jp2.read_int(size))

        length -= self.min_length
        if length > 0:
            self.insert(b"extra", self.jp2[length])

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

        self.insert(b"B", components)

class ColorSpecificationBox (AbstractBox):
    min_length  = 4
    def pull_box_data (self, length):
        self.assert_length_large_enough(length)

        for key in ("M", "P", "A"):
            self.insert(key, self.jp2.read_int(1))

        length -= 3

        if self["M"] == 1:
            if length < 4:
                self.insert(b"ECS", self.jp2.read_int(length))

            else:
                self.insert(b"ECS", self.jp2.read_int(4))

                length -= 4
                if length > 0:
                    self.insert(b"extra", self.jp2[length])

        elif self["M"] == 2:
            self.insert(b"ICP", self.jp2[length])

        else:
            self.insert(b"extra", self.jp2[length])

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

        self.insert(b"NE", ne)
        self.insert(b"NC", nc)
        self.insert(b"B", bit_depths)
        self.insert(b"P", parameters)

        length -= self.min_length
        if length > 0:
            self.insert(b"extra", self.jp2[length])

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

        self.insert(b"channels", channels)

        if extra > 0:
            self.insert(b"extra", self.jp2[extra])

class ChannelDefinitionBox (AbstractBox):
    ChannelDefTuple = namedtuple("ChannelDefTuple", ("k", "Ty", "As"))

    def pull_box_data (self, length):
        m               = self.jp2.read_int(2)

        self.min_length = 2 * (1 + m)
        self.assert_length_large_enough(length)

        channels        = [ ]
        for i in range(m):
            channels.append(self.ChannelDefTuple(
                    self.jp2.read_int(2),
                    self.jp2.read_int(2),
                    self.jp2.read_int(2)))

        self.insert(b"M", m)
        self.insert(b"channels", channels)

        length -= self.min_length
        if length > 0:
            self.insert(b"extra", self.jp2[length])

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
