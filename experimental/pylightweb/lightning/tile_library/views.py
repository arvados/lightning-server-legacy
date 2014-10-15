from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseServerError
from django.http import Http404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.template import RequestContext

from tile_library.models import Tile, TileVariant, TileLocusAnnotation, VarAnnotation, GenomeStatistic
from django.db.models import Avg, Count, Max, Min
from genes.models import GeneXRef

def getTileCoordInt(tile):
    """Returns integer for path, version, and step for tile """
    strTilename = hex(tile).lstrip('0x').rstrip('L')
    strTilename = strTilename.zfill(9)
    path = int(strTilename[:3], 16)
    version = int(strTilename[3:5], 16)
    step = int(strTilename[5:], 16)
    return path, version, step

def convert_pos_to_tile(tile):
    strTilename = hex(tile).lstrip('0x').rstrip('L')
    strTilename = strTilename.zfill(12)
    return int(strTilename, 16)

def convert_chromosome_to_tilename(chr_int):
    """chr_int: [1, 2, 3, ... 26, 27]
        23 => chrX
        24 => chrY
        25 => chrM
        26 => strangely-shaped chromosomes
        27 is non-existant, for determining the maximum integer possible in the database
    """
    chrom_int = int(chr_int) - 1
    if chrom_int < 0 or chrom_int > 26:
        raise BaseException(str(chr_int) + " is not an integer between 1 and 27")
    chr_path_lengths = Tile.CHR_PATH_LENGTHS
    name = hex(chr_path_lengths[chrom_int]).lstrip('0x').zfill(3)+"00"+"0000"
    varname = name + "000"
    name = int(name, 16)
    varname = int(varname, 16)
    return name, varname

def convert_path_to_tilename(path_int):
    path_int = int(path_int)
    name = hex(path_int).lstrip('0x').zfill(3)+"00"+"0000"
    varname = name + "000"
    name = int(name, 16)
    varname = int(varname, 16)
    return name, varname

def get_chromosome_name_from_int(chr_int):
    chr_index = [i for i,j in TileLocusAnnotation.CHR_CHOICES]
    return TileLocusAnnotation.CHR_CHOICES[chr_index.index(chr_int)][1]

def overall_statistics(request):
    chromosomes = TileLocusAnnotation.CHR_CHOICES
    chromosomes = [name for i, name in chromosomes]
    chromosomes.insert(0, 0)
    statistics = GenomeStatistic.objects.filter(pk__range=(1,27)).order_by('statistics_type')
    retval = zip(statistics, chromosomes)
    context = {
        'stats':retval,
        }
    return render(request, 'tile_library/statistics.html', context)

def chr_statistics(request, chr_int):
    chr_int = int(chr_int)
    chr_stats = GenomeStatistic.objects.get(pk=chr_int+1)

    chromosome = get_chromosome_name_from_int(chr_int)
    chr_path_lengths=Tile.CHR_PATH_LENGTHS
    paths = range(chr_path_lengths[chr_int-1], chr_path_lengths[chr_int])
    path_info = GenomeStatistic.objects.filter(path_name__range=(chr_path_lengths[chr_int-1], chr_path_lengths[chr_int]-1)).order_by('path_name')
    path_objects = [(i, hex(i).lstrip('0x'), Tile.CYTOMAP[i], path_obj) for (i, path_obj) in zip(paths, path_info)]
    context = {
        'chromosome_int':chr_int,
        'chromosome_name':chromosome,
        'chromosome_stats':chr_stats,
        'paths':path_objects,
        }
    return render(request, 'tile_library/chr_statistics.html', context)

def path_statistics(request, chr_int, path_int):
    chr_int = int(chr_int)
    path_int = int(path_int)
    chromosome = get_chromosome_name_from_int(chr_int)
    min_accepted, min_tile_accepted = convert_path_to_tilename(path_int)
    max_accepted, max_tile_accepted = convert_path_to_tilename(path_int+1)
    max_accepted -= 1
    max_tile_accepted -= 1
    #Positions is iterated over in view, so paginate this
    ordering = request.GET.get('ordering')
    positions = Tile.objects.filter(tilename__range=(min_accepted, max_accepted)).annotate(
        num_var=Count('variants'), min_len=Min('variants__length'), avg_len=Avg('variants__length'),
        max_len=Max('variants__length'))

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
    paginator = Paginator(positions, 16)
    page = request.GET.get('page')
    try:
        partial_positions = paginator.page(page)
    except PageNotAnInteger:
        #Deliver the first page
        partial_positions = paginator.page(1)
    except EmptyPage:
        #If page is out of range, deliver last page of results
        partial_positions = paginator.page(paginator.num_pages)
    path = GenomeStatistic.objects.get(path_name=path_int)
    
    context = {
        'request':request,
        'chromosome_int': chr_int,
        'chromosome': chromosome,
        'path_int':path_int,
        'path_hex':hex(path_int)[2:],
        'path_cyto':Tile.CYTOMAP[path_int],
        'path':path,
        'positions':partial_positions,
        }
    return render(request, 'tile_library/path_statistics.html', context)

def get_chr_int_from_path(path_int):
    for i, chrom in enumerate(Tile.CHR_PATH_LENGTHS):
        if path_int < chrom:
            return i

def annotate_with_exons(genes, positions):
    #Currently assumes all genes in Hg19 and do not pass over chromosomes
    all_exons = []
    for gene in genes:
        begins = gene.gene.exon_starts.strip(',').split(',')
        ends = gene.gene.exon_ends.strip(',').split(',')
        exons = [(int(begin), int(end)) for begin, end in zip(begins, ends)]
        all_exons.extend(exons)
    
    all_exons = sorted(list(set(all_exons)), key=lambda x:x[0])
    in_exon=False
    curr_exon = 0
    exon_dict = {}
    for position in positions:
        name = int(position.tilename)
        while all_exons[curr_exon][1] < position.min_base:
            curr_exon += 1
        if not in_exon:
            if position.max_base < all_exons[curr_exon][0]:
                exon_dict[name] = in_exon #False
            else:
                in_exon = True
                exon_dict[name] = in_exon #True
                if position.max_base - 24 > all_exons[curr_exon][1]:
                    in_exon = False
                    curr_exon += 1
        else:
            if position.max_base - 24 < all_exons[curr_exon][1]:
                exon_dict[name] = in_exon #True
            else:
                exon_dict[name] = in_exon #True
                in_exon = False
                curr_exon += 1
    return exon_dict

def gene_view(request, gene_xref_id):
    #TODO: figure out how to use assembly number from gene to 
    gene = GeneXRef.objects.get(pk=gene_xref_id)
    
    alias = gene.gene_aliases
    genes = GeneXRef.objects.filter(gene_aliases=alias)
    min_accepted = genes.aggregate(Min('gene__tile_start_tx'))['gene__tile_start_tx__min']
    max_accepted = genes.aggregate(Max('gene__tile_end_tx'))['gene__tile_end_tx__max']
    min_tile_accepted = convert_pos_to_tile(min_accepted)
    max_tile_accepted = convert_pos_to_tile(max_accepted)

    beg_path_int, foo, bar = getTileCoordInt(min_accepted)
    beg_path_hex = hex(beg_path_int).lstrip('0x')
    beg_path_name = Tile.CYTOMAP[beg_path_int]
    beg_path = GenomeStatistic.objects.get(path_name=beg_path_int)
    
    chr_int = get_chr_int_from_path(beg_path_int)
    chromosome = get_chromosome_name_from_int(chr_int)

    end_path_int, foo, bar = getTileCoordInt(max_accepted)
    if beg_path_int != end_path_int:
        end_path_hex = hex(end_path_int).lstrip('0x')
        end_path_name = Tile.CYTOMAP[end_path_int]
        end_path = GenomeStatistic.objects.get(path_name=end_path_int)
        position_info = {'beg_path_int':beg_path_int, 'beg_path_hex':beg_path_hex, 'beg_path_name':beg_path_name,
                     'beg_path':beg_path,
                     'end_path_int':end_path_int, 'end_path_hex':end_path_hex, 'end_path_name':end_path_name,
                     'end_path':end_path, 'chr_int':chr_int, 'chr_name':chromosome}
    else:
        position_info = {'end_path_int':beg_path_int, 'end_path_hex':beg_path_hex, 'end_path_name':beg_path_name,
                     'end_path':beg_path, 'chr_int':chr_int, 'chr_name':chromosome}
    
    #Positions is iterated over in view, so paginate this
    ordering = request.GET.get('ordering')
    positions = Tile.objects.filter(tilename__range=(min_accepted, max_accepted)).annotate(
        num_var=Count('variants'), min_len=Min('variants__length'), avg_len=Avg('variants__length'),
        max_len=Max('variants__length'), min_base=Min('tile_locus_annotations__begin_int'),
        max_base=Max('tile_locus_annotations__end_int'))
    exon_dict = annotate_with_exons(genes, positions)
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
    paginator = Paginator(positions, 16)
    page = request.GET.get('page')
    try:
        partial_positions = paginator.page(page)
    except PageNotAnInteger:
        #Deliver the first page
        partial_positions = paginator.page(1)
    except EmptyPage:
        #If page is out of range, deliver last page of results
        partial_positions = paginator.page(paginator.num_pages)
    for pos in partial_positions:
        pos.has_exon = exon_dict[int(pos.tilename)]
    context = {
        'request':request,
        'gene':gene,
        'position_info': position_info,
        'positions':partial_positions,
        'exon_dict':exon_dict,
        }
    return render(request, 'tile_library/gene_view.html', context)

def split_exons(genes, info):
    def to_percent(locus):
        return (int(locus)-info['start'])/float(info['end']-info['start'])*100
    #Currently assumes all genes in Hg19 and do not pass over chromosomes
    has_exons = False
    all_exons = []
    for gene in genes:
        begins = gene.gene.exon_starts.strip(',').split(',')
        ends = gene.gene.exon_ends.strip(',').split(',')
        exons = []
        inner_exons = []
        for beg, end in zip(begins, ends):
            beg = int(beg)
            end = int(end)
            if beg >= info['start'] and beg <= info['end']:
                #If beginning of exon in middle
                if end > info['end']:
                    inner_exons.append((beg, info['end']))
                else:
                    inner_exons.append((beg, end))
            elif beg <= info['start'] and end >= info['start']:
                #if beginning of exon before the start of the tile, but the exon
                # ends after the tile starts
                if end > info['end']:
                    #The exon extends past the tile
                    inner_exons = [(info['start'], info['end'])]
                else:
                    inner_exons.append((info['start'], end))
            #else do nothing: the exon isn't in the tile
        for i, (begin, end) in enumerate(inner_exons):
            second = to_percent(end) - to_percent(begin)
            if i == 0:
                exons.append((to_percent(begin), second))
            else:
                exons.append((to_percent(begin)-to_percent(inner_exons[i-1][1]), second))
        if len(inner_exons) == 0:
            exons.append((100, 0))
        else:
            has_exons = True
            exons.append((100-to_percent(inner_exons[-1][1]), 0))
        all_exons.append(exons)
        

    return has_exons, all_exons

def tile_in_gene_view(request, gene_xref_id, tilename):
    def to_percent(l, info):
        return (int(l)-info['start'])/float(info['end']-info['start'])*100
    tile_int = int(tilename)
    path_int, version, step = getTileCoordInt(tile_int)
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
    in_exon, all_exons = split_exons(genes, info)
        
    chr_int = get_chr_int_from_path(path_int)

    context = {
        'chr_int': chr_int,
        'chr_name': get_chromosome_name_from_int(chr_int),
        'path_int':path_int,
        'path_hex': hex(path_int)[2:],
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


def tile_view(request, chr_int, path_int, tilename):
    chr_int = int(chr_int)
    path_int = int(path_int)
    tile_int = int(tilename)
   
    next_path, version, step = getTileCoordInt(tile_int+1)
    next_chr = get_chr_int_from_path(next_path)
    next_tile = {'tile_int':tile_int+1, 'path_int':next_path, 'chr_int':next_chr}
    
    prev_path, version, step = getTileCoordInt(tile_int-1)
    prev_chr = get_chr_int_from_path(prev_path)
    prev_tile = {'tile_int':tile_int-1, 'path_int':prev_path, 'chr_int':prev_chr}
    
    position = Tile.objects.get(pk=tile_int)
    tiles = position.variants.all()
    context = {
        'chr_int': chr_int,
        'chr_name': get_chromosome_name_from_int(chr_int),
        'path_int':path_int,
        'path_hex': hex(path_int)[2:],
        'path_name': Tile.CYTOMAP[path_int],
        'position': position,
        'tiles':tiles,
        'next_tile':next_tile,
        'prev_tile':prev_tile,
        }
    return render(request, 'tile_library/tile_view.html', context)

