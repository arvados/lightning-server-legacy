from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseServerError
from django.http import Http404
from django.template import RequestContext, loader

from django.db.models import Count,Max,Min
from genes.models import UCSC_Gene, GeneXRef
import genes.functions as fns

def getTileCoordInt(tile):
    """Returns integer for path, version, and step for tile """
    strTilename = hex(tile).lstrip('0x').rstrip('L')
    strTilename = strTilename.zfill(9)
    path = int(strTilename[:3], 16)
    version = int(strTilename[3:5], 16)
    step = int(strTilename[5:], 16)
    return path, version, step


def slippymap(request):
    exact_gene = request.GET.get('exact')
    many_exact = request.GET.get('multiple-exact')
    gene_filter = request.GET.get('filter')
    pheno_filter = request.GET.get('phenotype')
    reviewed = request.GET.get('reviewed')
    if many_exact != None:
        matching = GeneXRef.objects.using('entire').filter(gene_aliases=many_exact).order_by('gene__chrom','description')
        overlapping_genes = fns.split_genes_into_groups(matching, by_tile=True)
        context = {'overlapping':overlapping_genes}
        
    elif exact_gene != None:
        matching = GeneXRef.objects.using('entire').filter(gene_aliases=exact_gene).order_by('gene__chrom','description')
        distinct_genes = GeneXRef.objects.order_by('gene_aliases').distinct('gene_aliases').filter(gene_aliases=exact_gene)
        context = {'genes':distinct_genes, 'matching':matching}

    elif gene_filter != None or pheno_filter != None or reviewed != None:
        matching = GeneXRef.objects.using('entire').order_by('gene_aliases').order_by('gene__chrom','description')
        distinct_genes = GeneXRef.objects.using('entire').order_by('gene_aliases').distinct('gene_aliases')
        if gene_filter != None and gene_filter != 'all':
            matching = matching.filter(gene_aliases__istartswith=gene_filter)
            distinct_genes = distinct_genes.filter(gene_aliases__istartswith=gene_filter)
            if not distinct_genes.exists() and len(gene_filter) > 1:
                matching = matching.filter(gene_aliases__icontains=gene_filter)
                distinct_genes = distinct_genes.filter(gene_aliases__icontains=gene_filter)
        if pheno_filter != None:
            matching = matching.filter(gene_review_phenotype_map__icontains=pheno_filter)
            distinct_genes = distinct_genes.filter(gene_review_phenotype_map__icontains=pheno_filter)
        if reviewed != None:
            matching = matching.filter(has_gene_review=True)
            distinct_genes = distinct_genes.filter(has_gene_review=True)
        context = {'genes':distinct_genes, 'matching':matching}
    else:
        context = {}
    return render(request, 'slippy/slippymap.html', context)

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
        matching = GeneXRef.objects.using('entire').filter(gene_aliases__istartswith=geneName)
        rendering = dealWithMatching(matching)
        if rendering != None:
            return rendering
        else:
            matching = GeneXRef.objects.using('entire').filter(gene_aliases__icontains=geneName)
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
        matching = GeneXRef.objects.using('entire').filter(gene_aliases=geneName)
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
            matching = GeneXRef.objects.using('entire').filter(has_gene_review=True)
            distinct_matching = matching.order_by('gene_aliases').distinct('gene_aliases')
        else:
            matching = GeneXRef.objects.using('entire').filter(gene_review_phenotype_map__icontains=phenotype)
            distinct_matching = matching.order_by('gene_aliases').distinct('gene_aliases')
        return render(request, 'slippy/loadall.html', {'matching':matching, 'distinct':distinct_matching})
    return HttpResponseServerError(error_msg)





