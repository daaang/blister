# Copyright (c) 2015 The Regents of the University of Michigan.
# All Rights Reserved. Licensed according to the terms of the Revised
# BSD License. See LICENSE.txt for details.
from sys    import  version_info

if version_info[0] > 2:
    # These are all pretty straightforward in python 3.
    def int_to_bytes (integer, length, byte_order):
        return integer.to_bytes(length, byte_order)
    def bytes_to_int (bytestring, byte_order):
        return int.from_bytes(bytestring, byte_order)
    def hex_to_bytes (hexstring):
        return bytes.fromhex(hexstring)

else:
    # None of them really exist in the same way, in python 2.
    class ByteOrder:
        BIG     = "big"
        LITTLE  = "little"

    def int_to_bytes (integer, length, byte_order):
        # We take in an integer, a desired result length, and the byte
        # order. We'll be returning a byte string.
        result = bytes()

        while integer > 0:
            # While we still have an integer, keep appending bytes.
            result += bytes([integer % 0x100])
            integer //= 0x100

        # If the result isn't long enough, append zeros until it is.
        result += bytes(length - len(result))

        if byte_order == ByteOrder.BIG:
            # It's currently in little-endian order, so we'll have to
            # reverse it.
            return result[::-1]

        # Otherwise, we'll keep it in little-endian order.
        return result

    def bytes_to_int (bytestring, byte_order):
        # We'll be processing a bytestring in big endian order.
        if byte_order == ByteOrder.LITTLE:
            # The bytestring is in little endian order, so we'll begin
            # by reversing it.
            bytestring = bytestring[::-1]

        # Start with zero.
        result = 0

        for byte in bytestring:
            # For each byte, we increase our result.
            result *= 0x100
            result += ord(byte)

        return result

    def hex_to_bytes (hexstring):
        # Python 2 doesn't have the bytes type, but it does have a `hex`
        # encoding attached to strings. Before that works, we'll need to
        # get rid of any whitespace.
        return hexstring.replace(" ", "").decode("hex")
