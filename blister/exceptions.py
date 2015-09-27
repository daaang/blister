# Copyright (c) 2015 The Regents of the University of Michigan.
# All Rights Reserved. Licensed according to the terms of the Revised
# BSD License. See LICENSE.txt for details.

class BlisterBaseError (Exception):
    """Root for all Blister errors.

    Note:
        This is meant to never be raised directly. Only its descendents
        will be raised; this is meant only to be caught.

    Examples:
        For the sake of clarity, all child exceptions default to showing
        the docstring if ever converted to strings.

        >>> class MyBlisterError (BlisterBaseError):
        ...     '''Quick description of this subclass.'''
        ...     pass
        ... 
        >>> raise MyBlisterError
        Traceback (most recent call last):
          File "<stdin>", line 1, in <module>
        MyBlisterError: Quick description of this subclass.

    """

    def __repr__ (self):
        # Assume the child exception class has implemented its own
        # __str__ method. If not, this'll look much the same as any
        # other python exception.
        return "{}({})".format(self.__class__.__name__, repr(str(self)))

    def __str__ (self):
        # By default, let's just keep our docstrings short.
        return self.__doc__

class FileReadError (BlisterBaseError):
    """File Read Error

    Something unexpected has happened while reading a file.

    Note:
        This is meant to never be raised directly. Only its descendents
        will be raised; this is meant only to be caught.

    Args:
        position (int):     The byte in the file.

    Examples:
        >>> two_fifty_six = UnexpectedEOF(256)
        >>> two_fifty_six
        UnexpectedEOF('Unexpected end of file. (0x00000100)')
        >>> str(two_fifty_six)
        'Unexpected end of file. (0x00000100)'
        >>> raise two_fifty_six
        Traceback (most recent call last):
          File "<stdin>", line 1, in <module>
        UnexpectedEOF: Unexpected end of file. (0x00000100)

        As you can see, the message is already set, and the output
        contains an eight-digit hexadecimal pointing (in theory) to the
        exact byte in the file where the problem occurred.

    """

    def __init__ (self, position, *args):
        # All I want to actually take in is a positional argument; the
        # message should be set by the child class.
        self.position   = position
        self.args       = args

    def __str__ (self):
        # After displaying the message, display the relevant position in
        # the file.
        return "{} (0x{:08x})".format(self.__doc__.format(*(self.args)),
                                      self.position)

class UnexpectedEOF (FileReadError):
    """Unexpected end of file."""
    pass

class TiffError (FileReadError):
    """Catch-all for tiff errors."""
    pass

class TiffUnknownByteOrder (TiffError):
    """Unknown byte order: {}"""
    pass

class TiffWrongMagicNumber (TiffError):
    """Wrong magic number: expected {:d}; found {:d}"""
    pass

class TiffFirstIFDOffsetTooLow (TiffError):
    """IFD offset must be at least {:d}; I was given {:d}"""
    pass

class TiffEmptyIFD (TiffError):
    """IFD {:d} must have at least one entry."""
    pass

class TiffDuplicateTag (TiffError):
    """Tag {:d} ({}) is already in IFD {:d}; no duplicates allowed."""
    pass

class TiffOffsetsWithoutBytecounts (TiffError):
    """Can't have tag {:d} ({}) without also having tag {:d} ({})."""
    pass

class TiffOffsetsDontMatchBytecounts (TiffError):
    """Array lengths must match between tags {:d} ({}) and {:d} ({})."""
    pass

class TiffFloatError (TiffError):
    """I don't know how to make a float {:d} byte{} long."""
    pass

class Jpeg2000Error (FileReadError):
    """Catch-all for jp2 errors."""
    pass

class Jpeg2000DuplicateKey (Jpeg2000Error):
    """Key {} appears more than once even though it shouldn't."""
    pass

class Jpeg2000CodeStreamError (Jpeg2000Error):
    """Catch-all for code stream errors."""
    pass

class Jpeg2000NoSOCMarker (Jpeg2000CodeStreamError):
    """Code stream didn't begin with the required SOC marker."""
    pass

class Jpeg2000NoSIZMarker (Jpeg2000CodeStreamError):
    """Code stream's second marker isn't SIZ, as is required."""
    pass

class Jpeg2000UnknownSubBlock (Jpeg2000CodeStreamError):
    """Unknown sub-block within {}, named {}."""
    pass

class Jpeg2000SIZIncorrectLength (Jpeg2000CodeStreamError):
    """Lsiz value ({:d}) does not match actual SIZ length ({:d})."""
    pass

class Jpeg2000SIZParameterTooSmall (Jpeg2000CodeStreamError):
    """SIZ parameter {} cannot be less than {:d} ({:d} given)."""
    pass

class Jpeg2000SIZParameterTooLarge (Jpeg2000CodeStreamError):
    """SIZ parameter {} must be less than {:d} ({:d} given)."""
    pass
