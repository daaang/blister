# Copyright (c) 2017 The Regents of the University of Michigan.
# All Rights Reserved. Licensed according to the terms of the Revised
# BSD License. See LICENSE.txt for details.

class XMPNamespace:

    uri = None
    prefix = "uri-only"

    class NoURI (RuntimeError):
        pass

    def __init__ (self):
        if self.uri is None:
            raise XMPNamespace.NoURI

    def is_valid (self):
        return True

    def __bool__ (self):
        return False

    def __repr__ (self):
        return "<{}>".format(self.__class__.__name__)
