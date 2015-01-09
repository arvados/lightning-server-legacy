import json
import requests
import re

from django.db.models import Q

from tile_library.models import TileLocusAnnotation, GenomeStatistic, TileVariant, Tile
import tile_library.basic_functions as basic_fns
import tile_library.functions as fns

def get_max_num_tiles_spanned_at_position(tile_position_int):
    path_int, version_int, step_int = basic_fns.get_position_ints_from_position_int(tile_position_int)
    #raises AssertionError if tile_position_int is not an integer, negative, or an invalid tile position
    try:
        num_tiles_spanned = int(GenomeStatistic.objects.get(path_name=path_int).max_num_positions_spanned)
        num_tiles_spanned = min(num_tiles_spanned, step_int+1) #Only need to look back as far as there are steps in this path
        return num_tiles_spanned
    except GenomeStatistic.DoesNotExist:
        raise Exception('GenomeStatistic for that path does not exist')

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
    if num_tiles_spanned > 1:
        for i in range(2, num_tiles_spanned+1):
            if i == 2:
                curr_Q = (Q(tile_id=tile_position_int-i) & Q(num_positions_spanned__gte=i))
            else:
                curr_Q = curr_Q | (Q(tile_id=tile_position_int-i) & Q(num_positions_spanned__gte=i))
        spanning_tile_variants = TileVariant.objects.filter(curr_Q).all()
    return spanning_tile_variants

def get_tile_variant_cgf_str_and_bases(tile_variant, low_int, high_int, assembly):
    tile_position_int = basic_fns.convert_tile_variant_int_to_position_int(int(tile_variant.tile_variant_name))
    locus = TileLocusAnnotation.object.filter(assembly=assembly).get(tile_id=tile_position_int)
    start_locus_int = int(locus.start_int)
    end_locus_int = int(locus.end_int)
    return get_tile_variant_cgf_str_and_bases_fast(tile_variant, low_int, high_int, start_locus_int, end_locus_int)

def get_tile_variant_cgf_str_and_bases_fast(tile_variant, low_int, high_int, start_locus_int, end_locus_int):
    cgf_str = tile_variant.conversion_to_cgf
    assert cgf_str != "", "CGF translation required"
    assert low_int <= end_locus_int, "Asked to get information of tile_variant that is before the low base of interest"
    assert high_int >= start_locus_int, "Asked to get information of tile_variant that is after the high base of interest"

    end_variant_int = start_locus_int + int(tile_variant.length)
    if end_variant_int == end_locus_int: # tile is same length as reference. Everything is fine
        higher_base_position = min(high_int, end_locus_int) - start_locus_int #add 1
    elif end_variant_int < end_locus_int: # tile is missing at least one base
        higher_base_position = min(high_int, end_variant_int) - (start_locus_int)
    else: #tile has at least an extra base
        higher_base_position = min(high_int, end_variant_int) - (start_locus_int)

    lower_base_position = max(low_int-start_locus_int, 0)
    bases = tile_variant.getBaseGroupBetweenPositions(lower_base_position, higher_base_position).upper()
    return cgf_str, bases

def get_cgf_translator(locuses, low_int, high_int):
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
            cgf_str, bases = get_tile_variant_cgf_str_and_bases_fast(var, low_int, high_int, start_locus_int, end_locus_int)
            assert cgf_str not in cgf_translator[i], "Repeat cgf_string in position %s" % (basic_fns.get_position_string_from_position_int(tile_position_int))
            cgf_translator[i][cgf_str] = bases
    return cgf_translator

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
    assert response['Type'] == "success", "Lantern-communication failure:" + response['Message']
    ## Create list of humans
    human_names = response['SampleId']
    return human_names

def get_population_sequences_at_position(position_hex_string, error_check=True, human_names=None):
    """
    Submits 'sample-position-variant' lantern query.
    If error_check, it runs get_population_names_and_check_lantern_version() and uses that result as human_names.
        This hits the lantern database
    Otherwise, it assumes the user ran get_population_names_and_check_lantern_version() and is passing human_names
        returned by that function
    Checks to make sure no humans were added or subtracted in the result
    Returns the phase A and phase B variant ids of the entire population at the position pointed to by position_hex_string
        (dictionary. keys are human names, values are [phase_A_cgf_string, phase_B_cgf_string])
    """
    if error_check:
        human_names = get_population_names_and_check_lantern_version()
        human_names = sorted(human_names)
    else:
        assert human_names != None, "Must supply list of human names if not error checking"
        human_names = sorted(human_names)
    post_data = {
        'Type':'sample-position-variant',
        'Dataset':'all',
        'Note':'Expects entire population set to be returned with their phase A and phase B variant ids',
        'SampleId':[],
        'Position': [position_hex_string]
    }
    post_data = json.dumps(post_data)
    try:
        post_response = requests.post(url="http://localhost:8080", data=post_data)
        response = json.loads(post_response.text)
    except requests.ConnectionError:
        raise requests.ConnectionError, "Lantern not responding on port 8080"
    assert "success" == response['Type'], "Lantern-communication failure:" + response['Message']
    humans = response['Result']
    human_names_returned = sorted(humans.keys())
    assert human_names_returned == human_names, "Returned list of human samples does not match the samples provided (or returned by error checking)"
    ret_dict = {}
    for hu in humans:
        ret_dict[hu] = [humans[hu][0][0], humans[hu][1][0]]
    return ret_dict

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
    assert last_position_int >= first_position_int, "Expects first_position_int to be less than last_position_int"
    position_hex_string = basic_fns.get_position_string_from_position_int(first_position_int)
    length_to_retrieve = hex(last_position_int - first_position_int + 1).lstrip('0x')
    post_data = {
        'Type':'sample-position-variant',
        'Dataset':'all',
        'Note':'Expects entire population set to be returned with their phase A and phase B variant ids',
        'SampleId':[],
        'Position':[position_hex_string+"+"+length_to_retrieve]
    }
    post_data = json.dumps(post_data)
    try:
        post_response = requests.post(url="http://localhost:8080", data=post_data)
        response = json.loads(post_response.text)
    except requests.ConnectionError:
        raise requests.ConnectionError, "Lantern not responding on port 8080"
    assert "success" == response['Type'], "Lantern-communication failure:" + response['Message']
    humans = response['Result']
    human_names_returned = sorted(humans.keys())
    assert human_names_returned == human_names, "Returned list of human samples does not match the samples provided (or returned by error checking)"
    return humans
