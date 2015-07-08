# Copyright (c) 2015 The Regents of the University of Michigan.
# All Rights Reserved. Licensed according to the terms of the Revised
# BSD License. See LICENSE.txt for details.
from io             import BytesIO, BufferedReader, SEEK_END

class ByteOrder:
    BIG     = "big"
    LITTLE  = "little"

########################################################################
################################ 2 to 3 ################################
########################################################################
############ Also, be sure to run on the command line:      ############
############                                                ############
############   $ sed -i -e 's/assertRaisesRegex/&p/' [file] ############
########################################################################

file = BufferedReader

def int_to_bytes (integer, length, byte_order):
    #result = ""
    #while integer > 0:
        #result += chr(integer % 0x100)
        #integer //= 0x100
    #result += "\0" * (length - len(result))
    #if byte_order == ByteOrder.BIG:
        #return result[::-1]
    #return result
    return integer.to_bytes(length, byte_order)

def bytes_to_int (bytestring, byte_order):
    #if byte_order == ByteOrder.LITTLE:
        #bytestring = bytestring[::-1]
    #result = 0
    #for byte in bytestring:
        #result *= 0x100
        #result += ord(byte)
    #return result
    return int.from_bytes(bytestring, byte_order)

def hex_to_bytes (hexstring):
    #return hexstring.replace(" ", "").decode("hex")
    return bytes.fromhex(hexstring)

def deflatten (*args, **kwargs):
    size            = 2
    has_default     = False

    if len(args) == 1:
        iterable    = args[0]

    elif len(args) > 1:
        size        = args[0]
        iterable    = args[1]

        if len(args) > 2:
            has_default = True
            default     = args[2]

    size = kwargs.get("size", size)

    if "iterable" in kwargs:
        iterable    = kwargs["iterable"]

    if "default" in kwargs:
        has_default = True
        default     = kwargs["default"]

    # We want the actual iterator.
    obj = iter(iterable)

    if has_default:
        next_args = (obj, default)
    else:
        next_args = (obj,)

    while True:
        # For each grouping, we construct a list that holds at least one
        # element from the iterable. We ignore defaults at this point,
        # since this is the ideal stopping point.
        result = [next(obj)]

        for i in range(1, size):
            # For the rest of the items in the group, I'll allow a
            # default value (if a default was given).
            result.append(next(*next_args))

        # We want a tuple; not a list.
        yield tuple(result)
