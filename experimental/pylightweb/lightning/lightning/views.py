import urllib

from django.shortcuts import render
from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse

from api_gui.forms import AroundLocusForm, BetweenLociForm
from tile_library.models import TileLocusAnnotation, GenomeStatistic, TileVariant
import tile_library.basic_functions as basic_fns
import tile_library.functions as fns
import tile_library.query_functions as query_fns

def home(request):
    """
        Display homepage
    """
    if request.GET.get('assembly') != None:
        #We were asked for something!
        data = request.GET
        GET_url_section = urllib.urlencode(data)
        if 'target_base' in data:
            return HttpResponseRedirect(request.build_absolute_uri(reverse('population_sequence_query:around_locus_form')+'?'+GET_url_section))
        elif 'lower_base' in data:
            return HttpResponseRedirect(request.build_absolute_uri(reverse('population_sequence_query:between_loci_form')+'?'+GET_url_section))
    assembly_converter = dict(TileLocusAnnotation.SUPPORTED_ASSEMBLY_CHOICES)
    chrom_converter = dict(TileLocusAnnotation.CHR_CHOICES)
    possible_assemblies_int = TileLocusAnnotation.objects.order_by(
        'assembly').distinct('assembly').values_list('assembly', flat=True)
    possible_chromosomes_int = TileLocusAnnotation.objects.order_by(
        'chromosome').distinct('chromosome').values_list('chromosome', flat=True)
    possible_assemblies = [(i, assembly_converter[i]) for i in possible_assemblies_int]
    possible_chromosomes = [(i, chrom_converter[i]) for i in possible_chromosomes_int]
    query_around_form=AroundLocusForm(possible_assemblies, possible_chromosomes)
    query_between_form=BetweenLociForm(possible_assemblies, possible_chromosomes)
    return render(request, 'lightning/index.html', {'query_around_form':query_around_form, 'query_between_form':query_between_form})

def help(request):
    """
        Display Questions
    """
    return render(request, 'lightning/help.html')
