from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.http import Http404

from loadgenomes.models import VarAnnotation, Tile, TileVariant


def statistics(request, check=True):
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
        'num_people': loaded_popul_size/2.0,
        'warning':warn,
        }
    return render(request, 'loadgenomes/statistics.html', context)

#def chrom_statistics(request, chrom):

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
