import collections
import copy
import decimal
import pydxf
import math



def ascii_record_iterator(stream):
    ''' Return a sequence of DxfRecords as parsed from a stream representing an ASCII DXF file.
        stream - Any stream supporting the readline method. Stream does not need to be seekable.
    '''

    while True:
        rec = pydxf.DxfRecord.parse_from_stream(stream)
        if rec is None:
            break
        yield rec


def list_extend(list, items):
    ''' Helper function for appending things to a list. If items is some kind of iterable, then each element of items
        is appended to list. Otherwise, the value of items is appended.
    '''
    if isinstance(items, collections.Iterable):
        list.extend(items)
    else:
        list.append(items)


def is_ascii_dxf(stream):
    ''' Given a stream, determine if the stream contents represent an ASCII DXF file.
        This function reads an arbitrary amount of data from the stream, and does not attempt to return the stream to
        its original state.
    '''

    # Just try to read 5 records from the stream. If that succeeds, it's probably an ASCII DXF file.
    for i in xrange(5):
        try:
            rec = pydxf.DxfRecord.parse_from_stream(stream)
        except pydxf.FormatException:
            return False

    return True


def convert_units(measurement, source_units, target_units):
    ''' Convert a number from one unit of measurement to another.
        source_units and target_units can be any string as found in the INSUNITS map, or key used to look up a value
        from that map.
    '''

    return convert_from_meters(convert_to_meters(measurement, source_units), target_units)


def convert_to_meters(measurement, source_units):
    ''' Convert a number from some unit of measurement to meters.
        source_units can be any string as found in the INSUNITS map, or a key used to look up a value from that map.
    '''

    source = source_units if isinstance(source_units, basestring) else INSUNITS[source_units]

    if source not in VALUE_IN_METERS:
        raise ValueError('Unknown source units {}'.format(source))

    return decimal.Decimal(measurement) * VALUE_IN_METERS[source]


def convert_from_meters(measurement, target_units):
    ''' Convert a number from a measurement in meters to some other unit.
        target_units can be any string as found in the INSUNITS map, or a key used to look up a value from that map.
    '''

    target = target_units if isinstance(target_units, basestring) else INSUNITS[target_units]

    if target not in VALUE_IN_METERS:
        raise ValueError('Unknown target units {}'.format(target))

    return decimal.Decimal(measurement) / VALUE_IN_METERS[target]


def swap_arc_winding(dfile):
    ''' Utility function for reversing the direction of all arcs in a file. Useful if a file's ANGDIR variable is set
        to clockwise, but you need it counter-clockwise, for example.
        An arc starting at 45 degrees and ending at 135 will be changed to start at 315 and end at 225.
        The provided dfile will be modified in place.
    '''
    # Note to future developers: This function only modifies arc winding because that's currently the only kind of
    # entity that is affected by changing angle direction. As more entities with angle dependencies are added, this
    # function should probably be modified and renamed to correct those entites as well.

    for entity in dfile.sections['ENTITIES']:
        if entity.name == 'ARC':
            entity.start_angle = (360 - entity.start_angle) % 360
            entity.end_angle = (360 - entity.end_angle) % 360


def rotate_arcs(dfile, degrees):
    ''' Rotate the start and end point of all arcs in the file's ANGDIR direction by _degrees_. Useful if a file's
        ANGBASE is set to some non-zero value, and you need it to be zero for easy processing.
        The provided dfile will be modified in place.
    '''
    # Note to future developers: This function only modifies arc angles because that's currently the only kind of
    # entity that is affected by changing the angle base. As more entities with angle dependencies are added, this
    # function should probably be modified and renamed to correct those entites as well.

    if degrees == 0:
        return

    for entity in dfile.sections['ENTITIES']:
        if entity.name == 'ARC':
            entity.start_angle = (entity.start_angle + degrees) % 360
            entity.end_angle = (entity.end_angle + degrees) % 360


def bulge_to_arc(v1, v2, bulge):
    ''' Calculate the arc parameters given two VERTEX entities and the DXF "bulge" value.
    Based on "Version 2" of "Bulge to Arc" found here: http://www.lee-mac.com/bulgeconversion.html '''
    def distance(p1, p2):
        return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)

    def angle(p1, p2):
        return math.atan2(p2[1] - p1[1], p2[0] - p1[0])

    def polar_add(point, angle, distance):
        return (point[0] + distance * math.cos(angle),
                point[1] + distance * math.sin(angle))

    p1 = (v1.x, v1.y)
    p2 = (v2.x, v2.y)
    radius = distance(p1, p2) * (1 + bulge ** 2) / (4 * bulge)
    center = polar_add(p1,
                       angle(p1, p2) + (math.pi/2 - 2 * math.atan(bulge)),
                       radius)
    start_angle = angle(center, p1)
    end_angle = angle(center, p2)
    if bulge < 0:
        start_angle, end_angle = end_angle, start_angle

    return center, radius, start_angle, end_angle


class keyfaultdict(collections.defaultdict):
    ''' Functions similarly to the standard library's defaultdict, but calls the default factory function with the
        missing key as the first argument.
    '''

    def __missing__(self, key):
        if self.default_factory is None:
            raise KeyError(key)
        value = self.default_factory(key)
        self[key] = value
        return value


class record_block_iterator(object):
    ''' Given a iterable collection of records, group the collection into lists of records using the block_start and
        block_end rules to determine block boundaries. Once the generator has run through completely, any records from
        the supplied set that aren't a member of a block can be accessed from the get_top_level_records method.
        block_end may be an iterable collection of rules, such that if any are encountered, the block ends.
    '''

    def __init__(self, records, block_start, block_end, include_end=False):
        self.records = (rec for rec in records)
        self.block_start = block_start
        self.block_end = block_end
        self.include_end = include_end
        self.end_rules = record_block_iterator._make_end_rules(block_end)
        self.top_level_records = []
        self.in_block = False
        self.exhausted = False
        self.next_set = []

    def __iter__(self):
        return self

    def __next__(self):
        return self.next()

    def get_top_level_records(self):
        if self.exhausted:
            return self.top_level_records

        raise RuntimeError('get_top_level_records called on record_block_iterator before generator is exhausted.')

    @staticmethod
    def _make_end_rules(block_end):
        if isinstance(block_end, pydxf.DxfRecord):
            return [block_end]
        elif isinstance(block_end, collections.Iterable):
            return list(block_end)
        else:
            raise TypeError

    def next(self):
        if self.exhausted:
            raise StopIteration

        record_set = copy.copy(self.next_set)
        self.next_set = []

        for rec in self.records:
            if self.in_block:
                if any(rule.matches(rec) for rule in self.end_rules):
                    if self.include_end:
                        record_set.append(rec)
                        self.in_block = False
                        break
                    else:
                        self.next_set.append(rec)
                        break
                else:
                    record_set.append(rec)
            else:
                if self.block_start.matches(rec):
                    self.in_block = True
                    record_set.append(rec)
                else:
                    self.top_level_records.append(rec)
        else:
            self.exhausted = True
            raise StopIteration

        return record_set


ANGDIR = {
    0: 'COUNTERCLOCKWISE',
    1: 'CLOCKWISE'
}

INSUNITS = {
    0: 'UNITLESS',
    1: 'INCHES',
    2: 'FEET',
    3: 'MILES',
    4: 'MILLIMETERS',
    5: 'CENTIMETERS',
    6: 'METERS',
    7: 'KILOMETERS',
    8: 'MICROINCHES',
    9: 'MILS',
    10: 'YARDS',
    11: 'ANGSTROMS',
    12: 'NANOMETERS',
    13: 'MICRONS',
    14: 'DECIMETERS',
    15: 'DECAMETERS',
    16: 'HECTOMETERS',
    17: 'GIGAMETERS',
    18: 'ASTRONOMICAL_UNITS',
    19: 'LIGHT_YEARS',
    20: 'PARSECS'
}

VALUE_IN_METERS = {
    'ANGSTROMS': decimal.Decimal('0.0000000001'),
    'NANOMETERS': decimal.Decimal('0.000000001'),
    'MICRONS': decimal.Decimal('0.000001'),
    'MILLIMETERS': decimal.Decimal('0.001'),
    'CENTIMETERS': decimal.Decimal('0.01'),
    'DECIMETERS': decimal.Decimal('0.1'),
    'METERS': decimal.Decimal('1'),
    'UNITLESS': decimal.Decimal('1'),
    'DECAMETERS': decimal.Decimal('10'),
    'HECTOMETERS': decimal.Decimal('100'),
    'KILOMETERS': decimal.Decimal('1000'),
    'GIGAMETERS': decimal.Decimal('1000000000'),
    'ASTRONOMICAL_UNITS': decimal.Decimal('149597870700'),
    'LIGHT_YEARS': decimal.Decimal('9460730472580800'),
    'PARSECS': decimal.Decimal('30856776376340066.65169031476'),
    'MICROINCHES': decimal.Decimal('0.0000000254'),
    'MILS': decimal.Decimal('0.0000254'),
    'INCHES': decimal.Decimal('0.0254'),
    'FEET': decimal.Decimal('0.3048'),
    'YARDS': decimal.Decimal('0.9144'),
    'MILES': decimal.Decimal('1609.344'),
}

COLORS = {
    0: '#000000',
    1: '#ff0000',
    2: '#ffff00',
    3: '#00ff00',
    4: '#00ffff',
    5: '#0000ff',
    6: '#ff00ff',
    7: '#ffffff',
    8: '#414141',
    9: '#808080',
    10: '#ff0000',
    11: '#ffaaaa',
    12: '#bd0000',
    13: '#bd7e7e',
    14: '#810000',
    15: '#815656',
    16: '#680000',
    17: '#684545',
    18: '#4f0000',
    19: '#4f3535',
    20: '#ff3f00',
    21: '#ffbfaa',
    22: '#bd2e00',
    23: '#bd8d7e',
    24: '#811f00',
    25: '#816056',
    26: '#681900',
    27: '#684e45',
    28: '#4f1300',
    29: '#4f3b35',
    30: '#ff7f00',
    31: '#ffd4aa',
    32: '#bd5e00',
    33: '#bd9d7e',
    34: '#814000',
    35: '#816b56',
    36: '#683400',
    37: '#685645',
    38: '#4f2700',
    39: '#4f4235',
    40: '#ffbf00',
    41: '#ffeaaa',
    42: '#bd8d00',
    43: '#bdad7e',
    44: '#816000',
    45: '#817656',
    46: '#684e00',
    47: '#685f45',
    48: '#4f3b00',
    49: '#4f4935',
    50: '#ffff00',
    51: '#ffffaa',
    52: '#bdbd00',
    53: '#bdbd7e',
    54: '#818100',
    55: '#818156',
    56: '#686800',
    57: '#686845',
    58: '#4f4f00',
    59: '#4f4f35',
    60: '#bfff00',
    61: '#eaffaa',
    62: '#8dbd00',
    63: '#adbd7e',
    64: '#608100',
    65: '#768156',
    66: '#4e6800',
    67: '#5f6845',
    68: '#3b4f00',
    69: '#494f35',
    70: '#7fff00',
    71: '#d4ffaa',
    72: '#5ebd00',
    73: '#9dbd7e',
    74: '#408100',
    75: '#6b8156',
    76: '#346800',
    77: '#566845',
    78: '#274f00',
    79: '#424f35',
    80: '#3fff00',
    81: '#bfffaa',
    82: '#2ebd00',
    83: '#8dbd7e',
    84: '#1f8100',
    85: '#608156',
    86: '#196800',
    87: '#4e6845',
    88: '#134f00',
    89: '#3b4f35',
    90: '#00ff00',
    91: '#aaffaa',
    92: '#00bd00',
    93: '#7ebd7e',
    94: '#008100',
    95: '#568156',
    96: '#006800',
    97: '#456845',
    98: '#004f00',
    99: '#354f35',
    100: '#00ff3f',
    101: '#aaffbf',
    102: '#00bd2e',
    103: '#7ebd8d',
    104: '#00811f',
    105: '#568160',
    106: '#006819',
    107: '#45684e',
    108: '#004f13',
    109: '#354f3b',
    110: '#00ff7f',
    111: '#aaffd4',
    112: '#00bd5e',
    113: '#7ebd9d',
    114: '#008140',
    115: '#56816b',
    116: '#006834',
    117: '#456856',
    118: '#004f27',
    119: '#354f42',
    120: '#00ffbf',
    121: '#aaffea',
    122: '#00bd8d',
    123: '#7ebdad',
    124: '#008160',
    125: '#568176',
    126: '#00684e',
    127: '#45685f',
    128: '#004f3b',
    129: '#354f49',
    130: '#00ffff',
    131: '#aaffff',
    132: '#00bdbd',
    133: '#7ebdbd',
    134: '#008181',
    135: '#568181',
    136: '#006868',
    137: '#456868',
    138: '#004f4f',
    139: '#354f4f',
    140: '#00bfff',
    141: '#aaeaff',
    142: '#008dbd',
    143: '#7eadbd',
    144: '#006081',
    145: '#567681',
    146: '#004e68',
    147: '#455f68',
    148: '#003b4f',
    149: '#35494f',
    150: '#007fff',
    151: '#aad4ff',
    152: '#005ebd',
    153: '#7e9dbd',
    154: '#004081',
    155: '#566b81',
    156: '#003468',
    157: '#455668',
    158: '#00274f',
    159: '#35424f',
    160: '#003fff',
    161: '#aabfff',
    162: '#002ebd',
    163: '#7e8dbd',
    164: '#001f81',
    165: '#566081',
    166: '#001968',
    167: '#454e68',
    168: '#00134f',
    169: '#353b4f',
    170: '#0000ff',
    171: '#aaaaff',
    172: '#0000bd',
    173: '#7e7ebd',
    174: '#000081',
    175: '#565681',
    176: '#000068',
    177: '#454568',
    178: '#00004f',
    179: '#35354f',
    180: '#3f00ff',
    181: '#bfaaff',
    182: '#2e00bd',
    183: '#8d7ebd',
    184: '#1f0081',
    185: '#605681',
    186: '#190068',
    187: '#4e4568',
    188: '#13004f',
    189: '#3b354f',
    190: '#7f00ff',
    191: '#d4aaff',
    192: '#5e00bd',
    193: '#9d7ebd',
    194: '#400081',
    195: '#6b5681',
    196: '#340068',
    197: '#564568',
    198: '#27004f',
    199: '#42354f',
    200: '#bf00ff',
    201: '#eaaaff',
    202: '#8d00bd',
    203: '#ad7ebd',
    204: '#600081',
    205: '#765681',
    206: '#4e0068',
    207: '#5f4568',
    208: '#3b004f',
    209: '#49354f',
    210: '#ff00ff',
    211: '#ffaaff',
    212: '#bd00bd',
    213: '#bd7ebd',
    214: '#810081',
    215: '#815681',
    216: '#680068',
    217: '#684568',
    218: '#4f004f',
    219: '#4f354f',
    220: '#ff00bf',
    221: '#ffaaea',
    222: '#bd008d',
    223: '#bd7ead',
    224: '#810060',
    225: '#815676',
    226: '#68004e',
    227: '#68455f',
    228: '#4f003b',
    229: '#4f3549',
    230: '#ff007f',
    231: '#ffaad4',
    232: '#bd005e',
    233: '#bd7e9d',
    234: '#810040',
    235: '#81566b',
    236: '#680034',
    237: '#684556',
    238: '#4f0027',
    239: '#4f3542',
    240: '#ff003f',
    241: '#ffaabf',
    242: '#bd002e',
    243: '#bd7e8d',
    244: '#81001f',
    245: '#815660',
    246: '#680019',
    247: '#68454e',
    248: '#4f0013',
    249: '#4f353b',
    250: '#333333',
    251: '#505050',
    252: '#696969',
    253: '#828282',
    254: '#bebebe',
    255: '#ffffff',
}
