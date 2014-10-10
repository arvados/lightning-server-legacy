from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseServerError
from django.http import Http404

from tile_library.models import Tile, TileVariant, TileLocusAnnotation, VarAnnotation, GenomeStatistic

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
    statistics = GenomeStatistic.objects.all()
    retval = zip(statistics, chromosomes)
    context = {
        'stats':retval,
        }
    return render(request, 'tile_library/statistics.html', context)

def chr_statistics(request, chr_int):
    chr_int = int(chr_int)
    
    min_accepted, min_tile_accepted = convert_chromosome_to_tilename(chr_int)
    max_accepted, max_tile_accepted = convert_chromosome_to_tilename(chr_int+1)
    max_accepted -= 1
    max_tile_accepted -= 1

    chr_stats = GenomeStatistic.objects.get(pk=chr_int+1)
    positions = Tile.objects.filter(tilename__range=(min_accepted, max_accepted))
    tiles = TileVariant.objects.filter(tile_variant_name__range=(min_tile_accepted, max_tile_accepted))

    chromosome = get_chromosome_name_from_int(chr_int)
    chr_path_lengths=Tile.CHR_PATH_LENGTHS
    paths = range(chr_path_lengths[chr_int-1], chr_path_lengths[chr_int])
    paths = [(i, hex(i)[2:], Tile.CYTOMAP[i]) for i in paths]
    context = {
        'chromosome_int':chr_int,
        'chromosome_name':chromosome,
        'chromosome_stats':chr_stats,
        'positions':positions,
        'tiles':tiles,
        'paths':paths,
        }
    return render(request, 'tile_library/chr_statistics.html', context)

def path_statistics(request, chr_int, path_int):
    chr_int = int(chr_int)
    path_int = int(path_int)
    chromosome = get_chromosome_name_from_int(chr_int)
    min_accepted, min_tile_accepted = convert_path_to_tilename(path_int)
    max_accepted, max_tile_accepted = convert_path_to_tilename(path_int+1)
    positions = Tile.objects.filter(tilename__gte=min_accepted).filter(tilename__lt=max_accepted)
    tiles = TileVariant.objects.filter(tile_variant_name__gte=min_tile_accepted).filter(tile_variant_name__lt=max_tile_accepted)
    context = {
        'chromosome_int': chr_int,
        'chromosome': chromosome,
        'path_int':path_int,
        'path':hex(path_int)[2:],
        'path_name':Tile.CYTOMAP[path_int],
        'positions':positions,
        'tiles':tiles,
        }
    return render(request, 'tile_library/path_statistics.html', context)

def tile_view(request, chr_int, path_int, tilename):
    chr_int = int(chr_int)
    path_int = int(path_int)
    tile_int = int(tilename)
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
        }
    return render(request, 'tile_library/tile_view.html', context)

