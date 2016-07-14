# Copyright (c) 2015 The Regents of the University of Michigan.
# All Rights Reserved. Licensed according to the terms of the Revised
# BSD License. See LICENSE.txt for details.
from .reader    import  IFDTag, IFDCompression, IFDExtraSamples,    \
                        IFDFillOrder, IFDOrientation,               \
                        IFDPhotometricInterpretation,               \
                        IFDPlanarConfiguration, IFDResolutionUnit,  \
                        IFDSubfileType, IFDThresholding, Tiff

__all__ = [
    "IFDTag",
    "IFDCompression",
    "IFDExtraSamples",
    "IFDFillOrder",
    "IFDOrientation",
    "IFDPhotometricInterpretation",
    "IFDPlanarConfiguration",
    "IFDResolutionUnit",
    "IFDSubfileType",
    "IFDThresholding",
    "Tiff",
]
