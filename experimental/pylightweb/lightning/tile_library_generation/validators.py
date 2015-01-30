import hashlib

import tile_library.basic_functions as basic_fns
from errors import TileLibraryValidationError

def validate_tile(tile_position_int):
    VALIDATION_ERRORS = {}
    if tile_position_int < 0:
        VALIDATION_ERRORS['tile_position_negative'] = "tile position int must be positive"
    if tile_position_int > int('fffffffff', 16):
        VALIDATION_ERRORS['tile_position_too_big'] = "tile position int must be smaller than or equal to 'fff.ff.ffff'"
    if len(VALIDATION_ERRORS) > 0:
        raise TileLibraryValidationError(VALIDATION_ERRORS)


def validate_tile_variant(TAG_LENGTH, tile_position_int, tile_variant_int, variant_value, sequence, seq_length, seq_md5sum, start_tag, end_tag):
    VALIDATION_ERRORS = {}
    if tile_position_int < 0:
        VALIDATION_ERRORS['tile_position_negative'] = "tile position int must be positive"
    if tile_position_int > int('fffffffff', 16):
        VALIDATION_ERRORS['tile_position_too_big'] = "tile position int must be smaller than or equal to 'fff.ff.ffff'"
    if tile_variant_int < 0:
        VALIDATION_ERRORS['variant_position_negative'] = "tile variant int must be positive"
    if tile_variant_int > int('ffffffffffff', 16):
        VALIDATION_ERRORS['variant_position_too_big'] = "tile variant int must be smaller than or equal to 'fff.ff.ffff.fff'"
    try:
        #If these throw a type error, I want it to propogate. Only catch ValueError
        tile_path, tile_path_version, tile_step = basic_fns.get_position_ints_from_position_int(tile_position_int)
        variant_path, variant_path_version, variant_step, variant_val = basic_fns.get_tile_variant_ints_from_tile_variant_int(tile_variant_int)
    except ValueError:
        raise TileLibraryValidationError(VALIDATION_ERRORS)
    if tile_path != variant_path:
        VALIDATION_ERRORS['path_mismatch'] = "tile variant path and tile position path must be equal"
    if tile_path_version != variant_path_version:
        VALIDATION_ERRORS['version_mismatch'] = "tile variant path version and tile position path version must be equal"
    if tile_step != variant_step:
        VALIDATION_ERRORS['step_mismatch'] = "tile variant step and tile position step must be equal"
    if variant_val != variant_value:
        VALIDATION_ERRORS['variant_value_mismatch'] = "tile variant value and input variant value must be equal"
    if seq_length != len(sequence):
        VALIDATION_ERRORS['length_mismatch'] = "length must be the length of the sequence"
    digestor = hashlib.new('md5', sequence)
    if digestor.hexdigest() != seq_md5sum:
        VALIDATION_ERRORS['md5sum_mismatch'] = "md5sum is not actually md5sum of sequence"
    if len(sequence) < TAG_LENGTH*2:
        VALIDATION_ERRORS['sequence_malformed'] = "Sequence is not long enough - the tags overlap"
    if sequence[:TAG_LENGTH] != start_tag:
        VALIDATION_ERRORS['start_tag_mismatch'] = "Sequence does not start with the given start tag"
    if sequence[-TAG_LENGTH:] != end_tag:
        VALIDATION_ERRORS['end_tag_mismatch'] = "Sequence does not end with the given end tag"
    if len(VALIDATION_ERRORS) > 0:
        raise TileLibraryValidationError(VALIDATION_ERRORS)

def validate_locus(TAG_LENGTH, tile_sequence_length, begin_int, end_int):
    VALIDATION_ERRORS = {}
    if end_int <= begin_int:
        VALIDATION_ERRORS['malformed_locus'] = "end_int must be strictly larger than begin_int"
    if tile_sequence_length != end_int - begin_int:
        VALIDATION_ERRORS['tile_length_locus_mismatch'] = "Sequence length must be the same length specified by the loci"
    if end_int - begin_int < TAG_LENGTH*2:
        VALIDATION_ERRORS['short_locus'] = "the distance between begin_int and end_int must be greater than twice the TAG_LENGTH"
    if len(VALIDATION_ERRORS) > 0:
        raise TileLibraryValidationError(VALIDATION_ERRORS)
