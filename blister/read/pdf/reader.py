# Copyright (c) 2015 The Regents of the University of Michigan.
# All Rights Reserved. Licensed according to the terms of the Revised
# BSD License. See LICENSE.txt for details.
from collections    import  namedtuple, deque, OrderedDict, Sequence, \
                            Hashable, Mapping, MutableSequence
from fractions      import  Fraction
from generic        import  FileReader, hex_to_bytes, deflatten
from re             import  compile as re_compile

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
            self.string = hex_to_bytes(hexstring)

        else:
            # If not, I'll need to add a `0` byte before converting it.
            self.string = hex_to_bytes(hexstring + b"0")

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

        # Follow each hashtag escape to get a new, more accurate string
        # of bytes.
        escaped         = self.re_hashtag.sub(self.hashtag_repl,
                                              name_bytes)

        try:
            # Try to decode using UTF-8.
            self.name   = escaped.decode("utf_8")
            self.utf8   = True

        except UnicodeDecodeError:
            # If we can't, we'll decode using some other possibilities,
            # but we'll also make a note that this is not UTF-8.
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
        return hex_to_bytes(match.group(1))

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

    def __dict__ (self):
        """Return a simple dict"""
        result = { }

        for key, values in self.internal_dict:
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

class PdfToken:
    """PDF Token"""
    def __init__ (self, bytestring):
        """Take in a string of regular bytes"""
        self.token  = bytestring

    def __bytes__ (self):
        """This is already little more than a bytes object"""
        return self.token

    def __eq__ (self, other):
        return bytes(self) == bytes(other)
    def __ne__ (self, other):
        return bytes(self) != bytes(other)

    def __repr__ (self):
        """Represent the token"""
        return "<{} {}>".format(self.__class__.__name__,
                                repr(self.token))

PdfObjectReference  = namedtuple("PdfObjectReference",
                                 ("number", "generation"))

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

    class EndDelimiter:
        pass

    def __init__ (self, pdf_file):
        # Internalize the file object.
        self.pdf    = pdf_file
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

        7.  If the result is a PdfDict, then we found a dictionary. The
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

            if self.byte = self.delim_comment:
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
                        self.pdf.error(-2, "Expected '>>', not '>'")

                    return mapping

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
                        hex_list = bytearray()

                    else:
                        # Otherwise, we'll initialize the list with this
                        # byte in it.
                        hex_list = bytearray(self.byte)

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

                            if value < 0 or value >= 010:
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

                                if next_digit < 0 or next_digit >= 010:
                                    # OK, so this one isn't a digit. Go
                                    # back and stop looking.
                                    self.backstep()
                                    break

                                # It is another digit! Add it to the
                                # value.
                                value *= 010
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
            self.pdf.error(-1, "Unexpected {} byte".format(
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

    def __repr__ (self):
        """Represent our position"""
        return "<{} {:08x}>".format(self.__class__.__name__, self.pos)
