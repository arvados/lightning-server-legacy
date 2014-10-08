from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseServerError
from django.http import Http404
from django.template import RequestContext, loader

from django.db.models import Count,Max,Min
from genes.models import UCSC_Gene, GeneXRef

def getTileCoordInt(tile):
    """Returns integer for path, version, and step for tile """
    strTilename = hex(tile).lstrip('0x').rstrip('L')
    strTilename = strTilename.zfill(9)
    path = int(strTilename[:3], 16)
    version = int(strTilename[3:5], 16)
    step = int(strTilename[5:], 16)
    return path, version, step


def slippymap(request):
    return render(request, 'slippy/slippymap.html', {})

def simplesearch(request):
    def dealWithMatching(matching):
        distinct_set = matching.order_by('gene_aliases').distinct('gene_aliases')
        number_of_distinct = distinct_set.count()
        if number_of_distinct == 1:
            tile_end_tx = matching.aggregate(Max('gene__tile_end_tx'))['gene__tile_end_tx__max']
            tile_start_tx = matching.aggregate(Min('gene__tile_start_tx'))['gene__tile_start_tx__min']
            spath, sversion, sstep = getTileCoordInt(tile_start_tx)
            epath, eversion, estep = getTileCoordInt(tile_end_tx)
            gene = matching.first()
            if gene.has_gene_review: 
                ptr = gene.gene_review_URLs
            else:
                ptr = ''
            context = {'gene': gene.gene_aliases, 'spath':spath, 'sstep':sstep, 'epath':epath, 'estep':estep, 'urlpointer':ptr}
            return render(request, 'slippy/search.html', context)
        elif number_of_distinct > 1:
            return render(request, 'slippy/multmatches.html', {'matching': distinct_set})
        else:
            return None
    error_msg = "No GET data sent."
    if request.method == "GET":
        geneName = request.GET['geneName']
        matching = GeneXRef.objects.filter(gene_aliases__istartswith=geneName)
        rendering = dealWithMatching(matching)
        if rendering != None:
            return rendering
        else:
            matching = GeneXRef.objects.filter(gene_aliases__icontains=geneName)
            rendering = dealWithMatching(matching)
            if rendering != None:
                return rendering
            else:
                error_msg = 'No genes containing "%s" were found.' % geneName
    return HttpResponseServerError(error_msg)
    
def specificsearch(request):
    error_msg = "No GET data sent."
    if request.method == "GET":
        geneName = request.GET['geneName']
        matching = GeneXRef.objects.filter(gene_aliases=geneName)
        if matching != None:
            tile_end_tx = matching.aggregate(Max('gene__tile_end_tx'))['gene__tile_end_tx__max']
            tile_start_tx = matching.aggregate(Min('gene__tile_start_tx'))['gene__tile_start_tx__min']
            spath, sversion, sstep = getTileCoordInt(tile_start_tx)
            epath, eversion, estep = getTileCoordInt(tile_end_tx)
            gene = matching.first()
            if gene.has_gene_review: 
                ptr = gene.gene_review_URLs
            else:
                ptr = ''
            context = {'gene': gene.gene_aliases, 'spath':spath, 'sstep':sstep, 'epath':epath, 'estep':estep, 'urlpointer':ptr}
            return render(request, 'slippy/search.html', context)
        else:
            error_msg = 'No genes containing "%s" were found.' % geneName
    return HttpResponseServerError(error_msg)

def loadall(request):
    error_msg = "No GET data sent."
    if request.method == "GET":
        phenotype = request.GET['filter']
        if phenotype == 'clinical':
            matching = GeneXRef.objects.filter(has_gene_review=True)
            distinct_matching = matching.order_by('gene_aliases').distinct('gene_aliases')
        else:
            matching = GeneXRef.objects.filter(gene_review_phenotype_map__icontains=phenotype)
            distinct_matching = matching.order_by('gene_aliases').distinct('gene_aliases')
        return render(request, 'slippy/loadall.html', {'matching':matching, 'distinct':distinct_matching})
    return HttpResponseServerError(error_msg)





