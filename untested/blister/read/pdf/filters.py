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

def png_decode_row (row, filter_id, previous_row, bpc):
    if filter_id == 0:
        # Before we do anything else, just check what's up with the
        # filter id. If it's zero, we don't have to even do a thing.
        return row

    # Otherwise, we need to prepare for a result row that looks
    # different from the one we've been given. We'll start with some
    # zero bytes that will be removed.
    result = [0] * bpc

    if filter_id == 1:
        for sub in row:
            # It's a Sub filter, which means I should add the value of
            # the corresponding byte of the previous component. If we're
            # not yet far enough in the row for there to have been a
            # previous component, then that's what those zero bytes were
            # for.
            result.append((sub + result[-bpc]) % 0x100)

    elif filter_id == 2:
        i = 0
        for sub in row:
            # It's an Up filter, which means we add the value of the
            # byte directly above this one, in the previous row.
            result.append((sub + previous_row[i]) % 0x100)
            i += 1

    elif filter_id == 3:
        i = 0
        for sub in row:
            # It's an Average filter, which means we add the floored
            # mean of the left and upper bytes.
            result.append((sub + ((result[-bpc] + previous_row[i])
                                  // 2)) % 0x100)
            i += 1

    elif filter_id == 4:
        # The Paeth filter is the most complicated. I actually split it
        # into two loops in order to simplify the process.
        i = 0
        for sub in row[:bpc]:
            # The first loop is through the bytes in the first
            # component. For these, the values of the "left" and "upper
            # left" bytes will default to zero, so the Paeth predictor
            # will equal the "above" byte. Therefore, the Paeth value
            # will also equal the "above" byte. So, for the bytes in
            # this component, this is the same as the Up filter.
            result.append((sub + previous_row[i]) % 0x100)
            i += 1

        for sub in row[bpc:]:
            # We want three bytes near this one.
            left        = result[-bpc]
            above       = previous_row[i]
            upper_left  = previous_row[i - bpc]

            # Calculate our predictor value and figure out how close it
            # is to each of those bytes.
            predictor   = left + above - upper_left
            dleft       = abs(predictor - left)
            dabove      = abs(predictor - above)
            dupper_left = abs(predictor - upper_left)

            if dleft <= dabove and dleft <= dupper_left:
                # The left value is closest.
                paeth   = left

            elif dabove <= dupper_left:
                # The above value is closest.
                paeth   = above

            else:
                # The upper-left value is closest.
                paeth   = upper_left

            # We add the paeth value.
            result.append((sub + paeth) % 0x100)

            i += 1

    else:
        raise Exception("There is no PNG type-{:d} filter".format(
                        filter_id))

    # Be sure to remove the zero-component we started with.
    return bytes(result[bpc:])

def decode_Flate (encoded_bytes, parms = { }):
    # First we decompress the string. That's probably all we'll need to
    # do.
    result  = zlib_decompress(encoded_bytes)

    # Get decode parameters.
    predictor   = parms.get("Predictor",        1)
    bpc         = parms.get("BitsPerComponent", 8)
    columns     = parms.get("Columns",          1)

    if predictor < 10:
        # We only care whether the predictor is under 10 or not. If it
        # is, we can return the data as-is.
        return result

    # Ok! Looks like our message was also filtered before its
    # compression. So our result is still encoded.
    png_encoded = result

    result      = b""

    # Our filtered data has a total length and its own row length one
    # greater than that of our resulting data.
    png_all_len = len(png_encoded)
    png_row_len = columns + 1

    # We need at least one column. We also need the result to be a
    # length that can divide evenly into rows.
    assert columns > 0
    assert png_all_len % png_row_len == 0

    # We'll start with a row of zeroes that we won't actually add to our
    # result. You know, just in case.
    row         = bytes(png_row_len)

    for i in range(0, png_all_len, png_row_len):
        # Decode the thing row-by-row.
        row     = png_decode_row(png_encoded[i+1:i+png_row_len],
                                 png_encoded[i],
                                 row,
                                 bpc)
        result += row

    return result
