# Copyright (c) 2015 The Regents of the University of Michigan.
# All Rights Reserved. Licensed according to the terms of the Revised
# BSD License. See LICENSE.txt for details.

# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs     import open
from os         import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the relevant file
with open(path.join(here, "DESCRIPTION.rst"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name                = "blister",
    version             = "0.1.0",
    description         = "PDF/A generation",
    long_description    = long_description,
    url                 = "https://github.com/daaang/blister",
    author              = "Matt LaChance",
    author_email        = "mattlach@umich.edu",
    license             = "BSD",
    packages            = ["blister"],

    # https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers         = [
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "Topic :: Text Processing :: General",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.3",
    ],
)
