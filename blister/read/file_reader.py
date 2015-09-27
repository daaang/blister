# Copyright (c) 2015 The Regents of the University of Michigan.
# All Rights Reserved. Licensed according to the terms of the Revised
# BSD License. See LICENSE.txt for details.
from io             import  BytesIO, BufferedReader, SEEK_END
from sys            import  version_info

from ..exceptions   import  UnexpectedEOF

if version_info[0] > 2:
    file = BufferedReader

class FileReader:
    """File Reader

    This contains an 'rb'-mode file object. It can also just contain a
    string, if necessary. Regardless, it tracks byte offsets and other
    useful stuff.

    Args:
        file_object (BufferedReader):   The file we're reading. This can
                                        also be a bytes object.

    Examples:
        You're meant to hand it a file stream object (reading bytes; not
        strings).

        >>> stream      = open("path/to/file", "r")
        >>> reader      = FileReader(stream)
        Traceback (most recent call last):
          File "<stdin>", line 1, in <module>
            raise TypeError("Expected a file with mode 'rb'")
        TypeError: Expected a file with mode 'rb'
        >>> from_str    = FileReader("sup doggie")
        Traceback (most recent call last):
          File "<stdin>", line 1, in <module>
            raise TypeError("Expected a file with mode 'rb'")
        TypeError: Expected a file with mode 'rb'

        As you can see, it doesn't like inits based on str. It's meant
        to operate over bytes.

        >>> stream      = open("path/to/file", "rb")
        >>> reader      = FileReader(stream)
        >>> from_bytes  = FileReader(b"sup doggie")
        >>> from_bytes.pos()
        0
        >>> from_bytes

    """

    # By default, we're big endian.
    default_byte_order  = "big"

    def __init__ (self, file_object):
        if isinstance(file_object, bytes):
            # Allow bytestrings as input. Pretend it's a file.
            file_object     = BufferedReader(BytesIO(file_object))

        if not isinstance(file_object, BufferedReader)  and \
                (not isinstance(file_object, file)      or  \
                    file_object.mode != "rb"):
            # Assert that we have a file.
            raise TypeError("Expected a file with mode 'rb'")

        # Set our file and our byte order.
        self.internal_file  = file_object
        self.byte_order     = self.default_byte_order

    def __getitem__ (self, key):
        if isinstance(key, slice):
            # We've been given a slice.
            if key.step is not None:
                # I'm not gonna, like, read every other byte, or
                # whatever. That would be way 2bonx.
                raise KeyError("Didn't expect a step argument.")

            if key.start is not None:
                # If we have two values, we're to seek to the first.
                self.seek(key.start)

            # Either way, we read this many bytes.
            return self.read(key.stop)

        # If we've not been given a slice, we'll not need to seek
        # anywhere.
        return self.read(key)

    def tell (self):
        """Call tell() in the file"""
        return self.internal_file.tell()

    def pos (self):
        """Call tell() in the file"""
        return self.tell()

    def seek (self, pos):
        """Call seek() in the file"""
        self.internal_file.seek(pos)

    def read (self, length = None):
        """Read, asserting we don't pass the EOF"""
        if length is None:
            # We've not been given a length, so we only need to read to
            # the end of the file.
            return self.internal_file.read()

        # Otherwise, we read only as needed.
        result = self.internal_file.read(length)

        if len(result) != length:
            # We've tried to read past the end. Whoops!
            self.error(UnexpectedEOF)

        # yayyy
        return result

    def quick_read (self, length):
        """Read without asserting anything"""
        return self.internal_file.read(length)

    def bytes_to_int(self, bytestring):
        """Return an int using our internal byte order flag"""
        return int.from_bytes(bytestring, self.byte_order)

    def read_int (self, length):
        """Read an int from the file"""
        return self.bytes_to_int(self[length])

    def error (self, error_class, altered_position = 0, *args):
        """Shortcut to raising an exception based on this file offset"""

        if altered_position <= 0:
            pos = self.pos() + altered_position
        else:
            pos = altered_position

        raise error_class(pos, *args)

    def seek_from_end (self, bytes_before_end = 0):
        """Seek backwards from the end of the file stream"""
        self.internal_file.seek(-bytes_before_end, SEEK_END)
