import json
import requests
import re
import string

from django.db.models import Q

from tile_library.models import TileLocusAnnotation, GenomeStatistic, TileVariant, Tile
import tile_library.basic_functions as fns
from errors import EmptyPathError, MissingStatisticsError

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
