# Copyright (c) 2015 The Regents of the University of Michigan.
# All Rights Reserved. Licensed according to the terms of the Revised
# BSD License. See LICENSE.txt for details.
from collections    import  namedtuple, deque, OrderedDict, Sequence, \
                            Hashable, Mapping, MutableSequence
from fractions      import  Fraction
from re             import  compile as re_compile

from ...internal    import  deflatten
from ..file_reader  import  FileReader
from .filters       import  decode_ASCIIHex, decode_ASCII85,    \
                            decode_Flate

def safe_decode (bytestring):
    """Decode bytes into a unicode string"""
    try:
        # Always start by trying to decode using UTF-8. Ideally,
        # everything I get will be encoded with that.
        return bytestring.decode("utf_8")

    except UnicodeDecodeError:
        try:
            # If it's not valid UTF-8, it could be that old pesky
            # MICROS~1 codepage 1252. Give that a whirl, just in case.
            return bytestring.decode("cp1252")

        except UnicodeDecodeError:
            # Failing that, just leave it encoded.
            return bytestring.decode("latin_1")

class PdfHex:
    """PDF Hex String"""
    def __init__ (self, hexstring):
        """Takes one argument: the string"""
        # I want to track whether we have an even-length hex string.
        self.is_even = (len(hexstring) % 2 == 0)

        if self.is_even:
            # If it's even, then cool, I can just convert it.
            self.string = bytes.fromhex(hexstring.decode("ascii"))

        else:
            # If not, I'll need to add a `0` byte before converting it.
            self.string = bytes.fromhex(hexstring.decode("ascii") + "0")

    def __bytes__ (self):
        """Get the bytes"""
        return self.string

    def __repr__ (self):
        """Represent the hex string"""
        return "<{} {}>".format(self.__class__.__name__,
                                repr(self.string))

class PdfName (Hashable):
    """PDF Name"""

    # Use this to find any `#`-escaped bytes.
    re_hashtag  = re_compile(rb"#([0-9a-fA-F]{2})")

    def __init__ (self, name_bytes):
        """Takes one argumet: the string of bytes following the vergule
        in the PDF content stream"""

        if isinstance(name_bytes, str):
            self.name       = name_bytes
            self.utf8       = True

            self.original   = None

        else:
            # Follow each hashtag escape to get a new, more accurate
            # string of bytes.
            escaped         = self.re_hashtag.sub(self.hashtag_repl,
                                                  name_bytes)

            try:
                # Try to decode using UTF-8.
                self.name   = escaped.decode("utf_8")
                self.utf8   = True

            except UnicodeDecodeError:
                # If we can't, we'll decode using some other
                # possibilities, but we'll also make a note that this is
                # not UTF-8.
                self.name   = safe_decode(escaped)
                self.utf8   = False

            # Also track the original bytes in case anyone wants to see
            # them.
            self.original   = name_bytes

    def __str__ (self):
        """Convert to unicode"""
        return self.name

    def __eq__ (self, other):
        return str(self) == str(other)
    def __ne__ (self, other):
        return str(self) != str(other)

    def __hash__ (self):
        """Hashed on the name itself"""
        return hash("/" + str(self))

    def __repr__ (self):
        """Python representation"""
        return "<{} {}>".format(self.__class__.__name__,
                                repr(str(self)))

    def hashtag_repl (self, match):
        """Replace `#XX` with a single byte"""
        return bytes.fromhex(match.group(1))

class PdfDictType:
    ObjStm      = PdfName("ObjStm")
    XRef        = PdfName("XRef")

class PdfDict (Mapping):
    """PDF Dictionary"""
    def __init__ (self):
        """No initialization arguments"""
        # I want a dictionary of lists and a list of key orders.
        self.internal_dict  = { }
        self.insert_order   = [ ]

    def __getitem__ (self, key):
        """Get the list of values found so far for this key"""
        # Just return the list of values associated with the key.
        return self.internal_dict.get(key, [ ])

    def __setitem__ (self, key, value):
        """Add a new value to this key's list"""
        if key in self.internal_dict:
            # The key's already in the dict. Grab its current list of
            # values.
            keylist = self.internal_dict[key]

            # Add this new value to the insertion order along with its
            # index-to-be.
            self.insert_order.append((key, len(keylist)))

            # Append it to the key's value list.
            keylist.append(value)

        else:
            # This is the first time we're setting this key. Ideally,
            # it's the only time! But, just in case, put it in a list.
            self.insert_order.append((key, 0))
            self.internal_dict[key] = [value]

    def __iter__ (self):
        """Iterate over the keys"""
        return self.keys()

    def __len__ (self):
        """Get the count of keys"""
        return len(self.internal_dict)

    def __contains__ (self, key):
        """Test whether we've seen this key"""
        return key in self.internal_dict

    def keys (self):
        """Iterate over keys in order of first insertion"""
        for key, index in self.insert_order:
            if index == 0:
                yield key

    def items (self):
        """Iterate over keys and values in order of insertion (may yield
        duplicate keys)"""
        for key, index in self.insert_order:
            yield (key, self.internal_dict[key][index])

    def values (self):
        """Iterate over values in order of insertion"""
        for key, index in self.insert_order:
            yield self.internal_dict[key][index]

    def get_python_dict (self):
        """Return a simple dict"""
        result = { }

        for key, values in self.internal_dict.items():
            # How many values are associated with this key?
            if len(values) == 1 and \
                    values[0] is not PdfObjectFactory.EndDelimiter:
                # If it's just one, then we'll use it.
                value   = values[0]

            else:
                # Otherwise, we're supposed to use null.
                value   = None

            if isinstance(key, PdfName):
                # If we have an honest-to-god name, then it should
                # override any other nonsense (if there is any).
                result[str(key)] = value
                continue

            if isinstance(key, bytes):
                # If we have a bytestring, then we should decode it to
                # unicode.
                strkey  = safe_decode(key)

            else:
                # Otherwise, cross your fingers and convert to string.
                strkey  = "{}".format(key)

            if strkey not in result:
                # I only actually add it if I'm not overwriting
                # anything. I don't want to deal with that.
                result[strkey] = value

        return result

    def __repr__ (self):
        pairs = [ ]
        for key, value in self.items():
            pairs.append("{}: {}".format(repr(key), repr(value)))

        return "<{} {{{}}}>".format(self.__class__.__name__,
                                    ", ".join(pairs))

class PdfToken (Hashable):
    """PDF Token"""
    def __init__ (self, bytestring):
        """Take in a string of regular bytes"""
        self.token  = bytes(bytestring)

    def __hash__ (self):
        return hash(self.token)

    def __bytes__ (self):
        """This is already little more than a bytes object"""
        return self.token

    def __eq__ (self, other):
        if not isinstance(other, self.__class__):
            return False

        return bytes(self) == bytes(other)

    def __ne__ (self, other):
        if not isinstance(other, self.__class__):
            return True

        return bytes(self) != bytes(other)

    def __repr__ (self):
        """Represent the token"""
        return "<{} {}>".format(self.__class__.__name__,
                                repr(self.token))

PdfObjectReference  = namedtuple("PdfObjectReference",
                                 ("number", "generation"))

class PdfIndirectObject:
    def __init__ (self, token_stack):
        if len(token_stack) != 4:
            raise Exception("Indirect objects should contain 4 tokens.")

        # Get all the information an indirect object can have about
        # itself.
        self.object_key = PdfObjectReference(token_stack.popleft(),
                                             token_stack.popleft())
        obj_token       = token_stack.popleft()
        self.value      = token_stack.popleft()

        if obj_token != PdfToken(b"obj"):
            # Be sure it's a valid indirect object.
            raise Exception("The third token should be obj.")

class PdfStream (PdfIndirectObject):
    decodable_filters   = {
        PdfName("ASCIIHexDecode"):  decode_ASCIIHex,
        PdfName("ASCII85Decode"):   decode_ASCII85,
        PdfName("FlateDecode"):     decode_Flate,
    }

    def __init__ (self, token_stack, offset):
        # Do all the normal checking and inserting for indirect objects.
        super(PdfStream, self).__init__(token_stack)

        # Also add our offset.
        self.stream_offset  = offset

        # By default, our data and filters are set to null. We don't
        # necessarily even have access to stream length information
        # right now, so we'll have to be patient and wait for someone
        # else to pull that.
        self.data           = None
        self.filters        = None

    def decode_stream_data (self, length, file_object):
        if self.data is None and self.filters is None:
            # If we haven't yet tried decoding anything, we start by
            # looking at filters.
            filters = self.value.get("Filter", [ ])
            parms   = self.value.get("DecodeParms", None)

            if not isinstance(filters, list):
                # Be sure we have a list of filters, even if there's
                # just one (just to make for consistent code).
                filters = [filters]

            if parms is None:
                parms   = [{}] * len(filters)

            if not isinstance(parms, list):
                assert len(filters) == 1
                parms   = [parms]

            for fname in filters:
                # Check each filter in the list.
                if fname not in self.decodable_filters:
                    # If it's not a filter we're equipped to handle,
                    # store the list.
                    self.filters = filters
                    self.parms   = parms

                    # We're done. No need to even look at the file.
                    return

            # OK! We can decode this stream, so let's get going. Seek to
            # wherever it starts and then read whatever's there.
            file_object.seek(self.stream_offset)
            data = file_object.read(length)

            i = 0
            for fname in filters:
                # Decode the data according to each filter.
                data = self.decodable_filters[fname](data, parms[i])
                i += 1

            # Set the data and leave the filter list null.
            self.data       = data

class PdfObjectFactory:
    """PDF Object Parser

    This should be initialized with a FileReader object holding the pdf
    file stream.

        >>> factory = PdfObjectFactory(pdf_file)
        >>> factory
        <PdfObjectFactory 00000000>

    Objects can then be read.

        >>> factory.read()
        15
        >>> factory.read()
        0
        >>> factory.read()
        <PdfToken obj>
        >>> factory.read()
        <PdfDict {<PdfName 'Linearized'>:   1,
                  <PdfName 'L'>:            4358971,
                  <PdfName 'O'>:            17,
                  <PdfName 'E'>:            351494,
                  <PdfName 'N'>:            3,
                  <PdfName 'T'>:            4358556,
                  <PdfName 'H'>:            [536, 193]}>
        >>> factory.read()
        <PdfToken endobj>
        >>> factory
        <PdfObjectFactory 00000064>

    If you plan on seeking to different places in the file stream, be
    sure you do it through this instance, as doing so externally could
    break things.

        >>> # We'll seek to the T value in the linearization dictionary.
        ... factory.seek(4358556)
        b'\r'
        >>> # Our position has been updated.
        ... factory
        <PdfObjectFactory 0042819c>
        >>> # This is the beginning of the first xref table.
        ... factory.read()
        0
        >>> factory.read()
        65535
        >>> factory.read()
        <PdfToken f>
        >>> factory.read()
        351494
        >>> factory.read()
        0
        >>> factory.read()
        <PdfToken n>
    """

    # Without assigning meaning just yet, these are the accepted PDF
    # whitespace characters.
    whitespace      = set(b"\0\t\n\f\r ")

    # These are the PDF delimiters.
    delimiters      = set(b"()<>[]{}%/")

    # All 8-bit characters other than whitespace and delimiters are
    # considered in PDFs to be "regular" characters. In other words
    irregular       = whitespace | delimiters

    # CR, LF, and EOL all represent stopping points.
    endings         = set(b"\r\n")

    # Be sure we aren't treating EOF as a regular byte.
    irregular.add(None)
    endings.add(None)

    # Here are some meaningful names for specific, meaningful bytes.
    eol_lf,             \
        eol_cr,         \
        delim_comment,  \
        delim_name,     \
        delim_array,    \
        delim_string,   \
        delim_angle,    \
        backslash,      \
        zero        = b"\n\r%/[(<\\0"

    # These all come in pairs.
    delim_pairs     = {
        b"("[0]: b")"[0],
        b"<"[0]: b">"[0],
        b"["[0]: b"]"[0],
        b"{"[0]: b"}"[0],
    }

    # These objects are presented as values rather than operators.
    known_values    = {
        b"null":    None,
        b"true":    True,
        b"false":   False,
    }

    # String literals escape characters with backslashes. These are the
    # simple cases. Left out are EOL sequences and octals, which require
    # somewhat more-specialized handling.
    string_escapes  = {
        b"n"[0]:  b"\n"[0],
        b"r"[0]:  b"\r"[0],
        b"t"[0]:  b"\t"[0],
        b"b"[0]:  b"\b"[0],
        b"f"[0]:  b"\f"[0],
        b"\\"[0]: b"\\"[0],
        b"("[0]:  b"("[0],
        b")"[0]:  b")"[0],
    }

    # Integers are one or more decimal digits optionally preceded by a
    # sign symbol.
    re_integer      = re_compile(rb"^[-+]?[0-9]+$")

    # Real numbers are a dot with one or more decimal digits on one side
    # and zero or more on the other. Like an integer, it is also
    # optionally preceded by a sign symbol.
    re_real         = re_compile(rb"^[-+]?(?:\.[0-9]+|[0-9]+\.[0-9]*)$")

    # These only come into play when we're iterating through some larger
    # PDF container object. Id est, this never comes into play over the
    # course of a regular `read` operation; rather, it comes into play
    # during recursive calls to `read` (specifically via `iter_read`).
    expected_tokens = {
        # Really the only token I can think of that I might come across
        # in the middle of stuff is an object reference. So here's that.
        b"R":   (2, PdfObjectReference),
    }

    # In the PDF spec, the last line of the PDF should simply be
    # `%%EOF`, but implementation note 18 (appendix H) goes on to say
    # that Acrobat Reader allows it to exist anywhere in the last 1024
    # bytes of the file. Therefore I should also allow it to exist
    # anywhere in the last 1024 bytes of the file.
    eof_marker_buffer   = 0x400

    class EndDelimiter:
        pass

    def __init__ (self, pdf_file):
        if isinstance(pdf_file, FileReader):
            # We want a FileReader object, and that's what we have!
            self.pdf    = pdf_file

        else:
            # We want a FileReader object, and that's what we'll get!
            self.pdf    = FileReader(pdf_file)

        # We also want to track our position and current character
        # separately.
        self.pos    = self.pdf.pos()
        self.byte   = self.pdf[1][0]

    def read (self, end_delimiter = False):
        """Read the next object from the content stream

        Return values:

        1.  Static values:

            -   PdfObjectFactory.EndDelimiter is a result that confirms that
                we've found the delimiter that you asked to look for (if you
                asked for one at all). If you set it to None, then this
                signifies the end of the content stream.

            -   None means `null` was found.

            -   True means `true` was found.

            -   False means `false` was found.

        2.  If the result is an int, then we found an integer (i.e. a
            number without a decimal point).

        3.  If the result is a Fraction, then we found a number with a
            decimal point.

        4.  If the result is a PdfToken, then we found some other series
            of regular (i.e. nondelimiter nonwhitespace) characters not
            mentioned above.

        5.  If the result is a PdfName, then we found a token prefixed
            by a `/` character.

        6.  If the result is a list, then we found an array. The values
            in the list will conform recursively to all these rules.

        7.  If the result is a dict, then we found a dictionary. The
            entities in the dictionary will conform recursively to all
            these rules.

        8.  If the result is a PdfHex, the we found a string contained
            in angle brackets (rather than a typical string contained in
            parentheses).

        9.  If the result is a bytes object, then we found a regular
            string contained in parentheses.
        """

        while True:
            # This loop ends by raising an exception. Any continuations
            # and breaks are explicit

            if self.byte == end_delimiter:
                # If this byte is the ending delimiter, then return this
                # special value to signal the end.
                self.step()
                return self.EndDelimiter

            if self.byte is None:
                # I should only be reaching the EOF if I'm looking for
                # it. Were that the case, the end_delimiter would have
                # been set to None. But it's not! So this is a surprise.
                # Attempting to read like this will result in an error.
                self.hardstep()

            if self.byte in self.whitespace:
                # Ignore whitespace.
                self.step()
                continue

            if self.byte == self.delim_comment:
                # This begins a comment.
                while self.step() not in self.endings:
                    # Loop on forward until we reach an EOL (or EOF).
                    pass

                # We've ignored the comment. Time to start paying
                # attention again.
                continue

            if self.byte not in self.irregular:
                # It's a regular character. That means we're reading a
                # token.
                bytelist = [self.byte]

                while self.step() not in self.irregular:
                    # Keep reading until we've read every regular
                    # character.
                    bytelist.append(self.byte)

                # Convert the list of bytes to what it really is.
                token = bytes(bytelist)

                if token in self.known_values:
                    # This is a static value.
                    return self.known_values[token]

                if self.re_integer.match(token) is not None:
                    # This is an integer.
                    return int(token)

                if self.re_real.match(token) is not None:
                    # This is a real number.
                    return Fraction(token.decode("ascii"))

                # This is some other kind of token, beyond the scope of
                # this function.
                return PdfToken(token)

            if self.byte == self.delim_name:
                # Collect all regular bytes following the delimiter.
                bytelist = [ ]

                while self.step() not in self.irregular:
                    # This one is regular.
                    bytelist.append(self.byte)

                # And we finish up pointing at the next byte, as we
                # should.
                return PdfName(bytes(bytelist))

            if self.byte == self.delim_array:
                # It's an array! Move forward to look at the first thing
                # in it, and then list-ify everything up through the
                # ending delimiter.
                end_byte = self.delim_pairs[self.byte]
                self.step()
                return list(self.iter_read(end_byte))

            if self.byte == self.delim_angle:
                # We don't yet know whether this is a hex string or a
                # mapping, but we do know what the closing delimiter
                # will be.
                end_byte    = self.delim_pairs[self.byte]

                if self.hardstep() == self.delim_angle:
                    # This is a mapping! We'll wrap it in a PdfDict
                    # instance and step forward to start looking.
                    mapping     = PdfDict()
                    self.step()

                    for key, value in deflatten(2,
                            self.iter_read(end_byte),
                            self.EndDelimiter):
                        # We iterate through all objects, in pairs,
                        # before the end delimiter. If there's an odd
                        # number for some reason, we'll set the missing
                        # value to EndDelimiter as a message to whoever
                        # will see the mapping.
                        mapping[key] = value

                    if self.byte != end_byte:
                        # Be sure we have a double-bracket close.
                        raise Exception("Expected '>>', not '>'")

                    self.step()
                    return mapping.get_python_dict()

                else:
                    # The second byte doesn't match the first, so this
                    # is not a mapping. The only other thing it can be
                    # is a hex-string.
                    if self.byte == end_byte:
                        # If this string is empty, then that's fine.
                        # We're already done.
                        return PdfHex(b"")

                    if self.byte in self.whitespace:
                        # If this byte is whitespace, we can ignore it.
                        # We'll just initialize our byte list.
                        hex_list = [ ]

                    else:
                        # Otherwise, we'll initialize the list with this
                        # byte in it.
                        hex_list = [self.byte]

                    while self.hardstep() != end_byte:
                        # Keep reading until the end delimiter.
                        if self.byte not in self.whitespace:
                            # Only record nonwhitespace bytes.
                            hex_list.append(self.byte)

                    # We're currently looking at that last bracket, so
                    # step forward.
                    self.step()

                    # Construct a PdfHex object.
                    return PdfHex(bytes(hex_list))

            if self.byte == self.delim_string:
                # This is a string literal. Prepare the end byte.
                end_byte    = self.delim_pairs[self.byte]

                # We start with a parenthesis depth of 1, since we've
                # just opened one.
                paren_depth = 1

                # This list will become a byte array.
                result      = bytearray()

                while True:
                    # Look at each character, one at a time.
                    self.hardstep()

                    if self.byte == self.backslash:
                        # If it's a backslash, we'll look at the next
                        # character.
                        self.hardstep()

                        if self.byte in self.string_escapes:
                            # These are the simple string escapes.
                            result.append(self.byte)

                        elif self.byte == self.eol_lf:
                            # Escaped line feeds are ignored.
                            pass

                        elif self.byte == self.eol_cr:
                            # Escaped carriage returns are ignored.
                            # However, so are CRLF endings, so we'll
                            # want to ignore the next byte too, if it's
                            # a line feed.
                            if self.hardstep() != self.eol_lf:
                                # Whoops! It isn't. Go back.
                                self.backstep()

                        else:
                            # Get the stated value of the byte.
                            value = self.byte - self.zero

                            if value < 0 or value >= 8:
                                # This isn't an octal, so this isn't a
                                # valid escape at all. We backtrack so
                                # as to ignore the backslash completely.
                                self.backstep()
                                continue

                            # Otherwise, we have an octal with at least
                            # one digit. There could be up to two more
                            # digits.
                            for i in range(2):
                                # Get the would-be value for the next
                                # digit.
                                next_digit = self.hardstep() - self.zero

                                if next_digit < 0 or next_digit >= 8:
                                    # OK, so this one isn't a digit. Go
                                    # back and stop looking.
                                    self.backstep()
                                    break

                                # It is another digit! Add it to the
                                # value.
                                value *= 8
                                value += next_digit

                            # Add the octal value.
                            result.append(value)

                        # We know we haven't affected the parenthesis
                        # depth, and we've already added everything we
                        # want to add to the result.
                        continue

                    if self.byte == self.delim_string:
                        # Open parentheses increase the depth.
                        paren_depth += 1

                    elif self.byte == end_byte:
                        # Close parentheses decrease the depth.
                        paren_depth -= 1

                        if paren_depth < 1:
                            # It's possible that we're done. If we are,
                            # we don't actually add the final
                            # parenthesis.
                            break

                    # Just add the byte.
                    result.append(self.byte)

                # Step forward, since we're currently looking at that
                # last parenthesis.
                self.step()

                # We return the string of bytes.
                return bytes(result)

            # This is only possible with one of the following five
            # bytes: ')', '>', ']', '{', '}'
            #
            # Everything else is handled. These five are delimiters that
            # don't delimit anything. Error out.
            raise Exception(-1, "Unexpected {} byte".format(
                                                repr(chr(self.byte))))

    def iter_read (self, end_delimiter):
        """
        Keep reading until the end delimiter is found; return an
        iterator.
        """
        # We'll actually pull out an entire stack first, so initialize
        # that stack.
        stack   = deque()

        # Go ahead and read in the first object.
        obj     = self.read(end_delimiter)

        while obj is not self.EndDelimiter:
            # We'll look at each object that isn't the end delimiter.
            if isinstance(obj, PdfToken):
                try:
                    # This is a token. See if we can make it into
                    # something better. If we can, we'll make a new
                    # deque just to hold arguments.
                    size, pdf_tuple = self.expected_tokens[bytes(obj)]
                    argstack        = deque()

                    for i in range(size):
                        # Pop items from the previously-seen stack and
                        # into our arguments.
                        argstack.appendleft(stack.pop())

                    # Recreate this object to contain those arguments as
                    # part of itself.
                    obj = pdf_tuple(*tuple(argstack))

                except KeyError:
                    # This is a token, and it isn't one we recognize.
                    # That's totally fine. It's fine. We're good.
                    pass

            # Whatever just happened here, append it to our stack.
            stack.append(obj)
            obj = self.read(end_delimiter)

        # All that's left is to iterate through the stack.
        return iter(stack)

    def step (self):
        """Move forward in the file by one byte"""
        if self.byte is not None:
            # If the current byte is None, then we're already at the end
            # of the file, so there'd be nothing to do. Otherwise, we
            # increment our positional pointer and get the next byte.
            self.pos   += 1
            self.step_helper()

        return self.byte

    def hardstep (self):
        """Move forward in the file by one byte and assert no EOF"""
        # No conditionals are needed; we just plow forward.
        self.byte   = self.pdf[1][0]
        self.pos   += 1

        return self.byte

    def seek (self, pos):
        """Seek to a specific point in the file"""
        # Set the position, seek there, and peek at the character.
        self.pos    = pos
        self.pdf.seek(pos)
        self.step_helper()

        return self.byte

    def backstep (self, steps_back = 1):
        """Take a step backwards"""
        # Seek in reverse, relatively.
        return self.seek(self.pos - steps_back)

    def step_helper (self):
        """Read the current byte"""
        # Assume our position is correct and that all we need to do is
        # read forward once.
        bytestring  = self.pdf.quick_read(1)

        if len(bytestring) == 0:
            # If we didn't read anything, we must be at the end of the
            # file, which we represent as None.
            self.byte   = None

        else:
            # Otherwise, grab the byte value.
            self.byte   = bytestring[0]

    def read_indirect_object (self, *already_read):
        # We'll be using a queue.
        token_stack = deque()

        for token in already_read:
            # Loop through any values we've already found outside of
            # this particular function.
            if isinstance(token, PdfToken):
                # If we find a token, take a closer look.
                token_bytes = bytes(token)

                if token_bytes == b"endobj":
                    # If we reach the end of the object, we have a basic
                    # indirect object on our hands.
                    return PdfIndirectObject(token_stack)

                if token_bytes == b"stream":
                    # Otherwise, if we reach the beginning of a stream,
                    # then there will be more work to do. But later.
                    return self.return_stream(token_stack)

            # If we aren't done, we can just push this token onto our
            # queue.
            token_stack.append(token)

        while len(token_stack) < 5:
            # Cool. We're done with already-found values, and now we're
            # just reading new ones.
            token = self.read()

            if isinstance(token, PdfToken):
                # Again tokens require closer looks.
                token_bytes = bytes(token)

                if token_bytes == b"endobj":
                    return PdfIndirectObject(token_stack)
                if token_bytes == b"stream":
                    return self.return_stream(token_stack)

            # And non-ending tokens will just be pushed.
            token_stack.append(token)

        # If we reach a fifth object without reaching an ending token,
        # then we have some invalid nonsense going on here. Eff that.
        raise Exception("The fifth object should be endobj or stream.")

    def point_at_last_xref (self):
        # Seek to the last 2048 bytes of the file.
        self.pdf.seek_from_end(2 * self.eof_marker_buffer)

        # Get the current position and read to the end.
        current_pos = self.pdf.pos()
        eof_str     = self.pdf.read()

        # Find the EOF marker in the last 1024 bytes.
        marker      = eof_str.rfind(b"%%EOF", self.eof_marker_buffer)

        if marker == -1:
            # Give up if we didn't find the marker.
            raise Exception("Couldn't find %%EOF marker anywhere in" \
                            " the last {:d} bytes".format(
                                    self.eof_marker_buffer))

        # We could just find the position of the startxref token, but we
        # want to be ready for something stupid like a comment, so we're
        # being just a little bit more careful.
        token_pos   = None
        while token_pos is None:
            # Find it.
            token_pos   = eof_str.rfind(b"startxref", 0, marker)

            if token_pos == -1:
                # If we can't find it, give up.
                raise Exception("Couldn't find startxref token" \
                                " anywhere in the last {:d}"    \
                                " bytes".format(
                                        2*self.eof_marker_buffer))

            if token_pos > 0:
                # If we're after the beginning of the string, checking
                # the previous byte is a simple subtraction.
                if eof_str[token_pos - 1] not in b"\n\r":
                    # Update the marker to narrow our search, and reset
                    # our token position.
                    marker      = token_pos
                    token_pos   = None

            else:
                # It's a bit silly, but hey, if we've actually found
                # startxref an entire 1024 bytes before %%EOF, we may as
                # well at least check to make sure it's at the beginning
                # of a line.
                if self.pdf[current_pos-1:1] not in b"\n\r":
                    # If it's not, then, well, we'll continue, but we
                    # definitely won't find anything.
                    marker      = token_pos
                    token_pos   = None

        # OK! We've found what appears to be a valid startxref token. We
        # can point ourselves at it.
        self.seek(current_pos + token_pos)

        if self.read() != PdfToken(b"startxref"):
            # If the next token isn't startxref, something really stupid
            # must be going on, and I want no part in it. I give up.
            raise Exception("Couldn't find startxref etc")

        # The next thing should be the offset value for the cross
        # reference table (or stream).
        xref_pos    = self.read()

        if not isinstance(xref_pos, int):
            # It's not an integer! What the heck
            raise Exception("Expected integer after startxref token")

        if xref_pos < 0:
            # Buh-whuh why is it negative! After all this! Ugh
            raise Exception("Expected positive startxref value")

        # Awesome. We have located the valid offset for the last cross
        # reference table in the PDF file. All that's left is to point
        # ourselves at that, and our work here is done.
        self.seek(xref_pos)

    def return_stream (self, token_stack):
        while self.byte != self.eol_lf:
            # Look for a line feed.
            self.step()

        # Go past the line feed.
        self.step()

        # Return the stream with the offset for the very beginning of
        # the stream data.
        return PdfStream(token_stack, self.pos)

    def __repr__ (self):
        """Represent our position"""
        return "<{} {:08x}>".format(self.__class__.__name__, self.pos)

class PdfTrailer:
    def __init__ (self,
                  size,
                  root,
                  info          = None,
                  original_id   = None,
                  current_id    = None):
        self.size           = size
        self.root           = root
        self.info           = info
        self.original_id    = original_id
        self.current_id     = current_id

    def __repr__ (self):
        values  = [
            "size: {}".format(repr(self.size)),
            "root: {:d} {:d} R".format(*self.root),
        ]

        if self.info is not None:
            values.append("info: {:d} {:d} R".format(*self.info))

        return "<{} {}>".format(self.__class__.__name__,
                                ", ".join(values))

class PdfObjEntry:
    FreeEntry   = 0
    InUseEntry  = 1
    Compressed  = 2

class PdfXrefHistory:
    old_fashioned_tokens = {
        PdfToken(b"f"): PdfObjEntry.FreeEntry,
        PdfToken(b"n"): PdfObjEntry.InUseEntry,
    }

    FreeEntryTuple  = namedtuple("FreeEntryTuple",  ("next_free",
                                                     "generation"))
    InUseEntryTuple = namedtuple("InUseEntryTuple", ("offset",
                                                     "generation"))
    CompressedTuple = namedtuple("CompressedTuple", ("parent_stream",
                                                     "index"))
    UnknownTuple    = namedtuple("UnknownTuple",    ("field_1",
                                                     "field_2",
                                                     "field_3"))

    default_type    = PdfObjEntry.InUseEntry

    default_field_2 = {
        # No known types have defaults for this field.
    }

    default_field_3 = {
        # InUseEntries have a default generation number of 0.
        PdfObjEntry.InUseEntry: 0,
    }

    endien          = "big"

    tuples_by_type  = {
        PdfObjEntry.FreeEntry:  FreeEntryTuple,
        PdfObjEntry.InUseEntry: InUseEntryTuple,
        PdfObjEntry.Compressed: CompressedTuple,
    }

    def __init__ (self, factory):
        # We'll store a list of cross reference tables and a list of
        # trailers.
        self.cross_refs = [ ]
        self.trailers   = [ ]

        # Be sure our factory is pointing at the last cross reference
        # section.
        factory.point_at_last_xref()

        # Since we haven't even started reading yet, we know there's
        # more to read.
        theres_more_to_read = True

        while theres_more_to_read:
            # While there is more to read, keep reading cross reference
            # sections.
            theres_more_to_read = self.read_xref(factory)

    def read_xref (self, factory):
        # Get whatever the first object is here.
        first_object    = factory.read()

        if first_object == PdfToken(b"xref"):
            # If it's an xref token, then it marks the beginning of an
            # old-fashioned cross reference stream.
            return self.read_table(factory)

        # The only other possibility is that we have a cross reference
        # stream. We've already read one token in the object, so all
        # that's left is to read the rest.
        return self.read_stream(
                factory, factory.read_indirect_object(first_object))

    def read_stream (self,
                     factory,
                     xref_stream,
                     section_data   = { },
                     is_hybrid      = False):

        # Be sure we actually have a stream.
        assert isinstance(xref_stream, PdfStream)
        assert xref_stream.value["Type"] == PdfDictType.XRef

        # Pull the dictionary and get the stream length.
        stream_dict     = xref_stream.value
        length          = stream_dict["Length"]
        if not isinstance(length, int):
            raise Exception("I do not support indirect lengths for" \
                            " cross reference streams.")

        # Decode the stream.
        xref_stream.decode_stream_data(length, factory.pdf)
        data            = xref_stream.data

        assert data is not None

        size            = stream_dict["Size"]
        widths          = stream_dict["W"]
        index           = stream_dict.get("Index", [0, size])

        assert len(widths) == 3

        pos             = 0
        for start, length in deflatten(2, index):
            # Each pair of values in the index array corresponds to a
            # subsection.
            for obj_num in range(start, start + length):
                assert obj_num not in section_data

                # Each object has a row in the stream.
                row = [ ]

                for width in widths:
                    # Each field could have a width of zero.
                    if width == 0:
                        # If so, we don't need to even look at the
                        # stream.
                        row.append(None)
                        continue

                    # Otherwise, we'll read however many bytes as a
                    # big-endien integer.
                    end = pos + width
                    row.append(int.from_bytes(data[pos:end],
                                              self.endien))

                    # Move our position forward in the stream.
                    pos = end

                section_data[obj_num] = self.get_xref_entry(row.pop(0),
                                                            row.pop(0),
                                                            row.pop(0))

        # Be sure we've reached the end of the stream.
        assert pos == len(data)

        # Insert our new cross reference section.
        self.cross_refs.insert(0, section_data)

        if not is_hybrid:
            # If this were a hybrid file, we'd already have a trailer.
            # But it's not, so we need to treat the stream dictionary as
            # if it were a trailer.
            return self.read_trailer(factory, stream_dict)

    def read_table (self, factory):

        # In the end, we'll have a dictionary keyed on object numbers.
        section_data = { }

        while True:
            # Get the first number of this subsection.
            object_start    = factory.read()

            if object_start == PdfToken(b"trailer"):
                # If it's actually the trailer token instead of the
                # start of a new subsection, then we're done with this
                # section, and we can insert it.
                self.cross_refs.insert(0, section_data)

                # Next up is adding the trailer.
                return self.read_trailer(factory, factory.read())

            # Otherwise, we must have a cross reference subsection to
            # read. Get the second number (the object count).
            object_stop     = factory.read() + object_start

            for object_number in range(object_start, object_stop):
                # Each line has three things on it: two numbers and a
                # type token.
                first_number    = factory.read()
                second_number   = factory.read()
                type_token      = factory.read()

                if object_number in section_data:
                    # If we've already seen this object number, we
                    # should silently ignore it (because Acrobat will
                    # also silently ignore it).
                    continue

                # The type should be in the old-fashioned token dict.
                entry_type      = self.old_fashioned_tokens[type_token]

                # Finally add whatever information we got in the
                # appropriate format to our section data.
                section_data[object_number] = self.get_xref_entry(
                                                entry_type,
                                                first_number,
                                                second_number)

    def read_trailer (self, factory, trailer):
        # These two must be in there.
        size    = trailer["Size"]
        root    = trailer.get("Root", None)

        # And these two might be in there.
        info    = trailer.get("Info", None)
        ids     = trailer.get("ID", [None, None])

        # Insert the trailer data.
        self.trailers.insert(0, PdfTrailer(size,
                                           root,
                                           info,
                                           ids[0],
                                           ids[1]))

        if "XRefStm" in trailer:
            # If the trailer links to a cross reference stream, then we
            # need to read that before we're really done.
            factory.seek(trailer["XRefStm"])

            # It'll point to an indirect object. I'll also need to
            # remove the most-recently-added cross reference section so
            # that it can be modified and re-added.
            self.read_stream(factory,
                             factory.read_indirect_object(),
                             self.cross_refs.pop(0),
                             is_hybrid = True)

        if "Prev" in trailer:
            # If there's a previous cross reference section, then we
            # need to point our factory at it.
            factory.seek(trailer["Prev"])

            # We return true to show that there's more work to do.
            return True

        else:
            # If there's no reference to a previous section, this must
            # be the first one. In this case, we return false to show
            # that we're done reading cross reference sections.
            return False

    def get_xref_entry (self, entry_type, field_2, field_3):
        # Be ready to swap in default values where needed.
        if entry_type is None:
            entry_type = self.default_type

        if field_2 is None:
            field_2 = self.default_field_2[entry_type]

        if field_3 is None:
            field_3 = self.default_field_3[entry_type]

        if entry_type not in self.tuples_by_type:
            return self.UnknownTuple(entry_type, field_2, field_3)

        # Now that everything's guaranteed to have a value, return the
        # named tuple.
        return self.tuples_by_type[entry_type](field_2, field_3)

class PdfCrossReference (Mapping):
    EntryTuple = namedtuple("EntryTuple", ("generation",
                                           "value"))

    ObjPos = namedtuple("ObjPos", ("offset",))
    SubObj = namedtuple("SubObj", ("parent", "index"))

    def __init__ (self, factory, xref_history):
        # We'll keep an internal dictionary and a maximum object number.
        self.internal_dict  = { }
        self.max_object_num = 0

        # First we pull all the most-recent cross reference data from
        # the history.
        self.pull_data_from_history(xref_history)

        # Second, we extract all the objects from the file (using our
        # factory).
        self.extract_objects_from_file(factory)

    def __len__ (self):
        return self.max_object_num + 1

    def __getitem__ (self, key):
        if not isinstance(key, tuple) \
                or len(key) != 2:
            # Be sure the user asked for an object number and a
            # generation number.
            raise KeyError("Expected a 2-tuple of object number and" \
                           " generation number.")

        # Extract the two numbers that will help is find the object.
        obj_num, gen_num = key

        if obj_num in self.internal_dict:
            # We do have an object by this number. Extract it.
            generation, value = self.internal_dict[obj_num]

            if generation == gen_num:
                # Oh nice! And the generation matches! Well done.
                return value

        # According to the PDF spec, there are no incorrect indirect
        # references to objects. If a referenced object does not
        # actually exist, it should be treated as null.
        return None

    def __iter__ (self):
        return self.keys()

    def __contains__ (self, key):
        if not isinstance(key, tuple) \
                or len(key) != 2:
            # If the key isn't a 2-tuple, then it isn't in here.
            return False

        # Extract the two numbers that make up the key.
        obj_num, gen_num = key

        if obj_num in self.internal_dict:
            # If we do have this object by number, make sure the key
            # matches.
            return gen_num == self.internal_dict[obj_num].generation

        else:
            # If we don't, then we don't.
            return False

    def simple_iterator (func):
        def result (self):
            # We want to iterate in order across every possible object.
            for obj_num in range(self.max_object_num + 1):
                # For each possible object number, check for its
                # existence in our internal dictionary.
                if obj_num in self.internal_dict:
                    # We have it. What we do next depends on exactly
                    # what we need to be yielding.
                    yield func(obj_num, self.internal_dict[obj_num])

        return result

    @simple_iterator
    def items (obj_num, entry):
        # Since we're returning the key and the value, we'll need to
        # extract that information from the entry, which contains half
        # the key and the entire value.
        gen_num, value = entry

        # The resulting 2-tuple contains a 2-tuple key and the value.
        return (PdfObjectReference(obj_num, gen_num), value)

    @simple_iterator
    def keys (obj_num, entry):
        # Half the key (the generation number) is in the entry.
        return PdfObjectReference(obj_num, entry.generation)

    @simple_iterator
    def values (obj_num, entry):
        # In this case, we needn't even look at the generation number.
        return entry.value

    def pull_data_from_history (self, xref_history):
        # We'll look at each cross reference section from oldest to
        # newest.
        for xref in xref_history.cross_refs:
            # We'll look at the actual entries in no particular order.
            for obj_num, value in xref.items():
                if obj_num > self.max_object_num:
                    # If this is the largest entry we've yet seen, we
                    # should make a note of it.
                    self.max_object_num = obj_num

                if isinstance(value, (PdfXrefHistory.FreeEntryTuple,
                                      PdfXrefHistory.UnknownTuple)):
                    # We don't track free objects.
                    if obj_num in self.internal_dict:
                        # If this object ever was in the dictionary, get
                        # rid of it.
                        del self.internal_dict[obj_num]

                elif isinstance(value, PdfXrefHistory.InUseEntryTuple):
                    # If it's just a regular entry, then we start by
                    # just adding the offset wrapped in the ObjPos
                    # tuple.
                    self.internal_dict[obj_num] = self.EntryTuple(
                            value.generation, self.ObjPos(value.offset))

                elif isinstance(value, PdfXrefHistory.CompressedTuple):
                    # Otherwise, if it's a compressed entry, then we'll
                    # give it its implicit generation number of zero and
                    # insert a 2-tuple with extraction information.
                    self.internal_dict[obj_num] = self.EntryTuple(0,
                            self.SubObj(value.parent_stream,
                                        value.index))

    def extract_objects_from_file (self, factory):
        # Pull all the easy objects and pay attention to which (if any)
        # are object streams.
        objstms = self.first_pass_normal_objects(factory)

        # Next we handle the object streams.
        self.second_pass_object_streams(factory, objstms)

    def first_pass_normal_objects (self, factory):
        # Be ready to collect a list of keys to object streams.
        objstms = set()

        for key, value in self.items():
            if isinstance(value, self.ObjPos):
                # The first time around, we only pay attention to simple
                # objects with nothing more than an offset. Point our
                # factory at that offset.
                factory.seek(value.offset)

                # Get the indirect object from the pdf file.
                indirect_object = factory.read_indirect_object()

                if indirect_object.object_key != key:
                    raise Exception("Keys must be equal")

                # Extract the subkeys for inserting the actual data into
                # the internal dictionary.
                obj, gen = key

                if isinstance(indirect_object, PdfStream):
                    # If we have a stream, check whether it's an object
                    # stream.
                    if indirect_object.value.get("Type", None) \
                            == PdfDictType.ObjStm:
                        # If it is, add it to the result set.
                        objstms.add(key)

                    # Also if it's a stream, we just add it as-is to the
                    # internal dictionary.
                    self.internal_dict[obj] = self.EntryTuple(
                            gen, indirect_object)

                else:
                    # If it's not a stream, we can safely add just the
                    # value without the PdfIndirectObject wrapper.
                    self.internal_dict[obj] = self.EntryTuple(
                            gen, indirect_object.value)

        # Every ObjPos object in our storage has been replaced by a
        # useful PDF value. All that's left are sub-objects and streams.
        return objstms

    def second_pass_object_streams (self, factory, objstms):
        # We want to track the size of this set in order to avoid an
        # infinite error loop.
        current_len = len(objstms)

        while current_len > 0:
            # If we still have streams to expand, generate a list to
            # iterate through. It can be in any order.
            stream_list = list(objstms)

            for stream_key in stream_list:
                # Get the stream info.
                stream  = self[stream_key]
                desc    = stream.value
                offset  = stream.stream_offset

                # In particular, grab the length.
                length  = desc["Length"]

                if not isinstance(length, int):
                    # If the length isn't an int, then it must be an
                    # indirect reference. This can be ok. Check.
                    length = self[length]

                    if isinstance(length, PdfIndirectObject):
                        # Yup! Grab the value itself.
                        length = length.value

                if not isinstance(length, int):
                    # If we still don't have a length, then we'll have
                    # to postpone this one until we do.
                    continue

                # Decode the stream data.
                stream.decode_stream_data(length, factory.pdf)

                if stream.data is None:
                    # If the data didn't decode, we can't move forward.
                    raise Exception("Why is this encoded all stupid")

                # We'll wrap the data in an object factory.
                stream_factory  = PdfObjectFactory(
                                        FileReader(stream.data))

                # We'll want an object count and the offset of the first
                # object from the stream dictionary.
                object_count    = desc["N"]
                shared_offset   = desc["First"]

                # I have to make the array of object offsets before I
                # can actually look at any objects.
                object_offsets  = [ ]
                for i in range(object_count):
                    # Pull the object number and offset from the stream.
                    # The offset will need to be added to the shared
                    # offset above since they're calculated based on the
                    # first object starting at zero.
                    num     = stream_factory.read()
                    off     = stream_factory.read() + shared_offset

                    # Grab the placeholder object that we're currently
                    # storing.
                    subobj  = self[num, 0]

                    # Be sure it's the right kind of placeholder and
                    # that its recorded parent and index match those of
                    # the stream we're looking at.
                    assert isinstance(subobj, self.SubObj)            \
                            and subobj.parent    == stream_key.number \
                            and subobj.index     == i

                    # Awesome! Add this info to the list.
                    object_offsets.append((num, off, i))

                for num, off, i in object_offsets:
                    # Now that we have our complete list, we can start
                    # jumping around in the stream. Read the object.
                    stream_factory.seek(off)
                    value   = stream_factory.read()

                    # Update its value in the internal storage.
                    self.internal_dict[num] = self.EntryTuple(0, value)

                # If we made it to here, then we've successfully dealt
                # with this object stream. Remove it from the to-do
                # list.
                objstms.remove(stream_key)

            old_len     = current_len
            current_len = len(objstms)
            if old_len == current_len:
                # I don't want any infinite loops in here.
                raise Exception("Failed to expand every object stream.")

        for key, value in self.items():
            # Be sure that all ObjPos and SubObj values have been
            # removed from our list.
            assert not isinstance(value, (self.ObjPos, self.SubObj))

            if isinstance(value, PdfIndirectObject):
                # If it's an indirect object, that's fine, as long as
                # it's a stream.
                assert isinstance(value, PdfStream)

                # That said, if it is a stream, we should try to decode
                # its contents. Pull its length.
                length  = self.follow_reference(value.value["Length"])

                # Decode the stream data (if there's decoding to do).
                value.decode_stream_data(length, factory.pdf)

        # All that decoding of stream data could have the factory all
        # out of whack with its file reader. To fix that, we'll point it
        # right back at the beginning of the PDF itself.
        factory.seek(0)

    def follow_reference (self, value):
        while isinstance(value, PdfObjectReference):
            # Follow any number of indirect references.
            value = self[value]

        # Return the actual value.
        return value

class PdfContentStream:
    expected_tokens     = {
        PdfToken(b"BT"): (PdfToken(b"ET"), {
            PdfToken(b"Tc"):    1,
            PdfToken(b"Tw"):    1,
            PdfToken(b"Tz"):    1,
            PdfToken(b"TL"):    1,
            PdfToken(b"Tf"):    2,
            PdfToken(b"Tr"):    1,
            PdfToken(b"Ts"):    1,

            PdfToken(b"Td"):    2,
            PdfToken(b"TD"):    2,
            PdfToken(b"Tm"):    6,
            PdfToken(b"T*"):    0,

            PdfToken(b"Tj"):    1,
            PdfToken(b"'"):     1,
            PdfToken(b'"'):     3,
            PdfToken(b"TJ"):    1,
        }),

        PdfToken(b"q"): (PdfToken(b"Q"), {
            PdfToken(b"cm"):    6,
            PdfToken(b"w"):     1,
            PdfToken(b"J"):     1,
            PdfToken(b"j"):     1,
            PdfToken(b"M"):     1,
            PdfToken(b"d"):     2,
            PdfToken(b"ri"):    1,
            PdfToken(b"i"):     1,
            PdfToken(b"gs"):    1,
            PdfToken(b"Do"):    1,
        }),
    }

    # I want a dictionary of dictionaries of dictionaries, and I want it
    # always to at the very least match the above dictionary, so I think
    # it's best to build it automagically.
    expected_resources  = { }

    for key in expected_tokens:
        # Make sure it's ready for every possible section.
        expected_resources[key.token] = { }

    # This iterable tuple is where I'm actually putting the data.
    for section, operator, index, resource in (
            (b"BT",    b"Tf",  0,  "Font"),
            (b"q",     b"Do",  0,  "XObject")):
        if operator not in expected_resources[section]:
            # If I haven't seen this particular operator in this
            # particular section yet, give it an empty dict.
            expected_resources[section][operator] = { }

        # Either way, add this particular argement index and its
        # resource dictionary name.
        expected_resources[section][operator][index] = resource

    SectionTuple        = namedtuple("SectionTuple",    ("start",
                                                         "stop",
                                                         "section"))
    OperatorTuple       = namedtuple("OperatorTuple",   ("token",
                                                         "args"))

    def __init__ (self, stream_data):
        # We really just want a factory.
        factory         = PdfObjectFactory(stream_data)

        # Interpret the content stream.
        self.sections   = self.read_sections(factory)

        # And build a dictionary of resources used by the stream that
        # exist elsewhere in the pdf (and will have to be named in the
        # page's resource dictionary).
        self.resources  = self.find_resources()

    def read_sections (self, factory):
        # We'll return a deque of sections.
        result  = deque()

        while True:
            # Read the next thing, and be ok with the end of the file.
            start           = factory.read(None)

            if start is factory.EndDelimiter:
                # If we reach the end of the file, we return our list of
                # sections.
                return result

            if start not in self.expected_tokens:
                # Otherwise, if we aren't expecting the section
                # beginning that we got, then we need to raise an
                # exception.
                raise Exception("Can't handle {}".format(repr(start)))

            # Get the ending token and the dictionary of expected
            # tokens.
            end, expected   = self.expected_tokens[start]

            # We'll represent unaccounted-for 
            stack           = deque()

            while True:
                # Get the next value.
                value   = factory.read()

                if value == end:
                    # It's the token that signifies the end of the
                    # section! Time to stop.
                    break

                if value in expected:
                    # We were looking for this value! We start building
                    # a new queue of arguments popped off our stack of
                    # all values.
                    args    = deque()

                    for i in range(expected[value]):
                        # Pop off whatever is the right number of
                        # arguments and push them onto our argument
                        # queue.
                        args.appendleft(stack.pop())

                    # We convert that deque to a tuple and push an
                    # OperatorTuple back into the value stack.
                    stack.append(self.OperatorTuple(value.token,
                                                    tuple(args)))

                elif isinstance(value, PdfToken):
                    # Tokens are not ok.
                    raise Exception("Unknown token in {}: {}".format(
                                    repr(start), repr(value)))

                else:
                    # Push it on in!
                    stack.append(value)

            # Add the section to the resulting section list.
            result.append(self.SectionTuple(start.token,
                                            end.token,
                                            stack))

    def find_resources (self):
        # In the end, I want to return a dictionary.
        resources   = { }

        for start, end, section in self.sections:
            # Now that I've created the 3-dimensinoal dictionary, I can
            # just grab the part I want for this particular section.
            current_exp = self.expected_resources[start]

            for operator_tuple in section:
                if not isinstance(operator_tuple, self.OperatorTuple):
                    # Assert that each thing in here is an operator
                    # tuple like it should be. If it isn't, then there
                    # must be some operands that aren't part of some
                    # operator.
                    raise Exception("EXTRA OPERANDS >:(")

                # Ok cool, go ahead and split the dang thing.
                operator, args = operator_tuple

                # Now I look at each operator tuple in the section. If
                # this operator isn't present in our expected resources
                # dictionary, then I'll pretend it's got an empty
                # dictionary.
                for index, resource in current_exp.get(
                        operator, { }).items():
                    # I'll want to add it under the resource name.
                    if resource not in resources:
                        # If we haven't seen this resource name yet,
                        # then I create a new set for it first.
                        resources[resource] = set()

                    # Pull the name argument.
                    name    = args[index]

                    if not isinstance(name, PdfName):
                        # Assert that we have an actual name. Gotta be a
                        # name yo
                        raise Exception("What it's gotta be a name")

                    # Awesome! Add the string version of the name to our
                    # result, since the string version is what we'll
                    # actually be using to access the thing in the
                    # python version of the dictionaries.
                    resources[resource].add(str(name))

        # Return dat dict.
        return resources

class Pdf (Mapping):
    def __init__ (self, file_object):
        if not isinstance(file_object, FileReader):
            # The user doesn't actually have to provide a FileReader
            # object, but, if they don't, we still need to have one.
            file_object = FileReader(file_object)

        # Store the FileReader object.
        self.pdf_file   = file_object

        # For the moment, we'll need an object factory.
        factory         = PdfObjectFactory(file_object)

        # We can use our factory to get a complete cross reference
        # history.
        xref_history    = PdfXrefHistory(factory)

        # We don't really need the complete history though. All we want
        # is the most recent trailer info and all the objects
        # themselves.
        self.trailer    = xref_history.trailers[-1]
        self.objects    = PdfCrossReference(factory, xref_history)

    def __getitem__ (self, key):
        return self.objects[key]

    def __len__ (self):
        return len(self.objects)

    def __iter__ (self):
        return iter(self.objects)

    def __contains (self, key):
        return key in self.objects

    def follow (self, value):
        return self.objects.follow_reference(value)
