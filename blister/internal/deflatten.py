# Copyright (c) 2015 The Regents of the University of Michigan.
# All Rights Reserved. Licensed according to the terms of the Revised
# BSD License. See LICENSE.txt for details.

def deflatten (*args, **kwargs) -> iter:
    """Deflatten a flat iterable into an iterable of tuples.

    Args:
        size (Optional[int]):   The size of each tuple you wish to
                                iterate through. Defaults to 2.

        iterable (Iterable):    The flat container to iterate over.

        default (Optional):     If set, the final tuple will be padded
                                out with these. If not, the final tuple
                                will be skipped (unless it's full of
                                valid values).

                                If given as a nonkeyword argument, the
                                size must be explicitly set.

    Yields:
        tuple:                  A tuple of elements from iterable.

    Examples:
        By default, it'll iterate in 2-tuples:

        >>> arr = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
        >>> for i, j in deflatten(arr):
        ...     print(i, j)
        ... 
        0 1
        2 3
        4 5
        6 7
        8 9
        10 11

        Optionally, you can specify a size:

        >>> for i, j, k in deflatten(3, arr):
        ...     print(i, j, k)
        ... 
        0 1 2
        3 4 5
        6 7 8
        9 10 11

        If you don't specify a default value, any extra items will be
        silently skipped:

        >>> for i, j, k, l, m in deflatten(5, arr):
        ...     print(i, j, k, l, m)
        ... 
        0 1 2 3 4
        5 6 7 8 9

        Otherwise, if you do specify a default value, then the final
        tuple will be filled in if and as necessary:

        >>> for i, j, k, l, m in deflatten(5, arr, "default"):
        ...     print(i, j, k, l, m)
        ... 
        0 1 2 3 4
        5 6 7 8 9
        10 11 default default default

    """

    # By default, assume a tuple size of two and no default value.
    size            = 2
    has_default     = False

    # What happens next depends on how many arguments I got.
    argcount        = len(args)

    if argcount == 1:
        # If there's just the one argument, it's the iterable.
        iterable    = args[0]

    elif argcount > 1:
        # If there are more arguments, the first is the tuple size, and
        # the second is the iterable.
        size        = args[0]
        iterable    = args[1]

        if argcount > 2:
            # If there's a third argument, then it's the default.
            has_default = True
            default     = args[2]

            if argcount > 3:
                # If there's a fourth argument, then there's a problem.
                raise TypeError("deflatten() takes at most 3" \
                        " arguments ({:d} given)".format(argcount))

    elif len(kwargs) == 0:
        # If we've been given no arguments, then that's a problem.
        raise TypeError("deflatten() takes at least 1 argument" \
                " (0 given)")

    if "iterable" in kwargs:
        # If we've been given a keyworded iterable, use it.
        iterable    = kwargs["iterable"]

    elif argcount < 1:
        # We need an iterable.
        raise TypeError("deflatten() must take an iterable")

    # Replace the size if there's a keyword for it.
    size = kwargs.get("size", size)

    if "default" in kwargs:
        # If there's a keyworded default, use it.
        has_default = True
        default     = kwargs["default"]

    # We want the actual iterator.
    obj = iter(iterable)

    if has_default:
        # If we have a default element, we'll pass it to `next`.
        next_args = (obj, default)

    else:
        # Otherwise, `next` will just be given the iterator.
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
