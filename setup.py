# Copyright (c) 2017 The Regents of the University of Michigan.
# All Rights Reserved. Licensed according to the terms of the Revised
# BSD License. See LICENSE.txt for details.
from setuptools import setup
from os import walk
from os.path import abspath, dirname, join
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

base_dir = get_path_to_base_directory()
long_desc = get_file_contents(base_dir, "README.rst")

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
        " :: ".join(("Programming Language", "C")),
        " :: ".join(("Programming Language", "Cython")),
        " :: ".join(("Programming Language", "Python", "3", "Only")),
        " :: ".join(("Topic", "Multimedia",
                     "Graphics", "Graphics Conversion")),
    ],

    packages=["blister"],
    package_dir={"": "lib"},
    ext_modules=get_ext_modules("lib/blister"),
)
