from django import template
from tile_library.models import Tile, TileVariant, GenomeVariant
from genes.models import GeneXRef
import tile_library.basic_functions as basic_fns
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.query import QuerySet

import string
import re
import json

register = template.Library()

@register.filter
def population_at_variant(variant_to_popul_dict, tile_variant):
    return variant_to_popul_dict[tile_variant.tile_variant_name]

@register.filter
def minus(val1, val2):
    return val1 - val2

@register.filter
def get_increment(increment, prev_ref_length):
    return increment - (int(prev_ref_length)-24)

@register.filter
def to_position_string(pos_int):
    return basic_fns.get_position_string_from_position_int(pos_int)

@register.filter
def aliases_pretty(names):
    aliases = names.split('\t')
    return string.join(aliases, ', ')

@register.filter
def get_base_change(genome_variant):
    reference_seq = genome_variant.reference_bases
    changed_seq = genome_variant.alternate_bases
    return reference_seq+" => "+changed_seq

@register.filter
def list_variants(genome_variants, genome_variants_to_choose_from):
    var_id_to_small_int = {}
    for i, var in enumerate(genome_variants_to_choose_from.all()):
        var_id_to_small_int[int(var.id)] = str(i+1)
    var_ids = []
    for var in genome_variants.all():
        int_id = int(var.id)
        if int_id in var_id_to_small_int:
            var_ids.append(var_id_to_small_int[int_id])
    var_ids.sort()
    return string.join(var_ids, ', ')

@register.simple_tag
def get_all_base_changes(genome_variants, tilevar):
    sequence_changes = []
    for var in genome_variants.all():
        start = var.translation_to_tilevariant.get(tile_variant=tilevar).start
        reference_seq = var.reference_bases
        changed_seq = var.alternate_bases
        sequence_changes.append(str(start) + " " + reference_seq+" => "+changed_seq)
    return string.join(sequence_changes, ', ')

@register.filter
def get_all_aliases(genome_variants, genome_variants_to_choose_from):
    poss_variants = list(genome_variants_to_choose_from.all())
    aliases = []
    for var in genome_variants.all():
        if var in poss_variants:
            if len(var.names) > 0: 
                aliases.extend(var.names.strip().split('\t'))
    return string.join(aliases, ', ')

def parse_info(variant):
    #TODO: reimplement this using regex
    ret_dict = {}
    parsing = variant.info.strip('{} ').split(',')
    for entry in parsing:
        if len(entry) > 0:
            key, value = entry.split(':')
            ret_dict[key.strip()] = value.strip()
    return ret_dict
    

@register.filter
def get_protein_changes(variant):
    #Currently assumes only 1 change per variant!
    #Would be cool to link directly to Gene view if that gene is recognized
    info = parse_info(variant)
    if 'amino_acid' in info:
        indicator, protein, mutation = info['amino_acid'].split(' ')
        return protein+":"+mutation
    else:
        return None

@register.filter
def get_other(variant):
    annotations = []
    info = parse_info(variant)
    for key in info:
        if key not in ['amino_acid', 'source', 'ucsc_trans', 'phenotype']:
            annotations.append(key+" : "+info[key])
    return string.join(annotations, ', ')

@register.filter
def get_all_protein_changes(genome_variants, genome_variants_to_choose_from):
    poss_variants = list(genome_variants_to_choose_from.all())
    changes = []
    for var in genome_variants.all():
        if var in poss_variants:
            protein_change = get_protein_changes(var)
            if protein_change != None:
                changes.append(protein_change)
    return string.join(changes, ', ')

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
    
