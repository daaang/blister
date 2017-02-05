# Copyright (c) 2017 The Regents of the University of Michigan.
# All Rights Reserved. Licensed according to the terms of the Revised
# BSD License. See LICENSE.txt for details.
from setuptools import setup
from os import walk
from os.path import abspath, dirname, join
from re import compile as re_compile
from sys import version_info
from Cython.Build import cythonize

class DevelopmentStatus:

    planning = "1 - Planning"
    pre_alpha = "2 - Pre-Alpha"
    alpha = "3 - Alpha"
    beta = "4 - Beta"
    stable = "5 - Production/Stable"
    mature = "6 - Mature"
    inactive = "7 - Inactive"

CURRENT_STATUS = DevelopmentStatus.planning
RE_PYTHON_FILE = re_compile(r"^.*\.pyx?$")

def get_path_to_base_directory():
    return abspath(dirname(__file__))

def get_file_contents(*args):
    with open(join(*args)) as the_file:
        result = the_file.read()

    return result

def get_ext_modules(base_dir):
    results = [ ]

    for root, dirs, filenames in walk(base_dir):
        for filename in filenames:
            if filename.endswith(".pyx"):
                results.append(join(root, filename))

    if results:
        return cythonize(results)

def maybe_replace_collections_abc (path):
    with open(path, "r") as f:
        contents = f.read()

    if "collections.abc" in contents:
        with open(path, "w") as f:
            f.write(contents.replace("collections.abc", "collections"))

def make_valid_for_3_2 (lib_dir):
    for root, dirs, filenames in walk(lib_dir):
        for filename in filenames:
            match = RE_PYTHON_FILE.match(filename)
            if match is None:
                continue

            maybe_replace_collections_abc(join(root, filename))

base_dir = get_path_to_base_directory()
long_desc = get_file_contents(base_dir, "README.rst")

if version_info < (3, 3):
    make_valid_for_3_2(join(base_dir, "lib"))

setup(
    name="Blister",
    version="1.0.0.dev0",
    description="Preservation-grade conversion between images",
    long_description=long_desc,
    license="BSD-3-Clause",
    author="Matt LaChance",
    author_email="mattlach@umich.edu",

    classifiers=[
        " :: ".join(("Development Status", CURRENT_STATUS)),
        " :: ".join(("License", "OSI Approved", "BSD License")),
        " :: ".join(("Natural Language", "English")),
        " :: ".join(("Programming Language", "Cython")),
        " :: ".join(("Programming Language", "Python", "3", "Only")),
        " :: ".join(("Topic", "Multimedia",
                     "Graphics", "Graphics Conversion")),
    ],

    packages=["blister", "blister.xmp"],
    package_dir={"": "lib"},
    ext_modules=get_ext_modules("lib/blister"),
)
