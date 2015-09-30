# Copyright (c) 2015 The Regents of the University of Michigan.
# All Rights Reserved. Licensed according to the terms of the Revised
# BSD License. See LICENSE.txt for details.
from zlib   import  compress as zlib_compress

def encode_ASCII85 (message):
    cols        = 72
    base        = 85
    zero        = b"!"[0]
    z_byte      = b"z"

    group_width = 4
    message_len = len(message)
    groups      = message_len // group_width
    final_group = message_len % group_width
    even_last   = groups * group_width

    result      = b""
    for i in range(0, even_last, group_width):
        total   = int.from_bytes(message[i:i+group_width], "big")

        if total == 0:
            result += z_byte
            continue

        five    = [ ]
        for j in range(5):
            digit   = total % base + zero
            total //= base

            five.insert(0, digit)

        result += bytes(five)

    if final_group > 0:
        missing = group_width - final_group
        group   = message[even_last:] + bytes([0] * missing)
        total   = int.from_bytes(group, "big")

        five    = [ ]
        for j in range(5):
            digit   = total % base + zero
            total //= base

            five.insert(0, digit)

        result += bytes(five[:missing+1])

    lines   = [ ]
    for i in range(0, len(result), cols):
        lines.append(result[i:i+cols])

    return b"\n".join(lines) + b"~>"

def encode_Flate (message):
    return zlib_compress(message, 9)
