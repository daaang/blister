# Copyright (c) 2015 The Regents of the University of Michigan.
# All Rights Reserved. Licensed according to the terms of the Revised
# BSD License. See LICENSE.txt for details.
from collections        import  deque, MutableMapping, namedtuple
from fractions          import  Fraction
from re                 import  compile as re_compile
from uuid               import  uuid4 as gen_uuid

from ...read.pdf.reader import  PdfName, PdfHex
from .filters           import  encode_Flate, encode_ASCII85

class PrePdfName:
    # We'll need to escape delimiters, whitespace, and `#` characters
    # with `#` characters. We'll also escape any non-ascii characters as
    # per adobe's recommendations.
    re_escape   = re_compile(rb"[^!-~]|[()<>{}[\]/%#]")

    def __init__ (self, namestr):
        # Set the unicode name.
        self.name   = namestr

        # Generate the coded name that goes in the PDF.
        self.gen_code()

    def __str__ (self):
        # Return the unicode name.
        return self.name

    def __bytes__ (self):
        # Return our coded name.
        return self.code

    def gen_code (self):
        # Encode the name with UTF-8.
        coded       = self.name.encode("utf_8")

        # Escape any characters that could be problematic for a name.
        escaped     = re_escape(self.escape_repl, coded)

        # Prepend a slash.
        self.code   = b"/" + escaped

    def escape_repl (self, match):
        # Bytes are escaped with a `#` and two hexadecimal bytes.
        return "#{:02x}".format(match.group(0)[0]).encode("ascii")

class PrePdfReference:
    def __init__ (self, uuid):
        # Objects have UUIDs before they're assigned numbers.
        self.uuid   = uuid

    def to_bytes (self, object_numbers):
        # Once we have numbers for each UUID, we can output bytes.
        number, generation = object_numbers[self.uuid]

        # It's all just ASCII, so there's no need to really encode
        # anything.
        return "{:d} {:d} R".format(number, generation).encode("ascii")

class PrePdfStream (MutableMapping):
    FileTuple   = namedtuple("FileTuple",   ("filename",
                                             "offset",
                                             "length"))

    def __init__ (self, info_dict = { }):
        # These are initialized with an info dictionary, and they
        # basically act like that exact dictionary.
        self.info       = info_dict

        # These values are the exception to this thing acting as a
        # dictionary.
        self.autovalues = {
            "Length":       self.get_length,
            "Filter":       self.get_filter,
            "DecodeParms":  self.get_decode_parms,
        }

        self.add_zip    = False
        self.add_base85 = False

        self.stream         = None
        self.source_filters = [ ]
        self.source_decodes = [ ]

    def __getitem__ (self, key):
        if key in self.autovalues:
            return self.autovalues[key]()

        else:
            return self.info[key]

    def __setitem__ (self, key, value):
        if key in self.autovalues:
            raise KeyError("{} is reserved".format(key))

        self.info[key] = value

    def __delitem__ (self, key):
        if key in self.autovalues:
            raise KeyError("{} is reserved".format(key))

        del self.info[key]

    def __iter__ (self):
        keys    = list(self.info.keys())

        for key in self.autovalues:
            if key in self:
                keys.append(key)

        keys.sort()
        return iter(keys)

    def __len__ (self):
        result = len(self.info)
        for key in self.autovalues:
            if key in self:
                result += 1

        return result

    def __contains__ (self):
        if key in self.autovalues:
            try:
                value = self.autovalues[key]()
                return True

            except KeyError:
                return False

        else:
            return key in self.info

    def get_length (self):
        assert not self.add_zip and not self.add_base85

        if isinstance(self.stream, self.FileTuple):
            return self.stream.length

        else:
            return len(self.stream)

    def get_filter (self):
        result  = list(self.source_filters)

        if self.add_zip:
            result.insert(0, PrePdfName("FlateDecode"))

        if self.add_base85:
            result.insert(0, PrePdfName("ASCII85Decode"))

        if len(result) == 0:
            raise KeyError

        elif len(result) == 1:
            return result[0]

        else:
            return result

    def get_decode_parms (self):
        result  = list(self.source_decodes)

        if self.add_zip:
            result.insert(0, { })

        if self.add_base85:
            result.insert(0, { })

        useful_values = False
        for value in result:
            if len(value) > 0:
                useful_values = True
                break

        if not useful_values:
            raise KeyError

        elif len(result) == 1:
            return result[0]

        else:
            return result

    def set_stream_to_file (self,
                            filename,
                            offset,
                            length,
                            filters         = [ ],
                            decode_parms    = [ ]):
        self.stream         = self.FileTuple(filename, offset, length)

        self.source_filters = filters
        self.source_decodes = decode_parms

    def set_stream_to_bytes (self,
                             stream,
                             filters        = [ ],
                             decode_parms   = [ ]):
        self.stream         = stream
        self.source_filters = filters
        self.source_decodes = decode_parms

        if self.add_zip:
            self.add_zip    = False
            self.stream     = encode_Flate(self.stream)
            self.source_filters.insert(0, PrePdfName("FlateDecode"))
            self.source_decodes.insert(0, { })

        if self.add_base85:
            self.add_base85 = False
            self.stream     = encode_ASCII85(self.stream)
            self.source_filters.insert(0, PrePdfName("ASCII85Decode"))
            self.source_decodes.insert(0, { })

    def write (self, outfile):
        if isinstance(self.stream, self.FileTuple):
            filename, offset, length = self.stream

            obj = open(filename, "rb")
            obj.seek(offset)
            outfile.write(obj.read(length))

            obj.close()

        else:
            outfile.write(self.stream)

class PrePdfObject (MutableMapping):
    # These are static values. Each just has its own name.
    static_tokens   = {
        None:   b"null",
        True:   b"true",
        False:  b"false",
    }

    # All these characters must be replaced by visual ASCII in PDF
    # strings. Note in particular the lack of backslashes and linefeeds.
    # Those are special cases: backslashes are escaped before all these,
    # and linefeeds are only sometimes escaped at all.
    string_escapes  = {
        b"\r":  b"\\r",
        b"\t":  b"\\t",
        b"\b":  b"\\b",
        b"\f":  b"\\f",
    }

    # If a byte we don't want to display as-is appears before what could
    # be an octal digit, then we have to handle that a particular way.
    re_long_octal   = re_compile(rb"([^\n -~])([0-7])")

    # Once we've dealt with all the above cases, we can just look at the
    # rest of the bytes we don't want to display as-is separately.
    re_any_octal    = re_compile(rb"[^\n -~]")

    # We only want to escape line feeds in short strings. In longer
    # strings, they'll only aid readability *and* there's a chance of
    # actually making the file significantly larger by escaping them
    # all. My choice of 80 characters as the cutoff is arbitrary.
    short_string    = 80

    stream_separate = (b"\nstream\n", b"\nendstream")
    stream_exlen    = len(stream_separate[0]) + len(stream_separate[1])

    def __init__ (self, value):
        # Objects hold values.
        self.modify(value)

        # We'll also track the most recently-generated bytes objects.
        self.recent = b""

    def modify (self, value):
        self.value      = value
        self.modified   = True

    def __len__ (self):
        result = len(self.recent)

        if isinstance(self.value, PrePdfStream):
            result += self.stream_exlen + self.value["Length"]

        # The length should always be handy.
        return len(self.recent)

    def write (self, outfile, object_numbers):
        if self.modified:
            outfile.write(self.to_bytes(object_numbers))
        else:
            outfile.write(self.recent)

        if isinstance(self.value, PrePdfStream):
            outfile.write(self.stream_separate[0])
            self.value.write_stream(outfile)
            outfile.write(self.stream_separate[1])

    def to_bytes (self, object_numbers):
        if isinstance(self.value, PrePdfStream):
            value       = dict(self.value)
        else:
            value       = self.value

        old_len         = len(self.recent)
        self.recent     = self.bytes_helper(value, object_numbers)
        new_len         = len(self.recent)
        self.modified   = False

        self.recent += b" " * (old_len - new_len)

        return self.recent

    def bytes_helper (self,
                      value,
                      object_numbers,
                      already_has_space = True):
        if value in self.static_tokens:
            # Static tokens are made of regular characters, so they need
            # to be separated by whitespace or delimiters.
            if already_has_space:
                # There's already a delimiter or some space, so we're
                # fine.
                return (self.static_tokens[value], False)

            else:
                # Uh oh! No delimiter, so we need to add our own space.
                return (b" " + self.static_tokens[value], False)

        elif isinstance(value, int):
            # Integers are also tokens, so we need to go through the
            # same as the above routine about whether we have space.
            if already_has_space:
                return ("{:d}".format(value).encode("ascii"), False)
            else:
                return (" {:d}".format(value).encode("ascii"), False)

        elif isinstance(value, Fraction):
            # Again, fractions are tokens. Etc etc etc.
            if already_has_space:
                return ("{:f}".format(value).encode("ascii"), False)
            else:
                return (" {:f}".format(value).encode("ascii"), False)

        elif isinstance(value, list):
            # But lists aren't tokens! They begin with delimiters, so
            # who cares what the previous byte was. Since I'm opening
            # with this delimiter, I can set our space tracker to true
            # for now.
            result  = b"["
            space   = True

            for item in value:
                # Items will be separated by spaces only when needed.
                more, space = self.bytes_helper(item,
                                                object_numbers,
                                                space)

                # Append this item to our result.
                result += more

            # Again, regardless of our last space value, we can just
            # tack on the delimiter and return true about space.
            return (result + b"]", True)

        elif isinstance(value, dict):
            # Dictionaries are similar to lists but with different
            # delimiters.
            result  = b"<<"

            # We sort our keys to ensure the same output every time this
            # is run on the same input.
            keys    = list(value.keys())
            keys.sort()

            for key in keys:
                # The first item in each pair is a name. It begins with
                # a delimiter, so I'm not even tracking space between
                # loops.
                result     += bytes(PrePdfName(key))

                # However, the first character is the only delimiter in
                # a name, so the next item might need to add some
                # whitespace.
                more, space = self.bytes_helper(value[key],
                                                object_numbers,
                                                False)
                result     += more

            # Whatever happens, close the dictionary.
            return (result + b">>", True)

        elif isinstance(value, bytes):
            # If we made a hex string, it'd be twice as long.
            hexlen  = len(value) * 2

            # The only way to know the length of the other kind of
            # string is to make one.
            string  = self.build_str(value)

            if hexlen < len(string):
                # If the hex string is shorter, build one and use it.
                return (b"<" + self.build_hexstr(value) + b">", True)

            else:
                # If the hex string isn't shorter, then we may as well
                # use the more human-readable string that we've already
                # gone through the work of creating.
                return (b"(" + string + b")", True)

        elif isinstance(value, PdfHex):
            # Same as bytes, except that I already know I want to return
            # a hex string.
            return (b"<" + self.build_hexstr(bytes(value)) + b">", True)

        elif isinstance(value, (PrePdfName, PdfName)):
            # If it's a name, we start with a delimiter, so we don't
            # need to worry about space. However, we also end with a
            # regular character, so we might need space later.
            return (bytes(value), False)

        else:
            raise Exception("??????")

    def simple_bytes_helper (self,
                             value,
                             object_numbers     = { },
                             already_has_space  = True):
        return self.bytes_helper(value,
                                 object_numbers,
                                 already_has_space)[0]

    def content_stream (self, content, resources = { }):
        # Start with an empty string.
        result = b""

        for start, end, section in content.sections:
            # Add the beginning marker for each section and also get its
            # particular expected-resource dictionary.
            result     += start + b"\n"
            current_exp = content.expected_resources[start]

            for operator, args in section:
                # Get the expected resource dictionary for each
                # operator.
                res_ref = current_exp.get(operator, { })

                for i in range(len(args)):
                    # Get each argument to each operator.
                    value   = args[i]

                    if i in res_ref:
                        # If this particular argument should name an
                        # external object, we need to check whether that
                        # object has changed names. If it has, it'll be
                        # in the resources dictionary.
                        value = resources.get((res_ref[i], value),
                                              value)

                    # Either way, we want to append its export value to
                    # our result.
                    result += b"\t" + self.simple_bytes_helper(value)

                # Now that the operands are all there, we can also
                # append the operator. It gets a linefeed as well.
                result += b"\t" + operator + b"\n"

            # We're done with the section! Append the section end
            # marker.
            result     += end + b"\n"

        return result

    def build_hexstr (self, string):
        # Each byte is a two-digit hexadecimal. Easy.
        return "".join("{:02x}".format(x) \
                for x in string).encode("ascii")

    def build_str (self, string):
        # We escape all the backslashes before we create any additional
        # ones.
        string  = string.replace(b"\\", b"\\\\")

        for key, value in self.string_escapes.items():
            # Make all the easy escapes first.
            string  = string.replace(key, value)

        # Escape any invisible characters followed by octal digits.
        string  = self.re_long_octal.sub(self.octal_long_escape, string)

        # Replace all other invisible characters.
        string  = self.re_any_octal.sub(self.octal_short_escape, string)

        # All that's left is dealing with parentheses. Those are far
        # more complicated. At its core, I need to escape any unmatched
        # parentheses. I could simply escape all parentheses, but that
        # makes the file unnecessarily larger. So I need to find any and
        # all parentheses that I can't match.
        left    = string.find(b"(")
        right   = string.find(b")")

        # I'll track left parentheses in a stack. That way, whenever I
        # find a right parenthesis, I can just pop the closest left from
        # the stack. Also, if I'm done finding right parentheses, I'll
        # have a stack of unmatched left parentheses to escape.
        lefts   = deque()

        # I'll also track my position.
        pointer = 0

        while left != -1:
            # I start by finding all the left parentheses.
            if right == -1:
                # If there are no right parentheses left, I can use a
                # more streamlined mini-loop to finish this one off.
                while left != -1:
                    # No need to check anything about right parentheses;
                    # I already know there aren't any more. Just keep
                    # adding lefts.
                    lefts.append(left)
                    pointer = left + 1
                    left    = string.find(b"(", pointer)

            elif left < right:
                # We've got indeces for left and right parentheses, and
                # the left one comes first. Ignore the right one for now
                # and push the left one onto our stack.
                lefts.append(left)
                pointer = left + 1
                left    = string.find(b"(", pointer)

            elif len(lefts) > 0:
                # We've got indeces for both types of parenthesis, and
                # the right one comes first, and we have at least one
                # left parenthesis in our stack. We can pop it out and
                # ignore this right parenthesis.
                lefts.pop()
                pointer = right + 1
                right   = string.find(b")", pointer)

            else:
                # We've got indeces for both types of parenthesis, and
                # the right one comes first, but our lefts stack is
                # empty. We need to escape this right parenthesis. Since
                # we're adding a single byte (the backslash), we'll need
                # to add two (instead of one) to our pointer.
                string  = string[:right] + b"\\" + string[right:]
                pointer = right + 2
                right   = string.find(b")", pointer)

                # Again, we're adding a byte, so we need to alter the
                # index of the next left parenthesis.
                left   += 1

        # There are no more left parentheses in the string. That doesn't
        # mean we're out of right parentheses though!
        while right != -1:
            if len(lefts) > 0:
                # We have a right parenthesis and a stack with left
                # parentheses. We'll pop one off the stack to match, and
                # then we can ignore them both.
                lefts.pop()
                pointer = right + 1
                right   = string.find(b")", pointer)

            else:
                # We're out of left parentheses entirely, and we still
                # have at least one right parenthesis to contend with.
                # Instead of the usual one-at-a-time replacement, we can
                # safely batch replace all that are left.
                string  = string[:pointer] + \
                          string[pointer:].replace(b")", b"\\)")

        for i in range(len(lefts)):
            # Because I'm popping off contents from right to left, I
            # don't have to worry about any of the indeces being made
            # incorrect by adding bytes. The goal here is to deal with
            # any and all left parentheses lacking matching right ones.
            left    = lefts.pop()
            string  = string[:left] + b"\\" + string[left:]

        if len(string) < self.short_string:
            # If our string is pretty short (arbitrarily defined), we'll
            # escape line feeds.
            return string.replace(b"\n", b"\\n")

        else:
            # If our string is longer, then line feeds will only make it
            # more readable.
            return string

    def octal_long_escape (self, match):
        # This is when a nonstandard ascii byte appears right before a
        # byte that could be an octal digit. In this case, I need to
        # unambiguously make the escape three digits (and also include
        # the rest of the match).
        return "\\{:03o}".format(match.group(1)[0]).encode("ascii") \
                + match.group(2)

    def octal_short_escape (self, match):
        # This is run after the long escape. Any remaining bytes that
        # need escaping won't be followed by misleading bytes, so I
        # don't need to worry about how long the escape itself is.
        return "\\{:o}".format(match.group(0)[0]).encode("ascii")

class PrePdf:
    def __init__ (self):
        # We have a simple dictionary of objects.
        self.objects    = { }

        # We always have a root and an info dict.
        self.root       = self.insert({"Type": PrePdfName("Catalog")})
        self.info       = self.insert({ })

    def insert (self, value):
        # Generate a new key.
        new_key = gen_uuid().int

        while new_key in self.objects:
            # Ensure that it's not already taken (very unlikely).
            new_key = gen_uuid().int

        # Insert the value as a pre-PDF object.
        self.objects[new_key] = PrePdfObject(value)

        return new_key

    def __setitem__ (self, key, value):
        if key in self.objects:
            # If the key's already there, go ahead and modify the
            # object.
            self.objects[key].modify(value)

        else:
            # If it isn't, we don't allow insertions with this method.
            raise KeyError("Must insert items with `insert`.")

    def __getitem__ (self, key):
        # Just get the dang value.
        self.objects[key].modified = True
        return self.objects[key].value

    def __delitem__ (self, key):
        # This does nothing to remove references. You probably should
        # not use this ever.
        del self.objects[key]

    def __len__ (self):
        return len(self.objects)
    def __iter__ (self):
        return objects.keys()
    def __contains__ (self, key):
        return key in self.objects

    def write (self, filename):
        outfile = open(filename, "wb")
        outfile.write("%PDF-1.5\n%\U0001f46e\n".encode("utf_8"))

        numbers = self.get_object_numbers()

        xrefmap = { }
        size    = 1

        for uuid, ref in numbers.items():
            num, gen    = ref
            offset      = outfile.tell()

            if num >= size:
                size = num + 1

            xrefmap[num]   = (offset, gen)

            outfile.write("{:d} {:d} obj\n".format(
                            num, gen).encode("ascii"))

            self.objects[uuid].write(outfile, numbers)

            oudfile.write(b"\nendobj\n")

        free    = [ ]
        for i in range(size):
            if i not in xrefmap:
                free.append(i)

        free.append(free.pop(0))

        xref    = [ ]
        for i in range(size):
            if i in xrefmap:
                offset, gen = xrefmap[i]
                xref.append((offset, gen, "n"))

            else:
                xref.append((free.pop(0), 0xffff, "f"))

        startxref   = outfile.tell()
        outfile.write(b"xref\n")
        outfile.write("{:d} {:d}\n".format(
                        0, len(xref)).encode("ascii"))

        for line in xref:
            outfile.write("{:010d} {:05} {} \n".format(
                            *line).encode("ascii"))

        outfile.write(b"trailer\n")
        PrePdfObject({
            "Size": size,
            "Root": PrePdfReference(self.root),
            "Info": PrePdfReference(self.info),
            "ID":   [ "this ain't right yet" ]}).write(outfile, numbers)

        outfile.write("\nstartxref\n{:d}\n%%EOF\n".format(
                        startxref).encode("ascii"))
        outfile.close()

    def get_object_numbers (self):
        # Make a set of remaining keys.
        keys    = set(self.objects)

        # We'll start by building an ordered list.
        ordered = [ ]

        # Add our root, then our info dict.
        self.number_key(keys, ordered, self.root)
        self.number_key(keys, ordered, self.info)

        for value in self[self.root].values():
            # For each item linked in our root, check for children.
            self.object_number_helper(self, keys, ordered, value)

        for key in keys:
            # Last, add any keys we didn't find in the object tree.
            ordered.append(key)

        # We want to return a dictionary.
        result  = { }

        # We'll increment numbers.
        number  = 0
        for key in ordered:
            # Increment and assign our number.
            number     += 1
            result[key] = (number, 0)

        return result

    def object_number_helper (self, key_set, ordered_list, value):
        if isinstance(value, PrePdfReference):
            # If it's a reference, I need to give it a number.
            self.number_key(key_set, ordered_list, value.uuid)

            # I also need to pull its value and run recursively, in case
            # there's more to do on it.
            self.object_number_helper(key_set,
                                      ordered_list,
                                      self[value.uuid])

        elif isinstance(value, dict):
            for item in value.values():
                self.object_number_helper(key_set, ordered_list, item)

        elif isinstance(value, list):
            for item in value:
                self.object_number_helper(key_set, ordered_list, item)

    def number_key (self, key_set, ordered_list, key):
        # Only number the key if it hasn't yet been numbered.
        if key in self.key_set:
            key_set.remove(key)
            ordered_list.append(key)
