class FileReader:
    """File Reader

    This contains an 'rb'-mode file object.

        >>> f = open("/path/to/file", "rb")
        >>> reader = FileReader(f)
    """

    default_byte_order  = "big"

    class ReadError (Exception):
        def __init__ (self, position, message):
            self.position   = position
            self.message    = message

        def __str__ (self):
            return "{} (0x{:08x})".format(str(self.message),
                                          self.position)

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
        if not isinstance(key, slice):
            key = slice(key)

        self.seek(key.start)
        return self.read(key.stop)

    def pos (self):
        return self.internal_file.tell()

    def seek (self, pos = None):
        if pos is not None:
            self.internal_file.seek(pos)

    def read (self, length = None):
        if length is None:
            return self.internal_file.read()

        result  = self.internal_file.read(length)

        if len(result) == length:
            return result

        self.error("Unexpected EOF")

    def quick_read (self, length):
        return self.internal_file.read(length)

    def bytes_to_int(self, bytestring):
        return bytes_to_int(bytestring, self.byte_order)

    def read_int (self, length):
        return self.bytes_to_int(self[length])

    def error (self, pos, message = None):
        if message is None:
            message = pos
            pos     = self.pos()

        elif pos < 0:
            pos    += self.pos()

        raise self.ReadError(pos, message)

    def seek_from_end (self, bytes_before_end = 0):
        self.internal_file.seek(-bytes_before_end, SEEK_END)
