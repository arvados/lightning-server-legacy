import json
import requests
import re
import string

from django.db.models import Q
from django.conf import settings

from tile_library.models import TileLocusAnnotation, GenomeStatistic, TileVariant, Tile
import tile_library.basic_functions as fns
import tile_library.query_functions as query_fns
from errors import EmptyPathError, MissingStatisticsError, UnexpectedLanternBehaviorError, CallsetNameDoesNotExist

def get_population_names_and_check_lantern_version():
    """
    Submits 'system-info' lantern query.
    Checks to make sure the lantern running is version 0.0.3
    Returns a list of human names

    Throws requests.ConnectionError, requests.Timeout, and UnexpectedLanternBehaviorError
    """
    ## Check that lantern version is the version that is expected
    post_data_check = {
        'Type':'system-info'
        }
    post_data_check = json.dumps(post_data_check)
    post_response = requests.post(url="http://localhost:8080", data=post_data_check, timeout=settings.LANTERN_TIMEOUT)
    try:
        response = json.loads(post_response.text)
    except ValueError:
        raise UnexpectedLanternBehaviorError("Lantern did not return a json-formatted response")
    if response['LanternVersion'] != '0.0.3':
        raise UnexpectedLanternBehaviorError("Lantern Version is expected to be 0.0.3. Lantern version running is %s" % (response['LanternVersion']))
    if response['Type'] != "success":
        raise UnexpectedLanternBehaviorError("Lantern-communication failure: %s" % (response['Message']))
    ## Create list of humans
    human_names = response['SampleId']
    return human_names

def make_sample_position_variant_query(position_query_string, human_subsection=[]):
    """
    Submits 'sample-position-variant' lantern query.
    Returns the json-formatted response of Lantern in python-friendly format

    Throws requests Exceptions and UnexpectedLanternBehaviorError
    """
    post_data = {
        'Type':'sample-position-variant',
        'Dataset':'all',
        'Note':'Expects entire population set to be returned with their phase A and phase B variant ids',
        'SampleId':human_subsection,
        'Position': [position_query_string]
    }
    post_data = json.dumps(post_data)
    post_response = requests.post(url="http://localhost:8080", data=post_data, timeout=settings.LANTERN_TIMEOUT)
    try:
        response = json.loads(post_response.text)
    except ValueError:
        raise UnexpectedLanternBehaviorError("Lantern did not return a json-formatted response")
    if response['Type'] != "success":
        raise UnexpectedLanternBehaviorError("Lantern-communication failure: %s" % (response['Message']))
    return response

def get_population_sequences_over_position_range(first_position_int, last_position_int, sub_population_list=[]):
    def convert_to_cgf(position_int):
        v, p, s = fns.get_position_strings_from_position_int(position_int)
        return string.join([p, v, s], '.')
    """
    Expects range to be inclusive
    Submits 'sample-position-variant' lantern query.
    Runs get_population_names_and_check_lantern_version() and uses that result to check the correct subsection of humans is returned.
        This hits the lantern database
    Checks to make sure no humans were added or subtracted in the result
    Returns the phase A and phase B variant ids of the entire population at the position pointed to by position_hex_string
        (dictionary. keys are human names, values are [[phase_A_cgf_string1, phase_A_cgf_string2, ...], [phase_B_cgf_string1, phase_B_cgf_string2, ...]])

    raises UnexpectedLanternBehaviorError, CallsetNameDoesNotExist, and requests Exceptions
    """
    human_names = get_population_names_and_check_lantern_version()
    for human in sub_population_list:
        if human not in human_names:
            raise CallsetNameDoesNotExist("%s is not loaded into Lantern" % (human))
    if sub_population_list == []:
        human_names = sorted(human_names)
    else:
        human_names = sorted(sub_population_list)
    version, first_path, step = fns.get_position_ints_from_position_int(first_position_int)
    version, last_path, step = fns.get_position_ints_from_position_int(last_position_int)
    position_hex_string = convert_to_cgf(first_position_int)
    last_position_hex_string = fns.get_position_string_from_position_int(last_position_int)
    assert last_position_int >= first_position_int, "Expects first_position_int (%s) to be less than last_position_int (%s)" % (position_hex_string, last_position_hex_string)
    if first_path == last_path:
        length_to_retrieve = hex(last_position_int - first_position_int + 1).lstrip('0x')
        response = make_sample_position_variant_query(position_hex_string+"+"+length_to_retrieve, human_subsection=sub_population_list)
        humans = response['Result']
        human_names_returned = sorted(humans.keys())
        if human_names_returned != human_names:
            raise UnexpectedLanternBehaviorError("Lantern error: sample-position-variant did not returned the requestd list of callsets")
    else:
        humans = {}
        for path in range(first_path, last_path+1):
            path_min_position_int, foo = fns.get_min_position_and_tile_variant_from_path_int(path)
            path_max_position_int = query_fns.get_highest_position_int_in_path(path)
            tmp_first_position_int = max(first_position_int, path_min_position_int)
            tmp_last_position_int = min(last_position_int, path_max_position_int)
            tmp_first_position_hex_string = convert_to_cgf(tmp_first_position_int)
            length_to_retrieve = hex(tmp_last_position_int - tmp_first_position_int + 1).lstrip('0x')
            response = make_sample_position_variant_query(tmp_first_position_hex_string+"+"+length_to_retrieve, human_subsection=sub_population_list)
            if humans == {}:
                humans = response['Result']
                human_names_returned = sorted(humans.keys())
                if human_names_returned != human_names:
                    raise UnexpectedLanternBehaviorError("Lantern error: sample-position-variant did not returned the requestd list of callsets")
            else:
                next_path_humans = response['Result']
                human_names_returned = sorted(next_path_humans.keys())
                if human_names_returned != human_names:
                    raise UnexpectedLanternBehaviorError("Lantern error: sample-position-variant did not returned the requestd list of callsets")
                for human in humans:
                    for i, sequence in enumerate(humans[human]):
                        humans[human][i] = sequence + next_path_humans[human][i]
    return humans

#def get_population_with_tile_variant_long_names(cgf_string):
#    """
#    Submits 'sample-tile-group-match' lantern query.
#    Returns a list of people which contain the tile variant
#    """
#    post_data = {
#        'Type':'sample-tile-group-match',
#        'Dataset':'all',
#        'Note':'Expects population set that contains variant to be returned',
#        'SampleId':[],
#        'TileGroupVariantId':[[cgf_string]]
#    }
#    post_data = json.dumps(post_data)
#    try:
#        post_response = requests.post(url="http://localhost:8080", data=post_data)
#        response = json.loads(post_response.text)
#    except ConnectionError:
#        raise ConnectionError, "Lantern not responding on port 8080"
#    except ValueError:
#        #first version of lantern doesn't return a valid json, so parse the return
#        m = re.match(r"(\[.*\])(\{.*\})", post_response.text)
#        response = json.loads(m.group(2))
#        result = json.loads('{"Result":' + m.group(1) +'}')
#        response['Result'] = result['Result']
#    assert "success" == response['Type'], "Lantern-communication failure:" + response['Message']
#    return response['Result']

#def get_population_with_tile_variant(cgf_string):
#    """
#    Submits 'sample-tile-group-match' lantern query.
#    Returns a list of people which contain the tile variant
#    """
#    large_file_names = get_population_with_tile_variant_long_names(cgf_string)
#    return [name.strip('" ').split('/')[-1] for name in large_file_names]
