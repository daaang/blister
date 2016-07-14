# Copyright (c) 2015 The Regents of the University of Michigan.
# All Rights Reserved. Licensed according to the terms of the Revised
# BSD License. See LICENSE.txt for details.
from collections        import  OrderedDict

from .boxed_file_reader import  BoxedFile
from .boxes             import  SuperBox

class Jpeg2000 (SuperBox):
    def __init__ (self, file_object):
        # We'll initialize the file object, since this is our first time
        # looking at it.
        self.jp2    = BoxedFile(file_object)
        self.initialize_data()

        # Give a junk length that will ultimately be ignored.
        self.pull_box_data(0)

    def find_boxes (self, max_pos):
        # We'll ignore the max_pos parameter, since, in this case, we're
        # reading to the end of the file. We'll also go ahead and start
        # at the zero offset.
        boxes = [ ]
        self.jp2.seek(0)

        while True:
            # Try to read a box.
            box = self.jp2.try_to_read_new_box()

            if box is not None:
                # If we succeeded, add the box.
                boxes.append(box)

                if box.length is not None:
                    # We only continue the loop (a) if we got a box and
                    # (b) if that box has a length.
                    continue

            # Otherwise, we exit the loop.
            break

        # Return the list.
        return boxes
