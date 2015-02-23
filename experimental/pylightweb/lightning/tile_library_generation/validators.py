import hashlib

import tile_library.basic_functions as basic_fns
from tile_library.constants import CHR_PATH_LENGTHS, CHR_OTHER, TAG_LENGTH
from errors import TileLibraryValidationError, MissingLocusError


def validate_tile(tile_position_int):
    VALIDATION_ERRORS = {}
    if tile_position_int < 0:
        VALIDATION_ERRORS['tile_position_negative'] = "tile position int must be positive"
    if tile_position_int > int('fffffffff', 16):
        VALIDATION_ERRORS['tile_position_too_big'] = "tile position int must be smaller than or equal to 'fff.ff.ffff'"
    if len(VALIDATION_ERRORS) > 0:
        raise TileLibraryValidationError(VALIDATION_ERRORS)

def validate_spanning_tile(tile_position_one, tile_position_two, num_positions_spanned):
    validate_tile(tile_position_one)
    validate_tile(tile_position_two)
    #If these throw an error, I want it to propogate.
    tile1_path, tile1_path_version, tile1_step = basic_fns.get_position_ints_from_position_int(tile_position_one)
    tile2_path, tile2_path_version, tile2_step = basic_fns.get_position_ints_from_position_int(tile_position_two)
    if tile1_path != tile2_path:
        raise TileLibraryValidationError({'spanning_tile_error':'starting and ending tiles cross paths'})
    if tile1_path_version != tile2_path_version:
        raise TileLibraryValidationError({'spanning_tile_error':'starting and ending tiles cross path versions'})
    if abs(tile2_step - tile1_step) != num_positions_spanned-1:
        raise TileLibraryValidationError({'spanning_tile_error':'number of steps spanned (from tile position integers and reported) do not match'})

def validate_tile_variant(tile_position_int, tile_variant_int, variant_value, sequence, seq_length, seq_md5sum, start_tag, end_tag):
    VALIDATION_ERRORS = {}
    if tile_position_int < 0:
        VALIDATION_ERRORS['tile_position_negative'] = "tile position int must be positive"
    if tile_position_int > int('fffffffff', 16):
        VALIDATION_ERRORS['tile_position_too_big'] = "tile position int must be smaller than or equal to 'fff.ff.ffff'"
    if tile_variant_int < 0:
        VALIDATION_ERRORS['variant_position_negative'] = "tile variant int must be positive"
    if tile_variant_int > int('ffffffffffff', 16):
        VALIDATION_ERRORS['variant_position_too_big'] = "tile variant int must be smaller than or equal to 'fff.ff.ffff.fff'"
    #If these throw an error, I want it to propogate.
    tile_path, tile_path_version, tile_step = basic_fns.get_position_ints_from_position_int(tile_position_int)
    variant_path, variant_path_version, variant_step, variant_val = basic_fns.get_tile_variant_ints_from_tile_variant_int(tile_variant_int)
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

def validate_locus(chromosome_int, tile_position_int, TAG_LENGTH, tile_sequence_length, begin_int, end_int):
    VALIDATION_ERRORS = {}
    path, version, step = basic_fns.get_position_ints_from_position_int(tile_position_int)
    if path not in range(CHR_PATH_LENGTHS[chromosome_int-1], CHR_PATH_LENGTHS[chromosome_int]):
        VALIDATION_ERRORS['chromosome_int-tile_position'] = "Path %i is not in chromosome %i, based on CHR_PATH_LENGTHS" % (path,chromosome_int)
    if end_int <= begin_int:
        VALIDATION_ERRORS['malformed_locus'] = "end_int must be strictly larger than begin_int"
    if tile_sequence_length != end_int - begin_int:
        VALIDATION_ERRORS['tile_length_locus_mismatch'] = "Sequence length must be the same length specified by the loci"
    if end_int - begin_int < TAG_LENGTH*2:
        VALIDATION_ERRORS['short_locus'] = "the distance between begin_int and end_int must be greater than twice the TAG_LENGTH"
    if len(VALIDATION_ERRORS) > 0:
        raise TileLibraryValidationError(VALIDATION_ERRORS)

def validate_genome_variant_model(genome_variant):
    VALIDATION_ERRORS = {}
    reference_seq = ''
    loci = TileLocusAnnotation.objects.filter(assembly_int=genome_variant.assembly_int).filter(chromosome_int=genome_variant.chromosome_int).filter(
        begin_int__lt=genome_variant.end_int).filter(end_int__gt=genome_variant.start_int).order_by('begin_int')
    if loci.count() == 0:
        raise TileLibraryValidationError({'missing_locus':'Unable to find any loci in assembly %i, chromosome %i, with a begin_int less than %i and an end in greater than %i' % ()})
    for locus in loci:
        reference_tile_variant_sequence = locus.get_reference_sequence()
        if reference_seq == '':
            reference_seq += reference_tile_variant_sequence
        else:
            reference_seq += reference_tile_variant_sequence[TAG_LENGTH:]
    if reference_seq
def validate_genome_variant_translation_models(genome_variant):
    VALIDATION_ERRORS = {}
    assembly = genome_variant.assembly_int
    tile_variants = genome_variant.tile_variants
    for tile_variant in tile_variants:
        num_pos_spanned = tile_variant.num_positions_spanned
        path, version, step, value = basic_fns.get_tile_variant_ints_from_tile_variant_int(int(tile_variant.tile_variant_int))
        tile_position_int = int(path+version+step,16)
        tile_string = basic_fns.get_position_string_from_position_int(tile_position)
        for tile_position in range(tile_position_int,tile_position_int+num_pos_spanned):
            try:
                #check loci annotations are available for defined assembly
                locus = TileLocusAnnotation.objects.filter(tile_position=tile_position).get(assembly_int=assembly)
                #check we are working in the same chromosome the tile variants are on
                if locus.chromosome != genome_variant.chromosome_int:
                    VALIDATION_ERRORS['chromosome_int'] = 'Locus for tile %s is not in chromosome %i' % (tile_string, genome_variant.chromosome_int)
                if locus.alternate_chromosome_name != genome_variant.alternate_chromosome_name:
                    VALIDATION_ERRORS['alternate_chromosome_name'] = "Locus for tile %s is not in chromosome %s" % (tile_string, genome_variant.alternate_chromosome_name)

            except TileLocusAnnotation.DoesNotExist:
                VALIDATION_ERRORS['assembly_int'] = 'Locus for assembly %i not found for tile %s' % (assembly, tile_string)
        try:
            start_int, end_int = tile_variant.get_locus(assembly)
            #check genome variant loci are withing tile variant loci
            if genome_variant.start_int < start_int+TAG_LENGTH:
                VALIDATION_ERRORS['start_int'] = "start_int is in the start tag or before the locus"
            if genome_variant.start_int > end_int-TAG_LENGTH:
                VALIDATION_ERRORS['start_int'] = "start_int is in the end tag or after the locus"
            if genome_variant.end_int < start_int+TAG_LENGTH:
                VALIDATION_ERRORS['end_int'] = "end int is in the start tag or before the locus"
            if genome_variant.edn_int > end_int-TAG_LENGTH:
                VALIDATION_ERRORS['end_int'] = "end int is in the end tag or after the locus"
        except MissingLocusError as e:
            raise AssertionError("Check TileVariant.get_locus: threw error when asking for assembly %i, but could get assembly via a raw query" % (assembly))
        #check the reference bases are correct
        if reference_seq[genome_variant.start_int:genome_variant.end_int] != genome_variant.reference_bases.strip('-'):
            VALIDATION_ERRORS['reference_bases'] = "Reference bases (%s) do not match bases in reference tile variant (%s)" % (genome_variant.reference_bases, reference_seq[genome_variant.start_int:genome_variant.end_int])
        through = tile_variant.translations_to_genome_variant.filter(genome_variant=genome_variant)
        if tile_variant.sequence[through.start:through.end] != genome_variant.alternate_bases.strip('-'):
            VALIDATION_ERRORS['reference_bases'] = "Alternate bases (%s) do not match bases in tile variant (%s)" % (genome_variant.alternate_bases, tile_variant.sequence[through.start:through.end])



def validate_genome_variant_and_tile_variant(gv_assembly, tv_assemblies, gv_chrom, tv_chrom):
    VALIDATION_ERRORS = {}
#    if gv_assembly != tv_assembly
