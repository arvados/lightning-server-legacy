#basic functions without dependencies:
#   used for converting integers to hex and human-readible names
#   used for converting cgf_string to integers
import string
import re

from django.conf import settings

import tile_library.human_readable_functions as human_readable_fns

NUM_HEX_INDEXES_FOR_PATH = settings.NUM_HEX_INDEXES_FOR_PATH
NUM_HEX_INDEXES_FOR_VERSION = settings.NUM_HEX_INDEXES_FOR_VERSION
NUM_HEX_INDEXES_FOR_STEP = settings.NUM_HEX_INDEXES_FOR_STEP
NUM_HEX_INDEXES_FOR_VARIANT_VALUE = settings.NUM_HEX_INDEXES_FOR_VARIANT_VALUE
LANTERN_NAME_FORMAT_STRING = settings.LANTERN_NAME_FORMAT_STRING
CHR_PATH_LENGTHS = settings.CHR_PATH_LENGTHS
CHR_CHOICES = settings.CHR_CHOICES
CHR_NONEXISTANT = settings.CHR_NONEXISTANT

hex_version_and_path_length = NUM_HEX_INDEXES_FOR_VERSION+NUM_HEX_INDEXES_FOR_PATH
hex_tile_length = NUM_HEX_INDEXES_FOR_VERSION+NUM_HEX_INDEXES_FOR_PATH+NUM_HEX_INDEXES_FOR_STEP
hex_tile_variant_length = hex_tile_length + NUM_HEX_INDEXES_FOR_VARIANT_VALUE

def get_position_strings_from_position_int(position_int):
    """
        Returns version, path, and step
        Expects integer, returns 3 strings
        Raises TypeError and ValueError
    """
    if type(position_int) != int:
        raise TypeError("Requires integer argument")
    if position_int < 0:
        raise ValueError("Requires positive argument")
    str_tile_name = hex(position_int).lstrip('0x').rstrip('L')
    if len(str_tile_name) > hex_tile_length:
        raise ValueError("Requires Tile integer. Given integer too large.")
    str_tile_name = str_tile_name.zfill(hex_tile_length)
    version = str_tile_name[:NUM_HEX_INDEXES_FOR_VERSION]
    path = str_tile_name[NUM_HEX_INDEXES_FOR_VERSION:hex_version_and_path_length]
    step = str_tile_name[hex_version_and_path_length:]
    return version, path, step
def get_position_string_from_position_int(position_int):
    """
        Returns hex indexing for tile position
        Expects integer, returns string
        Raises TypeError and ValueError
    """
    version, path, step = get_position_strings_from_position_int(position_int)
    return string.join([version, path, step], ".")
def get_position_ints_from_position_int(position_int):
    """
        Returns integers for path, version, and step for tile position
        Expects integer, returns 3 integers
        Raises TypeError and ValueError
    """
    version, path, step = get_position_strings_from_position_int(position_int)
    return int(version,16), int(path,16), int(step,16)
def get_tile_variant_strings_from_tile_variant_int(tile_variant_int):
    """
        Returns version, path, step, and var
        Expects integer, returns 3 strings
        Raises TypeError and ValueError
    """
    if type(tile_variant_int) != int:
        raise TypeError("Requires integer argument.")
    if tile_variant_int < 0:
        raise ValueError("Requires positive argument.")
    str_tile_name = hex(tile_variant_int).lstrip('0x').rstrip('L')
    if len(str_tile_name) > hex_tile_variant_length:
        raise ValueError("Requires valid TileVariant integer. Given integer too large.")
    str_tile_name = str_tile_name.zfill(hex_tile_variant_length)
    version = str_tile_name[:NUM_HEX_INDEXES_FOR_VERSION]
    path = str_tile_name[NUM_HEX_INDEXES_FOR_VERSION:hex_version_and_path_length]
    step = str_tile_name[hex_version_and_path_length:hex_tile_length]
    var = str_tile_name[hex_tile_length:]
    return version, path, step, var
def get_tile_variant_string_from_tile_variant_int(tile_variant_int):
    """
        Returns hex indexing for tile variant
        Expects integer, returns string
        Raises TypeError and ValueError
    """
    version, path, step, var = get_tile_variant_strings_from_tile_variant_int(tile_variant_int)
    return string.join([version, path, step, var], ".")
def get_tile_variant_ints_from_tile_variant_int(tile_variant_int):
    """
        Returns integers for path, version, step, and variant for tile variant
        Expects integer, returns 4 integers
        Raises TypeError and ValueError
    """
    version, path, step, var = get_tile_variant_strings_from_tile_variant_int(tile_variant_int)
    return int(version,16), int(path,16), int(step,16), int(var,16)
def convert_position_int_to_tile_variant_int(tile_int, variant_value=0):
    """
        Converts position integer to tile variant integer with a variant value of variant_value
        Expects integer, returns integer
        Raises TypeError and ValueError
    """
    if type(variant_value) != int:
        raise TypeError("Requires integer variant value")
    if variant_value < 0:
        raise ValueError("Requires positive variant value")
    hex_variant_value = hex(variant_value).lstrip('0x').rstrip('L').zfill(NUM_HEX_INDEXES_FOR_VARIANT_VALUE)
    if len(hex_variant_value) > NUM_HEX_INDEXES_FOR_VARIANT_VALUE:
        raise ValueError("Requires variant value integer. Given integer too large.")
    version, path, step = get_position_strings_from_position_int(tile_int)
    return int(version+path+step+hex_variant_value,16)
def convert_tile_variant_int_to_position_int(tile_variant_int):
    """
        Converts tile variant integer to its position integer
        Expects integer, returns integer
        Raises TypeError and ValueError
    """
    version, path, step, var = get_tile_variant_strings_from_tile_variant_int(tile_variant_int)
    return int(version+path+step,16)
def get_position_from_cgf_string(cgf_str):
    """
        Returns integer corresponding to the position pointed to by a cgf string
        Expects cgf-formatted string
        Raises TypeError and ValueError
    """
    if type(cgf_str) != str and type(cgf_str) != unicode:
        raise TypeError("Requires %s to be type string or unicode" % (cgf_str))
    matching = re.match(LANTERN_NAME_FORMAT_STRING, cgf_str)
    if matching == None:
        raise ValueError("%s does not match expected regex of cgf_string." % (cgf_str))
    path, version, step = matching.group(1).split('.')
    return int(version+path+step, 16)
def get_non_spanning_cgf_string(cgf_str):
    """
        Returns cgf-string without the trailing '+'
        Expects cgf-formatted string
        Raises TypeError and ValueError
    """
    if type(cgf_str) != str and type(cgf_str) != unicode:
        raise TypeError("Requires %s to be type string or unicode" % (cgf_str)) #Never raised in test functions
    matching = re.match(LANTERN_NAME_FORMAT_STRING, cgf_str)
    if matching == None:
        raise ValueError("%s does not match expected regex of cgf_string." % (cgf_str)) #Never raised
    return str(cgf_str.split('+')[0])
def get_number_of_tiles_spanned_from_cgf_string(cgf_str):
    """
        Returns integer corresponding to the number of positions spanned by a tilevariant encoded
            by a cgf string
        Expects cgf-formatted string
        Raises TypeError and ValueError
    """
    if type(cgf_str) != str and type(cgf_str) != unicode:
        raise TypeError("Requires %s to be type string or unicode" % (cgf_str))
    matching = re.match(LANTERN_NAME_FORMAT_STRING, cgf_str)
    if matching == None:
        raise ValueError("%s does not match expected regex of cgf_string." % (cgf_str))
    if matching.group(2) == None:
        return 1
    else:
        return int(matching.group(2), 16)
def get_min_position_and_tile_variant_from_path_int(path_int, path_version=0):
    """
        Takes a path integer and returns the minimum position integer and minimum tile variant integer
            in that path
        Expects integer, returns 2 integers
        Raises TypeError and ValueError
    """
    if type(path_int) != int:
        raise TypeError("Path integer expected to be of type int.")
    if path_int < 0:
        raise ValueError("Path integer expected to be greater than 0.")
    if path_int > settings.CHR_PATH_LENGTHS[-1]:
        raise ValueError("Path integer expected to be smaller than the maximum number of paths.")
    name = hex(path_version).lstrip('0x').zfill(settings.NUM_HEX_INDEXES_FOR_VERSION)+ \
           hex(path_int).lstrip('0x').zfill(settings.NUM_HEX_INDEXES_FOR_PATH)+ \
           "".zfill(settings.NUM_HEX_INDEXES_FOR_STEP)
    varname = name + "".zfill(settings.NUM_HEX_INDEXES_FOR_VARIANT_VALUE)
    name = int(name, 16)
    varname = int(varname, 16)
    return name, varname
def get_min_position_and_tile_variant_from_chromosome_int(chr_int):
    """
        Takes chromosome integer and returns the minimum position integer and
            the minimum tile variant integer in that chromosome
        Expects integer in CHR_CHOICES or equal to CHR_NONEXISTANT, returns 2 integers
        CHR_NONEXISTANT is for determining the maximum integer possible in the database
        Raises TypeError and ValueError
    """
    if type(chr_int) != int:
        raise TypeError("Expects integer for chromosome int")
    acceptable_chr_ints = [i for i,j in CHR_CHOICES]
    if chr_int not in acceptable_chr_ints and chr_int != CHR_NONEXISTANT:
        raise ValueError(str(chr_int) + " is not an acceptable chromosome integer")
    return get_min_position_and_tile_variant_from_path_int(CHR_PATH_LENGTHS[chr_int-1])
def get_chromosome_int_from_position_int(position_int):
    """
        Returns the chromosome a position int is located on
        Expects an int, returns an int
        Raises TypeError and ValueError
    """
    version, path, step = get_position_ints_from_position_int(position_int)
    return get_chromosome_int_from_path_int(path)
def get_chromosome_int_from_tile_variant_int(tile_variant_int):
    """
        Returns the chromosome a tile variant int is located on
        Expects an int, returns an int
        Raises TypeError and ValueError
    """
    version, path, step, variant_value = get_tile_variant_ints_from_tile_variant_int(tile_variant_int)
    return get_chromosome_int_from_path_int(path)
def get_chromosome_int_from_path_int(path_int):
    """
        Returns the chromosome a path is located on
        Expects an int, returns an int
        Raises TypeError and ValueError
    """
    if type(path_int) != int:
        raise TypeError("Expects integer for path int")
    if path_int < 0:
        raise ValueError("Path int is expected to be larger than 0")
    for i, chrom in enumerate(CHR_PATH_LENGTHS):
        if path_int < chrom:
            return i
    raise ValueError("path_int is larger than the largest path")
