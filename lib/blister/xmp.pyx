# Copyright (c) 2017 The Regents of the University of Michigan.
# All Rights Reserved. Licensed according to the terms of the Revised
# BSD License. See LICENSE.txt for details.

cdef set DEFAULT_XMP_NAMESPACES = {
    "stRef",
    "dc",
    "xmp",
    "xmpRights",
    "xmpMM",
    "xmpidq",
    "exifEX",
    "exif",
    "tiff",
}

cdef class XMP:

    def __len__ (self):
        return 0

    def __iter__ (self):
        return iter(())

    def __getattr__ (self, name):
        if name in DEFAULT_XMP_NAMESPACES:
            return ()

        else:
            self.raise_error_no_attr(name)

    def __getitem__ (self, key):
        raise KeyError

    def __repr__ (self):
        return "<{}>".format(self.__class__.__name__)

    cdef raise_error_no_attr (self, name):
        obj = "{}.{}".format(self.__class__.__module__,
                             self.__class__.__name__)

        message = "{} object has no attribute {}".format(repr(obj),
                                                         repr(name))

        raise AttributeError(message)
