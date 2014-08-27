from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseServerError
from django.http import Http404
from django.template import RequestContext, loader

from loadgenes.models import Gene


def index(request):
    #return HttpResponse("Hello, world. You are at the slippy index")
    return render(request, 'index.html', {})

def simplesearch(request):
    error_msg = "No GET data sent."
    if request.method == "GET":
        geneName = request.GET['geneName']
        matching = Gene.objects.filter(gene_name__icontains=geneName)
        if len(matching) >= 1:
            gene = matching[0]
            spath, sversion, sstep = gene.getTileCoord(gene.startCGF)
            epath, eversion, estep = gene.getTileCoord(gene.endCGF)
            context = {'gene': gene.gene_name, 'spath':spath, 'sstep':sstep, 'epath':epath, 'estep':estep}
            return render(request, 'search.html', context)
        else:
            error_msg = "No genes containing %s were found." % geneName
    return HttpResponseServerError(error_msg)

def search(request, text):
    matching = Gene.objects.filter(gene_name__icontains=text)
    if len(matching) >= 1:
        gene = matching[0]
        spath, sversion, sstep = gene.getTileCoord(gene.startCGF)
        epath, eversion, estep = gene.getTileCoord(gene.endCGF)
        context = {'gene': gene, 'spath':spath, 'sstep':sstep, 'epath':epath, 'estep':estep}
        return render(request, 'slippy/index.html', context)
    else:
        return HttpResponse("Gene %s not found." % text)
