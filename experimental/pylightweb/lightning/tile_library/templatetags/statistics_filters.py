from django import template
from django.db.models import Avg, Count, Max, Min
from tile_library.models import Tile, TileVariant
from tile_library import views


register = template.Library()

@register.filter
def avg_length(tile_var_list):
    return tile_var_list.aggregate(Avg('length'))['length__avg']

@register.filter
def max_num_variants(tile_var_list):
    retval = tile_var_list.aggregate(Max('variant_value'))['variant_value__max']
    if retval != None:
        return int(retval)+1
    else:
        return retval

@register.filter
def get_reference_length(position):
    reference = position.variants.filter(variant_value=0).first()
    return reference.length

@register.filter
def get_avg_length(position):
    if position.variants.count() == 1:
        return None
    else:
        return position.variants.aggregate(Avg('length'))['length__avg']

@register.filter
def narrow_pos_to_chromosome(tile_list, chrom):
    min_accepted, foo = views.convert_chromosome_to_tilename(chrom)
    max_accepted, foo = views.convert_chromosome_to_tilename(chrom + 1)
    positions = tile_list.filter(tilename__gte=min_accepted).filter(tilename__lt=max_accepted)
    return positions

@register.filter
def narrow_tiles_to_chromosome(tile_var_list, chrom):
    foo, min_accepted = views.convert_chromosome_to_tilename(chrom)
    foo, max_accepted = views.convert_chromosome_to_tilename(chrom + 1)
    tiles = tile_var_list.filter(tile_variant_name__gte=min_accepted).filter(tile_variant_name__lt=max_accepted)
    return tiles

@register.filter
def narrow_pos_to_path(tile_list, path):
    min_accepted, foo = views.convert_path_to_tilename(path)
    max_accepted, foo = views.convert_path_to_tilename(path + 1)
    positions = tile_list.filter(tilename__gte=min_accepted).filter(tilename__lt=max_accepted)
    return positions

@register.filter
def narrow_tiles_to_path(tile_var_list, path):
    foo, min_accepted = views.convert_path_to_tilename(path)
    foo, max_accepted = views.convert_path_to_tilename(path + 1)
    tiles = tile_var_list.filter(tile_variant_name__gte=min_accepted).filter(tile_variant_name__lt=max_accepted)
    return tiles

@register.filter
def aggregate_tiles_in_path(tile_var_list, path):
    foo, min_accepted = views.convert_path_to_tilename(path)
    foo, max_accepted = views.convert_path_to_tilename(path + 1)
    max_accepted -= 1
    info = tile_var_list.filter(tile_variant_name__range=(min_accepted, max_accepted)).aggregate(
        avg_var_val=Avg('variant_value'),
        max_var_val=Max('variant_value'),
        min_len=Min('length'),
        avg_len=Avg('length'),
        max_len=Max('length'))
    retval = [info]
    return retval
