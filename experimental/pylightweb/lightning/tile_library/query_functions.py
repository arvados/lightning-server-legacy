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

def get_population_with_tile_variant_long_names(cgf_string):
    """
    Submits 'sample-tile-group-match' lantern query.
    Returns a list of people which contain the tile variant
    """
    post_data = {
        'Type':'sample-tile-group-match',
        'Dataset':'all',
        'Note':'Expects population set that contains variant to be returned',
        'SampleId':[],
        'TileGroupVariantId':[[cgf_string]]
    }
    post_data = json.dumps(post_data)
    try:
        post_response = requests.post(url="http://localhost:8080", data=post_data)
        response = json.loads(post_response.text)
    except ConnectionError:
        raise ConnectionError, "Lantern not responding on port 8080"
    except ValueError:
        #first version of lantern doesn't return a valid json, so parse the return
        m = re.match(r"(\[.*\])(\{.*\})", post_response.text)
        response = json.loads(m.group(2))
        result = json.loads('{"Result":' + m.group(1) +'}')
        response['Result'] = result['Result']
    assert "success" == response['Type'], "Lantern-communication failure:" + response['Message']
    return response['Result']

def get_population_with_tile_variant(cgf_string):
    """
    Submits 'sample-tile-group-match' lantern query.
    Returns a list of people which contain the tile variant
    """
    large_file_names = get_population_with_tile_variant_long_names(cgf_string)
    return [name.strip('" ').split('/')[-1] for name in large_file_names]

def get_population_names_and_check_lantern_version():
    """
    Submits 'system-info' lantern query.
    Checks to make sure the lantern running is version 0.0.3
    Returns a list of human names
    """
    ## Check that lantern version is the version that is expected
    post_data_check = {
        'Type':'system-info'
        }
    post_data_check = json.dumps(post_data_check)
    try:
        post_response = requests.post(url="http://localhost:8080", data=post_data_check)
        response = json.loads(post_response.text)
    except requests.ConnectionError:
        raise requests.ConnectionError, "Lantern not responding on port 8080"
    assert response['LanternVersion'] == '0.0.3', "Lantern Version is expected to be 0.0.3"
    assert response['Type'] == "success", "Lantern-communication failure: " + response['Message']
    ## Create list of humans
    human_names = response['SampleId']
    return human_names

def make_sample_position_variant_query(position_query_string, human_subsection=[]):
    post_data = {
        'Type':'sample-position-variant',
        'Dataset':'all',
        'Note':'Expects entire population set to be returned with their phase A and phase B variant ids',
        'SampleId':human_subsection,
        'Position': [position_query_string]
    }
    post_data = json.dumps(post_data)
    try:
        post_response = requests.post(url="http://localhost:8080", data=post_data)
        return json.loads(post_response.text)
    except requests.ConnectionError:
        raise requests.ConnectionError, "Lantern not responding on port 8080"

def get_population_sequences_over_position_range(first_position_int, last_position_int):
    """
    Expects range to be inclusive
    Submits 'sample-position-variant' lantern query.
    Runs get_population_names_and_check_lantern_version() and uses that result to check all humans are returned.
        This hits the lantern database
    Checks to make sure no humans were added or subtracted in the result
    Returns the phase A and phase B variant ids of the entire population at the position pointed to by position_hex_string
        (dictionary. keys are human names, values are [[phase_A_cgf_string1, phase_A_cgf_string2, ...], [phase_B_cgf_string1, phase_B_cgf_string2, ...]])
    """
    human_names = get_population_names_and_check_lantern_version()
    human_names = sorted(human_names)
    first_path, foo, bar = basic_fns.get_position_ints_from_position_int(first_position_int)
    last_path, foo, bar = basic_fns.get_position_ints_from_position_int(last_position_int)
    position_hex_string = basic_fns.get_position_string_from_position_int(first_position_int)
    last_position_hex_string = basic_fns.get_position_string_from_position_int(last_position_int)
    assert last_position_int >= first_position_int, "Expects first_position_int (%s) to be less than last_position_int (%s)" % (position_hex_string, last_position_hex_string)
    if first_path == last_path:
        length_to_retrieve = hex(last_position_int - first_position_int + 1).lstrip('0x')
        response = make_sample_position_variant_query(position_hex_string+"+"+length_to_retrieve)
        assert "success" == response['Type'], "Lantern-communication failure: " + response['Message']
        humans = response['Result']
        human_names_returned = sorted(humans.keys())
        assert human_names_returned == human_names, "Lantern error: Returned list of human samples does not match the samples in lantern"
        return humans
    else:
        humans = {}
        for path in range(first_path, last_path+1):
            path_min_position_int, foo = fns.get_min_position_and_tile_variant_from_path_int(path)
            path_max_position_int = get_highest_position_int_in_path(path)
            tmp_first_position_int = max(first_position_int, path_min_position_int)
            tmp_last_position_int = min(last_position_int, path_max_position_int)
            tmp_first_position_hex_string = basic_fns.get_position_string_from_position_int(tmp_first_position_int)
            length_to_retrieve = hex(tmp_last_position_int - tmp_first_position_int + 1).lstrip('0x')
            response = make_sample_position_variant_query(tmp_first_position_hex_string+"+"+length_to_retrieve)
            assert "success" == response['Type'], "Lantern-communication failure: " + response['Message']
            if humans == {}:
                humans = response['Result']
                human_names_returned = sorted(humans.keys())
                assert human_names_returned == human_names, "Lantern error: Returned list of human samples does not match the samples in lantern"
            else:
                next_path_humans = response['Result']
                human_names_returned = sorted(next_path_humans.keys())
                assert human_names_returned == human_names, "Lantern error: Returned list of human samples does not match the samples in lantern"
                for human in humans:
                    for i, sequence in enumerate(humans[human]):
                        humans[human][i] = sequence + next_path_humans[human][i]

        return humans

def get_population_sequences_over_position_range_force_large_query(first_position_int, last_position_int):
    """
    Expects range to be inclusive
    Submits 'sample-position-variant' lantern query.
    Runs get_population_names_and_check_lantern_version() and uses that result to check all humans are returned.
        This hits the lantern database
    Checks to make sure no humans were added or subtracted in the result
    Returns the phase A and phase B variant ids of the entire population at the position pointed to by position_hex_string
        (dictionary. keys are human names, values are [[phase_A_cgf_string1, phase_A_cgf_string2, ...], [phase_B_cgf_string1, phase_B_cgf_string2, ...]])
    """
    human_names = get_population_names_and_check_lantern_version()
    human_names = sorted(human_names)
    position_hex_string = basic_fns.get_position_string_from_position_int(first_position_int)
    last_position_hex_string = basic_fns.get_position_string_from_position_int(last_position_int)
    assert last_position_int >= first_position_int, "Expects first_position_int (%s) to be less than last_position_int (%s)" % (position_hex_string, last_position_hex_string)
    length_to_retrieve = hex(last_position_int - first_position_int + 1).lstrip('0x')
    response = make_sample_position_variant_query(position_hex_string+"+"+length_to_retrieve)
    if "success" != response['Type'] and response['Message'] == "max elements exceeded":
        half_length_to_retrieve = hex((last_position_int - first_position_int + 1)/2).lstrip('0x')
        response1 = make_sample_position_variant_query(position_hex_string+"+"+half_length_to_retrieve)
        assert "success" == response1['Type'], "Lantern-communication failure: " + response1['Message'] + ". Tried cutting query in half. Failed on first half (%s)" % (position_hex_string+"+"+half_length_to_retrieve)
        next_position_hex_string = basic_fns.get_position_string_from_position_int(first_position_int + last_position_int/2)
        response2 = make_sample_position_variant_query(next_position_hex_string+"+"+half_length_to_retrieve)
        assert "success" == response2['Type'], "Lantern-communication failure: " + response2['Message'] + ". Tried cutting query in half. Failed on second half (%s)" % (next_position_hex_string+"+"+half_length_to_retrieve)
        humans = {}
        humans1 = response1['Result']
        humans2 = response2['Result']
        human_names_returned1 = sorted(humans1.keys())
        human_names_returned2 = sorted(humans2.keys())
        assert human_names_returned1 == human_names, "Lantern error: Returned list of human samples does not match the samples in lantern"
        assert human_names_returned2 == human_names, "Lantern error: Returned list of human samples does not match the samples in lantern"
        for human in humans1:
            max_num_phases = max(len(humans1[human]), len(humans2[human]))
            humans[human] = [[] for i in range(max_num_phases)]
            for i in range(max_num_phases):
                humans[human][i] = humans1[human][i] + humans2[human][i]
    else:
        assert "success" == response['Type'], "Lantern-communication failure: " + response['Message']
        humans = response['Result']
        human_names_returned = sorted(humans.keys())
        assert human_names_returned == human_names, "Lantern error: Returned list of human samples does not match the samples in lantern"
    return humans

def get_sub_population_sequences_over_position_range(list_of_humans, first_position_int, last_position_int):
    """
    Expects range to be inclusive
    Submits 'sample-position-variant' lantern query.
    Runs get_population_names_and_check_lantern_version() and uses that result to check all humans are returned.
        This hits the lantern database
    Checks to make sure no humans were added or subtracted in the result
    Returns the phase A and phase B variant ids of the entire population at the position pointed to by position_hex_string
        (dictionary. keys are human names, values are [[phase_A_cgf_string1, phase_A_cgf_string2, ...], [phase_B_cgf_string1, phase_B_cgf_string2, ...]])
    """
    human_names = get_population_names_and_check_lantern_version()
    for human in list_of_humans:
        assert human in human_names, "%s is not loaded into this server" % (human)
    position_hex_string = basic_fns.get_position_string_from_position_int(first_position_int)
    last_position_hex_string = basic_fns.get_position_string_from_position_int(last_position_int)
    assert last_position_int >= first_position_int, "Expects first_position_int (%s) to be less than last_position_int (%s)" % (position_hex_string, last_position_hex_string)
    length_to_retrieve = hex(last_position_int - first_position_int + 1).lstrip('0x')
    response = make_sample_position_variant_query(position_hex_string+"+"+length_to_retrieve, human_subsection=list_of_humans)
    assert "success" == response['Type'], "Lantern-communication failure: " + response['Message']
    humans = response['Result']
    return humans
