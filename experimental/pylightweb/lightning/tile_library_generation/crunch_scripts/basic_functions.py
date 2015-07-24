#basic functions without dependencies:
#   used for converting integers to hex and human-readible names
#   used for converting cgf_string to integers
import string
import re

def get_position_strings_from_position_int(position_int, num_v, num_p, num_s):
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
    if len(str_tile_name) > num_v+num_p+num_s:
        raise ValueError("Requires Tile integer. Given integer too large.")
    str_tile_name = str_tile_name.zfill(num_v+num_p+num_s)
    version = str_tile_name[:num_v]
    path = str_tile_name[num_v:num_v+num_p]
    step = str_tile_name[num_v+num_p:]
    return version, path, step
def get_position_string_from_position_int(position_int, num_v, num_p, num_s):
    """
        Returns hex indexing for tile position
        Expects integer, returns string
        Raises TypeError and ValueError
    """
    version, path, step = get_position_strings_from_position_int(position_int, num_v, num_p, num_s)
    return string.join([version, path, step], ".")
def get_position_ints_from_position_int(position_int, num_v, num_p, num_s):
    """
        Returns integers for path, version, and step for tile position
        Expects integer, returns 3 integers
        Raises TypeError and ValueError
    """
    version, path, step = get_position_strings_from_position_int(position_int, num_v, num_p, num_s)
    return int(version,16), int(path,16), int(step,16)
def get_tile_variant_strings_from_tile_variant_int(tile_variant_int, num_v, num_p, num_s, num_vv):
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
    if len(str_tile_name) > num_v+num_p+num_s+num_vv:
        raise ValueError("Requires valid TileVariant integer. Given integer too large.")
    str_tile_name = str_tile_name.zfill(num_v+num_p+num_s+num_vv)
    version = str_tile_name[:num_v]
    path = str_tile_name[num_v:num_v+num_p]
    step = str_tile_name[num_v+num_p:num_v+num_p+num_s]
    var = str_tile_name[num_v+num_p+num_s:]
    return version, path, step, var
def get_tile_variant_string_from_tile_variant_int(tile_variant_int, num_v, num_p, num_s, num_vv):
    """
        Returns hex indexing for tile variant
        Expects integer, returns string
        Raises TypeError and ValueError
    """
    version, path, step, var = get_tile_variant_strings_from_tile_variant_int(tile_variant_int, num_v, num_p, num_s, num_vv)
    return string.join([version, path, step, var], ".")
def get_tile_variant_ints_from_tile_variant_int(tile_variant_int, num_v, num_p, num_s, num_vv):
    """
        Returns integers for path, version, step, and variant for tile variant
        Expects integer, returns 4 integers
        Raises TypeError and ValueError
    """
    version, path, step, var = get_tile_variant_strings_from_tile_variant_int(tile_variant_int, num_v, num_p, num_s, num_vv)
    return int(version,16), int(path,16), int(step,16), int(var,16)
def convert_position_int_to_tile_variant_int(tile_int, num_v, num_p, num_s, num_vv, variant_value=0):
    """
        Converts position integer to tile variant integer with a variant value of variant_value
        Expects integer, returns integer
        Raises TypeError and ValueError
    """
    if type(variant_value) != int:
        raise TypeError("Requires integer variant value")
    if variant_value < 0:
        raise ValueError("Requires positive variant value")
    hex_variant_value = hex(variant_value).lstrip('0x').rstrip('L').zfill(num_vv)
    if len(hex_variant_value) > num_vv:
        raise ValueError("Requires variant value integer. Given integer too large.")
    version, path, step = get_position_strings_from_position_int(tile_int, num_v, num_p, num_s)
    return int(version+path+step+hex_variant_value,16)
def convert_tile_variant_int_to_position_int(tile_variant_int, num_v, num_p, num_s, num_vv):
    """
        Converts tile variant integer to its position integer
        Expects integer, returns integer
        Raises TypeError and ValueError
    """
    version, path, step, var = get_tile_variant_strings_from_tile_variant_int(tile_variant_int, num_v, num_p, num_s, num_vv)
    return int(version+path+step,16)
def get_position_from_cgf_string(cgf_str, lantern_name_format_string):
    """
        Returns integer corresponding to the position pointed to by a cgf string
        Expects cgf-formatted string
        Raises TypeError and ValueError
    """
    if type(cgf_str) != str and type(cgf_str) != unicode:
        raise TypeError("Requires %s to be type string or unicode" % (cgf_str))
    matching = re.match(lantern_name_format_string, cgf_str)
    if matching == None:
        raise ValueError("%s does not match expected regex of cgf_string." % (cgf_str))
    path, version, step = matching.group(1).split('.')
    return int(version+path+step, 16)
