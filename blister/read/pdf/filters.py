# Copyright (c) 2015 The Regents of the University of Michigan.
# All Rights Reserved. Licensed according to the terms of the Revised
# BSD License. See LICENSE.txt for details.
from re             import  compile as re_compile
from zlib           import  decompress as zlib_decompress

re_whitespace   = re_compile(rb"[\x00\r\n\t\f ]")
re_base85       = re_compile(rb"[^!-uz]")

def decode_ASCIIHex (encoded_bytes, parms = { }):
    # Look for an EOD marker.
    eod_marker      = encoded_bytes.find(b">")

    if eod_marker > -1:
        # If we find one, ignore anything and everything following it.
        encoded_bytes   = encoded_bytes[:eod_marker]

    # Strip any and all whitespace.
    no_whitespace   = re_whitespace.sub(encoded_bytes, b"")

    if len(no_whitespace) % 2 == 1:
        # If there's an odd number of bytes, append a zero.
        no_whitespace   += b"0"

    return bytes.fromhex(no_whitespace.decode("ascii"))

def decode_ASCII85 (encoded_bytes, parms = { }):
    # We're in base 85 and our "zero" digit is `!`.
    base            = 85
    zero            = b"!"[0]

    # `z` is a special byte indicating four bytes of 0, so be ready for
    # that.
    z_byte          = b"z"[0]
    four_zeroes     = bytes([0, 0, 0, 0])
    four            = len(four_zeroes)

    # If we don't get `z`, we'll be evaluating 5-byte chunks of data,
    # each a digit. Here are some prepared multipliers for those.
    multipliers     = (base**4, base**3, base**2, base, 1)
    group_size      = len(multipliers)

    # We'll start by looking for an EOD marker.
    eod_marker      = encoded_bytes.find(b"~>")

    if eod_marker > -1:
        # Found one! Remove anything and everything that follows.
        encoded_bytes   = encoded_bytes[:eod_marker]

    # Get rid of whitespace.
    no_whitespace   = re_whitespace.sub(encoded_bytes, b"")

    # Look for invalid characters.
    match           = re_base85.search(no_whitespace)

    if match is not None:
        # Don't even continue if there's a single out-of-place byte.
        raise Exception("Unexpected character")

    # Now we begin building our result string. We'll also want to
    # collect groups of bytes in a value array.
    result          = b""
    values          = [ ]

    for byte in no_whitespace:
        # For each byte, what we do depends on how many bytes we've
        # already collected.
        if len(values) == 0:
            # If we haven't collected any yet, then we should look out
            # for the special zero byte.
            if byte == z_byte:
                # Got one! Append four zeroes to it and skip the rest of
                # the loop logic.
                result += four_zeroes
                continue

            # Otherwise, it's a regular byte, and we should add it to
            # our list of values.
            values.append(byte - zero)

        else:
            # We already have at least one value in our list.
            if byte == z_byte:
                # If we find the special zero byte, something is wrong.
                # That can only exist outside of a group of five.
                raise Exception("z can't be part of a 5-group")

            # Go ahead and add this byte as well.
            values.append(byte - zero)

            if len(values) == group_size:
                # If we've made it to five in our group, it's time to
                # clear the thing out.
                total   = 0
                for i in multipliers:
                    # We can take advantage of that super-cool
                    # multiplier 5-tuple we made earlier.
                    total  += i * values.pop(0)

                # Python has its own int-to-bytes converter.
                result += total.to_bytes(four, "big")

    if len(values) != 0:
        # If there are still values in there, then we have a partial
        # group to look at. How many bytes are missing?
        missing = group_size - len(values)

        if missing >= four:
            # Not enough extra data to actually do anything with.
            raise Exception("4 missing bytes is too many")

        # Add zeroes as the missing values.
        values += [0] * missing

        # We build a total like normal, now that we have a group of 5
        # values for sure.
        total   = 0
        for i in multipliers:
            total  += i * values.pop(0)

        # We add this result *almost* like normal, except we strip off
        # the missing number of bytes.
        result += total.to_bytes(four, "big")[0:-missing]

    # If we made it to here, we have a decoded string. Awesome!
    return result

def decode_Flate (encoded_bytes, parms = { }):
    # I get to just use the library for this one! Easy.
    return zlib_decompress(encoded_bytes)
