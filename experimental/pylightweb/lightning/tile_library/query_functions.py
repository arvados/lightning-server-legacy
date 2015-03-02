import json
import requests
import re
import string

from django.db.models import Q

from tile_library.models import TileLocusAnnotation, GenomeStatistic, TileVariant, Tile
import tile_library.basic_functions as fns
from errors import EmptyPathError, MissingStatisticsError

def print_friendly_cgf_translator(cgf_translator):
    """
    Meant for reducing the number of lines printed while debugging. Not tested
    """
    new_string = ""
    for i in cgf_translator:
        new_string += str(sorted(i.keys()))+','
    return new_string.strip(',')

def get_highest_position_int_in_path(path_int):
    min_position, min_tile_var = fns.get_min_position_and_tile_variant_from_path_int(path_int)
    max_position, max_tile_var = fns.get_min_position_and_tile_variant_from_path_int(path_int+1)
    tile = Tile.objects.filter(tilename__range=(min_position, max_position-1)).last()
    if tile == None:
        raise EmptyPathError("No tiles are matched in path %s" % (hex(path_int).lstrip('0x').zfill(3)))
    return int(tile.tilename)

def get_max_num_tiles_spanned_at_position(tile_position_int):
    #Number to look back!
    path_int, version_int, step_int = basic_fns.get_position_ints_from_position_int(tile_position_int)
    #raises AssertionError if tile_position_int is not an integer, negative, or an invalid tile position
    try:
        num_tiles_spanned = GenomeStatistic.objects.get(path_name=path_int).max_num_positions_spanned
    except GenomeStatistic.DoesNotExist:
        foo, min_path_tile = fns.get_min_position_and_tile_variant_from_path_int(path_int)
        foo, max_path_tile = fns.get_min_position_and_tile_variant_from_path_int(path_int + 1)
        tilevars = TileVariant.objects.filter(tile_variant_name__range=(min_path_tile, max_path_tile-1))
        num_tiles_spanned = tilevars.aggregate(max_pos_spanned=Max('num_positions_spanned'))['max_pos_spanned']
    if num_tiles_spanned == None:
        raise EmptyPathError('No tiles are loaded for path containing tile: %s' % (hex(tile_position_int).lstrip('0x').zfill(9)))
    num_tiles_spanned = min(int(num_tiles_spanned)-1, step_int) #Only need to look back as far as there are steps in this path
    return num_tiles_spanned

def get_tile_variants_spanning_into_position(tile_position_int):
    """
    Returns list of tile variants that start before tile_position_int but span into tile_position_int
    Returns empty list if no spanning tiles overlap with that position
    """
    try:
        tile = Tile.objects.get(tilename=tile_position_int)
    except Tile.DoesNotExist:
        raise Exception("Tile position int must be the primary key to a Tile object loaded into the population")
    spanning_tile_variants = []
    num_tiles_spanned = get_max_num_tiles_spanned_at_position(tile_position_int)
    #raises AssertionError if tile_position_int is not an integer, negative, or an invalid tile position
    #raises Exception if the GenomeStatistic does not exist
    if num_tiles_spanned > 0:
        for i in range(1, num_tiles_spanned+1):
            if i == 1:
                curr_Q = (Q(tile_id=tile_position_int-i) & Q(num_positions_spanned__gt=i))
            else:
                curr_Q = curr_Q | (Q(tile_id=tile_position_int-i) & Q(num_positions_spanned__gt=i))
        spanning_tile_variants = TileVariant.objects.filter(curr_Q).all()
    return spanning_tile_variants

def get_tile_variant_cgf_str_and_all_bases(tile_variant):
    cgf_str = tile_variant.conversion_to_cgf
    bases = tile_variant.sequence.upper()
    return cgf_str, bases

def get_bases_from_cgf_str(cgf_str):
    tile_position_int = basic_fns.get_position_from_cgf_string(cgf_str)
    try:
        variant = TileVariant.objects.filter(tile_id=tile_position_int).get(conversion_to_cgf=cgf_str.split('+')[0])
    except TileVariant.DoesNotExist:
        raise Exception("Unable to find a tile variant matching %s" % (cgf_str))
    bases = variant.sequence.upper()
    return bases

def get_tile_variant_cgf_str_and_bases_between_loci_unknown_locus(tile_variant, low_int, high_int, assembly):
    lower_tile_position_int = basic_fns.convert_tile_variant_int_to_position_int(int(tile_variant.tile_variant_name))
    lower_locus = TileLocusAnnotation.objects.filter(assembly=assembly).get(tile_id=lower_tile_position_int)
    start_locus_int = int(lower_locus.begin_int)
    if tile_variant.num_positions_spanned == 1:
        end_locus_int = int(locus.end_int)
        return get_tile_variant_cgf_str_and_bases_between_loci_known_locus(tile_variant, low_int, high_int, start_locus_int, end_locus_int)
    else:
        upper_tile_position_int = lower_tile_position_int + tile_variant.num_positions_spanned - 1
        upper_locus = TileLocusAnnotation.objects.filter(assembly=assembly).get(tile_id=upper_tile_position_int)
        end_locus_int = int(upper_locus.end_int)
        return get_tile_variant_cgf_str_and_bases_between_loci_known_locus(tile_variant, low_int, high_int, start_locus_int, end_locus_int)

def get_tile_variant_cgf_str_and_bases_between_loci_known_locus(tile_variant, low_int, high_int, start_locus_int, end_locus_int):
    cgf_str = tile_variant.conversion_to_cgf
    if cgf_str == "": #if the cgf translation is empty, we will never get it returned by lantern
        return "", ""
    assert low_int <= end_locus_int, "Asked to get out-of-range information for %s. Query: [%i, %i) Locus: [%i, %i)" % (str(tile_variant), low_int, high_int, start_locus_int, end_locus_int)
    assert high_int >= start_locus_int, "Asked to get out-of-range information for %s. Query: [%i, %i) Locus: [%i, %i)" % (str(tile_variant), low_int, high_int, start_locus_int, end_locus_int)
    #If we are asked to retrieve the entire tile, our job is easy:
    if end_locus_int <= high_int and start_locus_int >= low_int:
        return cgf_str, tile_variant.sequence.upper()
    else:
        low_int = max(low_int - start_locus_int, 0)
        high_int -= start_locus_int
        assert end_locus_int >= start_locus_int, \
            "TileLocusAnnotation for tile %s is-malformed. The end locus is smaller than the start locus." % (string.join(cgf_str.split('.')[:-1], '.'))
        reference_to_tile_variant = [(0, 0), (end_locus_int-start_locus_int, tile_variant.length)]
        genome_variant_positions = tile_variant.translation_to_genome_variant.all()
        for translation in genome_variant_positions:
            ####################### ERROR CHECKING ######################################
            genome_variant_start_position = translation.start
            genome_variant_end_position = translation.end
            assert genome_variant_start_position >= 0, \
                "%s is malformed.  The start position of the variant is smaller than the start locus." % (str(translation))
            assert genome_variant_end_position >= 0, \
                "%s is malformed.  The end position of the variant is smaller than the start locus." % (str(translation))
            assert genome_variant_start_position <= tile_variant.length, \
                "%s is malformed.  The start position of the variant is larger than the variant length." % (str(translation))
            assert genome_variant_end_position <= tile_variant.length, \
                "%s is malformed.  The end position of the variant is larger than the variant length." % (str(translation))
            assert genome_variant_start_position <= genome_variant_end_position, \
                "%s is malformed. The variant ends before it begins." %s (str(translation))
            ####################### END OF ERROR CHECKING ###############################
            # we only need to add if the variant is an INDEL
            genome_variant = translation.genome_variant
            ref_bases = genome_variant.reference_bases
            alt_bases = genome_variant.alternate_bases
            if len(ref_bases) != len(alt_bases) or '-' in ref_bases or '-' in alt_bases:
                genome_variant_locus_start_position = genome_variant.start_increment
                genome_variant_locus_end_position = genome_variant.end_increment
                assert (genome_variant_locus_start_position, genome_variant_start_position) not in reference_to_tile_variant, \
                    "Database is malformed. Two variants at the exact same place" + str(sorted(reference_to_tile_variant))
                reference_to_tile_variant.append((genome_variant_locus_start_position, genome_variant_start_position))
                if alt_bases == '-':
                    end_index = genome_variant_start_position
                else:
                    end_index = genome_variant_start_position + len(alt_bases)
                reference_to_tile_variant.append((genome_variant_locus_end_position, end_index))
        reference_to_tile_variant.sort()
        if len(reference_to_tile_variant) == 2: #Only have SNPs, no calls, or the tile is reference. Positional numbers don't change
            lower_base_index = max(low_int, 0)
            higher_base_index = min(high_int, end_locus_int-start_locus_int)
        else:
            lower_base_index = get_index(low_int, reference_to_tile_variant)
            higher_base_index = get_index(high_int, reference_to_tile_variant)
        bases = tile_variant.getBaseGroupBetweenPositions(lower_base_index, higher_base_index).upper()
        return cgf_str, bases

def get_index(locus_bound, locus_converter):
    prev_locus_point, prev_variant_point = locus_converter[0]
    for locus_point, variant_point in locus_converter[1:]:
        if locus_bound <= locus_point:
            break
        prev_locus_point, prev_variant_point = locus_point, variant_point
    if locus_bound > locus_point:
        return variant_point
    length_of_ref = locus_point - prev_locus_point
    length_of_var = variant_point - prev_variant_point
    length_of_query = locus_bound - prev_locus_point
    if length_of_var == 0:
        # we are in a deletion
        assert length_of_ref > 0, "Reference length and variant length are 0. Variant: %s; Conversion list: %s. " % (tile_variant, str(reference_to_tile_variant))
        return prev_variant_point
    elif length_of_ref == length_of_var:
        # we are in a consistent area
        return prev_variant_point + length_of_query
    else:
        #The way I believe variants are built, we will never be in an insertion
        #We are in a substitution. All hopes are lost
        return prev_variant_point + min(length_of_query, length_of_var)

def get_cgf_translator(locuses, low_int, high_int, assembly):
    num_locuses = locuses.count()
    cgf_translator = [{} for i in range(num_locuses)]
    for i, locus in enumerate(locuses):
        tile_position_int = int(locus.tile_id)
        start_locus_int = int(locus.begin_int)
        end_locus_int = int(locus.end_int)
        low_variant_int = basic_fns.convert_position_int_to_tile_variant_int(tile_position_int)
        high_variant_int = basic_fns.convert_position_int_to_tile_variant_int(tile_position_int+1)-1
        tile_variants = TileVariant.objects.filter(tile_variant_name__range=(low_variant_int, high_variant_int)).all()
        for var in tile_variants:
            if var.num_positions_spanned != 1:
                upper_tile_position_int = tile_position_int + var.num_positions_spanned - 1
                upper_locus = TileLocusAnnotation.objects.filter(assembly=assembly).get(tile_id=upper_tile_position_int)
                large_end_locus_int = int(upper_locus.end_int)
                cgf_str, bases = get_tile_variant_cgf_str_and_bases_between_loci_known_locus(var, low_int, high_int, start_locus_int, large_end_locus_int)
            else:
                cgf_str, bases = get_tile_variant_cgf_str_and_bases_between_loci_known_locus(var, low_int, high_int, start_locus_int, end_locus_int)
            assert cgf_str not in cgf_translator[i], "Repeat cgf_string in position %s" % (basic_fns.get_position_string_from_position_int(tile_position_int))
            cgf_translator[i][cgf_str] = bases
    return cgf_translator

def crosses_center_index(variant, i, center_index, max_num_spanned):
    for num in range(max_num_spanned+1):
        if center_index-num == i and variant.num_positions_spanned > num:
            return True
    return False

def get_cgf_translator_and_center_cgf_translator(locuses, target_base, center_index, max_num_spanned, assembly):
    def manage_center_cgfs(center_cgf_translator, variant, start_locus_int, end_locus_int):
        lower_tile_position_int = int(variant.tile_id)
        if variant.num_positions_spanned != 1:
            lower_locus = TileLocusAnnotation.objects.filter(assembly=assembly).get(tile_id=lower_tile_position_int)
            start_locus_int = int(lower_locus.begin_int)
            upper_tile_position_int = lower_tile_position_int + var.num_positions_spanned - 1
            upper_locus = TileLocusAnnotation.objects.filter(assembly=assembly).get(tile_id=upper_tile_position_int)
            end_locus_int = int(upper_locus.end_int)
        keys = [(start_locus_int, target_base), (target_base, target_base+1), (target_base+1, end_locus_int)]
        for i, translator in enumerate(center_cgf_translator):
            cgf_str, bases = get_tile_variant_cgf_str_and_bases_between_loci_known_locus(variant, keys[i][0], keys[i][1], start_locus_int, end_locus_int)
            if cgf_str in translator:
                assert bases == translator[cgf_str], "Conflicting cgf_string-base pairing, cgf_str: %s, translator: %s" % (cgf_str,
                    print_friendly_cgf_translator(center_cgf_translator))
            center_cgf_translator[i][cgf_str] = bases
        return center_cgf_translator

    num_locuses = locuses.count()
    cgf_translator = [{} for i in range(num_locuses)]
    center_cgf_translator = [{}, {}, {}]

    for i, locus in enumerate(locuses):
        tile_position_int = int(locus.tile_id)
        start_locus_int = int(locus.begin_int)
        end_locus_int = int(locus.end_int)
        low_variant_int = basic_fns.convert_position_int_to_tile_variant_int(tile_position_int)
        high_variant_int = basic_fns.convert_position_int_to_tile_variant_int(tile_position_int+1)-1
        tile_variants = TileVariant.objects.filter(tile_variant_name__range=(low_variant_int, high_variant_int)).all()[:]
        if i == center_index:
            spanning_tile_variants = get_tile_variants_spanning_into_position(tile_position_int)
            for var in spanning_tile_variants:
                center_cgf_translator = manage_center_cgfs(center_cgf_translator, var, start_locus_int, end_locus_int)
        for var in tile_variants:
            if crosses_center_index(var, i, center_index, max_num_spanned):
                center_cgf_translator = manage_center_cgfs(center_cgf_translator, var, start_locus_int, end_locus_int)
            else:
                cgf_str, bases = get_tile_variant_cgf_str_and_all_bases(var)
                assert cgf_str not in cgf_translator[i], "Repeat cgf_string (%s) in position %s" % (cgf_str, basic_fns.get_position_string_from_position_int(tile_position_int))
                cgf_translator[i][cgf_str] = bases
    return center_cgf_translator, cgf_translator
