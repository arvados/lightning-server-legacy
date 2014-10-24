from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseServerError
from django.http import Http404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.template import RequestContext
from django.core.exceptions import ObjectDoesNotExist

from tile_library.models import Tile, TileVariant, TileLocusAnnotation, VarAnnotation, GenomeStatistic
import tile_library.basic_functions as base_fns
import tile_library.functions as functions
import genes.functions as gene_fns
from django.db.models import Avg, Count, Max, Min
from genes.models import GeneXRef

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
    """chr_int Chromosome Stats and all paths in that Chromosome """
    chr_int = int(chr_int)
    if chr_int <= 0 or chr_int >= len(Tile.CHR_PATH_LENGTHS):
        raise Http404
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

def get_positions(min_accepted, max_accepted):
    return Tile.objects.filter(tilename__range=(min_accepted, max_accepted)).annotate(
        num_var=Count('variants'), min_len=Min('variants__length'), avg_len=Avg('variants__length'),
        max_len=Max('variants__length'))

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
    paginator = Paginator(positions, num_tiles_per_page)
    try:
        partial_positions = paginator.page(page)
    except PageNotAnInteger:
        #Deliver the first page
        partial_positions = paginator.page(1)
    except EmptyPage:
        #If page is out of range, deliver last page of results
        partial_positions = paginator.page(paginator.num_pages)
    return partial_positions

def path_statistics(request, chr_int, path_int):
    """path_int Path Stats and the pagination of all tiles in that path """
    chr_int = int(chr_int)
    if chr_int <= 0 or chr_int >= len(Tile.CHR_PATH_LENGTHS):
        raise Http404
    chr_name = functions.get_chromosome_name_from_chromosome_int(chr_int)
    path_int = int(path_int)
    if path_int < Tile.CHR_PATH_LENGTHS[chr_int-1] or path_int >= Tile.CHR_PATH_LENGTHS[chr_int]:
        raise Http404
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
    
    ordering = request.GET.get('ordering')
    page = request.GET.get('page')
    num_per_page = request.GET.get('num')
    if num_per_page == None:
        num_per_page = 16
    positions = get_positions(min_accepted, max_accepted)
    partial_positions = get_partial_positions(positions, ordering,num_per_page, page)
    context['path'] = path
    context['positions'] = partial_positions
    return render(request, 'tile_library/path_statistics.html', context)



def tile_view(request, chr_int, path_int, tilename):
    chr_int = int(chr_int)
    if chr_int <= 0 or chr_int >= len(Tile.CHR_PATH_LENGTHS):
        raise Http404
    chr_name = functions.get_chromosome_name_from_chromosome_int(chr_int)
    path_int = int(path_int)
    if path_int < Tile.CHR_PATH_LENGTHS[chr_int-1] or path_int >= Tile.CHR_PATH_LENGTHS[chr_int]:
        raise Http404
    tile_int = int(tilename)
    min_tile_int, foo = functions.get_min_position_and_tile_variant_from_path_int(path_int)
    max_tile_int, foo = functions.get_min_position_and_tile_variant_from_path_int(path_int+1)
    if tile_int < min_tile_int or tile_int >= max_tile_int:
        raise Http404
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
        position = Tile.objects.get(pk=tile_int)
    except ObjectDoesNotExist:
        return render(request, 'tile_library/tile_view.html', context)
    tiles = position.variants.all()
    context['position'] = position
    context['tiles'] = tiles
    return render(request, 'tile_library/tile_view.html', context)

def get_positions_with_bases(min_accepted, max_accepted):
    return Tile.objects.filter(tilename__range=(min_accepted, max_accepted)).annotate(
        num_var=Count('variants'), min_len=Min('variants__length'), avg_len=Avg('variants__length'),
        max_len=Max('variants__length'), min_base=Min('tile_locus_annotations__begin_int'),
        max_base=Max('tile_locus_annotations__end_int'))

def gene_view(request, gene_xref_id): 
    gene = GeneXRef.objects.get(pk=gene_xref_id)
    alias = gene.gene_aliases
    genes = GeneXRef.objects.filter(gene_aliases=alias)

    overlapping_genes = gene_fns.split_genes_into_groups(genes, by_tile=True)
    assert len(overlapping_genes) == 1, 'Requires all genes to interlap'
    
    min_accepted = overlapping_genes[0][2]
    max_accepted = overlapping_genes[0][3]

    positions = get_positions_with_bases(min_accepted, max_accepted)
    
    exon_dict = gene_fns.annotate_positions_with_exons(overlapping_genes, positions)

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
    
    #Positions is iterated over in view, so paginate this
    ordering = request.GET.get('ordering')
    page = request.GET.get('page')
    partial_positions = get_partial_positions(positions, ordering, 16, page)
    for pos in partial_positions:
        pos.has_exon = exon_dict[int(pos.tilename)]
    context = {
        'request':request,
        'gene':gene,
        'chromosome':position_info['chr_name'],
        'chromosome_int':position_info['chr_int'],
        'position_info': position_info,
        'positions':partial_positions,
        'exon_dict':exon_dict,
        }
    return render(request, 'tile_library/gene_view.html', context)



def tile_in_gene_view(request, gene_xref_id, tilename):
    def to_percent(l, info):
        return (int(l)-info['start'])/float(info['end']-info['start'])*100
    tile_int = int(tilename)
    path_int, version, step = base_fns.get_position_ints_from_position_int(tile_int)
    print path_int
    position = Tile.objects.get(pk=tile_int)

    tiles = position.variants.all()
    gene = GeneXRef.objects.get(pk=gene_xref_id)
    
    alias = gene.gene_aliases
    genes = GeneXRef.objects.filter(gene_aliases=alias).order_by('gene__chrom','description')
    gene_ends = genes.aggregate(min_tile=Min('gene__tile_start_tx'), max_tile=Max('gene__tile_end_tx'))
    gene_assembly = gene.gene.assembly
    locus = position.tile_locus_annotations.filter(assembly=gene_assembly).first()
    info = {'start':int(locus.begin_int), 'end':int(locus.end_int)}
    start_tag = to_percent(info['start']+24, info)
    body = to_percent(info['end']-24, info)
    end_tag = to_percent(info['end'], info)
    tile_outline = [start_tag, body-start_tag, end_tag-body]
    in_exon, all_exons = gene_fns.color_exon_parts(genes, info['start'], info['end'])
        
    chr_int = functions.get_chromosome_int_from_path_int(path_int)

    context = {
        'chr_int': chr_int,
        'chr_name': functions.get_chromosome_name_from_chromosome_int(chr_int),
        'path_int':path_int,
        'path_hex': hex(path_int).lstrip('0x').zfill(1),
        'path_name': Tile.CYTOMAP[path_int],
        'position': position,
        'gene':gene,
        'genes':genes,
        'gene_ends':gene_ends,
        'tiles':tiles,
        'in_exon':in_exon,
        'pos_outline':tile_outline,
        'exons':zip(all_exons, genes),
        }
    return render(request, 'tile_library/tile_in_gene_view.html', context)
    

