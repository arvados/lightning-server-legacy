from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseServerError
from django.http import Http404
from django.template import RequestContext, loader

from loadgenes.models import Gene

def index(request):
    filters = Gene.objects.order_by().values_list('source').distinct()
    filters = [f[0] for f in filters]
    filters = sorted(filters)
    return render(request, 'index.html', {'filters':filters})

def simplesearch(request):
    def dealWithMatching(matching):
        if len(matching) == 1:
            gene = matching[0]
            spath, sversion, sstep = gene.getTileCoord(gene.startCGF)
            epath, eversion, estep = gene.getTileCoord(gene.endCGF)
            if gene.genereviewURLs == None:
                ptr = ''
            else:
                ptr = gene.genereviewURLs
            context = {'gene': gene.gene_name, 'spath':spath, 'sstep':sstep, 'epath':epath, 'estep':estep, 'urlpointer':ptr}
            return render(request, 'search.html', context)
        elif len(matching) > 1:
            return render(request, 'multmatches.html', {'matching': matching})
        else:
            return None
    error_msg = "No GET data sent."
    if request.method == "GET":
        geneName = request.GET['geneName']
        matching = Gene.objects.filter(gene_name__istartswith=geneName)
        rendering = dealWithMatching(matching)
        if rendering != None:
            return rendering
        else:
            matching = Gene.objects.filter(gene_name__icontains=geneName)
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
        matching = Gene.objects.filter(gene_name=geneName)
        if len(matching) == 1:
            gene = matching[0]
            spath, sversion, sstep = gene.getTileCoord(gene.startCGF)
            epath, eversion, estep = gene.getTileCoord(gene.endCGF)
            if gene.genereviewURLs == None:
                ptr = ''
            else:
                ptr = gene.genereviewURLs
            context = {'gene': gene.gene_name, 'spath':spath, 'sstep':sstep, 'epath':epath, 'estep':estep, 'urlpointer':ptr}
            return render(request, 'search.html', context)
        elif len(matching) > 1:
            error_msg = 'Multiple genes matched "%s" exactly.' % geneName
        else:
            error_msg = 'No genes containing "%s" were found.' % geneName
    return HttpResponseServerError(error_msg)

def loadall(request):
    error_msg = "No GET data sent."
    if request.method == "GET":
        sourceName = request.GET['filter']
        if sourceName == 'clinical':
            matching = Gene.objects.filter(genereview=True)
        else:
            matching = Gene.objects.filter(source=sourceName)
        return render(request, 'loadall.html', {'matching':matching})
    return HttpResponseServerError(error_msg)





