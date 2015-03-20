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
    assert type(path_int) == int
    assert path_int >= 0
    assert path_int <= Tile.CHR_PATH_LENGTHS[-1]
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
    assert type(chr_int) == int
    chrom_int = chr_int - 1
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
    assert path_int >= 0
    for i, chrom in enumerate(Tile.CHR_PATH_LENGTHS):
        if path_int < chrom:
            return i
    raise BaseException("path_int is larger than the largest path")

def get_chromosome_name_from_chromosome_int(chr_int):
    assert type(chr_int) == int
    chr_index = [i for i,j in TileLocusAnnotation.CHR_CHOICES]
    return TileLocusAnnotation.CHR_CHOICES[chr_index.index(chr_int)][1]
