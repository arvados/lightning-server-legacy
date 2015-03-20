from django import template
from tile_library.models import Tile, TileVariant, VarAnnotation
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.query import QuerySet

import string
import re

register = template.Library()

@register.filter
def strand_pretty(strand):
    assert type(strand)==bool or type(strand)==type(None), "Got unexpected type of input for strand"
    if strand:
        return '+'
    elif strand == False:
        return '-'
    else:
        return ''

@register.filter
def get_SNP_INDEL_annotations(tile_variant):
    assert type(tile_variant)==TileVariant, "Expects type TileVariant for input"
    try:
        return tile_variant.annotations.filter(annotation_type='SNP_INDEL')
    except ObjectDoesNotExist:
        raise BaseException("TileVariant does not exist")

@register.filter
def get_readable_annotation_text(annotation):
    assert type(annotation)==VarAnnotation, "Expects type VarAnnotation for input"
    try:
        assert annotation.annotation_type == 'SNP_INDEL', "Expects VarAnnotation type to be SNP_INDEL"
        text = annotation.annotation_text
        useful = re.search('SNP.*|SUB.*|INDEL.*', text).group(0)
        return useful
    except ObjectDoesNotExist:
        raise BaseException("Annotation does not exist")

@register.filter
def get_database_annotations(tile_variant):
    assert type(tile_variant)==TileVariant, "Expects type TileVariant for input"
    try:
        return tile_variant.annotations.filter(annotation_type='DATABASE')
    except ObjectDoesNotExist:
        raise BaseException("TileVariant does not exist")
    
@register.filter
def get_snps(annotation):
    assert type(annotation)==VarAnnotation, "Expects type VarAnnotation for input"
    try:
        assert annotation.annotation_type == 'DATABASE', "Expects VarAnnotation type to be DATABASE"
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
    except ObjectDoesNotExist:
        raise BaseException("Annotation does not exist")
    

@register.filter
def get_aa(annotation):
    #This assumes only one amino acid note per annotation
    assert type(annotation)==VarAnnotation, "Expects type VarAnnotation for input"
    try:
        assert annotation.annotation_type == 'DATABASE', "Expects VarAnnotation type to be DATABASE"
        text = annotation.annotation_text
        amino_acids = re.search('(?<=amino_acid)[\s\w\*]*', text)
        if amino_acids:
            return amino_acids.group(0)
        else:
            return amino_acids
    except ObjectDoesNotExist:
        raise BaseException("Annotation does not exist")

@register.filter
def get_other(annotation):
    assert type(annotation)==VarAnnotation, "Expects type VarAnnotation for input"
    try:
        assert annotation.annotation_type == 'DATABASE', "Expects VarAnnotation type to be DATABASE"
        pieces = annotation.annotation_text.split(';')
        retarray = []
        for text in pieces:
            if not (text.startswith('alleles') or text.startswith('amino_acid') or text.startswith('db_xref') or text.startswith('ref_allele')):
                retarray.append(text)                
        return retarray
    except ObjectDoesNotExist:
        raise BaseException("Annotation does not exist")



@register.filter
def get_reference_sequence(tiles):
    assert type(tiles)==QuerySet, "Expects type QuerySet for input"
    try:
        reference = tiles.filter(variant_value=0).all()[0]
        seq = reference.sequence
        middle = seq[24:-24]
        tmplist = re.split("(.{50})", middle)
        retlist = []
        for i in tmplist:
            if len(i) > 0:
                retlist.append(i)
        return retlist
    except:
        raise BaseException("TileVariants do not exist")
    
