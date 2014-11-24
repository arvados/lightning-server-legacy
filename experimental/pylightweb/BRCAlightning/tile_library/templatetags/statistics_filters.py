from django import template
import urllib
from tile_library.models import TileVariant
from django.db.models import Avg, Count, Max, Min

register = template.Library()

##@register.filter
##def floatcomma(number):
##    l = number.split('.')
##    

@register.filter
def get_reference_length(position):
    reference = position.tile_variants.get(variant_value=0)
    return reference.length

@register.filter
def get_num_position_annotations(position):
    try:
        return position.num_pos_annotations
    except AttributeError:
        return position.starting_genome_variants.count()
#        return len(position.approx_genomevar)

@register.filter
def get_avg_pos_spanned(position):
    try:
        return position.avg_pos_spanned
    except AttributeError:
        pass
    tile_variant = TileVariant.objects.filter(tile=position).aggregate(avg=Avg("num_positions_spanned"))
    return tile_variant['avg']

@register.filter
def get_max_pos_spanned(position):
    try:
        return position.max_pos_spanned
    except AttributeError:
        tile_variant = TileVariant.objects.filter(tile=position).aggregate(maximum=Max("num_positions_spanned"))
        return tile_variant['maximum']

@register.filter
def get_avg_num_tile_annotations(position):
    try:
        return position.avg_num_tile_annotations
    except AttributeError:
        tile_variant = TileVariant.objects.filter(tile=position).annotate(num_annotation=Count('genome_variants')).aggregate(avg=Avg("num_annotation"))
        return tile_variant['avg']

@register.filter
def get_max_num_tile_annotations(position):
    try:
        return position.max_num_tile_annotations
    except AttributeError:
        tile_variant = TileVariant.objects.filter(tile=position).annotate(num_annotation=Count('genome_variants')).aggregate(maximum=Max("num_annotation"))
        return tile_variant['maximum']

@register.filter
def get_min_len(position):
    try:
        return position.min_len
    except AttributeError:
        tile_variant = TileVariant.objects.filter(tile=position).aggregate(interest=Min("length"))
        return tile_variant['interest']

@register.filter
def get_avg_len(position):
    try:
        return position.avg_len
    except AttributeError:
        tile_variant = TileVariant.objects.filter(tile=position).aggregate(interest=Avg("length"))
        return tile_variant['interest']

@register.filter
def get_max_len(position):
    try:
        return position.max_len
    except AttributeError:
        tile_variant = TileVariant.objects.filter(tile=position).aggregate(interest=Max("length"))
        return tile_variant['interest']

@register.simple_tag
def url_replace(request, field, value):
    """request expected to be request.GET """
    dict_ = request.copy()
    dict_[field] = value
    return urllib.urlencode(dict_)

