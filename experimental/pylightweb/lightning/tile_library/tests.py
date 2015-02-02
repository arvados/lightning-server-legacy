import random
import hashlib
import string
import subprocess
from unittest import skip

from django.test import TestCase, LiveServerTestCase
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core.urlresolvers import reverse
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError

from errors import MissingStatisticsError, InvalidGenomeError, ExistingStatisticsError
from tile_library.models import TAG_LENGTH, Tile, TileLocusAnnotation, TileVariant, GenomeVariant, GenomeVariantTranslation, GenomeStatistic
import tile_library.basic_functions as basic_fns
import tile_library.functions as fns
import tile_library.generate_stats as gen_stats
import tile_library.query_functions as query_fns

BASE_LIBRARY_STRUCTURE = {
    1: {
        '0': [
            {'vars':3, 'lengths':[448,749,450], 'spanning_num':[1,2,1]},
            {'vars':2, 'lengths':[301,301], 'spanning_num':[1,1]},
            {'vars':3, 'lengths':[273,300,840], 'spanning_num':[1,2,3]},
            {'vars':1, 'lengths':[149], 'spanning_num':[1]},
            {'vars':1, 'lengths':[425], 'spanning_num':[1]},
        ],
        '1': [
            {'vars':5, 'lengths':[549,500,600,550,549], 'spanning_num':[1,1,1,1,1]},
        ]
    },
    2: {
        '3f': [
            {'vars':3, 'lengths':[248,498,248], 'spanning_num':[1,2,1]},
            {'vars':3, 'lengths':[250,264,265], 'spanning_num':[1,1,1]},
        ]
    }
}
INVALID_HUMAN_LIBRARY = {
    26: {
        '360': [
            {'vars':3, 'lengths':[448,749,450], 'spanning_num':[1,2,1]},
            {'vars':2, 'lengths':[301,301], 'spanning_num':[1,1]},
            {'vars':3, 'lengths':[273,300,840], 'spanning_num':[1,2,3]},
            {'vars':1, 'lengths':[149], 'spanning_num':[1]},
            {'vars':1, 'lengths':[425], 'spanning_num':[1]},
        ]
    }
}
def mk_genome_seq(length, uppercase=True):
    if uppercase:
        choices = ['A','G','C','T']
    else:
        choices = ['a','g','c','t']
    s = ''
    for i in range(length):
        s += random.choice(choices)
    return s
def mk_tile(tile_int, start_pos, end_pos, num_vars, lengths, spanning_nums=[], start_tag=None, end_tag=None, assembly=19, chrom=1):
    assert len(lengths) == num_vars
    assert lengths[0] == end_pos-start_pos
    if start_tag == None:
        start_tag = mk_genome_seq(TAG_LENGTH)
    if end_tag == None:
        end_tag = mk_genome_seq(TAG_LENGTH)
    new = Tile(tilename=tile_int, start_tag=start_tag, end_tag=end_tag)
    new.save()
    mk_tilevars(num_vars, lengths, start_tag, end_tag, new, tile_int, spanning_nums=spanning_nums)
    locus = TileLocusAnnotation(assembly=assembly, chromosome=chrom, begin_int=start_pos, end_int=end_pos, tile=new)
    locus.save()
    return new, start_tag, end_tag, locus
def mk_tilevars(num_vars, lengths, start_tag, end_tag, tile, tile_int, spanning_nums=[]):
    assert len(lengths) == num_vars
    if spanning_nums==[]:
        spanning_nums = [1 for i in range(num_vars)]
    assert (len(spanning_nums)==num_vars)
    for i in range(num_vars):
        tile_hex = string.join(basic_fns.convert_position_int_to_position_hex_str(tile_int), "")
        tile_hex += hex(i).lstrip('0x').zfill(3)
        tile_var_int = int(tile_hex, 16)
        length = lengths[i]
        num_pos_spanned = spanning_nums[i]
        randseq_len = length - TAG_LENGTH*2
        seq = start_tag
        seq += mk_genome_seq(randseq_len, uppercase=False)
        seq += end_tag
        digestor = hashlib.new('md5', seq)
        new = TileVariant(
            tile_variant_name=tile_var_int,
            tile=tile,
            variant_value=i,
            length=length,
            md5sum=digestor.hexdigest(),
            sequence=seq,
            num_positions_spanned=num_pos_spanned
        )
        new.save()
def make_tiles(chroms_with_paths_with_tile_vars, assembly_default=19):
    """
    assumes chroms_with_paths_with_tile_vars is a dictionary, keyed with integers (chromosomes)
    The value associated with each chromosome is a dictionary, keyed with integers (paths)
    The value associated with each path is a list of dictionaries, one for each position.
    Each position dictionary has key:value pairs:
        'vars':int (number of tile variants)
        'lengths':[a, b, ...] (lengths. First is length of tile variant 0 - the default. Is has length == vars)
        'spanning_num':[i, i, ...] (number of positions tile variant spans)
    """
    for chrom_int in chroms_with_paths_with_tile_vars:
        #Each chromosome starts at locus 0
        locus = 0
        for path_hex in chroms_with_paths_with_tile_vars[chrom_int]:
            tile_vars = chroms_with_paths_with_tile_vars[chrom_int][path_hex]
            for i, position in enumerate(tile_vars):
                tile_int = int(path_hex.zfill(3)+'00'+hex(i).lstrip('0x').zfill(4), 16)
                if i == 0:
                    t, foo, new_start_tag, annotation = mk_tile(
                        tile_int,
                        locus,
                        tile_vars[i]['lengths'][0]+locus,
                        tile_vars[i]['vars'],
                        tile_vars[i]['lengths'],
                        spanning_nums=tile_vars[i]['spanning_num'],
                        assembly=assembly_default,
                        chrom=chrom_int
                    )
                else:
                    t, foo, new_start_tag, annotation = mk_tile(
                        tile_int,
                        locus,
                        tile_vars[i]['lengths'][0]+locus,
                        tile_vars[i]['vars'],
                        tile_vars[i]['lengths'],
                        spanning_nums=tile_vars[i]['spanning_num'],
                        start_tag=new_start_tag,
                        assembly=assembly_default,
                        chrom=chrom_int
                    )
                locus += tile_vars[i]['lengths'][0] - TAG_LENGTH
def make_tile_position(tile_position):
    if type(tile_position) == int:
        tile_position_int = tile_position
    else:
        tile_position_int = int(tile_position, 16)
    start_tag = mk_genome_seq(TAG_LENGTH)
    end_tag = mk_genome_seq(TAG_LENGTH)
    new = Tile(tilename=tile_position_int, start_tag=start_tag, end_tag=end_tag)
    new.save()
    return new
def make_tile_position_and_variant(tile_position, tile_variant, length):
    tile=make_tile_position(tile_position)
    if type(tile_variant) == int:
        tile_variant_int = tile_variant
    else:
        tile_variant_int = int(tile_variant, 16)
    foo, foo, foo, variant_value = basic_fns.get_tile_variant_ints_from_tile_variant_int(tile_variant)
    seq = tile.start_tag
    seq += mk_genome_seq(length-TAG_LENGTH*2, uppercase=False)
    seq += tile.end_tag
    digestor = hashlib.new('md5', seq)
    tilevar = TileVariant(
        tile_variant_name=tile_variant_int,
        tile=tile,
        variant_value=variant_value,
        length=length,
        md5sum=digestor.hexdigest(),
        sequence=seq,
        num_positions_spanned=1
    )
    tilevar.save()
    return tile, tilevar

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
        self.assertRaises(TypeError, basic_fns.convert_position_int_to_position_hex_str, '10')
        self.assertRaises(ValueError, basic_fns.convert_position_int_to_position_hex_str, -1)
        self.assertRaises(ValueError, basic_fns.convert_position_int_to_position_hex_str, int('1000000000', 16))
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
        self.assertRaises(TypeError, basic_fns.convert_tile_variant_int_to_tile_hex_str, '10')
        self.assertRaises(ValueError, basic_fns.convert_tile_variant_int_to_tile_hex_str, -1)
        self.assertRaises(ValueError, basic_fns.convert_tile_variant_int_to_tile_hex_str, int('1000000000000', 16))
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
        self.assertRaises(TypeError, basic_fns.get_position_string_from_position_int, '10')
        self.assertRaises(ValueError, basic_fns.get_position_string_from_position_int, -1)
        self.assertRaises(ValueError, basic_fns.get_position_string_from_position_int, int('1000000000', 16))
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
        self.assertRaises(TypeError, basic_fns.get_position_ints_from_position_int, '10')
        self.assertRaises(ValueError, basic_fns.get_position_ints_from_position_int, -1)
        self.assertRaises(ValueError, basic_fns.get_position_ints_from_position_int, int('1000000000', 16))
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
        self.assertRaises(TypeError, basic_fns.get_tile_variant_string_from_tile_variant_int, '10')
        self.assertRaises(ValueError, basic_fns.get_tile_variant_string_from_tile_variant_int, -1)
        self.assertRaises(ValueError, basic_fns.get_tile_variant_string_from_tile_variant_int, int('1000000000000', 16))
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
        self.assertRaises(TypeError, basic_fns.get_tile_variant_ints_from_tile_variant_int, '10')
        self.assertRaises(ValueError, basic_fns.get_tile_variant_ints_from_tile_variant_int, -1)
        self.assertRaises(ValueError, basic_fns.get_tile_variant_ints_from_tile_variant_int, int('1000000000000', 16))
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
        self.assertRaises(TypeError, basic_fns.convert_position_int_to_tile_variant_int, '10')
        self.assertRaises(ValueError, basic_fns.convert_position_int_to_tile_variant_int, -1)
        self.assertRaises(ValueError, basic_fns.convert_position_int_to_tile_variant_int, int('1000000000', 16))
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
        self.assertRaises(TypeError, basic_fns.convert_tile_variant_int_to_position_int, '10')
        self.assertRaises(ValueError, basic_fns.convert_tile_variant_int_to_position_int, -1)
        self.assertRaises(ValueError, basic_fns.convert_tile_variant_int_to_position_int, int('1000000000000', 16))
    def test_get_position_from_cgf_string(self):
        pos_int = int('2c20000a0', 16)
        cgf_string = '2c2.00.00a0.0000'
        self.assertEqual(type(basic_fns.get_position_from_cgf_string(cgf_string)), int)
        self.assertEqual(basic_fns.get_position_from_cgf_string(cgf_string), pos_int)
        self.assertEqual(basic_fns.get_position_from_cgf_string(cgf_string+"+2"), pos_int)
        cgf_string = u'2c2.00.00a0.0000'
        self.assertEqual(basic_fns.get_position_from_cgf_string(cgf_string), pos_int)
        self.assertEqual(basic_fns.get_position_from_cgf_string(cgf_string+"+2"), pos_int)
    def test_get_position_from_cgf_string_failure(self):
        self.assertRaises(TypeError, basic_fns.get_position_from_cgf_string, int('002000304000a', 16))
        self.assertRaises(ValueError, basic_fns.get_position_from_cgf_string, '000.00.0000')
        self.assertRaises(ValueError, basic_fns.get_position_from_cgf_string, '000.00.0000.000')
        self.assertRaises(ValueError, basic_fns.get_position_from_cgf_string, '000.00.0000.000x')
        self.assertRaises(ValueError, basic_fns.get_position_from_cgf_string, '000.00.0000.000a+')
    def test_get_number_of_tiles_spanned(self):
        cgf_string = '2c2.00.00a0.0000'
        self.assertEqual(type(basic_fns.get_number_of_tiles_spanned(cgf_string)), int)
        self.assertEqual(basic_fns.get_number_of_tiles_spanned(cgf_string), 1)
        self.assertEqual(basic_fns.get_number_of_tiles_spanned(cgf_string+"+2"), 2)
        self.assertEqual(basic_fns.get_number_of_tiles_spanned(cgf_string+"+f"), 15)
        cgf_string = u'2c2.00.00a0.0000'
        self.assertEqual(type(basic_fns.get_number_of_tiles_spanned(cgf_string)), int)
        self.assertEqual(basic_fns.get_number_of_tiles_spanned(cgf_string), 1)
        self.assertEqual(basic_fns.get_number_of_tiles_spanned(cgf_string+"+2"), 2)
        self.assertEqual(basic_fns.get_number_of_tiles_spanned(cgf_string+"+f"), 15)
    def test_get_number_of_tiles_spanned_failure(self):
        self.assertRaises(TypeError, basic_fns.get_position_from_cgf_string, int('002000304000a', 16))
        self.assertRaises(ValueError, basic_fns.get_position_from_cgf_string, '000.00.0000')
        self.assertRaises(ValueError, basic_fns.get_position_from_cgf_string, '000.00.0000.000')
        self.assertRaises(ValueError, basic_fns.get_position_from_cgf_string, '000.00.0000.000x')
        self.assertRaises(ValueError, basic_fns.get_position_from_cgf_string, '000.00.0000.000a+')
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
        self.assertRaises(TypeError, fns.get_min_position_and_tile_variant_from_path_int, '1')
        self.assertRaises(ValueError, fns.get_min_position_and_tile_variant_from_path_int, -1)
        bad_path = Tile.CHR_PATH_LENGTHS[-1] + 1
        self.assertRaises(ValueError, fns.get_min_position_and_tile_variant_from_path_int, bad_path)
    #Is it acceptable to use an already tested function to check against another function?
    def test_get_min_position_and_tile_variant_from_chromosome_int(self):
        for i, path_int in enumerate(Tile.CHR_PATH_LENGTHS):
            name, varname = fns.get_min_position_and_tile_variant_from_chromosome_int(i+1)
            exp_name, exp_varname = fns.get_min_position_and_tile_variant_from_path_int(int(path_int))
            self.assertEqual(name, exp_name)
            self.assertEqual(varname, exp_varname)
    def test_get_min_position_and_tile_variant_from_chromosome_int_failure(self):
        self.assertRaises(TypeError, fns.get_min_position_and_tile_variant_from_chromosome_int, '1')
        self.assertRaises(ValueError, fns.get_min_position_and_tile_variant_from_chromosome_int, 0)
        self.assertRaises(ValueError, fns.get_min_position_and_tile_variant_from_chromosome_int, 28)
    def test_get_chromosome_int_from_position_int(self):
        # Not implemented yet
        self.assertRaises(NotImplementedError, fns.get_chromosome_int_from_position_int, 0)
    def test_get_chromosome_int_from_position_int_failure(self):
        # Not implemented yet
        self.assertRaises(NotImplementedError, fns.get_chromosome_int_from_position_int, 0)
    def test_get_chromosome_int_from_tile_variant_int(self):
        #Not implemented yet
        self.assertRaises(NotImplementedError, fns.get_chromosome_int_from_tile_variant_int, 0)
    def test_get_chromosome_int_from_tile_variant_int_failure(self):
        #Not implemented yet
        self.assertRaises(NotImplementedError, fns.get_chromosome_int_from_tile_variant_int, 0)
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
        self.assertRaises(TypeError, fns.get_chromosome_int_from_path_int, '2a')
        self.assertRaises(ValueError, fns.get_chromosome_int_from_path_int, -1)
        bad_path = Tile.CHR_PATH_LENGTHS[-1]
        self.assertRaises(ValueError, fns.get_chromosome_int_from_path_int, bad_path)
    #Feels a bit weird because the names might change...
    def test_get_chromosome_name_from_chromosome_int(self):
        self.assertEqual(fns.get_chromosome_name_from_chromosome_int(1), 'chr1')
        self.assertEqual(fns.get_chromosome_name_from_chromosome_int(23), 'chrX')
        self.assertEqual(fns.get_chromosome_name_from_chromosome_int(24), 'chrY')
        self.assertEqual(fns.get_chromosome_name_from_chromosome_int(25), 'chrM')
    def test_get_chromosome_name_from_chromosome_int_failure(self):
        self.assertRaises(TypeError, fns.get_chromosome_name_from_chromosome_int, '1')
        self.assertRaises(ValueError, fns.get_chromosome_name_from_chromosome_int, -1)
        self.assertRaises(ValueError, fns.get_chromosome_name_from_chromosome_int, 27)
################################## TEST Tile model ###################################
class TestTileModel(TestCase):
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
    def test_non_int_tile_int(self):
        with self.assertRaises(ValidationError):
            Tile(tilename='invalid').save()
    def test_negative_tile_int(self):
        with self.assertRaises(ValidationError):
            Tile(tilename=-1).save()
    def test_too_big_tile_int(self):
        with self.assertRaises(ValidationError):
            Tile(tilename=int('1000000000', 16)).save()
    def test_non_existant_tags(self):
        with self.assertRaises(ValidationError):
            Tile(tilename=0).save()
    def test_too_short_tags(self):
        with self.assertRaises(ValidationError):
            Tile(tilename=0, start_tag='AA', end_tag='AG').save()
    def test_successful_save(self):
        make_tile_position(0)
    def test_same_name_space_failure(self):
        make_tile_position(0)
        with self.assertRaises(ValidationError) as cm:
            make_tile_position(0)
################################## TEST TileVariant model ###################################
class TestTileVariantModel(TestCase):
    def test_non_int_tile_variant_int(self):
        tile=make_tile_position(0)
        seq = tile.start_tag
        seq += mk_genome_seq(250-TAG_LENGTH*2, uppercase=False)
        seq += tile.end_tag
        digestor = hashlib.new('md5', seq)
        with self.assertRaises(ValidationError) as cm:
            TileVariant(
                tile_variant_name='fail',
                tile=tile,
                variant_value=0,
                length=250,
                md5sum=digestor.hexdigest(),
                sequence=seq,
                num_positions_spanned=1
            ).save()
    def test_negative_tile_variant_int(self):
        tile=make_tile_position(0)
        seq = tile.start_tag
        seq += mk_genome_seq(250-TAG_LENGTH*2, uppercase=False)
        seq += tile.end_tag
        digestor = hashlib.new('md5', seq)
        with self.assertRaises(ValidationError) as cm:
            TileVariant(
                tile_variant_name=-1,
                tile=tile,
                variant_value=0,
                length=250,
                md5sum=digestor.hexdigest(),
                sequence=seq,
                num_positions_spanned=1
            ).save()
    def test_too_big_tile_variant_int(self):
        tile=make_tile_position('fffffffff')
        seq = tile.start_tag
        seq += mk_genome_seq(250-TAG_LENGTH*2, uppercase=False)
        seq += tile.end_tag
        digestor = hashlib.new('md5', seq)
        with self.assertRaises(ValidationError) as cm:
            TileVariant(
                tile_variant_name=int('1000000000000',16),
                tile=tile,
                variant_value=0,
                length=250,
                md5sum=digestor.hexdigest(),
                sequence=seq,
                num_positions_spanned=1
            ).save()
        #print str(cm.exception)
    def test_nonexistant_tile_position(self):
        seq = mk_genome_seq(250, uppercase=False)
        digestor = hashlib.new('md5', seq)
        with self.assertRaises(ValidationError) as cm:
            TileVariant(
                tile_variant_name=int('000000000000',16),
                variant_value=0,
                length=250,
                md5sum=digestor.hexdigest(),
                sequence=seq,
                num_positions_spanned=1
            ).save()
    def test_invalid_positions_spanned(self):
        tile=make_tile_position(0)
        seq = tile.start_tag
        seq += mk_genome_seq(250-TAG_LENGTH*2, uppercase=False)
        seq += tile.end_tag
        digestor = hashlib.new('md5', seq)
        with self.assertRaises(ValidationError) as cm:
            TileVariant(
                tile_variant_name=0,
                tile=tile,
                variant_value=0,
                length=250,
                md5sum=digestor.hexdigest(),
                sequence=seq,
                num_positions_spanned=0
            ).save()
        with self.assertRaises(ValidationError) as cm:
            TileVariant(
                tile_variant_name=0,
                tile=tile,
                variant_value=0,
                length=250,
                md5sum=digestor.hexdigest(),
                sequence=seq,
                num_positions_spanned=-1
            ).save()
    def test_invalid_variant_value(self):
        tile=make_tile_position(0)
        seq = tile.start_tag
        seq += mk_genome_seq(250-TAG_LENGTH*2, uppercase=False)
        seq += tile.end_tag
        digestor = hashlib.new('md5', seq)
        with self.assertRaises(ValidationError) as cm:
            TileVariant(
                tile_variant_name=0,
                tile=tile,
                variant_value=-1,
                length=250,
                md5sum=digestor.hexdigest(),
                sequence=seq,
                num_positions_spanned=1
            ).save()
    def test_invalid_start_tag(self):
        tile=make_tile_position(0)
        seq = tile.start_tag[:20]
        seq += mk_genome_seq(250-TAG_LENGTH*2, uppercase=False)
        seq += tile.end_tag
        digestor = hashlib.new('md5', seq)
        with self.assertRaises(ValidationError) as cm:
            TileVariant(
                tile_variant_name=0,
                tile=tile,
                variant_value=0,
                length=246,
                md5sum=digestor.hexdigest(),
                sequence=seq,
                num_positions_spanned=1,
                start_tag=tile.start_tag[:20]
            ).save()
    def test_invalid_end_tag(self):
        tile=make_tile_position(0)
        seq = tile.start_tag
        seq += mk_genome_seq(250-TAG_LENGTH*2, uppercase=False)
        seq += tile.end_tag[:20]
        digestor = hashlib.new('md5', seq)
        with self.assertRaises(ValidationError) as cm:
            TileVariant(
                tile_variant_name=0,
                tile=tile,
                variant_value=0,
                length=246,
                md5sum=digestor.hexdigest(),
                sequence=seq,
                num_positions_spanned=1,
                end_tag=tile.end_tag[:20]
            ).save()
    def test_mismatching_paths(self):
        tile=make_tile_position(0)
        seq = tile.start_tag
        seq += mk_genome_seq(250-TAG_LENGTH*2, uppercase=False)
        seq += tile.end_tag
        digestor = hashlib.new('md5', seq)
        with self.assertRaises(ValidationError) as cm:
            TileVariant(
                tile_variant_name=int('001000000000',16),
                tile=tile,
                variant_value=0,
                length=250,
                md5sum=digestor.hexdigest(),
                sequence=seq,
                num_positions_spanned=1
            ).save()
    def test_mismatching_path_versions(self):
        tile=make_tile_position(0)
        seq = tile.start_tag
        seq += mk_genome_seq(250-TAG_LENGTH*2, uppercase=False)
        seq += tile.end_tag
        digestor = hashlib.new('md5', seq)
        with self.assertRaises(ValidationError) as cm:
            TileVariant(
                tile_variant_name=int('000010000000',16),
                tile=tile,
                variant_value=0,
                length=250,
                md5sum=digestor.hexdigest(),
                sequence=seq,
                num_positions_spanned=1
            ).save()
    def test_mismatching_steps(self):
        tile=make_tile_position(0)
        seq = tile.start_tag
        seq += mk_genome_seq(250-TAG_LENGTH*2, uppercase=False)
        seq += tile.end_tag
        digestor = hashlib.new('md5', seq)
        with self.assertRaises(ValidationError) as cm:
            TileVariant(
                tile_variant_name=int('000000001000',16),
                tile=tile,
                variant_value=0,
                length=250,
                md5sum=digestor.hexdigest(),
                sequence=seq,
                num_positions_spanned=1
            ).save()
    def test_mismatching_variant_values(self):
        tile=make_tile_position(0)
        seq = tile.start_tag
        seq += mk_genome_seq(250-TAG_LENGTH*2, uppercase=False)
        seq += tile.end_tag
        digestor = hashlib.new('md5', seq)
        with self.assertRaises(ValidationError) as cm:
            TileVariant(
                tile_variant_name=int('000000000001',16),
                tile=tile,
                variant_value=0,
                length=250,
                md5sum=digestor.hexdigest(),
                sequence=seq,
                num_positions_spanned=1
            ).save()
    def test_mismatching_length_and_sequence_length(self):
        tile=make_tile_position(0)
        seq = tile.start_tag
        seq += mk_genome_seq(250-TAG_LENGTH*2, uppercase=False)
        seq += tile.end_tag
        digestor = hashlib.new('md5', seq)
        with self.assertRaises(ValidationError) as cm:
            TileVariant(
                tile_variant_name=0,
                tile=tile,
                variant_value=0,
                length=249,
                md5sum=digestor.hexdigest(),
                sequence=seq,
                num_positions_spanned=1
            ).save()
    def test_mismatching_md5sum(self):
        tile=make_tile_position(0)
        seq = tile.start_tag
        seq += mk_genome_seq(250-TAG_LENGTH*2, uppercase=False)
        seq += tile.end_tag
        with self.assertRaises(ValidationError) as cm:
            TileVariant(
                tile_variant_name=int('000000000000',16),
                tile=tile,
                variant_value=0,
                length=250,
                md5sum='aaadde',
                sequence=seq,
                num_positions_spanned=1
            ).save()
    def test_mismatching_start_tag(self):
        tile=make_tile_position(0)
        seq =  mk_genome_seq(TAG_LENGTH)
        seq += mk_genome_seq(250-TAG_LENGTH*2, uppercase=False)
        seq += tile.end_tag
        digestor = hashlib.new('md5', seq)
        with self.assertRaises(ValidationError) as cm:
            TileVariant(
                tile_variant_name=int('000000000000',16),
                tile=tile,
                variant_value=0,
                length=250,
                md5sum=digestor.hexdigest(),
                sequence=seq,
                num_positions_spanned=1
            ).save()
    def test_mismatching_end_tag(self):
        tile=make_tile_position(0)
        seq =  tile.start_tag
        seq += mk_genome_seq(250-TAG_LENGTH*2, uppercase=False)
        seq += mk_genome_seq(TAG_LENGTH)
        digestor = hashlib.new('md5', seq)
        with self.assertRaises(ValidationError) as cm:
            TileVariant(
                tile_variant_name=int('000000000000',16),
                tile=tile,
                variant_value=0,
                length=250,
                md5sum=digestor.hexdigest(),
                sequence=seq,
                num_positions_spanned=1
            ).save()
    def test_successful_save(self):
        tile=make_tile_position(0)
        seq = tile.start_tag
        seq += mk_genome_seq(250-TAG_LENGTH*2, uppercase=False)
        seq += tile.end_tag
        digestor = hashlib.new('md5', seq)
        TileVariant(
            tile_variant_name=0,
            tile=tile,
            variant_value=0,
            length=250,
            md5sum=digestor.hexdigest(),
            sequence=seq,
            num_positions_spanned=1
        ).save()
    def test_successful_save_with_alternate_tags(self):
        tile=make_tile_position(0)
        start_tag = mk_genome_seq(TAG_LENGTH)
        end_tag = mk_genome_seq(TAG_LENGTH)
        seq = start_tag
        seq += mk_genome_seq(250-TAG_LENGTH*2, uppercase=False)
        seq += end_tag
        digestor = hashlib.new('md5', seq)
        TileVariant(
            tile_variant_name=0,
            tile=tile,
            variant_value=0,
            length=250,
            md5sum=digestor.hexdigest(),
            sequence=seq,
            num_positions_spanned=1,
            start_tag=start_tag,
            end_tag=end_tag
        ).save()
    def test_same_name_space_failure(self):
        tile=make_tile_position(0)
        seq =  tile.start_tag
        seq += mk_genome_seq(250-TAG_LENGTH*2, uppercase=False)
        seq += tile.end_tag
        digestor = hashlib.new('md5', seq)
        TileVariant(
            tile_variant_name=0,
            tile=tile,
            variant_value=0,
            length=250,
            md5sum=digestor.hexdigest(),
            sequence=seq,
            num_positions_spanned=1
        ).save()
        with self.assertRaises(ValidationError) as cm:
            TileVariant(
                tile_variant_name=0,
                tile=tile,
                variant_value=0,
                length=250,
                md5sum=digestor.hexdigest(),
                sequence=seq,
                num_positions_spanned=1
            ).save()
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
        #Does not worry about correctness, since not saving any tiles
        new_tile_variant = TileVariant(tile_variant_name=int('1c403002f0f3', 16))
        self.assertEqual(type(new_tile_variant.getString()), str)
        self.assertEqual(new_tile_variant.getString(), '1c4.03.002f.0f3')

        new_tile_variant = TileVariant(tile_variant_name=int('10',16))
        self.assertEqual(new_tile_variant.getString(), '000.00.0000.010')

        new_tile_variant = TileVariant(tile_variant_name=int('1000100', 16))
        self.assertEqual(new_tile_variant.getString(), '000.00.1000.100')

        new_tile_variant = TileVariant(tile_variant_name=int('10000001', 16))
        self.assertEqual(new_tile_variant.getString(), '000.01.0000.001')

        new_tile_variant = TileVariant(tile_variant_name=int('100000010', 16))
        self.assertEqual(new_tile_variant.getString(), '000.10.0000.010')

        new_tile_variant = TileVariant(tile_variant_name=int('1000000100', 16))
        self.assertEqual(new_tile_variant.getString(), '001.00.0000.100')

        new_tile_variant = TileVariant(tile_variant_name=int('10000000020', 16))
        self.assertEqual(new_tile_variant.getString(), '010.00.0000.020')
    def test_is_reference(self):
        """
        Tile.isReference() returns boolean
        Testing with Tile 0a1.00.1004
        """
        new_tile_variant = TileVariant(tile_variant_name=int('a1001004003', 16), variant_value=3)
        self.assertEqual(type(new_tile_variant.isReference()), bool)
        self.assertFalse(new_tile_variant.isReference())

        new_tile_variant = TileVariant(tile_variant_name=int('a1001004001', 16),variant_value=1)
        self.assertFalse(new_tile_variant.isReference())

        new_tile_variant = TileVariant(tile_variant_name=int('a1001004000', 16), variant_value=0)
        self.assertTrue(new_tile_variant.isReference())
    def test_get_base_at_position_non_int_castable(self):
        tile = TileVariant(length=5, sequence='AGTCN')
        with self.assertRaises(ValueError) as cm:
            tile.getBaseAtPosition('a')
    def test_get_base_at_position_too_big(self):
        tile = TileVariant(length=5, sequence='AGTCN')
        with self.assertRaises(ValueError) as cm:
            tile.getBaseAtPosition(5)
    def test_get_base_at_position_negative(self):
        tile = TileVariant(length=5, sequence='AGTCN')
        with self.assertRaises(ValueError) as cm:
            tile.getBaseAtPosition(-1)
    def test_get_base_at_position(self):
        tile = TileVariant(length=5, sequence='AGTCN')
        self.assertEqual(tile.getBaseAtPosition(0), 'A')
        self.assertEqual(tile.getBaseAtPosition(1), 'G')
        self.assertEqual(tile.getBaseAtPosition(2), 'T')
        self.assertEqual(tile.getBaseAtPosition(3), 'C')
        self.assertEqual(tile.getBaseAtPosition(4), 'N')
    def test_get_base_between_positions_non_int_castable(self):
        tile = TileVariant(tile_variant_name=0, length=5, sequence='AGTCN')
        with self.assertRaises(ValueError) as cm:
            tile.getBaseGroupBetweenPositions('a', 1)
        with self.assertRaises(ValueError) as cm:
            tile.getBaseGroupBetweenPositions(1, 'a')
    def test_get_base_between_positions_too_big(self):
        tile = TileVariant(tile_variant_name=0, length=5, sequence='AGTCN')
        with self.assertRaises(ValueError) as cm:
            tile.getBaseGroupBetweenPositions(0,6)
        with self.assertRaises(ValueError) as cm:
            tile.getBaseGroupBetweenPositions(6,5)
    def test_get_base_between_positions_negative(self):
        tile = TileVariant(tile_variant_name=0, length=5, sequence='AGTCN')
        with self.assertRaises(ValueError) as cm:
            tile.getBaseGroupBetweenPositions(-1, 0)
        with self.assertRaises(ValueError) as cm:
            tile.getBaseGroupBetweenPositions(0,-1)
    def test_get_base_between_positions_smaller_end_position(self):
        tile = TileVariant(tile_variant_name=0, length=5, sequence='AGTCN')
        with self.assertRaises(ValueError) as cm:
            tile.getBaseGroupBetweenPositions(1, 0)
    def test_get_base_between_positions(self):
        tile = TileVariant(tile_variant_name=0, length=5, sequence='AGTCN')
        self.assertEqual(tile.getBaseGroupBetweenPositions(0,0), '')
        self.assertEqual(tile.getBaseGroupBetweenPositions(0,1), 'A')
        self.assertEqual(tile.getBaseGroupBetweenPositions(1,2), 'G')
        self.assertEqual(tile.getBaseGroupBetweenPositions(2,3), 'T')
        self.assertEqual(tile.getBaseGroupBetweenPositions(3,4), 'C')
        self.assertEqual(tile.getBaseGroupBetweenPositions(4,5), 'N')
        self.assertEqual(tile.getBaseGroupBetweenPositions(0,5), 'AGTCN')
        self.assertEqual(tile.getBaseGroupBetweenPositions(1,5), 'GTCN')
        self.assertEqual(tile.getBaseGroupBetweenPositions(1,4), 'GTC')
################################## TEST GenomeVariant model ###################################
class TestGenomeVariantModel(TestCase):
    pass
################################## TEST GenomeVariantTranslation model ###################################
class TestGenomeVariantTranslationModel(TestCase):
    pass
################################## TEST TileLocusAnnotation model ###################################
class TestTileLocusAnnotationModel(TestCase):
    def test_unknown_assembly(self):
        tile, tilevar = make_tile_position_and_variant(0, 0, 250)
        with self.assertRaises(ValidationError) as cm:
            TileLocusAnnotation(assembly=0, chromosome=1, begin_int=0, end_int=250, tile=tile).save()
    def test_unknown_chromosome(self):
        tile, tilevar = make_tile_position_and_variant(0, 0, 250)
        with self.assertRaises(ValidationError) as cm:
            TileLocusAnnotation(assembly=19, chromosome=0, begin_int=0, end_int=250, tile=tile).save()
    def test_missing_tile(self):
        with self.assertRaises(ValidationError) as cm:
            TileLocusAnnotation(assembly=19, chromosome=1, begin_int=0, end_int=250).save()
    def test_missing_tile_variant(self):
        tile = make_tile_position(0)
        with self.assertRaises(ValidationError) as cm:
            TileLocusAnnotation(assembly=19, chromosome=1, begin_int=0, end_int=250, tile=tile).save()
    def test_begin_int_bigger_than_end_int(self):
        tile, tilevar = make_tile_position_and_variant(0, 0, 250)
        with self.assertRaises(ValidationError) as cm:
            TileLocusAnnotation(assembly=19, chromosome=1, begin_int=250, end_int=0, tile=tile).save()
################################## TEST GenomeStatistic model ###################################
class TestGenomeStatisticModel(TestCase):
    #Just need to test saving
    def test_negative_statistics_int(self):
        with self.assertRaises(ValidationError) as cm:
            GenomeStatistic(statistics_type=-1, num_of_positions=0, num_of_tiles=0).save()
    def test_too_big_statistics_int(self):
        with self.assertRaises(ValidationError) as cm:
            GenomeStatistic(statistics_type=28, num_of_positions=0, num_of_tiles=0).save()
    def test_too_small_path_name(self):
        with self.assertRaises(ValidationError) as cm:
            GenomeStatistic(statistics_type=0, path_name=-2, num_of_positions=0, num_of_tiles=0).save()
    def test_neg_one_path_name_on_path_statistic(self):
        with self.assertRaises(ValidationError) as cm:
            GenomeStatistic(statistics_type=27, path_name=-1, num_of_positions=0, num_of_tiles=0).save()
    def test_negative_num_positions(self):
        with self.assertRaises(ValidationError) as cm:
            GenomeStatistic(statistics_type=0, num_of_positions=-1, num_of_tiles=0).save()
    def test_negative_num_tiles(self):
        with self.assertRaises(ValidationError) as cm:
            GenomeStatistic(statistics_type=0, num_of_positions=0, num_of_tiles=-1).save()
    def test_more_positions_than_tiles(self):
        with self.assertRaises(ValidationError) as cm:
            GenomeStatistic(statistics_type=0, num_of_positions=2, num_of_tiles=1).save()
    def test_tiles_without_positions(self):
        with self.assertRaises(ValidationError) as cm:
            GenomeStatistic(statistics_type=0, num_of_positions=0, num_of_tiles=1).save()
    def test_weird_spanning_tiles(self):
        with self.assertRaises(ValidationError) as cm:
            GenomeStatistic(statistics_type=0, num_of_positions=1, num_of_tiles=1, max_num_positions_spanned=0).save()
    def test_duplicate_chromosome_statistics(self):
        GenomeStatistic(statistics_type=0, num_of_positions=1, num_of_tiles=1).save()
        with self.assertRaises(ValidationError) as cm:
            GenomeStatistic(statistics_type=0, num_of_positions=1, num_of_tiles=2).save()
    def test_duplicate_path_statistics(self):
        GenomeStatistic(statistics_type=27, path_name=1, num_of_positions=1, num_of_tiles=1).save()
        with self.assertRaises(ValidationError) as cm:
            GenomeStatistic(statistics_type=27, path_name=1, num_of_positions=1, num_of_tiles=2).save()
################################## TEST generate_statistics ###################################
class TestGenerateStatistics(TestCase):
    def setUp(self):
        make_tiles(BASE_LIBRARY_STRUCTURE)
    def test_initialize(self):
        """
        The following structure:
            Chr1:
                Path 0:
                    0, 2, {'vars':3, 'lengths':[448,749,450], 'spanning_num':[1,2,1]}
                    1, 1, {'vars':2, 'lengths':[301,301], 'spanning_num':[1,1]}
                    2, 3, {'vars':3, 'lengths':[273,300,840], 'spanning_num':[1,2,3]}
                    3, 1, {'vars':1, 'lengths':[149], 'spanning_num':[1]}
                    4, 1, {'vars':1, 'lengths':[425], 'spanning_num':[1]}
                Path 1:
                    0, 1, {'vars':5, 'lengths':[549,500,600,550,549], 'spanning_num':[1,1,1,1,1]}
            Chr2:
                Path 63:
                    0, 2, {'vars':3, 'lengths':[248,498,248], 'spanning_num':[1,2,1]}
                    1, 1, {'vars':3, 'lengths':[250,264,265], 'spanning_num':[1,1,1]}
        """
        gen_stats.initialize(silent=True)
        self.assertEqual(GenomeStatistic.objects.count(), 27+Tile.CHR_PATH_LENGTHS[-1])
        check_vals = [{'num_pos':8, 'num_tiles':21, 'max_num_spanned':3}, #Genome
                      {'num_pos':6, 'num_tiles':15, 'max_num_spanned':3}, #Chromosome 1
                      {'num_pos':2, 'num_tiles':6, 'max_num_spanned':2}] #Chromosome 2
        for i in range(27):
            whole_genome_or_chrom_stats = GenomeStatistic.objects.filter(statistics_type=i).all()
            self.assertEqual(len(whole_genome_or_chrom_stats), 1)
            whole_genome_or_chrom_stats = whole_genome_or_chrom_stats.first()
            if i < 3:
                self.assertEqual(whole_genome_or_chrom_stats.num_of_positions, check_vals[i]['num_pos'])
                self.assertEqual(whole_genome_or_chrom_stats.num_of_tiles, check_vals[i]['num_tiles'])
                self.assertEqual(whole_genome_or_chrom_stats.max_num_positions_spanned, check_vals[i]['max_num_spanned'])
            else:
                self.assertEqual(whole_genome_or_chrom_stats.num_of_positions, 0)
                self.assertEqual(whole_genome_or_chrom_stats.num_of_tiles, 0)
                self.assertIsNone(whole_genome_or_chrom_stats.max_num_positions_spanned)
            self.assertEqual(whole_genome_or_chrom_stats.path_name, -1)

        tile_int, foo = fns.get_min_position_and_tile_variant_from_chromosome_int(2)
        path, version, step = basic_fns.get_position_ints_from_position_int(tile_int)
        check_vals = {0:{'num_pos':5, 'num_tiles':10, 'max_num_spanned':3}, #Path 0
                      1:{'num_pos':1, 'num_tiles':5, 'max_num_spanned':1}, #Path 1
                      path:{'num_pos':2, 'num_tiles':6, 'max_num_spanned':2}} #Path 63
        for i in range(Tile.CHR_PATH_LENGTHS[-1]):
            whole_genome_or_chrom_stats = GenomeStatistic.objects.filter(statistics_type=27).filter(path_name=i).all()
            self.assertEqual(len(whole_genome_or_chrom_stats), 1)
            whole_genome_or_chrom_stats = whole_genome_or_chrom_stats.first()
            if i in check_vals:
                self.assertEqual(whole_genome_or_chrom_stats.num_of_positions, check_vals[i]['num_pos'])
                self.assertEqual(whole_genome_or_chrom_stats.num_of_tiles, check_vals[i]['num_tiles'])
                self.assertEqual(whole_genome_or_chrom_stats.max_num_positions_spanned, check_vals[i]['max_num_spanned'])
            else:
                self.assertEqual(whole_genome_or_chrom_stats.num_of_positions, 0)
                self.assertEqual(whole_genome_or_chrom_stats.num_of_tiles, 0)
                self.assertIsNone(whole_genome_or_chrom_stats.max_num_positions_spanned)
    def test_initialize_failure_after_initializing_once(self):
        gen_stats.initialize(silent=True)
        self.assertRaises(ExistingStatisticsError, gen_stats.initialize)
    def test_update_on_same_library(self):
        gen_stats.initialize(silent=True)
        gen_stats.update(silent=True)
        self.assertEqual(GenomeStatistic.objects.count(), 27+Tile.CHR_PATH_LENGTHS[-1])
        check_vals = [{'num_pos':8, 'num_tiles':21, 'max_num_spanned':3}, #Genome
                      {'num_pos':6, 'num_tiles':15, 'max_num_spanned':3}, #Chromosome 1
                      {'num_pos':2, 'num_tiles':6, 'max_num_spanned':2}] #Chromosome 2
        for i in range(27):
            whole_genome_or_chrom_stats = GenomeStatistic.objects.filter(statistics_type=i).all()
            self.assertEqual(len(whole_genome_or_chrom_stats), 1)
            whole_genome_or_chrom_stats = whole_genome_or_chrom_stats.first()
            if i < 3:
                self.assertEqual(whole_genome_or_chrom_stats.num_of_positions, check_vals[i]['num_pos'])
                self.assertEqual(whole_genome_or_chrom_stats.num_of_tiles, check_vals[i]['num_tiles'])
                self.assertEqual(whole_genome_or_chrom_stats.max_num_positions_spanned, check_vals[i]['max_num_spanned'])
            else:
                self.assertEqual(whole_genome_or_chrom_stats.num_of_positions, 0)
                self.assertEqual(whole_genome_or_chrom_stats.num_of_tiles, 0)
                self.assertIsNone(whole_genome_or_chrom_stats.max_num_positions_spanned)
            self.assertEqual(whole_genome_or_chrom_stats.path_name, -1)

        tile_int, foo = fns.get_min_position_and_tile_variant_from_chromosome_int(2)
        path, version, step = basic_fns.get_position_ints_from_position_int(tile_int)
        check_vals = {0:{'num_pos':5, 'num_tiles':10, 'max_num_spanned':3}, #Path 0
                      1:{'num_pos':1, 'num_tiles':5, 'max_num_spanned':1}, #Path 1
                      path:{'num_pos':2, 'num_tiles':6, 'max_num_spanned':2}} #Path 63
        for i in range(Tile.CHR_PATH_LENGTHS[-1]):
            whole_genome_or_chrom_stats = GenomeStatistic.objects.filter(statistics_type=27).filter(path_name=i).all()
            self.assertEqual(len(whole_genome_or_chrom_stats), 1)
            whole_genome_or_chrom_stats = whole_genome_or_chrom_stats.first()
            if i in check_vals:
                self.assertEqual(whole_genome_or_chrom_stats.num_of_positions, check_vals[i]['num_pos'])
                self.assertEqual(whole_genome_or_chrom_stats.num_of_tiles, check_vals[i]['num_tiles'])
                self.assertEqual(whole_genome_or_chrom_stats.max_num_positions_spanned, check_vals[i]['max_num_spanned'])
            else:
                self.assertEqual(whole_genome_or_chrom_stats.num_of_positions, 0)
                self.assertEqual(whole_genome_or_chrom_stats.num_of_tiles, 0)
                self.assertIsNone(whole_genome_or_chrom_stats.max_num_positions_spanned)
    def test_update_on_updated_library(self):
        """
        Updated structure is (additions shown with asterisk):
        Chr1:
            Path 0:
                0, 2, {'vars':3, 'lengths':[448,749,450], 'spanning_num':[1,2,1]}
                1, 1, {'vars':2, 'lengths':[301,301], 'spanning_num':[1,1]}
                2, 3, {'vars':3, 'lengths':[273,300,840], 'spanning_num':[1,2,3]}
                3, 1, {'vars':1, 'lengths':[149], 'spanning_num':[1]}
                4, 1, {'vars':1, 'lengths':[425], 'spanning_num':[1]}
            Path 1:
                0, 1, {'vars':5, 'lengths':[549,500,600,550,549], 'spanning_num':[1,1,1,1,1]}
               *1, 4, {'vars':2, 'lengths':[220, 1130], 'spanning_num':[1, 4]}
               *2, 1, {'vars':1, 'lengths':[335], 'spanning_num':[1]}
               *3, 1, {'vars':1, 'lengths':[346], 'spanning_num':[1]}
               *4, 1, {'vars':1, 'lengths':[201], 'spanning_num':[1]}
        Chr2:
            Path 3f:
                0, 2, {'vars':3, 'lengths':[248,498,248], 'spanning_num':[1,2,1]}
                1, 1, {'vars':3, 'lengths':[250,264,265], 'spanning_num':[1,1,1]}
        Chr 3:
            Path 7d:
               *0, 1, {'vars':6, 'lengths':[250,300,300,310,260,275]}
               *1, 1, {'vars':1, 'lengths':[150]}
        """
        gen_stats.initialize(silent=True)
        #initialization#
        new_start_tag = Tile.objects.get(tilename=int('001000000', 16)).end_tag
        locus = TileLocusAnnotation.objects.filter(assembly=19).filter(chromosome=1).order_by('begin_int').last().end_int
        locus -= TAG_LENGTH
        chr1_path1_new_tiles = [
            {'vars':2, 'lengths':[220, 1130], 'spanning_num':[1,4]},
            {'vars':1, 'lengths':[335], 'spanning_num':[1]},
            {'vars':1, 'lengths':[346], 'spanning_num':[1]},
            {'vars':1, 'lengths':[201], 'spanning_num':[1]}
        ]
        for i, position in enumerate(chr1_path1_new_tiles):
            pos_int = int('00100'+hex(i+1).lstrip('0x').zfill(4), 16)
            t, ignore, new_start_tag, ignore = mk_tile(
                pos_int,
                locus,
                locus+position['lengths'][0],
                position['vars'],
                position['lengths'],
                spanning_nums=position['spanning_num'],
                start_tag=new_start_tag,
                assembly=19
            )
            locus += chr1_path1_new_tiles[i]['lengths'][0] - TAG_LENGTH
        chr3_paths = {
            3: {
                '7d': [
                    {'vars':6, 'lengths':[250,300,300,310,260,275], 'spanning_num':[1,1,1,1,1,1]},
                    {'vars':1, 'lengths':[301], 'spanning_num':[1]},
                ]
            }
        }
        make_tiles(chr3_paths)

        #end of initialization#
        gen_stats.update(silent=True)
        check_vals = [{'num_pos':14, 'num_tiles':33, 'max_num_spanned':4}, #Genome
                      {'num_pos':10, 'num_tiles':20, 'max_num_spanned':4}, #Chr1
                      {'num_pos':2, 'num_tiles':6, 'max_num_spanned':2}, #Chr2
                      {'num_pos':2, 'num_tiles':7, 'max_num_spanned':1}] #Chr3

        for i in range(27):
            genome_piece = GenomeStatistic.objects.filter(statistics_type=i).all()
            self.assertEqual(len(genome_piece), 1)
            genome_piece = genome_piece.first()
            if i < 4:
                self.assertEqual(genome_piece.num_of_positions, check_vals[i]['num_pos'])
                self.assertEqual(genome_piece.num_of_tiles, check_vals[i]['num_tiles'])
                self.assertEqual(genome_piece.max_num_positions_spanned, check_vals[i]['max_num_spanned'])
            else:
                self.assertEqual(genome_piece.num_of_positions, 0)
                self.assertEqual(genome_piece.num_of_tiles, 0)
                self.assertIsNone(genome_piece.max_num_positions_spanned)
            self.assertEqual(genome_piece.path_name, -1)

        tile_int, foo = fns.get_min_position_and_tile_variant_from_chromosome_int(2)
        path_on_2, version, step = basic_fns.get_position_ints_from_position_int(tile_int)
        tile_int, foo = fns.get_min_position_and_tile_variant_from_chromosome_int(3)
        path_on_3, version, step = basic_fns.get_position_ints_from_position_int(tile_int)
        check_vals = {0:{'num_pos':5, 'num_tiles':10, 'max_num_spanned':3},
                      1:{'num_pos':5, 'num_tiles':10, 'max_num_spanned':4},
                      path_on_2:{'num_pos':2, 'num_tiles':6, 'max_num_spanned':2},
                      path_on_3:{'num_pos':2, 'num_tiles':7, 'max_num_spanned':1},
                     }
        for i in range(Tile.CHR_PATH_LENGTHS[-1]):
            genome_piece = GenomeStatistic.objects.filter(statistics_type=27).filter(path_name=i).all()
            self.assertEqual(len(genome_piece), 1)
            genome_piece = genome_piece.first()
            if i in check_vals:
                self.assertEqual(genome_piece.num_of_positions, check_vals[i]['num_pos'])
                self.assertEqual(genome_piece.num_of_tiles, check_vals[i]['num_tiles'])
                self.assertEqual(genome_piece.max_num_positions_spanned, check_vals[i]['max_num_spanned'])
            else:
                self.assertEqual(genome_piece.num_of_positions, 0)
                self.assertEqual(genome_piece.num_of_tiles, 0)
                self.assertIsNone(genome_piece.max_num_positions_spanned)
    def test_update_failure_without_initialize(self):
        self.assertRaises(MissingStatisticsError, gen_stats.update, silent=True)
    def test_initialize_failure_invalid_genome(self):
        ## Genome Statistics assumes a human genome (number of chromosomes)
        make_tiles(INVALID_HUMAN_LIBRARY)
        self.assertRaises(InvalidGenomeError, gen_stats.initialize)
    def test_update_failure_invalid_genome(self):
        ## Genome Statistics assumes a human genome (number of chromosomes)
        gen_stats.initialize(silent=True)
        make_tiles(INVALID_HUMAN_LIBRARY)
        self.assertRaises(InvalidGenomeError, gen_stats.update)
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
