import json
import requests
import re

from django.db.models import Q

from tile_library.models import TileLocusAnnotation, GenomeStatistic, TileVariant, Tile
import tile_library.basic_functions as basic_fns
import tile_library.functions as fns

def get_tile_variants_spanning_into_position(tile_position_int):
    """
    Returns list of tile variants that start before tile_position_int but span into tile_position_int
    Returns empty list if no spanning tiles overlap with that position
    """
    spanning_tile_variants = []
    path_int, version_int, step_int = basic_fns.get_position_ints_from_position_int(tile_position_int)
    #raises AssertionError if tile_position_int is not an integer, negative, or an invalid tile position
    try:
        tile = Tile.objects.get(tilename=tile_position_int)
        num_tiles_spanned = int(GenomeStatistic.objects.get(path_name=path_int).max_num_positions_spanned)
        num_tiles_spanned = min(num_tiles_spanned, step_int+1) #Only need to look back as far as there are steps in this path
        if num_tiles_spanned > 1:
            for i in range(2, num_tiles_spanned+1):
                if i == 2:
                    curr_Q = (Q(tile_id=tile_position_int-i) & Q(num_positions_spanned__gte=i))
                else:
                    curr_Q = curr_Q | (Q(tile_id=tile_position_int-i) & Q(num_positions_spanned__gte=i))
            spanning_tile_variants = TileVariant.objects.filter(curr_Q).all()
        return spanning_tile_variants
    except Tile.DoesNotExist:
        raise Exception("Tile position int must be the primary key to a Tile object loaded into the population")
    except GenomeStatistic.DoesNotExist:
        raise Exception('GenomeStatistic for that path does not exist')

def get_population_with_tile_variant(cgf_string):
    """
    Submits a lantern query. Returns a list of people which contain the tile variant
    """
    post_data = {
        'Type':'sample-tile-group-match',
        'Dataset':'all',
        'Note':'Expects population set that contains variant to be returned',
        'SampleId':[],
        'TileGroupVariantId':[[cgf_string]]
    }
    post_data = json.dumps(post_data)
    post_response = requests.post(url="http://localhost:8080", data=post_data)
    try:
        response = json.loads(post_response.text)
    except ValueError:
        #first version of lantern doesn't return a valid json, so parse the return
        m = re.match(r"(\[.*\])(\{.*\})", post_response.text)
        response = json.loads(m.group(2))
        result = json.loads('{"Result":' + m.group(1) +'}')
        response['Result'] = result['Result']
    assert "success" == response['Type'], "Lantern-communication failure:" + response['Message']
    large_file_names = response['Result']
    retlist = [name.strip('" ').split('/')[-1] for name in large_file_names]
    return retlist
