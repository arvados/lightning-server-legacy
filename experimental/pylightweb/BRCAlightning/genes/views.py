from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseServerError
from django.http import Http404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import string

from django.db.models import Avg, Count, Max, Min
from genes.models import UCSC_Gene, GeneXRef
import genes.functions as fns

def current_gene_names(request):
    distinct_genes = GeneXRef.objects.using('entire').order_by('gene_aliases').distinct('gene_aliases')

    gene_filter = request.GET.get('filter')
    if gene_filter != None and gene_filter != 'all':
        trial_distinct_genes = distinct_genes.filter(gene_aliases__istartswith=gene_filter)
        if not trial_distinct_genes.exists():
            if len(gene_filter) > 1:
                distinct_genes = distinct_genes.filter(gene_aliases__icontains=gene_filter)
        else:
            distinct_genes = trial_distinct_genes

    pheno_filter = request.GET.get('phenotype')
    if pheno_filter != None:
        distinct_genes = distinct_genes.filter(gene_review_phenotype_map__icontains=pheno_filter)
        
    reviewed = request.GET.get('reviewed')
    if reviewed != None:
        distinct_genes = distinct_genes.filter(has_gene_review=True)
        
    paginator = Paginator(distinct_genes, 15)
    page = request.GET.get('page')
    try:
        partial_genes = paginator.page(page)
    except PageNotAnInteger:
        #Deliver the first page
        partial_genes = paginator.page(1)
    except EmptyPage:
        #If page is out of range, deliver last page of results
        partial_genes = paginator.page(paginator.num_pages)
        
    letters = string.uppercase
    get_objects = {'gene_filter':gene_filter, 'reviewed':reviewed, 'phenotype':pheno_filter, 'page':page}
    context = {
        'request':request,
        'genes':partial_genes,
        'letters':letters,
        'get_objects':get_objects,
        }
    
    return render(request, 'genes/names.html', context)

def specific_gene(request, xref_id):
    gene = GeneXRef.objects.using('entire').get(pk=xref_id)
    alias = gene.gene_aliases
    genes = GeneXRef.objects.using('entire').filter(gene_aliases=alias).order_by('gene__chrom','description')
    genes, exons, num_genes, num_non_overlapping_groups = fns.split_exons_and_get_length(genes)
    context = {
        'gene':gene,
        'genes':genes,
        'exons':exons,
        'num_genes':num_genes,
        'num_non_over': num_non_overlapping_groups,
        }
    return render(request, 'genes/gene_view.html', context)
        
