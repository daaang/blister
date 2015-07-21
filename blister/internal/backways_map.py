# Copyright (c) 2015 The Regents of the University of Michigan.
# All Rights Reserved. Licensed according to the terms of the Revised
# BSD License. See LICENSE.txt for details.

def make_backways_map (enum_class):
    """Make a backways value mapping.

    This takes in what is basically an enum class and constructs a
    dictionary keyed on the values. Its values will be the associated
    name strings.

    The point of this is to be pretty more than anything else.

    Args:
        enum_class (class): The class to make a reverse mapping of.

    Returns:
        dict:               A mapping with keys matching the values of
                            the class. Its values will match the class
                            variable names.

    Examples:
        Here's an example enumeration.

        >>> class SomeEnum:
        ...     ThingOne    = 1
        ...     ThingTwo    = 2
        ...     ThingThree  = 3
        ... 
        >>> make_backways_map(SomeEnum)
        {1: "ThingOne", 2: "ThingTwo", 3: "ThingThree"}

        Collisions in enum values are not allowed.

        >>> class BadEnum:
        ...     ThingOne        = 1
        ...     AnotherThingOne = 1
        ...     ThingTwo        = 2
        ... 
        >>> make_backways_map(BadEnum)
        Traceback (most recent call list):
          File "<stdin>", line 1, in <module>
        AssertionError: Can't have more than one 1 (BadEnum.ThingOne and
                BadEnum.AnotherThingOne)

    """

    # We're making a dictionary.
    result  = { }

    # Here's the super-informative error message we'll give if there's a
    # collision.
    error   = "Can't have more than one {{:d}} ({name}.{{}} and" \
              " {name}.{{}})".format(name = enum_class.__name__).format

    for key, value in vars(enum_class).items():
        # Look at each key-value pair.
        if key.startswith("_"):
            # All the regular python stuff starts with underscores.
            # Ignore it.
            continue

        # We're gonna use the values as keys. If this one's already in
        # there, then we have a collision. Report all nice-like.
        assert value not in result, error(value, result[value], key)

        # Nice! Add the pair.
        result[value] = key

    # Now we can return this happy dictionary.
    return result
