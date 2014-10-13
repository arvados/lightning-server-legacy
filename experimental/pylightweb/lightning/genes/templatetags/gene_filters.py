from django import template
import string
import urllib

from tile_library.models import TileLocusAnnotation

register = template.Library()


@register.simple_tag
def url_replace(request, field, value):
    dict_ = request.copy()
    dict_[field] = value
    return urllib.urlencode(dict_)

@register.simple_tag
def url_replace_and_clear(request, field, value, *fields_to_clear):
    dict_ = request.copy()
    dict_[field] = value
    for f in fields_to_clear:
        if f in dict_:
            del dict_[f]
    return urllib.urlencode(dict_)

@register.simple_tag
def url_clear(request, *fields_to_clear):
    dict_ = request.copy()
    for f in fields_to_clear:
        if f in dict_:
            del dict_[f]
    return urllib.urlencode(dict_)

@register.filter
def get_gene_review_urls(gene_xref):
    retlist = []
    for url in gene_xref.gene_review_URLs.split(';'):
        if len(url) > 0:
            obj = {'url':url}
            nbkid = url.split('/')[-1]
            for mapping in gene_xref.gene_review_phenotype_map.split(';'):
                if mapping.split(':')[0] == nbkid:
                    obj['phenotype'] = mapping.split(':')[1]
            retlist.append(obj)
    if len(retlist) == 0:
        return None
    else:
        return retlist
        
@register.filter
def assembly_pretty(assembly_int):
    assembly_index = [i for i,j in TileLocusAnnotation.SUPPORTED_ASSEMBLY_CHOICES]
    return TileLocusAnnotation.SUPPORTED_ASSEMBLY_CHOICES[assembly_index.index(assembly_int)][1]

@register.filter
def chromosome_pretty(chr_int):
    chr_index = [i for i,j in TileLocusAnnotation.CHR_CHOICES]
    return TileLocusAnnotation.CHR_CHOICES[chr_index.index(chr_int)][1]

@register.filter
def strand_pretty(strand):
    if strand:
        return '+'
    elif strand == False:
        return '-'
    else:
        return ''


@register.filter
def tile_string(tile):
    strTilename = hex(tile).lstrip('0x').rstrip('L')
    strTilename = strTilename.zfill(9)
    path = strTilename[:3]
    version = strTilename[3:5]
    step = strTilename[5:]
    return string.join([path, version, step], '.')

@register.filter
def pretty_exons(exon_string):
    return exon_string.strip(',').replace(',', ', ')
