#basic functions without dependencies:
#   used for converting integers to hex and human-readible names
#   used for converting cgf_string to integers
import string
import re

def convert_position_int_to_position_hex_str(pos_int):
    """Returns path, version, step, and var
    Expects integer, returns 3 strings
    """
    if type(pos_int) != int:
        raise TypeError("Requires integer argument")
    if pos_int < 0:
        raise ValueError("Requires positive argument")
    str_tile_name = hex(pos_int).lstrip('0x').rstrip('L')
    if len(str_tile_name) > 9:
        raise ValueError("Requires Tile integer. Given integer too large.")
    str_tile_name = str_tile_name.zfill(9)
    path = str_tile_name[:3]
    version = str_tile_name[3:5]
    step = str_tile_name[5:]
    return path, version, step

def convert_tile_variant_int_to_tile_hex_str(tile_variant_int):
    if type(tile_variant_int) != int:
        raise TypeError("Requires integer argument.")
    if tile_variant_int < 0:
        raise ValueError("Requires positive argument.")
    str_tile_name = hex(tile_variant_int).lstrip('0x').rstrip('L')
    if len(str_tile_name) > 12:
        raise ValueError("Requires valid TileVariant integer. Given integer too large.")
    str_tile_name = str_tile_name.zfill(12)
    path = str_tile_name[:3]
    version = str_tile_name[3:5]
    step = str_tile_name[5:9]
    var = str_tile_name[9:]
    return path, version, step, var

def get_position_string_from_position_int(position_int):
    """Returns hex indexing for tile position
    Expects integer, returns string
    """
    path, version, step = convert_position_int_to_position_hex_str(position_int)
    return string.join([path, version, step], ".")

def get_position_ints_from_position_int(position_int):
    """Returns integers for path, version, and step for tile position
    Expects integer, returns 3 integers
    """
    path, version, step = convert_position_int_to_position_hex_str(position_int)
    return int(path,16), int(version,16), int(step,16)

def get_tile_variant_string_from_tile_variant_int(tile_variant_int):
    """Returns hex indexing for tile variant
    Expects integer, returns string
    """
    path, version, step, var = convert_tile_variant_int_to_tile_hex_str(tile_variant_int)
    return string.join([path, version, step, var], ".")

def get_tile_variant_ints_from_tile_variant_int(tile_variant_int):
    """Returns integers for path, version, step, and variant for tile variant
    Expects integer, returns 4 integers
    """
    path, version, step, var = convert_tile_variant_int_to_tile_hex_str(tile_variant_int)
    return int(path,16), int(version,16), int(step,16), int(var,16)

def convert_position_int_to_tile_variant_int(tile_int):
    """Converts position integer to reference tile variant integer
    Expects integer, returns integer
    """
    path, version, step = convert_position_int_to_position_hex_str(tile_int)
    return int(path+version+step+'000',16)

def convert_tile_variant_int_to_position_int(tile_variant_int):
    """Converts tile variant integer to its position integer
    Expects integer, returns integer
    """
    path, version, step, var = convert_tile_variant_int_to_tile_hex_str(tile_variant_int)
    return int(path+version+step,16)

def get_position_from_cgf_string(cgf_str):
    if type(cgf_str) != str and type(cgf_str) != unicode:
        raise TypeError("Requires %s to be type string or unicode" % (cgf_str))
    matching = re.match('^([0-9a-f]{3}\.[0-9a-f]{2}\.[0-9a-f]{4})\.[0-9a-f]{4}(?:\+[0-9a-f]+$|$)', cgf_str)
    if matching == None:
        raise ValueError("%s does not match expected regex of cgf_string." % (cgf_str))
    return int(string.join(matching.group(1).split('.'), ''), 16)

def get_number_of_tiles_spanned(cgf_str):
    if type(cgf_str) != str and type(cgf_str) != unicode:
        raise TypeError("Unable to cast %s as type string or unicode" % (cgf_str))
    matching = re.match('^([0-9a-f]{3}\.[0-9a-f]{2}\.[0-9a-f]{4})\.[0-9a-f]{4}(?:\+[0-9a-f]+$|$)', cgf_str)
    if matching == None:
        raise ValueError("%s does not match expected regex of cgf_string." % (cgf_str))
    if matching.group(1) == '':
        return 1
    else:
        return int(matching.group(1), 16)
