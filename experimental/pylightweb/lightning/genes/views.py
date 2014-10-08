from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseServerError
from django.http import Http404

from genes.models import UCSC_Gene, GeneXRef

def current_gene_names(request):
    distinct_genes = GeneXRef.objects.order_by('gene_aliases').distinct('gene_aliases')
    context = {
        'genes':distinct_genes,
        }
    return render(request, 'genes/names.html', context)

def specific_gene(request, xref_id):
    gene = GeneXRef.objects.get(pk=xref_id)
    alias = gene.gene_aliases
    genes = GeneXRef.objects.filter(gene_aliases=alias).order_by('description')
    context = {
        'gene':gene,
        'genes':genes,
        }
    return render(request, 'genes/gene_view.html', context)
        
