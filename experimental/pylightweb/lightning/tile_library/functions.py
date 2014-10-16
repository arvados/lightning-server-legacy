#Define basic functions used for interacting with tile_library
from tile_library.models import Tile, TileLocusAnnotation
    #need Tile for constants: get_min_position_and_tile_variant_from_chromosome_int,
    #                         get_chromosome_int_from_path_int,
    #need TileLocusAnnotation for constants: get_chromosome_name_from_chromosome_int,
def convert_position_int_to_position_hex_str(pos_int):
    """Returns path, version, step, and var
    Expects integer, returns 4 strings
    """
    assert type(pos_int) == int
    str_tile_name = hex(pos_int).lstrip('0x').rstrip('L')
    str_tile_name = str_tile_name.zfill(9)
    path = str_tile_name[:3]
    version = str_tile_name[3:5]
    step = str_tile_name[5:]
    return path, version, step

def convert_tile_variant_int_to_tile_hex_str(tile_variant_int):
    assert type(tile_variant_int) == int
    str_tile_name = hex(tile_variant_int).lstrip('0x').rstrip('L')
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

def get_min_position_and_tile_variant_from_path_int(path_int):
    """Takes path integer and returns the minimum position integer and minimum tile variant integer
       in that path
       Expects integer, returns 2 integers
       (used to be known as view.convert_path_to_tilename)
    """
    assert type(path_int) == int
    name = hex(path_int).lstrip('0x').zfill(3)+"00"+"0000"
    varname = name + "000"
    name = int(name, 16)
    varname = int(varname, 16)
    return name, varname

def get_min_position_and_tile_variant_from_chromosome_int(chr_int):
    """Takes chromosome integer and returns the minimum position integer and minimum tile variant integer
       in that chromosome
       Expects integer: [1, 27], returns 2 integers

    chr_int: [1, 2, 3, ... 26, 27]
        23 => chrX
        24 => chrY
        25 => chrM
        26 => strangely-shaped chromosomes
        27 is non-existant, for determining the maximum integer possible in the database
    """
    chrom_int = int(chr_int) - 1
    if chrom_int < 0 or chrom_int > 26:
        raise BaseException(str(chr_int) + " is not an integer between 1 and 27")
    chr_path_lengths = Tile.CHR_PATH_LENGTHS
    return get_min_position_and_tile_variant_from_path_int(chr_path_lengths[chrom_int])

def get_chromosome_int_from_position_int(position_int):
    raise BaseException("Not implemented yet!")

def get_chromosome_int_from_tile_variant_int(tile_int):
    raise BaseException("Not implemented yet!")

def get_chromosome_int_from_path_int(path_int):
    assert type(path_int) == int
    for i, chrom in enumerate(Tile.CHR_PATH_LENGTHS):
        if path_int < chrom:
            return i
    raise BaseException("path_int is larger than the largest path")

def get_chromosome_name_from_chromosome_int(chr_int):
    assert type(chr_int) == int
    chr_index = [i for i,j in TileLocusAnnotation.CHR_CHOICES]
    return TileLocusAnnotation.CHR_CHOICES[chr_index.index(chr_int)][1]
