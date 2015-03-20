import time
import json
import requests
import re
import urllib

from django.shortcuts import render
from django.http import Http404
from django.core.urlresolvers import reverse

from variant_query.forms import AroundLocusForm, BetweenLociForm
from tile_library.models import TileLocusAnnotation, GenomeStatistic, TileVariant
import tile_library.basic_functions as basic_fns
import tile_library.functions as fns
import tile_library.query_functions as query_fns

def send_internal_api_request(request, GET_dictionary, reverse_url_locator_string):
    GET_url_section = urllib.urlencode(GET_dictionary)
    query_url = request.build_absolute_uri(reverse(reverse_url_locator_string))+'?'+GET_url_section
    return requests.get(url=query_url)

def around_locus_query_view(request):
    """
        Submit a variant query
        Query specs:
            Assembly
            Chromosome
            Target base (0-indexed, 1-indexed)
            k-bases upstream and downstream from target base
        More advanced query specs:
            Population subset
    """
    assembly_converter = dict(TileLocusAnnotation.SUPPORTED_ASSEMBLY_CHOICES)
    chrom_converter = dict(TileLocusAnnotation.CHR_CHOICES)
    possible_assemblies_int = TileLocusAnnotation.objects.order_by(
        'assembly').distinct('assembly').values_list('assembly', flat=True)
    possible_chromosomes_int = TileLocusAnnotation.objects.order_by(
        'chromosome').distinct('chromosome').values_list('chromosome', flat=True)
    t2 = time.time()
    possible_assemblies = [(i, assembly_converter[i]) for i in possible_assemblies_int]
    t3 = time.time()
    possible_chromosomes = [(i, chrom_converter[i]) for i in possible_chromosomes_int]
    t4 = time.time()
    if request.GET.get('assembly') != None:
        #We were asked for something!
        data = request.GET
        form = AroundLocusForm(possible_assemblies, possible_chromosomes, data)
        t5 = time.time()
        api_response = send_internal_api_request(request, data, 'api:pop_around_locus')
        if api_response.status_code == 200:
            humans = json.loads(api_response.text)
            response = {'text':'Success!', 'humans':humans}
        else:
            response = {'text':'Error: ' + api_response.text}
        t6 = time.time()
        response['time'] = t6-t5
    else:
        form=AroundLocusForm(possible_assemblies, possible_chromosomes)
        response = None
    return render(request, 'variant_query/index.html', {'form_name': "Population Sequence Around Locus ", 'form':form, 'time1':t3-t2, 'time2':t4-t3, 'response': response})

def between_loci_query_view(request):
    """
        Submit a variant query
        Query specs:
            Assembly
            Chromosome
            lower base (0-indexed, 1-indexed)
            upper base (0-indexed, 1-indexed)
        More advanced query specs:
            (Currently not implemented)
            Population subset
    """
    assembly_converter = dict(TileLocusAnnotation.SUPPORTED_ASSEMBLY_CHOICES)
    chrom_converter = dict(TileLocusAnnotation.CHR_CHOICES)
    possible_assemblies_int = TileLocusAnnotation.objects.order_by(
        'assembly').distinct('assembly').values_list('assembly', flat=True)
    possible_chromosomes_int = TileLocusAnnotation.objects.order_by(
        'chromosome').distinct('chromosome').values_list('chromosome', flat=True)
    t2 = time.time()
    possible_assemblies = [(i, assembly_converter[i]) for i in possible_assemblies_int]
    t3 = time.time()
    possible_chromosomes = [(i, chrom_converter[i]) for i in possible_chromosomes_int]
    t4 = time.time()
    if request.GET.get('assembly') != None:
        #We were asked for something!
        data = request.GET
        form = BetweenLociForm(possible_assemblies, possible_chromosomes, data)
        t5 = time.time()
        api_response = send_internal_api_request(request, data, 'api:pop_between_loci')
        if api_response.status_code == 200:
            humans = json.loads(api_response.text)
            response = {'text':'Success!', 'humans':humans}
        else:
            response = {'text':'Error: ' + api_response.text}
        t6 = time.time()
        response['time'] = t6-t5
    else:
        form=BetweenLociForm(possible_assemblies, possible_chromosomes)
        response = None
    return render(request, 'variant_query/index.html', {'form_name': "Population Sequence Between Loci ",'form':form, 'time1':t3-t2, 'time2':t4-t3, 'response': response})
