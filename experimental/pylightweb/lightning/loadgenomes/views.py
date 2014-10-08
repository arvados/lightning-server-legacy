from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseServerError
from django.http import Http404

from loadgenomes.models import VarAnnotation, Tile, TileVariant


def statistics(request, check=True):
    positions = Tile.objects.all()
    loaded_popul_size = sum(var.population_size for var in positions[0].variants.all())
    context = {
        'num_people': loaded_popul_size/2.0,
        }
    return render(request, 'loadgenomes/statistics.html', context)

def loadstatistics(request, check=True):
    positions = Tile.objects.all()
    loaded_popul_size = sum(var.population_size for var in positions[0].variants.all())
    warn = False
    if check:
        for pos in positions:
            if sum(var.population_size for var in pos.variants.all()) != loaded_popul_size:
                print pos.__unicode__()
                warn = True
    tiles = TileVariant.objects.all()
    #Currently only looking at chromosomes up to M
    chromosomes = range(1,26)
    context = {
        'positions': positions,
        'tiles':tiles,
        'chromosomes':chromosomes,
        'warning':warn,
        }
    return render(request, 'loadgenomes/loadstatistics.html', context)

def chrom_statistics(request, chrom):
    chrom_int = int(chrom_int)-1
    if chrom_int < 0 or chrom_int > 25:
        return HttpResponseServerError("That is not a chromosome integer format, expect an integer between 1 and 25. We don't support unconventional chromosomes yet")
    chr_path_lengths = [0,63,125,187,234,279,327,371,411,454,496,532,573,609,641,673,698,722,742,761,781,795,811,851,862,863]
    min_accepted = hex(chr_path_lengths[chrom_int])[2:]+"00"+"0000"
    min_var_accepted = min_accepted + "000"
    min_accepted = int(min_accepted, 16)
    min_var_accepted = int(min_var_accepted, 16)
    max_accepted = hex(chr_path_lengths[chrom_int+1])[2:]+"00"+"0000"
    max_var_accepted = max_accepted + "000"
    max_accepted = int(max_accepted, 16)
    max_var_accepted = int(max_var_accepted, 16)
    positions = Tile.objects.filter(tilename__gte=min_accepted).filter(tilename__lt=max_accepted)
    tiles = TileVariant.objects.filter(tile_variant_name__gte=min_var_accepted).filter(tile_variant_name__lt=max_var_accepted)
    context = {
        'positions': positions,
        'tiles':tiles,
        'chromosome':chrom_int,
        }
    return render(request, 'loadgenomes/loadstatistics.html', context)



def index(request):
    trusted_annotation_list = VarAnnotation.objects.filter(source="library_generation")
    non_trusted_annotation_list = TileVarAnnotation.objects.filter(source="person")
    context = {
        'trusted_list': trusted_annotation_list,
        'uncertain_list': non_trusted_annotation_list,
        }
    return render(request, 'loadgenomes/index.html', context)

def detail(request, annotation_id):
    annotation = get_object_or_404(TileVarAnnotation, pk=annotation_id)
    return render(request, 'loadgenomes/detail.html', {'annotation' : annotation})

def review(request, annotation_id):
    annotation = get_object_or_404(TileVarAnnotation, pk=annotation_id)
    return render(request, 'loadgenomes/review.html', {'annotation' : annotation})

def annotate(request, tile_id):
    return HttpResponse("You are annotating tile %s" % tile_id)

def upload(request):
    return HttpResponse("You are uploading a new genome")
