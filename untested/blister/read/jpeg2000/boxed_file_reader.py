# Copyright (c) 2015 The Regents of the University of Michigan.
# All Rights Reserved. Licensed according to the terms of the Revised
# BSD License. See LICENSE.txt for details.
from collections    import  namedtuple

from ..file_reader  import  FileReader

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
        length  = self.quick_read(4)

        if len(length) == 0:
            # If we were already at the EOF, return expected failure.
            return None

        # The length should actually be an integer.
        length  = self.bytes_to_int(length)

        # Collect the name next.
        name    = self[4]

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
