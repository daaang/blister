# Copyright (c) 2017 The Regents of the University of Michigan.
# All Rights Reserved. Licensed according to the terms of the Revised
# BSD License. See LICENSE.txt for details.

cdef class XMP:

    def __len__ (self):
        return 0

    def __iter__ (self):
        return iter(())

    def __getattr__ (self, name):
        if name == "stRef":
            return ()

        else:
            self.__raise_no_attr(name)

    def __repr__ (self):
        return "<{}>".format(self.__class__.__name__)

    def __raise_no_attr (self, name):
        obj = "{}.{}".format(self.__class__.__module__,
                             self.__class__.__name__)

        message = "{} object has no attribute {}".format(repr(obj),
                                                         repr(name))

        raise AttributeError(message)
