import random
import hashlib
import string
import subprocess
from unittest import skipIf

from django.test import TestCase, LiveServerTestCase
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core.urlresolvers import reverse
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError

from errors import MissingStatisticsError, InvalidGenomeError, ExistingStatisticsError
from tile_library.constants import TAG_LENGTH, CHR_1, CHR_2, CHR_3, CHR_OTHER, CHR_NONEXISTANT, ASSEMBLY_18, ASSEMBLY_19, \
    NUM_HEX_INDEXES_FOR_PATH, NUM_HEX_INDEXES_FOR_VERSION, NUM_HEX_INDEXES_FOR_STEP, NUM_HEX_INDEXES_FOR_VARIANT_VALUE, \
    NUM_HEX_INDEXES_FOR_CGF_VARIANT_VALUE, GENOME, PATH
from tile_library.models import Tile, TileLocusAnnotation, TileVariant, GenomeVariant, GenomeVariantTranslation, GenomeStatistic
import tile_library.basic_functions as basic_fns
import tile_library.generate_stats as gen_stats
import tile_library.query_functions as query_fns
import tile_library.constants as constants

SUPPORTED_ASSEMBLY_INTS = [i for i, j in constants.SUPPORTED_ASSEMBLY_CHOICES]
SUPPORTED_CHR_INTS = [i for i, j in constants.CHR_CHOICES]
SUPPORTED_STATISTICS_TYPE_INTS = [i for i, j in constants.STATISTICS_TYPE_CHOICES]
genome_and_chromosomes = SUPPORTED_STATISTICS_TYPE_INTS[:]
genome_and_chromosomes.remove(PATH)

BASE_LIBRARY_STRUCTURE = {
    CHR_1: {
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
    CHR_2: {
        hex(constants.CHR_PATH_LENGTHS[CHR_1]).lstrip('0x'): [
            {'vars':3, 'lengths':[248,498,248], 'spanning_num':[1,2,1]},
            {'vars':3, 'lengths':[250,264,265], 'spanning_num':[1,1,1]},
        ]
    }
}
INVALID_HUMAN_LIBRARY = {
    CHR_OTHER: {
        hex(constants.CHR_PATH_LENGTHS[CHR_OTHER]).lstrip('0x'): [
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
def mk_tile(tile_int, start_pos, end_pos, num_vars, lengths, spanning_nums=[], start_tag=None, end_tag=None, assembly=ASSEMBLY_19, chrom=CHR_1, ref_variant_value=0):
    assert len(lengths) == num_vars
    assert ref_variant_value < num_vars
    assert lengths[ref_variant_value] == end_pos-start_pos
    if start_tag == None:
        start_tag = mk_genome_seq(TAG_LENGTH)
    if end_tag == None:
        end_tag = mk_genome_seq(TAG_LENGTH)
    new = Tile(tile_position_int=tile_int, start_tag=start_tag, end_tag=end_tag)
    new.save()
    mk_tilevars(num_vars, lengths, start_tag, end_tag, new, tile_int, spanning_nums=spanning_nums)
    locus = TileLocusAnnotation(assembly_int=assembly, chromosome_int=chrom, start_int=start_pos, end_int=end_pos, tile_position=new, tile_variant_value=ref_variant_value)
    locus.save()
    return new, start_tag, end_tag, locus
def mk_tilevars(num_vars, lengths, start_tag, end_tag, tile, tile_int, spanning_nums=[]):
    assert len(lengths) == num_vars
    if spanning_nums==[]:
        spanning_nums = [1 for i in range(num_vars)]
    assert (len(spanning_nums)==num_vars)
    for i in range(num_vars):
        tile_hex = string.join(basic_fns.get_position_strings_from_position_int(tile_int), "")
        tile_hex += hex(i).lstrip('0x').zfill(NUM_HEX_INDEXES_FOR_VARIANT_VALUE)
        tile_var_int = int(tile_hex, 16)
        length = lengths[i]
        num_pos_spanned = spanning_nums[i]
        randseq_len = length - TAG_LENGTH*2
        seq = start_tag
        seq += mk_genome_seq(randseq_len, uppercase=False)
        seq += end_tag
        digestor = hashlib.new('md5', seq)
        new = TileVariant(
            tile_variant_int=tile_var_int,
            tile=tile,
            variant_value=i,
            length=length,
            md5sum=digestor.hexdigest(),
            sequence=seq,
            num_positions_spanned=num_pos_spanned
        )
        new.save()
def make_tiles(chroms_with_paths_with_tile_vars, assembly_default=ASSEMBLY_19, version_default=0):
    """
    assumes chroms_with_paths_with_tile_vars is a dictionary, keyed with integers (chromosomes)
    The value associated with each chromosome is a dictionary, keyed with strings (paths)
    The value associated with each path is a list of dictionaries, one for each position.
    Each position dictionary has key:value pairs:
        'vars':int (number of tile variants)
        'lengths':[a, b, ...] (lengths. First is length of tile variant 0 - the default. Is has length == vars)
        'spanning_num':[i, i, ...] (number of positions tile variant spans)
    Currently does not implement generating a position where the assembly variant value is not 0
    """
    for chrom_int in chroms_with_paths_with_tile_vars:
        #Each chromosome starts at locus 0
        locus = 0
        for path_hex in chroms_with_paths_with_tile_vars[chrom_int]:
            tile_vars = chroms_with_paths_with_tile_vars[chrom_int][path_hex]
            for i, position in enumerate(tile_vars):
                tile_int = int(
                    path_hex.zfill(NUM_HEX_INDEXES_FOR_PATH)+\
                    hex(version_default).lstrip('0x').zfill(NUM_HEX_INDEXES_FOR_VERSION)+\
                    hex(i).lstrip('0x').zfill(NUM_HEX_INDEXES_FOR_STEP),
                16)
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
    new = Tile(tile_position_int=tile_position_int, start_tag=start_tag, end_tag=end_tag)
    new.save()
    return new
def make_tile_variant(tile, tile_variant, length):
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
        tile_variant_int=tile_variant_int,
        tile=tile,
        variant_value=variant_value,
        length=length,
        md5sum=digestor.hexdigest(),
        sequence=seq,
        num_positions_spanned=1
    )
    tilevar.save()
    return tilevar
def make_tile_position_and_variant(tile_position, tile_variant, length):
    tile=make_tile_position(tile_position)
    tilevar = make_tile_variant(tile, tile_variant, length)
    return tile, tilevar

# Test suite makes assumptions about constants. Tell the user if the constants don't hold
if NUM_HEX_INDEXES_FOR_PATH != 3 or NUM_HEX_INDEXES_FOR_VERSION != 2 or NUM_HEX_INDEXES_FOR_STEP != 4 or NUM_HEX_INDEXES_FOR_VARIANT_VALUE != 3 or NUM_HEX_INDEXES_FOR_CGF_VARIANT_VALUE != 4:
    raise Exception("Testing currently assumes certain values for NUM_HEX_INDEXES_FOR_* constant values")

######################### TEST basic_functions ###################################
class TestConstants(TestCase):
    def test_chr_path_lengths_constants(self):
        """
            CHR_PATH_LENGTHS
        """
        chr_list = constants.CHR_PATH_LENGTHS
        #Check type of lists
        self.assertEqual(type(chr_list), list)
        #Check format of CHR_PATH_LENGTHS
        for i, length in enumerate(chr_list):
            self.assertEqual(type(length), int)
            if i > 0:
                self.assertGreaterEqual(length, chr_list[i-1])
            else:
                self.assertEqual(length, 0)
        self.assertEqual(len(chr_list), CHR_NONEXISTANT)
    def test_cytomap_constants(self):
        """
            CYTOMAP
        """
        chr_list = constants.CHR_PATH_LENGTHS
        cytomap = constants.CYTOMAP
        #Check type of lists
        self.assertEqual(type(cytomap), list)
        #Make sure we have the same number of paths and cytomap entries
        self.assertEqual(len(cytomap), chr_list[-1])
        for s in cytomap:
            self.assertEqual(type(s), str)
    def test_genome_statistics_types(self):
        statistics_types = constants.STATISTICS_TYPE_CHOICES
        chr_list = constants.CHR_CHOICES
        self.assertEqual(len(statistics_types), len(chr_list)+2)
        self.assertListEqual(SUPPORTED_STATISTICS_TYPE_INTS, [GENOME] + SUPPORTED_CHR_INTS + [PATH])
######################### TEST basic_functions ###################################
class TestBasicFunctions(TestCase):
    def test_get_position_strings_from_position_int(self):
        """ Expects integer between 0 and 68719476735, returns 3 strings """
        tile_int = int('0c003020f', 16)
        path, version, step = basic_fns.get_position_strings_from_position_int(tile_int)
        self.assertEqual(type(path), str)
        self.assertEqual(type(version), str)
        self.assertEqual(type(step), str)
        self.assertEqual(path, '0c0')
        self.assertEqual(version, '03')
        self.assertEqual(step, '020f')
        tile_int = int('1c003020f', 16)
        path, version, step = basic_fns.get_position_strings_from_position_int(tile_int)
        self.assertEqual(path, '1c0')
        self.assertEqual(version, '03')
        self.assertEqual(step, '020f')
    def test_get_position_strings_from_position_int_failure(self):
        self.assertRaises(TypeError, basic_fns.get_position_strings_from_position_int, '10')
        self.assertRaises(ValueError, basic_fns.get_position_strings_from_position_int, -1)
        self.assertRaises(ValueError, basic_fns.get_position_strings_from_position_int, int('1000000000', 16))
    def test_get_tile_variant_strings_from_tile_variant_int(self):
        """ Expects integer, returns 4 strings """
        tile_int = int('0c010020f0a0', 16)
        path, version, step, var = basic_fns.get_tile_variant_strings_from_tile_variant_int(tile_int)
        self.assertEqual(type(path), str)
        self.assertEqual(type(version), str)
        self.assertEqual(type(step), str)
        self.assertEqual(type(var), str)
        self.assertEqual(path, '0c0')
        self.assertEqual(version, '10')
        self.assertEqual(step, '020f')
        self.assertEqual(var, '0a0')
        tile_int = int('1c010020f0a0', 16)
        path, version, step, var = basic_fns.get_tile_variant_strings_from_tile_variant_int(tile_int)
        self.assertEqual(path, '1c0')
        self.assertEqual(version, '10')
        self.assertEqual(step, '020f')
        self.assertEqual(var, '0a0')
    def test_get_tile_variant_strings_from_tile_variant_int_failure(self):
        self.assertRaises(TypeError, basic_fns.get_tile_variant_strings_from_tile_variant_int, '10')
        self.assertRaises(ValueError, basic_fns.get_tile_variant_strings_from_tile_variant_int, -1)
        self.assertRaises(ValueError, basic_fns.get_tile_variant_strings_from_tile_variant_int, int('1000000000000', 16))
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
    def test_convert_position_int_to_tile_variant_int_alternate_variant_value(self):
        """ Expects integer, returns integer """
        tile_int = int('1c403002f', 16)
        check_int = int('1c403002f002', 16)
        self.assertEqual(type(basic_fns.convert_position_int_to_tile_variant_int(tile_int)), int)
        self.assertEqual(basic_fns.convert_position_int_to_tile_variant_int(tile_int, variant_value=2), check_int)
        tile_int = int('0', 16)
        check_int = 3
        self.assertEqual(basic_fns.convert_position_int_to_tile_variant_int(tile_int, variant_value=3), check_int)
        tile_int = int('1000', 16)
        check_int = int('100000a', 16)
        self.assertEqual(basic_fns.convert_position_int_to_tile_variant_int(tile_int, variant_value=10), check_int)
        tile_int = int('10000', 16)
        check_int = int('1000000f', 16)
        self.assertEqual(basic_fns.convert_position_int_to_tile_variant_int(tile_int, variant_value=15), check_int)
        tile_int = int('100000', 16)
        check_int = int('100000000', 16)
        self.assertEqual(basic_fns.convert_position_int_to_tile_variant_int(tile_int, variant_value=0), check_int)
        tile_int = int('1000000', 16)
        check_int = int('1000000001', 16)
        self.assertEqual(basic_fns.convert_position_int_to_tile_variant_int(tile_int, variant_value=1), check_int)
        tile_int = int('10000000', 16)
        check_int = int('100000000a0', 16)
        self.assertEqual(basic_fns.convert_position_int_to_tile_variant_int(tile_int, variant_value=int('a0', 16)), check_int)
    def test_convert_position_int_to_tile_variant_int_failure(self):
        self.assertRaises(TypeError, basic_fns.convert_position_int_to_tile_variant_int, '10')
        self.assertRaises(ValueError, basic_fns.convert_position_int_to_tile_variant_int, -1)
        self.assertRaises(ValueError, basic_fns.convert_position_int_to_tile_variant_int, int('1000000000', 16))
        self.assertRaises(TypeError, basic_fns.convert_position_int_to_tile_variant_int, 0, variant_value='0')
        self.assertRaises(ValueError, basic_fns.convert_position_int_to_tile_variant_int, 0, variant_value=-1)
        self.assertRaises(ValueError, basic_fns.convert_position_int_to_tile_variant_int, 0, variant_value=int('1000',16))
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
    def test_get_number_of_tiles_spanned_from_cgf_string(self):
        cgf_string = '2c2.00.00a0.0000'
        self.assertEqual(type(basic_fns.get_number_of_tiles_spanned_from_cgf_string(cgf_string)), int)
        self.assertEqual(basic_fns.get_number_of_tiles_spanned_from_cgf_string(cgf_string), 1)
        self.assertEqual(basic_fns.get_number_of_tiles_spanned_from_cgf_string(cgf_string+"+2"), 2)
        self.assertEqual(basic_fns.get_number_of_tiles_spanned_from_cgf_string(cgf_string+"+f"), 15)
        cgf_string = u'2c2.00.00a0.0000'
        self.assertEqual(type(basic_fns.get_number_of_tiles_spanned_from_cgf_string(cgf_string)), int)
        self.assertEqual(basic_fns.get_number_of_tiles_spanned_from_cgf_string(cgf_string), 1)
        self.assertEqual(basic_fns.get_number_of_tiles_spanned_from_cgf_string(cgf_string+u'+2'), 2)
        self.assertEqual(basic_fns.get_number_of_tiles_spanned_from_cgf_string(cgf_string+u'+f'), 15)
    def test_get_number_of_tiles_spanned_from_cgf_string_failure(self):
        self.assertRaises(TypeError, basic_fns.get_number_of_tiles_spanned_from_cgf_string, int('002000304000a', 16))
        self.assertRaises(ValueError, basic_fns.get_number_of_tiles_spanned_from_cgf_string, '000.00.0000')
        self.assertRaises(ValueError, basic_fns.get_number_of_tiles_spanned_from_cgf_string, '000.00.0000.000')
        self.assertRaises(ValueError, basic_fns.get_number_of_tiles_spanned_from_cgf_string, '000.00.0000.000x')
        self.assertRaises(ValueError, basic_fns.get_number_of_tiles_spanned_from_cgf_string, '000.00.0000.000a+')
    def test_get_min_position_and_tile_variant_from_path_int(self):
        """ Expects int, returns two integers"""
        tile_int = int('1c4000000', 16)
        tile_variant_int = int('1c4000000000', 16)
        name, varname = basic_fns.get_min_position_and_tile_variant_from_path_int(int('1c4',16))
        self.assertEqual(type(name), int)
        self.assertEqual(type(varname), int)
        self.assertEqual(name, tile_int)
        self.assertEqual(varname, tile_variant_int)

        name, varname = basic_fns.get_min_position_and_tile_variant_from_path_int(0)
        self.assertEqual(name, 0)
        self.assertEqual(varname, 0)

        tile_int = int('1000000', 16)
        tile_variant_int = int('1000000000', 16)
        name, varname = basic_fns.get_min_position_and_tile_variant_from_path_int(1)
        self.assertEqual(name, tile_int)
        self.assertEqual(varname, tile_variant_int)

        tile_int = int('10000000', 16)
        tile_variant_int= int('10000000000', 16)
        name, varname = basic_fns.get_min_position_and_tile_variant_from_path_int(16)
        self.assertEqual(name, tile_int)
        self.assertEqual(varname, tile_variant_int)
    def test_get_min_position_and_tile_variant_from_path_int_failure(self):
        self.assertRaises(TypeError, basic_fns.get_min_position_and_tile_variant_from_path_int, '1')
        self.assertRaises(ValueError, basic_fns.get_min_position_and_tile_variant_from_path_int, -1)
        bad_path = constants.CHR_PATH_LENGTHS[-1] + 1
        self.assertRaises(ValueError, basic_fns.get_min_position_and_tile_variant_from_path_int, bad_path)
    #Is it acceptable to use an already tested function to check against another function?
    def test_get_min_position_and_tile_variant_from_chromosome_int(self):
        for i, path_int in enumerate(constants.CHR_PATH_LENGTHS):
            name, varname = basic_fns.get_min_position_and_tile_variant_from_chromosome_int(i+1)
            exp_name, exp_varname = basic_fns.get_min_position_and_tile_variant_from_path_int(int(path_int))
            self.assertEqual(name, exp_name)
            self.assertEqual(varname, exp_varname)
    def test_get_min_position_and_tile_variant_from_chromosome_int_failure(self):
        self.assertRaises(TypeError, basic_fns.get_min_position_and_tile_variant_from_chromosome_int, '1')
        self.assertRaises(ValueError, basic_fns.get_min_position_and_tile_variant_from_chromosome_int, CHR_1-1)
        self.assertRaises(ValueError, basic_fns.get_min_position_and_tile_variant_from_chromosome_int, CHR_NONEXISTANT+1)
    #Feels a bit weird because the last populated path is 25, but technical last path is 26..
    def test_get_chromosome_int_from_position_int(self):
        def get_path_hex(path):
            return hex(path).lstrip('0x').zfill(3)
        path_in_one = get_path_hex(constants.CHR_PATH_LENGTHS[1]/2)
        self.assertEqual(basic_fns.get_chromosome_int_from_position_int(int(path_in_one+'00'+'0000',16)), 1)
        self.assertEqual(basic_fns.get_chromosome_int_from_position_int(int(path_in_one+'00'+'00f0',16)), 1)
        self.assertEqual(basic_fns.get_chromosome_int_from_position_int(int(path_in_one+'a0'+'100a',16)), 1)
        path_in_one = '000'
        self.assertEqual(basic_fns.get_chromosome_int_from_position_int(int(path_in_one+'01'+'0000',16)), 1)
        path_in_two = get_path_hex(constants.CHR_PATH_LENGTHS[1])
        self.assertEqual(basic_fns.get_chromosome_int_from_position_int(int(path_in_two+'10'+'000a',16)), 2)
        path_in_last = get_path_hex(constants.CHR_PATH_LENGTHS[-1]-1)
        self.assertEqual(basic_fns.get_chromosome_int_from_position_int(int(path_in_last+'00'+'00a1',16)), 25)
    def test_get_chromosome_int_from_position_int_failure(self):
        self.assertRaises(TypeError, basic_fns.get_chromosome_int_from_position_int, '0')
        self.assertRaises(ValueError, basic_fns.get_chromosome_int_from_position_int, -1)
        bad_path = constants.CHR_PATH_LENGTHS[-1]
        self.assertRaises(ValueError, basic_fns.get_chromosome_int_from_position_int, int(hex(bad_path).lstrip('0x').zfill(3)+'00'+'0000',16))
    def test_get_chromosome_int_from_tile_variant_int(self):
        def get_path_hex(path):
            return hex(path).lstrip('0x').zfill(3)
        path_in_one = get_path_hex(constants.CHR_PATH_LENGTHS[1]/2)
        self.assertEqual(basic_fns.get_chromosome_int_from_tile_variant_int(int(path_in_one+'00'+'0000'+'000',16)), 1)
        self.assertEqual(basic_fns.get_chromosome_int_from_tile_variant_int(int(path_in_one+'00'+'00f0'+'100',16)), 1)
        self.assertEqual(basic_fns.get_chromosome_int_from_tile_variant_int(int(path_in_one+'a0'+'100a'+'00a',16)), 1)
        path_in_one = '000'
        self.assertEqual(basic_fns.get_chromosome_int_from_tile_variant_int(int(path_in_one+'01'+'0000'+'020',16)), 1)
        path_in_two = get_path_hex(constants.CHR_PATH_LENGTHS[1])
        self.assertEqual(basic_fns.get_chromosome_int_from_tile_variant_int(int(path_in_two+'10'+'000a'+'0af',16)), 2)
        path_in_last = get_path_hex(constants.CHR_PATH_LENGTHS[-1]-1)
        self.assertEqual(basic_fns.get_chromosome_int_from_tile_variant_int(int(path_in_last+'00'+'00a1'+'001',16)), 25)
    def test_get_chromosome_int_from_tile_variant_int_failure(self):
        self.assertRaises(TypeError, basic_fns.get_chromosome_int_from_tile_variant_int, '0')
        self.assertRaises(ValueError, basic_fns.get_chromosome_int_from_tile_variant_int, -1)
        bad_path = constants.CHR_PATH_LENGTHS[-1]
        self.assertRaises(ValueError, basic_fns.get_chromosome_int_from_tile_variant_int, int(hex(bad_path).lstrip('0x').zfill(3)+'00'+'0000'+'000',16))
    #Feels a bit weird because the last populated path is 25, but technical last path is 26...
    def test_get_chromosome_int_from_path_int(self):
        path_in_one = constants.CHR_PATH_LENGTHS[1]/2
        self.assertEqual(basic_fns.get_chromosome_int_from_path_int(path_in_one), 1)
        path_in_one = 0
        self.assertEqual(basic_fns.get_chromosome_int_from_path_int(path_in_one), 1)
        path_in_two = constants.CHR_PATH_LENGTHS[1]
        self.assertEqual(basic_fns.get_chromosome_int_from_path_int(path_in_two), 2)
        path_in_last = constants.CHR_PATH_LENGTHS[-1]-1
        self.assertEqual(basic_fns.get_chromosome_int_from_path_int(path_in_last), 25)
    def test_get_chromosome_int_from_path_int_failure(self):
        self.assertRaises(TypeError, basic_fns.get_chromosome_int_from_path_int, '2a')
        self.assertRaises(ValueError, basic_fns.get_chromosome_int_from_path_int, -1)
        bad_path = constants.CHR_PATH_LENGTHS[-1]
        self.assertRaises(ValueError, basic_fns.get_chromosome_int_from_path_int, bad_path)
################################## TEST human_readable_functions ###################################
class TestHumanReadableFunctions(TestCase):
    pass
    #    def test_get_chromosome_name_from_chromosome_int(self):
    #        self.assertEqual(basic_fns.get_chromosome_name_from_chromosome_int(1), 'chr1')
    #        self.assertEqual(basic_fns.get_chromosome_name_from_chromosome_int(23), 'chrX')
    #        self.assertEqual(basic_fns.get_chromosome_name_from_chromosome_int(24), 'chrY')
    #        self.assertEqual(basic_fns.get_chromosome_name_from_chromosome_int(25), 'chrM')
    #    def test_get_chromosome_name_from_chromosome_int_failure(self):
    #        self.assertRaises(TypeError, basic_fns.get_chromosome_name_from_chromosome_int, '1')
    #        self.assertRaises(ValueError, basic_fns.get_chromosome_name_from_chromosome_int, -1)
    #        self.assertRaises(ValueError, basic_fns.get_chromosome_name_from_chromosome_int, 27)
################################## TEST Tile model ###################################
class TestTileModel(TestCase):
    def test_get_string(self):
        """
            Tile.get_string() returns str
            Testing with Tile 1c4.03.002f
            000.00.0000
            000.00.1000
            000.01.0000
            000.10.0000
            001.00.0000
            010.00.0000
        """
        tile_int = int('1c403002f', 16)
        new_tile = Tile(tile_position_int=tile_int, start_tag="ACGT", end_tag="CCCG")
        self.assertEqual(type(new_tile.get_string()), str)
        self.assertEqual(new_tile.get_string(), '1c4.03.002f')
        tile_int = int('0', 16)
        new_tile = Tile(tile_position_int=tile_int, start_tag="ACGT", end_tag="CCCG")
        self.assertEqual(new_tile.get_string(), '000.00.0000')
        tile_int = int('1000', 16)
        new_tile = Tile(tile_position_int=tile_int, start_tag="ACGT", end_tag="CCCG")
        self.assertEqual(new_tile.get_string(), '000.00.1000')
        tile_int = int('10000', 16)
        new_tile = Tile(tile_position_int=tile_int, start_tag="ACGT", end_tag="CCCG")
        self.assertEqual(new_tile.get_string(), '000.01.0000')
        tile_int = int('100000', 16)
        new_tile = Tile(tile_position_int=tile_int, start_tag="ACGT", end_tag="CCCG")
        self.assertEqual(new_tile.get_string(), '000.10.0000')
        tile_int = int('1000000', 16)
        new_tile = Tile(tile_position_int=tile_int, start_tag="ACGT", end_tag="CCCG")
        self.assertEqual(new_tile.get_string(), '001.00.0000')
        tile_int = int('10000000', 16)
        new_tile = Tile(tile_position_int=tile_int, start_tag="ACGT", end_tag="CCCG")
        self.assertEqual(new_tile.get_string(), '010.00.0000')
    def test_non_int_tile_int(self):
        with self.assertRaises(ValidationError):
            Tile(tile_position_int='invalid').save()
    def test_negative_tile_int(self):
        with self.assertRaises(ValidationError):
            Tile(tile_position_int=-1).save()
    def test_too_big_tile_int(self):
        with self.assertRaises(ValidationError):
            Tile(tile_position_int=int('1000000000', 16)).save()
    def test_non_existant_tags(self):
        with self.assertRaises(ValidationError):
            Tile(tile_position_int=0).save()
    def test_too_short_tags(self):
        with self.assertRaises(ValidationError):
            Tile(tile_position_int=0, start_tag='AA', end_tag='AG').save()
    def test_successful_save(self):
        make_tile_position(0)
    def test_same_name_space_failure(self):
        make_tile_position(0)
        with self.assertRaises(ValidationError) as cm:
            make_tile_position(0)
################################## TEST TileLocusAnnotation model ###################################
class TestTileLocusAnnotationModel(TestCase):
    @skipIf(0 in SUPPORTED_ASSEMBLY_INTS, "Testing if error is raised with an unsupported assembly, but assembly=0 is defined")
    def test_unknown_assembly(self):
        tile, tilevar = make_tile_position_and_variant(0, 0, 250)
        with self.assertRaises(ValidationError) as cm:
            TileLocusAnnotation(assembly_int=0, chromosome_int=CHR_1, start_int=0, end_int=250, tile_position=tile, tile_variant_value=0).save()
    @skipIf(CHR_1-1 in SUPPORTED_CHR_INTS, "Testing if error is raised with an unsupported assembly, but chromosome=CHR_1-1 is defined")
    def test_unknown_chromosome(self):
        tile, tilevar = make_tile_position_and_variant(0, 0, 250)
        with self.assertRaises(ValidationError) as cm:
            TileLocusAnnotation(assembly_int=ASSEMBLY_19, chromosome_int=CHR_1-1, start_int=0, end_int=250, tile_position=tile, tile_variant_value=0).save()
    def test_missing_tile(self):
        with self.assertRaises(ValidationError) as cm:
            TileLocusAnnotation(assembly_int=ASSEMBLY_19, chromosome_int=CHR_1, start_int=0, end_int=250).save()
    def test_missing_tile_variant(self):
        tile = make_tile_position(0)
        with self.assertRaises(ValidationError) as cm:
            TileLocusAnnotation(assembly_int=ASSEMBLY_19, chromosome_int=CHR_1, start_int=0, end_int=250, tile_position=tile, tile_variant_value=0).save()
    def test_wrong_tile_variant(self):
        tile, tilevar = make_tile_position_and_variant(0, 0, 250)
        with self.assertRaises(ValidationError) as cm:
            TileLocusAnnotation(assembly_int=ASSEMBLY_19, chromosome_int=CHR_1, start_int=0, end_int=250, tile_position=tile, tile_variant_value=1).save()
    def test_wrong_tile_variant_where_both_variants_exist(self):
        tile, tilevar = make_tile_position_and_variant(0, 0, 250)
        tilevar2 = make_tile_variant(tile, 1, 249)
        with self.assertRaises(ValidationError) as cm:
            TileLocusAnnotation(assembly_int=ASSEMBLY_19, chromosome_int=CHR_1, start_int=0, end_int=250, tile_position=tile, tile_variant_value=1).save()
    def test_begin_int_bigger_than_end_int(self):
        tile, tilevar = make_tile_position_and_variant(0, 0, 250)
        with self.assertRaises(ValidationError) as cm:
            TileLocusAnnotation(assembly_int=ASSEMBLY_19, chromosome_int=CHR_1, start_int=250, end_int=0, tile_position=tile, tile_variant_value=0).save()
    def test_saving_success(self):
        tile, tilevar = make_tile_position_and_variant(0, 0, 250)
        TileLocusAnnotation(assembly_int=ASSEMBLY_19, chromosome_int=CHR_1, start_int=0, end_int=250, tile_position=tile, tile_variant_value=0).save()
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
                tile_variant_int='fail',
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
                tile_variant_int=-1,
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
                tile_variant_int=int('1000000000000',16),
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
                tile_variant_int=int('000000000000',16),
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
                tile_variant_int=0,
                tile=tile,
                variant_value=0,
                length=250,
                md5sum=digestor.hexdigest(),
                sequence=seq,
                num_positions_spanned=0
            ).save()
        with self.assertRaises(ValidationError) as cm:
            TileVariant(
                tile_variant_int=0,
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
                tile_variant_int=0,
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
                tile_variant_int=0,
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
                tile_variant_int=0,
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
                tile_variant_int=int('001000000000',16),
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
                tile_variant_int=int('000010000000',16),
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
                tile_variant_int=int('000000001000',16),
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
                tile_variant_int=int('000000000001',16),
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
                tile_variant_int=0,
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
                tile_variant_int=int('000000000000',16),
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
                tile_variant_int=int('000000000000',16),
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
                tile_variant_int=int('000000000000',16),
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
            tile_variant_int=0,
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
            tile_variant_int=0,
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
            tile_variant_int=0,
            tile=tile,
            variant_value=0,
            length=250,
            md5sum=digestor.hexdigest(),
            sequence=seq,
            num_positions_spanned=1
        ).save()
        with self.assertRaises(ValidationError) as cm:
            TileVariant(
                tile_variant_int=0,
                tile=tile,
                variant_value=0,
                length=250,
                md5sum=digestor.hexdigest(),
                sequence=seq,
                num_positions_spanned=1
            ).save()
    def test_get_string(self):
        """
            TileVariant.get_string() returns str
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
        new_tile_variant = TileVariant(tile_variant_int=int('1c403002f0f3', 16))
        self.assertEqual(type(new_tile_variant.get_string()), str)
        self.assertEqual(new_tile_variant.get_string(), '1c4.03.002f.0f3')

        new_tile_variant = TileVariant(tile_variant_int=int('10',16))
        self.assertEqual(new_tile_variant.get_string(), '000.00.0000.010')

        new_tile_variant = TileVariant(tile_variant_int=int('1000100', 16))
        self.assertEqual(new_tile_variant.get_string(), '000.00.1000.100')

        new_tile_variant = TileVariant(tile_variant_int=int('10000001', 16))
        self.assertEqual(new_tile_variant.get_string(), '000.01.0000.001')

        new_tile_variant = TileVariant(tile_variant_int=int('100000010', 16))
        self.assertEqual(new_tile_variant.get_string(), '000.10.0000.010')

        new_tile_variant = TileVariant(tile_variant_int=int('1000000100', 16))
        self.assertEqual(new_tile_variant.get_string(), '001.00.0000.100')

        new_tile_variant = TileVariant(tile_variant_int=int('10000000020', 16))
        self.assertEqual(new_tile_variant.get_string(), '010.00.0000.020')
    def test_is_reference(self):
        """
            Tile.is_reference() returns boolean
            Testing with Tile 0a1.00.1004
        """
        tile, tilevar = make_tile_position_and_variant(0, 0, 250)
        tilevar2 = make_tile_variant(tile, 1, 249)
        TileLocusAnnotation(assembly_int=ASSEMBLY_19, chromosome_int=CHR_1, start_int=0, end_int=250, tile_position=tile, tile_variant_value=0).save()
        TileLocusAnnotation(assembly_int=ASSEMBLY_18, chromosome_int=CHR_1, start_int=0, end_int=249, tile_position=tile, tile_variant_value=1).save()
        self.assertEqual(type(tilevar.is_reference(ASSEMBLY_19)), bool)
        self.assertTrue(tilevar.is_reference(ASSEMBLY_19))
        self.assertFalse(tilevar2.is_reference(ASSEMBLY_19))
        self.assertFalse(tilevar.is_reference(ASSEMBLY_18))
        self.assertTrue(tilevar2.is_reference(ASSEMBLY_18))
    def test_get_base_at_position_non_int_castable(self):
        tile = TileVariant(length=5, sequence='AGTCN')
        with self.assertRaises(ValueError) as cm:
            tile.get_base_at_position('a')
    def test_get_base_at_position_too_big(self):
        tile = TileVariant(length=5, sequence='AGTCN')
        with self.assertRaises(ValueError) as cm:
            tile.get_base_at_position(5)
    def test_get_base_at_position_negative(self):
        tile = TileVariant(length=5, sequence='AGTCN')
        with self.assertRaises(ValueError) as cm:
            tile.get_base_at_position(-1)
    def test_get_base_at_position(self):
        tile = TileVariant(length=5, sequence='AGTCN')
        self.assertEqual(tile.get_base_at_position(0), 'A')
        self.assertEqual(tile.get_base_at_position(1), 'G')
        self.assertEqual(tile.get_base_at_position(2), 'T')
        self.assertEqual(tile.get_base_at_position(3), 'C')
        self.assertEqual(tile.get_base_at_position(4), 'N')
    def test_get_base_between_positions_non_int_castable(self):
        tile = TileVariant(tile_variant_int=0, length=5, sequence='AGTCN')
        with self.assertRaises(ValueError) as cm:
            tile.get_base_group_between_positions('a', 1)
        with self.assertRaises(ValueError) as cm:
            tile.get_base_group_between_positions(1, 'a')
    def test_get_base_between_positions_too_big(self):
        tile = TileVariant(tile_variant_int=0, length=5, sequence='AGTCN')
        with self.assertRaises(ValueError) as cm:
            tile.get_base_group_between_positions(0,6)
        with self.assertRaises(ValueError) as cm:
            tile.get_base_group_between_positions(6,5)
    def test_get_base_between_positions_negative(self):
        tile = TileVariant(tile_variant_int=0, length=5, sequence='AGTCN')
        with self.assertRaises(ValueError) as cm:
            tile.get_base_group_between_positions(-1, 0)
        with self.assertRaises(ValueError) as cm:
            tile.get_base_group_between_positions(0,-1)
    def test_get_base_between_positions_smaller_end_position(self):
        tile = TileVariant(tile_variant_int=0, length=5, sequence='AGTCN')
        with self.assertRaises(ValueError) as cm:
            tile.get_base_group_between_positions(1, 0)
    def test_get_base_between_positions(self):
        tile = TileVariant(tile_variant_int=0, length=5, sequence='AGTCN')
        self.assertEqual(tile.get_base_group_between_positions(0,0), '')
        self.assertEqual(tile.get_base_group_between_positions(0,1), 'A')
        self.assertEqual(tile.get_base_group_between_positions(1,2), 'G')
        self.assertEqual(tile.get_base_group_between_positions(2,3), 'T')
        self.assertEqual(tile.get_base_group_between_positions(3,4), 'C')
        self.assertEqual(tile.get_base_group_between_positions(4,5), 'N')
        self.assertEqual(tile.get_base_group_between_positions(0,5), 'AGTCN')
        self.assertEqual(tile.get_base_group_between_positions(1,5), 'GTCN')
        self.assertEqual(tile.get_base_group_between_positions(1,4), 'GTC')
################################## TEST GenomeVariant model ###################################
class TestGenomeVariantModel(TestCase):
    pass
################################## TEST GenomeVariantTranslation model ###################################
class TestGenomeVariantTranslationModel(TestCase):
    pass
################################## TEST GenomeStatistic model ###################################
class TestGenomeStatisticModel(TestCase):
    @skipIf(GENOME-1 in SUPPORTED_STATISTICS_TYPE_INTS, "Testing if error is raised with an unsupported statistics type, but %i is a valid Statistics type" % (GENOME-1))
    def test_negative_statistics_int(self):
        with self.assertRaises(ValidationError) as cm:
            GenomeStatistic(statistics_type=GENOME-1, num_of_positions=0, num_of_tiles=0).save()
    @skipIf(PATH+1 in SUPPORTED_STATISTICS_TYPE_INTS, "Testing if error is raised with an unsupported statistics type, but %i is a valid Statistics type" % (PATH+1))
    def test_too_big_statistics_int(self):
        with self.assertRaises(ValidationError) as cm:
            GenomeStatistic(statistics_type=PATH+1, num_of_positions=0, num_of_tiles=0).save()
    def test_too_small_path_name(self):
        with self.assertRaises(ValidationError) as cm:
            GenomeStatistic(statistics_type=GENOME, path_name=-2, num_of_positions=0, num_of_tiles=0).save()
    def test_too_big_path_name(self):
        with self.assertRaises(ValidationError) as cm:
            GenomeStatistic(statistics_type=GENOME, path_name=0, num_of_positions=0, num_of_tiles=0).save()
    def test_neg_one_path_name_on_path_statistic(self):
        with self.assertRaises(ValidationError) as cm:
            GenomeStatistic(statistics_type=PATH, path_name=-1, num_of_positions=0, num_of_tiles=0).save()
    def test_negative_num_positions(self):
        with self.assertRaises(ValidationError) as cm:
            GenomeStatistic(statistics_type=GENOME, num_of_positions=-1, num_of_tiles=0).save()
    def test_negative_num_tiles(self):
        with self.assertRaises(ValidationError) as cm:
            GenomeStatistic(statistics_type=GENOME, num_of_positions=0, num_of_tiles=-1).save()
    def test_more_positions_than_tiles(self):
        with self.assertRaises(ValidationError) as cm:
            GenomeStatistic(statistics_type=GENOME, num_of_positions=2, num_of_tiles=1).save()
    def test_tiles_without_positions(self):
        with self.assertRaises(ValidationError) as cm:
            GenomeStatistic(statistics_type=GENOME, num_of_positions=0, num_of_tiles=1).save()
    def test_weird_spanning_tiles(self):
        with self.assertRaises(ValidationError) as cm:
            GenomeStatistic(statistics_type=GENOME, num_of_positions=1, num_of_tiles=1, max_num_positions_spanned=0).save()
    def test_duplicate_chromosome_statistics(self):
        GenomeStatistic(statistics_type=GENOME, num_of_positions=1, num_of_tiles=1).save()
        with self.assertRaises(ValidationError) as cm:
            GenomeStatistic(statistics_type=GENOME, num_of_positions=1, num_of_tiles=2).save()
    def test_duplicate_path_statistics(self):
        GenomeStatistic(statistics_type=PATH, path_name=1, num_of_positions=1, num_of_tiles=1).save()
        with self.assertRaises(ValidationError) as cm:
            GenomeStatistic(statistics_type=PATH, path_name=1, num_of_positions=1, num_of_tiles=2).save()
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
        self.assertEqual(GenomeStatistic.objects.count(), len(SUPPORTED_STATISTICS_TYPE_INTS)-1+constants.CHR_PATH_LENGTHS[-1])
        check_vals = {GENOME:{'num_pos':8, 'num_tiles':21, 'max_num_spanned':3}, #Genome
                      CHR_1:{'num_pos':6, 'num_tiles':15, 'max_num_spanned':3}, #Chromosome 1
                      CHR_2:{'num_pos':2, 'num_tiles':6, 'max_num_spanned':2}} #Chromosome 2
        for i in genome_and_chromosomes:
            whole_genome_or_chrom_stats = GenomeStatistic.objects.filter(statistics_type=i).all()
            self.assertEqual(len(whole_genome_or_chrom_stats), 1)
            whole_genome_or_chrom_stats = whole_genome_or_chrom_stats.first()
            if i == GENOME or i == CHR_1 or i == CHR_2:
                self.assertEqual(whole_genome_or_chrom_stats.num_of_positions, check_vals[i]['num_pos'])
                self.assertEqual(whole_genome_or_chrom_stats.num_of_tiles, check_vals[i]['num_tiles'])
                self.assertEqual(whole_genome_or_chrom_stats.max_num_positions_spanned, check_vals[i]['max_num_spanned'])
            else:
                self.assertEqual(whole_genome_or_chrom_stats.num_of_positions, 0)
                self.assertEqual(whole_genome_or_chrom_stats.num_of_tiles, 0)
                self.assertIsNone(whole_genome_or_chrom_stats.max_num_positions_spanned)
            self.assertEqual(whole_genome_or_chrom_stats.path_name, -1)

        tile_int, foo = basic_fns.get_min_position_and_tile_variant_from_chromosome_int(CHR_2)
        path, version, step = basic_fns.get_position_ints_from_position_int(tile_int)
        check_vals = {0:{'num_pos':5, 'num_tiles':10, 'max_num_spanned':3}, #Path 0
                      1:{'num_pos':1, 'num_tiles':5, 'max_num_spanned':1}, #Path 1
                      path:{'num_pos':2, 'num_tiles':6, 'max_num_spanned':2}} #Path 63
        for i in range(constants.CHR_PATH_LENGTHS[-1]):
            whole_genome_or_chrom_stats = GenomeStatistic.objects.filter(statistics_type=PATH).filter(path_name=i).all()
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
        self.assertEqual(GenomeStatistic.objects.count(), len(SUPPORTED_STATISTICS_TYPE_INTS)-1+constants.CHR_PATH_LENGTHS[-1])
        check_vals = {GENOME:{'num_pos':8, 'num_tiles':21, 'max_num_spanned':3}, #Genome
                      CHR_1:{'num_pos':6, 'num_tiles':15, 'max_num_spanned':3}, #Chromosome 1
                      CHR_2:{'num_pos':2, 'num_tiles':6, 'max_num_spanned':2}} #Chromosome 2
        for i in genome_and_chromosomes:
            whole_genome_or_chrom_stats = GenomeStatistic.objects.filter(statistics_type=i).all()
            self.assertEqual(len(whole_genome_or_chrom_stats), 1)
            whole_genome_or_chrom_stats = whole_genome_or_chrom_stats.first()
            if i == GENOME or i == CHR_1 or i == CHR_2:
                self.assertEqual(whole_genome_or_chrom_stats.num_of_positions, check_vals[i]['num_pos'])
                self.assertEqual(whole_genome_or_chrom_stats.num_of_tiles, check_vals[i]['num_tiles'])
                self.assertEqual(whole_genome_or_chrom_stats.max_num_positions_spanned, check_vals[i]['max_num_spanned'])
            else:
                self.assertEqual(whole_genome_or_chrom_stats.num_of_positions, 0)
                self.assertEqual(whole_genome_or_chrom_stats.num_of_tiles, 0)
                self.assertIsNone(whole_genome_or_chrom_stats.max_num_positions_spanned)
            self.assertEqual(whole_genome_or_chrom_stats.path_name, -1)

        tile_int, foo = basic_fns.get_min_position_and_tile_variant_from_chromosome_int(CHR_2)
        path, version, step = basic_fns.get_position_ints_from_position_int(tile_int)
        check_vals = {0:{'num_pos':5, 'num_tiles':10, 'max_num_spanned':3}, #Path 0
                      1:{'num_pos':1, 'num_tiles':5, 'max_num_spanned':1}, #Path 1
                      path:{'num_pos':2, 'num_tiles':6, 'max_num_spanned':2}} #Path 63
        for i in range(constants.CHR_PATH_LENGTHS[-1]):
            whole_genome_or_chrom_stats = GenomeStatistic.objects.filter(statistics_type=PATH).filter(path_name=i).all()
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
        new_start_tag = Tile.objects.get(tile_position_int=int('001000000', 16)).end_tag
        locus = TileLocusAnnotation.objects.filter(assembly_int=ASSEMBLY_19).filter(chromosome_int=CHR_1).order_by('start_int').last().end_int
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
                assembly=ASSEMBLY_19
            )
            locus += chr1_path1_new_tiles[i]['lengths'][0] - TAG_LENGTH
        chr3_paths = {
            CHR_3: {
                hex(constants.CHR_PATH_LENGTHS[CHR_2]).lstrip('0x'): [
                    {'vars':6, 'lengths':[250,300,300,310,260,275], 'spanning_num':[1,1,1,1,1,1]},
                    {'vars':1, 'lengths':[301], 'spanning_num':[1]},
                ]
            }
        }
        make_tiles(chr3_paths)

        #end of initialization#
        gen_stats.update(silent=True)
        check_vals = {GENOME:{'num_pos':14, 'num_tiles':33, 'max_num_spanned':4}, #Genome
                      CHR_1:{'num_pos':10, 'num_tiles':20, 'max_num_spanned':4}, #Chr1
                      CHR_2:{'num_pos':2, 'num_tiles':6, 'max_num_spanned':2}, #Chr2
                      CHR_3:{'num_pos':2, 'num_tiles':7, 'max_num_spanned':1}} #Chr3

        for i in genome_and_chromosomes:
            genome_piece = GenomeStatistic.objects.filter(statistics_type=i).all()
            self.assertEqual(len(genome_piece), 1)
            genome_piece = genome_piece.first()
            if i in [GENOME, CHR_1, CHR_2, CHR_3]:
                self.assertEqual(genome_piece.num_of_positions, check_vals[i]['num_pos'])
                self.assertEqual(genome_piece.num_of_tiles, check_vals[i]['num_tiles'])
                self.assertEqual(genome_piece.max_num_positions_spanned, check_vals[i]['max_num_spanned'])
            else:
                self.assertEqual(genome_piece.num_of_positions, 0)
                self.assertEqual(genome_piece.num_of_tiles, 0)
                self.assertIsNone(genome_piece.max_num_positions_spanned)
            self.assertEqual(genome_piece.path_name, -1)

        tile_int, foo = basic_fns.get_min_position_and_tile_variant_from_chromosome_int(CHR_2)
        path_on_2, version, step = basic_fns.get_position_ints_from_position_int(tile_int)
        tile_int, foo = basic_fns.get_min_position_and_tile_variant_from_chromosome_int(CHR_3)
        path_on_3, version, step = basic_fns.get_position_ints_from_position_int(tile_int)
        check_vals = {0:{'num_pos':5, 'num_tiles':10, 'max_num_spanned':3},
                      1:{'num_pos':5, 'num_tiles':10, 'max_num_spanned':4},
                      path_on_2:{'num_pos':2, 'num_tiles':6, 'max_num_spanned':2},
                      path_on_3:{'num_pos':2, 'num_tiles':7, 'max_num_spanned':1},
                     }
        for i in range(constants.CHR_PATH_LENGTHS[-1]):
            genome_piece = GenomeStatistic.objects.filter(statistics_type=PATH).filter(path_name=i).all()
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
##        self.assertEqual(position.tile_position_int, 0)
##        self.assertEqual(position.start_tag, 'GTAGGCTTTCCTATTCCCACCTTG')
##        self.assertEqual(position.end_tag, 'CGCGGTTATTTCTACGACATAAAT')
