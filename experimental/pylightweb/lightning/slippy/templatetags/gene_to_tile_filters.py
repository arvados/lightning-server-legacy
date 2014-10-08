from django import template
from django.db.models import Count,Max,Min

register = template.Library()

@register.filter
def get_tile_start_tx(matching, alias):
    return matching.filter(gene_aliases=alias).aggregate(Min('gene__tile_start_tx'))['gene__tile_start_tx__min']

@register.filter
def get_tile_end_tx(matching, alias):
    return matching.filter(gene_aliases=alias).aggregate(Max('gene__tile_end_tx'))['gene__tile_end_tx__max']
