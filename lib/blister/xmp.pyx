# Copyright (c) 2017 The Regents of the University of Michigan.
# All Rights Reserved. Licensed according to the terms of the Revised
# BSD License. See LICENSE.txt for details.

class XMP:

    def __bool__ (self):
        return False

    def __len__ (self):
        return 0

    def __repr__ (self):
        return "<{}>".format(self.__class__.__name__)
