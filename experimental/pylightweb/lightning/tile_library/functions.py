#Define functions used for interacting with tile_library
import tile_library.basic_functions as basic
from tile_library.models import Tile, TileLocusAnnotation
    #need Tile for constants: get_min_position_and_tile_variant_from_path_int,
    #                         get_min_position_and_tile_variant_from_chromosome_int,
    #                         get_chromosome_int_from_path_int,

    #need TileLocusAnnotation for constants: get_chromosome_name_from_chromosome_int,

def get_min_position_and_tile_variant_from_path_int(path_int):
    """Takes path integer and returns the minimum position integer and minimum tile variant integer
       in that path. Assumes path version is 0
       Expects integer, returns 2 integers
    """
    if type(path_int) != int:
        raise TypeError("Path integer expected to be of type int.")
    if path_int < 0:
        raise ValueError("Path integer expected to be greater than 0.")
    if path_int > Tile.CHR_PATH_LENGTHS[-1]:
        raise ValueError("Path integer expected to be smaller than the maximum number of paths.")
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
    if type(chr_int) != int:
        raise TypeError("Expects integer for chromosome int")
    chrom_int = chr_int - 1
    if chrom_int < 0 or chrom_int > 26:
        raise ValueError(str(chr_int) + " is not an integer between 1 and 27")
    chr_path_lengths = Tile.CHR_PATH_LENGTHS
    return get_min_position_and_tile_variant_from_path_int(chr_path_lengths[chrom_int])

def get_chromosome_int_from_position_int(position_int):
    raise NotImplementedError("get_chromosome_int_from_position_int is not yet implemented")

def get_chromosome_int_from_tile_variant_int(tile_int):
    raise NotImplementedError("get_chromosome_int_from_tile_variant_int is not yet implemented")

def get_chromosome_int_from_path_int(path_int):
    if type(path_int) != int:
        raise TypeError("Expects integer for path int")
    if path_int < 0:
        raise ValueError("Path int is expected to be larger than 0")
    for i, chrom in enumerate(Tile.CHR_PATH_LENGTHS):
        if path_int < chrom:
            return i
    raise ValueError("path_int is larger than the largest path")

def get_chromosome_name_from_chromosome_int(chr_int):
    if type(chr_int) != int:
        raise TypeError("Expects chromosome int to be of type int")
    chr_index = [i for i,j in TileLocusAnnotation.CHR_CHOICES]
    return TileLocusAnnotation.CHR_CHOICES[chr_index.index(chr_int)][1]
