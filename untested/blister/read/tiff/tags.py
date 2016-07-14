# Copyright (c) 2015 The Regents of the University of Michigan.
# All Rights Reserved. Licensed according to the terms of the Revised
# BSD License. See LICENSE.txt for details.
from ...internal.backways_map import make_backways_map

class IFDTag:
    """IFD tags by name"""
    NewSubfileType              = 0x00fe
    SubfileType                 = 0x00ff

    ImageWidth                  = 0x0100
    ImageLength                 = 0x0101
    BitsPerSample               = 0x0102
    Compression                 = 0x0103
    PhotometricInterpretation   = 0x0106
    Thresholding                = 0x0107

    CellWidth                   = 0x0108
    CellLength                  = 0x0109
    FillOrder                   = 0x010a
    DocumentName                = 0x010d
    ImageDescription            = 0x010e
    Make                        = 0x010f

    Model                       = 0x0110
    StripOffsets                = 0x0111
    Orientation                 = 0x0112
    SamplesPerPixel             = 0x0115
    RowsPerStrip                = 0x0116
    StripByteCounts             = 0x0117

    MinSampleValue              = 0x0118
    MaxSampleValue              = 0x0119
    XResolution                 = 0x011a
    YResolution                 = 0x011b
    PlanarConfiguration         = 0x011c
    PageName                    = 0x011d
    XPosition                   = 0x011e
    YPosition                   = 0x011f

    FreeOffsets                 = 0x0120
    FreeByteCounts              = 0x0121
    GrayResponseUnit            = 0x0122
    GrayResponseCurve           = 0x0123
    T4Options                   = 0x0124
    T6Options                   = 0x0125

    ResolutionUnit              = 0x0128
    PageNumber                  = 0x0129
    TransferFunction            = 0x012d

    Software                    = 0x0131
    DateTime                    = 0x0132

    Artist                      = 0x013b
    HostComputer                = 0x013c
    Predictor                   = 0x013d
    WhitePoint                  = 0x013e
    PrimaryChromaticities       = 0x013f

    ColorMap                    = 0x0140
    HalftoneHints               = 0x0141
    TileWidth                   = 0x0142
    TileLength                  = 0x0143
    TileOffsets                 = 0x0144
    TileByteCounts              = 0x0145
    BadFaxLines                 = 0x0146
    CleanFaxData                = 0x0147

    ConsecutiveBadFaxLines      = 0x0148
    SubIFDs                     = 0x014a
    InkSet                      = 0x014c
    InkNames                    = 0x014d
    NumberOfInks                = 0x014e

    DotRange                    = 0x0150
    TargetPrinter               = 0x0151
    ExtraSamples                = 0x0152
    SampleFormat                = 0x0153
    SMinSampleValue             = 0x0154
    SMaxSampleValue             = 0x0155
    TransferRange               = 0x0156
    ClipPath                    = 0x0157

    XClipPathUnits              = 0x0158
    YClipPathUnits              = 0x0159
    Indexed                     = 0x015a
    JPEGTables                  = 0x015b
    OPIProxy                    = 0x015f

    GlobalParametersIFD         = 0x0190
    ProfileType                 = 0x0191
    FaxProfile                  = 0x0192
    CodingMethods               = 0x0193
    VersionYear                 = 0x0194
    ModeNumber                  = 0x0195

    Decode                      = 0x01b1
    DefaultImageColor           = 0x01b2

    JPEGProc                    = 0x0200
    JPEGInterchangeFormat       = 0x0201
    JPEGInterchangeFormatLength = 0x0202
    JPEGRestartInterval         = 0x0203
    JPEGLosslessPredictors      = 0x0205
    JPEGPointTransforms         = 0x0206
    JPEGQTables                 = 0x0207

    JPEGDCTables                = 0x0208
    JPEGACTables                = 0x0209

    YCbCrCoefficients           = 0x0211
    YCbCrSubSampling            = 0x0212
    YCbCrPositioning            = 0x0213
    ReferenceBlackWhite         = 0x0214

    StripRowCounts              = 0x022f
    XMP                         = 0x02bc
    ImageID                     = 0x800d
    Copyright                   = 0x8298
    ImageLayer                  = 0x87ac

    # Private tags
    WangAnnotation              = 0x80a4

    MDFileTag                   = 0x82a5
    MDScalePixel                = 0x82a6
    MDColorTable                = 0x82a7
    MDLabName                   = 0x82a8
    MDSampleInfo                = 0x82a9
    MDPrepDate                  = 0x82aa
    MDPrepTime                  = 0x82ab
    MDFileUnits                 = 0x82ac

    ModelPixelScaleTag          = 0x830e

    IPTC                        = 0x83bb

    INGRPacketDataTag           = 0x847e
    INGRFlagRegisters           = 0x847f

    IrasBTransformationMatrix   = 0x8480
    ModelTiepointTag            = 0x8482
    ModelTransformationTag      = 0x85d8

    Photoshop                   = 0x8649

    ExifIFD                     = 0x8769

    ICCProfile                  = 0x8773

    GeoKeyDirectoryTag          = 0x87af
    GeoDoubleParamsTag          = 0x87b0
    GeoAsciiParamsTag           = 0x87b1

    GPS_IFD                     = 0x8825

    HylaFAXFaxRecvParams        = 0x885c
    HylaFAXFaxSubAddress        = 0x885d
    HylaFAXFaxRecvTime          = 0x885e

    ImageSourceData             = 0x935c

    InteroperabilityIFD         = 0xa005

    GDAL_METADATA               = 0xa480
    GDAL_NODATA                 = 0xa481

    OceScanjobDescription       = 0xc427
    OceApplicationSelector      = 0xc428
    OceIdentificationNumber     = 0xc429
    OceImageLogicCharacteristics= 0xc42a

    DNGVersion                  = 0xc612
    DNGBackwardVersion          = 0xc613
    UniqueCameraModel           = 0xc614
    LocalizedCameraModel        = 0xc615
    CFAPlaneColor               = 0xc616
    CFALayout                   = 0xc617

    LinearizationTable          = 0xc618
    BlackLevelRepeatDim         = 0xc619
    BlackLevel                  = 0xc61a
    BlackLevelDeltaH            = 0xc61b
    BlackLevelDeltaV            = 0xc61c
    WhiteLevel                  = 0xc61d
    DefaultScale                = 0xc61e
    DefaultCropOrigin           = 0xc61f

    DefaultCropSize             = 0xc620
    ColorMatrix1                = 0xc621
    ColorMatrix2                = 0xc622
    CameraCalibration1          = 0xc623
    CameraCalibration2          = 0xc624
    ReductionMatrix1            = 0xc625
    ReductionMatrix2            = 0xc626
    AnalogBalance               = 0xc627

    AsShotNeutral               = 0xc628
    AsShotWhiteXY               = 0xc629
    BaselineExposure            = 0xc62a
    BaselineNoise               = 0xc62b
    BaselineSharpness           = 0xc62c
    BayerGreenSplit             = 0xc62d
    LinearResponseLimit         = 0xc62e
    CameraSerialNumber          = 0xc62f

    LensInfo                    = 0xc630
    ChromaBlurRadius            = 0xc631
    AntiAliasStrength           = 0xc632
    DNGPrivateData              = 0xc634
    MakerNoteSafety             = 0xc635

    CalibrationIlluminant1      = 0xc65a
    CalibrationIlluminant2      = 0xc65b
    BestQualityScale            = 0xc65c

    AliasLayerMetadata          = 0xc660

class IFDCompression:
    """IFDTag.Compression values"""
    uncompressed        = 1
    CCITT_ID            = 2
    Group3Fax           = 3
    Group4Fax           = 4
    LZW                 = 5
    JPEG                = 6
    PackBits            = 0x8005

class IFDExtraSamples:
    """IFDTag.ExtraSamples values"""
    Unspecified         = 0
    Associated          = 1
    Unassociated        = 2

class IFDFillOrder:
    """IFDTag.FillOrder values"""
    LeftToRight         = 1
    RightToLeft         = 2

class IFDOrientation:
    """IFDTag.Orientation values

    These, rather than describe the actual interpretation, give the list
    of transformations that would be required in order to display the
    image at a normal orientation.

    These arguments (excepting "normal") are the exact things one could
    hand to pnmflip.
    """

    normal                          = 1
    leftright                       = 2
    leftright_topbottom             = 3
    topbottom                       = 4
    transpose                       = 5
    transpose_leftright             = 6
    transpose_leftright_topbottom   = 7
    transpose_topbottom             = 8

class IFDPhotometricInterpretation:
    """IFDTag.PhotometricInterpretation values"""
    WhiteIsZero         = 0
    BlackIsZero         = 1
    RGB                 = 2
    Palette             = 3
    TransparencyMask    = 4

class IFDPlanarConfiguration:
    """IFDTag.PlanarConfiguration values"""
    Chunky              = 1
    Planar              = 2

class IFDResolutionUnit:
    """IFDTag.ResolutionUnit values"""
    NoUnit              = 1
    Inch                = 2
    Centimeter          = 3

class IFDSubfileType:
    """IFDTag.SubfileType values"""
    FullResolution      = 1
    ReducedResolution   = 2
    SinglePage          = 3

class IFDThresholding:
    """IFDTag.Thresholding values"""
    Nothing             = 1
    Ordered             = 2
    Randomized          = 3

# This simply pairs IFD tags with IFD value classes.
IFDTagPairs = (
    (IFDTag.Compression,                IFDCompression),
    (IFDTag.ExtraSamples,               IFDExtraSamples),
    (IFDTag.FillOrder,                  IFDFillOrder),
    (IFDTag.Orientation,                IFDOrientation),
    (IFDTag.PhotometricInterpretation,  IFDPhotometricInterpretation),
    (IFDTag.PlanarConfiguration,        IFDPlanarConfiguration),
    (IFDTag.ResolutionUnit,             IFDResolutionUnit),
    (IFDTag.SubfileType,                IFDSubfileType),
    (IFDTag.Thresholding,               IFDThresholding),
)

# Here's a nice backways IFD tag map.
TiffTagNameDict     = make_backways_map(IFDTag)

# We'll do the same thing for IFD tag values.
TiffTagValueDict    = { }
for tag, value_class in IFDTagPairs:
    TiffTagValueDict[tag] = make_backways_map(value_class)
