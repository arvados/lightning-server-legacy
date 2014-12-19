import time
import json
import requests
import re

from django.shortcuts import render
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from django.db.models import Q

from variant_query.forms import SearchForm
from tile_library.models import TileLocusAnnotation, GenomeStatistic, TileVariant
import tile_library.basic_functions as basic_fns
import tile_library.functions as fns

def get_humans_with_base_change(base_position, tile_position_int, spanning_tiles_to_check):
    def get_population_repr_of_tile_var(cgf_string):
        post_data = {
                'Type':'sample-tile-group-match',
                'Dataset':'all',
                'Note':'expect population set to be returned from a match of variant',
                'SampleId':[],
                'TileGroupVariantId':[[cgf_string]]
            }
        post_data = json.dumps(post_data)
        post_response = requests.post(url="http://localhost:8080", data=post_data)
        m = re.match('\[(.*)\](\{.+\})', post_response.text)
        assert "success" == json.loads(m.group(2))['Type'], "Lantern-communication failure"
        large_file_names = m.group(1).split(',')
        retlist = [name.strip('" ').split('/')[-1] for name in large_file_names]
        return retlist
    humans = {}
    low_variant_int = basic_fns.convert_position_int_to_tile_variant_int(tile_position_int)
    high_variant_int = basic_fns.convert_position_int_to_tile_variant_int(tile_position_int+1)-1
    tile_variants = TileVariant.objects.filter(tile_variant_name__range=(low_variant_int, high_variant_int)).all()
    for tile_variant in tile_variants:
        cgf_str = tile_variant.conversion_to_cgf
        base_call = tile_variant.getBaseAtPosition(base_position)
        matching_humans = get_population_repr_of_tile_var(cgf_str)
        for hu in matching_humans:
            if hu != '':
                if hu in humans:
                    humans[hu][0] += ", "+base_call
                    humans[hu][1] += ", "+cgf_str
                else:
                    humans[hu] = [base_call, cgf_str]
    for tile_variant in spanning_tiles_to_check:
        cgf_str = tile_variant.conversion_to_cgf
        base_call = tile_variant.getBaseAtPosition(base_position)
        matching_humans = get_population_repr_of_tile_var(cgf_str)
        for hu in matching_humans:
            if hu != '':
                if hu in humans:
                    humans[hu][0] += ", "+base_call
                    humans[hu][1] += ", "+cgf_str
                else:
                    humans[hu] = [base_call, cgf_str]
    ## humans expected to be list of dictionaries with keys "name" and "base"
    retlist = []
    for human in humans:
        retlist.append({'name':human, 'base':humans[human][0], 'tile_variants':humans[human][1]})
    return retlist

def get_spanning_tiles(tile_position_int):
    """ ignores any spanning tiles started at the given position. Only looks backward
        returns an empty list if no spanning tiles overlap with that position """
    spanning_tile_variants = []
    path_int, version_int, step_int = basic_fns.get_position_ints_from_position_int(tile_position_int)
    num_tiles_spanned = int(GenomeStatistic.objects.get(path_name=path_int).max_num_positions_spanned)
    num_tiles_spanned = min(num_tiles_spanned, step_int+1)
    if num_tiles_spanned > 1:
        for i in range(2, num_tiles_spanned+1):
            if i == 2:
                curr_Q = (Q(tile_id=tile_position_int-i) & Q(num_positions_spanned__gte=i))
            else:
                curr_Q = curr_Q | (Q(tile_id=tile_position_int-i) & Q(num_positions_spanned__gte=i))
        spanning_tile_variants = TileVariant.objects.filter(curr_Q).all()
    return spanning_tile_variants

def index(request):
    """
        Submit a variant query
        Query specs:
            Assembly
            Chromosome
            Target base (0-indexed, 1-indexed)
        More advanced query specs:
            k-bases upstream and downstream from target base
            Population subset
    """
    assembly_converter = dict(TileLocusAnnotation.SUPPORTED_ASSEMBLY_CHOICES)
    chrom_converter = dict(TileLocusAnnotation.CHR_CHOICES)
    possible_assemblies_int = TileLocusAnnotation.objects.order_by(
        'assembly').distinct('assembly').values_list('assembly', flat=True)
    possible_chromosomes_int = TileLocusAnnotation.objects.order_by(
        'chromosome').distinct('chromosome').values_list('chromosome', flat=True)
    t2 = time.time()
    possible_assemblies = [(i, assembly_converter[i]) for i in possible_assemblies_int]
    t3 = time.time()
    possible_chromosomes = [(i, chrom_converter[i]) for i in possible_chromosomes_int]
    t4 = time.time()
    if request.GET.get('assembly') != None:
        #We were asked for something!
        data = request.GET
        form = SearchForm(possible_assemblies, possible_chromosomes, data)
        assembly = data['assembly']
        chromosome = data['chromosome']
        base_int = int(data['target_base'])
        if int(data['indexing']) == 1:
            base_int -= 1
        t5 = time.time()
        base_query = TileLocusAnnotation.objects.filter(assembly=assembly).filter(chromosome=chromosome)
        try:
            locus = base_query.filter(begin_int__lte=base_int).filter(end_int__gt=base_int).get()
            tile_position = locus.tile
            tile_position_int = int(tile_position.tilename)
            tile_position_name = basic_fns.get_position_string_from_position_int(tile_position_int)
            position_base_int = base_int - int(locus.begin_int)
            
            #This tile_position_name can be used to query the majority of the population.
            #   However, we still need to get spanning tiles that don't start on this position
            #   but still overlap it
            spanning_tile_variants = get_spanning_tiles(tile_position_int)
            humans = get_humans_with_base_change(position_base_int, tile_position_int, spanning_tile_variants)
            response = {'text':'Success!', 'humans':humans}
        except ObjectDoesNotExist:
            smallest_int = base_query.order_by('begin_int').first().begin_int
            largest_int = base_query.order_by('end_int').first().end_int
            response_text = "That locus is not loaded into this library. Try a number in the range %i to %i." % (smallest_int, largest_int)
            response = {'text': response_text}
        t6 = time.time()
        response['time'] = t6-t5
    else:
        form=SearchForm(possible_assemblies, possible_chromosomes)
        response = None
    return render(request, 'variant_query/index', {'form':form, 'time1':t3-t2, 'time2':t4-t3, 'response': response})

