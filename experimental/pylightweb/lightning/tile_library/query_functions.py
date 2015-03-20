import json
import requests
import re
import string

from django.db.models import Q, Avg, Count, Max, Min
from django.core.urlresolvers import reverse

from tile_library.models import TileLocusAnnotation, GenomeStatistic, TileVariant, Tile, LanternTranslator
import tile_library.basic_functions as fns
from errors import EmptyPathError, MissingStatisticsError, CGFTranslatorError

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
    tile = Tile.objects.filter(tile_position_int__range=(min_position, max_position-1)).last()
    if tile == None:
        raise EmptyPathError("No tiles are matched in path %s" % (hex(path_int).lstrip('0x').zfill(3)))
    return int(tile.tile_position_int)

def get_max_num_tiles_spanned_at_position(tile_position_int):
    #Number to look back!
    path_int, version_int, step_int = fns.get_position_ints_from_position_int(tile_position_int)
    #raises AssertionError if tile_position_int is not an integer, negative, or an invalid tile position
    try:
        num_tiles_spanned = GenomeStatistic.objects.get(path_name=path_int).max_num_positions_spanned
    except GenomeStatistic.DoesNotExist:
        foo, min_path_tile = fns.get_min_position_and_tile_variant_from_path_int(path_int)
        foo, max_path_tile = fns.get_min_position_and_tile_variant_from_path_int(path_int + 1)
        tilevars = TileVariant.objects.filter(tile_variant_int__range=(min_path_tile, max_path_tile-1))
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
        tile = Tile.objects.get(tile_position_int=tile_position_int)
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

def get_tile_variant_lantern_name_and_all_bases(tile_variant):
    """
    Assumes tile variant is in our tile library, since we have the tile variant

    Can raise LanternTranslator.DoesNotExist if tile_variant does not have a name associated with it
    """
    lantern_name = LanternTranslator.objects.filter(tile_variant_int=int(tile_variant.tile_variant_int)).get(tile_library_host='').lantern_name
    bases = tile_variant.sequence.upper()
    return lantern_name, bases

def get_bases_from_lantern_name(lantern_name):
    """
    No assumptions about the location of the tile library

    Can raise ValueError, TypeError if lantern_name is not the correct format
    Can raise LanternTranslator.DoesNotExist if lantern_name is not in the database
    Can raise LanternTranslator.DegradedVariantError if the lantern translator has problems re-retrieving the variant data
    """
    lantern_name = fns.get_non_spanning_cgf_string(lantern_name)
    try:
        lantern_translation = LanternTranslator.objects.get(lantern_name=lantern_name)
        if lantern_translation.tile_library_host == "":
            #In our library!
            bases = TileVariant.objects.get(tile_variant_int=int(lantern_translation.tile_variant_int)).sequence.upper()
        else:
            tile_library_path = reverse('api:tile_variant_query_by_int', args=[lantern_translation.tile_variant_int])
            r = requests.get("http://%s%s" % (lantern_translation.tile_library_host, tile_library_path))
            r.raise_for_status()
            tile_variant = json.loads(r.text)
            bases = tile_variant['sequence'].upper()
    except (TileVariant.DoesNotExist, requests.exceptions.RequestException) as e:
        raise LanternTranslator.DegradedVariantError("Translator %s has degraded. %s" % (lantern_name, str(e)))
    except LanternTranslator.DoesNotExist:
        return ""
    return bases

def get_tile_variant_cgf_str_and_bases_between_loci_unknown_locus(tile_variant, queried_low_int, queried_high_int, assembly):
    lantern_name = tile_variant.get_tile_variant_lantern_name()
    if lantern_name != "":
        bases = tile_variant.get_bases_between_loci(queried_low_int, queried_high_int, assembly)
        return lantern_name, bases
    return lantern_name, ""

def get_tile_variant_cgf_str_and_bases_between_loci_known_locus(tile_variant, queried_low_int, queried_high_int, start_locus_int, end_locus_int):
    lantern_name = tile_variant.get_tile_variant_lantern_name()
    if lantern_name != "":
        bases = tile_variant.get_bases_between_loci_known_locus(queried_low_int, queried_high_int, start_locus_int, end_locus_int)
        return lantern_name, bases
    return lantern_name, ""

def get_simple_cgf_translator(locuses, low_int, high_int, assembly):
    num_locuses = locuses.count()
    simple_cgf_translator = {}
    for i, locus in enumerate(locuses):
        tile_position_int = int(locus.tile_position_id)
        start_locus_int = int(locus.start_int)
        end_locus_int = int(locus.end_int)
        low_variant_int = fns.convert_position_int_to_tile_variant_int(tile_position_int)
        high_variant_int = fns.convert_position_int_to_tile_variant_int(tile_position_int+1)-1
        tile_variants = TileVariant.objects.filter(tile_variant_int__range=(low_variant_int, high_variant_int)).all()
        for var in tile_variants:
            if var.num_positions_spanned != 1:
                upper_tile_position_int = tile_position_int + var.num_positions_spanned - 1
                upper_locus = TileLocusAnnotation.objects.filter(assembly_int=assembly).get(tile_position_id=upper_tile_position_int)
                large_end_locus_int = int(upper_locus.end_int)
                cgf_str, bases = get_tile_variant_cgf_str_and_bases_between_loci_known_locus(var, low_int, high_int, start_locus_int, large_end_locus_int)
            else:
                cgf_str, bases = get_tile_variant_cgf_str_and_bases_between_loci_known_locus(var, low_int, high_int, start_locus_int, end_locus_int)
            if cgf_str != '':
                if cgf_str in simple_cgf_translator:
                    raise CGFTranslatorError("Repeat cgf_string (%s) in cgf_translator" % (cgf_str))
                simple_cgf_translator[cgf_str] = bases
    return simple_cgf_translator

def crosses_center_index(variant, i, center_index, max_num_spanned):
    for num in range(max_num_spanned+1):
        if center_index-num == i and variant.num_positions_spanned > num:
            return True
    return False

def get_cgf_translator_and_center_cgf_translator(locuses, target_base, center_index, max_num_spanned, assembly):
    def manage_center_cgfs(center_cgf_translator, variant, start_locus_int, end_locus_int):
        lower_tile_position_int = int(variant.tile_id)
        if variant.num_positions_spanned != 1:
            lower_locus = TileLocusAnnotation.objects.filter(assembly_int=assembly).get(tile_position_id=lower_tile_position_int)
            start_locus_int = int(lower_locus.start_int)
            upper_tile_position_int = lower_tile_position_int + var.num_positions_spanned - 1
            upper_locus = TileLocusAnnotation.objects.filter(assembly_int=assembly).get(tile_position_id=upper_tile_position_int)
            end_locus_int = int(upper_locus.end_int)
        keys = [(start_locus_int, target_base), (target_base, target_base+1), (target_base+1, end_locus_int)]
        for i, translator in enumerate(center_cgf_translator):
            #print center_cgf_translator, keys, i
            cgf_str, bases = get_tile_variant_cgf_str_and_bases_between_loci_known_locus(variant, keys[i][0], keys[i][1], start_locus_int, end_locus_int)
            if cgf_str in translator:
                assert bases == translator[cgf_str], "Conflicting cgf_string-base pairing, cgf_str: %s, translator: %s" % (cgf_str,
                    print_friendly_cgf_translator(center_cgf_translator))
            center_cgf_translator[i][cgf_str] = bases
        return center_cgf_translator

    num_locuses = locuses.count()
    cgf_translator = {}
    center_cgf_translator = [{}, {}, {}]

    for i, locus in enumerate(locuses):
        tile_position_int = int(locus.tile_position_id)
        start_locus_int = int(locus.start_int)
        end_locus_int = int(locus.end_int)
        low_variant_int = fns.convert_position_int_to_tile_variant_int(tile_position_int)
        high_variant_int = fns.convert_position_int_to_tile_variant_int(tile_position_int+1)-1
        tile_variants = TileVariant.objects.filter(tile_variant_int__range=(low_variant_int, high_variant_int)).all()[:]
        if i == center_index:
            spanning_tile_variants = get_tile_variants_spanning_into_position(tile_position_int)
            for var in spanning_tile_variants:
                center_cgf_translator = manage_center_cgfs(center_cgf_translator, var, start_locus_int, end_locus_int)
        for var in tile_variants:
            if crosses_center_index(var, i, center_index, max_num_spanned):
                center_cgf_translator = manage_center_cgfs(center_cgf_translator, var, start_locus_int, end_locus_int)
            else:
                try:
                    cgf_str, bases = get_tile_variant_lantern_name_and_all_bases(var)
                except LanternTranslator.DoesNotExist:
                    cgf_str = ''
                    bases = ''
                if cgf_str != '':
                    if cgf_str in cgf_translator:
                        raise CGFTranslatorError("Repeat cgf_string (%s) in non-center cgf_translator" % (cgf_str))
                    cgf_translator[cgf_str] = bases
    return center_cgf_translator, cgf_translator
