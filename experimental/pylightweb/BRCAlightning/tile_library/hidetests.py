from django.test import TestCase, LiveServerTestCase
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core.urlresolvers import reverse
from django.core.paginator import Paginator
from django.core.management import call_command
from selenium.webdriver.firefox.webdriver import WebDriver
from selenium import webdriver

from tile_library.models import Tile, TileVariant, TileLocusAnnotation, GenomeStatistic
import tile_library.basic_functions as basic_fns
import tile_library.functions as fns
import tile_library.generate_stats as gen_stats
import tile_library.views as views
import tile_library.templatetags.statistics_filters as stat_filters
import tile_library.templatetags.tile_filters as tile_filters

from genes.tests import mk_gene_xref, make_gene1, make_gene1pt5, make_diff_assembly, make_chr2_gene, make_gene2, make_gene3, make_gene4, make_tiles
from genes.models import GeneXRef, UCSC_Gene
import genes.functions as gene_fns

import random
import hashlib
import string
import subprocess

#Currently testing functions defined by basic_functions, functions, and models
#Check that generate_stats behaves as expected (adds the correct statistics)
#Checks that performance does not error
#Checks views and functions used by the views for overall statistics, chromosome statistics,
#   and path statistics

#Testing for VarAnnotation will wait until revamp of annotation model (Story #4067)
#View/functionality for tile_views should be revisited after revamp

#Currently no functions are defined for TileLocusAnnotation or GenomeStatistic

LONG_GENE1_CHECK_DICT = {0:False, 1:True, 2:False, 3:False, 4:True, 5:True,
                         6:False, 7:False, 8:False, 9:False, 10:False, 11:False,
                         12:False, 13:False, 14:False, 15:False, 16:False, 17:True}
#Needed to check when paths are crossed
LONG_GENE1_CHECK_LIST = [False, True, False, False, True, True,
                         False, False, False, False, False, False,
                         False, False, False, False, False, True]
def mk_genome_seq(length, uppercase=True):
    if uppercase:
        choices = ['A','G','C','T']
    else:
        choices = ['a','g','c','t']
    s = ''
    for i in range(length):
        s += random.choice(choices)
    return s

def mk_tile(tile_int, start_pos, end_pos, num_vars, lengths, start_tag=None, end_tag=None, assembly=19, chrom=1):
    assert len(lengths) == num_vars
    assert lengths[0] == end_pos-start_pos
    if start_tag == None:
        start_tag = mk_genome_seq(24)
    if end_tag == None:
        end_tag = mk_genome_seq(24)
    new = Tile(tilename=tile_int, start_tag=start_tag, end_tag=end_tag)
    new.save()
    locus = TileLocusAnnotation(assembly=assembly, chromosome=chrom, begin_int=start_pos, end_int=end_pos, tile=new)
    locus.save()
    mk_tilevars(num_vars, lengths, start_tag, end_tag, new, tile_int)
    return new, start_tag, end_tag, locus

def mk_tilevars(num_vars, lengths, start_tag, end_tag, tile, tile_int):
    assert len(lengths) == num_vars
    for i in range(num_vars):
        tile_hex = string.join(basic_fns.convert_position_int_to_position_hex_str(tile_int), "")
        tile_hex += hex(i).lstrip('0x').zfill(3)
        tile_var_int = int(tile_hex, 16)
        length = lengths[i]
        randseq_len = length - 24*2
        seq = start_tag
        seq += mk_genome_seq(randseq_len, uppercase=False)
        seq += end_tag
        digestor = hashlib.new('md5', seq)
        new = TileVariant(tile_variant_name=tile_var_int, tile=tile, variant_value=i, length=length,
                          md5sum=digestor.hexdigest(), sequence=seq, num_positions_spanned=1)
        new.save()
        
def make_long_gene1(assembly=19):
    """(Assembly 19, chr1)
              gene1: 400   |___|       |_____|                      |_____| 5500
                          600-700     1100-1900                    5450-5500
    gene1 (by tile): 0    1                                             17  17
    """
    random_letters = 'foo long'
    g = UCSC_Gene(ucsc_gene_id=random_letters, assembly=assembly, chrom=1, strand=True, start_tx=400,
                           tile_start_tx=0, end_tx=5500, tile_end_tx=17, start_cds=600,
                           tile_start_cds=1, end_cds=5500, tile_end_cds=17, exon_count=3,
                           exon_starts='600,1100,5450', exon_ends='700, 1900, 5500', uniprot_display_id=random_letters,
                           align_id=random_letters)
    g.save()
    mk_gene_xref(g, random_letters, 'gene1')

def make_tiles(assembly_default=19, skip_zero=False):
    """
    creates the following structure:
            i,  min,     avg,  max
            0,  448,  448.67,  450 {'vars':3, 'lengths':[448,448,450]}, #1
            1,  301,  301.00,  301 {'vars':2, 'lengths':[301,301]}, #2
            2,  200,  257.67,  300 {'vars':3, 'lengths':[273,200,300]}, #3
            3,  149,  149.00,  149 {'vars':1, 'lengths':[149]}, #4
            4,  425,  425.00,  425 {'vars':1, 'lengths':[425]}, #5
            5,  500,  549.75,  600 {'vars':4, 'lengths':[549,500,600,550]}, #6
            6,  198,  199.00,  200 {'vars':4, 'lengths':[199,198,200,199]}, #7
            7,  249,  249.00,  249 {'vars':2, 'lengths':[249,249]}, #8
            8,  199,  199.00,  199 {'vars':1, 'lengths':[199]}, #9
            9, 1200, 1200.00, 1200 {'vars':1, 'lengths':[1200]}, #10
           10,  264,  264.50,  265 {'vars':2, 'lengths':[264,265]}, #11
           11,  249,  250.50,  252 {'vars':6, 'lengths':[251,250,250,251,252,249]}, #12
           12,  275,  275.50,  276 {'vars':2, 'lengths':[275,276]}, #13
           13,  277,  277.00,  277 {'vars':2, 'lengths':[277,277]}, #14
           14,  267,  267.00,  267 {'vars':1, 'lengths':[267]}, #15
           15,  258,  258.00,  258 {'vars':1, 'lengths':[258]}, #16
           16,  248,  248.00,  248 {'vars':3, 'lengths':[248,248,248]}, #17
           17,  250,  250.00,  250 {'vars':1, 'lengths':[250]}, #18
           
    loci = [(0, 448),    #0 -> 448
            (448-24, 725),#1 -> 301
            (725-24, 974),#2 -> 273
            (974-24, 1099),#3 -> 149
            (1099-24,1500),#4 -> 425
            (1500-24,2025),#5 -> 549
            (2025-24,2200),#6 -> 199
            (2200-24,2425),#7 -> 249
            (2425-24,2600),#8 -> 199
            ]

    """
    tile_vars = [
            {'vars':3, 'lengths':[448,448,450]}, #1
            {'vars':2, 'lengths':[301,301]}, #2
            {'vars':3, 'lengths':[273,200,300]}, #3
            {'vars':1, 'lengths':[149]}, #4
            {'vars':1, 'lengths':[425]}, #5
            {'vars':4, 'lengths':[549,500,600,550]}, #6
            {'vars':4, 'lengths':[199,198,200,199]}, #7
            {'vars':2, 'lengths':[249,249]}, #8
            {'vars':1, 'lengths':[199]}, #9
            {'vars':1, 'lengths':[1200]}, #10
            {'vars':2, 'lengths':[264,265]}, #11
            {'vars':6, 'lengths':[251,250,250,251,252,249]}, #12
            {'vars':2, 'lengths':[275,276]}, #13
            {'vars':2, 'lengths':[277,277]}, #14
            {'vars':1, 'lengths':[267]}, #15
            {'vars':1, 'lengths':[258]}, #16
            {'vars':3, 'lengths':[248,248,248]}, #17
            {'vars':1, 'lengths':[250]}, #18
        ]
    locus = 0
    if skip_zero:
        call_command('loaddata', 'test_view_tiles', verbosity=0)
        t = Tile.objects.get(pk=0)
        new_start_tag = t.start_tag
        l = TileLocusAnnotation(assembly=assembly_default, chromosome=1, begin_int=0, end_int=448, tile=t)
        l.save()
        locus += 448-24
        for j in range(1, 18):
            t, foo, new_start_tag, annotation = mk_tile(j, locus, tile_vars[j]['lengths'][0]+locus, tile_vars[j]['vars'], tile_vars[j]['lengths'], start_tag=new_start_tag, assembly=assembly_default)
            #print j, locus, locus+tile_vars[j]['lengths'][0]
            locus += tile_vars[j]['lengths'][0] - 24
    else:
        for j in range(18):
            if j == 0:
                t, foo, new_start_tag, annotation = mk_tile(j, locus, tile_vars[j]['lengths'][0]+locus, tile_vars[j]['vars'], tile_vars[j]['lengths'], assembly=assembly_default)
            else:
                t, foo, new_start_tag, annotation = mk_tile(j, locus, tile_vars[j]['lengths'][0]+locus, tile_vars[j]['vars'], tile_vars[j]['lengths'], start_tag=new_start_tag, assembly=assembly_default)
            #print j, locus, locus+tile_vars[j]['lengths'][0]
            locus += tile_vars[j]['lengths'][0] - 24
            
    locus = 0
    t, foo, new_start_tag, annotation = mk_tile(1000, locus, tile_vars[0]['lengths'][0]+locus, 1, [tile_vars[0]['lengths'][0]], assembly=assembly_default, chrom=2)
    locus += tile_vars[0]['lengths'][0] - 24
    for i in range(1, 5):
        t, foo, new_start_tag, annotation = mk_tile(i+1000, locus, tile_vars[i]['lengths'][0]+locus, 1, [tile_vars[i]['lengths'][0]], start_tag=new_start_tag,
                                                    assembly=assembly_default, chrom=2)
        locus += tile_vars[i]['lengths'][0] - 24
                                                    
def make_ridiculously_long_gene(assembly_default=19):
    """
        (Assembly 19, chr1)
                gene1: 400          |___|       |_____|               |_____|        5500
                                   600-700     1100-1900             5450-5500
      gene1 (by tile): 0.00.0000   0.00.0001                              2.00.0004  2.00.0004
    
    creates the following structure:
            i,  min,     avg,  max
        Path 0:
            0,  448,  448.67,  450 {'vars':3, 'lengths':[448,448,450]}, #1
            1,  301,  301.00,  301 {'vars':2, 'lengths':[301,301]}, #2
            2,  200,  257.67,  300 {'vars':3, 'lengths':[273,200,300]}, #3
            3,  149,  149.00,  149 {'vars':1, 'lengths':[149]}, #4
            4,  425,  425.00,  425 {'vars':1, 'lengths':[425]}, #5
        Path 1:
            0,  500,  549.75,  600 {'vars':4, 'lengths':[549,500,600,550]}, #6
            1,  198,  199.00,  200 {'vars':4, 'lengths':[199,198,200,199]}, #7
            2,  249,  249.00,  249 {'vars':2, 'lengths':[249,249]}, #8
            3,  199,  199.00,  199 {'vars':1, 'lengths':[199]}, #9
            4, 1200, 1200.00, 1200 {'vars':1, 'lengths':[1200]}, #10
            5,  264,  264.50,  265 {'vars':2, 'lengths':[264,265]}, #11
            6,  249,  250.50,  252 {'vars':6, 'lengths':[251,250,250,251,252,249]}, #12
            7,  275,  275.50,  276 {'vars':2, 'lengths':[275,276]}, #13
        Path 2:
            0,  277,  277.00,  277 {'vars':2, 'lengths':[277,277]}, #14
            1,  267,  267.00,  267 {'vars':1, 'lengths':[267]}, #15
            2,  258,  258.00,  258 {'vars':1, 'lengths':[258]}, #16
            3,  248,  248.00,  248 {'vars':3, 'lengths':[248,248,248]}, #17
            4,  250,  250.00,  250 {'vars':1, 'lengths':[250]}, #18
           
    loci = [(0, 448),    #0 -> 448
            (448-24, 725),#1 -> 301
            (725-24, 974),#2 -> 273
            (974-24, 1099),#3 -> 149
            (1099-24,1500),#4 -> 425
            (1500-24,2025),#5 -> 549
            (2025-24,2200),#6 -> 199
            (2200-24,2425),#7 -> 249
            (2425-24,2600),#8 -> 199
            ]

    """
    tile_vars = [
            {'vars':3, 'lengths':[448,448,450]}, #1
            {'vars':2, 'lengths':[301,301]}, #2
            {'vars':3, 'lengths':[273,200,300]}, #3
            {'vars':1, 'lengths':[149]}, #4
            {'vars':1, 'lengths':[425]}, #5
            {'vars':4, 'lengths':[549,500,600,550]}, #6
            {'vars':4, 'lengths':[199,198,200,199]}, #7
            {'vars':2, 'lengths':[249,249]}, #8
            {'vars':1, 'lengths':[199]}, #9
            {'vars':1, 'lengths':[1200]}, #10
            {'vars':2, 'lengths':[264,265]}, #11
            {'vars':6, 'lengths':[251,250,250,251,252,249]}, #12
            {'vars':2, 'lengths':[275,276]}, #13
            {'vars':2, 'lengths':[277,277]}, #14
            {'vars':1, 'lengths':[267]}, #15
            {'vars':1, 'lengths':[258]}, #16
            {'vars':3, 'lengths':[248,248,248]}, #17
            {'vars':1, 'lengths':[250]}, #18
        ]
    
    locus = 0
    for j in range(18):
        if j == 0:
            t, foo, new_start_tag, annotation = mk_tile(j, locus, tile_vars[j]['lengths'][0]+locus, tile_vars[j]['vars'], tile_vars[j]['lengths'], assembly=assembly_default)
        elif j < 5:
            t, foo, new_start_tag, annotation = mk_tile(j, locus, tile_vars[j]['lengths'][0]+locus, tile_vars[j]['vars'], tile_vars[j]['lengths'], start_tag=new_start_tag, assembly=assembly_default)
        elif j < 13:
            i = j - 5
            i = int('100000'+str(i), 16)
            t, foo, new_start_tag, annotation = mk_tile(i, locus, tile_vars[j]['lengths'][0]+locus, tile_vars[j]['vars'], tile_vars[j]['lengths'], start_tag=new_start_tag, assembly=assembly_default)
        elif j < 18:
            i = j - 13
            i = int('200000'+str(i), 16)
            t, foo, new_start_tag, annotation = mk_tile(i, locus, tile_vars[j]['lengths'][0]+locus, tile_vars[j]['vars'], tile_vars[j]['lengths'], start_tag=new_start_tag, assembly=assembly_default)
        #print j, locus, locus+tile_vars[j]['lengths'][0]
        locus += tile_vars[j]['lengths'][0] - 24

    for j in range(10):
        i = int(hex(Tile.CHR_PATH_LENGTHS[1]).lstrip('0x').zfill(1)+"00000"+str(j), 16)
        if j == 0:
            t, foo, new_start_tag, annotation = mk_tile(i, locus, tile_vars[j]['lengths'][0]+locus, tile_vars[j]['vars'], tile_vars[j]['lengths'], assembly=assembly_default)
        else:
            t, foo, new_start_tag, annotation = mk_tile(i, locus, tile_vars[j]['lengths'][0]+locus, tile_vars[j]['vars'], tile_vars[j]['lengths'], start_tag=new_start_tag, assembly=assembly_default)
        #print j, locus, locus+tile_vars[j]['lengths'][0]
        locus += tile_vars[j]['lengths'][0] - 24
        
    random_letters = 'foo long'
    g = UCSC_Gene(ucsc_gene_id=random_letters, assembly=19, chrom=1, strand=True, start_tx=400,
                           tile_start_tx=0, end_tx=5500, tile_end_tx=int('2000004', 16), start_cds=600,
                           tile_start_cds=1, end_cds=5500, tile_end_cds=int('2000004', 16), exon_count=3,
                           exon_starts='600,1100,5450', exon_ends='700, 1900, 5500', uniprot_display_id=random_letters,
                           align_id=random_letters)
    g.save()
    mk_gene_xref(g, random_letters, 'gene1')

######################### TEST basic_functions ###################################
class TestBasicFunctions(TestCase):
    def test_convert_position_int_to_position_hex_str(self):
        """ Expects integer between 0 and 68719476735, returns 3 strings """
        tile_int = int('0c003020f', 16)
        path, version, step = basic_fns.convert_position_int_to_position_hex_str(tile_int)
        self.assertEqual(type(path), str)
        self.assertEqual(type(version), str)
        self.assertEqual(type(step), str)
        self.assertEqual(path, '0c0')
        self.assertEqual(version, '03')
        self.assertEqual(step, '020f')
        tile_int = int('1c003020f', 16)
        path, version, step = basic_fns.convert_position_int_to_position_hex_str(tile_int)
        self.assertEqual(path, '1c0')
        self.assertEqual(version, '03')
        self.assertEqual(step, '020f')
        
    def test_convert_position_int_to_position_hex_str_failure(self):
        self.assertRaises(AssertionError, basic_fns.convert_position_int_to_position_hex_str, '10')
        self.assertRaises(AssertionError, basic_fns.convert_position_int_to_position_hex_str, -1)
        self.assertRaises(AssertionError, basic_fns.convert_position_int_to_position_hex_str, int('1000000000', 16))
        
    def test_convert_tile_variant_int_to_tile_hex_str(self):
        """ Expects integer, returns 4 strings """
        tile_int = int('0c010020f0a0', 16)
        path, version, step, var = basic_fns.convert_tile_variant_int_to_tile_hex_str(tile_int)
        self.assertEqual(type(path), str)
        self.assertEqual(type(version), str)
        self.assertEqual(type(step), str)
        self.assertEqual(type(var), str)
        self.assertEqual(path, '0c0')
        self.assertEqual(version, '10')
        self.assertEqual(step, '020f')
        self.assertEqual(var, '0a0')
        tile_int = int('1c010020f0a0', 16)
        path, version, step, var = basic_fns.convert_tile_variant_int_to_tile_hex_str(tile_int)
        self.assertEqual(path, '1c0')
        self.assertEqual(version, '10')
        self.assertEqual(step, '020f')
        self.assertEqual(var, '0a0')
        
    def test_convert_tile_variant_int_to_tile_hex_str_failure(self):
        self.assertRaises(AssertionError, basic_fns.convert_tile_variant_int_to_tile_hex_str, '10')
        self.assertRaises(AssertionError, basic_fns.convert_tile_variant_int_to_tile_hex_str, -1)
        self.assertRaises(AssertionError, basic_fns.convert_tile_variant_int_to_tile_hex_str, int('1000000000000', 16))
        
    def test_get_position_string_from_position_int(self):
        """ Expects integer, returns string """
        tile_int = int('1c403002f', 16)
        self.assertEqual(type(basic_fns.get_position_string_from_position_int(tile_int)), str)
        self.assertEqual(basic_fns.get_position_string_from_position_int(tile_int), '1c4.03.002f')
        tile_int = int('0', 16)
        self.assertEqual(basic_fns.get_position_string_from_position_int(tile_int), '000.00.0000')
        tile_int = int('1000', 16)
        self.assertEqual(basic_fns.get_position_string_from_position_int(tile_int), '000.00.1000')
        tile_int = int('10000', 16)
        self.assertEqual(basic_fns.get_position_string_from_position_int(tile_int), '000.01.0000')
        tile_int = int('100000', 16)
        self.assertEqual(basic_fns.get_position_string_from_position_int(tile_int), '000.10.0000')
        tile_int = int('1000000', 16)
        self.assertEqual(basic_fns.get_position_string_from_position_int(tile_int), '001.00.0000')
        tile_int = int('10000000', 16)
        self.assertEqual(basic_fns.get_position_string_from_position_int(tile_int), '010.00.0000')
        
    def test_get_position_string_from_position_int_failure(self):
        self.assertRaises(AssertionError, basic_fns.get_position_string_from_position_int, '10')
        self.assertRaises(AssertionError, basic_fns.get_position_string_from_position_int, -1)
        self.assertRaises(AssertionError, basic_fns.get_position_string_from_position_int, int('1000000000', 16))
        
    def test_get_position_ints_from_position_int(self):
        """ Expects integer, returns 3 integers """
        tile_int = int('0c003020f', 16)
        path, version, step = basic_fns.get_position_ints_from_position_int(tile_int)
        self.assertEqual(type(path), int)
        self.assertEqual(type(version), int)
        self.assertEqual(type(step), int)
        self.assertEqual(path, int('0c0',16))
        self.assertEqual(version, int('03',16))
        self.assertEqual(step, int('020f',16))

    def test_get_position_ints_from_position_int_failure(self):
        self.assertRaises(AssertionError, basic_fns.get_position_ints_from_position_int, '10')
        self.assertRaises(AssertionError, basic_fns.get_position_ints_from_position_int, -1)
        self.assertRaises(AssertionError, basic_fns.get_position_ints_from_position_int, int('1000000000', 16))
        
    def test_get_tile_variant_string_from_tile_variant_int(self):
        """ Expects integer, returns string """
        tile_variant_int = int('1c403002f0f3', 16)
        self.assertEqual(type(basic_fns.get_tile_variant_string_from_tile_variant_int(tile_variant_int)), str)
        self.assertEqual(basic_fns.get_tile_variant_string_from_tile_variant_int(tile_variant_int), '1c4.03.002f.0f3')
        tile_variant_int = int('10', 16)
        self.assertEqual(basic_fns.get_tile_variant_string_from_tile_variant_int(tile_variant_int), '000.00.0000.010')
        tile_variant_int = int('1000100', 16)
        self.assertEqual(basic_fns.get_tile_variant_string_from_tile_variant_int(tile_variant_int), '000.00.1000.100')
        tile_variant_int = int('10000001', 16)
        self.assertEqual(basic_fns.get_tile_variant_string_from_tile_variant_int(tile_variant_int), '000.01.0000.001')
        tile_variant_int = int('100000010', 16)
        self.assertEqual(basic_fns.get_tile_variant_string_from_tile_variant_int(tile_variant_int), '000.10.0000.010')
        tile_variant_int = int('1000000100', 16)
        self.assertEqual(basic_fns.get_tile_variant_string_from_tile_variant_int(tile_variant_int), '001.00.0000.100')
        tile_variant_int = int('10000000020', 16)
        self.assertEqual(basic_fns.get_tile_variant_string_from_tile_variant_int(tile_variant_int), '010.00.0000.020')

    def test_get_tile_variant_string_from_tile_variant_int_failure(self):
        self.assertRaises(AssertionError, basic_fns.get_tile_variant_string_from_tile_variant_int, '10')
        self.assertRaises(AssertionError, basic_fns.get_tile_variant_string_from_tile_variant_int, -1)
        self.assertRaises(AssertionError, basic_fns.get_tile_variant_string_from_tile_variant_int, int('1000000000000', 16))
        
    def test_get_tile_variant_ints_from_tile_variant_int(self):
        """ Expects integer, returns 4 integers """
        tile_int = int('0c003020f0a0', 16)
        path, version, step, var = basic_fns.get_tile_variant_ints_from_tile_variant_int(tile_int)
        self.assertEqual(type(path), int)
        self.assertEqual(type(version), int)
        self.assertEqual(type(step), int)
        self.assertEqual(path, int('0c0',16))
        self.assertEqual(version, int('03',16))
        self.assertEqual(step, int('020f',16))
        self.assertEqual(var, int('0a0',16))
        
    def test_get_tile_variant_string_from_tile_variant_int_failure(self):
        self.assertRaises(AssertionError, basic_fns.get_tile_variant_ints_from_tile_variant_int, '10')
        self.assertRaises(AssertionError, basic_fns.get_tile_variant_ints_from_tile_variant_int, -1)
        self.assertRaises(AssertionError, basic_fns.get_tile_variant_ints_from_tile_variant_int, int('1000000000000', 16))
        
    def test_convert_position_int_to_tile_variant_int(self):
        """ Expects integer, returns integer """
        tile_int = int('1c403002f', 16)
        check_int = int('1c403002f000', 16)
        self.assertEqual(type(basic_fns.convert_position_int_to_tile_variant_int(tile_int)), int)
        self.assertEqual(basic_fns.convert_position_int_to_tile_variant_int(tile_int), check_int)
        tile_int = int('0', 16)
        check_int = 0
        self.assertEqual(basic_fns.convert_position_int_to_tile_variant_int(tile_int), check_int)
        tile_int = int('1000', 16)
        check_int = int('1000000', 16)
        self.assertEqual(basic_fns.convert_position_int_to_tile_variant_int(tile_int), check_int)
        tile_int = int('10000', 16)
        check_int = int('10000000', 16)
        self.assertEqual(basic_fns.convert_position_int_to_tile_variant_int(tile_int), check_int)
        tile_int = int('100000', 16)
        check_int = int('100000000', 16)
        self.assertEqual(basic_fns.convert_position_int_to_tile_variant_int(tile_int), check_int)
        tile_int = int('1000000', 16)
        check_int = int('1000000000', 16)
        self.assertEqual(basic_fns.convert_position_int_to_tile_variant_int(tile_int), check_int)
        tile_int = int('10000000', 16)
        check_int = int('10000000000', 16)
        self.assertEqual(basic_fns.convert_position_int_to_tile_variant_int(tile_int), check_int)
        
    def test_convert_position_int_to_tile_variant_int_failure(self):
        self.assertRaises(AssertionError, basic_fns.convert_position_int_to_tile_variant_int, '10')
        self.assertRaises(AssertionError, basic_fns.convert_position_int_to_tile_variant_int, -1)
        self.assertRaises(AssertionError, basic_fns.convert_position_int_to_tile_variant_int, int('1000000000', 16))

    def test_convert_tile_variant_int_to_position_int(self):
        """ Expects int, returns int """
        tile_int = int('1c403002f', 16)
        tile_variant_int = int('1c403002f000', 16)
        self.assertEqual(type(basic_fns.convert_tile_variant_int_to_position_int(tile_variant_int)), int)
        self.assertEqual(basic_fns.convert_tile_variant_int_to_position_int(tile_variant_int), tile_int)
        tile_variant_int = int('1c403002f001', 16)
        self.assertEqual(basic_fns.convert_tile_variant_int_to_position_int(tile_variant_int), tile_int)
        tile_variant_int = int('1c403002f010', 16)
        self.assertEqual(basic_fns.convert_tile_variant_int_to_position_int(tile_variant_int), tile_int)
        tile_variant_int = int('1c403002f100', 16)
        self.assertEqual(basic_fns.convert_tile_variant_int_to_position_int(tile_variant_int), tile_int)
        
        tile_int = int('0', 16)
        tile_variant_int = 0
        self.assertEqual(basic_fns.convert_tile_variant_int_to_position_int(tile_variant_int), tile_int)
        tile_int = int('1000', 16)
        tile_variant_int = int('1000000', 16)
        self.assertEqual(basic_fns.convert_tile_variant_int_to_position_int(tile_variant_int), tile_int)
        tile_int = int('10000', 16)
        tile_variant_int = int('10000000', 16)
        self.assertEqual(basic_fns.convert_tile_variant_int_to_position_int(tile_variant_int), tile_int)
        tile_int = int('100000', 16)
        tile_variant_int = int('100000000', 16)
        self.assertEqual(basic_fns.convert_tile_variant_int_to_position_int(tile_variant_int), tile_int)
        tile_int = int('1000000', 16)
        tile_variant_int = int('1000000000', 16)
        self.assertEqual(basic_fns.convert_tile_variant_int_to_position_int(tile_variant_int), tile_int)
        tile_int = int('10000000', 16)
        tile_variant_int= int('10000000000', 16)
        self.assertEqual(basic_fns.convert_tile_variant_int_to_position_int(tile_variant_int), tile_int)
        
    def test_convert_tile_variant_int_to_position_failure(self):
        self.assertRaises(AssertionError, basic_fns.convert_tile_variant_int_to_position_int, '10')
        self.assertRaises(AssertionError, basic_fns.convert_tile_variant_int_to_position_int, -1)
        self.assertRaises(AssertionError, basic_fns.convert_tile_variant_int_to_position_int, int('1000000000000', 16))

################################## TEST functions ###################################       
class TestAdvancedFunctions(TestCase):
    def test_get_min_position_and_tile_variant_from_path_int(self):
        """ Expects int, returns two integers"""
        tile_int = int('1c4000000', 16)
        tile_variant_int = int('1c4000000000', 16)
        name, varname = fns.get_min_position_and_tile_variant_from_path_int(int('1c4',16))
        self.assertEqual(type(name), int)
        self.assertEqual(type(varname), int)
        self.assertEqual(name, tile_int)
        self.assertEqual(varname, tile_variant_int)
        
        name, varname = fns.get_min_position_and_tile_variant_from_path_int(0)
        self.assertEqual(name, 0)
        self.assertEqual(varname, 0)
        
        tile_int = int('1000000', 16)
        tile_variant_int = int('1000000000', 16)
        name, varname = fns.get_min_position_and_tile_variant_from_path_int(1)
        self.assertEqual(name, tile_int)
        self.assertEqual(varname, tile_variant_int)
        
        tile_int = int('10000000', 16)
        tile_variant_int= int('10000000000', 16)
        name, varname = fns.get_min_position_and_tile_variant_from_path_int(16)
        self.assertEqual(name, tile_int)
        self.assertEqual(varname, tile_variant_int)

    def test_get_min_position_and_tile_variant_from_path_int_failure(self):
        self.assertRaises(AssertionError, fns.get_min_position_and_tile_variant_from_path_int, '1')
        self.assertRaises(AssertionError, fns.get_min_position_and_tile_variant_from_path_int, -1)
        bad_path = Tile.CHR_PATH_LENGTHS[-1] + 1
        self.assertRaises(AssertionError, fns.get_min_position_and_tile_variant_from_path_int, bad_path)

    #Is it acceptable to use an already tested function to check against another function?
    def test_get_min_position_and_tile_variant_from_chromosome_int(self):
        for i, path_int in enumerate(Tile.CHR_PATH_LENGTHS):
            name, varname = fns.get_min_position_and_tile_variant_from_chromosome_int(i+1)
            exp_name, exp_varname = fns.get_min_position_and_tile_variant_from_path_int(int(path_int))
            self.assertEqual(name, exp_name)
            self.assertEqual(varname, exp_varname)
        
    def test_get_min_position_and_tile_variant_from_chromosome_int_failure(self):
        self.assertRaises(AssertionError, fns.get_min_position_and_tile_variant_from_chromosome_int, '1')
        self.assertRaises(BaseException, fns.get_min_position_and_tile_variant_from_chromosome_int, 0)
        self.assertRaises(BaseException, fns.get_min_position_and_tile_variant_from_chromosome_int, 28)

    def test_get_chromosome_int_from_position_int(self):
        # Not implemented yet
        self.assertRaises(BaseException, fns.get_chromosome_int_from_position_int, 0)

    def test_get_chromosome_int_from_position_int_failure(self):
        # Not implemented yet
        self.assertRaises(BaseException, fns.get_chromosome_int_from_position_int, 0)
        
    def test_get_chromosome_int_from_tile_variant_int(self):
        #Not implemented yet
        self.assertRaises(BaseException, fns.get_chromosome_int_from_tile_variant_int, 0)
        
    def test_get_chromosome_int_from_tile_variant_int_failure(self):
        #Not implemented yet
        self.assertRaises(BaseException, fns.get_chromosome_int_from_tile_variant_int, 0)
        
    #Feels a bit weird because the last populated path is 25, but technical last path is 26...
    def test_get_chromosome_int_from_path_int(self):
        path_in_one = Tile.CHR_PATH_LENGTHS[1]/2
        self.assertEqual(fns.get_chromosome_int_from_path_int(path_in_one), 1)
        path_in_one = 0
        self.assertEqual(fns.get_chromosome_int_from_path_int(path_in_one), 1)
        path_in_two = Tile.CHR_PATH_LENGTHS[1]
        self.assertEqual(fns.get_chromosome_int_from_path_int(path_in_two), 2)
        path_in_last = Tile.CHR_PATH_LENGTHS[-1]-1
        self.assertEqual(fns.get_chromosome_int_from_path_int(path_in_last), 25)
        
    def test_get_chromosome_int_from_path_int_failure(self):
        self.assertRaises(AssertionError, fns.get_chromosome_int_from_path_int, -1)
        bad_path = Tile.CHR_PATH_LENGTHS[-1]
        self.assertRaises(BaseException, fns.get_chromosome_int_from_path_int, bad_path)
    
    #Feels a bit weird because the names might change...
    def test_get_chromosome_name_from_chromosome_int(self):
        self.assertEqual(fns.get_chromosome_name_from_chromosome_int(1), 'chr1')
        self.assertEqual(fns.get_chromosome_name_from_chromosome_int(23), 'chrX')
        self.assertEqual(fns.get_chromosome_name_from_chromosome_int(24), 'chrY')
        self.assertEqual(fns.get_chromosome_name_from_chromosome_int(25), 'chrM')
        
    def test_get_chromosome_name_from_chromosome_int_failure(self):
        self.assertRaises(AssertionError, fns.get_chromosome_name_from_chromosome_int, '1')
        self.assertRaises(ValueError, fns.get_chromosome_name_from_chromosome_int, -1)
        self.assertRaises(ValueError, fns.get_chromosome_name_from_chromosome_int, 27)


################################## TEST models ###################################   
class TestTileMethods(TestCase):
    def test_get_tile_string(self):
        """
        Tile.getTileString() returns str
        Testing with Tile 1c4.03.002f
        000.00.0000
        000.00.1000
        000.01.0000
        000.10.0000
        001.00.0000
        010.00.0000
        """
        tile_int = int('1c403002f', 16)
        new_tile = Tile(tilename=tile_int, start_tag="ACGT", end_tag="CCCG")
        self.assertEqual(type(new_tile.getTileString()), str)
        self.assertEqual(new_tile.getTileString(), '1c4.03.002f')
        tile_int = int('0', 16)
        new_tile = Tile(tilename=tile_int, start_tag="ACGT", end_tag="CCCG")
        self.assertEqual(new_tile.getTileString(), '000.00.0000')
        tile_int = int('1000', 16)
        new_tile = Tile(tilename=tile_int, start_tag="ACGT", end_tag="CCCG")
        self.assertEqual(new_tile.getTileString(), '000.00.1000')
        tile_int = int('10000', 16)
        new_tile = Tile(tilename=tile_int, start_tag="ACGT", end_tag="CCCG")
        self.assertEqual(new_tile.getTileString(), '000.01.0000')
        tile_int = int('100000', 16)
        new_tile = Tile(tilename=tile_int, start_tag="ACGT", end_tag="CCCG")
        self.assertEqual(new_tile.getTileString(), '000.10.0000')
        tile_int = int('1000000', 16)
        new_tile = Tile(tilename=tile_int, start_tag="ACGT", end_tag="CCCG")
        self.assertEqual(new_tile.getTileString(), '001.00.0000')
        tile_int = int('10000000', 16)
        new_tile = Tile(tilename=tile_int, start_tag="ACGT", end_tag="CCCG")
        self.assertEqual(new_tile.getTileString(), '010.00.0000')

    def test_tile_constants(self):
        """
        Tile defines CHR_PATH_LENGTHS and CYTOMAP, check that these definitions
        are as expected
        """
        chr_list = Tile.CHR_PATH_LENGTHS
        cytomap = Tile.CYTOMAP
        #Check type of lists
        self.assertEqual(type(chr_list), list)
        self.assertEqual(type(cytomap), list)
        #Check format of CHR_PATH_LENGTHS
        for i, length in enumerate(chr_list):
            self.assertEqual(type(length), int)
            if i > 0:
                self.assertGreaterEqual(length, chr_list[i-1])
            else:
                self.assertEqual(length, 0)
        self.assertEqual(len(chr_list), 27)
        #Make sure we have the same number of paths and cytomap entries
        self.assertEqual(len(cytomap), chr_list[-1])
        for s in cytomap:
            self.assertEqual(type(s), str)

            
################################## TEST models continued ###################################
class TestTileVariantMethods(TestCase):
    def test_get_string(self):
        """
        TileVariant.getString() returns str
        Testing with Tile 1c4.03.002f
        TileVariant 1c4.03.002f.0f3
        000.00.0000 => 010
        000.00.1000 => 100
        000.01.0000 => 001
        000.10.0000 => 010
        001.00.0000 => 100
        010.00.0000 => 020
        """
        tile_int = int('1c403002f', 16)
        new_tile = Tile(tilename=tile_int, start_tag="ACGT", end_tag="CCCG")
        tile_variant_int = int('1c403002f0f3', 16)
        new_tile_variant = TileVariant(tile_variant_name=tile_variant_int,tile=new_tile, variant_value=int('f3',16),
                                       length=250, md5sum="05fee", sequence="TO BIG TO STORE", num_positions_spanned=1)
        self.assertEqual(type(new_tile_variant.getString()), str)
        self.assertEqual(new_tile_variant.getString(), '1c4.03.002f.0f3')
        
        tile_int = int('0', 16)
        new_tile = Tile(tilename=tile_int, start_tag="ACGT", end_tag="CCCG")
        tile_variant_int = int('10', 16)
        new_tile_variant = TileVariant(tile_variant_name=tile_variant_int,tile=new_tile, variant_value=int('10',16),
                                       length=250, md5sum="05fee", sequence="TO BIG TO STORE", num_positions_spanned=1)
        self.assertEqual(new_tile_variant.getString(), '000.00.0000.010')

        tile_int = int('1000', 16)
        new_tile = Tile(tilename=tile_int, start_tag="ACGT", end_tag="CCCG")
        tile_variant_int = int('1000100', 16)
        new_tile_variant = TileVariant(tile_variant_name=tile_variant_int,tile=new_tile, variant_value=int('100',16),
                                       length=250, md5sum="05fee", sequence="TO BIG TO STORE", num_positions_spanned=1)
        self.assertEqual(new_tile_variant.getString(), '000.00.1000.100')
        
        tile_int = int('10000', 16)
        new_tile = Tile(tilename=tile_int, start_tag="ACGT", end_tag="CCCG")
        tile_variant_int = int('10000001', 16)
        new_tile_variant = TileVariant(tile_variant_name=tile_variant_int,tile=new_tile, variant_value=int('10',16),
                                       length=250, md5sum="05fee", sequence="TO BIG TO STORE", num_positions_spanned=1)
        self.assertEqual(new_tile_variant.getString(), '000.01.0000.001')

        tile_int = int('100000', 16)
        new_tile = Tile(tilename=tile_int, start_tag="ACGT", end_tag="CCCG")
        tile_variant_int = int('100000010', 16)
        new_tile_variant = TileVariant(tile_variant_name=tile_variant_int,tile=new_tile, variant_value=int('10',16),
                                       length=250, md5sum="05fee", sequence="TO BIG TO STORE", num_positions_spanned=1)
        self.assertEqual(new_tile_variant.getString(), '000.10.0000.010')

        tile_int = int('1000000', 16)
        new_tile = Tile(tilename=tile_int, start_tag="ACGT", end_tag="CCCG")
        tile_variant_int = int('1000000100', 16)
        new_tile_variant = TileVariant(tile_variant_name=tile_variant_int,tile=new_tile, variant_value=int('10',16),
                                       length=250, md5sum="05fee", sequence="TO BIG TO STORE", num_positions_spanned=1)
        self.assertEqual(new_tile_variant.getString(), '001.00.0000.100')

        tile_int = int('10000000', 16)
        new_tile = Tile(tilename=tile_int, start_tag="ACGT", end_tag="CCCG")
        tile_variant_int = int('10000000020', 16)
        new_tile_variant = TileVariant(tile_variant_name=tile_variant_int,tile=new_tile, variant_value=int('10',16),
                                       length=250, md5sum="05fee", sequence="TO BIG TO STORE", num_positions_spanned=1)
        self.assertEqual(new_tile_variant.getString(), '010.00.0000.020')
    def test_is_reference(self):
        """
        Tile.isReference() returns boolean
        Testing with Tile 0a1.00.1004
        """
        tilename = int('a1001004', 16)
        new_tile = Tile(tilename=tilename, start_tag="ACGT", end_tag="CCCG")
        tile_variant_int = int('a1001004003', 16)
        new_tile_variant = TileVariant(tile_variant_name=tile_variant_int,tile=new_tile, variant_value=3,
                                       length=250, md5sum="05fee", sequence="TO BIG TO STORE", num_positions_spanned=1)
        self.assertEqual(type(new_tile_variant.isReference()), bool)
        self.assertFalse(new_tile_variant.isReference())
        
        tile_variant_int = int('a1001004001', 16)
        new_tile_variant = TileVariant(tile_variant_name=tile_variant_int,tile=new_tile, variant_value=1,
                                       length=250, md5sum="05fee", sequence="TO BIG TO STORE", num_positions_spanned=1)
        self.assertFalse(new_tile_variant.isReference())

        tile_variant_int = int('a1001004000', 16)
        new_tile_variant = TileVariant(tile_variant_name=tile_variant_int,tile=new_tile, variant_value=0,
                                       length=250, md5sum="05fee", sequence="TO BIG TO STORE", num_positions_spanned=1)
        self.assertTrue(new_tile_variant.isReference())

################################## TEST generate_statistics ###################################
#####################           TODO: multiple chromosomes!          ###############
class TestGenerateStatistics(TestCase):
    def setUp(self):
        make_ridiculously_long_gene()
        super(TestGenerateStatistics, self).setUp()

    def test_generate_stats_initialize(self):
        """
        The following structure:
            i,  min,     avg,  max
        Path 0:
            0,  448,  448.67,  450 {'vars':3, 'lengths':[448,448,450]}, #1
            1,  301,  301.00,  301 {'vars':2, 'lengths':[301,301]}, #2
            2,  200,  257.67,  300 {'vars':3, 'lengths':[273,200,300]}, #3
            3,  149,  149.00,  149 {'vars':1, 'lengths':[149]}, #4
            4,  425,  425.00,  425 {'vars':1, 'lengths':[425]}, #5
        Path 1:
            0,  500,  549.75,  600 {'vars':4, 'lengths':[549,500,600,550]}, #6
            1,  198,  199.00,  200 {'vars':4, 'lengths':[199,198,200,199]}, #7
            2,  249,  249.00,  249 {'vars':2, 'lengths':[249,249]}, #8
            3,  199,  199.00,  199 {'vars':1, 'lengths':[199]}, #9
            4, 1200, 1200.00, 1200 {'vars':1, 'lengths':[1200]}, #10
            5,  264,  264.50,  265 {'vars':2, 'lengths':[264,265]}, #11
            6,  249,  250.50,  252 {'vars':6, 'lengths':[251,250,250,251,252,249]}, #12
            7,  275,  275.50,  276 {'vars':2, 'lengths':[275,276]}, #13
        Path 2:
            0,  277,  277.00,  277 {'vars':2, 'lengths':[277,277]}, #14
            1,  267,  267.00,  267 {'vars':1, 'lengths':[267]}, #15
            2,  258,  258.00,  258 {'vars':1, 'lengths':[258]}, #16
            3,  248,  248.00,  248 {'vars':3, 'lengths':[248,248,248]}, #17
            4,  250,  250.00,  250 {'vars':1, 'lengths':[250]}, #18
        test_generate_stats has the following structure:
        Chr 1:
        Path 0: Position 0: Variant 0 (length 250)
                            Variant 1 (length 252)
                            Variant 2 (length 250)
                Position 1: Variant 0 (length 248)
                            Variant 1 (length 248)
                Position 2: Variant 0 (length 200)
                            Variant 1 (length 250)
                            Variant 2 (length 300)
                Position 3: Variant 0 (length 250)
                Position 4: Variant 0 (length 199)
        Path 1: Position 0: Variant 0 (length 248)
                            Variant 1 (length 248)
                            Variant 2 (length 248)
                            Variant 3 (length 248)
                            Variant 4 (length 248)

        Chr 2:
        Path 63: Position 0: Variant 0 (length 1000)
                             Variant 1 (length 1100)
                             Variant 2 (length 1050)
                             Variant 3 (length 1040)
                 Position 1: Variant 0 (length 200)
                             Variant 1 (length 250)
        """
        gen_stats.initialize(silent=True)
        self.assertEqual(GenomeStatistic.objects.count(), 27+Tile.CHR_PATH_LENGTHS[-1])
        check_vals = [{'num_pos':8, 'num_tiles':21, 'avg_var':2.625, 'max_var':5, 'min_len':199,
                       'avg_len_low':396.523, 'avg_len_hi':396.524, 'max_len':1100},
                      {'num_pos':6, 'num_tiles':15, 'avg_var':2.5, 'max_var':5, 'min_len':199,
                       'avg_len_low':245.800, 'avg_len_hi':245.800, 'max_len':300},
                      {'num_pos':2, 'num_tiles':6, 'avg_var':3, 'max_var':4, 'min_len':200,
                       'avg_len_low':773.333, 'avg_len_hi':773.334, 'max_len':1100}]
        
        for i in range(27):
            genome_piece = GenomeStatistic.objects.filter(statistics_type=i).all()
            self.assertEqual(len(genome_piece), 1)
            genome_piece = genome_piece.first()
            if i < 3:
                self.assertEqual(genome_piece.position_num, check_vals[i]['num_pos'])
                self.assertEqual(genome_piece.tile_num, check_vals[i]['num_tiles'])
                self.assertEqual(float(genome_piece.avg_variant_val), check_vals[i]['avg_var'])
                self.assertEqual(genome_piece.max_variant_val, check_vals[i]['max_var'])
                self.assertEqual(genome_piece.min_length, check_vals[i]['min_len'])
                self.assertGreaterEqual(float(genome_piece.avg_length), check_vals[i]['avg_len_low'])
                self.assertLessEqual(float(genome_piece.avg_length), check_vals[i]['avg_len_hi'])
                self.assertEqual(genome_piece.max_length, check_vals[i]['max_len'])
            else:
                self.assertEqual(genome_piece.position_num, 0)
                self.assertEqual(genome_piece.tile_num, 0)
                self.assertIsNone(genome_piece.avg_variant_val)
                self.assertIsNone(genome_piece.max_variant_val)
                self.assertIsNone(genome_piece.min_length)
                self.assertIsNone(genome_piece.avg_length)
                self.assertIsNone(genome_piece.max_length)
            self.assertIsNone(genome_piece.avg_annotations_per_position)
            self.assertIsNone(genome_piece.max_annotations_per_position)
            self.assertIsNone(genome_piece.avg_annotations_per_tile)
            self.assertIsNone(genome_piece.max_annotations_per_tile)
        tile_int, foo = fns.get_min_position_and_tile_variant_from_chromosome_int(2)
        path, version, step = basic_fns.get_position_ints_from_position_int(tile_int)
        check_vals = {0:{'num_pos':5, 'num_tiles':10, 'avg_var':2, 'max_var':3, 'min_len':199,
                         'avg_len_low':244.700, 'avg_len_hi':244.700, 'max_len':300},
                      1:{'num_pos':1, 'num_tiles':5, 'avg_var':5, 'max_var':5, 'min_len':248,
                         'avg_len_low':248.000, 'avg_len_hi':248.000, 'max_len':248},
                      path:{'num_pos':2, 'num_tiles':6, 'avg_var':3, 'max_var':4, 'min_len':200,
                            'avg_len_low':773.333, 'avg_len_hi':773.334, 'max_len':1100}}
        for i in range(Tile.CHR_PATH_LENGTHS[-1]):
            genome_piece = GenomeStatistic.objects.filter(statistics_type=27).filter(path_name=i).all()
            self.assertEqual(len(genome_piece), 1)
            genome_piece = genome_piece.first()
            if i in check_vals:
                self.assertEqual(genome_piece.position_num, check_vals[i]['num_pos'])
                self.assertEqual(genome_piece.tile_num, check_vals[i]['num_tiles'])
                self.assertEqual(float(genome_piece.avg_variant_val), check_vals[i]['avg_var'])
                self.assertEqual(genome_piece.max_variant_val, check_vals[i]['max_var'])
                self.assertEqual(genome_piece.min_length, check_vals[i]['min_len'])
                self.assertGreaterEqual(float(genome_piece.avg_length), check_vals[i]['avg_len_low'])
                self.assertLessEqual(float(genome_piece.avg_length), check_vals[i]['avg_len_hi'])
                self.assertEqual(genome_piece.max_length, check_vals[i]['max_len'])
            else:
                self.assertEqual(genome_piece.position_num, 0)
                self.assertEqual(genome_piece.tile_num, 0)
                self.assertIsNone(genome_piece.avg_variant_val)
                self.assertIsNone(genome_piece.max_variant_val)
                self.assertIsNone(genome_piece.min_length)
                self.assertIsNone(genome_piece.avg_length)
                self.assertIsNone(genome_piece.max_length)
            self.assertIsNone(genome_piece.avg_annotations_per_position)
            self.assertIsNone(genome_piece.max_annotations_per_position)
            self.assertIsNone(genome_piece.avg_annotations_per_tile)
            self.assertIsNone(genome_piece.max_annotations_per_tile)
    def test_initialize_failure(self):
        gen_stats.initialize(silent=True)
        self.assertRaises(AssertionError, gen_stats.initialize)
    def test_update_on_same_library(self):
        gen_stats.initialize(silent=True)
        gen_stats.update(silent=True)
        check_vals = [{'num_pos':8, 'num_tiles':21, 'avg_var':2.625, 'max_var':5, 'min_len':199,
                       'avg_len_low':396.523, 'avg_len_hi':396.524, 'max_len':1100},
                      {'num_pos':6, 'num_tiles':15, 'avg_var':2.5, 'max_var':5, 'min_len':199,
                       'avg_len_low':245.800, 'avg_len_hi':245.800, 'max_len':300},
                      {'num_pos':2, 'num_tiles':6, 'avg_var':3, 'max_var':4, 'min_len':200,
                       'avg_len_low':773.333, 'avg_len_hi':773.334, 'max_len':1100}]
        
        for i in range(27):
            genome_piece = GenomeStatistic.objects.filter(statistics_type=i).all()
            self.assertEqual(len(genome_piece), 1)
            genome_piece = genome_piece.first()
            if i < 3:
                self.assertEqual(genome_piece.position_num, check_vals[i]['num_pos'])
                self.assertEqual(genome_piece.tile_num, check_vals[i]['num_tiles'])
                self.assertEqual(float(genome_piece.avg_variant_val), check_vals[i]['avg_var'])
                self.assertEqual(genome_piece.max_variant_val, check_vals[i]['max_var'])
                self.assertEqual(genome_piece.min_length, check_vals[i]['min_len'])
                self.assertGreaterEqual(float(genome_piece.avg_length), check_vals[i]['avg_len_low'])
                self.assertLessEqual(float(genome_piece.avg_length), check_vals[i]['avg_len_hi'])
                self.assertEqual(genome_piece.max_length, check_vals[i]['max_len'])
            else:
                self.assertEqual(genome_piece.position_num, 0)
                self.assertEqual(genome_piece.tile_num, 0)
                self.assertIsNone(genome_piece.avg_variant_val)
                self.assertIsNone(genome_piece.max_variant_val)
                self.assertIsNone(genome_piece.min_length)
                self.assertIsNone(genome_piece.avg_length)
                self.assertIsNone(genome_piece.max_length)
            self.assertIsNone(genome_piece.avg_annotations_per_position)
            self.assertIsNone(genome_piece.max_annotations_per_position)
            self.assertIsNone(genome_piece.avg_annotations_per_tile)
            self.assertIsNone(genome_piece.max_annotations_per_tile)
        tile_int, foo = fns.get_min_position_and_tile_variant_from_chromosome_int(2)
        path, version, step = basic_fns.get_position_ints_from_position_int(tile_int)
        check_vals = {0:{'num_pos':5, 'num_tiles':10, 'avg_var':2, 'max_var':3, 'min_len':199,
                         'avg_len_low':244.700, 'avg_len_hi':244.700, 'max_len':300},
                      1:{'num_pos':1, 'num_tiles':5, 'avg_var':5, 'max_var':5, 'min_len':248,
                         'avg_len_low':248.000, 'avg_len_hi':248.000, 'max_len':248},
                      path:{'num_pos':2, 'num_tiles':6, 'avg_var':3, 'max_var':4, 'min_len':200,
                            'avg_len_low':773.333, 'avg_len_hi':773.334, 'max_len':1100}}
        for i in range(Tile.CHR_PATH_LENGTHS[-1]):
            genome_piece = GenomeStatistic.objects.filter(statistics_type=27).filter(path_name=i).all()
            self.assertEqual(len(genome_piece), 1)
            genome_piece = genome_piece.first()
            if i in check_vals:
                self.assertEqual(genome_piece.position_num, check_vals[i]['num_pos'])
                self.assertEqual(genome_piece.tile_num, check_vals[i]['num_tiles'])
                self.assertEqual(float(genome_piece.avg_variant_val), check_vals[i]['avg_var'])
                self.assertEqual(genome_piece.max_variant_val, check_vals[i]['max_var'])
                self.assertEqual(genome_piece.min_length, check_vals[i]['min_len'])
                self.assertGreaterEqual(float(genome_piece.avg_length), check_vals[i]['avg_len_low'])
                self.assertLessEqual(float(genome_piece.avg_length), check_vals[i]['avg_len_hi'])
                self.assertEqual(genome_piece.max_length, check_vals[i]['max_len'])
            else:
                self.assertEqual(genome_piece.position_num, 0)
                self.assertEqual(genome_piece.tile_num, 0)
                self.assertIsNone(genome_piece.avg_variant_val)
                self.assertIsNone(genome_piece.max_variant_val)
                self.assertIsNone(genome_piece.min_length)
                self.assertIsNone(genome_piece.avg_length)
                self.assertIsNone(genome_piece.max_length)
            self.assertIsNone(genome_piece.avg_annotations_per_position)
            self.assertIsNone(genome_piece.max_annotations_per_position)
            self.assertIsNone(genome_piece.avg_annotations_per_tile)
            self.assertIsNone(genome_piece.max_annotations_per_tile)
    def test_update_on_updated_library(self):
        """
        Updated structure is (additions shown with asterisk):

        Chr 1:
        Path 0: Position 0: Variant 0 (length 250)
                            Variant 1 (length 252)
                            Variant 2 (length 250)
                Position 1: Variant 0 (length 248)
                            Variant 1 (length 248)
                Position 2: Variant 0 (length 200)
                            Variant 1 (length 250)
                            Variant 2 (length 300)
                Position 3: Variant 0 (length 250)
                Position 4: Variant 0 (length 199)
                            Variant 1 (length 500)*
        Path 1: Position 0: Variant 0 (length 248)
                            Variant 1 (length 248)
                            Variant 2 (length 248)
                            Variant 3 (length 248)
                            Variant 4 (length 248)
                Position 1: Variant 0 (length 1200)*

        Chr 2:
        Path 63: Position 0: Variant 0 (length 1000)
                             Variant 1 (length 1100)
                             Variant 2 (length 1050)
                             Variant 3 (length 1040)
                 Position 1: Variant 0 (length 200)
                             Variant 1 (length 250)

        Chr 3:
        1st Path: Position 0: Variant 0 (length 250)*
                              Variant 1 (length 300)*
                              Variant 2 (length 300)*
                              Variant 3 (length 310)*
                              Variant 4 (length 260)*
                              Variant 5 (length 275)*
                  Position 1: Variant 0 (length 150)*
        """
        gen_stats.initialize(silent=True)
        #initialization#
        pos, tile_variant = fns.get_min_position_and_tile_variant_from_chromosome_int(3)
        tile0 = Tile(tilename=pos, start_tag="ACGT", end_tag="CCCG")
        lengths = [250,300,300,310,260,275]
        for i in range(6):
            t = TileVariant(tile_variant_name=tile_variant+i,tile=tile0, variant_value=i,
                            length=lengths[i], md5sum="05fee", sequence="TO BIG TO STORE", num_positions_spanned=1)
            t.save()
        tile0.save()
        
        tile1 = Tile(tilename=pos+1, start_tag="AAAAAA", end_tag="AGGGGGG")
        tile_variant_int = basic_fns.convert_position_int_to_tile_variant_int(pos+1)
        t = TileVariant(tile_variant_name=tile_variant_int,tile=tile1, variant_value=0,
                        length=150, md5sum="05fee", sequence="TO BIG TO STORE", num_positions_spanned=1)
        t.save()
        tile1.save()

        pos, tile_variant = fns.get_min_position_and_tile_variant_from_path_int(1)
        tile_variant_int = basic_fns.convert_position_int_to_tile_variant_int(pos+1)
        tile2 = Tile(tilename=pos+1, start_tag="AAAAAA", end_tag="AGGGGGG")
        t = TileVariant(tile_variant_name=tile_variant_int,tile=tile2, variant_value=0,
                        length=1200, md5sum="05fee", sequence="TO BIG TO STORE", num_positions_spanned=1)
        t.save()
        tile2.save()
        
        tile3 = Tile.objects.get(pk=3)
        tile_hex = string.join(basic_fns.convert_position_int_to_position_hex_str(3), "")
        tile_hex += hex(1).lstrip('0x').zfill(3)
        tile_var_int = int(tile_hex, 16)
        t = TileVariant(tile_variant_name=tile_var_int,tile=tile3, variant_value=1,
                        length=500, md5sum="05fee", sequence="TO BIG TO STORE", num_positions_spanned=1)
        t.save()
        tile3.save()
        
        #end of initialization#
        gen_stats.update(silent=True)
        check_vals = [{'num_pos':11, 'num_tiles':30, 'avg_var':2.727, 'max_var':6, 'min_len':150,
                       'avg_len_low':395.733, 'avg_len_hi':395.734, 'max_len':1200},
                      {'num_pos':7, 'num_tiles':17, 'avg_var':2.429, 'max_var':5, 'min_len':199,
                       'avg_len_low':316.882, 'avg_len_hi':316.883, 'max_len':1200},
                      {'num_pos':2, 'num_tiles':6, 'avg_var':3, 'max_var':4, 'min_len':200,
                       'avg_len_low':773.333, 'avg_len_hi':773.334, 'max_len':1100},
                      {'num_pos':2, 'num_tiles':7, 'avg_var':3.5, 'max_var':6, 'min_len':150,
                       'avg_len_low':263.571, 'avg_len_hi':263.572, 'max_len':310}]
        
        for i in range(27):
            genome_piece = GenomeStatistic.objects.filter(statistics_type=i).all()
            self.assertEqual(len(genome_piece), 1)
            genome_piece = genome_piece.first()
            if i < 4:
                self.assertEqual(genome_piece.position_num, check_vals[i]['num_pos'])
                self.assertEqual(genome_piece.tile_num, check_vals[i]['num_tiles'])
                self.assertEqual(float(genome_piece.avg_variant_val), check_vals[i]['avg_var'])
                self.assertEqual(genome_piece.max_variant_val, check_vals[i]['max_var'])
                self.assertEqual(genome_piece.min_length, check_vals[i]['min_len'])
                self.assertGreaterEqual(float(genome_piece.avg_length), check_vals[i]['avg_len_low'])
                self.assertLessEqual(float(genome_piece.avg_length), check_vals[i]['avg_len_hi'])
                self.assertEqual(genome_piece.max_length, check_vals[i]['max_len'])
            else:
                self.assertEqual(genome_piece.position_num, 0)
                self.assertEqual(genome_piece.tile_num, 0)
                self.assertIsNone(genome_piece.avg_variant_val)
                self.assertIsNone(genome_piece.max_variant_val)
                self.assertIsNone(genome_piece.min_length)
                self.assertIsNone(genome_piece.avg_length)
                self.assertIsNone(genome_piece.max_length)
            self.assertIsNone(genome_piece.avg_annotations_per_position)
            self.assertIsNone(genome_piece.max_annotations_per_position)
            self.assertIsNone(genome_piece.avg_annotations_per_tile)
            self.assertIsNone(genome_piece.max_annotations_per_tile)
        tile_int, foo = fns.get_min_position_and_tile_variant_from_chromosome_int(2)
        path_on_2, version, step = basic_fns.get_position_ints_from_position_int(tile_int)
        tile_int, foo = fns.get_min_position_and_tile_variant_from_chromosome_int(3)
        path_on_3, version, step = basic_fns.get_position_ints_from_position_int(tile_int)
        check_vals = {0:{'num_pos':5, 'num_tiles':11, 'avg_var':2.2, 'max_var':3, 'min_len':199,
                         'avg_len_low':267.909, 'avg_len_hi':267.910, 'max_len':500},
                      1:{'num_pos':2, 'num_tiles':6, 'avg_var':3, 'max_var':5, 'min_len':248,
                         'avg_len_low':406.666, 'avg_len_hi':406.667, 'max_len':1200},
                      path_on_2:{'num_pos':2, 'num_tiles':6, 'avg_var':3, 'max_var':4, 'min_len':200,
                                 'avg_len_low':773.333, 'avg_len_hi':773.334, 'max_len':1100},
                      path_on_3:{'num_pos':2, 'num_tiles':7, 'avg_var':3.5, 'max_var':6, 'min_len':150,
                                 'avg_len_low':263.571, 'avg_len_hi':263.572, 'max_len':310},
                     }
        for i in range(Tile.CHR_PATH_LENGTHS[-1]):
            genome_piece = GenomeStatistic.objects.filter(statistics_type=27).filter(path_name=i).all()
            self.assertEqual(len(genome_piece), 1)
            genome_piece = genome_piece.first()
            if i in check_vals:
                self.assertEqual(genome_piece.position_num, check_vals[i]['num_pos'])
                self.assertEqual(genome_piece.tile_num, check_vals[i]['num_tiles'])
                self.assertEqual(float(genome_piece.avg_variant_val), check_vals[i]['avg_var'])
                self.assertEqual(genome_piece.max_variant_val, check_vals[i]['max_var'])
                self.assertEqual(genome_piece.min_length, check_vals[i]['min_len'])
                self.assertGreaterEqual(float(genome_piece.avg_length), check_vals[i]['avg_len_low'])
                self.assertLessEqual(float(genome_piece.avg_length), check_vals[i]['avg_len_hi'])
                self.assertEqual(genome_piece.max_length, check_vals[i]['max_len'])
            else:
                self.assertEqual(genome_piece.position_num, 0)
                self.assertEqual(genome_piece.tile_num, 0)
                self.assertIsNone(genome_piece.avg_variant_val)
                self.assertIsNone(genome_piece.max_variant_val)
                self.assertIsNone(genome_piece.min_length)
                self.assertIsNone(genome_piece.avg_length)
                self.assertIsNone(genome_piece.max_length)
            self.assertIsNone(genome_piece.avg_annotations_per_position)
            self.assertIsNone(genome_piece.max_annotations_per_position)
            self.assertIsNone(genome_piece.avg_annotations_per_tile)
            self.assertIsNone(genome_piece.max_annotations_per_tile)
    def test_update_failure(self):
        self.assertRaises(BaseException, gen_stats.update, silent=True)

    
################################## TEST overall_statistics_views ###################################    
##class TestViewOverallStatistics(TestCase):
##    def test_overall_statistics_empty_view(self):
##        response = self.client.get(reverse('tile_library:statistics'))
##        self.assertEqual(response.status_code, 200)
##        self.assertQuerysetEqual(response.context['stats'], [])
##        self.assertContains(response, "No statistics for this Tile Library are available.")
##        
##    def test_overall_statistics_view(self):
##        gen_stats.initialize(silent=True)
##        response = self.client.get(reverse('tile_library:statistics'))
##        self.assertEqual(response.status_code, 200)
##        stat_query_set, names = zip(*response.context['stats'])
##        self.assertEqual(len(names), 27)
##        self.assertQuerysetEqual(stat_query_set,range(27), transform=lambda stat_set: stat_set.statistics_type)
##
##class TestViewChrStatistics(TestCase):
##    def test_wrong_numbers_return_404(self):
##        response = self.client.get(reverse('tile_library:chr_statistics', args=(0,)))
##        self.assertEqual(response.status_code, 404)
##        response = self.client.get(reverse('tile_library:chr_statistics', args=(27,)))
##        self.assertEqual(response.status_code, 404)
##
##    def test_chr_statistics_empty_view(self):
##        #highly doubt this will happen, but completeness...
##        response = self.client.get(reverse('tile_library:chr_statistics', args=(1,)))
##        self.assertEqual(response.status_code, 200)
##        self.assertFalse('chromosome_stats' in response.context)
##        self.assertContains(response, "No statistics for this Tile Library are available.")
##        
##    def test_first_chr_statistics_view(self):
##        gen_stats.initialize(silent=True)
##        response = self.client.get(reverse('tile_library:chr_statistics', args=(1,)))
##        self.assertEqual(response.status_code, 200)
##        self.assertTrue('paths' in response.context)
##        self.assertContains(response, 'Path 0')
##        path_ints, path_hexs, path_names, paths = zip(*response.context['paths'])
##        
##        self.assertEqual(len(paths), Tile.CHR_PATH_LENGTHS[1])
##        self.assertQuerysetEqual(paths,path_ints, transform=lambda path_stat: path_stat.path_name)
##        
##    def test_mitochondrial_chr_statistics_view(self):
##        gen_stats.initialize(silent=True)
##        response = self.client.get(reverse('tile_library:chr_statistics', args=(25,)))
##        self.assertEqual(response.status_code, 200)
##        self.assertTrue('paths' in response.context)
##        path_ints, path_hexs, path_names, paths = zip(*response.context['paths'])
##        self.assertNotContains(response, 'Path 0')
##        self.assertEqual(len(paths), Tile.CHR_PATH_LENGTHS[25]-Tile.CHR_PATH_LENGTHS[24])
##        self.assertQuerysetEqual(paths,path_ints, transform=lambda path_stat: path_stat.path_name)
##        
##    def test_other_chr_statistics_view(self):
##        gen_stats.initialize(silent=True)
##        response = self.client.get(reverse('tile_library:chr_statistics', args=(26,)))
##        self.assertEqual(response.status_code, 200)
##        self.assertTrue('paths' in response.context)
##        self.assertNotContains(response, 'Path 0')
##        try:
##            path_ints, path_hexs, path_names, paths = zip(*response.context['paths'])
##            self.assertQuerysetEqual(paths,path_ints, transform=lambda path_stat: path_stat.path_name)
##        except ValueError:
##            paths = response.context['paths']
##            self.assertQuerysetEqual(paths,[])
##        self.assertEqual(len(paths), Tile.CHR_PATH_LENGTHS[26]-Tile.CHR_PATH_LENGTHS[25])
##
########################## TEST views.get_positions (used by path/gene views) ################## 
##class TestGetPositionsFunctions(TestCase):
##    fixtures = ['test_view_paths.json']
##    """
##        Currently, this test suite assumes that views.get_positions will only be called with
##            correct inputs...
##        test_view_paths has the following structure:
##            i,  min,     avg,  max
##            0,  250,  250.67,  252 {'vars':3, 'lengths':[250,252,250]}, #1
##            1,  248,  248.00,  248 {'vars':2, 'lengths':[248,248]}, #2
##            2,  200,  250.00,  300 {'vars':3, 'lengths':[200,250,300]}, #3
##            3,  250,  250.00,  250 {'vars':1, 'lengths':[250]}, #4
##            4,  199,  199.00,  199 {'vars':1, 'lengths':[199]}, #5
##            5,  150,  205.00,  250 {'vars':4, 'lengths':[150,250,200,220]}, #6
##            6,  250,  250.25,  251 {'vars':4, 'lengths':[250,250,250,251]}, #7
##            7, 1200, 1200.00, 1200 {'vars':1, 'lengths':[1200]}, #8
##            8,  300,  300.33,  301 {'vars':3, 'lengths':[300,300,301]}, #9
##            9,  264,  264.50,  265 {'vars':2, 'lengths':[264,265]}, #10
##           10,  249,  250.50,  252 {'vars':6, 'lengths':[251,250,250,251,252,249]}, #11
##           11,  275,  275.50,  276 {'vars':2, 'lengths':[275,276]}, #12
##           12,  277,  277.00,  277 {'vars':2, 'lengths':[277,277]}, #13
##           13,  267,  267.00,  267 {'vars':1, 'lengths':[267]}, #14
##           14,  258,  258.00,  258 {'vars':1, 'lengths':[258]}, #15
##           15,  248,  248.00,  248 {'vars':3, 'lengths':[248,248,248]}, #16
##           16,  250,  250.00,  250 {'vars':1, 'lengths':[250]}, #17
##        """
##    def test_get_positions(self):
##        positions = views.get_positions(0, 0)
##        self.assertEqual(len(positions), 1)
##        expected = {'num_var':3, 'min_len': 250, 'avg_len':250.66666666666666, 'max_len':252}
##        for pos in positions:
##            self.assertEqual(pos.num_var, expected['num_var'])
##            self.assertEqual(pos.min_len, expected['min_len'])
##            self.assertAlmostEqual(pos.avg_len, expected['avg_len'])
##            self.assertEqual(pos.max_len, expected['max_len'])
##
##        positions = views.get_positions(0, 1)
##        self.assertEqual(len(positions), 2)
##        expected = [{'num_var':3, 'min_len': 250, 'avg_len':250.66666666666666, 'max_len':252},
##                    {'num_var':2, 'min_len': 248, 'avg_len':248, 'max_len':248}]
##        for i, pos in enumerate(positions):
##            self.assertEqual(pos.num_var, expected[i]['num_var'])
##            self.assertEqual(pos.min_len, expected[i]['min_len'])
##            self.assertAlmostEqual(pos.avg_len, expected[i]['avg_len'])
##            self.assertEqual(pos.max_len, expected[i]['max_len'])
##
##        positions = views.get_positions(1, 2)
##        self.assertEqual(len(positions), 2)
##        expected = [{'num_var':2, 'min_len': 248, 'avg_len':248, 'max_len':248},
##                    {'num_var':3, 'min_len': 200, 'avg_len':250, 'max_len':300},]
##        for i, pos in enumerate(positions):
##            self.assertEqual(pos.num_var, expected[i]['num_var'])
##            self.assertEqual(pos.min_len, expected[i]['min_len'])
##            self.assertAlmostEqual(pos.avg_len, expected[i]['avg_len'])
##            self.assertEqual(pos.max_len, expected[i]['max_len'])
##    #def test_get_positions_invalid_inputs(self):
##            
##    def test_pagination_size(self):
##        positions = views.get_positions(0, 17)
##        partial_positions = views.get_partial_positions(positions, "", 5, 1)
##        self.assertEqual(len(partial_positions), 5)
##        partial_positions = views.get_partial_positions(positions, "", 10, 1)
##        self.assertEqual(len(partial_positions), 10)
##        partial_positions = views.get_partial_positions(positions, "", 15, 1)
##        self.assertEqual(len(partial_positions), 15)
##        partial_positions = views.get_partial_positions(positions, "", 20, 1)
##        self.assertEqual(len(partial_positions), 17)
##    def test_pagination(self):
##        positions = views.get_positions(0, 17)
##        partial_positions = views.get_partial_positions(positions, "", 5, 1)
##        self.assertEqual(len(partial_positions), len(positions[:5]))
##        for pos1, pos2 in zip(partial_positions, positions[:5]):
##            self.assertEqual(pos1, pos2)
##        
##        partial_positions = views.get_partial_positions(positions, "", 5, "")
##        self.assertEqual(len(partial_positions), len(positions[:5]))
##        for pos1, pos2 in zip(partial_positions, positions[:5]):
##            self.assertEqual(pos1, pos2)
##        
##        partial_positions = views.get_partial_positions(positions, "", 5, 2)
##        self.assertEqual(len(partial_positions), len(positions[5:10]))
##        for pos1, pos2 in zip(partial_positions, positions[5:10]):
##            self.assertEqual(pos1, pos2)
##
##        partial_positions = views.get_partial_positions(positions, "", 5, 3)
##        self.assertEqual(len(partial_positions), len(positions[10:15]))
##        for pos1, pos2 in zip(partial_positions, positions[10:15]):
##            self.assertEqual(pos1, pos2)
##        
##        partial_positions = views.get_partial_positions(positions, "", 5, 4)
##        self.assertEqual(len(partial_positions), len(positions[15:]))
##        for pos1, pos2 in zip(partial_positions, positions[15:]):
##            self.assertEqual(pos1, pos2)
##
##        overreaching = views.get_partial_positions(positions, "", 5, 5)
##        self.assertEqual(len(partial_positions), len(overreaching))
##        for pos1, pos2 in zip(partial_positions, overreaching):
##            self.assertEqual(pos1, pos2)
##
##        underreaching = views.get_partial_positions(positions, "", 5, -1)
##        self.assertEqual(len(partial_positions), len(underreaching))
##        for pos1, pos2 in zip(partial_positions, underreaching):
##            self.assertEqual(pos1, pos2)
##        
##        partial_positions = views.get_partial_positions(positions, "", 10, 1)
##        self.assertEqual(len(partial_positions), len(positions[:10]))
##        for pos1, pos2 in zip(partial_positions, positions[:10]):
##            self.assertEqual(pos1, pos2)
##            
##        partial_positions = views.get_partial_positions(positions, "", 15, 1)
##        self.assertEqual(len(partial_positions), len(positions[:15]))
##        for pos1, pos2 in zip(partial_positions, positions[:15]):
##            self.assertEqual(pos1, pos2)
##
##        partial_positions = views.get_partial_positions(positions, "", 20, 1)
##        self.assertEqual(len(partial_positions), len(positions))
##        for pos1, pos2 in zip(partial_positions, positions):
##            self.assertEqual(pos1, pos2)
##    def test_tile_ordering(self):
##        positions = views.get_positions(0, 17)
##        pos_reversed = list(positions)
##        pos_reversed.reverse()
##        
##        partial_positions = views.get_partial_positions(positions, "desc_tile", 5, 1)
##        for i, pos in enumerate(partial_positions):
##            self.assertEqual(pos, pos_reversed[i])
##            
##    def test_var_ordering(self):
##        positions = views.get_positions(0, 17)
##        partial_positions = views.get_partial_positions(positions, "desc_var", 5, 1)
##        expected = [[positions[10]],
##                    [positions[5], positions[6]],
##                    [positions[5], positions[6]],
##                    [positions[0], positions[2], positions[8], positions[15]],
##                    [positions[0], positions[2], positions[8], positions[15]]]
##        for i, pos in enumerate(partial_positions):
##            self.assertTrue(pos in expected[i])
##
##        partial_positions = views.get_partial_positions(positions, "asc_var", 5, 1)
##        expected = [positions[3], positions[4], positions[7], positions[13], positions[14], positions[16]]
##        for pos in partial_positions:
##            self.assertTrue(pos in expected)
##    def test_length_ordering(self):
##        positions = views.get_positions(0, 17)
##        partial_positions = views.get_partial_positions(positions, "asc_min_len", 5, 1)
##        expected = [[positions[5]],
##                    [positions[4]],
##                    [positions[2]],
##                    [positions[1], positions[15]],
##                    [positions[1], positions[15]]]
##        for i, pos in enumerate(partial_positions):
##            self.assertTrue(pos in expected[i])
##            
##        partial_positions = views.get_partial_positions(positions, "desc_min_len", 5, 1)
##        expected = [positions[7],
##                    positions[8],
##                    positions[12],
##                    positions[11],
##                    positions[13]]
##        for i, pos in enumerate(partial_positions):
##            self.assertEqual(pos, expected[i])
##
##        partial_positions = views.get_partial_positions(positions, "asc_avg_len", 5, 1)
##        expected = [[positions[4]],
##                    [positions[5]],
##                    [positions[1], positions[15]],
##                    [positions[1], positions[15]],
##                    [positions[2], positions[3], positions[16]]]
##        for i, pos in enumerate(partial_positions):
##            self.assertTrue(pos in expected[i])
##            
##        partial_positions = views.get_partial_positions(positions, "desc_avg_len", 5, 1)
##        expected = [positions[7],
##                    positions[8],
##                    positions[12],
##                    positions[11],
##                    positions[13]]
##        for i, pos in enumerate(partial_positions):
##            self.assertEqual(pos, expected[i])
##
##        partial_positions = views.get_partial_positions(positions, "asc_max_len", 5, 1)
##        expected = [[positions[4]],
##                    [positions[1], positions[15]],
##                    [positions[1], positions[15]],
##                    [positions[3], positions[5], positions[16]],
##                    [positions[3], positions[5], positions[16]]]
##        for i, pos in enumerate(partial_positions):
##            self.assertTrue(pos in expected[i])
##            
##        partial_positions = views.get_partial_positions(positions, "desc_max_len", 5, 1)
##        expected = [positions[7],
##                    positions[8],
##                    positions[2],
##                    positions[12],
##                    positions[11]]
##        for i, pos in enumerate(partial_positions):
##            self.assertEqual(pos, expected[i])
##            
##    def test_tile_ordering_pages(self):
##        positions = views.get_positions(0, 17)
##        pos_reversed = list(positions)
##        pos_reversed.reverse()
##        
##        partial_positions = views.get_partial_positions(positions, "desc_tile", 5, 2)
##        for i, pos in enumerate(partial_positions):
##            self.assertEqual(pos, pos_reversed[i+5])
##
##        partial_positions = views.get_partial_positions(positions, "desc_tile", 5, 3)
##        for i, pos in enumerate(partial_positions):
##            self.assertEqual(pos, pos_reversed[i+10])
##            
##        partial_positions = views.get_partial_positions(positions, "desc_tile", 5, 4)
##        for i, pos in enumerate(partial_positions):
##            self.assertEqual(pos, pos_reversed[i+15])
##            
##    def test_var_ordering_pages(self):
##        positions = views.get_positions(0, 17)
##        partial_positions = views.get_partial_positions(positions, "desc_var", 5, 2)
##        expected = [[positions[0], positions[2], positions[8], positions[15]],
##                    [positions[0], positions[2], positions[8], positions[15]],
##                    [positions[1], positions[9], positions[11], positions[12]],
##                    [positions[1], positions[9], positions[11], positions[12]],
##                    [positions[1], positions[9], positions[11], positions[12]]]
##        for i, pos in enumerate(partial_positions):
##            self.assertTrue(pos in expected[i])
##
##        partial_positions = views.get_partial_positions(positions, "desc_var", 5, 3)
##        expected = [[positions[1], positions[9], positions[11], positions[12]],
##                    [positions[3], positions[4], positions[7], positions[13], positions[14], positions[16]],
##                    [positions[3], positions[4], positions[7], positions[13], positions[14], positions[16]],
##                    [positions[3], positions[4], positions[7], positions[13], positions[14], positions[16]],
##                    [positions[3], positions[4], positions[7], positions[13], positions[14], positions[16]]]
##        for i, pos in enumerate(partial_positions):
##            self.assertTrue(pos in expected[i])
##
##        partial_positions = views.get_partial_positions(positions, "desc_var", 5, 4)
##        expected = [positions[3], positions[4], positions[7], positions[13], positions[14], positions[16]]
##        for i, pos in enumerate(partial_positions):
##            self.assertTrue(pos in expected)
##
##        partial_positions = views.get_partial_positions(positions, "asc_var", 5, 2)
##        expected = [[positions[3], positions[4], positions[7], positions[13], positions[14], positions[16]],
##                    [positions[1], positions[9], positions[11], positions[12]],
##                    [positions[1], positions[9], positions[11], positions[12]],
##                    [positions[1], positions[9], positions[11], positions[12]],
##                    [positions[1], positions[9], positions[11], positions[12]]]
##        for i, pos in enumerate(partial_positions):
##            self.assertTrue(pos in expected[i])
##
##        partial_positions = views.get_partial_positions(positions, "asc_var", 5, 3)
##        expected = [[positions[0], positions[2], positions[8], positions[15]],
##                    [positions[0], positions[2], positions[8], positions[15]],
##                    [positions[0], positions[2], positions[8], positions[15]],
##                    [positions[0], positions[2], positions[8], positions[15]],
##                    [positions[5], positions[6]]]
##        for i, pos in enumerate(partial_positions):
##            self.assertTrue(pos in expected[i])
##
##        partial_positions = views.get_partial_positions(positions, "asc_var", 5, 4)
##        expected = [[positions[5], positions[6]],
##                    [positions[10]]]
##        for i, pos in enumerate(partial_positions):
##            self.assertTrue(pos in expected[i])
##    
#################################### TEST path_statistics_views ################################### 
##class TestViewPathStatistics(TestCase):
##    fixtures = ['test_view_paths.json']
##    """
##        test_view_paths has the following structure:
##            i,  min,     avg,  max
##            0,  250,  250.67,  252 {'vars':3, 'lengths':[250,252,250]}, #1
##            1,  248,  248.00,  248 {'vars':2, 'lengths':[248,248]}, #2
##            2,  200,  250.00,  300 {'vars':3, 'lengths':[200,250,300]}, #3
##            3,  250,  250.00,  250 {'vars':1, 'lengths':[250]}, #4
##            4,  199,  199.00,  199 {'vars':1, 'lengths':[199]}, #5
##            5,  150,  205.00,  250 {'vars':4, 'lengths':[150,250,200,220]}, #6
##            6,  250,  250.25,  251 {'vars':4, 'lengths':[250,250,250,251]}, #7
##            7, 1200, 1200.00, 1200 {'vars':1, 'lengths':[1200]}, #8
##            8,  300,  300.33,  301 {'vars':3, 'lengths':[300,300,301]}, #9
##            9,  264,  264.50,  265 {'vars':2, 'lengths':[264,265]}, #10
##           10,  249,  250.50,  252 {'vars':6, 'lengths':[251,250,250,251,252,249]}, #11
##           11,  275,  275.50,  276 {'vars':2, 'lengths':[275,276]}, #12
##           12,  277,  277.00,  277 {'vars':2, 'lengths':[277,277]}, #13
##           13,  267,  267.00,  267 {'vars':1, 'lengths':[267]}, #14
##           14,  258,  258.00,  258 {'vars':1, 'lengths':[258]}, #15
##           15,  248,  248.00,  248 {'vars':3, 'lengths':[248,248,248]}, #16
##           16,  250,  250.00,  250 {'vars':1, 'lengths':[250]}, #17
##        Most view tests will be on path 0 (the first path)
##        """
##    def test_wrong_numbers_return_404(self):
##        response = self.client.get(reverse('tile_library:path_statistics', args=(0,0)))
##        self.assertEqual(response.status_code, 404)
##        response = self.client.get(reverse('tile_library:path_statistics', args=(27,0)))
##        self.assertEqual(response.status_code, 404)
##        response = self.client.get(reverse('tile_library:path_statistics', args=(2, Tile.CHR_PATH_LENGTHS[1]-1)))
##        self.assertEqual(response.status_code, 404)
##        response = self.client.get(reverse('tile_library:path_statistics', args=(2, Tile.CHR_PATH_LENGTHS[2])))
##        self.assertEqual(response.status_code, 404)
##
##    def test_path_no_statistics_view(self):
##        #highly doubt this will happen, but completeness...
##        response = self.client.get(reverse('tile_library:path_statistics', args=(1,0)))
##        self.assertEqual(response.status_code, 200)
##        self.assertFalse('path' in response.context)
##        self.assertFalse('positions' in response.context)
##        self.assertContains(response, "No statistics for this Tile Library are available.")
##
##    def test_path_empty_tiles_view(self):
##        gen_stats.initialize(silent=True)
##        response = self.client.get(reverse('tile_library:path_statistics', args=(1,1)))
##        self.assertEqual(response.status_code, 200)
##        for page in response.context['positions']:
##            self.assertEqual(page, [])
##        self.assertContains(response, "No tiles are in this path.")
##    
##    def test_basic_statistics_view(self):
##        true_positions = views.get_positions(0, 17)
##        gen_stats.initialize(silent=True)
##        response = self.client.get(reverse('tile_library:path_statistics', args=(1,0)))
##        self.assertEqual(response.status_code, 200)
##        self.assertTrue('path' in response.context)
##        self.assertTrue('positions' in response.context)
##        self.assertEqual(response.context['chromosome_int'], 1)
##        self.assertEqual(response.context['chromosome'], 'chr1')
##        self.assertEqual(response.context['path_int'], 0)
##        self.assertEqual(response.context['path_hex'], '0')
##        self.assertEqual(response.context['path_cyto'], Tile.CYTOMAP[0])
##        path = response.context['path']
##        positions = response.context['positions']
##        
##        self.assertEqual(len(positions), 16)
##        for i, pos in enumerate(positions):
##            self.assertEqual(pos, true_positions[i])
##        self.assertEqual(path.statistics_type, 27)
##        self.assertEqual(path.path_name, 0)
##        self.assertEqual(path.position_num, 17)
##        self.assertEqual(path.tile_num, 40)
##        self.assertEqual(path.max_variant_val, 6)
##        self.assertEqual(path.min_length, 150)
##        self.assertEqual(path.max_length, 1200)
##
##    def test_first_page_statistics_view(self):
##        """ Test asking for the first page is the same as the default page """
##        gen_stats.initialize(silent=True)
##        response_1 = self.client.get(reverse('tile_library:path_statistics', args=(1,0))+'?page=1')
##        response_2 = self.client.get(reverse('tile_library:path_statistics', args=(1,0)))
##        for item in ['chromosome_int', 'chromosome', 'path_int', 'path_hex', 'path_cyto', 'path']:
##            self.assertEqual(response_1.context[item], response_2.context[item])
##        self.assertEqual(len(response_1.context['positions']), len(response_2.context['positions']))
##        for pos1, pos2 in zip(response_1.context['positions'], response_2.context['positions']):
##            self.assertEqual(pos1, pos2)
##
##    def test_second_page_statistics_view(self):
##        """ Test asking for the first page is the same as the default page """
##        true_positions = views.get_positions(0, 17)
##        gen_stats.initialize(silent=True)
##        response_1 = self.client.get(reverse('tile_library:path_statistics', args=(1,0))+'?page=2')
##        response_2 = self.client.get(reverse('tile_library:path_statistics', args=(1,0)))
##        for item in ['chromosome_int', 'chromosome', 'path_int', 'path_hex', 'path_cyto', 'path']:
##            self.assertEqual(response_1.context[item], response_2.context[item])
##        self.assertEqual(len(response_1.context['positions']), len(true_positions[16:]))
##        for pos1, pos2 in zip(response_1.context['positions'], true_positions[16:]):
##            self.assertEqual(pos1, pos2)
##
##    def test_pagination_alteration_statistics_view(self):
##        true_positions = views.get_positions(0, 17)
##        gen_stats.initialize(silent=True)
##        response_1 = self.client.get(reverse('tile_library:path_statistics', args=(1,0))+'?num=10')
##        self.assertEqual(len(response_1.context['positions']),10)
##        
##        response_2 = self.client.get(reverse('tile_library:path_statistics', args=(1,0)))
##        for item in ['chromosome_int', 'chromosome', 'path_int', 'path_hex', 'path_cyto', 'path']:
##            self.assertEqual(response_1.context[item], response_2.context[item])
##
##        self.assertNotEqual(len(response_1.context['positions']), len(response_2.context['positions']))
##        for pos1, pos2 in zip(response_1.context['positions'], response_2.context['positions']):
##            self.assertEqual(pos1, pos2)
##
##    def test_pagination_alteration_second_page_statistics_view(self):
##        true_positions = views.get_positions(0, 17)
##        gen_stats.initialize(silent=True)
##        response_1 = self.client.get(reverse('tile_library:path_statistics', args=(1,0))+'?num=10&page=2')
##        self.assertEqual(len(response_1.context['positions']),7)
##        
##        response_2 = self.client.get(reverse('tile_library:path_statistics', args=(1,0)))
##        for item in ['chromosome_int', 'chromosome', 'path_int', 'path_hex', 'path_cyto', 'path']:
##            self.assertEqual(response_1.context[item], response_2.context[item])
##
##        self.assertEqual(len(response_1.context['positions']), len(true_positions[10:]))
##        for pos1, pos2 in zip(response_1.context['positions'], true_positions[10:]):
##            self.assertEqual(pos1, pos2)
##
##    def test_ordering_statistics_view(self):
##        rev_positions = list(views.get_positions(0, 17))
##        rev_positions.reverse()
##        gen_stats.initialize(silent=True)
##        response_1 = self.client.get(reverse('tile_library:path_statistics', args=(1,0))+'?ordering=desc_tile')
##        self.assertEqual(len(response_1.context['positions']),16)
##        
##        response_2 = self.client.get(reverse('tile_library:path_statistics', args=(1,0)))
##        for item in ['chromosome_int', 'chromosome', 'path_int', 'path_hex', 'path_cyto', 'path']:
##            self.assertEqual(response_1.context[item], response_2.context[item])
##
##        self.assertEqual(len(response_1.context['positions']), len(rev_positions[:16]))
##        for pos1, pos2 in zip(response_1.context['positions'], rev_positions[:16]):
##            self.assertEqual(pos1, pos2)
##
##    def test_ordering_pagination_alteration_statistics_view(self):
##        rev_positions = list(views.get_positions(0, 17))
##        rev_positions.reverse()
##        gen_stats.initialize(silent=True)
##        response_1 = self.client.get(reverse('tile_library:path_statistics', args=(1,0))+'?ordering=desc_tile&num=10')
##        self.assertEqual(len(response_1.context['positions']),10)
##        
##        response_2 = self.client.get(reverse('tile_library:path_statistics', args=(1,0)))
##        for item in ['chromosome_int', 'chromosome', 'path_int', 'path_hex', 'path_cyto', 'path']:
##            self.assertEqual(response_1.context[item], response_2.context[item])
##
##        self.assertEqual(len(response_1.context['positions']), len(rev_positions[:10]))
##        for pos1, pos2 in zip(response_1.context['positions'], rev_positions[:10]):
##            self.assertEqual(pos1, pos2)
##
##    def test_ordering_second_page_statistics_view(self):
##        rev_positions = list(views.get_positions(0, 17))
##        rev_positions.reverse()
##        gen_stats.initialize(silent=True)
##        response_1 = self.client.get(reverse('tile_library:path_statistics', args=(1,0))+'?ordering=desc_tile&page=2')
##        self.assertEqual(len(response_1.context['positions']),1)
##        
##        response_2 = self.client.get(reverse('tile_library:path_statistics', args=(1,0)))
##        for item in ['chromosome_int', 'chromosome', 'path_int', 'path_hex', 'path_cyto', 'path']:
##            self.assertEqual(response_1.context[item], response_2.context[item])
##
##        self.assertEqual(len(response_1.context['positions']), len(rev_positions[16:]))
##        for pos1, pos2 in zip(response_1.context['positions'], rev_positions[16:]):
##            self.assertEqual(pos1, pos2)
##
##    def test_ordering_pagination_alteration_second_page_statistics_view(self):
##        rev_positions = list(views.get_positions(0, 17))
##        rev_positions.reverse()
##        gen_stats.initialize(silent=True)
##        response_1 = self.client.get(reverse('tile_library:path_statistics', args=(1,0))+'?ordering=desc_tile&num=10&page=2')
##        self.assertEqual(len(response_1.context['positions']),7)
##        
##        response_2 = self.client.get(reverse('tile_library:path_statistics', args=(1,0)))
##        for item in ['chromosome_int', 'chromosome', 'path_int', 'path_hex', 'path_cyto', 'path']:
##            self.assertEqual(response_1.context[item], response_2.context[item])
##
##        self.assertEqual(len(response_1.context['positions']), len(rev_positions[10:]))
##        for pos1, pos2 in zip(response_1.context['positions'], rev_positions[10:]):
##            self.assertEqual(pos1, pos2)
##
##    def test_template_tags_reference_length(self):
##        positions = views.get_positions(0, 17)
##        lengths = [250, 248, 200, 250, 199, 150, 250, 1200, 300, 264, 251, 275, 277, 267, 258, 248, 250]
##        for i, position in enumerate(positions):
##            self.assertEqual(stat_filters.get_reference_length(position), lengths[i])
##
##    def test_template_tags_url_replace_with_view(self):
##        positions = views.get_positions(0, 17)
##        response_1 = self.client.get(reverse('tile_library:path_statistics', args=(1,0))+'?ordering=desc_tile&num=10&page=2')
##        r = response_1.context['request'].GET
##        self.assertEqual(stat_filters.url_replace(r, 'page', 1), 'ordering=desc_tile&num=10&page=1')
##        self.assertEqual(stat_filters.url_replace(r, 'ordering', 'desc_var'), 'ordering=desc_var&num=10&page=2')
##        self.assertEqual(stat_filters.url_replace(r, 'num', 15), 'ordering=desc_tile&num=15&page=2')
##
##        response_1 = self.client.get(reverse('tile_library:path_statistics', args=(1,0)))
##        r = response_1.context['request'].GET
##        self.assertEqual(stat_filters.url_replace(r, 'page', 2), 'page=2')
##        self.assertEqual(stat_filters.url_replace(r, 'ordering', 'desc_var'), 'ordering=desc_var')
##        self.assertEqual(stat_filters.url_replace(r, 'num', 15), 'num=15')
##
##        response_1 = self.client.get(reverse('tile_library:path_statistics', args=(1,0))+'?ordering=desc_tile&num=10')
##        r = response_1.context['request'].GET
##        self.assertEqual(stat_filters.url_replace(r, 'page', 2), 'ordering=desc_tile&num=10&page=2')
##        self.assertEqual(stat_filters.url_replace(r, 'ordering', 'desc_var'), 'ordering=desc_var&num=10')
##        self.assertEqual(stat_filters.url_replace(r, 'num', 15), 'ordering=desc_tile&num=15')
##
#################################### TEST tile_views ###################################
##
##class TestTileViewTemplateTags(TestCase):
##    fixtures = ['test_view_tiles.json.gz']
##    """
##        test_view_tiles has the following structure:
##        position,  min,     avg,  max
##               0,  249,  250.50,  252 {'vars':6, 'lengths':[251,250,250,251,252,249]}
##        Most view tests will be on path 0 (the first path)
##    """
##    def test_template_tags_strand_pretty(self):
##        self.assertEqual(tile_filters.strand_pretty(True), '+')
##        self.assertEqual(tile_filters.strand_pretty(False), '-')
##        self.assertEqual(tile_filters.strand_pretty(None), '')
##    def test_template_tags_strand_pretty_incorrect_input(self):
##        self.assertRaises(AssertionError, tile_filters.strand_pretty, 1)
##    
##    def test_template_tags_get_SNP_INDEL_annotations_no_annotations(self):
##        tile_variant = TileVariant.objects.get(pk=0)
##        annotations = tile_filters.get_SNP_INDEL_annotations(tile_variant)
##        self.assertEqual(len(annotations), 0)
##        self.assertQuerysetEqual(annotations, [])
##        
##    def test_template_tags_get_SNP_INDEL_annotations(self):
##        tile_variant = TileVariant.objects.get(pk=1)
##        annotations = tile_filters.get_SNP_INDEL_annotations(tile_variant)
##        self.assertEqual(len(annotations), 1)
##        self.assertQuerysetEqual(annotations, ['SNP_INDEL'], transform=lambda a: a.annotation_type)
##
##        tile_variant = TileVariant.objects.get(pk=2)
##        annotations = tile_filters.get_SNP_INDEL_annotations(tile_variant)
##        self.assertEqual(len(annotations), 2)
##        self.assertQuerysetEqual(annotations, ['SNP_INDEL','SNP_INDEL'], transform=lambda a: a.annotation_type)
##        
##    def test_template_tags_get_SNP_INDEL_annotations_incorrect_input(self):
##        #Incorrect type of input (Tile instead of TileVariant)
##        tile = Tile.objects.filter(pk=0)
##        self.assertRaises(AssertionError, tile_filters.get_SNP_INDEL_annotations, tile)
##        #TileVariant that does not exist
##        tile_variant = TileVariant.objects.filter(pk=10)
##        self.assertRaises(BaseException, tile_filters.get_SNP_INDEL_annotations, tile_variant)
##
##    def test_template_tags_get_database_annotations_no_annotations(self):
##        tile_variant = TileVariant.objects.get(pk=0)
##        annotations = tile_filters.get_database_annotations(tile_variant)
##        self.assertEqual(len(annotations), 0)
##        self.assertQuerysetEqual(annotations, [])
##        
##    def test_template_tags_get_database_annotations(self):
##        tile_variant = TileVariant.objects.get(pk=2)
##        annotations = tile_filters.get_database_annotations(tile_variant)
##        self.assertEqual(len(annotations), 1)
##        self.assertQuerysetEqual(annotations, ['DATABASE'], transform=lambda a: a.annotation_type)
##        
##    def test_template_tags_get_database_annotations_incorrect_input(self):
##        #Incorrect type of input (Tile instead of TileVariant)
##        tile = Tile.objects.get(pk=0)
##        self.assertRaises(AssertionError, tile_filters.get_database_annotations, tile)
##        #TileVariant that does not exist
##        tile_variant = TileVariant.objects.filter(pk=10)
##        self.assertRaises(BaseException, tile_filters.get_database_annotations, tile_variant)
##
##    def test_template_tags_get_readable_annotation_text_no_annotation_text(self):
##        #wait until annotation revamp
##        #Also check for weirdly formated annotation text
##        pass
##
##    def test_template_tags_get_readable_annotation_text(self):
##        annotations = TileVariant.objects.get(pk=1).annotations.filter(annotation_type='SNP_INDEL')
##        readable = tile_filters.get_readable_annotation_text(annotations[0])
##        self.assertEqual(readable, 'INDEL 25 G => -')
##
##        annotations = TileVariant.objects.get(pk=2).annotations.filter(annotation_type='SNP_INDEL').order_by('annotation_text')
##        readable = tile_filters.get_readable_annotation_text(annotations[1])
##        self.assertEqual(readable, 'INDEL 25 G => -')
##        readable = tile_filters.get_readable_annotation_text(annotations[0])
##        self.assertEqual(readable, 'SNP 251 T => A')
##
##    def test_template_tags_get_readable_annotation_text_incorrect_input(self):
##        #Incorrect type of input (Tile instead of VarAnnotation)
##        tile = Tile.objects.get(pk=0)
##        self.assertRaises(AssertionError, tile_filters.get_readable_annotation_text, tile)
##        #Non-existant annotation 
##        annotation = TileVariant.objects.get(pk=0).annotations.filter(pk=1)
##        self.assertRaises(BaseException, tile_filters.get_readable_annotation_text, annotation)
##        #Wrong-type of annotation
##        annotation = TileVariant.objects.get(pk=2).annotations.filter(annotation_type='DATABASE')
##        self.assertRaises(BaseException, tile_filters.get_readable_annotation_text, annotation)
##
##    def test_template_tags_get_snps_no_annotation_text(self):
##        #wait until annotation revamp
##        #Also check for weirdly formated annotation text
##        pass
##
##    def test_template_tags_get_snps(self):
##        annotations = TileVariant.objects.get(pk=2).annotations.filter(annotation_type='DATABASE')
##        readable = tile_filters.get_snps(annotations[0])
##        self.assertEqual(type(readable), list)
##        self.assertItemsEqual(readable, ['rs1708875'])
##        
##    def test_template_tags_get_snps_incorrect_input(self):
##        #Incorrect type of input (Tile instead of VarAnnotation)
##        tile = Tile.objects.get(pk=0)
##        self.assertRaises(AssertionError, tile_filters.get_snps, tile)
##        #Non-existant annotation 
##        annotation = TileVariant.objects.get(pk=0).annotations.filter(pk=1)
##        self.assertRaises(BaseException, tile_filters.get_snps, annotation)
##        #Wrong-type of annotation
##        annotation = TileVariant.objects.get(pk=2).annotations.filter(annotation_type='SNP_INDEL')
##        self.assertRaises(BaseException, tile_filters.get_snps, annotation)
##        
##    def test_template_tags_get_aa_no_annotation_text(self):
##        #wait until annotation revamp
##        #Also check for weirdly formated annotation text
##        pass
##    
##    def test_template_tags_get_aa(self):
##        annotations = TileVariant.objects.get(pk=2).annotations.filter(annotation_type='DATABASE')
##        readable = tile_filters.get_aa(annotations[0])
##        self.assertNotEqual(type(readable), list)
##        self.assertEqual(readable.strip(), 'RUNDC1 W160R')
##    
##    def test_template_tags_get_aa_incorrect_input(self):
##        #Incorrect type of input (Tile instead of VarAnnotation)
##        tile = Tile.objects.get(pk=0)
##        self.assertRaises(AssertionError, tile_filters.get_aa, tile)
##        #Non-existant annotation 
##        annotation = TileVariant.objects.get(pk=0).annotations.filter(pk=1)
##        self.assertRaises(BaseException, tile_filters.get_aa, annotation)
##        #Wrong-type of annotation
##        annotation = TileVariant.objects.get(pk=2).annotations.filter(annotation_type='SNP_INDEL')
##        self.assertRaises(BaseException, tile_filters.get_aa, annotation)
##        
##    def test_template_tags_get_other_no_annotation_text(self):
##        #wait until annotation revamp
##        #Also check for weirdly formated annotation text
##        pass
##    
##    def test_template_tags_get_other(self):
##        annotations = TileVariant.objects.get(pk=2).annotations.filter(annotation_type='DATABASE')
##        readable = tile_filters.get_other(annotations[0])
##        self.assertEqual(type(readable), list)
##        self.assertEqual(readable, ['ucsc_trans uc002ici.1'])
##        
##    def test_template_tags_get_other_incorrect_input(self):
##        #Incorrect type of input (Tile instead of VarAnnotation)
##        tile = Tile.objects.get(pk=0)
##        self.assertRaises(AssertionError, tile_filters.get_other, tile)
##        #Non-existant annotation 
##        annotation = TileVariant.objects.get(pk=0).annotations.filter(pk=1)
##        self.assertRaises(BaseException, tile_filters.get_other, annotation)
##        #Wrong-type of annotation
##        annotation = TileVariant.objects.get(pk=2).annotations.filter(annotation_type='SNP_INDEL')
##        self.assertRaises(BaseException, tile_filters.get_other, annotation)
##        
##    def test_template_tags_get_reference_sequence(self):
##        tile_variants = Tile.objects.get(pk=0).variants.all()
##        ref_seq_list = tile_filters.get_reference_sequence(tile_variants)
##        self.assertEqual(type(ref_seq_list), list)
##        self.assertTrue(str(ref_seq_list[0]).startswith('ggtttgtccgtggt'))
##        self.assertEqual(ref_seq_list[-1], 'ggc')
##        for seq in ref_seq_list[:-1]:
##            self.assertEqual(len(seq), 50)
##
##    def test_template_tags_get_reference_sequence_incorrect_input(self):
##        tile_variants = TileVariant.objects.get(pk=0)
##        self.assertRaises(AssertionError,tile_filters.get_reference_sequence, tile_variants)
##        tile_variants = TileVariant.objects.filter(tile=1)
##        self.assertRaises(BaseException,tile_filters.get_reference_sequence, tile_variants)
##        
##class TestViewTileView(TestCase):
##    fixtures = ['test_view_tiles.json.gz']
##    """
##        test_view_tiles has the following structure:
##        position,  min,     avg,  max
##               0,  249,  250.50,  252 {'vars':6, 'lengths':[251,250,250,251,252,249]}
##        Most view tests will be on path 0 (the first path)
##
##        Tile View does not require Statistics, so don't need to check what happens if
##            generate_statistics hasn't been run: it will be the exact same
##        """
##    def test_wrong_numbers_return_404(self):
##        response = self.client.get(reverse('tile_library:tile_view', args=(0,0,0)))
##        self.assertEqual(response.status_code, 404)
##        response = self.client.get(reverse('tile_library:tile_view', args=(27,0,0)))
##        self.assertEqual(response.status_code, 404)
##        
##        reasonable_tile, foo = fns.get_min_position_and_tile_variant_from_path_int(Tile.CHR_PATH_LENGTHS[1]-1)
##        response = self.client.get(reverse('tile_library:tile_view', args=(2, Tile.CHR_PATH_LENGTHS[1]-1,reasonable_tile)))
##        self.assertEqual(response.status_code, 404)
##        response = self.client.get(reverse('tile_library:tile_view', args=(2, Tile.CHR_PATH_LENGTHS[1]-1,0)))
##        self.assertEqual(response.status_code, 404)
##        
##        reasonable_tile, foo = fns.get_min_position_and_tile_variant_from_path_int(Tile.CHR_PATH_LENGTHS[2])
##        response = self.client.get(reverse('tile_library:tile_view', args=(2, Tile.CHR_PATH_LENGTHS[2],reasonable_tile)))
##        self.assertEqual(response.status_code, 404)
##        response = self.client.get(reverse('tile_library:tile_view', args=(2, Tile.CHR_PATH_LENGTHS[2],0)))
##        self.assertEqual(response.status_code, 404)
##        
##        response = self.client.get(reverse('tile_library:tile_view', args=(1,1,0)))
##        self.assertEqual(response.status_code, 404)
##
##        big_tile, foo = fns.get_min_position_and_tile_variant_from_path_int(1)
##        response = self.client.get(reverse('tile_library:tile_view', args=(1,0,big_tile)))
##        self.assertEqual(response.status_code, 404)
##
##    def test_non_existant_tile_view(self):
##        response = self.client.get(reverse('tile_library:tile_view', args=(1,0,1)))
##        self.assertEqual(response.status_code, 200)
##        self.assertFalse('position' in response.context)
##        self.assertFalse('tiles' in response.context)
##        self.assertContains(response, "not populated")
##
##    def test_view(self):
##        response = self.client.get(reverse('tile_library:tile_view', args=(1,0,0)))
##        self.assertEqual(response.status_code, 200)
##        self.assertTrue('position' in response.context)
##        self.assertTrue('tiles' in response.context)
##        self.assertEqual(response.context['chr_int'], 1)
##        self.assertEqual(response.context['chr_name'], 'chr1')
##        self.assertEqual(response.context['path_int'], 0)
##        self.assertEqual(response.context['path_hex'], '0')
##        self.assertEqual(response.context['path_name'], Tile.CYTOMAP[0])
##        self.assertEqual(response.context['position_name'], '000.00.0000')
##        position = response.context['position']
##        tiles = response.context['tiles']
##        true_tiles = TileVariant.objects.all()
##        self.assertEqual(len(tiles), 6)
##        for i, t in enumerate(tiles):
##            self.assertEqual(t, true_tiles[i])
##        self.assertEqual(position.tilename, 0)
##        self.assertEqual(position.start_tag, 'GTAGGCTTTCCTATTCCCACCTTG')
##        self.assertEqual(position.end_tag, 'CGCGGTTATTTCTACGACATAAAT')
##
##        
#################################### TEST gene_path_views ################################### 
##class TestViewGenePathView(TestCase):
##    """
##        make_tiles generates the following structure:
##            i,  min,     avg,  max
##            0,  448,  448.67,  450 {'vars':3, 'lengths':[448,448,450]}, #1
##            1,  301,  301.00,  301 {'vars':2, 'lengths':[301,301]}, #2
##            2,  200,  257.67,  300 {'vars':3, 'lengths':[273,200,300]}, #3
##            3,  149,  149.00,  149 {'vars':1, 'lengths':[149]}, #4
##            4,  425,  425.00,  425 {'vars':1, 'lengths':[425]}, #5
##            5,  500,  549.75,  600 {'vars':4, 'lengths':[549,500,600,550]}, #6
##            6,  198,  199.00,  200 {'vars':4, 'lengths':[199,198,200,199]}, #7
##            7,  249,  249.00,  249 {'vars':2, 'lengths':[249,249]}, #8
##            8,  199,  199.00,  199 {'vars':1, 'lengths':[199]}, #9
##            9, 1200, 1200.00, 1200 {'vars':1, 'lengths':[1200]}, #10
##           10,  264,  264.50,  265 {'vars':2, 'lengths':[264,265]}, #11
##           11,  249,  250.50,  252 {'vars':6, 'lengths':[251,250,250,251,252,249]}, #12
##           12,  275,  275.50,  276 {'vars':2, 'lengths':[275,276]}, #13
##           13,  277,  277.00,  277 {'vars':2, 'lengths':[277,277]}, #14
##           14,  267,  267.00,  267 {'vars':1, 'lengths':[267]}, #15
##           15,  258,  258.00,  258 {'vars':1, 'lengths':[258]}, #16
##           16,  248,  248.00,  248 {'vars':3, 'lengths':[248,248,248]}, #17
##           17,  250,  250.00,  250 {'vars':1, 'lengths':[250]}, #18
##
##        Most view tests will be on path 0 (the first path)
##        """
##    def test_wrong_gene_id_return_404(self):
##        #Fail when nothing exists
##        response = self.client.get(reverse('tile_library:gene_view', args=(0,)))
##        self.assertEqual(response.status_code, 404)
##        #Fail when wrong gene
##        make_gene1()
##        gene_id = GeneXRef.objects.all().first().id
##        response = self.client.get(reverse('tile_library:gene_view', args=(gene_id+1,)))
##        self.assertEqual(response.status_code, 404)
##        #Fail when tiles exist and still wrong gene
##        make_tiles()
##        response = self.client.get(reverse('tile_library:gene_view', args=(gene_id+1,)))
##        self.assertEqual(response.status_code, 404)
##
##    def test_non_overlapping_genes_return_404(self):
##        #Non-overlapping genes should not be viewed in this manner
##        make_tiles()
##        make_gene1()
##        make_chr2_gene()
##        gene_id = GeneXRef.objects.all().first().id
##        response = self.client.get(reverse('tile_library:gene_view', args=(gene_id,)))
##        self.assertEqual(response.status_code, 404)
##        
##    def test_absence_of_or_wrong_tile_locus_annotations_return_404(self):
##        #If genes have wrong assembly and we can't lift-over, raise 404
##        make_tiles(assembly_default=18)
##        make_gene1()
##        gene_id = GeneXRef.objects.all().first().id
##        response = self.client.get(reverse('tile_library:gene_view', args=(gene_id,)))
##        self.assertEqual(response.status_code, 404)
##    
##    #Gene view is not dependent on statistics
##    def test_gene_empty_tiles_view(self):
##        make_gene1()
##        gene_id = GeneXRef.objects.all().first().id
##        response = self.client.get(reverse('tile_library:gene_view', args=(gene_id,)))
##        self.assertEqual(response.status_code, 200)
##        self.assertFalse('positions' in response.context)
##        self.assertFalse('exon_dict' in response.context)
##        self.assertContains(response, "The tiles composing this gene are not loaded into the Tile Library.")
##
##    def test_basic_gene_path_view(self):
##        make_tiles()
##        make_long_gene1()
##        gene_id = GeneXRef.objects.all().first().id
##        true_positions = views.get_positions(0, 17)
##        response = self.client.get(reverse('tile_library:gene_view', args=(gene_id,)))
##        self.assertEqual(response.status_code, 200)
##        self.assertTrue('positions' in response.context)
##        self.assertTrue('exon_dict' in response.context)
##        self.assertEqual(response.context['chromosome_int'], 1)
##        self.assertEqual(response.context['chromosome'], 'chr1')
##        info = response.context['position_info']
##        self.assertEqual(info['end_path_int'], 0)
##        self.assertEqual(info['end_path_hex'], '0')
##        self.assertEqual(info['end_path_name'], Tile.CYTOMAP[0])
##        self.assertFalse('beg_path_int' in info)
##        self.assertFalse('beg_path_hex' in info)
##        self.assertFalse('beg_path_name' in info)
##        positions = response.context['positions']
##        exon_dict = response.context['exon_dict']
##
##        self.assertEqual(len(positions), 16)
##        for i, pos in enumerate(positions):
##            self.assertEqual(pos, true_positions[i])
##        self.assertEqual(exon_dict, LONG_GENE1_CHECK_DICT)
##
##    def test_basic_gene_path_view_alternate_assembly(self):
##        make_tiles(assembly_default=18)
##        make_long_gene1(assembly=18)
##        gene_id = GeneXRef.objects.all().first().id
##        true_positions = views.get_positions(0, 17)
##        response = self.client.get(reverse('tile_library:gene_view', args=(gene_id,)))
##        self.assertEqual(response.status_code, 200)
##        self.assertTrue('positions' in response.context)
##        self.assertTrue('exon_dict' in response.context)
##        self.assertEqual(response.context['chromosome_int'], 1)
##        self.assertEqual(response.context['chromosome'], 'chr1')
##        info = response.context['position_info']
##        self.assertEqual(info['end_path_int'], 0)
##        self.assertEqual(info['end_path_hex'], '0')
##        self.assertEqual(info['end_path_name'], Tile.CYTOMAP[0])
##        self.assertFalse('beg_path_int' in info)
##        self.assertFalse('beg_path_hex' in info)
##        self.assertFalse('beg_path_name' in info)
##        positions = response.context['positions']
##        exon_dict = response.context['exon_dict']
##
##        self.assertEqual(len(positions), 16)
##        for i, pos in enumerate(positions):
##            self.assertEqual(pos, true_positions[i])
##        self.assertEqual(exon_dict, LONG_GENE1_CHECK_DICT)
##
##    def test_small_gene_path_view(self):
##        make_tiles()
##        make_gene1()
##        gene_id = GeneXRef.objects.all().first().id
##        true_positions = views.get_positions(0, 17)
##        response = self.client.get(reverse('tile_library:gene_view', args=(gene_id,)))
##        self.assertEqual(response.status_code, 200)
##        self.assertTrue('positions' in response.context)
##        self.assertTrue('exon_dict' in response.context)
##        self.assertEqual(response.context['chromosome_int'], 1)
##        self.assertEqual(response.context['chromosome'], 'chr1')
##        info = response.context['position_info']
##        self.assertEqual(info['end_path_int'], 0)
##        self.assertEqual(info['end_path_hex'], '0')
##        self.assertEqual(info['end_path_name'], Tile.CYTOMAP[0])
##        self.assertFalse('beg_path_int' in info)
##        self.assertFalse('beg_path_hex' in info)
##        self.assertFalse('beg_path_name' in info)
##    
##        positions = response.context['positions']
##        exon_dict = response.context['exon_dict']
##        check_dict = {1:True, 2:False, 3:False, 4:True, 5:True}
##        self.assertEqual(len(positions), 5)
##        for i, pos in enumerate(positions):
##            self.assertEqual(pos, true_positions[i+1]) 
##        self.assertEqual(exon_dict, check_dict)
##
##    def test_gene_spanning_many_paths_view(self):
##        make_ridiculously_long_gene()
##        gene_id = GeneXRef.objects.all().first().id
##        true_positions = views.get_positions(0, int('2000006', 16))
##        response = self.client.get(reverse('tile_library:gene_view', args=(gene_id,)))
##        self.assertEqual(response.status_code, 200)
##        self.assertTrue('positions' in response.context)
##        self.assertTrue('exon_dict' in response.context)
##        self.assertEqual(response.context['chromosome_int'], 1)
##        self.assertEqual(response.context['chromosome'], 'chr1')
##        info = response.context['position_info']
##        self.assertEqual(info['end_path_int'], 2)
##        self.assertEqual(info['end_path_hex'], '2')
##        self.assertEqual(info['end_path_name'], Tile.CYTOMAP[2])
##        self.assertEqual(info['beg_path_int'], 0)
##        self.assertEqual(info['beg_path_hex'], '0')
##        self.assertEqual(info['beg_path_name'], Tile.CYTOMAP[0])
##    
##        positions = response.context['positions']
##        exon_dict = response.context['exon_dict']
##        self.assertEqual(len(positions), 16)
##        for i, pos in enumerate(positions):
##            self.assertEqual(pos, true_positions[i])
##
##        l = sorted(exon_dict.keys())
##        exon_list = []
##        for i in l:
##            exon_list.append(exon_dict[i])
##        for i in range(len(exon_dict)):
##            self.assertEqual(exon_list[i], LONG_GENE1_CHECK_LIST[i])
##        
##    def test_first_page_gene_page_view(self):
##        """ Test asking for the first page is the same as the default page """
##        make_tiles()
##        make_long_gene1()
##        gene_id = GeneXRef.objects.all().first().id
##        true_positions = views.get_positions(0, 17)
##        response_1 = self.client.get(reverse('tile_library:gene_view', args=(gene_id,))+'?page=1')
##        response_2 = self.client.get(reverse('tile_library:gene_view', args=(gene_id,)))
##
##        for item in ['chromosome_int', 'chromosome', 'position_info']:
##            self.assertEqual(response_1.context[item], response_2.context[item])
##        self.assertItemsEqual(response_1.context['positions'], response_2.context['positions'])
##        self.assertEqual(response_1.context['exon_dict'], response_2.context['exon_dict'])
##        self.assertEqual(response_1.context['exon_dict'], LONG_GENE1_CHECK_DICT)
##
##    def test_second_page_gene_page_view(self):
##        """ Test asking for the first page is the same as the default page """
##        make_tiles()
##        make_long_gene1()
##        gene_id = GeneXRef.objects.all().first().id
##        true_positions = views.get_positions(0, 17)
##        response_1 = self.client.get(reverse('tile_library:gene_view', args=(gene_id,))+'?page=2')
##        response_2 = self.client.get(reverse('tile_library:gene_view', args=(gene_id,)))
##        for item in ['chromosome_int', 'chromosome', 'position_info']:
##            self.assertEqual(response_1.context[item], response_2.context[item])
##
##        self.assertEqual(len(response_1.context['positions']), len(true_positions[16:]))
##        for pos1, pos2 in zip(response_1.context['positions'], true_positions[16:]):
##            self.assertEqual(pos1, pos2)    
##        self.assertEqual(response_1.context['exon_dict'], response_2.context['exon_dict'])
##        self.assertEqual(response_1.context['exon_dict'], LONG_GENE1_CHECK_DICT)
##
##    def test_pagination_alteration_statistics_view(self):
##        make_tiles()
##        make_long_gene1()
##        gene_id = GeneXRef.objects.all().first().id
##        true_positions = views.get_positions(0, 17)
##        response_1 = self.client.get(reverse('tile_library:gene_view', args=(gene_id,))+'?num=10')
##        self.assertEqual(len(response_1.context['positions']),10)
##
##        response_2 = self.client.get(reverse('tile_library:gene_view', args=(gene_id,)))
##        for item in ['chromosome_int', 'chromosome', 'position_info']:
##            self.assertEqual(response_1.context[item], response_2.context[item])
##
##        self.assertNotEqual(len(response_1.context['positions']), len(response_2.context['positions']))
##        for pos1, pos2 in zip(response_1.context['positions'], response_2.context['positions']):
##            self.assertEqual(pos1, pos2)
##        self.assertEqual(response_1.context['exon_dict'], response_2.context['exon_dict'])
##        self.assertEqual(response_1.context['exon_dict'], LONG_GENE1_CHECK_DICT)
##
##    def test_pagination_alteration_second_page_statistics_view(self):
##        make_tiles()
##        make_long_gene1()
##        gene_id = GeneXRef.objects.all().first().id
##        true_positions = views.get_positions(0, 17)
##        response_1 = self.client.get(reverse('tile_library:gene_view', args=(gene_id,))+'?num=10&page=2')
##        self.assertEqual(len(response_1.context['positions']),8)
##
##        response_2 = self.client.get(reverse('tile_library:gene_view', args=(gene_id,)))
##        for item in ['chromosome_int', 'chromosome', 'position_info']:
##            self.assertEqual(response_1.context[item], response_2.context[item])
##        self.assertEqual(len(response_1.context['positions']), len(true_positions[10:]))
##        for pos1, pos2 in zip(response_1.context['positions'], true_positions[10:]):
##            self.assertEqual(pos1, pos2)
##        self.assertEqual(response_1.context['exon_dict'], response_2.context['exon_dict'])
##        self.assertEqual(response_1.context['exon_dict'], LONG_GENE1_CHECK_DICT)
##        
##    def test_ordering_statistics_view(self):
##        make_tiles()
##        make_long_gene1()
##        gene_id = GeneXRef.objects.all().first().id
##        rev_positions = list(views.get_positions(0, 17))
##        rev_positions.reverse()
##        response_1 = self.client.get(reverse('tile_library:gene_view', args=(gene_id,))+'?ordering=desc_tile')
##        self.assertEqual(len(response_1.context['positions']),16)
##        
##        response_2 = self.client.get(reverse('tile_library:gene_view', args=(gene_id,)))
##        for item in ['chromosome_int', 'chromosome', 'position_info']:
##            self.assertEqual(response_1.context[item], response_2.context[item])
##        self.assertEqual(len(response_1.context['positions']), len(rev_positions[:16]))
##        for pos1, pos2 in zip(response_1.context['positions'], rev_positions[:16]):
##            self.assertEqual(pos1, pos2)
##        self.assertEqual(response_1.context['exon_dict'], response_2.context['exon_dict'])
##        self.assertEqual(response_1.context['exon_dict'], LONG_GENE1_CHECK_DICT)
##
##    def test_ordering_pagination_alteration_statistics_view(self):
##        make_tiles()
##        make_long_gene1()
##        gene_id = GeneXRef.objects.all().first().id
##        rev_positions = list(views.get_positions(0, 17))
##        rev_positions.reverse()
##        response_1 = self.client.get(reverse('tile_library:gene_view', args=(gene_id,))+'?ordering=desc_tile&num=10')
##        self.assertEqual(len(response_1.context['positions']),10)
##
##        response_2 = self.client.get(reverse('tile_library:gene_view', args=(gene_id,)))
##        for item in ['chromosome_int', 'chromosome', 'position_info']:
##            self.assertEqual(response_1.context[item], response_2.context[item])
##        self.assertEqual(len(response_1.context['positions']), len(rev_positions[:10]))
##        for pos1, pos2 in zip(response_1.context['positions'], rev_positions[:10]):
##            self.assertEqual(pos1, pos2)
##        self.assertEqual(response_1.context['exon_dict'], response_2.context['exon_dict'])
##        self.assertEqual(response_1.context['exon_dict'], LONG_GENE1_CHECK_DICT)
##
##    def test_ordering_second_page_statistics_view(self):
##        make_tiles()
##        make_long_gene1()
##        gene_id = GeneXRef.objects.all().first().id
##        rev_positions = list(views.get_positions(0, 17))
##        rev_positions.reverse()
##        response_1 = self.client.get(reverse('tile_library:gene_view', args=(gene_id,))+'?ordering=desc_tile&page=2')
##        self.assertEqual(len(response_1.context['positions']),2)
##
##        response_2 = self.client.get(reverse('tile_library:gene_view', args=(gene_id,)))
##        for item in ['chromosome_int', 'chromosome', 'position_info']:
##            self.assertEqual(response_1.context[item], response_2.context[item])
##        self.assertEqual(len(response_1.context['positions']), len(rev_positions[16:]))
##        for pos1, pos2 in zip(response_1.context['positions'], rev_positions[16:]):
##            self.assertEqual(pos1, pos2)
##        self.assertEqual(response_1.context['exon_dict'], response_2.context['exon_dict'])
##        self.assertEqual(response_1.context['exon_dict'], LONG_GENE1_CHECK_DICT)
##
##    def test_ordering_pagination_alteration_second_page_statistics_view(self):
##        make_tiles()
##        make_long_gene1()
##        gene_id = GeneXRef.objects.all().first().id
##        rev_positions = list(views.get_positions(0, 17))
##        rev_positions.reverse()
##        response_1 = self.client.get(reverse('tile_library:gene_view', args=(gene_id,))+'?ordering=desc_tile&num=10&page=2')
##        self.assertEqual(len(response_1.context['positions']),8)
##        
##        response_2 = self.client.get(reverse('tile_library:gene_view', args=(gene_id,)))
##        for item in ['chromosome_int', 'chromosome', 'position_info']:
##            self.assertEqual(response_1.context[item], response_2.context[item])
##        self.assertEqual(len(response_1.context['positions']), len(rev_positions[10:]))
##        for pos1, pos2 in zip(response_1.context['positions'], rev_positions[10:]):
##            self.assertEqual(pos1, pos2)
##        self.assertEqual(response_1.context['exon_dict'], response_2.context['exon_dict'])
##        self.assertEqual(response_1.context['exon_dict'], LONG_GENE1_CHECK_DICT)
##
##class TestViewGeneTileView(TestCase):
##    """
##        test_view_tiles has the following structure:
##        position,  min,     avg,  max
##               0,  249,  250.50,  252 {'vars':6, 'lengths':[251,250,250,251,252,249]}
##        Most view tests will be on path 0 (the first path)
##
##        Tile View does not require Statistics, so don't need to check what happens if
##            generate_statistics hasn't been run: it will be the exact same
##        """
##    def test_wrong_numbers_return_404(self):
##        #Fail when nothing exists
##        response = self.client.get(reverse('tile_library:tile_in_gene_view', args=(0,1)))
##        self.assertEqual(response.status_code, 404)
##        #Fail when tile doesn't exist and wrong gene
##        make_gene1()
##        gene_id = GeneXRef.objects.all().first().id
##        response = self.client.get(reverse('tile_library:tile_in_gene_view', args=(gene_id+1,1)))
##        self.assertEqual(response.status_code, 404)
##        #Fail when tiles exist and still wrong gene
##        make_tiles()
##        response = self.client.get(reverse('tile_library:tile_in_gene_view', args=(gene_id+1,1)))
##        self.assertEqual(response.status_code, 404)
##
##    def test_non_overlapping_genes_return_404(self):
##        #Non-overlapping genes should not be viewed in this manner
##        make_tiles()
##        make_gene1()
##        make_chr2_gene()
##        gene_id = GeneXRef.objects.all().first().id
##        response = self.client.get(reverse('tile_library:tile_in_gene_view', args=(gene_id,1)))
##        self.assertEqual(response.status_code, 404)
##        
##    def test_absence_of_or_wrong_tile_locus_annotations_return_404(self):
##        #If genes have wrong assembly and we can't lift-over, raise 404
##        make_tiles(assembly_default=18)
##        make_gene1()
##        gene_id = GeneXRef.objects.all().first().id
##        response = self.client.get(reverse('tile_library:tile_in_gene_view', args=(gene_id,1)))
##        self.assertEqual(response.status_code, 404)
##    
##    #Gene view and tile view is not dependent on statistics
##    def test_non_existant_tile_in_gene_view(self):
##        make_gene1()
##        gene_id = GeneXRef.objects.all().first().id
##        response = self.client.get(reverse('tile_library:tile_in_gene_view', args=(gene_id,1)))
##        self.assertEqual(response.status_code, 200)
##        self.assertFalse('position' in response.context)
##        self.assertFalse('tiles' in response.context)
##        self.assertFalse('pos_outline' in response.context)
##        self.assertFalse('in_exon' in response.context)
##        self.assertFalse('exons' in response.context)
##        self.assertContains(response, "This position (tile) has not been loaded into the Tile Library.") 
##
##    def test_view_not_in_gene_checking_lower_table(self):
##        make_tiles(skip_zero=True)
##        make_long_gene1()
##        gene_id = GeneXRef.objects.all().first().id
##        response = self.client.get(reverse('tile_library:tile_in_gene_view', args=(gene_id,0)))
##        self.assertEqual(response.status_code, 200)
##        self.assertTrue('position' in response.context)
##        self.assertTrue('tiles' in response.context)
##        self.assertTrue('pos_outline' in response.context)
##        self.assertTrue('in_exon' in response.context)
##        self.assertTrue('exons' in response.context)
##        self.assertEqual(response.context['chr_int'], 1)
##        self.assertEqual(response.context['chr_name'], 'chr1')
##        self.assertEqual(response.context['path_int'], 0)
##        self.assertEqual(response.context['path_hex'], '0')
##        self.assertEqual(response.context['path_name'], Tile.CYTOMAP[0])
##        self.assertEqual(response.context['position_name'], '000.00.0000')
##        position = response.context['position']
##        tiles = response.context['tiles']
##        true_tiles = TileVariant.objects.all()
##        self.assertEqual(len(tiles), 6)
##        for i, t in enumerate(tiles):
##            self.assertEqual(t, true_tiles[i])
##        self.assertEqual(position.tilename, 0)
##        self.assertEqual(position.start_tag, 'GTAGGCTTTCCTATTCCCACCTTG')
##        self.assertEqual(position.end_tag, 'CGCGGTTATTTCTACGACATAAAT')
##        
##        self.assertContains(response, "No piece of this tile is coding.")
##        
##        pos_outline = response.context['pos_outline']
##        self.assertAlmostEqual(pos_outline[0], 24/448.0*100)
##        self.assertAlmostEqual(pos_outline[1], 400/448.0*100)
##        self.assertAlmostEqual(pos_outline[2], 24/448.0*100)
##
##        self.assertFalse(response.context['in_exon'])
##
##        all_exons, genes = zip(*response.context['exons'])
##        #all_exons is colorings
##        has_exons, check_all_exons = gene_fns.color_exon_parts(GeneXRef.objects.all(), Tile.objects.get(pk=0))
##        self.assertItemsEqual(all_exons, check_all_exons)
##        self.assertItemsEqual(genes, list(GeneXRef.objects.all()))
##        
##    def test_view_in_gene(self):
##        make_tiles()
##        make_long_gene1()
##        gene_id = GeneXRef.objects.all().first().id
##        response = self.client.get(reverse('tile_library:tile_in_gene_view', args=(gene_id,1)))
##        self.assertEqual(response.status_code, 200)
##        self.assertTrue('position' in response.context)
##        self.assertTrue('tiles' in response.context)
##        self.assertTrue('pos_outline' in response.context)
##        self.assertTrue('in_exon' in response.context)
##        self.assertTrue('exons' in response.context)
##        self.assertEqual(response.context['chr_int'], 1)
##        self.assertEqual(response.context['chr_name'], 'chr1')
##        self.assertEqual(response.context['path_int'], 0)
##        self.assertEqual(response.context['path_hex'], '0')
##        self.assertEqual(response.context['path_name'], Tile.CYTOMAP[0])
##        self.assertEqual(response.context['position_name'], '000.00.0001')
##        position = response.context['position']
##        tiles = response.context['tiles']
##        true_tiles = TileVariant.objects.filter(tile_id=1)
##        self.assertEqual(len(tiles), 2)
##        for i, t in enumerate(tiles):
##            self.assertEqual(t, true_tiles[i])
##        self.assertEqual(position.tilename, 1)
##        
##        pos_outline = response.context['pos_outline']
##        self.assertAlmostEqual(pos_outline[0], 24/301.0*100)
##        self.assertAlmostEqual(pos_outline[1], 253/301.0*100)
##        self.assertAlmostEqual(pos_outline[2], 24/301.0*100)
##
##        self.assertTrue(response.context['in_exon'])
##
##        all_exons, genes = zip(*response.context['exons'])
##        #all_exons is coloring
##        has_exons, check_all_exons = gene_fns.color_exon_parts(GeneXRef.objects.all(), Tile.objects.get(pk=1))
##        self.assertItemsEqual(all_exons, check_all_exons)
##        self.assertItemsEqual(genes, list(GeneXRef.objects.all()))
##
##    def test_view_multiple_genes_tile_in_gene(self):
##        make_tiles()
##        make_gene1()
##        make_gene1pt5()
##        gene_id = GeneXRef.objects.all().first().id
##        response = self.client.get(reverse('tile_library:tile_in_gene_view', args=(gene_id,1)))
##        self.assertEqual(response.status_code, 200)
##
##        position = response.context['position']
##        tiles = response.context['tiles']
##        true_tiles = TileVariant.objects.filter(tile_id=1)
##        self.assertEqual(len(tiles), 2)
##        for i, t in enumerate(tiles):
##            self.assertEqual(t, true_tiles[i])
##        self.assertEqual(position.tilename, 1)
##        
##        pos_outline = response.context['pos_outline']
##        self.assertAlmostEqual(pos_outline[0], 24/301.0*100)
##        self.assertAlmostEqual(pos_outline[1], 253/301.0*100)
##        self.assertAlmostEqual(pos_outline[2], 24/301.0*100)
##
##        self.assertTrue(response.context['in_exon'])
##
##        all_exons, genes = zip(*response.context['exons'])
##        #all_exons is coloring
##        has_exons, check_all_exons = gene_fns.color_exon_parts(GeneXRef.objects.all(), Tile.objects.get(pk=1))
##        self.assertItemsEqual(all_exons, check_all_exons)
##        self.assertItemsEqual(genes, list(GeneXRef.objects.all()))
##
##
##class TestViewTileLibraryInteractive(StaticLiveServerTestCase):
##    @classmethod
##    def setUpClass(cls):
##        cls.selenium = webdriver.PhantomJS()
##        #cls.selenium = WebDriver()
##        super(TestViewTileLibraryInteractive, cls).setUpClass()
##
##    @classmethod
##    def tearDownClass(cls):
##        cls.selenium.quit()
##        super(TestViewTileLibraryInteractive, cls).tearDownClass()
##    
##    def test_overall_statistics_breadcrumbs(self):
##        self.selenium.get('%s%s' % (self.live_server_url, reverse('tile_library:statistics')))
##        elements = self.selenium.find_element_by_class_name("breadcrumb").find_elements_by_tag_name('li')
##        self.assertEqual(len(elements), 2)
##        for element in elements:
##            self.assertTrue(element.is_displayed())
##            if element.text == 'Home':
##                self.assertFalse('active' in element.get_attribute('class'))
##                self.assertEqual(element.find_element_by_link_text('Home').get_attribute('href'), '%s/' % (self.live_server_url))
##                
##            elif element.text == 'Library':
##                self.assertTrue('active' in element.get_attribute('class'))
##                self.assertEqual(element.find_element_by_link_text('Library').get_attribute('href'), '%s#' % (self.selenium.current_url))
##                
##    def test_overall_statistics_view_hrefs(self):
##        gen_stats.initialize(silent=True)
##        self.selenium.get('%s%s' % (self.live_server_url, reverse('tile_library:statistics')))
##        elements = self.selenium.find_element_by_class_name("table-responsive").find_elements_by_tag_name('tr')
##        self.assertEqual(len(elements), 28)
##        for i, element in enumerate(elements):
##            self.assertTrue(element.is_displayed())
##            if i > 1:
##                self.assertEqual(element.find_element_by_tag_name('a').get_attribute('href'), '%s%s' % (self.live_server_url, reverse('tile_library:chr_statistics', args=(i-1,))))               
##
##    def test_first_chr_statistics_breadcrumbs(self):
##        self.selenium.get('%s%s' % (self.live_server_url, reverse('tile_library:chr_statistics', args=(1,))))
##        elements = self.selenium.find_element_by_class_name("breadcrumb").find_elements_by_tag_name('li')
##        self.assertEqual(len(elements), 3)
##        for element in elements:
##            self.assertTrue(element.is_displayed())
##            if element.text == 'Home':
##                self.assertFalse('active' in element.get_attribute('class'))
##                self.assertEqual(element.find_element_by_link_text('Home').get_attribute('href'), '%s/' % (self.live_server_url))
##                
##            elif element.text == 'Library':
##                self.assertFalse('active' in element.get_attribute('class'))
##                self.assertEqual(element.find_element_by_link_text('Library').get_attribute('href'), '%s%s' % (self.live_server_url, reverse('tile_library:statistics')))
##                
##            else:
##                self.assertTrue('active' in element.get_attribute('class'))
##                #This will throw an error if the link does not exist
##                self.assertEqual(element.find_element_by_link_text('chr1').get_attribute('href'), '%s#' % (self.selenium.current_url))
##                
##    def test_first_chr_statistics_view_hrefs(self):
##        gen_stats.initialize(silent=True)
##        self.selenium.get('%s%s' % (self.live_server_url, reverse('tile_library:chr_statistics', args=(1,))))
##        elements = self.selenium.find_element_by_class_name("table-responsive").find_elements_by_tag_name('tr')
##        self.assertEqual(len(elements), 2+Tile.CHR_PATH_LENGTHS[1])
##        for i, element in enumerate(elements):
##            self.assertTrue(element.is_displayed())
##            if i > 1:
##                self.assertEqual(element.find_element_by_tag_name('a').get_attribute('href'), '%s%s' % (self.live_server_url, reverse('tile_library:path_statistics', args=(1,i-2))))               
##
##    def test_mitochondrial_chr_statistics_breadcrumbs(self):
##        self.selenium.get('%s%s' % (self.live_server_url, reverse('tile_library:chr_statistics', args=(25,))))
##        elements = self.selenium.find_element_by_class_name("breadcrumb").find_elements_by_tag_name('li')
##        self.assertEqual(len(elements), 3)
##        for element in elements:
##            self.assertEqual(element.is_displayed(), True)
##            if element.text == 'Home':
##                self.assertFalse('active' in element.get_attribute('class'))
##                self.assertEqual(element.find_element_by_link_text('Home').get_attribute('href'), '%s/' % (self.live_server_url))
##
##            elif element.text == 'Library':
##                self.assertFalse('active' in element.get_attribute('class'))
##                self.assertEqual(element.find_element_by_link_text('Library').get_attribute('href'), '%s%s' % (self.live_server_url, reverse('tile_library:statistics')))
##                
##            else:
##                self.assertTrue('active' in element.get_attribute('class'))
##                #This will throw an error if the link does not exist
##                self.assertEqual(element.find_element_by_link_text('chrM').get_attribute('href'), '%s#' % (self.selenium.current_url))
##    
##    def test_mitochondrial_chr_statistics_view_hrefs(self):
##        gen_stats.initialize(silent=True)
##        self.selenium.get('%s%s' % (self.live_server_url, reverse('tile_library:chr_statistics', args=(25,))))
##        elements = self.selenium.find_element_by_class_name("table-responsive").find_elements_by_tag_name('tr')
##        
##        self.assertEqual(len(elements), 2+Tile.CHR_PATH_LENGTHS[25]-Tile.CHR_PATH_LENGTHS[24])
##        for i, element in enumerate(elements):
##            self.assertTrue(element.is_displayed())
##            if i > 1:
##                self.assertEqual(element.find_element_by_tag_name('a').get_attribute('href'), '%s%s' % (self.live_server_url,
##                                                                                                        reverse('tile_library:path_statistics', args=(25,i-2+Tile.CHR_PATH_LENGTHS[24]))))               
##
##    def test_other_chr_statistics_breadcrumbs(self):
##        self.selenium.get('%s%s' % (self.live_server_url, reverse('tile_library:chr_statistics', args=(26,))))
##        elements = self.selenium.find_element_by_class_name("breadcrumb").find_elements_by_tag_name('li')
##        self.assertEqual(len(elements), 3)
##        for element in elements:
##            self.assertTrue(element.is_displayed())
##            if element.text == 'Home':
##                self.assertFalse('active' in element.get_attribute('class'))
##                self.assertEqual(element.find_element_by_link_text('Home').get_attribute('href'), '%s/' % (self.live_server_url))
##                
##            elif element.text == 'Library':
##                self.assertFalse('active' in element.get_attribute('class'))
##                self.assertEqual(element.find_element_by_link_text('Library').get_attribute('href'), '%s%s' % (self.live_server_url, reverse('tile_library:statistics')))
##                
##            else:
##                self.assertTrue('active' in element.get_attribute('class'))
##                #This will throw an error if the link does not exist
##                self.assertEqual(element.find_element_by_link_text('Other').get_attribute('href'), '%s#' % (self.selenium.current_url))
##                
##    def test_other_chr_statistics_view_hrefs(self):
##        gen_stats.initialize(silent=True)
##        self.selenium.get('%s%s' % (self.live_server_url, reverse('tile_library:chr_statistics', args=(26,))))
##        elements = self.selenium.find_element_by_class_name("table-responsive").find_elements_by_tag_name('tr')
##        
##        self.assertEqual(len(elements), 2+Tile.CHR_PATH_LENGTHS[26]-Tile.CHR_PATH_LENGTHS[25])
##        for i, element in enumerate(elements):
##            self.assertTrue(element.is_displayed())
##            if i > 1:
##                self.assertEqual(element.find_element_by_tag_name('a').get_attribute('href'), '%s%s' % (self.live_server_url,
##                                                                                                        reverse('tile_library:path_statistics', args=(26,i-2+Tile.CHR_PATH_LENGTHS[25]))))
##
##    def test_path_statistics_breadcrumbs(self):
##        self.selenium.get('%s%s' % (self.live_server_url, reverse('tile_library:path_statistics', args=(1,0))))
##        elements = self.selenium.find_element_by_class_name("breadcrumb").find_elements_by_tag_name('li')
##        self.assertEqual(len(elements), 4)
##        for element in elements:
##            self.assertTrue(element.is_displayed())
##            if element.text == 'Home':
##                self.assertFalse('active' in element.get_attribute('class'))
##                self.assertEqual(element.find_element_by_link_text('Home').get_attribute('href'), '%s/' % (self.live_server_url))
##                
##            elif element.text == 'Library':
##                self.assertFalse('active' in element.get_attribute('class'))
##                self.assertEqual(element.find_element_by_link_text('Library').get_attribute('href'), '%s%s' % (self.live_server_url, reverse('tile_library:statistics')))
##                
##            elif element.text == 'chr1':
##                self.assertFalse('active' in element.get_attribute('class'))
##                self.assertEqual(element.find_element_by_link_text('chr1').get_attribute('href'), '%s%s' % (self.live_server_url, reverse('tile_library:chr_statistics', args=(1,))))
##            else:
##                self.assertTrue('active' in element.get_attribute('class'))
##                #This will throw an error if the link does not exist
##                self.assertEqual(element.find_element_by_link_text('Path 0').get_attribute('href'), '%s#' % (self.selenium.current_url))
##
##    def test_path_statistics_view_no_statistics(self):
##        self.selenium.get('%s%s' % (self.live_server_url, reverse('tile_library:path_statistics', args=(1,0))))
##        #check that path 0 title shows the 0
##        
##        title_element = self.selenium.find_element_by_class_name("page-header").find_element_by_tag_name('h1')
##        self.assertTrue('Path 0' in title_element.text)
##
##        #check that pagination and all tables are hidden if no statistics available
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        for element in elements:
##            self.assertFalse(element.is_displayed())
##
##        elements = self.selenium.find_elements_by_class_name("pagination")
##        for element in elements:
##            self.assertFalse(element.is_displayed())
##            
##    def test_path_statistics_view_no_positions(self):
##        gen_stats.initialize(silent=True)
##        self.selenium.get('%s%s' % (self.live_server_url, reverse('tile_library:path_statistics', args=(1,1))))
##
##        #check that pagination and second table is hidden if no positions available
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 2)
##        for i, element in enumerate(elements):
##            if i == 0:
##                self.assertTrue(element.is_displayed())
##            else:
##                self.assertFalse(element.is_displayed())
##                
##        elements = self.selenium.find_elements_by_class_name("pagination")
##        for element in elements:
##            self.assertFalse(element.is_displayed())
##            
##    #For tile_view, no hrefs (other than snps, which don't have clear testing) are checkable outside the breadcrumbs
##    def test_tile_view_breadcrumbs(self):
##        self.selenium.get('%s%s' % (self.live_server_url, reverse('tile_library:tile_view', args=(1,0,0))))
##        elements = self.selenium.find_element_by_class_name("breadcrumb").find_elements_by_tag_name('li')
##        self.assertEqual(len(elements), 5)
##        for element in elements:
##            self.assertTrue(element.is_displayed())
##            if element.text == 'Home':
##                self.assertFalse('active' in element.get_attribute('class'))
##                self.assertEqual(element.find_element_by_link_text('Home').get_attribute('href'), '%s/' % (self.live_server_url))
##                
##            elif element.text == 'Library':
##                self.assertFalse('active' in element.get_attribute('class'))
##                self.assertEqual(element.find_element_by_link_text('Library').get_attribute('href'), '%s%s' % (self.live_server_url, reverse('tile_library:statistics')))
##                
##            elif element.text == 'chr1':
##                self.assertFalse('active' in element.get_attribute('class'))
##                self.assertEqual(element.find_element_by_link_text('chr1').get_attribute('href'), '%s%s' % (self.live_server_url, reverse('tile_library:chr_statistics', args=(1,))))
##
##            elif element.text == 'Path 0':
##                self.assertFalse('active' in element.get_attribute('class'))
##                self.assertEqual(element.find_element_by_link_text('Path 0').get_attribute('href'), '%s%s' % (self.live_server_url, reverse('tile_library:path_statistics', args=(1,0))))
##
##            else:
##                self.assertTrue('active' in element.get_attribute('class'))
##                #This will throw an error if the link does not exist
##                self.assertEqual(element.find_element_by_link_text('Tile 000.00.0000').get_attribute('href'), '%s#' % (self.selenium.current_url))
##
##    def test_gene_path_view_breadcrumbs(self):
##        make_long_gene1()
##        gene_id = GeneXRef.objects.all().first().id
##        self.selenium.get('%s%s' % (self.live_server_url, reverse('tile_library:gene_view', args=(gene_id,))))
##        elements = self.selenium.find_element_by_class_name("breadcrumb").find_elements_by_tag_name('li')
##        self.assertEqual(len(elements), 4)
##        for element in elements:
##            self.assertTrue(element.is_displayed())
##            if element.text == 'Home':
##                self.assertFalse('active' in element.get_attribute('class'))
##                self.assertEqual(element.find_element_by_link_text('Home').get_attribute('href'), '%s/' % (self.live_server_url))
##                
##            elif element.text == 'Library':
##                self.assertFalse('active' in element.get_attribute('class'))
##                self.assertEqual(element.find_element_by_link_text('Library').get_attribute('href'), '%s%s' % (self.live_server_url, reverse('tile_library:statistics')))
##                
##            elif element.text == 'chr1':
##                self.assertFalse('active' in element.get_attribute('class'))
##                self.assertEqual(element.find_element_by_link_text('chr1').get_attribute('href'), '%s%s' % (self.live_server_url, reverse('tile_library:chr_statistics', args=(1,))))
##
##            else:
##                self.assertTrue('active' in element.get_attribute('class'))
##                #This will throw an error if the link does not exist
##                self.assertEqual(element.find_element_by_link_text('Gene gene1').get_attribute('href'), '%s#' % (self.selenium.current_url))
##
##    #Gene view does not require statistics to be run, so don't need to test for that behavior
##    def test_gene_path_view_change_view_buttons(self):
##        make_long_gene1()
##        gene_id = GeneXRef.objects.all().first().id
##        gene_name = GeneXRef.objects.all().first().gene_aliases
##        self.selenium.get('%s%s' % (self.live_server_url, reverse('tile_library:gene_view', args=(gene_id,))))
##        elements = self.selenium.find_element_by_class_name("page-header").find_elements_by_class_name('btn-default')
##        self.assertEqual(len(elements), 3)
##        for element in elements:
##            self.assertTrue(element.is_displayed())
##            if element.text == 'Generic View':
##                self.assertFalse('active' in element.get_attribute('class'))
##                self.assertEqual(element.get_attribute('href'), '%s%s' % (self.live_server_url, reverse('genes:specific', args=(gene_id,))))
##                
##            elif element.text == 'Map View':
##                self.assertFalse('active' in element.get_attribute('class'))
##                self.assertEqual(element.get_attribute('href'), '%s%s?exact=%s' % (self.live_server_url, reverse('slippy:slippymap'), gene_name))
##
##            else:
##                self.assertTrue('active' in element.get_attribute('class'))
##                self.assertTrue('disabled' in element.get_attribute('class'))
##                #This will throw an error if the link does not exist
##                self.assertEqual(element.get_attribute('href'), '%s' % (self.selenium.current_url))
##
##    def test_gene_path_view_no_positions(self):
##        make_long_gene1()
##        gene_id = GeneXRef.objects.all().first().id
##        self.selenium.get('%s%s' % (self.live_server_url, reverse('tile_library:gene_view', args=(gene_id,))))
##
##        #check that pagination and table is hidden if no positions available
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 1)
##        for element in elements:
##            self.assertFalse(element.is_displayed())
##                
##        elements = self.selenium.find_elements_by_class_name("pagination")
##        for element in elements:
##            self.assertFalse(element.is_displayed())
##
##    def test_gene_path_view_exons_colored_positions(self):
##        make_tiles()
##        make_long_gene1()
##        gene_id = GeneXRef.objects.all().first().id
##        self.selenium.get('%s%s' % (self.live_server_url, reverse('tile_library:gene_view', args=(gene_id,))))
##        gene_id = GeneXRef.objects.all().first().id
##
##        #Check that 1 table exists and is visible. Check new rows for exon
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 1)
##        for element in elements:
##            self.assertTrue(element.is_displayed())
##            table_rows = element.find_elements_by_tag_name('tr')
##            self.assertEqual(len(table_rows[1:]), 16)
##            for j, row in enumerate(table_rows[1:]):
##                self.assertEqual('success' in row.get_attribute('class'), LONG_GENE1_CHECK_DICT[j])
##        #Switch pages to check the other 2
##        pagination_element = self.selenium.find_element_by_class_name("pagination")
##        pagination_element.find_elements_by_tag_name('li')[1].find_element_by_tag_name('a').click()
##
##        #Check that 1 table exist and is visible. Check new rows for exon
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 1)
##        for i, element in enumerate(elements):
##            self.assertTrue(element.is_displayed())
##            table_rows = element.find_elements_by_tag_name('tr')
##            self.assertEqual(len(table_rows[1:]), 2)
##            for j, row in enumerate(table_rows[1:]):
##                self.assertEqual('success' in row.get_attribute('class'), LONG_GENE1_CHECK_DICT[j+16])
##
##    def test_gene_path_view_smaller_exons_colored_positions(self):
##        make_tiles()
##        make_gene1()
##        gene_id = GeneXRef.objects.all().first().id
##        self.selenium.get('%s%s' % (self.live_server_url, reverse('tile_library:gene_view', args=(gene_id,))))
##
##        #Check that 1 table exists and is visible. Check new rows for exon
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 1)
##        check_dict = {1:True, 2:False, 3:False, 4:True, 5:True}
##        for element in elements:
##            self.assertTrue(element.is_displayed())
##            table_rows = element.find_elements_by_tag_name('tr')
##            self.assertEqual(len(table_rows[1:]), 5)
##            for j, row in enumerate(table_rows[1:]):
##                self.assertEqual('success' in row.get_attribute('class'), check_dict[j+1])
##        #Check pagination elements exist, are visible, and link correctly
##        elements = self.selenium.find_elements_by_class_name("pagination")
##        self.assertEqual(len(elements),2)
##        for element in elements:
##            self.assertTrue(element.is_displayed())
##            pages = element.find_elements_by_tag_name('li')
##            self.assertEqual(len(pages), 1)
##            for i, page in enumerate(pages):
##                self.assertTrue(page.is_displayed())
##                self.assertEqual(page.find_element_by_tag_name('a').get_attribute('href'), '%s#' % (self.selenium.current_url))
##
##    def test_gene_path_view_multiple_exons_colored_positions(self):
##        make_tiles()
##        make_long_gene1()
##        make_gene1pt5()
##        gene_id = GeneXRef.objects.all().first().id
##        self.selenium.get('%s%s' % (self.live_server_url, reverse('tile_library:gene_view', args=(gene_id,))))
##        gene_id = GeneXRef.objects.all().first().id
##
##        #Check that 1 table exists and is visible. Check new rows for exon
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 1)
##        check_dict = LONG_GENE1_CHECK_DICT
##        check_dict[2] = True
##        for element in elements:
##            self.assertTrue(element.is_displayed())
##            table_rows = element.find_elements_by_tag_name('tr')
##            self.assertEqual(len(table_rows[1:]), 16)
##            for j, row in enumerate(table_rows[1:]):
##                self.assertEqual('success' in row.get_attribute('class'), check_dict[j])
##        
##        pagination_element = self.selenium.find_element_by_class_name("pagination")
##        pagination_element.find_elements_by_tag_name('li')[1].find_element_by_tag_name('a').click()
##
##        #Check that 1 table exists and is visible. Check new rows for exon
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 1)
##        for i, element in enumerate(elements):
##            self.assertTrue(element.is_displayed())
##            table_rows = element.find_elements_by_tag_name('tr')
##            self.assertEqual(len(table_rows[1:]), 2)
##            for j, row in enumerate(table_rows[1:]):
##                self.assertEqual('success' in row.get_attribute('class'), check_dict[j+16])
##
##    def test_gene_path_view_multiple_short_exons_colored_positions(self):
##        make_tiles()
##        make_gene1()
##        make_gene1pt5()
##        gene_id = GeneXRef.objects.all().first().id
##        self.selenium.get('%s%s' % (self.live_server_url, reverse('tile_library:gene_view', args=(gene_id,))))
##
##        #Check that 1 table exists and is visible. Check new rows for exon
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 1)
##        check_dict = {1:True, 2:True, 3:False, 4:True, 5:True}
##        for element in elements:
##            self.assertTrue(element.is_displayed())
##            table_rows = element.find_elements_by_tag_name('tr')
##            self.assertEqual(len(table_rows[1:]), 5)
##            for j, row in enumerate(table_rows[1:]):
##                self.assertEqual('success' in row.get_attribute('class'), check_dict[j+1])
##
##        
##    def test_gene_tile_statistics_in_gene_breadcrumbs(self):
##        make_tiles()
##        make_gene1()
##        gene_id = GeneXRef.objects.all().first().id
##        self.selenium.get('%s%s' % (self.live_server_url, reverse('tile_library:tile_in_gene_view', args=(gene_id,1))))
##        elements = self.selenium.find_element_by_class_name("breadcrumb").find_elements_by_tag_name('li')
##        self.assertEqual(len(elements), 5)
##        for element in elements:
##            self.assertTrue(element.is_displayed())
##            if element.text == 'Home':
##                self.assertFalse('active' in element.get_attribute('class'))
##                self.assertEqual(element.find_element_by_link_text('Home').get_attribute('href'), '%s/' % (self.live_server_url))
##                
##            elif element.text == 'Library':
##                self.assertFalse('active' in element.get_attribute('class'))
##                self.assertEqual(element.find_element_by_link_text('Library').get_attribute('href'), '%s%s' % (self.live_server_url, reverse('tile_library:statistics')))
##                
##            elif element.text == 'chr1':
##                self.assertFalse('active' in element.get_attribute('class'))
##                self.assertEqual(element.find_element_by_link_text('chr1').get_attribute('href'), '%s%s' % (self.live_server_url, reverse('tile_library:chr_statistics', args=(1,))))
##
##            elif element.text == 'Gene gene1':
##                self.assertFalse('active' in element.get_attribute('class'))
##                self.assertEqual(element.find_element_by_link_text('Gene gene1').get_attribute('href'), '%s%s' % (self.live_server_url, reverse('tile_library:gene_view', args=(gene_id,))))
##
##            else:
##                self.assertTrue('active' in element.get_attribute('class'))
##                #This will throw an error if the link does not exist
##                self.assertEqual(element.find_element_by_link_text('Tile 000.00.0001').get_attribute('href'), '%s#' % (self.selenium.current_url))
##
##    def test_gene_tile_statistics_not_in_gene_breadcrumbs(self):
##        make_tiles()
##        make_gene1()
##        gene_id = GeneXRef.objects.all().first().id
##        self.selenium.get('%s%s' % (self.live_server_url, reverse('tile_library:tile_in_gene_view', args=(gene_id,2))))
##        elements = self.selenium.find_element_by_class_name("breadcrumb").find_elements_by_tag_name('li')
##        self.assertEqual(len(elements), 5)
##        for element in elements:
##            self.assertTrue(element.is_displayed())
##            if element.text == 'Home':
##                self.assertFalse('active' in element.get_attribute('class'))
##                self.assertEqual(element.find_element_by_link_text('Home').get_attribute('href'), '%s/' % (self.live_server_url))
##                
##            elif element.text == 'Library':
##                self.assertFalse('active' in element.get_attribute('class'))
##                self.assertEqual(element.find_element_by_link_text('Library').get_attribute('href'), '%s%s' % (self.live_server_url, reverse('tile_library:statistics')))
##                
##            elif element.text == 'chr1':
##                self.assertFalse('active' in element.get_attribute('class'))
##                self.assertEqual(element.find_element_by_link_text('chr1').get_attribute('href'), '%s%s' % (self.live_server_url, reverse('tile_library:chr_statistics', args=(1,))))
##
##            elif element.text == 'Gene gene1':
##                self.assertFalse('active' in element.get_attribute('class'))
##                self.assertEqual(element.find_element_by_link_text('Gene gene1').get_attribute('href'), '%s%s' % (self.live_server_url, reverse('tile_library:gene_view', args=(gene_id,))))
##
##            else:
##                self.assertTrue('active' in element.get_attribute('class'))
##                #This will throw an error if the link does not exist
##                self.assertEqual(element.find_element_by_link_text('Tile 000.00.0002').get_attribute('href'), '%s#' % (self.selenium.current_url))
##
##    def test_gene_tile_view_fast_nav(self):
##        #check buttons for swapping
##        make_tiles()
##        make_gene1()
##        gene_id = GeneXRef.objects.all().first().id
##        self.selenium.get('%s%s' % (self.live_server_url, reverse('tile_library:tile_in_gene_view', args=(gene_id,1))))
##        title = self.selenium.find_element_by_class_name("page-header").find_element_by_tag_name('h1').text
##        self.assertEqual(title, 'Tile Position 000.00.0001 (Path 0, chr1p36.33, Gene gene1)')
##        elements = self.selenium.find_element_by_class_name("page-header").find_elements_by_tag_name('a')
##        self.assertEqual(len(elements), 2)
##        self.assertTrue('disabled' in elements[0].get_attribute('class'))
##        self.assertFalse('disabled' in elements[1].get_attribute('class'))
##        elements[1].click()
##        for i in range(3):
##            title = self.selenium.find_element_by_class_name("page-header").find_element_by_tag_name('h1').text
##            self.assertEqual(title, 'Tile Position 000.00.000%i (Path 0, chr1p36.33, Gene gene1)' % (i+2))
##            elements = self.selenium.find_element_by_class_name("page-header").find_elements_by_tag_name('a')
##            self.assertEqual(len(elements), 2)
##            self.assertFalse('disabled' in elements[0].get_attribute('class'))
##            self.assertFalse('disabled' in elements[1].get_attribute('class'))
##            elements[1].click()
##        title = self.selenium.find_element_by_class_name("page-header").find_element_by_tag_name('h1').text
##        self.assertEqual(title, 'Tile Position 000.00.0005 (Path 0, chr1p36.33, Gene gene1)')
##        elements = self.selenium.find_element_by_class_name("page-header").find_elements_by_tag_name('a')
##        self.assertEqual(len(elements), 2)
##        self.assertFalse('disabled' in elements[0].get_attribute('class'))
##        self.assertTrue('disabled' in elements[1].get_attribute('class'))
##        elements[0].click()
##        title = self.selenium.find_element_by_class_name("page-header").find_element_by_tag_name('h1').text
##        self.assertEqual(title, 'Tile Position 000.00.0004 (Path 0, chr1p36.33, Gene gene1)')
##        
##
##    def test_gene_tile_in_gene_view_exon_splicing_table(self):
##        #check Exon Splicing table exist
##        make_tiles()
##        make_gene1pt5()
##        gene_id = GeneXRef.objects.all().first().id
##        self.selenium.get('%s%s' % (self.live_server_url, reverse('tile_library:tile_in_gene_view', args=(gene_id,2))))
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 2)
##        for i, element in enumerate(elements):
##            self.assertTrue(element.is_displayed())
##            table_rows = element.find_elements_by_tag_name('tr')
##            if i == 0:    
##                self.assertEqual(len(table_rows[1:]), 2)
##            else:
##                self.assertEqual(len(table_rows[1:]), 3)
##                
##    def test_gene_tile_in_gene_view_exon_splicing_table_multiple_genes(self):
##        #check Exon Splicing table exist
##        make_tiles()
##        make_gene1()
##        make_gene1pt5()
##        gene_id = GeneXRef.objects.all().first().id
##        self.selenium.get('%s%s' % (self.live_server_url, reverse('tile_library:tile_in_gene_view', args=(gene_id,1))))
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 2)
##        for i, element in enumerate(elements):
##            self.assertTrue(element.is_displayed())
##            table_rows = element.find_elements_by_tag_name('tr')
##            if i == 0:    
##                self.assertEqual(len(table_rows[1:]), 3)
##            else:
##                self.assertEqual(len(table_rows[1:]), 2)
##
##    def test_gene_tile_not_in_gene_view_splicing_table_nonexistant(self):
##        #check Exon Splicing table does not exist
##        make_tiles()
##        make_gene1()
##        gene_id = GeneXRef.objects.all().first().id
##        self.selenium.get('%s%s' % (self.live_server_url, reverse('tile_library:tile_in_gene_view', args=(gene_id,2))))
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 1)
##        for i, element in enumerate(elements):
##            table_rows = element.find_elements_by_tag_name('tr')
##            self.assertTrue(element.is_displayed())
##            self.assertEqual(len(table_rows[1:]), 3)
##
##class TestGeneViewInteractive(StaticLiveServerTestCase):
##    #long_gene1 contains all 17 tiles
##    @classmethod
##    def setUpClass(cls):
##        cls.selenium = webdriver.PhantomJS()
##        super(TestGeneViewInteractive, cls).setUpClass()
##
##    @classmethod
##    def tearDownClass(cls):
##        cls.selenium.quit()
##        super(TestGeneViewInteractive, cls).tearDownClass()
##        
##    def setUp(self):
##        make_tiles()
##        make_long_gene1()
##        gene_id = GeneXRef.objects.all().first().id
##        self.selenium.get('%s%s' % (self.live_server_url, reverse('tile_library:gene_view', args=(gene_id,))))
##        super(TestGeneViewInteractive, self).setUp()
##            
##    def test_view_native_full_page(self):
##        gene_id = GeneXRef.objects.all().first().id
##        #Check that 1 table exists and is visible. Check that hrefs in table link correctly
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 1)
##        for element in elements:
##            self.assertTrue(element.is_displayed())
##            table_rows = element.find_elements_by_tag_name('tr')
##            self.assertEqual(len(table_rows[1:]), 16)
##            for j, row in enumerate(table_rows[1:]):
##                self.assertEqual(row.find_element_by_tag_name('a').get_attribute('href'), '%s%s' % (self.live_server_url,
##                                                                                                    reverse('tile_library:tile_in_gene_view', args=(gene_id,j))))
##                    
##        #Check pagination elements exist, are visible, and link correctly
##        elements = self.selenium.find_elements_by_class_name("pagination")
##        self.assertEqual(len(elements),2)
##        for element in elements:
##            self.assertTrue(element.is_displayed())
##            pages = element.find_elements_by_tag_name('li')
##            self.assertEqual(len(pages), 2)
##            for i, page in enumerate(pages):
##                self.assertTrue(page.is_displayed())
##                if i == 0:
##                    self.assertEqual(page.find_element_by_tag_name('a').get_attribute('href'), '%s#' % (self.selenium.current_url))
##                else:
##                    self.assertEqual(page.find_element_by_tag_name('a').get_attribute('href'), '%s%s?page=2' % (self.live_server_url, reverse('tile_library:gene_view', args=(gene_id,))))
##    
##    def test_go_to_page_native_view(self):
##        gene_id = GeneXRef.objects.all().first().id
##        #Go to next page (using top pagination)
##        pagination_element = self.selenium.find_element_by_class_name("pagination")
##        pagination_element.find_elements_by_tag_name('li')[1].find_element_by_tag_name('a').click()
##
##        #Check that 1 table exist and is visible. Check new hrefs for correctness
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 1)
##        for i, element in enumerate(elements):
##            self.assertTrue(element.is_displayed())
##            table_rows = element.find_elements_by_tag_name('tr')
##            self.assertEqual(len(table_rows[1:]), 2)
##            for j, row in enumerate(table_rows[1:]):
##                self.assertEqual(row.find_element_by_tag_name('a').get_attribute('href'), '%s%s' % (self.live_server_url,
##                                                                                                    reverse('tile_library:tile_in_gene_view', args=(gene_id,j+16))))
##
##        #Check pagination elements exist, are visible, and link correctly
##        elements = self.selenium.find_elements_by_class_name("pagination")
##        self.assertEqual(len(elements),2)
##        for element in elements:
##            self.assertTrue(element.is_displayed())
##            pages = element.find_elements_by_tag_name('li')
##            self.assertEqual(len(pages), 2)
##            for i, page in enumerate(pages):
##                self.assertTrue(page.is_displayed())
##                if i == 0:
##                    self.assertEqual(page.find_element_by_tag_name('a').get_attribute('href'), '%s%s?page=1' % (self.live_server_url, reverse('tile_library:gene_view', args=(gene_id,)))) 
##                else:
##                    self.assertEqual(page.find_element_by_tag_name('a').get_attribute('href'), '%s#' % (self.selenium.current_url))
##        #Go to prev page (using lower pagination)
##        pagination_element = elements[1]
##        pagination_element.find_elements_by_tag_name('li')[0].find_element_by_tag_name('a').click()
##
##        #Check this page has first tables
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 1)
##        for i, element in enumerate(elements):
##            self.assertTrue(element.is_displayed())
##            table_rows = element.find_elements_by_tag_name('tr')
##            self.assertEqual(len(table_rows[1:]), 16)
##            for j, row in enumerate(table_rows[1:]):
##                self.assertEqual(row.find_element_by_tag_name('a').get_attribute('href'), '%s%s' % (self.live_server_url,
##                                                                                                    reverse('tile_library:tile_in_gene_view', args=(gene_id,j))))
##    def test_sort_by_desc_position(self):
##        gene_id = GeneXRef.objects.all().first().id
##        #Click button to sort the table contents by ascending position
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        table_buttons = elements[0].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('button')
##        table_buttons[0].click()
##        elements[0].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('a')[1].click()
##        
##        #Check the table has the requested order (descending position)
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 1)
##        for i, element in enumerate(elements):
##            self.assertTrue(element.is_displayed())
##            table_rows = element.find_elements_by_tag_name('tr')
##            self.assertEqual(len(table_rows[1:]), 16)
##            for j, row in enumerate(table_rows[1:]):
##                self.assertEqual(row.find_element_by_tag_name('a').get_attribute('href'), '%s%s' % (self.live_server_url,
##                                                                                                    reverse('tile_library:tile_in_gene_view', args=(gene_id,j))))
##
##    def test_sort_by_ascending_position(self):
##        gene_id = GeneXRef.objects.all().first().id
##        #Click button to sort the table contents by ascending position
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        table_buttons = elements[0].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('button')
##        table_buttons[0].click()
##        elements[0].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('a')[0].click()
##
##        #Check the table has the requested order (ascending position)
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 1)
##        for i, element in enumerate(elements):
##            self.assertTrue(element.is_displayed())
##            table_rows = element.find_elements_by_tag_name('tr')
##            self.assertEqual(len(table_rows[1:]), 16)
##            for j, row in enumerate(table_rows[1:]):
##                self.assertEqual(row.find_element_by_tag_name('a').get_attribute('href'), '%s%s' % (self.live_server_url,
##                                                                                                    reverse('tile_library:tile_in_gene_view', args=(gene_id,17-j))))
##
##    def test_sort_by_desc_min_len(self):
##        gene_id = GeneXRef.objects.all().first().id
##        #Click button to sort the table contents by descending minimum length
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        table_buttons = elements[0].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('button')
##        table_buttons[2].click()
##        elements[0].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('a')[4].click()
##        
##        #Check the table has the requested order (descending minimum length)
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 1)
##        for i, element in enumerate(elements):
##            self.assertTrue(element.is_displayed())
##            table_rows = element.find_elements_by_tag_name('tr')
##            self.assertEqual(len(table_rows[1:]), 16)
##            prev = 1300
##            for j, row in enumerate(table_rows[1:]):
##                curr = row.find_elements_by_tag_name('td')[3].text.strip()
##                if curr == '-':
##                    #Make sure variant number is 1 if the length is displayed as '-'
##                    self.assertEqual(int(row.find_elements_by_tag_name('td')[1].text.strip()), 1)
##                    curr = int(row.find_elements_by_tag_name('td')[2].text.strip())
##                else:
##                    curr = int(curr)
##                self.assertGreaterEqual(prev, curr)
##                prev = curr
##
##    def test_sort_by_ascending_min_len(self):
##        gene_id = GeneXRef.objects.all().first().id
##        #Click button to sort the table contents by ascending minimum length
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        table_buttons = elements[0].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('button')
##        table_buttons[2].click()
##        elements[0].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('a')[5].click()
##        
##        #Check the table has the requested order (ascending minimum length)
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 1)
##        for i, element in enumerate(elements):
##            self.assertTrue(element.is_displayed())
##            table_rows = element.find_elements_by_tag_name('tr')
##            self.assertEqual(len(table_rows[1:]), 16)
##            prev = 0
##            for j, row in enumerate(table_rows[1:]):
##                curr = row.find_elements_by_tag_name('td')[3].text.strip()
##                if curr == '-':
##                    #Make sure variant number is 1 if the length is displayed as '-'
##                    self.assertEqual(int(row.find_elements_by_tag_name('td')[1].text.strip()), 1)
##                    curr = int(row.find_elements_by_tag_name('td')[2].text.strip())
##                else:
##                    curr = int(curr)
##                self.assertLessEqual(prev, curr)
##                prev = curr
##    
##    def test_sort_by_desc_avg_len(self):
##        gene_id = GeneXRef.objects.all().first().id
##        #Click button to sort the table contents by descending minimum length
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        table_buttons = elements[0].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('button')
##        table_buttons[3].click()
##        elements[0].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('a')[6].click()
##        
##        #Check the table has the requested order (descending minimum length)
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 1)
##        for i, element in enumerate(elements):
##            self.assertTrue(element.is_displayed())
##            table_rows = element.find_elements_by_tag_name('tr')
##            self.assertEqual(len(table_rows[1:]), 16)
##            prev = 1300
##            for j, row in enumerate(table_rows[1:]):
##                curr = row.find_elements_by_tag_name('td')[4].text.strip()
##                if curr == '-':
##                    #Make sure variant number is 1 if the length is displayed as '-'
##                    self.assertEqual(int(row.find_elements_by_tag_name('td')[1].text.strip()), 1)
##                    curr = float(row.find_elements_by_tag_name('td')[2].text.strip())
##                else:
##                    curr = float(curr)
##                self.assertGreaterEqual(prev, curr)
##                prev = curr
##
##    def test_sort_by_ascending_avg_len(self):
##        gene_id = GeneXRef.objects.all().first().id
##        #Click button to sort the table contents by ascending minimum length
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        table_buttons = elements[0].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('button')
##        table_buttons[3].click()
##        elements[0].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('a')[7].click()
##        
##        #Check the table has the requested order (ascending minimum length)
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 1)
##        for i, element in enumerate(elements):
##            self.assertTrue(element.is_displayed())
##            table_rows = element.find_elements_by_tag_name('tr')
##            self.assertEqual(len(table_rows[1:]), 16)
##            prev = 0
##            for j, row in enumerate(table_rows[1:]):
##                curr = row.find_elements_by_tag_name('td')[4].text.strip()
##                if curr == '-':
##                    #Make sure variant number is 1 if the length is displayed as '-'
##                    self.assertEqual(int(row.find_elements_by_tag_name('td')[1].text.strip()), 1)
##                    curr = float(row.find_elements_by_tag_name('td')[2].text.strip())
##                else:
##                    curr = float(curr)
##                self.assertLessEqual(prev, curr)
##                prev = curr
##
##    def test_sort_by_desc_max_len(self):
##        gene_id = GeneXRef.objects.all().first().id
##        #Click button to sort the table contents by descending minimum length
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        table_buttons = elements[0].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('button')
##        table_buttons[4].click()
##        elements[0].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('a')[8].click()
##        
##        #Check the table has the requested order (descending minimum length)
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 1)
##        for i, element in enumerate(elements):
##            self.assertTrue(element.is_displayed())
##            table_rows = element.find_elements_by_tag_name('tr')
##            self.assertEqual(len(table_rows[1:]), 16)
##            prev = 1300
##            for j, row in enumerate(table_rows[1:]):
##                curr = row.find_elements_by_tag_name('td')[5].text.strip()
##                if curr == '-':
##                    #Make sure variant number is 1 if the length is displayed as '-'
##                    self.assertEqual(int(row.find_elements_by_tag_name('td')[1].text.strip()), 1)
##                    curr = int(row.find_elements_by_tag_name('td')[2].text.strip())
##                else:
##                    curr = int(curr)
##                self.assertGreaterEqual(prev, curr)
##                prev = curr
##
##    def test_sort_by_ascending_max_len(self):
##        gene_id = GeneXRef.objects.all().first().id
##        #Click button to sort the table contents by ascending minimum length
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        table_buttons = elements[0].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('button')
##        table_buttons[4].click()
##        elements[0].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('a')[9].click()
##        
##        #Check the table has the requested order (ascending minimum length)
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 1)
##        for i, element in enumerate(elements):
##            self.assertTrue(element.is_displayed())
##            table_rows = element.find_elements_by_tag_name('tr')
##            self.assertEqual(len(table_rows[1:]), 16)
##            prev = 0
##            for j, row in enumerate(table_rows[1:]):
##                curr = row.find_elements_by_tag_name('td')[5].text.strip()
##                if curr == '-':
##                    #Make sure variant number is 1 if the length is displayed as '-'
##                    self.assertEqual(int(row.find_elements_by_tag_name('td')[1].text.strip()), 1)
##                    curr = int(row.find_elements_by_tag_name('td')[2].text.strip())
##                else:
##                    curr = int(curr)
##                self.assertLessEqual(prev, curr)
##                prev = curr
##    
##    def test_sort_by_desc_var(self):
##        gene_id = GeneXRef.objects.all().first().id
##        #Click button to sort the table contents by descending number of variants
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        table_buttons = elements[0].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('button')
##        table_buttons[1].click()
##        elements[0].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('a')[2].click()
##
##        #Check the table has the requested order (descending number of variants)!
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 1)
##        for i, element in enumerate(elements):
##            self.assertTrue(element.is_displayed())
##            if i > 0:
##                table_rows = element.find_elements_by_tag_name('tr')
##                self.assertEqual(len(table_rows[1:]), 16)
##                prev = 10
##                for row in table_rows[1:]:
##                    curr = int(row.find_elements_by_tag_name('td')[1].text.strip())
##                    self.assertGreaterEqual(prev, curr)
##                    prev = curr
##                    
##    def test_sort_by_asc_var_and_change_page(self):
##        gene_id = GeneXRef.objects.all().first().id
##        #Click button to sort the table contents by ascending number of variants
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        table_buttons = elements[0].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('button')
##        table_buttons[1].click()
##        elements[0].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('a')[3].click()
##
##        #Check the table has the requested order(ascending number of variants)!
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 1)
##        for i, element in enumerate(elements):
##            self.assertTrue(element.is_displayed())
##            table_rows = element.find_elements_by_tag_name('tr')
##            self.assertEqual(len(table_rows[1:]), 16)
##            prev = 0
##            for row in table_rows[1:]:
##                curr = int(row.find_elements_by_tag_name('td')[1].text.strip())
##                self.assertLessEqual(prev, curr)
##                prev = curr
##        
##        #Go to next page (using lower pagination)
##        pagination_element = self.selenium.find_elements_by_class_name("pagination")[1]
##        pagination_element.find_elements_by_tag_name('li')[1].find_element_by_tag_name('a').click()
##
##        #Check the table has the requested order (still ascending number of variants)!
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 1)
##        for i, element in enumerate(elements):
##            self.assertTrue(element.is_displayed())
##            table_rows = element.find_elements_by_tag_name('tr')
##            self.assertEqual(len(table_rows[1:]), 2)
##            for row in table_rows[1:]:
##                curr = int(row.find_elements_by_tag_name('td')[1].text.strip())
##                self.assertLessEqual(prev, curr)
##                prev = curr
##
##class TestViewPopulatedPathInteractive(StaticLiveServerTestCase):
##    fixtures = ['test_view_paths.json']
##    
##    @classmethod
##    def setUpClass(cls):
##        cls.selenium = webdriver.PhantomJS()
##        super(TestViewPopulatedPathInteractive, cls).setUpClass()
##
##    @classmethod
##    def tearDownClass(cls):
##        cls.selenium.quit()
##        super(TestViewPopulatedPathInteractive, cls).tearDownClass()
##
##    def setUp(self):
##        gen_stats.initialize(silent=True)
##        self.selenium.get('%s%s' % (self.live_server_url, reverse('tile_library:path_statistics', args=(1,0))))
##        super(TestViewPopulatedPathInteractive, self).setUp()
##
##    def test_view_native_full_page(self):
##        #Check that 2 tables exist and are visible. Check that hrefs in second table link correctly
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 2)
##        for i, element in enumerate(elements):
##            self.assertTrue(element.is_displayed())
##            if i > 0:
##                table_rows = element.find_elements_by_tag_name('tr')
##                self.assertEqual(len(table_rows[1:]), 16)
##                for j, row in enumerate(table_rows[1:]):
##                    self.assertEqual(row.find_element_by_tag_name('a').get_attribute('href'), '%s%s' % (self.live_server_url,
##                                                                                                        reverse('tile_library:tile_view', args=(1,0,j))))
##                    
##        #Check pagination elements exist, are visible, and link correctly
##        elements = self.selenium.find_elements_by_class_name("pagination")
##        self.assertEqual(len(elements),2)
##        for element in elements:
##            self.assertTrue(element.is_displayed())
##            pages = element.find_elements_by_tag_name('li')
##            self.assertEqual(len(pages), 2)
##            for i, page in enumerate(pages):
##                self.assertTrue(page.is_displayed())
##                if i == 0:
##                    self.assertEqual(page.find_element_by_tag_name('a').get_attribute('href'), '%s#' % (self.selenium.current_url))
##                else:
##                    self.assertEqual(page.find_element_by_tag_name('a').get_attribute('href'), '%s%s?page=2' % (self.live_server_url, reverse('tile_library:path_statistics', args=(1,0))))
##    
##    def test_go_to_page_native_view(self):
##        #Go to next page (using top pagination)
##        pagination_element = self.selenium.find_element_by_class_name("pagination")
##        pagination_element.find_elements_by_tag_name('li')[1].find_element_by_tag_name('a').click()
##
##        #Check that 2 tables exist and are visible. Check new hrefs for correctness
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 2)
##        for i, element in enumerate(elements):
##            self.assertTrue(element.is_displayed())
##            if i > 0:
##                table_rows = element.find_elements_by_tag_name('tr')
##                self.assertEqual(len(table_rows[1:]), 1)
##                for j, row in enumerate(table_rows[1:]):
##                    self.assertEqual(row.find_element_by_tag_name('a').get_attribute('href'), '%s%s' % (self.live_server_url,
##                                                                                                        reverse('tile_library:tile_view', args=(1,0,j+16))))
##
##        #Check pagination elements exist, are visible, and link correctly
##        elements = self.selenium.find_elements_by_class_name("pagination")
##        self.assertEqual(len(elements),2)
##        for element in elements:
##            self.assertTrue(element.is_displayed())
##            pages = element.find_elements_by_tag_name('li')
##            self.assertEqual(len(pages), 2)
##            for i, page in enumerate(pages):
##                self.assertTrue(page.is_displayed())
##                if i == 0:
##                    self.assertEqual(page.find_element_by_tag_name('a').get_attribute('href'), '%s%s?page=1' % (self.live_server_url, reverse('tile_library:path_statistics', args=(1,0)))) 
##                else:
##                    self.assertEqual(page.find_element_by_tag_name('a').get_attribute('href'), '%s#' % (self.selenium.current_url))
##        #Go to prev page (using lower pagination)
##        pagination_element = elements[1]
##        pagination_element.find_elements_by_tag_name('li')[0].find_element_by_tag_name('a').click()
##
##        #Check this page has first tables
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 2)
##        for i, element in enumerate(elements):
##            self.assertTrue(element.is_displayed())
##            if i > 0:
##                table_rows = element.find_elements_by_tag_name('tr')
##                self.assertEqual(len(table_rows[1:]), 16)
##                for j, row in enumerate(table_rows[1:]):
##                    self.assertEqual(row.find_element_by_tag_name('a').get_attribute('href'), '%s%s' % (self.live_server_url,
##                                                                                                        reverse('tile_library:tile_view', args=(1,0,j))))
##    def test_sort_by_desc_position(self):
##        #Click button to sort the table contents by ascending position
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        table_buttons = elements[1].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('button')
##        table_buttons[0].click()
##        elements[1].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('a')[1].click()
##        
##        #Check the table has the requested order (descending position)
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 2)
##        for i, element in enumerate(elements):
##            self.assertTrue(element.is_displayed())
##            if i > 0:
##                table_rows = element.find_elements_by_tag_name('tr')
##                self.assertEqual(len(table_rows[1:]), 16)
##                for j, row in enumerate(table_rows[1:]):
##                    self.assertEqual(row.find_element_by_tag_name('a').get_attribute('href'), '%s%s' % (self.live_server_url,
##                                                                                                        reverse('tile_library:tile_view', args=(1,0,j))))
##
##    def test_sort_by_ascending_position(self):
##        #Click button to sort the table contents by ascending position
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        table_buttons = elements[1].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('button')
##        table_buttons[0].click()
##        elements[1].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('a')[0].click()
##
##        #Check the table has the requested order (ascending position)
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 2)
##        for i, element in enumerate(elements):
##            self.assertTrue(element.is_displayed())
##            if i > 0:
##                table_rows = element.find_elements_by_tag_name('tr')
##                self.assertEqual(len(table_rows[1:]), 16)
##                for j, row in enumerate(table_rows[1:]):
##                    self.assertEqual(row.find_element_by_tag_name('a').get_attribute('href'), '%s%s' % (self.live_server_url,
##                                                                                                        reverse('tile_library:tile_view', args=(1,0,16-j))))
##
##    def test_sort_by_desc_min_len(self):
##        #Click button to sort the table contents by descending minimum length
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        table_buttons = elements[1].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('button')
##        table_buttons[2].click()
##        elements[1].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('a')[4].click()
##        
##        #Check the table has the requested order (descending minimum length)
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 2)
##        for i, element in enumerate(elements):
##            self.assertTrue(element.is_displayed())
##            if i > 0:
##                table_rows = element.find_elements_by_tag_name('tr')
##                self.assertEqual(len(table_rows[1:]), 16)
##                prev = 1300
##                for j, row in enumerate(table_rows[1:]):
##                    curr = row.find_elements_by_tag_name('td')[3].text.strip()
##                    if curr == '-':
##                        #Make sure variant number is 1 if the length is displayed as '-'
##                        self.assertEqual(int(row.find_elements_by_tag_name('td')[1].text.strip()), 1)
##                        curr = int(row.find_elements_by_tag_name('td')[2].text.strip())
##                    else:
##                        curr = int(curr)
##                    self.assertGreaterEqual(prev, curr)
##                    prev = curr
##                    
##
##    def test_sort_by_ascending_min_len(self):
##        #Click button to sort the table contents by ascending minimum length
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        table_buttons = elements[1].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('button')
##        table_buttons[2].click()
##        elements[1].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('a')[5].click()
##        
##        #Check the table has the requested order (ascending minimum length)
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 2)
##        for i, element in enumerate(elements):
##            self.assertTrue(element.is_displayed())
##            if i > 0:
##                table_rows = element.find_elements_by_tag_name('tr')
##                self.assertEqual(len(table_rows[1:]), 16)
##                prev = 0
##                for j, row in enumerate(table_rows[1:]):
##                    curr = row.find_elements_by_tag_name('td')[3].text.strip()
##                    if curr == '-':
##                        #Make sure variant number is 1 if the length is displayed as '-'
##                        self.assertEqual(int(row.find_elements_by_tag_name('td')[1].text.strip()), 1)
##                        curr = int(row.find_elements_by_tag_name('td')[2].text.strip())
##                    else:
##                        curr = int(curr)
##                    self.assertLessEqual(prev, curr)
##                    prev = curr
##    
##    def test_sort_by_desc_avg_len(self):
##        #Click button to sort the table contents by descending minimum length
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        table_buttons = elements[1].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('button')
##        table_buttons[3].click()
##        elements[1].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('a')[6].click()
##        
##        #Check the table has the requested order (descending minimum length)
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 2)
##        for i, element in enumerate(elements):
##            self.assertTrue(element.is_displayed())
##            if i > 0:
##                table_rows = element.find_elements_by_tag_name('tr')
##                self.assertEqual(len(table_rows[1:]), 16)
##                prev = 1300
##                for j, row in enumerate(table_rows[1:]):
##                    curr = row.find_elements_by_tag_name('td')[4].text.strip()
##                    if curr == '-':
##                        #Make sure variant number is 1 if the length is displayed as '-'
##                        self.assertEqual(int(row.find_elements_by_tag_name('td')[1].text.strip()), 1)
##                        curr = float(row.find_elements_by_tag_name('td')[2].text.strip())
##                    else:
##                        curr = float(curr)
##                    self.assertGreaterEqual(prev, curr)
##                    prev = curr
##                    
##
##    def test_sort_by_ascending_avg_len(self):
##        #Click button to sort the table contents by ascending minimum length
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        table_buttons = elements[1].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('button')
##        table_buttons[3].click()
##        elements[1].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('a')[7].click()
##        
##        #Check the table has the requested order (ascending minimum length)
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 2)
##        for i, element in enumerate(elements):
##            self.assertTrue(element.is_displayed())
##            if i > 0:
##                table_rows = element.find_elements_by_tag_name('tr')
##                self.assertEqual(len(table_rows[1:]), 16)
##                prev = 0
##                for j, row in enumerate(table_rows[1:]):
##                    curr = row.find_elements_by_tag_name('td')[4].text.strip()
##                    if curr == '-':
##                        #Make sure variant number is 1 if the length is displayed as '-'
##                        self.assertEqual(int(row.find_elements_by_tag_name('td')[1].text.strip()), 1)
##                        curr = float(row.find_elements_by_tag_name('td')[2].text.strip())
##                    else:
##                        curr = float(curr)
##                    self.assertLessEqual(prev, curr)
##                    prev = curr
##
##    def test_sort_by_desc_max_len(self):
##        #Click button to sort the table contents by descending minimum length
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        table_buttons = elements[1].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('button')
##        table_buttons[4].click()
##        elements[1].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('a')[8].click()
##        
##        #Check the table has the requested order (descending minimum length)
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 2)
##        for i, element in enumerate(elements):
##            self.assertTrue(element.is_displayed())
##            if i > 0:
##                table_rows = element.find_elements_by_tag_name('tr')
##                self.assertEqual(len(table_rows[1:]), 16)
##                prev = 1300
##                for j, row in enumerate(table_rows[1:]):
##                    curr = row.find_elements_by_tag_name('td')[5].text.strip()
##                    if curr == '-':
##                        #Make sure variant number is 1 if the length is displayed as '-'
##                        self.assertEqual(int(row.find_elements_by_tag_name('td')[1].text.strip()), 1)
##                        curr = int(row.find_elements_by_tag_name('td')[2].text.strip())
##                    else:
##                        curr = int(curr)
##                    self.assertGreaterEqual(prev, curr)
##                    prev = curr
##                    
##
##    def test_sort_by_ascending_max_len(self):
##        #Click button to sort the table contents by ascending minimum length
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        table_buttons = elements[1].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('button')
##        table_buttons[4].click()
##        elements[1].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('a')[9].click()
##        
##        #Check the table has the requested order (ascending minimum length)
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 2)
##        for i, element in enumerate(elements):
##            self.assertTrue(element.is_displayed())
##            if i > 0:
##                table_rows = element.find_elements_by_tag_name('tr')
##                self.assertEqual(len(table_rows[1:]), 16)
##                prev = 0
##                for j, row in enumerate(table_rows[1:]):
##                    curr = row.find_elements_by_tag_name('td')[5].text.strip()
##                    if curr == '-':
##                        #Make sure variant number is 1 if the length is displayed as '-'
##                        self.assertEqual(int(row.find_elements_by_tag_name('td')[1].text.strip()), 1)
##                        curr = int(row.find_elements_by_tag_name('td')[2].text.strip())
##                    else:
##                        curr = int(curr)
##                    self.assertLessEqual(prev, curr)
##                    prev = curr
##    
##    def test_sort_by_desc_var(self):
##        #Click button to sort the table contents by descending number of variants
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        table_buttons = elements[1].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('button')
##        table_buttons[1].click()
##        elements[1].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('a')[2].click()
##
##        #Check the table has the requested order (descending number of variants)!
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 2)
##        for i, element in enumerate(elements):
##            self.assertTrue(element.is_displayed())
##            if i > 0:
##                table_rows = element.find_elements_by_tag_name('tr')
##                self.assertEqual(len(table_rows[1:]), 16)
##                prev = 10
##                for row in table_rows[1:]:
##                    curr = int(row.find_elements_by_tag_name('td')[1].text.strip())
##                    self.assertGreaterEqual(prev, curr)
##                    prev = curr
##                    
##    def test_sort_by_asc_var_and_change_page(self):
##        #Click button to sort the table contents by ascending number of variants
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        table_buttons = elements[1].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('button')
##        table_buttons[1].click()
##        elements[1].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('a')[3].click()
##
##        #Check the table has the requested order(ascending number of variants)!
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 2)
##        for i, element in enumerate(elements):
##            self.assertTrue(element.is_displayed())
##            if i > 0:
##                table_rows = element.find_elements_by_tag_name('tr')
##                self.assertEqual(len(table_rows[1:]), 16)
##                prev = 0
##                for row in table_rows[1:]:
##                    curr = int(row.find_elements_by_tag_name('td')[1].text.strip())
##                    self.assertLessEqual(prev, curr)
##                    prev = curr
##        
##        #Go to next page (using lower pagination)
##        pagination_element = self.selenium.find_elements_by_class_name("pagination")[1]
##        pagination_element.find_elements_by_tag_name('li')[1].find_element_by_tag_name('a').click()
##
##        #Check the table has the requested order (still ascending number of variants)!
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 2)
##        for i, element in enumerate(elements):
##            self.assertTrue(element.is_displayed())
##            if i > 0:
##                table_rows = element.find_elements_by_tag_name('tr')
##                self.assertEqual(len(table_rows[1:]), 1)
##                for row in table_rows[1:]:
##                    curr = int(row.find_elements_by_tag_name('td')[1].text.strip())
##                    self.assertLessEqual(prev, curr)
##                    prev = curr
