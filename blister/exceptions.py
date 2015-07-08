class BlisterException (Exception):
    pass

class FileReadError (BlisterException):
    def __init__ (self, position, message):
        self.position   = position
        self.message    = message

    def __str__ (self):
        return "{} (0x{:08x})".format(str(self.message),
                                      self.position)
