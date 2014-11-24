from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseServerError, HttpResponseRedirect, Http404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.template import RequestContext
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.db.models import Prefetch, Q, Avg, Count, Max, Min

import string
import requests
import json
import re

from tile_library.models import Tile, TileVariant, TileLocusAnnotation, GenomeStatistic, GenomeVariant
import tile_library.basic_functions as base_fns
import tile_library.functions as functions
import genes.functions as gene_fns
from genes.models import GeneXRef

######################################################################################
################################# Helper Functions ###################################
######################################################################################

def get_positions_no_annotations(*tile_filter_args, **tile_filter_kwargs):
    tilevariants = TileVariant.objects.annotate(num_annotations=Count('genome_variants'))
    positions = Tile.objects.filter(*tile_filter_args, **tile_filter_kwargs).order_by('tilename').distinct('tilename')
    positions = positions.prefetch_related(
        Prefetch('tile_variants', queryset=tilevariants, to_attr='tilevar_with_ann'),
        Prefetch('starting_genome_variants', to_attr='approx_genomevar')
        )
    return positions

def get_positions_tile_variant_annotations(*tile_filter_args, **tile_filter_kwargs):
    tilevariants = TileVariant.objects.annotate(num_annotations=Count('genome_variants'))
    positions = Tile.objects.filter(*tile_filter_args, **tile_filter_kwargs)
    positions = positions.prefetch_related(
        Prefetch('tile_variants', queryset=tilevariants, to_attr='tilevar_with_ann'),
        Prefetch('starting_genome_variants', to_attr='approx_genomevar')
        ).annotate(
            num_var=Count('tile_variants'), min_len=Min('tile_variants__length'), avg_len=Avg('tile_variants__length'),
            max_len=Max('tile_variants__length'), avg_pos_spanned=Avg('tile_variants__num_positions_spanned'),
            max_pos_spanned=Max('tile_variants__num_positions_spanned'))
    return positions

def get_positions_starting_genome_variant_annotations(*tile_filter_args, **tile_filter_kwargs):
    tilevariants = TileVariant.objects.annotate(num_annotations=Count('genome_variants'))
    positions = Tile.objects.filter(*tile_filter_args, **tile_filter_kwargs)
    positions = positions.prefetch_related(
        Prefetch('tile_variants', queryset=tilevariants, to_attr='tilevar_with_ann'),
        Prefetch('starting_genome_variants', to_attr='approx_genomevar')
        ).annotate(num_pos_annotations=Count('starting_genome_variants'))
    return positions


def get_positions(min_accepted, max_accepted):
    return get_positions_tile_variant_annotations(tilename__range=(min_accepted, max_accepted))

def get_partial_positions(positions, ordering, num_tiles_per_page, page):
    if ordering == 'desc_tile':
        positions = positions.order_by('-tilename')
    elif ordering == 'desc_var':
        positions = positions.order_by('-num_var')
    elif ordering == 'asc_var':
        positions = positions.order_by('num_var')
    elif ordering == 'desc_min_len':
        positions = positions.order_by('-min_len')
    elif ordering == 'asc_min_len':
        positions = positions.order_by('min_len')
    elif ordering == 'desc_avg_len':
        positions = positions.order_by('-avg_len')
    elif ordering == 'asc_avg_len':
        positions = positions.order_by('avg_len')
    elif ordering == 'desc_max_len':
        positions = positions.order_by('-max_len')
    elif ordering == 'asc_max_len':
        positions = positions.order_by('max_len')
    elif ordering == 'desc_avg_positions_spanned':
        positions = positions.order_by('-avg_pos_spanned')
    elif ordering == 'asc_avg_positions_spanned':
        positions = positions.order_by('avg_pos_spanned')
    elif ordering == 'desc_max_positions_spanned':
        positions = positions.order_by('-max_pos_spanned')
    elif ordering == 'asc_max_positions_spanned':
        positions = positions.order_by('max_pos_spanned')
    paginator = Paginator(positions, num_tiles_per_page)
    try:
        partial_positions = paginator.page(page)
    except PageNotAnInteger:
        #Deliver the first page
        partial_positions = paginator.page(1)
    except EmptyPage:
        #If page is out of range, deliver last page of results
        partial_positions = paginator.page(paginator.num_pages)
        #hit the boundaries of using queries
    return partial_positions

def parse_request_to_partial_positions(request, positions):
    ordering = request.GET.get('ordering')
    page = request.GET.get('page')
    num_per_page = request.GET.get('num')
    if num_per_page == None:
        num_per_page = 16
    partial_positions = get_partial_positions(positions,ordering,num_per_page,page)
    return partial_positions

def get_population_repr_of_tile_variants(tiles, spanning_tiles):
    def get_population_repr_of_tile_var(tile_variant, tile_to_popul, total_people):
        assert tile_variant.tile_variant_name not in tile_to_popul
        post_data = {
            'Type':'sample-tile-group-match',
            'Dataset':'all',
            'Note':'expect population set to be returned from a match of variant',
            'SampleId':[],
            'TileGroupVariantId':[]
        }
        tile_var_cgf_string = tile_variant.conversion_to_cgf
        if tile_var_cgf_string == '':
            tile_var_cgf_string = base_fns.get_tile_variant_string_from_tile_variant_int(int(tile_variant.tile_variant_name))
        post_data['TileGroupVariantId'].append([tile_var_cgf_string])
        post_data = json.dumps(post_data)
        post_response = requests.post(url="http://localhost:8080", data=post_data)
        m = re.match('\[(.*)\](\{.+\})', post_response.text)
        assert "success" == json.loads(m.group(2))['Type'], "Lantern-communication failure"
        if m.group(1) == '':
            num_matching_people = 0
        else:
            num_matching_people = len(m.group(1).split(','))
        tile_to_popul[tile_variant.tile_variant_name] = num_matching_people
        total_people += num_matching_people
        return tile_to_popul, total_people
        
    tile_to_popul = {}
    total_people = 0
    for tile in tiles:
        tile_to_popul, total_people = get_population_repr_of_tile_var(tile, tile_to_popul, total_people)
    for tile in spanning_tiles:
        tile_to_popul, total_people = get_population_repr_of_tile_var(tile, tile_to_popul, total_people)
    return tile_to_popul, total_people

######################################################################################
########################### Overall Statistics Views #################################
######################################################################################

def overall_statistics(request):
    """Whole Genome Stats + 26 Chromosome Stats """
    chromosomes = GenomeStatistic.NAME_CHOICES
    chromosomes = [name for i, name in chromosomes]
        #range is inclusive, and we want the 26 chromosomes and the entire genome
    statistics = GenomeStatistic.objects.filter(statistics_type__range=(0,26)).order_by('statistics_type')
    if len(statistics) == 0:
        statistics_with_names = []
    else:
        statistics_with_names = zip(statistics, chromosomes)
    context = {
        'stats':statistics_with_names,
        }
    return render(request, 'tile_library/statistics.html', context)

def chr_statistics(request, chr_int):
    """Chromosome Stats and all paths in that Chromosome """
    chr_int = int(chr_int)
    if chr_int <= 0 or chr_int >= len(Tile.CHR_PATH_LENGTHS):
        raise Http404("Incorrect format for Chromosome Integer, not recognized")
    chr_name = functions.get_chromosome_name_from_chromosome_int(chr_int)
    try:
        chr_stats = GenomeStatistic.objects.get(statistics_type=chr_int)
        chr_path_lengths=Tile.CHR_PATH_LENGTHS
        paths = range(chr_path_lengths[chr_int-1], chr_path_lengths[chr_int])
        path_info = GenomeStatistic.objects.filter(statistics_type=27).filter(path_name__range=(chr_path_lengths[chr_int-1], chr_path_lengths[chr_int]-1)).order_by('path_name')
        path_objects = [(i, hex(i).lstrip('0x').zfill(1), Tile.CYTOMAP[i], path_obj) for (i, path_obj) in zip(paths, path_info)]
        context = {
            'chromosome_int':chr_int,
            'chromosome_name':chr_name,
            'chromosome_stats':chr_stats,
            'paths':path_objects,
            }
        return render(request, 'tile_library/chr_statistics.html', context)
    except ObjectDoesNotExist:
        context = {
            'chromosome_int':chr_int,
            'chromosome_name':chr_name,
            }
        return render(request, 'tile_library/chr_statistics.html', context)

def path_statistics(request, chr_int, path_int):
    """path_int Path Stats and the pagination of all tiles in that path """
    chr_int = int(chr_int)
    if chr_int <= 0 or chr_int >= len(Tile.CHR_PATH_LENGTHS):
        raise Http404("Incorrect format for Chromosome Integer, not recognized")
    chr_name = functions.get_chromosome_name_from_chromosome_int(chr_int)
    path_int = int(path_int)
    if path_int < Tile.CHR_PATH_LENGTHS[chr_int-1] or path_int >= Tile.CHR_PATH_LENGTHS[chr_int]:
        raise Http404("Incorrect format for Path Integer given Chromosome Integer, not recognized")
    context = {
            'request':request,
            'chromosome_int': chr_int,
            'chromosome': chr_name,
            'path_int':path_int,
            'path_hex':hex(path_int).lstrip('0x').zfill(1),
            'path_cyto':Tile.CYTOMAP[path_int],
            }
    try:
        path = GenomeStatistic.objects.get(path_name=path_int)
    except ObjectDoesNotExist:
        return render(request, 'tile_library/path_statistics.html', context)
    
    min_accepted, foo = functions.get_min_position_and_tile_variant_from_path_int(path_int)
    max_accepted, foo = functions.get_min_position_and_tile_variant_from_path_int(path_int+1)
    max_accepted -= 1
    
    positions = get_positions(min_accepted, max_accepted)
    context['path'] = path
    context['positions'] = parse_request_to_partial_positions(request, positions)
    return render(request, 'tile_library/path_statistics.html', context)

def abbrev_tile_view(request,  tilename):
    tile_int = int(tilename)
    path_int, version, step = base_fns.get_position_ints_from_position_int(tile_int)
    chr_int = functions.get_chromosome_int_from_path_int(path_int)
    return HttpResponseRedirect(reverse('tile_library:tile_view', args=(chr_int, path_int, tile_int)))

def tile_view(request, chr_int, path_int, tilename):
    chr_int = int(chr_int)
    if chr_int <= 0 or chr_int >= len(Tile.CHR_PATH_LENGTHS):
        raise Http404("Incorrect Chromosome Integer, not recognized")
    chr_name = functions.get_chromosome_name_from_chromosome_int(chr_int)
    path_int = int(path_int)
    if path_int < Tile.CHR_PATH_LENGTHS[chr_int-1] or path_int >= Tile.CHR_PATH_LENGTHS[chr_int]:
        raise Http404("Incorrect Path Integer given Chromosome Integer, not recognized")
    tile_int = int(tilename)
    min_tile_int, foo = functions.get_min_position_and_tile_variant_from_path_int(path_int)
    max_tile_int, foo = functions.get_min_position_and_tile_variant_from_path_int(path_int+1)
    if tile_int < min_tile_int or tile_int >= max_tile_int:
        raise Http404("Incorrect Tile Integer given Path Integer, not recognized")
    position_name = base_fns.get_position_string_from_position_int(tile_int)
    context = {
        'chr_int': chr_int,
        'chr_name': chr_name,
        'path_int':path_int,
        'path_hex': hex(path_int).lstrip('0x').zfill(1),
        'path_name': Tile.CYTOMAP[path_int],
        'position_name':position_name
        }
    try:
        path = GenomeStatistic.objects.get(path_name=path_int)
        position = Tile.objects.get(pk=tile_int)
        #TODO: Check this assumption
        #   GenomeVariant needs to look-back at most one position
        if tile_int == min_tile_int:
            genome_variants = GenomeVariant.objects.filter(start_tile_position=tile_int)
            tiles = position.tile_variants.filter(num_positions_spanned=1)
            spanning_tiles = position.tile_variants.filter(num_positions_spanned__gt=1)
        else:
            prev_ref_length = TileVariant.objects.filter(tile_id=tile_int-1).get(variant_value=0).length
            context['prev_ref_length'] = prev_ref_length
            genome_variants = GenomeVariant.objects.filter(Q(start_tile_position=tile_int) | Q(end_tile_position=tile_int) |
                                               (Q(end_tile_position=tile_int-1) & Q(end_increment__gte=prev_ref_length-24)))
            num_look_back_tiles = path.max_num_positions_spanned
            for i in range(num_look_back_tiles):
                if i == 0:
                    curr_Q = Q(tile_id=tile_int)
                else:
                    curr_Q = curr_Q | (Q(tile_id=tile_int-i) & Q(num_positions_spanned__gt=i))
            tiles = position.tile_variants.filter(num_positions_spanned=1)
            spanning_tiles = TileVariant.objects.filter(curr_Q).filter(num_positions_spanned__gt=1)
    except ObjectDoesNotExist:
        return render(request, 'tile_library/tile_view.html', context)
    context['position'] = position
    context['tiles'] = tiles
    context['spanning_tiles'] = spanning_tiles
    context['genome_variants'] = genome_variants
    tile_to_popul, num_people = get_population_repr_of_tile_variants(tiles, spanning_tiles)
    context['total_people'] = num_people
    context['tile_to_popul'] = tile_to_popul
    return render(request, 'tile_library/tile_view.html', context)

######################################################################################
################################## Locus Query View  #################################
######################################################################################

def view_locus_range(request, assembly_int, chr_int, lower_int, upper_int):
    assembly_int = int(assembly_int)
    supported_assembly_ints, supported_assembly_names = zip(*TileLocusAnnotation.SUPPORTED_ASSEMBLY_CHOICES)
    if assembly_int not in supported_assembly_ints:
        raise Http404("Unsupported assembly integer, not recognized")
    chr_int = int(chr_int)
    if chr_int <= 0 or chr_int >= len(Tile.CHR_PATH_LENGTHS):
        raise Http404("Incorrect format for Chromosome Integer, not recognized")
    chr_name = functions.get_chromosome_name_from_chromosome_int(chr_int)
    lower_int = int(lower_int)
    upper_int = int(upper_int)
    min_list = TileLocusAnnotation.objects.filter(assembly=assembly_int).filter(chromosome=chr_int).filter(begin_int__lte=lower_int).order_by('begin_int')
    max_list = TileLocusAnnotation.objects.filter(assembly=assembly_int).filter(chromosome=chr_int).filter(begin_int__lte=lower_int).order_by('-end_int')
    if min_list.count() == 0 or max_list.count() == 0:
        raise Http404("Unable to locate tiles within that locus range")
    min_accepted = min_list.first().tile.tilename
    max_accepted = max_list.first().tile.tilename
    positions = get_positions(min_accepted, max_accepted)
    partial_positions = parse_request_to_partial_positions(request, positions)
    context = {
            'request':request,
            'window_title':"Lightning: Tile Library Statistics for Loci Range",
            'breadcrumb_title': "Loci "+str(lower_int) +"-"+str(upper_int),
            'page_title':"Tile Library Statistics: Loci Range "+str(lower_int) +"-"+str(upper_int),
            'tile_url': 'tile_library:abbrev_tile_view',
            'chromosome_int': chr_int,
            'chromosome': chr_name,
            'positions': partial_positions,
            }
    return render(request, 'tile_library/search_response_positions_sortable', context)

######################################################################################
################################# rsID Search Views  #################################
######################################################################################

def rs_id_search_exact(request, rs_id):
    return rs_id_search(request, rs_id, exact=True)

def rs_id_search(request, rs_id, exact=False):
    tilevariants = TileVariant.objects.annotate(num_annotations=Count('genome_variants'))
    if exact:
        tile_url = 'tile_library:rs_id_tile_view_exact'
        page_title = 'Tile Positions containing the exact rsID: "'+ rs_id + '"'
        filter_arg = Q(starting_genome_variants__names__icontains=rs_id+"\t"
                       ) | Q(starting_genome_variants__names__iendswith=rs_id
                             ) | Q(ending_genome_variants__names__icontains=rs_id+"\t"
                                   ) | Q(ending_genome_variants__names__iendswith=rs_id)
    else:
        tile_url = 'tile_library:rs_id_tile_view'
        page_title = 'Tile Positions containing ' + rs_id
        filter_arg = Q(starting_genome_variants__names__icontains=rs_id) | Q(ending_genome_variants__names__icontains=rs_id)
    positions = get_positions_no_annotations(filter_arg)
    partial_positions = parse_request_to_partial_positions(request, positions)
    context = {
        'request':request,
        'window_title': "Lightning: Tile Positions containing " + rs_id,
        'breadcrumb_title': rs_id,
        'page_title': page_title,
        'positions': partial_positions,
        'tile_url': tile_url,
        'tile_specification':rs_id,
        }
    return render(request, 'tile_library/search_response_positions', context)

def rs_id_tile_view_exact(request, rs_id, position_int):
    return rs_id_tile_view(request, rs_id, position_int, exact=True)

def rs_id_tile_view(request, rs_id, position_int, exact=False):
    #TODO: assert Genome Variants length > 0
    if exact:
        query_descr = "Exactly match " + rs_id
        breadcrumb_url = 'tile_library:rs_id_search_exact'
    else:
        query_descr = "Containing " + rs_id
        breadcrumb_url = 'tile_library:rs_id_search'
    position_int = int(position_int)
    position_name = base_fns.get_position_string_from_position_int(position_int)
    path_int, version_int, step_int = base_fns.get_position_ints_from_position_int(position_int)
    min_position_int, foo = functions.get_min_position_and_tile_variant_from_path_int(path_int)
    chr_int = functions.get_chromosome_int_from_path_int(path_int)
    path_hex = hex(path_int).lstrip('0x').zfill(1)
    path_name = Tile.CYTOMAP[path_int]
    chr_name = functions.get_chromosome_name_from_chromosome_int(chr_int)
    context = {
        'window_title': "Lightning: Position "+ position_name + " - query on rsID",
        'genome_position':"(Path " + path_hex + ", "+chr_name + path_name + ")",
        'query_description': query_descr,
        'breadcrumb_url': breadcrumb_url,
        'breadcrumb_title': rs_id,
        'breadcrumb_arg': rs_id,
        }
    try:
        path = GenomeStatistic.objects.get(path_name=path_int)
        position = Tile.objects.get(pk=position_int)
        #TODO: Check this assumption
        #   GenomeVariant needs to look-back at most one position
        if position_int == min_position_int:
            genome_variants = GenomeVariant.objects.filter(start_tile_position=position_int)
            tiles = position.tile_variants.filter(num_positions_spanned=1)
            spanning_tiles = position.tile_variants.filter(num_positions_spanned__gt=1)
        else:
            prev_ref_length = TileVariant.objects.filter(tile_id=position_int-1).get(variant_value=0).length
            context['prev_ref_length'] = prev_ref_length
            genome_variants = GenomeVariant.objects.filter(Q(start_tile_position=position_int) | Q(end_tile_position=position_int) |
                                               (Q(end_tile_position=position_int-1) & Q(end_increment__gte=prev_ref_length-24)))
            num_look_back_tiles = path.max_num_positions_spanned
            for i in range(num_look_back_tiles):
                if i == 0:
                    curr_Q = Q(tile_id=position_int)
                else:
                    curr_Q = curr_Q | (Q(tile_id=position_int-i) & Q(num_positions_spanned__gt=i))
            tiles = position.tile_variants.filter(num_positions_spanned=1)
            spanning_tiles = TileVariant.objects.filter(curr_Q).filter(num_positions_spanned__gt=1)
    except ObjectDoesNotExist:
        return render(request, 'tile_library/search_response_tile_variants', context)
    context['position'] = position
    context['all_genome_variants'] = genome_variants
    if exact:
        context['tiles'] = tiles.filter(Q(genome_variants__names__icontains=rs_id+'\t')| Q(genome_variants__names__iendswith=rs_id)
                                        ).order_by('tile_variant_name').distinct('tile_variant_name')
        context['spanning_tiles'] = spanning_tiles.filter(
            Q(genome_variants__names__icontains=rs_id+'\t') | Q(genome_variants__names__iendswith=rs_id)
            ).order_by('tile_variant_name').distinct('tile_variant_name')
        context['queried_genome_variants'] = genome_variants.filter(Q(names__icontains=rs_id+'\t') | Q(names__iendswith=rs_id))
    else:
        context['tiles'] = tiles.filter(genome_variants__names__icontains=rs_id).order_by('tile_variant_name').distinct('tile_variant_name')
        context['spanning_tiles'] = spanning_tiles.filter(genome_variants__names__icontains=rs_id).order_by('tile_variant_name').distinct('tile_variant_name')
        context['queried_genome_variants'] = genome_variants.filter(names__icontains=rs_id)
    tiles = context['tiles']
    spanning_tiles = context['spanning_tiles']
    tile_to_popul, num_people = get_population_repr_of_tile_variants(tiles, spanning_tiles)
    context['total_people'] = num_people
    context['tile_to_popul'] = tile_to_popul
    return render(request, 'tile_library/search_response_tile_variants', context)


######################################################################################
############################ Locus Variant Query View ################################
######################################################################################

def tile_variant_view(request, assembly_int, chr_int, locus, reference, mutation):
    assembly_int = int(assembly_int)
    supported_assembly_ints, supported_assembly_names = zip(*TileLocusAnnotation.SUPPORTED_ASSEMBLY_CHOICES)
    if assembly_int not in supported_assembly_ints:
        raise Http404("Unsupported assembly integer, not recognized")
    chr_int = int(chr_int)
    if chr_int <= 0 or chr_int >= len(Tile.CHR_PATH_LENGTHS):
        raise Http404("Incorrect format for Chromosome Integer, not recognized")
    chr_name = functions.get_chromosome_name_from_chromosome_int(chr_int)
    locus = int(locus)
    
    positions = TileLocusAnnotation.objects.filter(assembly=assembly_int).filter(chromosome=chr_int).filter(begin_int__lte=locus).filter(end_int__gte=locus)
    if positions.exists():
        found = False
        matching_genome_variants = []
        for position in positions:
            position_int = position.tile_id
            start_int = locus - position.begin_int - 1
            if start_int <= 24:
                genome_variant_position = position_int-1
                genome_variant = GenomeVariant.objects.filter(reference_bases=reference).filter(alternate_bases=mutation).filter(start_increment=start_int).filter(
                    start_tile_position_id=position_int-1)
            else:
                genome_variant_position = position_int
                genome_variant = GenomeVariant.objects.filter(reference_bases=reference).filter(alternate_bases=mutation).filter(start_increment=start_int).filter(
                    start_tile_position_id=position_int)
            if genome_variant.exists():
                found = True
                matching_genome_variants.extend(genome_variant.all())
        if not found or len(matching_genome_variants) == 0:
            raise Http404("Unable to find a variant in this library starting at the locus 'chr%d:%d' \
                           with a reference sequence of %s and alternate sequence of %s" % (chr_int, locus, reference, mutation))
        elif len(matching_genome_variants) > 1:
            raise Http404("Found multiple variants in this library starting at the locus 'chr%d:%d' \
                           with a reference sequence of %s and alternate sequence of %s" % (chr_int, locus, reference, mutation))
        else:
            queried_variant = matching_genome_variants[0]
            position_int = int(genome_variant_position)
            position_name = base_fns.get_position_string_from_position_int(position_int)
            position = Tile.objects.get(pk=position_int)
            path_int, version_int, step_int = base_fns.get_position_ints_from_position_int(position_int)
            min_position_int, foo = functions.get_min_position_and_tile_variant_from_path_int(path_int)
            path_hex = hex(path_int).lstrip('0x').zfill(1)
            path_name = Tile.CYTOMAP[path_int]
            context = {
                'window_title': "Lightning: Position "+ position_name + " - query on variant",
                'genome_position': "(Path " + path_hex + ", "+chr_name + path_name + ")",
                'query_description': "Variant starting at " + chr_name + ":" + str(locus) + ' with reference sequence "' + reference + '" and alternate sequence "' + mutation + '"',
                'position':position,
                'queried_genome_variants':[queried_variant],
                }
            try:
                path = GenomeStatistic.objects.get(path_name=path_int)
                if position_int == min_position_int:
                    all_genome_variants = GenomeVariant.objects.filter(start_tile_position=position_int)
                    tiles = position.tile_variants.filter(num_positions_spanned=1)
                    spanning_tiles = position.tile_variants.filter(num_positions_spanned__gt=1)
                else:
                    prev_ref_length = TileVariant.objects.filter(tile_id=position_int-1).get(variant_value=0).length
                    context['prev_ref_length'] = prev_ref_length
                    genome_variants = GenomeVariant.objects.filter(Q(start_tile_position=position_int) | Q(end_tile_position=position_int) |
                                                       (Q(end_tile_position=position_int-1) & Q(end_increment__gte=prev_ref_length-24)))
                    num_look_back_tiles = path.max_num_positions_spanned
                    for i in range(num_look_back_tiles):
                        if i == 0:
                            curr_Q = Q(tile_id=position_int)
                        else:
                            curr_Q = curr_Q | (Q(tile_id=position_int-i) & Q(num_positions_spanned__gt=i))
                    tiles = position.tile_variants.filter(num_positions_spanned=1)
                    spanning_tiles = TileVariant.objects.filter(curr_Q).filter(num_positions_spanned__gt=1)
            except ObjectDoesNotExist:
                return render(request, 'tile_library/search_response_tile_variants', context)
            context['all_genome_variants'] = genome_variants
            context['tiles'] = tiles.filter(genome_variants=queried_variant).order_by('tile_variant_name').distinct('tile_variant_name')
            context['spanning_tiles'] = spanning_tiles.filter(genome_variants=queried_variant).order_by('tile_variant_name').distinct('tile_variant_name')
            tiles = context['tiles']
            spanning_tiles = context['spanning_tiles']
            tile_to_popul, num_people = get_population_repr_of_tile_variants(tiles, spanning_tiles)
            context['total_people'] = num_people
            context['tile_to_popul'] = tile_to_popul
            return render(request, 'tile_library/search_response_tile_variants', context)
    else:
        raise Http404("Unable to find a position in this library satisfying the locus 'chr%d:%d'" % (chr_int, locus))


######################################################################################
############################## Protein Search Views  ##############################
######################################################################################

def all_protein_changes(request):
    return HttpResponseRedirect(reverse('tile_library:protein_search', args=("_all",)))

def protein_search(request, protein):
    tilevariants = TileVariant.objects.annotate(num_annotations=Count('genome_variants'))
    if protein == "_all":
        breadcrumb_title = "Any predicted protein change"
        page_title = "Tile positions containing any protein mutation"
        filter_arg = Q(starting_genome_variants__info__icontains="amino_acid") | Q(ending_genome_variants__info__icontains="amino_acid")
    else:
        breadcrumb_title = 'Mutation in protein "'+protein+ '"'
        page_title = 'Tile Positions containing a change in protein "' + protein + '"'
        filter_arg = Q(starting_genome_variants__info__icontains=protein) | Q(ending_genome_variants__info__icontains=protein)

    positions = get_positions_no_annotations(filter_arg)
    partial_positions = parse_request_to_partial_positions(request, positions)
    context = {
        'request':request,
        'window_title': "Lightning: Tile Positions containing a predicted protein change",
        'breadcrumb_title': breadcrumb_title,
        'page_title': page_title,
        'positions': partial_positions,
        'tile_url': 'tile_library:protein_tile_view',
        'tile_specification':protein,
        }
    return render(request, 'tile_library/search_response_positions', context)

def protein_tile_view(request, protein, position_int):
    #TODO: assert Genome Variants length > 0
    if protein == "_all":
        breadcrumb_title = "Any predicted protein change"
        query_descr = "Containing any protein mutation"
    else:
        breadcrumb_title = 'Mutation in protein "'+protein+'"'
        query_descr = 'Containing a change in protein "' + protein + '"'
    position_int = int(position_int)
    position_name = base_fns.get_position_string_from_position_int(position_int)
    path_int, version_int, step_int = base_fns.get_position_ints_from_position_int(position_int)
    min_position_int, foo = functions.get_min_position_and_tile_variant_from_path_int(path_int)
    chr_int = functions.get_chromosome_int_from_path_int(path_int)
    chr_name = functions.get_chromosome_name_from_chromosome_int(chr_int)
    path_hex = hex(path_int).lstrip('0x').zfill(1)
    path_name = Tile.CYTOMAP[path_int]
    context = {
        'window_title': "Lightning: Position "+ position_name + " - query on variant",
        'breadcrumb_title': breadcrumb_title,
        'breadcrumb_url':'tile_library:protein_search',
        'breadcrumb_arg':protein,
        'genome_position': "(Path " + path_hex + ", "+chr_name + path_name + ")",
        'query_description':query_descr,
        }
    try:
        path = GenomeStatistic.objects.get(path_name=path_int)
        position = Tile.objects.get(pk=position_int)
        #TODO: Check this assumption
        #   GenomeVariant needs to look-back at most one position
        if position_int == min_position_int:
            genome_variants = GenomeVariant.objects.filter(start_tile_position=position_int)
            tiles = position.tile_variants.filter(num_positions_spanned=1)
            spanning_tiles = position.tile_variants.filter(num_positions_spanned__gt=1)
        else:
            prev_ref_length = TileVariant.objects.filter(tile_id=position_int-1).get(variant_value=0).length
            context['prev_ref_length'] = prev_ref_length
            genome_variants = GenomeVariant.objects.filter(Q(start_tile_position=position_int) | Q(end_tile_position=position_int) |
                                               (Q(end_tile_position=position_int-1) & Q(end_increment__gte=prev_ref_length-24)))
            num_look_back_tiles = path.max_num_positions_spanned
            for i in range(num_look_back_tiles):
                if i == 0:
                    curr_Q = Q(tile_id=position_int)
                else:
                    curr_Q = curr_Q | (Q(tile_id=position_int-i) & Q(num_positions_spanned__gt=i))
            tiles = position.tile_variants.filter(num_positions_spanned=1)
            spanning_tiles = TileVariant.objects.filter(curr_Q).filter(num_positions_spanned__gt=1)
    except ObjectDoesNotExist:
        return render(request, 'tile_library/search_response_tile_variants', context)
    context['position'] = position
    context['all_genome_variants'] = genome_variants
    if protein == '_all':
        context['tiles'] = tiles.filter(Q(genome_variants__info__icontains="amino_acid")).order_by('tile_variant_name').distinct('tile_variant_name')
        context['spanning_tiles'] = spanning_tiles.filter(Q(genome_variants__info__icontains="amino_acid")
            ).order_by('tile_variant_name').distinct('tile_variant_name')
        context['queried_genome_variants'] = genome_variants.filter(Q(info__icontains="amino_acid"))
    else:
        context['tiles'] = tiles.filter(genome_variants__info__icontains=protein).order_by('tile_variant_name').distinct('tile_variant_name')
        context['spanning_tiles'] = spanning_tiles.filter(genome_variants__info__icontains=protein).order_by('tile_variant_name').distinct('tile_variant_name')
        context['queried_genome_variants'] = genome_variants.filter(info__icontains=protein)
    tiles = context['tiles']
    spanning_tiles = context['spanning_tiles']
    tile_to_popul, num_people = get_population_repr_of_tile_variants(tiles, spanning_tiles)
    context['total_people'] = num_people
    context['tile_to_popul'] = tile_to_popul
    return render(request, 'tile_library/search_response_tile_variants', context)


######################################################################################
################################## Gene Query Views #################################
######################################################################################

def gene_view(request, gene_xref_id):
    try:
        gene = GeneXRef.objects.using('entire').get(pk=gene_xref_id)    
    except ObjectDoesNotExist:
        raise Http404("Gene Integer not recognized as a GeneXRef id")
    context = {'request':request, 'gene':gene}
    alias = gene.gene_aliases
    genes = GeneXRef.objects.using('entire').filter(gene_aliases=alias)
    overlapping_genes = gene_fns.split_genes_into_groups(genes, by_tile=True)
    if len(overlapping_genes) != 1:
        raise Http404('Require genes to interlap. Genes with that alias do not interlap')
    
    min_accepted = overlapping_genes[0][2]
    max_accepted = overlapping_genes[0][3]

    beg_path_int, beg_version_int, beg_step_int = base_fns.get_position_ints_from_position_int(min_accepted)
    beg_path_hex = hex(beg_path_int).lstrip('0x').zfill(1)
    beg_path_name = Tile.CYTOMAP[beg_path_int]
    
    chr_int = overlapping_genes[0][1]
    chr_name = functions.get_chromosome_name_from_chromosome_int(chr_int)

    end_path_int, end_version_int, end_step_int = base_fns.get_position_ints_from_position_int(max_accepted)
    if beg_path_int != end_path_int:
        end_path_hex = hex(end_path_int).lstrip('0x').zfill(1)
        end_path_name = Tile.CYTOMAP[end_path_int]
        position_info = {'beg_path_int':beg_path_int, 'beg_path_hex':beg_path_hex, 'beg_path_name':beg_path_name,
                         'end_path_int':end_path_int, 'end_path_hex':end_path_hex, 'end_path_name':end_path_name,
                         'chr_int':chr_int, 'chr_name':chr_name}
    else:
        position_info = {'end_path_int':beg_path_int, 'end_path_hex':beg_path_hex, 'end_path_name':beg_path_name,
                         'chr_int':chr_int, 'chr_name':chr_name}

    context['chromosome'] = position_info['chr_name']
    context['chromosome_int'] = position_info['chr_int']
    context['position_info'] = position_info

    positions = get_positions(min_accepted, max_accepted)
    if positions.count() > 0:
        try:
            exon_dict = gene_fns.annotate_positions_with_exons_overlapping_genes(overlapping_genes, positions)
        except BaseException as e:
            raise Http404(str(e))
        partial_positions = parse_request_to_partial_positions(request, positions)
        for pos in partial_positions:
            pos.has_exon = exon_dict[int(pos.tilename)]
        context['positions'] = partial_positions
        context['exon_dict'] = exon_dict

    return render(request, 'tile_library/gene_view.html', context)


def tile_in_gene_view(request, gene_xref_id, tilename):
    def to_percent(l, info):
        return (int(l)-info['start'])/float(info['end']-info['start'])*100
    context = {}
    tile_int = int(tilename)
    context['position_name'] = string.join(list(base_fns.convert_position_int_to_position_hex_str(tile_int)), '.')
    context['position_int'] = tile_int
    path_int, version, step = base_fns.get_position_ints_from_position_int(tile_int)
    #Add path info to context
    context['path_int'] = path_int
    context['path_hex'] = hex(path_int).lstrip('0x').zfill(1)
    context['path_name'] = Tile.CYTOMAP[path_int]
    
    chr_int = functions.get_chromosome_int_from_path_int(path_int)
    #Add chromosome info to context
    context['chr_int'] = chr_int
    context['chr_name'] = functions.get_chromosome_name_from_chromosome_int(chr_int)
    try:
        gene = GeneXRef.objects.using('entire').get(pk=gene_xref_id)
        #Add gene to context
        context['gene'] = gene
    except ObjectDoesNotExist:
        raise Http404("Gene Integer not recognized as a GeneXRef id")

    #I think it's ok to use the first gene assembly. Not sure, though...
    gene_assembly = gene.gene.assembly
    alias = gene.gene_aliases

    genes = GeneXRef.objects.using('entire').filter(gene_aliases=alias).order_by('gene__chrom','description')
    gene_ends = genes.aggregate(min_tile=Min('gene__tile_start_tx'), max_tile=Max('gene__tile_end_tx'))
    #Add gene_ends to context
    context['gene_ends'] = gene_ends
    try:
        position = Tile.objects.get(pk=tile_int)
    except ObjectDoesNotExist:
        return render(request, 'tile_library/tile_in_gene_view.html', context)
    #Add position to context
    context['position'] = position
    try:
        locus = position.tile_locus_annotations.get(assembly=gene_assembly)
    except ObjectDoesNotExist:
        raise Http404("Tile Position does not have the ability to lift over to the assembly used by the genes")

    info = {'start':int(locus.begin_int), 'end':int(locus.end_int)}
    start_tag = to_percent(info['start']+24, info)
    body = to_percent(info['end']-24, info)
    end_tag = to_percent(info['end'], info)
    #Add the position outline to context
    context['pos_outline'] = [start_tag, body-start_tag, end_tag-body]

    tiles = position.tile_variants.all()
    #Add tiles to context
    context['tiles'] = tiles
    
    try:
        #color_exon_parts does not sort the genes, so don't need to resort
        in_exon, all_exons = gene_fns.color_exon_parts(genes, position)
    except BaseException as e:
        raise Http404(str(e))
    
    #Add in_exon, genes, and all_exons to context
    context['in_exon'] = in_exon
    context['exons'] = zip(all_exons, genes)
    
    min_tile_int, foo = functions.get_min_position_and_tile_variant_from_path_int(path_int)
    try:
        path = GenomeStatistic.objects.get(path_name=path_int)
        #TODO: Check this assumption
        #   GenomeVariant needs to look-back at most one position
        if tile_int == min_tile_int:
            genome_variants = GenomeVariant.objects.filter(start_tile_position=tile_int)
            tiles = position.tile_variants.filter(num_positions_spanned=1)
            spanning_tiles = position.tile_variants.filter(num_positions_spanned__gt=1)
        else:
            prev_ref_length = TileVariant.objects.filter(tile_id=tile_int-1).get(variant_value=0).length
            context['prev_ref_length'] = prev_ref_length
            genome_variants = GenomeVariant.objects.filter(Q(start_tile_position=tile_int) | Q(end_tile_position=tile_int) |
                                               (Q(end_tile_position=tile_int-1) & Q(end_increment__gte=prev_ref_length-24)))
            num_look_back_tiles = path.max_num_positions_spanned
            for i in range(num_look_back_tiles):
                if i == 0:
                    curr_Q = Q(tile_id=tile_int)
                else:
                    curr_Q = curr_Q | (Q(tile_id=tile_int-i) & Q(num_positions_spanned__gt=i))
            tiles = position.tile_variants.filter(num_positions_spanned=1)
            spanning_tiles = TileVariant.objects.filter(curr_Q).filter(num_positions_spanned__gt=1)
    except ObjectDoesNotExist:
        return render(request, 'tile_library/tile_in_gene_view.html', context)
    context['tiles'] = tiles
    context['spanning_tiles'] = spanning_tiles
    context['genome_variants'] = genome_variants
    tile_to_popul, num_people = get_population_repr_of_tile_variants(tiles, spanning_tiles)
    context['total_people'] = num_people
    context['tile_to_popul'] = tile_to_popul
    return render(request, 'tile_library/tile_in_gene_view.html', context)
