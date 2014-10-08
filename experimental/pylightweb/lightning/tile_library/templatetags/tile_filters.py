from django import template
from tile_library.models import Tile, TileVariant

import string
import re

register = template.Library()

@register.filter
def get_SNP_INDEL_annotations(tile):
    return tile.annotations.filter(annotation_type='SNP_INDEL')

@register.filter
def get_readable_annotation_text(annotation):
    text = annotation.annotation_text
    useful = re.search('SNP.*|SUB.*|INDEL.*', text).group(0)
    return useful

@register.filter
def get_database_annotations(tile):
    return tile.annotations.filter(annotation_type='DATABASE')

@register.filter
def get_snps(annotation):
    text = annotation.annotation_text
    rsIDs = re.search('(?<=db_xref)[\s dbsnp\.0-9rs:]*', text).group(0)
    ref = re.search('rs[0-9]+', rsIDs)
    trunc_text = rsIDs
    snp_refs = []
    while ref != None:
        trunc_text = trunc_text[ref.end():]
        snp_refs.append(ref.group(0))
        ref = re.search('rs[0-9]+', trunc_text)
    return snp_refs

@register.filter
def get_aa(annotation):
    text = annotation.annotation_text
    #return text
    amino_acids = re.search('(?<=amino_acid)[\s\w\*]*', text)
    if amino_acids:
        return amino_acids.group(0)
    else:
        return amino_acids

@register.filter
def get_other(annotation):
    #return annotation.annotation_text
    pieces = annotation.annotation_text.split(';')
    retarray = []
    for text in pieces:
        if not (text.startswith('alleles') or text.startswith('amino_acid') or text.startswith('db_xref') or text.startswith('ref_allele')):
            retarray.append(text)                
    return retarray



@register.filter
def get_reference_sequence(tiles):
    reference = tiles.filter(variant_value=0).all()[0]
    seq = reference.sequence
    middle = seq[25:-24]
    return re.split("(.{50})", middle)
    
