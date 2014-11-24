from django import template
import urllib

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
    total = sum([tilevar.num_positions_spanned for tilevar in position.tilevar_with_ann])
    try:
        return float(total)/position.num_var
    except AttributeError:
        num = len(position.tilevar_with_ann)
        return float(total)/num

@register.filter
def get_max_pos_spanned(position):
    try:
        return position.max_pos_spanned
    except AttributeError:
        return max([tilevar.num_positions_spanned for tilevar in position.tilevar_with_ann])

@register.filter
def get_avg_num_tile_annotations(position):
    try:
        return position.avg_num_tile_annotations
    except AttributeError:
        pass
    total = sum([tilevar.num_annotations for tilevar in position.tilevar_with_ann])
    try:
        return float(total)/position.num_var
    except AttributeError:
        num = len(position.tilevar_with_ann)
        return float(total)/num

@register.filter
def get_max_num_tile_annotations(position):
    try:
        return position.max_num_tile_annotations
    except AttributeError:
        return max([tilevar.num_annotations for tilevar in position.tilevar_with_ann])

@register.filter
def get_min_len(position):
    try:
        return position.min_len
    except AttributeError:
        return min([tilevar.length for tilevar in position.tilevar_with_ann])

@register.filter
def get_avg_len(position):
    try:
        return position.avg_len
    except AttributeError:
        total = sum([tilevar.length for tilevar in position.tilevar_with_ann])
        num = len(position.tilevar_with_ann)
        return float(total)/num

@register.filter
def get_max_len(position):
    try:
        return position.max_len
    except AttributeError:
        return max([tilevar.length for tilevar in position.tilevar_with_ann])

@register.simple_tag
def url_replace(request, field, value):
    """request expected to be request.GET """
    dict_ = request.copy()
    dict_[field] = value
    return urllib.urlencode(dict_)

