from django import template
from django.db.models import Avg, Count, Max, Min
from tile_library.models import Tile, TileVariant
from tile_library import views

import urllib

register = template.Library()

@register.filter
def get_reference_length(position):
    reference = position.variants.filter(variant_value=0).first()
    return reference.length

@register.simple_tag
def url_replace(request, field, value):
    dict_ = request.copy()
    dict_[field] = value
    return urllib.urlencode(dict_)

