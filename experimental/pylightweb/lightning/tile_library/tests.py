import random
import requests
import hashlib
import string
import subprocess
from unittest import skipIf, skip

from django.test import TestCase, LiveServerTestCase, override_settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core.urlresolvers import reverse
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError
from django.conf import settings

TAG_LENGTH = settings.TAG_LENGTH
CHR_1 = settings.CHR_1
CHR_2 = settings.CHR_2
CHR_3 = settings.CHR_3
CHR_Y = settings.CHR_Y
CHR_M = settings.CHR_M
CHR_OTHER = settings.CHR_OTHER
CHR_NONEXISTANT = settings.CHR_NONEXISTANT
ASSEMBLY_18 = settings.ASSEMBLY_18
ASSEMBLY_19 = settings.ASSEMBLY_19
NUM_HEX_INDEXES_FOR_VERSION = settings.NUM_HEX_INDEXES_FOR_VERSION
NUM_HEX_INDEXES_FOR_PATH = settings.NUM_HEX_INDEXES_FOR_PATH
NUM_HEX_INDEXES_FOR_STEP = settings.NUM_HEX_INDEXES_FOR_STEP
NUM_HEX_INDEXES_FOR_VARIANT_VALUE = settings.NUM_HEX_INDEXES_FOR_VARIANT_VALUE
NUM_HEX_INDEXES_FOR_CGF_VARIANT_VALUE = settings.NUM_HEX_INDEXES_FOR_CGF_VARIANT_VALUE
GENOME = settings.GENOME
PATH = settings.PATH

from errors import MissingStatisticsError, InvalidGenomeError, ExistingStatisticsError, MissingLocusError, UnexpectedLanternBehaviorError, CallsetNameDoesNotExist
from tile_library.models import Tile, TileLocusAnnotation, TileVariant, LanternTranslator, GenomeVariant, GenomeVariantTranslation, GenomeStatistic
from tile_library import settings
import tile_library.test_scripts.complicated_library as build_library
import tile_library.basic_functions as basic_fns
import tile_library.generate_stats as gen_stats
import tile_library.query_functions as query_fns
import tile_library.lantern_query_functions as lantern_query_fns

supported_assembly_ints = [i for i, j in settings.SUPPORTED_ASSEMBLY_CHOICES]
supported_chr_ints = [i for i, j in settings.CHR_CHOICES]
supported_statistics_type_ints = [i for i, j in settings.STATISTICS_TYPE_CHOICES]
genome_and_chromosomes = supported_statistics_type_ints[:]
genome_and_chromosomes.remove(PATH)

NUM_RANDOM_TESTS_TO_RUN=1

version_min = '0'*NUM_HEX_INDEXES_FOR_VERSION
version_max='f'*NUM_HEX_INDEXES_FOR_VERSION
path_min = '0'*NUM_HEX_INDEXES_FOR_PATH
theoretical_path_max = 'f'*NUM_HEX_INDEXES_FOR_PATH
step_min = '0'*NUM_HEX_INDEXES_FOR_STEP
step_max = 'f'*NUM_HEX_INDEXES_FOR_STEP
variant_value_min = '0'*NUM_HEX_INDEXES_FOR_VARIANT_VALUE
variant_value_max = 'f'*NUM_HEX_INDEXES_FOR_VARIANT_VALUE

BASE_LIBRARY_STRUCTURE = {
    CHR_1: {
        '0': [
            {'vars':3, 'lengths':[448,749,450], 'spanning_nums':[1,2,1]},
            {'vars':2, 'lengths':[301,301], 'spanning_nums':[1,1]},
            {'vars':3, 'lengths':[273,300,840], 'spanning_nums':[1,2,3]},
            {'vars':1, 'lengths':[149], 'spanning_nums':[1]},
            {'vars':1, 'lengths':[425], 'spanning_nums':[1]},
        ],
        '1': [
            {'vars':5, 'lengths':[549,500,600,550,549], 'spanning_nums':[1,1,1,1,1]},
        ]
    },
    CHR_2: {
        hex(settings.CHR_PATH_LENGTHS[CHR_1]).lstrip('0x'): [
            {'vars':3, 'lengths':[248,498,248], 'spanning_nums':[1,2,1]},
            {'vars':3, 'lengths':[250,264,265], 'spanning_nums':[1,1,1]},
        ]
    }
}
INVALID_HUMAN_LIBRARY = {
    CHR_OTHER: {
        hex(settings.CHR_PATH_LENGTHS[CHR_OTHER]).lstrip('0x'): [
            {'vars':3, 'lengths':[448,749,450], 'spanning_nums':[1,2,1]},
            {'vars':2, 'lengths':[301,301], 'spanning_nums':[1,1]},
            {'vars':3, 'lengths':[273,300,840], 'spanning_nums':[1,2,3]},
            {'vars':1, 'lengths':[149], 'spanning_nums':[1]},
            {'vars':1, 'lengths':[425], 'spanning_nums':[1]},
        ]
    }
}
def mk_hex_num(length,min_num=None):
    choices = ['0', '1','2','3','4','5','6','7','8','9','a','b','c','d','e','f']
    s = ''
    if min_num != None:
        assert min_num <= length
        for i in range(min_num):
            s+= random.choice(choices)
        s.zfill(length)
        return s
    else:
        for i in range(length):
            s += random.choice(choices)
        return s
def mk_genome_seq(length, uppercase=False):
    if uppercase:
        choices = ['A','G','C','T']
    else:
        choices = ['a','g','c','t']
    s = ''
    for i in range(length):
        s += random.choice(choices)
    return s
def mk_tile(tile_int, start_pos, end_pos, num_vars, lengths, is_end_of_path=False, spanning_nums=[], start_tag='', end_tag='', assembly=ASSEMBLY_19, chrom=CHR_1, ref_variant_value=0, ignore_loci=False):
    assert len(lengths) == num_vars
    assert ref_variant_value < num_vars
    assert lengths[ref_variant_value] == end_pos-start_pos
    version, path, step = basic_fns.get_position_ints_from_position_int(tile_int)
    if step == 0:
        path_start = True
    else:
        path_start = False
        if start_tag == '':
            start_tag = mk_genome_seq(TAG_LENGTH)
    if end_tag == '' and not is_end_of_path:
        end_tag = mk_genome_seq(TAG_LENGTH)
    new = Tile(tile_position_int=tile_int, start_tag=start_tag, end_tag=end_tag, is_start_of_path=path_start, is_end_of_path=is_end_of_path)
    new.save()
    mk_tilevars(num_vars, lengths, new, spanning_nums=spanning_nums)
    if not ignore_loci:
        locus = TileLocusAnnotation(assembly_int=assembly, chromosome_int=chrom, start_int=start_pos, end_int=end_pos, tile_position=new, tile_variant_value=ref_variant_value)
        locus.save()
        return new, start_tag, end_tag, locus
    return new, start_tag, end_tag, None
def mk_tilevars(num_vars, lengths, tile, spanning_nums=[], start_variant_value=0):
    assert len(lengths) == num_vars
    if spanning_nums==[]:
        spanning_nums = [1 for i in range(num_vars)]
    assert (len(spanning_nums)==num_vars)
    for i in range(start_variant_value, num_vars):
        tile_int = int(tile.tile_position_int)
        tile_hex = string.join(basic_fns.get_position_strings_from_position_int(tile_int), "")
        tile_hex += hex(i).lstrip('0x').zfill(NUM_HEX_INDEXES_FOR_VARIANT_VALUE)
        tile_var_int = int(tile_hex, 16)
        length = lengths[i]
        num_pos_spanned = spanning_nums[i]
        start_tag = tile.start_tag
        if num_pos_spanned == 1:
            end_tag = tile.end_tag
        else:
            end_tag = Tile.objects.get(tile_position_int=tile_int+num_pos_spanned-1).end_tag
        randseq_len = length - len(start_tag) - len(end_tag)
        seq = start_tag + mk_genome_seq(randseq_len) + end_tag
        digestor = hashlib.new('md5', seq)
        new = TileVariant(
            tile_variant_int=tile_var_int,
            tile=tile,
            variant_value=i,
            length=length,
            md5sum=digestor.hexdigest(),
            sequence=seq,
            num_positions_spanned=num_pos_spanned,
            start_tag = seq[:TAG_LENGTH],
            end_tag = seq[-TAG_LENGTH:]
        )
        new.save()
def make_tiles(chroms_with_paths_with_tile_vars, assembly_default=ASSEMBLY_19, version_default=0, ignore_loci=False):
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
        paths = chroms_with_paths_with_tile_vars[chrom_int]
        paths = sorted(paths, key=lambda path: int(path,16))
        for path_hex in paths:
            tile_vars = chroms_with_paths_with_tile_vars[chrom_int][path_hex]
            #Make positions
            tile_objects = []
            for step, position in enumerate(tile_vars):
                tile_int = int(
                    hex(version_default).lstrip('0x').zfill(NUM_HEX_INDEXES_FOR_VERSION)+\
                    path_hex.zfill(NUM_HEX_INDEXES_FOR_PATH)+\
                    hex(step).lstrip('0x').zfill(NUM_HEX_INDEXES_FOR_STEP),
                16)
                length = position['lengths'][0]
                if step == 0:
                    t, foo, new_start_tag, annotation = mk_tile(
                        tile_int,
                        locus,
                        length+locus,
                        1,
                        [length],
                        spanning_nums=[position['spanning_nums'][0]],
                        assembly=assembly_default,
                        chrom=chrom_int,
                        ignore_loci=ignore_loci
                    )
                else:
                    t, foo, new_start_tag, annotation = mk_tile(
                        tile_int,
                        locus,
                        length+locus,
                        1,
                        [length],
                        spanning_nums=[position['spanning_nums'][0]],
                        start_tag=new_start_tag,
                        assembly=assembly_default,
                        chrom=chrom_int,
                        ignore_loci=ignore_loci
                    )
                tile_objects.append(t)
                locus += length - TAG_LENGTH
            #initialize variants
            for step, position in enumerate(tile_vars):
                if position['vars'] > 1:
                    tile = tile_objects[step]
                    mk_tilevars(position['vars'], position['lengths'], tile, position['spanning_nums'], start_variant_value=1)
def make_tile_position(tile_position, is_path_end=False):
    if type(tile_position) == int:
        tile_position_int = tile_position
    else:
        tile_position_int = int(tile_position, 16)
    version, path, step = basic_fns.get_position_ints_from_position_int(tile_position_int)
    if step == 0:
        is_path_start = True
        start_tag = ""
    else:
        is_path_start = False
        start_tag = mk_genome_seq(TAG_LENGTH)
    if is_path_end:
        end_tag = ""
    else:
        end_tag = mk_genome_seq(TAG_LENGTH)
    new = Tile(tile_position_int=tile_position_int, start_tag=start_tag, end_tag=end_tag, is_start_of_path=is_path_start, is_end_of_path=is_path_end)
    new.save()
    return new
def make_tile_variant(starting_tile, ending_tile, tile_variant, length, num_spanned=1):
    if type(tile_variant) == int:
        tile_variant_int = tile_variant
    else:
        tile_variant_int = int(tile_variant, 16)
    foo, foo, foo, variant_value = basic_fns.get_tile_variant_ints_from_tile_variant_int(tile_variant_int)
    starting_tag = starting_tile.start_tag
    ending_tag = ending_tile.end_tag
    seq = starting_tag
    seq += mk_genome_seq(length-len(starting_tag)-len(ending_tag))
    seq += ending_tag
    digestor = hashlib.new('md5', seq)
    tilevar = TileVariant(
        tile_variant_int=tile_variant_int,
        tile=starting_tile,
        variant_value=variant_value,
        length=length,
        md5sum=digestor.hexdigest(),
        sequence=seq,
        num_positions_spanned=num_spanned,
        start_tag = seq[:TAG_LENGTH],
        end_tag = seq[-TAG_LENGTH:]
    )
    tilevar.save()
    return tilevar
def make_tile_position_and_variant(tile_position, tile_variant, length, tile_ending=None, num_spanned=1):
    tile = make_tile_position(tile_position)
    if tile_ending == None:
        ending_tile = tile
    else:
        ending_tile = tile_ending
    tilevar = make_tile_variant(tile, ending_tile, tile_variant, length, num_spanned=num_spanned)
    return tile, tilevar

######################### TEST basic_functions ###################################
class TestBasicFunctions(TestCase):
    #get_position_strings_from_position_int
    def test_get_position_strings_from_position_int_type(self):
        version, path, step = basic_fns.get_position_strings_from_position_int(0)
        self.assertIsInstance(version, str)
        self.assertIsInstance(path, str)
        self.assertIsInstance(step, str)
    def test_get_position_strings_from_random_position_ints(self):
        for i in range(NUM_RANDOM_TESTS_TO_RUN):
            v=mk_hex_num(NUM_HEX_INDEXES_FOR_VERSION)
            p=mk_hex_num(NUM_HEX_INDEXES_FOR_PATH)
            s=mk_hex_num(NUM_HEX_INDEXES_FOR_STEP)
            tile_int = int(v+p+s, 16)
            version, path, step = basic_fns.get_position_strings_from_position_int(tile_int)
            self.assertEqual(version, v)
            self.assertEqual(path, p)
            self.assertEqual(step, s)
    def test_get_position_strings_from_min_and_max_positions(self):
        version, path, step = basic_fns.get_position_strings_from_position_int(0)
        self.assertEqual(version, '0'*NUM_HEX_INDEXES_FOR_VERSION)
        self.assertEqual(path, '0'*NUM_HEX_INDEXES_FOR_PATH)
        self.assertEqual(step, '0'*NUM_HEX_INDEXES_FOR_STEP)
        v='f'*NUM_HEX_INDEXES_FOR_VERSION
        p='f'*NUM_HEX_INDEXES_FOR_PATH
        s='f'*NUM_HEX_INDEXES_FOR_STEP
        tile_int = int(v+p+s, 16)
        version, path, step = basic_fns.get_position_strings_from_position_int(tile_int)
        self.assertEqual(version, v)
        self.assertEqual(path, p)
        self.assertEqual(step, s)
    def test_get_position_strings_from_position_int_failure(self):
        self.assertRaises(TypeError, basic_fns.get_position_strings_from_position_int, '10')
        self.assertRaises(ValueError, basic_fns.get_position_strings_from_position_int, -1)
        v='f'*NUM_HEX_INDEXES_FOR_VERSION
        p='f'*NUM_HEX_INDEXES_FOR_PATH
        s='f'*NUM_HEX_INDEXES_FOR_STEP
        tile_int = int(v+p+s, 16)
        self.assertRaises(ValueError, basic_fns.get_position_strings_from_position_int, tile_int+1)
    #get_position_string_from_position_int
    def test_get_position_string_from_position_int_type(self):
        pos_str = basic_fns.get_position_string_from_position_int(0)
        self.assertIsInstance(pos_str, str)
    def test_get_position_string_from_random_position_ints(self):
        for i in range(NUM_RANDOM_TESTS_TO_RUN):
            v=mk_hex_num(NUM_HEX_INDEXES_FOR_VERSION)
            p=mk_hex_num(NUM_HEX_INDEXES_FOR_PATH)
            s=mk_hex_num(NUM_HEX_INDEXES_FOR_STEP)
            tile_int = int(v+p+s, 16)
            pos_str = basic_fns.get_position_string_from_position_int(tile_int)
            self.assertEqual(pos_str, string.join([v,p,s],sep='.'))
    def test_get_position_string_from_max_and_min_positions(self):
        v='0'*NUM_HEX_INDEXES_FOR_VERSION
        p='0'*NUM_HEX_INDEXES_FOR_PATH
        s='0'*NUM_HEX_INDEXES_FOR_STEP
        tile_int = int(v+p+s, 16)
        pos_str = basic_fns.get_position_string_from_position_int(tile_int)
        self.assertEqual(pos_str, string.join([v,p,s],sep='.'))
        v='f'*NUM_HEX_INDEXES_FOR_VERSION
        p='f'*NUM_HEX_INDEXES_FOR_PATH
        s='f'*NUM_HEX_INDEXES_FOR_STEP
        tile_int = int(v+p+s, 16)
        pos_str = basic_fns.get_position_string_from_position_int(tile_int)
        self.assertEqual(pos_str, string.join([v,p,s],sep='.'))
    def test_get_position_string_from_position_int_failure(self):
        self.assertRaises(TypeError, basic_fns.get_position_string_from_position_int, '10')
        self.assertRaises(ValueError, basic_fns.get_position_string_from_position_int, -1)
        v='f'*NUM_HEX_INDEXES_FOR_VERSION
        p='f'*NUM_HEX_INDEXES_FOR_PATH
        s='f'*NUM_HEX_INDEXES_FOR_STEP
        tile_int = int(v+p+s, 16)
        self.assertRaises(ValueError, basic_fns.get_position_string_from_position_int, tile_int+1)
    #get_position_ints_from_position_int
    def test_get_position_ints_from_position_int_type(self):
        version, path, step = basic_fns.get_position_ints_from_position_int(0)
        self.assertIsInstance(version, int)
        self.assertIsInstance(path, int)
        self.assertIsInstance(step, int)
    def test_get_position_ints_from_random_position_ints(self):
        """ Expects integer, returns 3 integers """
        for i in range(NUM_RANDOM_TESTS_TO_RUN):
            v=mk_hex_num(NUM_HEX_INDEXES_FOR_VERSION)
            p=mk_hex_num(NUM_HEX_INDEXES_FOR_PATH)
            s=mk_hex_num(NUM_HEX_INDEXES_FOR_STEP)
            tile_int = int(v+p+s, 16)
            version, path, step = basic_fns.get_position_ints_from_position_int(tile_int)
            self.assertEqual(version, int(v,16))
            self.assertEqual(path, int(p,16))
            self.assertEqual(step, int(s,16))
    def test_get_position_intss_from_min_and_max_positions(self):
        version, path, step = basic_fns.get_position_ints_from_position_int(0)
        self.assertEqual(version, 0)
        self.assertEqual(path, 0)
        self.assertEqual(step, 0)
        v='f'*NUM_HEX_INDEXES_FOR_VERSION
        p='f'*NUM_HEX_INDEXES_FOR_PATH
        s='f'*NUM_HEX_INDEXES_FOR_STEP
        tile_int = int(v+p+s, 16)
        version, path, step = basic_fns.get_position_ints_from_position_int(tile_int)
        self.assertEqual(version, int(v,16))
        self.assertEqual(path, int(p,16))
        self.assertEqual(step, int(s,16))
    def test_get_position_ints_from_position_int_failure(self):
        self.assertRaises(TypeError, basic_fns.get_position_ints_from_position_int, '10')
        self.assertRaises(ValueError, basic_fns.get_position_ints_from_position_int, -1)
        v='f'*NUM_HEX_INDEXES_FOR_VERSION
        p='f'*NUM_HEX_INDEXES_FOR_PATH
        s='f'*NUM_HEX_INDEXES_FOR_STEP
        tile_int = int(v+p+s, 16)
        self.assertRaises(ValueError, basic_fns.get_position_ints_from_position_int, tile_int+1)
    #get_tile_variant_strings_from_tile_variant_int
    def test_get_tile_variant_strings_from_tile_variant_int_type(self):
        version, path, step, variant = basic_fns.get_tile_variant_strings_from_tile_variant_int(0)
        self.assertIsInstance(version, str)
        self.assertIsInstance(path, str)
        self.assertIsInstance(step, str)
        self.assertIsInstance(variant, str)
    def test_get_tile_variant_strings_from_random_tile_variants(self):
        for i in range(NUM_RANDOM_TESTS_TO_RUN):
            v=mk_hex_num(NUM_HEX_INDEXES_FOR_VERSION)
            p=mk_hex_num(NUM_HEX_INDEXES_FOR_PATH)
            s=mk_hex_num(NUM_HEX_INDEXES_FOR_STEP)
            vv=mk_hex_num(NUM_HEX_INDEXES_FOR_VARIANT_VALUE)
            tile_int = int(v+p+s+vv, 16)
            version, path, step, variant = basic_fns.get_tile_variant_strings_from_tile_variant_int(tile_int)
            self.assertEqual(version, v)
            self.assertEqual(path, p)
            self.assertEqual(step, s)
            self.assertEqual(variant, vv)
    def test_get_tile_variant_strings_from_min_and_max_tile_variants(self):
        version, path, step, variant = basic_fns.get_tile_variant_strings_from_tile_variant_int(0)
        self.assertEqual(version, '0'*NUM_HEX_INDEXES_FOR_VERSION)
        self.assertEqual(path, '0'*NUM_HEX_INDEXES_FOR_PATH)
        self.assertEqual(step, '0'*NUM_HEX_INDEXES_FOR_STEP)
        self.assertEqual(variant, '0'*NUM_HEX_INDEXES_FOR_VARIANT_VALUE)
        v='f'*NUM_HEX_INDEXES_FOR_VERSION
        p='f'*NUM_HEX_INDEXES_FOR_PATH
        s='f'*NUM_HEX_INDEXES_FOR_STEP
        vv='f'*NUM_HEX_INDEXES_FOR_VARIANT_VALUE
        tile_int = int(v+p+s+vv, 16)
        version, path, step, variant = basic_fns.get_tile_variant_strings_from_tile_variant_int(tile_int)
        self.assertEqual(version, v)
        self.assertEqual(path, p)
        self.assertEqual(step, s)
        self.assertEqual(variant, vv)
    def test_get_tile_variant_strings_from_tile_variant_int_failure(self):
        self.assertRaises(TypeError, basic_fns.get_tile_variant_strings_from_tile_variant_int, '10')
        self.assertRaises(ValueError, basic_fns.get_tile_variant_strings_from_tile_variant_int, -1)
        v='f'*NUM_HEX_INDEXES_FOR_VERSION
        p='f'*NUM_HEX_INDEXES_FOR_PATH
        s='f'*NUM_HEX_INDEXES_FOR_STEP
        vv='f'*NUM_HEX_INDEXES_FOR_VARIANT_VALUE
        tile_int = int(v+p+s+vv, 16)
        self.assertRaises(ValueError, basic_fns.get_tile_variant_strings_from_tile_variant_int, tile_int+1)
    #get_tile_variant_string_from_tile_variant_int
    def test_get_tile_variant_string_from_tile_variant_int_type(self):
        s = basic_fns.get_tile_variant_string_from_tile_variant_int(0)
        self.assertIsInstance(s, str)
    def test_get_tile_variant_string_from_random_tile_variant_ints(self):
        for i in range(NUM_RANDOM_TESTS_TO_RUN):
            v=mk_hex_num(NUM_HEX_INDEXES_FOR_VERSION)
            p=mk_hex_num(NUM_HEX_INDEXES_FOR_PATH)
            s=mk_hex_num(NUM_HEX_INDEXES_FOR_STEP)
            vv=mk_hex_num(NUM_HEX_INDEXES_FOR_VARIANT_VALUE)
            tv_int = int(v+p+s+vv, 16)
            tv_str = basic_fns.get_tile_variant_string_from_tile_variant_int(tv_int)
            self.assertEqual(tv_str, string.join([v,p,s,vv],sep='.'))
    def test_get_tile_variant_string_from_max_and_min_tile_variants(self):
        v='0'*NUM_HEX_INDEXES_FOR_VERSION
        p='0'*NUM_HEX_INDEXES_FOR_PATH
        s='0'*NUM_HEX_INDEXES_FOR_STEP
        vv='0'*NUM_HEX_INDEXES_FOR_VARIANT_VALUE
        tv_int = int(v+p+s+vv, 16)
        tv_str = basic_fns.get_tile_variant_string_from_tile_variant_int(tv_int)
        self.assertEqual(tv_str, string.join([v,p,s,vv],sep='.'))
        v='f'*NUM_HEX_INDEXES_FOR_VERSION
        p='f'*NUM_HEX_INDEXES_FOR_PATH
        s='f'*NUM_HEX_INDEXES_FOR_STEP
        vv='f'*NUM_HEX_INDEXES_FOR_VARIANT_VALUE
        tv_int = int(v+p+s+vv, 16)
        tv_str = basic_fns.get_tile_variant_string_from_tile_variant_int(tv_int)
        self.assertEqual(tv_str, string.join([v,p,s,vv],sep='.'))
    def test_get_tile_variant_string_from_tile_variant_int_failure(self):
        self.assertRaises(TypeError, basic_fns.get_tile_variant_string_from_tile_variant_int, '10')
        self.assertRaises(ValueError, basic_fns.get_tile_variant_string_from_tile_variant_int, -1)
        v='f'*NUM_HEX_INDEXES_FOR_VERSION
        p='f'*NUM_HEX_INDEXES_FOR_PATH
        s='f'*NUM_HEX_INDEXES_FOR_STEP
        vv='f'*NUM_HEX_INDEXES_FOR_VARIANT_VALUE
        tv_int = int(v+p+s+vv, 16)
        self.assertRaises(ValueError, basic_fns.get_tile_variant_string_from_tile_variant_int, tv_int+1)
    #get_tile_variant_ints_from_tile_variant_int
    def test_get_tile_variant_ints_from_tile_variant_int_type(self):
        version, path, step, variant = basic_fns.get_tile_variant_ints_from_tile_variant_int(0)
        self.assertIsInstance(version, int)
        self.assertIsInstance(path, int)
        self.assertIsInstance(step, int)
        self.assertIsInstance(variant, int)
    def test_get_tile_variant_ints_from_random_tile_variants(self):
        for i in range(NUM_RANDOM_TESTS_TO_RUN):
            v=mk_hex_num(NUM_HEX_INDEXES_FOR_VERSION)
            p=mk_hex_num(NUM_HEX_INDEXES_FOR_PATH)
            s=mk_hex_num(NUM_HEX_INDEXES_FOR_STEP)
            vv=mk_hex_num(NUM_HEX_INDEXES_FOR_VARIANT_VALUE)
            tile_int = int(v+p+s+vv, 16)
            version, path, step, variant = basic_fns.get_tile_variant_ints_from_tile_variant_int(tile_int)
            self.assertEqual(version, int(v,16))
            self.assertEqual(path, int(p,16))
            self.assertEqual(step, int(s,16))
            self.assertEqual(variant, int(vv,16))
    def test_get_tile_variant_ints_from_min_and_max_tile_variants(self):
        version, path, step, variant = basic_fns.get_tile_variant_ints_from_tile_variant_int(0)
        self.assertEqual(version, 0)
        self.assertEqual(path, 0)
        self.assertEqual(step, 0)
        self.assertEqual(variant, 0)
        v='f'*NUM_HEX_INDEXES_FOR_VERSION
        p='f'*NUM_HEX_INDEXES_FOR_PATH
        s='f'*NUM_HEX_INDEXES_FOR_STEP
        vv='f'*NUM_HEX_INDEXES_FOR_VARIANT_VALUE
        tile_int = int(v+p+s+vv, 16)
        version, path, step, variant = basic_fns.get_tile_variant_ints_from_tile_variant_int(tile_int)
        self.assertEqual(version, int(v,16))
        self.assertEqual(path, int(p,16))
        self.assertEqual(step, int(s,16))
        self.assertEqual(variant, int(vv,16))
    def test_get_tile_variant_ints_from_tile_variant_int_failure(self):
        self.assertRaises(TypeError, basic_fns.get_tile_variant_ints_from_tile_variant_int, '10')
        self.assertRaises(ValueError, basic_fns.get_tile_variant_ints_from_tile_variant_int, -1)
        v='f'*NUM_HEX_INDEXES_FOR_VERSION
        p='f'*NUM_HEX_INDEXES_FOR_PATH
        s='f'*NUM_HEX_INDEXES_FOR_STEP
        vv='f'*NUM_HEX_INDEXES_FOR_VARIANT_VALUE
        tile_int = int(v+p+s+vv, 16)
        self.assertRaises(ValueError, basic_fns.get_tile_variant_ints_from_tile_variant_int, tile_int+1)
    #convert_position_int_to_tile_variant_int
    def test_convert_position_int_to_tile_variant_int_type(self):
        tv_int = basic_fns.convert_position_int_to_tile_variant_int(0)
        self.assertIsInstance(tv_int, int)
        tv_int = basic_fns.convert_position_int_to_tile_variant_int(0, variant_value=0)
        self.assertIsInstance(tv_int, int)
        tv_int = basic_fns.convert_position_int_to_tile_variant_int(0, variant_value=1)
        self.assertIsInstance(tv_int, int)
        tv_int = basic_fns.convert_position_int_to_tile_variant_int(0, variant_value=int('f'*NUM_HEX_INDEXES_FOR_VARIANT_VALUE,16))
        self.assertIsInstance(tv_int, int)
    def test_convert_random_position_ints_to_tile_variant_int(self):
        for i in range(NUM_RANDOM_TESTS_TO_RUN):
            v=mk_hex_num(NUM_HEX_INDEXES_FOR_VERSION)
            p=mk_hex_num(NUM_HEX_INDEXES_FOR_PATH)
            s=mk_hex_num(NUM_HEX_INDEXES_FOR_STEP)
            vv=mk_hex_num(NUM_HEX_INDEXES_FOR_VARIANT_VALUE)
            tile_int = int(v+p+s, 16)
            tv_int = basic_fns.convert_position_int_to_tile_variant_int(tile_int, variant_value=int(vv,16))
            self.assertEqual(tv_int, int(v+p+s+vv,16))
    def test_convert_min_and_max_position_ints_to_tile_variant_int(self):
        vv_min = '0'*NUM_HEX_INDEXES_FOR_VARIANT_VALUE
        vv_max = 'f'*NUM_HEX_INDEXES_FOR_VARIANT_VALUE
        tv_int = basic_fns.convert_position_int_to_tile_variant_int(0)
        self.assertEqual(tv_int, 0)
        tv_int = basic_fns.convert_position_int_to_tile_variant_int(0, variant_value=0)
        self.assertEqual(tv_int, 0)
        tv_int = basic_fns.convert_position_int_to_tile_variant_int(0, variant_value=1)
        self.assertEqual(tv_int, 1)
        tv_int = basic_fns.convert_position_int_to_tile_variant_int(0, variant_value=int(vv_max,16))
        self.assertEqual(tv_int, int(vv_max,16))
        v='f'*NUM_HEX_INDEXES_FOR_VERSION
        p='f'*NUM_HEX_INDEXES_FOR_PATH
        s='f'*NUM_HEX_INDEXES_FOR_STEP
        tile_int = int(v+p+s, 16)
        tv_int = basic_fns.convert_position_int_to_tile_variant_int(tile_int)
        self.assertEqual(tv_int, int(v+p+s+vv_min,16))
        tv_int = basic_fns.convert_position_int_to_tile_variant_int(tile_int, variant_value=int(vv_max,16))
        self.assertEqual(tv_int, int(v+p+s+vv_max,16))
    def test_convert_position_int_to_tile_variant_int_failure(self):
        self.assertRaises(TypeError, basic_fns.convert_position_int_to_tile_variant_int, '10')
        self.assertRaises(ValueError, basic_fns.convert_position_int_to_tile_variant_int, -1)
        v='f'*NUM_HEX_INDEXES_FOR_VERSION
        p='f'*NUM_HEX_INDEXES_FOR_PATH
        s='f'*NUM_HEX_INDEXES_FOR_STEP
        tile_int = int(v+p+s, 16)
        self.assertRaises(ValueError, basic_fns.convert_position_int_to_tile_variant_int, tile_int+1)
        self.assertRaises(TypeError, basic_fns.convert_position_int_to_tile_variant_int, 0, variant_value='0')
        self.assertRaises(ValueError, basic_fns.convert_position_int_to_tile_variant_int, 0, variant_value=-1)
        vv_max = int('f'*NUM_HEX_INDEXES_FOR_VARIANT_VALUE,16)
        self.assertRaises(ValueError, basic_fns.convert_position_int_to_tile_variant_int, 0, variant_value=vv_max+1)
    #convert_tile_variant_int_to_position_int
    def test_convert_tile_variant_int_to_position_int_type(self):
        pos_int = basic_fns.convert_tile_variant_int_to_position_int(0)
        self.assertIsInstance(pos_int, int)
    def test_convert_random_tile_variant_ints_to_position_int(self):
        for i in range(NUM_RANDOM_TESTS_TO_RUN):
            v=mk_hex_num(NUM_HEX_INDEXES_FOR_VERSION)
            p=mk_hex_num(NUM_HEX_INDEXES_FOR_PATH)
            s=mk_hex_num(NUM_HEX_INDEXES_FOR_STEP)
            vv=mk_hex_num(NUM_HEX_INDEXES_FOR_VARIANT_VALUE)
            pos_int = basic_fns.convert_tile_variant_int_to_position_int(int(v+p+s+vv, 16))
            self.assertEqual(pos_int, int(v+p+s,16))
    def test_convert_min_and_max_tile_variant_ints_to_position_int(self):
        pos_int = basic_fns.convert_position_int_to_tile_variant_int(0)
        self.assertEqual(pos_int, 0)
        v='f'*NUM_HEX_INDEXES_FOR_VERSION
        p='f'*NUM_HEX_INDEXES_FOR_PATH
        s='f'*NUM_HEX_INDEXES_FOR_STEP
        vv = 'f'*NUM_HEX_INDEXES_FOR_VARIANT_VALUE
        pos_int = basic_fns.convert_tile_variant_int_to_position_int(int(v+p+s+vv, 16))
        self.assertEqual(pos_int, int(v+p+s,16))
    def test_convert_tile_variant_int_to_position_failure(self):
        self.assertRaises(TypeError, basic_fns.convert_tile_variant_int_to_position_int, '10')
        self.assertRaises(ValueError, basic_fns.convert_tile_variant_int_to_position_int, -1)
        v='f'*NUM_HEX_INDEXES_FOR_VERSION
        p='f'*NUM_HEX_INDEXES_FOR_PATH
        s='f'*NUM_HEX_INDEXES_FOR_STEP
        vv = 'f'*NUM_HEX_INDEXES_FOR_VARIANT_VALUE
        max_tv_int = int(v+p+s+vv,16)
        self.assertRaises(ValueError, basic_fns.convert_tile_variant_int_to_position_int, max_tv_int+1)
    def test_get_non_spanning_cgf_string_type(self):
        v='0'*NUM_HEX_INDEXES_FOR_VERSION
        p='0'*NUM_HEX_INDEXES_FOR_PATH
        s='0'*NUM_HEX_INDEXES_FOR_STEP
        vv = '0'*NUM_HEX_INDEXES_FOR_CGF_VARIANT_VALUE
        sv = '0'
        cgf_str = basic_fns.get_non_spanning_cgf_string(string.join([p,v,s,vv],sep='.'))
        self.assertIsInstance(cgf_str, str)
        cgf_str = basic_fns.get_non_spanning_cgf_string(string.join([p,v,s,vv],sep='.')+'+'+sv)
        self.assertIsInstance(cgf_str, str)
        cgf_str = basic_fns.get_non_spanning_cgf_string(unicode(string.join([p,v,s,vv],sep='.')))
        self.assertIsInstance(cgf_str, str)
        cgf_str = basic_fns.get_non_spanning_cgf_string(unicode(string.join([p,v,s,vv],sep='.')+'+'+sv))
        self.assertIsInstance(cgf_str, str)
    def test_get_non_spanning_cgf_strings(self):
        for i in range(NUM_RANDOM_TESTS_TO_RUN):
            v=mk_hex_num(NUM_HEX_INDEXES_FOR_VERSION)
            p=mk_hex_num(NUM_HEX_INDEXES_FOR_PATH)
            s=mk_hex_num(NUM_HEX_INDEXES_FOR_STEP)
            vv=mk_hex_num(NUM_HEX_INDEXES_FOR_CGF_VARIANT_VALUE)
            sv=mk_hex_num(NUM_HEX_INDEXES_FOR_CGF_VARIANT_VALUE)
            cgf_str = basic_fns.get_non_spanning_cgf_string(string.join([p,v,s,vv],sep='.'))
            self.assertEqual(cgf_str, string.join([p,v,s,vv], sep='.'))
            cgf_str = basic_fns.get_non_spanning_cgf_string(string.join([p,v,s,vv],sep='.')+'+'+sv)
            self.assertEqual(cgf_str, string.join([p,v,s,vv], sep='.'))
    def test_get_non_spanning_cgf_string_from_min_and_max_cgf_strings(self):
        v='0'*NUM_HEX_INDEXES_FOR_VERSION
        p='0'*NUM_HEX_INDEXES_FOR_PATH
        s='0'*NUM_HEX_INDEXES_FOR_STEP
        vv = '0'*NUM_HEX_INDEXES_FOR_CGF_VARIANT_VALUE
        cgf_str = basic_fns.get_non_spanning_cgf_string(string.join([p,v,s,vv],sep='.'))
        self.assertEqual(cgf_str, string.join([p,v,s,vv], sep='.'))
        cgf_str = basic_fns.get_non_spanning_cgf_string(string.join([p,v,s,vv],sep='.')+'+0')
        self.assertEqual(cgf_str, string.join([p,v,s,vv], sep='.'))
        cgf_str = basic_fns.get_non_spanning_cgf_string(string.join([p,v,s,vv],sep='.')+'+fff')
        self.assertEqual(cgf_str, string.join([p,v,s,vv], sep='.'))
        v='f'*NUM_HEX_INDEXES_FOR_VERSION
        p='f'*NUM_HEX_INDEXES_FOR_PATH
        s='f'*NUM_HEX_INDEXES_FOR_STEP
        vv = 'f'*NUM_HEX_INDEXES_FOR_CGF_VARIANT_VALUE
        cgf_str = basic_fns.get_non_spanning_cgf_string(string.join([p,v,s,vv],sep='.'))
        self.assertEqual(cgf_str, string.join([p,v,s,vv], sep='.'))
        cgf_str = basic_fns.get_non_spanning_cgf_string(string.join([p,v,s,vv],sep='.')+'+0')
        self.assertEqual(cgf_str, string.join([p,v,s,vv], sep='.'))
        cgf_str = basic_fns.get_non_spanning_cgf_string(string.join([p,v,s,vv],sep='.')+'+fff')
        self.assertEqual(cgf_str, string.join([p,v,s,vv], sep='.'))
    def test_get_non_spanning_cgf_string_failure(self):
        self.assertRaises(TypeError, basic_fns.get_non_spanning_cgf_string, 0)
        v='0'*NUM_HEX_INDEXES_FOR_VERSION
        p='0'*NUM_HEX_INDEXES_FOR_PATH
        s='0'*NUM_HEX_INDEXES_FOR_STEP
        vv = '0'*(NUM_HEX_INDEXES_FOR_CGF_VARIANT_VALUE-1)
        vv2 = 'x'*NUM_HEX_INDEXES_FOR_CGF_VARIANT_VALUE
        self.assertRaises(ValueError, basic_fns.get_non_spanning_cgf_string, string.join([p,v,s],sep='.'))
        self.assertRaises(ValueError, basic_fns.get_non_spanning_cgf_string, string.join([p,v,s,vv],sep='.'))
        self.assertRaises(ValueError, basic_fns.get_non_spanning_cgf_string, string.join([p,v,s,vv2],sep='.'))
        self.assertRaises(ValueError, basic_fns.get_non_spanning_cgf_string, string.join([p,v,s,vv+'0'],sep='.')+'+')
        self.assertRaises(ValueError, basic_fns.get_non_spanning_cgf_string, string.join([v,p,s,vv+'0'],sep='.'))
        self.assertRaises(ValueError, basic_fns.get_non_spanning_cgf_string, string.join([p,v,s,vv+'0'],sep='.')+'+x')
    #get_position_from_cgf_string
    def test_get_position_from_cgf_string_type(self):
        v='0'*NUM_HEX_INDEXES_FOR_VERSION
        p='0'*NUM_HEX_INDEXES_FOR_PATH
        s='0'*NUM_HEX_INDEXES_FOR_STEP
        vv = '0'*NUM_HEX_INDEXES_FOR_CGF_VARIANT_VALUE
        sv = '0'
        pos_int = basic_fns.get_position_from_cgf_string(string.join([p,v,s,vv],sep='.'))
        self.assertIsInstance(pos_int, int)
        pos_int = basic_fns.get_position_from_cgf_string(string.join([p,v,s,vv],sep='.')+'+'+sv)
        self.assertIsInstance(pos_int, int)
        pos_int = basic_fns.get_position_from_cgf_string(unicode(string.join([p,v,s,vv],sep='.')))
        self.assertIsInstance(pos_int, int)
        pos_int = basic_fns.get_position_from_cgf_string(unicode(string.join([p,v,s,vv],sep='.')+'+'+sv))
        self.assertIsInstance(pos_int, int)
    def test_get_position_from_random_cgf_strings(self):
        for i in range(NUM_RANDOM_TESTS_TO_RUN):
            v=mk_hex_num(NUM_HEX_INDEXES_FOR_VERSION)
            p=mk_hex_num(NUM_HEX_INDEXES_FOR_PATH)
            s=mk_hex_num(NUM_HEX_INDEXES_FOR_STEP)
            vv=mk_hex_num(NUM_HEX_INDEXES_FOR_CGF_VARIANT_VALUE)
            sv=mk_hex_num(NUM_HEX_INDEXES_FOR_CGF_VARIANT_VALUE)
            pos_int = basic_fns.get_position_from_cgf_string(string.join([p,v,s,vv],sep='.'))
            self.assertEqual(pos_int, int(v+p+s,16))
            pos_int = basic_fns.get_position_from_cgf_string(string.join([p,v,s,vv],sep='.')+'+'+sv)
            self.assertEqual(pos_int, int(v+p+s,16))
    def test_get_position_from_min_and_max_cgf_strings(self):
        v='0'*NUM_HEX_INDEXES_FOR_VERSION
        p='0'*NUM_HEX_INDEXES_FOR_PATH
        s='0'*NUM_HEX_INDEXES_FOR_STEP
        vv = '0'*NUM_HEX_INDEXES_FOR_CGF_VARIANT_VALUE
        pos_int = basic_fns.get_position_from_cgf_string(string.join([p,v,s,vv],sep='.'))
        self.assertEqual(pos_int, 0)
        pos_int = basic_fns.get_position_from_cgf_string(string.join([p,v,s,vv],sep='.')+'+0')
        self.assertEqual(pos_int, 0)
        pos_int = basic_fns.get_position_from_cgf_string(string.join([p,v,s,vv],sep='.')+'+fff')
        self.assertEqual(pos_int, 0)
        v='f'*NUM_HEX_INDEXES_FOR_VERSION
        p='f'*NUM_HEX_INDEXES_FOR_PATH
        s='f'*NUM_HEX_INDEXES_FOR_STEP
        vv = 'f'*NUM_HEX_INDEXES_FOR_CGF_VARIANT_VALUE
        pos_int = basic_fns.get_position_from_cgf_string(string.join([p,v,s,vv],sep='.'))
        self.assertEqual(pos_int, int(v+p+s,16))
        pos_int = basic_fns.get_position_from_cgf_string(string.join([p,v,s,vv],sep='.')+'+0')
        self.assertEqual(pos_int, int(v+p+s,16))
        pos_int = basic_fns.get_position_from_cgf_string(string.join([p,v,s,vv],sep='.')+'+fff')
        self.assertEqual(pos_int, int(v+p+s,16))
    def test_get_position_from_cgf_string_failure(self):
        self.assertRaises(TypeError, basic_fns.get_position_from_cgf_string, 0)
        v='0'*NUM_HEX_INDEXES_FOR_VERSION
        p='0'*NUM_HEX_INDEXES_FOR_PATH
        s='0'*NUM_HEX_INDEXES_FOR_STEP
        vv = '0'*(NUM_HEX_INDEXES_FOR_CGF_VARIANT_VALUE-1)
        vv2 = 'x'*NUM_HEX_INDEXES_FOR_CGF_VARIANT_VALUE
        self.assertRaises(ValueError, basic_fns.get_position_from_cgf_string, string.join([p,v,s],sep='.'))
        self.assertRaises(ValueError, basic_fns.get_position_from_cgf_string, string.join([p,v,s,vv],sep='.'))
        self.assertRaises(ValueError, basic_fns.get_position_from_cgf_string, string.join([p,v,s,vv2],sep='.'))
        self.assertRaises(ValueError, basic_fns.get_position_from_cgf_string, string.join([p,v,s,vv+'0'],sep='.')+'+')
        self.assertRaises(ValueError, basic_fns.get_position_from_cgf_string, string.join([v,p,s,vv+'0'],sep='.'))
        self.assertRaises(ValueError, basic_fns.get_position_from_cgf_string, string.join([p,v,s,vv+'0'],sep='.')+'+x')
    #get_number_of_tiles_spanned_from_cgf_string
    def test_get_number_of_tiles_spanned_from_cgf_string_type(self):
        v='0'*NUM_HEX_INDEXES_FOR_VERSION
        p='0'*NUM_HEX_INDEXES_FOR_PATH
        s='0'*NUM_HEX_INDEXES_FOR_STEP
        vv = '0'*NUM_HEX_INDEXES_FOR_CGF_VARIANT_VALUE
        sv = '0'
        n = basic_fns.get_number_of_tiles_spanned_from_cgf_string(string.join([p,v,s,vv],sep='.'))
        self.assertIsInstance(n, int)
        n = basic_fns.get_number_of_tiles_spanned_from_cgf_string(string.join([p,v,s,vv],sep='.')+'+'+sv)
        self.assertIsInstance(n, int)
        n = basic_fns.get_number_of_tiles_spanned_from_cgf_string(unicode(string.join([p,v,s,vv],sep='.')))
        self.assertIsInstance(n, int)
        n = basic_fns.get_number_of_tiles_spanned_from_cgf_string(unicode(string.join([p,v,s,vv],sep='.')+'+'+sv))
        self.assertIsInstance(n, int)
    def test_get_number_of_tiles_spanned_from_random_cgf_strings(self):
        for i in range(NUM_RANDOM_TESTS_TO_RUN):
            v=mk_hex_num(NUM_HEX_INDEXES_FOR_VERSION)
            p=mk_hex_num(NUM_HEX_INDEXES_FOR_PATH)
            s=mk_hex_num(NUM_HEX_INDEXES_FOR_STEP)
            vv=mk_hex_num(NUM_HEX_INDEXES_FOR_CGF_VARIANT_VALUE)
            sv=mk_hex_num(NUM_HEX_INDEXES_FOR_CGF_VARIANT_VALUE)
            n = basic_fns.get_number_of_tiles_spanned_from_cgf_string(string.join([p,v,s,vv],sep='.'))
            self.assertEqual(n, 1)
            n = basic_fns.get_number_of_tiles_spanned_from_cgf_string(string.join([p,v,s,vv],sep='.')+'+'+sv)
            self.assertEqual(n, int(sv,16))
    def test_get_number_of_tiles_spanned_from_min_and_max_cgf_strings(self):
        v='0'*NUM_HEX_INDEXES_FOR_VERSION
        p='0'*NUM_HEX_INDEXES_FOR_PATH
        s='0'*NUM_HEX_INDEXES_FOR_STEP
        vv = '0'*NUM_HEX_INDEXES_FOR_CGF_VARIANT_VALUE
        n = basic_fns.get_number_of_tiles_spanned_from_cgf_string(string.join([p,v,s,vv],sep='.'))
        self.assertEqual(n, 1)
        n = basic_fns.get_number_of_tiles_spanned_from_cgf_string(string.join([p,v,s,vv],sep='.')+'+0')
        self.assertEqual(n, 0)
        n = basic_fns.get_number_of_tiles_spanned_from_cgf_string(string.join([p,v,s,vv],sep='.')+'+fff')
        self.assertEqual(n, int('fff',16))
        v='f'*NUM_HEX_INDEXES_FOR_VERSION
        p='f'*NUM_HEX_INDEXES_FOR_PATH
        s='f'*NUM_HEX_INDEXES_FOR_STEP
        vv = 'f'*NUM_HEX_INDEXES_FOR_CGF_VARIANT_VALUE
        n = basic_fns.get_number_of_tiles_spanned_from_cgf_string(string.join([p,v,s,vv],sep='.'))
        self.assertEqual(n,1)
        n = basic_fns.get_number_of_tiles_spanned_from_cgf_string(string.join([p,v,s,vv],sep='.')+'+0')
        self.assertEqual(n, 0)
        n = basic_fns.get_number_of_tiles_spanned_from_cgf_string(string.join([p,v,s,vv],sep='.')+'+fff')
        self.assertEqual(n, int('fff', 16))
    def test_get_number_of_tiles_spanned_from_cgf_string_failure(self):
        self.assertRaises(TypeError, basic_fns.get_number_of_tiles_spanned_from_cgf_string, 0)
        v='0'*NUM_HEX_INDEXES_FOR_VERSION
        p='0'*NUM_HEX_INDEXES_FOR_PATH
        s='0'*NUM_HEX_INDEXES_FOR_STEP
        vv = '0'*(NUM_HEX_INDEXES_FOR_CGF_VARIANT_VALUE-1)
        vv2 = 'x'*NUM_HEX_INDEXES_FOR_CGF_VARIANT_VALUE
        self.assertRaises(ValueError, basic_fns.get_number_of_tiles_spanned_from_cgf_string, string.join([p,v,s],sep='.'))
        self.assertRaises(ValueError, basic_fns.get_number_of_tiles_spanned_from_cgf_string, string.join([p,v,s,vv],sep='.'))
        self.assertRaises(ValueError, basic_fns.get_number_of_tiles_spanned_from_cgf_string, string.join([p,v,s,vv2],sep='.'))
        self.assertRaises(ValueError, basic_fns.get_number_of_tiles_spanned_from_cgf_string, string.join([p,v,s,vv+'0'],sep='.')+'+')
        self.assertRaises(ValueError, basic_fns.get_number_of_tiles_spanned_from_cgf_string, string.join([v,p,s,vv+'0'],sep='.'))
        self.assertRaises(ValueError, basic_fns.get_number_of_tiles_spanned_from_cgf_string, string.join([p,v,s,vv+'0'],sep='.')+'+x')
    #get_min_position_and_tile_variant_from_path_int
    def test_get_min_position_and_tile_variant_from_path_int_type(self):
        pos, tv = basic_fns.get_min_position_and_tile_variant_from_path_int(0)
        self.assertIsInstance(pos, int)
        self.assertIsInstance(tv, int)
        pos, tv = basic_fns.get_min_position_and_tile_variant_from_path_int(0, path_version=0)
        self.assertIsInstance(pos, int)
        self.assertIsInstance(tv, int)
        pos, tv = basic_fns.get_min_position_and_tile_variant_from_path_int(0, path_version=1)
        self.assertIsInstance(pos, int)
        self.assertIsInstance(tv, int)
    def test_get_min_position_and_tile_variant_from_random_path_ints(self):
        for i in range(NUM_RANDOM_TESTS_TO_RUN):
            v=mk_hex_num(NUM_HEX_INDEXES_FOR_VERSION)
            v_0 = '0'*NUM_HEX_INDEXES_FOR_VERSION
            p=hex(random.randrange(settings.CHR_PATH_LENGTHS[-1]+1)).lstrip('0x').zfill(NUM_HEX_INDEXES_FOR_PATH)
            s='0'*NUM_HEX_INDEXES_FOR_STEP
            vv='0'*NUM_HEX_INDEXES_FOR_VARIANT_VALUE
            pos, tv = basic_fns.get_min_position_and_tile_variant_from_path_int(int(p,16))
            self.assertEqual(pos, int(v_0+p+s, 16))
            self.assertEqual(tv, int(v_0+p+s+vv, 16))
            pos, tv = basic_fns.get_min_position_and_tile_variant_from_path_int(int(p,16), path_version=int(v,16))
            self.assertEqual(pos, int(v+p+s, 16))
            self.assertEqual(tv, int(v+p+s+vv, 16))
    def test_get_min_position_and_tile_variant_from_min_and_max_path_int(self):
        v_min='0'*NUM_HEX_INDEXES_FOR_VERSION
        v_max='f'*NUM_HEX_INDEXES_FOR_VERSION
        p='0'*NUM_HEX_INDEXES_FOR_PATH
        s='0'*NUM_HEX_INDEXES_FOR_STEP
        vv='0'*NUM_HEX_INDEXES_FOR_VARIANT_VALUE
        pos, tv = basic_fns.get_min_position_and_tile_variant_from_path_int(int(p,16))
        self.assertEqual(pos, 0)
        self.assertEqual(tv, 0)
        pos, tv = basic_fns.get_min_position_and_tile_variant_from_path_int(int(p,16), path_version=int(v_max,16))
        self.assertEqual(pos, int(v_max+p+s, 16))
        self.assertEqual(tv, int(v_max+p+s+vv, 16))
        p=hex(settings.CHR_PATH_LENGTHS[-1]).lstrip('0x').zfill(NUM_HEX_INDEXES_FOR_PATH)
        pos, tv = basic_fns.get_min_position_and_tile_variant_from_path_int(int(p,16))
        self.assertEqual(pos, int(v_min+p+s, 16))
        self.assertEqual(tv, int(v_min+p+s+vv, 16))
        pos, tv = basic_fns.get_min_position_and_tile_variant_from_path_int(int(p,16), path_version=int(v_max,16))
        self.assertEqual(pos, int(v_max+p+s, 16))
        self.assertEqual(tv, int(v_max+p+s+vv, 16))
    def test_get_min_position_and_tile_variant_from_path_int_failure(self):
        self.assertRaises(TypeError, basic_fns.get_min_position_and_tile_variant_from_path_int, '1')
        self.assertRaises(ValueError, basic_fns.get_min_position_and_tile_variant_from_path_int, -1)
        bad_path = settings.CHR_PATH_LENGTHS[-1] + 1
        self.assertRaises(ValueError, basic_fns.get_min_position_and_tile_variant_from_path_int, bad_path)
    #Is it acceptable to use an already tested function to check against another function?
    def test_get_min_position_and_tile_variant_from_chromosome_int(self):
        for i, path_int in enumerate(settings.CHR_PATH_LENGTHS):
            name, varname = basic_fns.get_min_position_and_tile_variant_from_chromosome_int(i+1)
            exp_name, exp_varname = basic_fns.get_min_position_and_tile_variant_from_path_int(int(path_int))
            self.assertEqual(name, exp_name)
            self.assertEqual(varname, exp_varname)
    def test_get_min_position_and_tile_variant_from_chromosome_int_failure(self):
        self.assertRaises(TypeError, basic_fns.get_min_position_and_tile_variant_from_chromosome_int, '1')
        self.assertRaises(ValueError, basic_fns.get_min_position_and_tile_variant_from_chromosome_int, CHR_1-1)
        self.assertRaises(ValueError, basic_fns.get_min_position_and_tile_variant_from_chromosome_int, CHR_NONEXISTANT+1)
    #Feels a bit weird because the last populated path is 25, but technical last path is 26..
    #get_chromosome_int_from_position_int
    def test_get_chromosome_int_from_position_int_type(self):
        c = basic_fns.get_chromosome_int_from_position_int(0)
        self.assertIsInstance(c, int)
    def test_get_chromosome_int_from_position_ints(self):
        def get_path_hex(path):
            return hex(path).lstrip('0x').zfill(NUM_HEX_INDEXES_FOR_PATH)
        v_min='0'*NUM_HEX_INDEXES_FOR_VERSION
        v_max='f'*NUM_HEX_INDEXES_FOR_VERSION
        s_min='0'*NUM_HEX_INDEXES_FOR_STEP
        s_max='f'*NUM_HEX_INDEXES_FOR_STEP

        path_in_one = get_path_hex(0)
        c = basic_fns.get_chromosome_int_from_position_int(int(v_min+path_in_one+s_min,16))
        self.assertEqual(c, CHR_1)
        c = basic_fns.get_chromosome_int_from_position_int(int(v_max+path_in_one+s_max,16))
        self.assertEqual(c, CHR_1)

        path_in_one = get_path_hex(settings.CHR_PATH_LENGTHS[1]/2)
        c = basic_fns.get_chromosome_int_from_position_int(int(v_min+path_in_one+s_min,16))
        self.assertEqual(c, CHR_1)
        c = basic_fns.get_chromosome_int_from_position_int(int(v_max+path_in_one+s_max,16))
        self.assertEqual(c, CHR_1)

        path_in_two = get_path_hex(settings.CHR_PATH_LENGTHS[1])
        c = basic_fns.get_chromosome_int_from_position_int(int(v_min+path_in_two+s_min,16))
        self.assertEqual(c, CHR_2)
        c = basic_fns.get_chromosome_int_from_position_int(int(v_max+path_in_two+s_max,16))
        self.assertEqual(c, CHR_2)

        path_in_last = get_path_hex(settings.CHR_PATH_LENGTHS[-3])
        c = basic_fns.get_chromosome_int_from_position_int(int(v_min+path_in_last+s_min,16))
        self.assertEqual(c, CHR_M)
        c = basic_fns.get_chromosome_int_from_position_int(int(v_max+path_in_last+s_max,16))
        self.assertEqual(c, CHR_M)
    def test_get_chromosome_int_from_position_int_failure(self):
        self.assertRaises(TypeError, basic_fns.get_chromosome_int_from_position_int, '0')
        self.assertRaises(ValueError, basic_fns.get_chromosome_int_from_position_int, -1)
        bad_path = settings.CHR_PATH_LENGTHS[-1] + 1
        v='0'*NUM_HEX_INDEXES_FOR_VERSION
        p=hex(bad_path).lstrip('0x').zfill(NUM_HEX_INDEXES_FOR_PATH)
        s='0'*NUM_HEX_INDEXES_FOR_STEP
        self.assertRaises(ValueError, basic_fns.get_chromosome_int_from_position_int, int(v+p+s,16))
    #get_chromosome_int_from_tile_variant_int
    def test_get_chromosome_int_from_tile_variant_int_type(self):
        c = basic_fns.get_chromosome_int_from_tile_variant_int(0)
        self.assertIsInstance(c, int)
    def test_get_chromosome_int_from_tile_variant_ints(self):
        def get_path_hex(path):
            return hex(path).lstrip('0x').zfill(NUM_HEX_INDEXES_FOR_PATH)
        v_min='0'*NUM_HEX_INDEXES_FOR_VERSION
        v_max='f'*NUM_HEX_INDEXES_FOR_VERSION
        s_min='0'*NUM_HEX_INDEXES_FOR_STEP
        s_max='f'*NUM_HEX_INDEXES_FOR_STEP
        vv_min='0'*NUM_HEX_INDEXES_FOR_VARIANT_VALUE
        vv_max='f'*NUM_HEX_INDEXES_FOR_VARIANT_VALUE
        path_in_one = get_path_hex(0)
        c = basic_fns.get_chromosome_int_from_tile_variant_int(int(v_min+path_in_one+s_min+vv_min,16))
        self.assertEqual(c, CHR_1)
        c = basic_fns.get_chromosome_int_from_tile_variant_int(int(v_max+path_in_one+s_max+vv_max,16))
        self.assertEqual(c, CHR_1)

        path_in_one = get_path_hex(settings.CHR_PATH_LENGTHS[1]/2)
        c = basic_fns.get_chromosome_int_from_tile_variant_int(int(v_min+path_in_one+s_min+vv_min,16))
        self.assertEqual(c, CHR_1)
        c = basic_fns.get_chromosome_int_from_tile_variant_int(int(v_max+path_in_one+s_max+vv_max,16))
        self.assertEqual(c, CHR_1)

        path_in_two = get_path_hex(settings.CHR_PATH_LENGTHS[1])
        c = basic_fns.get_chromosome_int_from_tile_variant_int(int(v_min+path_in_two+s_min+vv_min,16))
        self.assertEqual(c, CHR_2)
        c = basic_fns.get_chromosome_int_from_tile_variant_int(int(v_max+path_in_two+s_max+vv_max,16))
        self.assertEqual(c, CHR_2)

        path_in_last = get_path_hex(settings.CHR_PATH_LENGTHS[-3])
        c = basic_fns.get_chromosome_int_from_tile_variant_int(int(v_min+path_in_last+s_min+vv_min,16))
        self.assertEqual(c, CHR_M)
        c = basic_fns.get_chromosome_int_from_tile_variant_int(int(v_max+path_in_last+s_max+vv_max,16))
        self.assertEqual(c, CHR_M)
    def test_get_chromosome_int_from_tile_variant_int_failure(self):
        self.assertRaises(TypeError, basic_fns.get_chromosome_int_from_tile_variant_int, '0')
        self.assertRaises(ValueError, basic_fns.get_chromosome_int_from_tile_variant_int, -1)
        bad_path = settings.CHR_PATH_LENGTHS[-1]+1
        v='0'*NUM_HEX_INDEXES_FOR_VERSION
        p=hex(bad_path).lstrip('0x').zfill(NUM_HEX_INDEXES_FOR_PATH)
        s='0'*NUM_HEX_INDEXES_FOR_STEP
        vv='0'*NUM_HEX_INDEXES_FOR_VARIANT_VALUE
        self.assertRaises(ValueError, basic_fns.get_chromosome_int_from_tile_variant_int, int(v+p+s+vv,16))
    #Feels a bit weird because the last populated path is 25, but technical last path is 26...
    def test_get_chromosome_int_from_path_int(self):
        path_in_one = settings.CHR_PATH_LENGTHS[1]/2
        self.assertEqual(basic_fns.get_chromosome_int_from_path_int(path_in_one), CHR_1)
        path_in_one = 0
        self.assertEqual(basic_fns.get_chromosome_int_from_path_int(path_in_one), CHR_1)
        path_in_two = settings.CHR_PATH_LENGTHS[1]
        self.assertEqual(basic_fns.get_chromosome_int_from_path_int(path_in_two), CHR_2)
        path_in_last = settings.CHR_PATH_LENGTHS[-3]
        self.assertEqual(basic_fns.get_chromosome_int_from_path_int(path_in_last), CHR_M)
    def test_get_chromosome_int_from_path_int_failure(self):
        self.assertRaises(TypeError, basic_fns.get_chromosome_int_from_path_int, '0')
        self.assertRaises(ValueError, basic_fns.get_chromosome_int_from_path_int, -1)
        bad_path = settings.CHR_PATH_LENGTHS[-1] +1
        self.assertRaises(ValueError, basic_fns.get_chromosome_int_from_path_int, bad_path)
################################## TEST Tile model ###################################
## Currently unable to test the validity of the tile_library
##  (ie. 1 'is_start_of_path' and 1 'is_end_of_path')
##  (The path starts at tile position 0 and increments by one each time)
class TestTileModel(TestCase):
    def test_get_string_type(self):
        new_tile = Tile(tile_position_int=0)
        self.assertIsInstance(new_tile.get_string(), str)
    def test_get_string_random_tiles(self):
        for i in range(NUM_RANDOM_TESTS_TO_RUN):
            v=mk_hex_num(NUM_HEX_INDEXES_FOR_VERSION)
            p=mk_hex_num(NUM_HEX_INDEXES_FOR_PATH)
            s=mk_hex_num(NUM_HEX_INDEXES_FOR_STEP)
            new_tile = Tile(tile_position_int=int(v+p+s,16))
            self.assertEqual(new_tile.get_string(), string.join([v,p,s],sep='.'))
    def test_get_string_from_max_and_min_tiles(self):
        new_tile = Tile(tile_position_int=int(version_min+path_min+step_min,16))
        self.assertEqual(new_tile.get_string(), string.join([version_min,path_min,step_min],sep='.'))
        new_tile = Tile(tile_position_int=int(version_max+theoretical_path_max+step_max,16))
        self.assertEqual(new_tile.get_string(), string.join([version_max,theoretical_path_max,step_max],sep='.'))
    def test_non_int_tile_int(self):
        with self.assertRaises(ValidationError) as cm:
            Tile(tile_position_int='invalid', start_tag="a"*TAG_LENGTH, end_tag="a"*TAG_LENGTH).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('tile_position_int', cm.exception.message_dict)
    def test_negative_tile_int(self):
        with self.assertRaises(ValidationError) as cm:
            Tile(tile_position_int=-1, start_tag="a"*TAG_LENGTH, end_tag="a"*TAG_LENGTH).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('tile_position_int', cm.exception.message_dict)
    def test_too_big_tile_int(self):
        with self.assertRaises(ValidationError) as cm:
            tile_int = int('f'*(NUM_HEX_INDEXES_FOR_VERSION+NUM_HEX_INDEXES_FOR_PATH+NUM_HEX_INDEXES_FOR_STEP), 16)
            Tile(tile_position_int=tile_int+1, start_tag="a"*TAG_LENGTH, end_tag="a"*TAG_LENGTH).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('tile_position_int', cm.exception.message_dict)
    def test_too_short_tags(self):
        with self.assertRaises(ValidationError) as cm:
            Tile(tile_position_int=1, start_tag='aa', end_tag='ag').save()
        self.assertEqual(len(cm.exception.message_dict), 2)
        self.assertIn('start_tag', cm.exception.message_dict)
        self.assertIn('TAG_LENGTH', str(cm.exception.message_dict['start_tag']))
        self.assertIn('end_tag', cm.exception.message_dict)
        self.assertIn('TAG_LENGTH', str(cm.exception.message_dict['end_tag']))
    def test_uppercase_tags(self):
        with self.assertRaises(ValidationError) as cm:
            Tile(tile_position_int=1, start_tag='A'*(TAG_LENGTH), end_tag='G'*TAG_LENGTH).save()
        self.assertEqual(len(cm.exception.message_dict), 2)
        self.assertIn('start_tag', cm.exception.message_dict)
        self.assertIn('case', str(cm.exception.message_dict['start_tag']))
        self.assertIn('end_tag', cm.exception.message_dict)
        self.assertIn('case', str(cm.exception.message_dict['end_tag']))
    def test_failure_step_is_zero_but_not_start_of_path(self):
        with self.assertRaises(ValidationError) as cm:
            Tile(tile_position_int=0, start_tag='a'*(TAG_LENGTH), end_tag='a'*TAG_LENGTH, is_start_of_path=False).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('tile_position_int-is_start_of_path', cm.exception.message_dict)
    def test_failure_step_is_not_zero_but_is_start_of_path(self):
        with self.assertRaises(ValidationError) as cm:
            Tile(tile_position_int=1, end_tag='a'*TAG_LENGTH, is_start_of_path=True).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('tile_position_int-is_start_of_path', cm.exception.message_dict)
    def test_failure_start_of_path_with_defined_start_tag(self):
        with self.assertRaises(ValidationError) as cm:
            Tile(tile_position_int=0, start_tag='a'*(TAG_LENGTH), end_tag='a'*TAG_LENGTH, is_start_of_path=True).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('start_tag-is_start_of_path', cm.exception.message_dict)
    def test_failure_end_of_path_with_defined_end_tag(self):
        with self.assertRaises(ValidationError) as cm:
            Tile(tile_position_int=1, start_tag='a'*(TAG_LENGTH), end_tag='a'*TAG_LENGTH, is_end_of_path=True).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('end_tag-is_end_of_path', cm.exception.message_dict)
    def test_failure_middle_of_path_without_tags(self):
        with self.assertRaises(ValidationError) as cm:
            Tile(tile_position_int=1).save()
        self.assertEqual(len(cm.exception.message_dict), 2)
        self.assertIn('start_tag-is_start_of_path', cm.exception.message_dict)
        self.assertIn('empty', str(cm.exception.message_dict['start_tag-is_start_of_path']))
        self.assertIn('end_tag-is_end_of_path', cm.exception.message_dict)
        self.assertIn('empty', str(cm.exception.message_dict['end_tag-is_end_of_path']))
    def test_successful_save(self):
        make_tile_position(0)
    def test_successful_save_of_tile_that_is_both_start_and_end_of_path(self):
        Tile(tile_position_int=0, is_start_of_path=True, is_end_of_path=True).save()
    def test_same_name_space_failure(self):
        make_tile_position(0)
        with self.assertRaises(ValidationError) as cm:
            make_tile_position(0)
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('tile_position_int', cm.exception.message_dict)
################################## TEST TileLocusAnnotation model ###################################
class TestTileLocusAnnotationModel(TestCase):
    def test_non_int_assembly(self):
        tile, tilevar = make_tile_position_and_variant(0, 0, 250)
        with self.assertRaises(ValidationError) as cm:
            TileLocusAnnotation(assembly_int="hg19", chromosome_int=CHR_1, start_int=0, end_int=250, tile_position=tile, tile_variant_value=0).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('assembly_int', cm.exception.message_dict)
    @skipIf(0 in settings.SUPPORTED_ASSEMBLY_CHOICES, "Testing behavior for saving an unknown assembly, but 0 is in settings.SUPPORTED_ASSEMBLY_CHOICES")
    def test_unknown_assembly(self):
        tile, tilevar = make_tile_position_and_variant(0, 0, 250)
        with self.assertRaises(ValidationError) as cm:
            TileLocusAnnotation(assembly_int=0, chromosome_int=CHR_1, start_int=0, end_int=250, tile_position=tile, tile_variant_value=0).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('assembly_int', cm.exception.message_dict)
    def test_non_int_chromosome(self):
        tile, tilevar = make_tile_position_and_variant(0, 0, 250)
        with self.assertRaises(ValidationError) as cm:
            TileLocusAnnotation(assembly_int=ASSEMBLY_19, chromosome_int="chr1", start_int=0, end_int=250, tile_position=tile, tile_variant_value=0).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('chromosome_int', cm.exception.message_dict)
    @skipIf(0 in settings.CHR_CHOICES, "Testing behavior for saving an unknown chromosome, but 0 is in settings.CHR_CHOICES")
    def test_unknown_chromosome(self):
        tile, tilevar = make_tile_position_and_variant(0, 0, 250)
        with self.assertRaises(ValidationError) as cm:
            TileLocusAnnotation(assembly_int=ASSEMBLY_19, chromosome_int=0, start_int=0, end_int=250, tile_position=tile, tile_variant_value=0).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('chromosome_int', cm.exception.message_dict)
    def test_missing_tile(self):
        with self.assertRaises(ValidationError) as cm:
            TileLocusAnnotation(assembly_int=ASSEMBLY_19, chromosome_int=CHR_1, start_int=0, end_int=250, tile_variant_value=0).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('tile_position', cm.exception.message_dict)
    def test_missing_tile_variant(self):
        tile = make_tile_position(0)
        with self.assertRaises(ValidationError) as cm:
            TileLocusAnnotation(assembly_int=ASSEMBLY_19, chromosome_int=CHR_1, start_int=0, end_int=250, tile_position=tile, tile_variant_value=0).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('tile_variant_value', cm.exception.message_dict)
    def test_wrong_tile_variant(self):
        tile, tilevar = make_tile_position_and_variant(0, 0, 250)
        with self.assertRaises(ValidationError) as cm:
            TileLocusAnnotation(assembly_int=ASSEMBLY_19, chromosome_int=CHR_1, start_int=0, end_int=250, tile_position=tile, tile_variant_value=1).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('tile_variant_value', cm.exception.message_dict)
    def test_wrong_tile_variant_where_both_variants_exist(self):
        tile, tilevar = make_tile_position_and_variant(0, 0, 250)
        tilevar2 = make_tile_variant(tile, tile, 1, 249)
        with self.assertRaises(ValidationError) as cm:
            TileLocusAnnotation(assembly_int=ASSEMBLY_19, chromosome_int=CHR_1, start_int=0, end_int=250, tile_position=tile, tile_variant_value=1).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('tile_length_locus_mismatch', cm.exception.message_dict)
    def test_begin_int_bigger_than_end_int(self):
        tile, tilevar = make_tile_position_and_variant(0, 0, 250)
        with self.assertRaises(ValidationError) as cm:
            TileLocusAnnotation(assembly_int=ASSEMBLY_19, chromosome_int=CHR_1, start_int=250, end_int=0, tile_position=tile, tile_variant_value=0).save()
        self.assertEqual(len(cm.exception.message_dict), 3)
        self.assertIn('malformed_locus', cm.exception.message_dict)
        self.assertIn('tile_length_locus_mismatch', cm.exception.message_dict) #this cannot be avoided because of assumption start_int < end_int
        self.assertIn('short_locus', cm.exception.message_dict) #this cannot be avoided because of assumption start_int < end_int
    def test_tile_smaller_than_tag_length(self):
        tile, tilevar = make_tile_position_and_variant(0, 0, TAG_LENGTH*2)
        with self.assertRaises(ValidationError) as cm:
            TileLocusAnnotation(assembly_int=ASSEMBLY_19, chromosome_int=CHR_1, start_int=0, end_int=TAG_LENGTH, tile_position=tile, tile_variant_value=0).save()
        self.assertEqual(len(cm.exception.message_dict), 2)
        self.assertIn('short_locus', cm.exception.message_dict)
        self.assertIn('tile_length_locus_mismatch', cm.exception.message_dict) #this cannot be avoided because of error checking in TileVariant
    def test_path_on_wrong_chromosome(self):
        def get_path_hex(path):
            return hex(path).lstrip('0x').zfill(NUM_HEX_INDEXES_FOR_PATH)
        v_min='0'*NUM_HEX_INDEXES_FOR_VERSION
        v_max='f'*NUM_HEX_INDEXES_FOR_VERSION
        s_min='0'*NUM_HEX_INDEXES_FOR_STEP
        s_max='f'*NUM_HEX_INDEXES_FOR_STEP
        vv='0'*NUM_HEX_INDEXES_FOR_VARIANT_VALUE

        path_in_one = get_path_hex(0)
        tile, tilevar = make_tile_position_and_variant(int(v_min+path_in_one+s_min,16), int(v_min+path_in_one+s_min+vv,16), 250)
        with self.assertRaises(ValidationError) as cm:
            TileLocusAnnotation(assembly_int=ASSEMBLY_19, chromosome_int=CHR_2, start_int=0, end_int=250, tile_position=tile, tile_variant_value=0).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('chromosome_int-tile_position', cm.exception.message_dict)

        path_in_one = get_path_hex(settings.CHR_PATH_LENGTHS[1]-1)
        tile, tilevar = make_tile_position_and_variant(int(v_max+path_in_one+s_max,16), int(v_max+path_in_one+s_max+vv,16), 250)
        with self.assertRaises(ValidationError) as cm:
            TileLocusAnnotation(assembly_int=ASSEMBLY_19, chromosome_int=CHR_2, start_int=0, end_int=250, tile_position=tile, tile_variant_value=0).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('chromosome_int-tile_position', cm.exception.message_dict)

        path_in_two = get_path_hex(settings.CHR_PATH_LENGTHS[1])
        tile, tilevar = make_tile_position_and_variant(int(v_min+path_in_two+s_min,16), int(v_min+path_in_two+s_min+vv,16), 250)
        with self.assertRaises(ValidationError) as cm:
            TileLocusAnnotation(assembly_int=ASSEMBLY_19, chromosome_int=CHR_1, start_int=0, end_int=250, tile_position=tile, tile_variant_value=0).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('chromosome_int-tile_position', cm.exception.message_dict)

        path_in_last = get_path_hex(settings.CHR_PATH_LENGTHS[-2]-1)
        tile, tilevar = make_tile_position_and_variant(int(v_max+path_in_last+s_max,16), int(v_max+path_in_last+s_max+vv,16), 250)
        with self.assertRaises(ValidationError) as cm:
            TileLocusAnnotation(assembly_int=ASSEMBLY_19, chromosome_int=CHR_OTHER, start_int=0, end_int=250, tile_position=tile, tile_variant_value=0).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('chromosome_int-tile_position', cm.exception.message_dict)

        path_in_last = get_path_hex(settings.CHR_PATH_LENGTHS[-3])
        tile, tilevar = make_tile_position_and_variant(int(v_min+path_in_last+s_min,16), int(v_min+path_in_last+s_min+vv,16), 250)
        with self.assertRaises(ValidationError) as cm:
            TileLocusAnnotation(assembly_int=ASSEMBLY_19, chromosome_int=CHR_Y, start_int=0, end_int=250, tile_position=tile, tile_variant_value=0).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('chromosome_int-tile_position', cm.exception.message_dict)
    def test_saving_success(self):
        def get_path_hex(path):
            return hex(path).lstrip('0x').zfill(NUM_HEX_INDEXES_FOR_PATH)
        v_min='0'*NUM_HEX_INDEXES_FOR_VERSION
        v_max='f'*NUM_HEX_INDEXES_FOR_VERSION
        s_min='0'*NUM_HEX_INDEXES_FOR_STEP
        s_max='f'*NUM_HEX_INDEXES_FOR_STEP
        vv='0'*NUM_HEX_INDEXES_FOR_VARIANT_VALUE

        path_in_one = get_path_hex(0)
        tile, tilevar = make_tile_position_and_variant(int(v_min+path_in_one+s_min,16), int(v_min+path_in_one+s_min+vv,16), 250)
        TileLocusAnnotation(assembly_int=ASSEMBLY_19, chromosome_int=CHR_1, start_int=0, end_int=250, tile_position=tile, tile_variant_value=0).save()

        path_in_one = get_path_hex(settings.CHR_PATH_LENGTHS[1]-1)
        tile, tilevar = make_tile_position_and_variant(int(v_max+path_in_one+s_max,16), int(v_max+path_in_one+s_max+vv,16), 250)
        TileLocusAnnotation(assembly_int=ASSEMBLY_19, chromosome_int=CHR_1, start_int=0, end_int=250, tile_position=tile, tile_variant_value=0).save()

        path_in_two = get_path_hex(settings.CHR_PATH_LENGTHS[1])
        tile, tilevar = make_tile_position_and_variant(int(v_min+path_in_two+s_min,16), int(v_min+path_in_two+s_min+vv,16), 250)
        TileLocusAnnotation(assembly_int=ASSEMBLY_19, chromosome_int=CHR_2, start_int=0, end_int=250, tile_position=tile, tile_variant_value=0).save()

        path_in_last = get_path_hex(settings.CHR_PATH_LENGTHS[-2]-1)
        tile, tilevar = make_tile_position_and_variant(int(v_max+path_in_last+s_max,16), int(v_max+path_in_last+s_max+vv,16), 250)
        TileLocusAnnotation(assembly_int=ASSEMBLY_19, chromosome_int=CHR_M, start_int=0, end_int=250, tile_position=tile, tile_variant_value=0).save()

        path_in_last = get_path_hex(settings.CHR_PATH_LENGTHS[-3])
        tile, tilevar = make_tile_position_and_variant(int(v_min+path_in_last+s_min,16), int(v_min+path_in_last+s_min+vv,16), 250)
        TileLocusAnnotation(assembly_int=ASSEMBLY_19, chromosome_int=CHR_M, start_int=0, end_int=250, tile_position=tile, tile_variant_value=0).save()
    def test_multiple_annotations_failure(self):
        tile, tilevar = make_tile_position_and_variant(0, 0, 250)
        tilevar2 = make_tile_variant(tile, tile, 1, 249)
        TileLocusAnnotation(assembly_int=ASSEMBLY_19, chromosome_int=CHR_1, start_int=0, end_int=250, tile_position=tile, tile_variant_value=0).save()
        with self.assertRaises(ValidationError) as cm:
            TileLocusAnnotation(assembly_int=ASSEMBLY_19, chromosome_int=CHR_1, start_int=0, end_int=249, tile_position=tile, tile_variant_value=1).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('__all__', cm.exception.message_dict)
################################## TEST TileVariant model ###################################
class TestTileVariantModel(TestCase):
    def test_non_int_tile_variant_int(self):
        tile=make_tile_position(1)
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
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('tile_variant_int', cm.exception.message_dict)
    def test_negative_tile_variant_int(self):
        tile=make_tile_position(1)
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
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('tile_variant_int', cm.exception.message_dict)
    def test_too_big_tile_variant_int(self):
        tile=make_tile_position('f'*(NUM_HEX_INDEXES_FOR_VERSION + NUM_HEX_INDEXES_FOR_PATH + NUM_HEX_INDEXES_FOR_STEP))
        tile_var_int = 'f'*(NUM_HEX_INDEXES_FOR_VERSION + NUM_HEX_INDEXES_FOR_PATH + NUM_HEX_INDEXES_FOR_STEP+NUM_HEX_INDEXES_FOR_VARIANT_VALUE)
        seq = tile.start_tag
        seq += mk_genome_seq(250-TAG_LENGTH*2, uppercase=False)
        seq += tile.end_tag
        digestor = hashlib.new('md5', seq)
        with self.assertRaises(ValidationError) as cm:
            TileVariant(
                tile_variant_int=int(tile_var_int,16)+1,
                tile=tile,
                variant_value=0,
                length=250,
                md5sum=digestor.hexdigest(),
                sequence=seq,
                num_positions_spanned=1
            ).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('tile_variant_int', cm.exception.message_dict)
    def test_nonexistant_tile_position(self):
        seq = mk_genome_seq(250)
        digestor = hashlib.new('md5', seq)
        with self.assertRaises(ValidationError) as cm:
            TileVariant(
                tile_variant_int=int('1'+variant_value_min,16),
                variant_value=0,
                length=250,
                md5sum=digestor.hexdigest(),
                sequence=seq,
                num_positions_spanned=1
            ).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('tile', cm.exception.message_dict)
    def test_invalid_positions_spanned(self):
        tile=make_tile_position(1)
        seq = tile.start_tag
        seq += mk_genome_seq(250-TAG_LENGTH*2, uppercase=False)
        seq += tile.end_tag
        digestor = hashlib.new('md5', seq)
        with self.assertRaises(ValidationError) as cm:
            TileVariant(
                tile_variant_int=int('1'+variant_value_min,16),
                tile=tile,
                variant_value=0,
                length=250,
                md5sum=digestor.hexdigest(),
                sequence=seq,
                num_positions_spanned=0
            ).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('num_positions_spanned', cm.exception.message_dict)
        with self.assertRaises(ValidationError) as cm:
            TileVariant(
                tile_variant_int=int('1'+variant_value_min,16),
                tile=tile,
                variant_value=0,
                length=250,
                md5sum=digestor.hexdigest(),
                sequence=seq,
                num_positions_spanned=-1
            ).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('num_positions_spanned', cm.exception.message_dict)
    def test_invalid_variant_value(self):
        tile=make_tile_position(1)
        seq = tile.start_tag
        seq += mk_genome_seq(250-TAG_LENGTH*2, uppercase=False)
        seq += tile.end_tag
        digestor = hashlib.new('md5', seq)
        with self.assertRaises(ValidationError) as cm:
            TileVariant(
                tile_variant_int=int('1'+variant_value_min,16),
                tile=tile,
                variant_value=-1,
                length=250,
                md5sum=digestor.hexdigest(),
                sequence=seq,
                num_positions_spanned=1
            ).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('variant_value', cm.exception.message_dict)
    def test_invalid_start_tag(self):
        tile=make_tile_position(1)
        seq = tile.start_tag[:TAG_LENGTH-1]
        seq += mk_genome_seq(250-TAG_LENGTH*2, uppercase=False)
        seq += tile.end_tag
        digestor = hashlib.new('md5', seq)
        with self.assertRaises(ValidationError) as cm:
            TileVariant(
                tile_variant_int=int('1'+variant_value_min,16),
                tile=tile,
                variant_value=0,
                length=250-TAG_LENGTH*2,
                md5sum=digestor.hexdigest(),
                sequence=seq,
                num_positions_spanned=1,
                start_tag=tile.start_tag[:TAG_LENGTH-1]
            ).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('start_tag', cm.exception.message_dict)
    def test_invalid_end_tag(self):
        tile=make_tile_position(1)
        seq = tile.start_tag
        seq += mk_genome_seq(250-TAG_LENGTH*2, uppercase=False)
        seq += tile.end_tag[:TAG_LENGTH-1]
        digestor = hashlib.new('md5', seq)
        with self.assertRaises(ValidationError) as cm:
            TileVariant(
                tile_variant_int=int('1'+variant_value_min,16),
                tile=tile,
                variant_value=0,
                length=250-TAG_LENGTH*2,
                md5sum=digestor.hexdigest(),
                sequence=seq,
                num_positions_spanned=1,
                end_tag=tile.end_tag[:TAG_LENGTH-1]
            ).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('end_tag', cm.exception.message_dict)
    def test_mismatching_path_versions(self):
        tile=make_tile_position(1)
        seq = tile.start_tag
        seq += mk_genome_seq(250-TAG_LENGTH*2)
        seq += tile.end_tag
        digestor = hashlib.new('md5', seq)
        md5sum=digestor.hexdigest()
        v='0'*(NUM_HEX_INDEXES_FOR_VERSION-1)+'1'
        p='0'*(NUM_HEX_INDEXES_FOR_PATH)
        s='0'*(NUM_HEX_INDEXES_FOR_STEP-1)+'1'
        vv='0'*(NUM_HEX_INDEXES_FOR_VARIANT_VALUE)
        with self.assertRaises(ValidationError) as cm:
            TileVariant(
                tile_variant_int=int(v+p+s+vv,16),
                tile=tile,
                variant_value=0,
                length=250,
                md5sum=md5sum,
                sequence=seq,
                num_positions_spanned=1
            ).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('version_mismatch', cm.exception.message_dict)
        vv='f'*(NUM_HEX_INDEXES_FOR_VARIANT_VALUE)
        with self.assertRaises(ValidationError) as cm:
            TileVariant(
                tile_variant_int=int(v+p+s+vv,16),
                tile=tile,
                variant_value=int(vv,16),
                length=250,
                md5sum=md5sum,
                sequence=seq,
                num_positions_spanned=1
            ).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('version_mismatch', cm.exception.message_dict)
    def test_mismatching_paths(self):
        tile=make_tile_position(1)
        seq = tile.start_tag
        seq += mk_genome_seq(250-TAG_LENGTH*2)
        seq += tile.end_tag
        digestor = hashlib.new('md5', seq)
        md5sum=digestor.hexdigest()
        v='0'*(NUM_HEX_INDEXES_FOR_VERSION)
        p='0'*(NUM_HEX_INDEXES_FOR_PATH-1)+'1'
        s='0'*(NUM_HEX_INDEXES_FOR_STEP-1)+'1'
        vv='0'*(NUM_HEX_INDEXES_FOR_VARIANT_VALUE)
        with self.assertRaises(ValidationError) as cm:
            TileVariant(
                tile_variant_int=int(v+p+s+vv,16),
                tile=tile,
                variant_value=0,
                length=250,
                md5sum=md5sum,
                sequence=seq,
                num_positions_spanned=1
            ).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('path_mismatch', cm.exception.message_dict)
        vv='f'*(NUM_HEX_INDEXES_FOR_VARIANT_VALUE)
        with self.assertRaises(ValidationError) as cm:
            TileVariant(
                tile_variant_int=int(v+p+s+vv,16),
                tile=tile,
                variant_value=int(vv,16),
                length=250,
                md5sum=md5sum,
                sequence=seq,
                num_positions_spanned=1
            ).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('path_mismatch', cm.exception.message_dict)
    def test_mismatching_steps(self):
        tile=make_tile_position(1)
        seq = tile.start_tag
        seq += mk_genome_seq(250-TAG_LENGTH*2)
        seq += tile.end_tag
        digestor = hashlib.new('md5', seq)
        md5sum=digestor.hexdigest()
        with self.assertRaises(ValidationError) as cm:
            TileVariant(
                tile_variant_int=0,
                tile=tile,
                variant_value=0,
                length=250,
                md5sum=md5sum,
                sequence=seq,
                num_positions_spanned=1
            ).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('step_mismatch', cm.exception.message_dict)
        vv='f'*(NUM_HEX_INDEXES_FOR_VARIANT_VALUE)
        with self.assertRaises(ValidationError) as cm:
            TileVariant(
                tile_variant_int=int(vv,16),
                tile=tile,
                variant_value=int(vv,16),
                length=250,
                md5sum=md5sum,
                sequence=seq,
                num_positions_spanned=1
            ).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('step_mismatch', cm.exception.message_dict)
    def test_mismatching_variant_values(self):
        tile = make_tile_position(1)
        seq = tile.start_tag
        seq += mk_genome_seq(250-TAG_LENGTH*2)
        seq += tile.end_tag
        digestor = hashlib.new('md5', seq)
        vv='0'*(NUM_HEX_INDEXES_FOR_VARIANT_VALUE-1)+'1'
        with self.assertRaises(ValidationError) as cm:
            TileVariant(
                tile_variant_int=int('1'+vv,16),
                tile=tile,
                variant_value=0,
                length=250,
                md5sum=digestor.hexdigest(),
                sequence=seq,
                num_positions_spanned=1
            ).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('variant_value_mismatch', cm.exception.message_dict)
    def test_mismatching_length_and_sequence_length(self):
        tile=make_tile_position(1)
        seq = tile.start_tag
        seq += mk_genome_seq(250-TAG_LENGTH*2)
        seq += tile.end_tag
        digestor = hashlib.new('md5', seq)
        with self.assertRaises(ValidationError) as cm:
            TileVariant(
                tile_variant_int=int('1'+variant_value_min,16),
                tile=tile,
                variant_value=0,
                length=249,
                md5sum=digestor.hexdigest(),
                sequence=seq,
                num_positions_spanned=1
            ).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('length_mismatch', cm.exception.message_dict)
    def test_mismatching_md5sum(self):
        tile=make_tile_position(1)
        seq = tile.start_tag
        seq += mk_genome_seq(250-TAG_LENGTH*2)
        seq += tile.end_tag
        with self.assertRaises(ValidationError) as cm:
            TileVariant(
                tile_variant_int=int('1'+variant_value_min,16),
                tile=tile,
                variant_value=0,
                length=250,
                md5sum='aaadde',
                sequence=seq,
                num_positions_spanned=1
            ).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('md5sum-sequence', cm.exception.message_dict)
    def test_too_short_sequence(self):
        start_tag = mk_genome_seq(TAG_LENGTH)
        tile = Tile(tile_position_int=1, start_tag=start_tag, end_tag=start_tag)
        tile.save()
        digestor = hashlib.new('md5', start_tag)
        with self.assertRaises(ValidationError) as cm:
            TileVariant(
                tile_variant_int=int('1'+variant_value_min,16),
                tile=tile,
                variant_value=0,
                length=TAG_LENGTH,
                md5sum=digestor.hexdigest(),
                sequence=start_tag,
                num_positions_spanned=1
            ).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('sequence_malformed', cm.exception.message_dict)
    def test_mismatching_start_tag(self):
        tile=make_tile_position(1)
        seq =  mk_genome_seq(TAG_LENGTH)
        seq += mk_genome_seq(250-TAG_LENGTH*2)
        seq += tile.end_tag
        digestor = hashlib.new('md5', seq)
        with self.assertRaises(ValidationError) as cm:
            TileVariant(
                tile_variant_int=int('1'+variant_value_min,16),
                tile=tile,
                variant_value=0,
                length=250,
                md5sum=digestor.hexdigest(),
                sequence=seq,
                num_positions_spanned=1
            ).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('start_tag-sequence', cm.exception.message_dict)
    def test_mismatching_end_tag(self):
        tile=make_tile_position(1)
        seq =  tile.start_tag
        seq += mk_genome_seq(250-TAG_LENGTH*2)
        seq += mk_genome_seq(TAG_LENGTH)
        digestor = hashlib.new('md5', seq)
        with self.assertRaises(ValidationError) as cm:
            TileVariant(
                tile_variant_int=int('1'+variant_value_min,16),
                tile=tile,
                variant_value=0,
                length=250,
                md5sum=digestor.hexdigest(),
                sequence=seq,
                num_positions_spanned=1
            ).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('end_tag-sequence', cm.exception.message_dict)
    def test_successful_save(self):
        make_tile_position_and_variant(1, '1'+variant_value_min, 250)
    def test_successful_save_with_alternate_tags(self):
        tile=make_tile_position(1)
        start_tag = mk_genome_seq(TAG_LENGTH)
        end_tag = mk_genome_seq(TAG_LENGTH)
        seq = start_tag
        seq += mk_genome_seq(250-TAG_LENGTH*2)
        seq += end_tag
        digestor = hashlib.new('md5', seq)
        TileVariant(
            tile_variant_int=int('1'+variant_value_min, 16),
            tile=tile,
            variant_value=0,
            length=250,
            md5sum=digestor.hexdigest(),
            sequence=seq,
            num_positions_spanned=1,
            start_tag=start_tag,
            end_tag=end_tag
        ).save()
    def test_spanning_tile_missing_end_tile(self):
        tile=make_tile_position(1)
        seq = tile.start_tag
        seq += mk_genome_seq(750-TAG_LENGTH)
        digestor = hashlib.new('md5', seq)
        with self.assertRaises(ValidationError) as cm:
            TileVariant(
                tile_variant_int=int('1'+variant_value_min,16),
                tile=tile,
                variant_value=0,
                length=750,
                md5sum=digestor.hexdigest(),
                sequence=seq,
                num_positions_spanned=3
            ).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('spanning_tile_error_missing_tile', cm.exception.message_dict)
    def test_spanning_tile_on_two_paths(self):
        v='0'*(NUM_HEX_INDEXES_FOR_VERSION)
        starting_p='0'*(NUM_HEX_INDEXES_FOR_PATH)
        ending_p='0'*(NUM_HEX_INDEXES_FOR_PATH-1)+'1'
        starting_s='f'*(NUM_HEX_INDEXES_FOR_STEP)
        ending_s='0'*(NUM_HEX_INDEXES_FOR_STEP)
        vv='0'*(NUM_HEX_INDEXES_FOR_VARIANT_VALUE)
        ending_tile, ending_tilevar =make_tile_position_and_variant(v+ending_p+ending_s, v+ending_p+ending_s+vv, 250)
        starting_tile, starting_tilevar = make_tile_position_and_variant(v+starting_p+starting_s,v+starting_p+starting_s+vv, 250)
        with self.assertRaises(ValidationError) as cm:
            make_tile_variant(starting_tile, ending_tile, v+starting_p+starting_s+'0'*(NUM_HEX_INDEXES_FOR_VARIANT_VALUE-1)+'1', 500, num_spanned=2)
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('spanning_tile_error', cm.exception.message_dict)
    def test_spanning_tile_on_two_paths_using_complicated_library(self):
        build_library.make_reference()
        with self.assertRaises(ValidationError) as cm:
            build_library.make_broken_genome_variant()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('spanning_tile_error', cm.exception.message_dict)
    def test_spanning_tile_on_two_path_versions_and_two_paths(self):
        #Prevented by the small int restriction on num_positions spanned
        starting_v='0'*(NUM_HEX_INDEXES_FOR_VERSION)
        ending_v='0'*(NUM_HEX_INDEXES_FOR_VERSION-1)+'1'
        starting_p='f'*(NUM_HEX_INDEXES_FOR_PATH)
        ending_p='0'*(NUM_HEX_INDEXES_FOR_PATH)
        starting_s='f'*(NUM_HEX_INDEXES_FOR_STEP)
        ending_s='0'*(NUM_HEX_INDEXES_FOR_STEP)
        vv='0'*(NUM_HEX_INDEXES_FOR_VARIANT_VALUE)
        ending_tile, ending_tilevar = make_tile_position_and_variant(ending_v+ending_p+ending_s, ending_v+ending_p+ending_s+vv,250)
        starting_tile, starting_tilevar = make_tile_position_and_variant(starting_v+starting_p+starting_s, starting_v+starting_p+starting_s+vv,250)
        with self.assertRaises(ValidationError) as cm:
            next_tilevar_int = int(starting_v+starting_p+starting_s+vv,16)+1
            make_tile_variant(starting_tile, ending_tile, next_tilevar_int, 500, num_spanned=2)
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('spanning_tile_error', cm.exception.message_dict)
    def test_spanning_tile_on_two_path_versions(self):
        #Prevented by the small int restriction on num_positions spanned
        starting_v='0'*(NUM_HEX_INDEXES_FOR_VERSION)
        ending_v='0'*(NUM_HEX_INDEXES_FOR_VERSION-1)+'1'
        p='0'*(NUM_HEX_INDEXES_FOR_PATH)
        starting_s='f'*(NUM_HEX_INDEXES_FOR_STEP)
        ending_s='0'*(NUM_HEX_INDEXES_FOR_STEP)
        vv='0'*(NUM_HEX_INDEXES_FOR_VARIANT_VALUE)
        ending_tile, ending_tilevar = make_tile_position_and_variant(ending_v+p+ending_s, ending_v+p+ending_s+vv,250)
        starting_tile, starting_tilevar = make_tile_position_and_variant(starting_v+p+starting_s, starting_v+p+starting_s+vv,250)
        with self.assertRaises(ValidationError) as cm:
            num_spanned=int(ending_v+p+ending_s,16)-int(starting_v+p+starting_s,16)
            make_tile_variant(starting_tile, ending_tile, int(starting_v+p+starting_s+vv,16)+1, 500, num_spanned=num_spanned)
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('num_positions_spanned', cm.exception.message_dict)
    def test_successful_spanning_tile_save(self):
        tile1=make_tile_position(1)
        make_tile_position_and_variant(0, 1, 500, tile_ending=tile1, num_spanned=2)
    def test_successful_spanning_tile_when_missing_middle_save(self):
        tile2=make_tile_position(2)
        make_tile_position_and_variant(0, 1, 700, tile_ending=tile2, num_spanned=3)
    def test_same_name_space_failure(self):
        tile, tilevar = make_tile_position_and_variant(0,0,250)
        with self.assertRaises(ValidationError) as cm:
            make_tile_variant(tile, tile, 0, 249)
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('tile_variant_int', cm.exception.message_dict)
    def test_same_md5sum_and_tile_failure(self):
        build_library.make_reference()
        s = '0'*(NUM_HEX_INDEXES_FOR_STEP-1)+'1'
        vv = '0'*(NUM_HEX_INDEXES_FOR_VARIANT_VALUE-1)+'1'
        with self.assertRaises(ValidationError) as cm:
            tv = build_library.make_tile_variant(int(s+vv,16), "TCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTC".lower(), 1)
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('__all__', cm.exception.message_dict)
    def test_get_string_type(self):
        new_tile = TileVariant(tile_variant_int=0)
        self.assertIsInstance(new_tile.get_string(), str)
    def test_get_string_random_tiles(self):
        for i in range(NUM_RANDOM_TESTS_TO_RUN):
            v=mk_hex_num(NUM_HEX_INDEXES_FOR_VERSION)
            p=mk_hex_num(NUM_HEX_INDEXES_FOR_PATH)
            s=mk_hex_num(NUM_HEX_INDEXES_FOR_STEP)
            vv=mk_hex_num(NUM_HEX_INDEXES_FOR_VARIANT_VALUE)
            new_tile = TileVariant(tile_variant_int=int(v+p+s+vv,16))
            self.assertEqual(new_tile.get_string(), string.join([v,p,s,vv],sep='.'))
    def test_get_string_from_max_and_min_tiles(self):
        v='0'*NUM_HEX_INDEXES_FOR_VERSION
        p='0'*NUM_HEX_INDEXES_FOR_PATH
        s='0'*NUM_HEX_INDEXES_FOR_STEP
        vv='0'*(NUM_HEX_INDEXES_FOR_VARIANT_VALUE)
        new_tile = TileVariant(tile_variant_int=int(v+p+s+vv,16))
        self.assertEqual(new_tile.get_string(), string.join([v,p,s,vv],sep='.'))
        v='f'*NUM_HEX_INDEXES_FOR_VERSION
        p='f'*NUM_HEX_INDEXES_FOR_PATH
        s='f'*NUM_HEX_INDEXES_FOR_STEP
        vv='f'*(NUM_HEX_INDEXES_FOR_VARIANT_VALUE)
        new_tile = TileVariant(tile_variant_int=int(v+p+s+vv,16))
        self.assertEqual(new_tile.get_string(), string.join([v,p,s,vv],sep='.'))
    def test_is_reference_non_int_assembly(self):
        tile, tilevar = make_tile_position_and_variant(0, 0, 250)
        with self.assertRaises(ValueError) as cm:
            tilevar.is_reference('a')
    @override_settings(SUPPORTED_ASSEMBLY_CHOICES=((18, 'hg18'),))
    def test_is_reference_unsupported_assembly(self):
        tile, tilevar = make_tile_position_and_variant(0, 0, 250)
        with self.assertRaises(ValueError) as cm:
            tilevar.is_reference(0)
    def test_is_reference_missing_locus(self):
        s='0'*(NUM_HEX_INDEXES_FOR_STEP-1)+'1'
        vv='0'*(NUM_HEX_INDEXES_FOR_VARIANT_VALUE)
        tile, tilevar = make_tile_position_and_variant(0, 0, 250)
        tile2, tilevar2 = make_tile_position_and_variant(1, int(s+vv,16), 500+TAG_LENGTH-250)
        TileLocusAnnotation(assembly_int=ASSEMBLY_19, chromosome_int=CHR_1, start_int=250-TAG_LENGTH, end_int=500, tile_position=tile2, tile_variant_value=0).save()
        TileLocusAnnotation(assembly_int=ASSEMBLY_18, chromosome_int=CHR_1, start_int=250-TAG_LENGTH, end_int=500, tile_position=tile2, tile_variant_value=0).save()
        with self.assertRaises(MissingLocusError) as cm:
            tilevar.is_reference(ASSEMBLY_19)
        with self.assertRaises(MissingLocusError) as cm:
            tilevar.is_reference(ASSEMBLY_18)
        TileLocusAnnotation(assembly_int=ASSEMBLY_19, chromosome_int=CHR_1, start_int=0, end_int=250, tile_position=tile, tile_variant_value=0).save()
        tilevar.is_reference(ASSEMBLY_19)
        with self.assertRaises(MissingLocusError) as cm:
            tilevar.is_reference(ASSEMBLY_18)
    def test_is_reference_one_assembly_on_one_tilevar_success(self):
        tile, tilevar = make_tile_position_and_variant(0, 0, 250)
        tilevar2 = make_tile_variant(tile, tile, 1, 250)
        TileLocusAnnotation(assembly_int=ASSEMBLY_19, chromosome_int=CHR_1, start_int=0, end_int=250, tile_position=tile, tile_variant_value=0).save()
        self.assertIsInstance(tilevar.is_reference(ASSEMBLY_19), bool)
        self.assertTrue(tilevar.is_reference(ASSEMBLY_19))
        self.assertFalse(tilevar2.is_reference(ASSEMBLY_19))
        # Adding another assembly to the same tilevariant should only change 1 query
        TileLocusAnnotation(assembly_int=ASSEMBLY_18, chromosome_int=CHR_1, start_int=0, end_int=250, tile_position=tile, tile_variant_value=0).save()
        self.assertTrue(tilevar.is_reference(ASSEMBLY_19))
        self.assertFalse(tilevar2.is_reference(ASSEMBLY_19))
        self.assertTrue(tilevar.is_reference(ASSEMBLY_18))
        self.assertFalse(tilevar2.is_reference(ASSEMBLY_18))
    def test_is_reference_multiple_assemblies_success(self):
        tile, tilevar = make_tile_position_and_variant(0, 0, 250)
        tilevar2 = make_tile_variant(tile, tile, 1, 249)
        TileLocusAnnotation(assembly_int=ASSEMBLY_19, chromosome_int=CHR_1, start_int=0, end_int=250, tile_position=tile, tile_variant_value=0).save()
        TileLocusAnnotation(assembly_int=ASSEMBLY_18, chromosome_int=CHR_1, start_int=0, end_int=249, tile_position=tile, tile_variant_value=1).save()
        self.assertIsInstance(tilevar.is_reference(ASSEMBLY_19), bool)
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
    def test_get_locus_non_int_assembly(self):
        tile, tilevar = make_tile_position_and_variant(0, 0, 250)
        TileLocusAnnotation(assembly_int=ASSEMBLY_19, chromosome_int=CHR_1, start_int=0, end_int=250, tile_position=tile, tile_variant_value=0).save()
        with self.assertRaises(ValueError) as cm:
            tilevar.get_locus('hi')
    @override_settings(SUPPORTED_ASSEMBLY_CHOICES=((19, 'hg19'),))
    def test_get_locus_unsupported_assembly(self):
        tile, tilevar = make_tile_position_and_variant(0, 0, 250)
        TileLocusAnnotation(assembly_int=ASSEMBLY_19, chromosome_int=CHR_1, start_int=0, end_int=250, tile_position=tile, tile_variant_value=0).save()
        with self.assertRaises(ValueError) as cm:
            tilevar.get_locus(0)
    def test_get_locus_missing_locus(self):
        vv='0'*(NUM_HEX_INDEXES_FOR_VARIANT_VALUE)
        tile, tilevar = make_tile_position_and_variant(0, 0, 250)
        tile2, tilevar2 = make_tile_position_and_variant(1, int('1'+vv,16), 500+TAG_LENGTH-250)
        TileLocusAnnotation(assembly_int=ASSEMBLY_19, chromosome_int=CHR_1, start_int=250-TAG_LENGTH, end_int=500, tile_position=tile2, tile_variant_value=0).save()
        TileLocusAnnotation(assembly_int=ASSEMBLY_18, chromosome_int=CHR_1, start_int=250-TAG_LENGTH, end_int=500, tile_position=tile2, tile_variant_value=0).save()
        with self.assertRaises(MissingLocusError) as cm:
            tilevar.get_locus(ASSEMBLY_19)
        with self.assertRaises(MissingLocusError) as cm:
            tilevar.get_locus(ASSEMBLY_18)
        TileLocusAnnotation(assembly_int=ASSEMBLY_19, chromosome_int=CHR_1, start_int=0, end_int=250, tile_position=tile, tile_variant_value=0).save()
        tilevar.get_locus(ASSEMBLY_19) # should not raise an error now
        with self.assertRaises(MissingLocusError) as cm:
            tilevar.get_locus(ASSEMBLY_18) # should still raise an error
    def test_get_locus_missing_end_locus(self):
        tile, tilevar = make_tile_position_and_variant(0, 0, 250)
        TileLocusAnnotation(assembly_int=ASSEMBLY_19, chromosome_int=CHR_1, start_int=0, end_int=250, tile_position=tile, tile_variant_value=0).save()
        TileLocusAnnotation(assembly_int=ASSEMBLY_18, chromosome_int=CHR_1, start_int=0, end_int=250, tile_position=tile, tile_variant_value=0).save()
        vv='0'*(NUM_HEX_INDEXES_FOR_VARIANT_VALUE)
        tile2, tilevar2 = make_tile_position_and_variant(1, int('1'+vv,16), 500+TAG_LENGTH-250)
        TileLocusAnnotation(assembly_int=ASSEMBLY_19, chromosome_int=CHR_1, start_int=250-TAG_LENGTH, end_int=500, tile_position=tile2, tile_variant_value=0).save()
        TileLocusAnnotation(assembly_int=ASSEMBLY_18, chromosome_int=CHR_1, start_int=250-TAG_LENGTH, end_int=500, tile_position=tile2, tile_variant_value=0).save()
        tile3, tilevar3 = make_tile_position_and_variant(2, int('2'+vv,16), 750+TAG_LENGTH-500)

        spanning_tilevar = make_tile_variant(tile, tile3, 1, 750, num_spanned=3)

        with self.assertRaises(MissingLocusError) as cm:
            spanning_tilevar.get_locus(ASSEMBLY_19)
        with self.assertRaises(MissingLocusError) as cm:
            spanning_tilevar.get_locus(ASSEMBLY_18)
        TileLocusAnnotation(assembly_int=ASSEMBLY_19, chromosome_int=CHR_1, start_int=500-TAG_LENGTH, end_int=750, tile_position=tile3, tile_variant_value=0).save()
        spanning_tilevar.get_locus(ASSEMBLY_19) # should not raise an error now
        with self.assertRaises(MissingLocusError) as cm:
            spanning_tilevar.get_locus(ASSEMBLY_18) # should still raise an error
    def test_get_locus_type_return(self):
        vv='0'*(NUM_HEX_INDEXES_FOR_VARIANT_VALUE)
        tile, tilevar = make_tile_position_and_variant(0, 0, 250)
        TileLocusAnnotation(assembly_int=ASSEMBLY_19, chromosome_int=CHR_1, start_int=0, end_int=250, tile_position=tile, tile_variant_value=0).save()
        TileLocusAnnotation(assembly_int=ASSEMBLY_18, chromosome_int=CHR_1, start_int=0, end_int=250, tile_position=tile, tile_variant_value=0).save()
        tile2, tilevar2 = make_tile_position_and_variant(1, int('1'+vv,16), 500+TAG_LENGTH-250)
        TileLocusAnnotation(assembly_int=ASSEMBLY_19, chromosome_int=CHR_1, start_int=250-TAG_LENGTH, end_int=500, tile_position=tile2, tile_variant_value=0).save()
        TileLocusAnnotation(assembly_int=ASSEMBLY_18, chromosome_int=CHR_1, start_int=250-TAG_LENGTH, end_int=500, tile_position=tile2, tile_variant_value=0).save()
        tile3, tilevar3 = make_tile_position_and_variant(2, int('2'+vv,16), 750+TAG_LENGTH-500)
        TileLocusAnnotation(assembly_int=ASSEMBLY_19, chromosome_int=CHR_1, start_int=500-TAG_LENGTH, end_int=750, tile_position=tile3, tile_variant_value=0).save()
        TileLocusAnnotation(assembly_int=ASSEMBLY_18, chromosome_int=CHR_1, start_int=500-TAG_LENGTH, end_int=750, tile_position=tile3, tile_variant_value=0).save()
        spanning_tilevar = make_tile_variant(tile, tile3, 1, 750, num_spanned=3)
        start, end = tilevar.get_locus(ASSEMBLY_19)
        self.assertIsInstance(start, int)
        self.assertIsInstance(end, int)
        start, end = tilevar.get_locus(ASSEMBLY_18)
        self.assertIsInstance(start, int)
        self.assertIsInstance(end, int)
    def test_get_locus_non_spanning_success(self):
        tile, tilevar = make_tile_position_and_variant(0, 0, 250)
        tilevar2 = make_tile_variant(tile, tile, 1, 249)
        TileLocusAnnotation(assembly_int=ASSEMBLY_19, chromosome_int=CHR_1, start_int=0, end_int=250, tile_position=tile, tile_variant_value=0).save()
        TileLocusAnnotation(assembly_int=ASSEMBLY_18, chromosome_int=CHR_1, start_int=0, end_int=249, tile_position=tile, tile_variant_value=1).save()
        start, end = tilevar.get_locus(ASSEMBLY_19)
        self.assertEqual(start, 0)
        self.assertEqual(end, 250)
        start, end = tilevar.get_locus(ASSEMBLY_18)
        self.assertEqual(start, 0)
        self.assertEqual(end, 249)
        start, end = tilevar2.get_locus(ASSEMBLY_19)
        self.assertEqual(start, 0)
        self.assertEqual(end, 250)
        start, end = tilevar2.get_locus(ASSEMBLY_18)
        self.assertEqual(start, 0)
        self.assertEqual(end, 249)
    def test_get_locus_spanning_success(self):
        vv='0'*(NUM_HEX_INDEXES_FOR_VARIANT_VALUE)
        tile, tilevar = make_tile_position_and_variant(0, 0, 250)
        tilevar_var1 = make_tile_variant(tile, tile, 1, 249)
        TileLocusAnnotation(assembly_int=ASSEMBLY_19, chromosome_int=CHR_1, start_int=0, end_int=250, tile_position=tile, tile_variant_value=0).save()
        TileLocusAnnotation(assembly_int=ASSEMBLY_18, chromosome_int=CHR_1, start_int=0, end_int=249, tile_position=tile, tile_variant_value=1).save()

        tile1, tilevar1 = make_tile_position_and_variant(1, int('1'+vv,16), 500+TAG_LENGTH-250)
        TileLocusAnnotation(assembly_int=ASSEMBLY_19, chromosome_int=CHR_1, start_int=250-TAG_LENGTH, end_int=500, tile_position=tile1, tile_variant_value=0).save()
        TileLocusAnnotation(assembly_int=ASSEMBLY_18, chromosome_int=CHR_1, start_int=249-TAG_LENGTH, end_int=499, tile_position=tile1, tile_variant_value=0).save()

        tile2, tilevar2 = make_tile_position_and_variant(2, int('2'+vv,16), 750+TAG_LENGTH-500)
        TileLocusAnnotation(assembly_int=ASSEMBLY_19, chromosome_int=CHR_1, start_int=500-TAG_LENGTH, end_int=750, tile_position=tile2, tile_variant_value=0).save()
        TileLocusAnnotation(assembly_int=ASSEMBLY_18, chromosome_int=CHR_1, start_int=499-TAG_LENGTH, end_int=749, tile_position=tile2, tile_variant_value=0).save()

        spanning_tilevar = make_tile_variant(tile, tile2, 2, 750, num_spanned=3)

        start, end = spanning_tilevar.get_locus(ASSEMBLY_19)
        self.assertEqual(start, 0)
        self.assertEqual(end, 750)
        start, end = spanning_tilevar.get_locus(ASSEMBLY_18)
        self.assertEqual(start, 0)
        self.assertEqual(end, 749)
    def test_get_locus_spanning_success_missing_middle_info(self):
        vv='0'*(NUM_HEX_INDEXES_FOR_VARIANT_VALUE)
        tile, tilevar = make_tile_position_and_variant(0, 0, 250)
        tilevar_var1 = make_tile_variant(tile, tile, 1, 249)
        TileLocusAnnotation(assembly_int=ASSEMBLY_19, chromosome_int=CHR_1, start_int=0, end_int=250, tile_position=tile, tile_variant_value=0).save()
        TileLocusAnnotation(assembly_int=ASSEMBLY_18, chromosome_int=CHR_1, start_int=0, end_int=249, tile_position=tile, tile_variant_value=1).save()

        tile3, tilevar3 = make_tile_position_and_variant(2, int('2'+vv,16), 750+TAG_LENGTH-500)
        TileLocusAnnotation(assembly_int=ASSEMBLY_19, chromosome_int=CHR_1, start_int=500-TAG_LENGTH, end_int=750, tile_position=tile3, tile_variant_value=0).save()
        TileLocusAnnotation(assembly_int=ASSEMBLY_18, chromosome_int=CHR_1, start_int=499-TAG_LENGTH, end_int=749, tile_position=tile3, tile_variant_value=0).save()

        spanning_tilevar = make_tile_variant(tile, tile3, 2, 750, num_spanned=3)

        start, end = spanning_tilevar.get_locus(ASSEMBLY_19)
        self.assertEqual(start, 0)
        self.assertEqual(end, 750)
        start, end = spanning_tilevar.get_locus(ASSEMBLY_18)
        self.assertEqual(start, 0)
        self.assertEqual(end, 749)
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
################################## TEST LanternTranslator model ###################################
class TestLanternTranslatorModel(TestCase):
    def setUp(self):
        self.v='0'*NUM_HEX_INDEXES_FOR_VERSION
        self.p='0'*NUM_HEX_INDEXES_FOR_PATH
        self.s='0'*NUM_HEX_INDEXES_FOR_STEP
        self.vv = '0'*(NUM_HEX_INDEXES_FOR_CGF_VARIANT_VALUE)
        self.min_name = string.join([self.p,self.v,self.s,self.vv], sep='.')
        tile, tilevar = make_tile_position_and_variant(0, 0, 250)
        self.tile = tile
    def test_failure_wrong_type_lantern_name(self):
        with self.assertRaises(ValidationError) as cm:
            LanternTranslator(lantern_name=0, tile_variant_int=0).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('lantern_name', cm.exception.message_dict)
    def test_failure_lantern_name_does_not_follow_specified_lantern_format(self):
        v='0'*NUM_HEX_INDEXES_FOR_VERSION
        p='0'*NUM_HEX_INDEXES_FOR_PATH
        s='0'*NUM_HEX_INDEXES_FOR_STEP
        vv = '0'*(NUM_HEX_INDEXES_FOR_CGF_VARIANT_VALUE-1)
        vv2 = 'x'*NUM_HEX_INDEXES_FOR_CGF_VARIANT_VALUE
        with self.assertRaises(ValidationError) as cm:
            LanternTranslator(lantern_name=string.join([p,v,s],sep='.'), tile_variant_int=0).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('lantern_name', cm.exception.message_dict)
        with self.assertRaises(ValidationError) as cm:
            LanternTranslator(lantern_name=string.join([p,v,s,vv],sep='.'), tile_variant_int=0).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('lantern_name', cm.exception.message_dict)
        with self.assertRaises(ValidationError) as cm:
            LanternTranslator(lantern_name=string.join([p,v,s,vv2],sep='.'), tile_variant_int=0).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('lantern_name', cm.exception.message_dict)
        with self.assertRaises(ValidationError) as cm:
            LanternTranslator(lantern_name=string.join([v,p,s,vv+'0'],sep='.'), tile_variant_int=0).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('lantern_name', cm.exception.message_dict)
        with self.assertRaises(ValidationError) as cm:
            LanternTranslator(lantern_name=string.join([p,v,s,vv+'0'],sep='.')+'+', tile_variant_int=0).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('lantern_name', cm.exception.message_dict)
        with self.assertRaises(ValidationError) as cm:
            LanternTranslator(lantern_name=string.join([p,v,s,vv+'0'],sep='.')+'+x', tile_variant_int=0).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('lantern_name', cm.exception.message_dict)
    def test_failure_lantern_name_has_spanning_notation(self):
        with self.assertRaises(ValidationError) as cm:
            LanternTranslator(lantern_name=self.min_name+'+0', tile_variant_int=0).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('lantern_name', cm.exception.message_dict)
        with self.assertRaises(ValidationError) as cm:
            LanternTranslator(lantern_name=self.min_name+'+fff', tile_variant_int=0).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('lantern_name', cm.exception.message_dict)
    def test_failure_non_int_tile_variant_int(self):
        with self.assertRaises(ValidationError) as cm:
            LanternTranslator(lantern_name=self.min_name, tile_variant_int='fail').save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('tile_variant_int', cm.exception.message_dict)
    def test_failure_negative_tile_variant_int(self):
        with self.assertRaises(ValidationError) as cm:
            LanternTranslator(lantern_name=self.min_name, tile_variant_int=-1).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('tile_variant_int', cm.exception.message_dict)
    def test_failure_too_big_tile_variant_int(self):
        tile_var_int = 'f'*(NUM_HEX_INDEXES_FOR_VERSION + NUM_HEX_INDEXES_FOR_PATH + NUM_HEX_INDEXES_FOR_STEP+NUM_HEX_INDEXES_FOR_VARIANT_VALUE)
        with self.assertRaises(ValidationError) as cm:
            LanternTranslator(lantern_name=self.min_name, tile_variant_int=int(tile_var_int,16)+1).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('tile_variant_int', cm.exception.message_dict)
    #test lantern_name and tile_variant_int on different versions, paths, and steps
    def test_failure_mismatching_versions(self):
        v = '1'*(NUM_HEX_INDEXES_FOR_VERSION)
        with self.assertRaises(ValidationError) as cm:
            LanternTranslator(lantern_name=string.join([self.p,v,self.s,self.vv], sep='.'), tile_variant_int=0).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('version_mismatch', cm.exception.message_dict)
    def test_failure_mismatching_paths(self):
        p = '1'*(NUM_HEX_INDEXES_FOR_PATH)
        with self.assertRaises(ValidationError) as cm:
            LanternTranslator(lantern_name=string.join([p,self.v,self.s,self.vv], sep='.'), tile_variant_int=0).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('path_mismatch', cm.exception.message_dict)
    def test_failure_mismatching_steps(self):
        s = '1'*(NUM_HEX_INDEXES_FOR_STEP)
        with self.assertRaises(ValidationError) as cm:
            LanternTranslator(lantern_name=string.join([self.p,self.v,s,self.vv], sep='.'), tile_variant_int=0).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('step_mismatch', cm.exception.message_dict)
    #test missing TileVariant in local db
    def test_failure_missing_tilevariant_in_local_db(self):
        p = '1'*(NUM_HEX_INDEXES_FOR_PATH)
        library_vv = '0'*(NUM_HEX_INDEXES_FOR_VARIANT_VALUE)
        with self.assertRaises(ValidationError) as cm:
            LanternTranslator(lantern_name=string.join([p,self.v,self.s,self.vv], sep='.'), tile_variant_int=int(p+self.s+library_vv, 16)).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('tile_variant_int-tile_library_host', cm.exception.message_dict)
    #test successes
    def test_success_min(self):
        LanternTranslator(lantern_name=self.min_name, tile_variant_int=0).save()
    def test_success_max(self):
        v='f'*NUM_HEX_INDEXES_FOR_VERSION
        p = hex(settings.CHR_PATH_LENGTHS[-1]-1).lstrip('0x').zfill(NUM_HEX_INDEXES_FOR_PATH)
        s='f'*NUM_HEX_INDEXES_FOR_STEP
        lantern_vv = 'f'*NUM_HEX_INDEXES_FOR_CGF_VARIANT_VALUE
        library_vv = 'f'*NUM_HEX_INDEXES_FOR_VARIANT_VALUE
        max_lantern_name = string.join([p,v,s,lantern_vv],sep='.')
        max_library_tile_var_int = int(v+p+s+library_vv,16)
        make_tile_position_and_variant(int(v+p+s,16), max_library_tile_var_int, 250)
        LanternTranslator(lantern_name=max_lantern_name, tile_variant_int=max_library_tile_var_int).save()
    #test uniqueness
    def test_failure_duplicate_lantern_names(self):
        LanternTranslator(lantern_name=self.min_name, tile_variant_int=0).save()
        make_tile_variant(self.tile, self.tile, 1, 250)
        with self.assertRaises(ValidationError) as cm:
            LanternTranslator(lantern_name=self.min_name, tile_variant_int=1).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('lantern_name', cm.exception.message_dict)
    def test_failure_duplicate_tile_variant_ints_in_same_database(self):
        LanternTranslator(lantern_name=self.min_name, tile_variant_int=0).save()
        vv = '1'*(NUM_HEX_INDEXES_FOR_CGF_VARIANT_VALUE)
        new_name = string.join([self.p,self.v,self.s,vv], sep='.')
        with self.assertRaises(ValidationError) as cm:
            LanternTranslator(lantern_name=new_name, tile_variant_int=0).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('__all__', cm.exception.message_dict)
class TestLanternTranslatorModelOtherDB(LiveServerTestCase):
    def setUp(self):
        self.v='0'*NUM_HEX_INDEXES_FOR_VERSION
        self.p='0'*NUM_HEX_INDEXES_FOR_PATH
        self.s='0'*NUM_HEX_INDEXES_FOR_STEP
        self.vv = '0'*(NUM_HEX_INDEXES_FOR_CGF_VARIANT_VALUE)
        self.min_name = string.join([self.p,self.v,self.s,self.vv], sep='.')
        tile, tilevar = make_tile_position_and_variant(0, 0, 250)
        self.tile = tile
    #test tile_library_host not equal to "", request logic!
    def test_failure_wrong_port(self):
        with self.assertRaises(ValidationError) as cm:
            LanternTranslator(lantern_name=self.min_name, tile_library_host='localhost:8000', tile_variant_int=0).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('tile_library_host', cm.exception.message_dict)
    def test_failure_non_existant_server(self):
        with self.assertRaises(ValidationError) as cm:
            LanternTranslator(lantern_name=self.min_name, tile_library_host='fail', tile_variant_int=0).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('tile_library_host', cm.exception.message_dict)
        with self.assertRaises(ValidationError) as cm:
            LanternTranslator(lantern_name=self.min_name, tile_library_host=self.live_server_url, tile_variant_int=0).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('tile_library_host', cm.exception.message_dict)
    def test_failure_bad_response(self):
        with self.assertRaises(ValidationError) as cm:
            LanternTranslator(lantern_name=self.min_name, tile_library_host='lightning-dev3.curoverse.com/brca', tile_variant_int=0).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('tile_library_int-tile_library_host', cm.exception.message_dict)
    def test_success(self):
        LanternTranslator(lantern_name=self.min_name, tile_library_host=self.live_server_url.strip().lstrip('http://'), tile_variant_int=0).save()
################################## TEST GenomeVariant model ###################################
class TestGenomeVariantModel(TestCase):
    def setUp(self):
        build_library.make_reference()
    def test_failure_multiple_genome_variants_with_same_id(self):
        build_library.make_genome_variant(0, 24, 25, 'C', 'G')
        with self.assertRaises(ValidationError) as cm:
            build_library.make_genome_variant(0, 25, 26, 'G', 'A')
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('id', cm.exception.message_dict)
    def test_failure_non_int_assembly(self):
        with self.assertRaises(ValidationError) as cm:
            build_library.make_genome_variant(0, 24, 25, 'C', 'G', assembly="hi")
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('assembly_int', cm.exception.message_dict)
    @skipIf(0 in supported_assembly_ints, "Checking behavior for unsupported assembly, but 0 is supported")
    def test_failure_unsupported_assembly(self):
        with self.assertRaises(ValidationError) as cm:
            build_library.make_genome_variant(0, 24, 25, 'C', 'G', assembly=0)
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('assembly_int', cm.exception.message_dict)
    def test_failure_missing_locus_with_correct_assembly(self):
        with self.assertRaises(ValidationError) as cm:
            build_library.make_genome_variant(0, 24, 25, 'C', 'G', assembly=ASSEMBLY_18)
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('missing_locus', cm.exception.message_dict)
    def test_failure_non_int_chromosome(self):
        with self.assertRaises(ValidationError) as cm:
            build_library.make_genome_variant(0, 24, 25, 'C', 'G', chrom='hi')
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('chromosome_int', cm.exception.message_dict)
    @skipIf(0 in supported_chr_ints, "Checking behavior for unsupported chromosome, but 0 is supported")
    def test_failure_unsupported_chromosome(self):
        with self.assertRaises(ValidationError) as cm:
            build_library.make_genome_variant(0, 24, 25, 'C', 'G', chrom=0)
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('chromosome_int', cm.exception.message_dict)
    def test_failure_missing_locus_with_correct_chromosome(self):
        locus = TileLocusAnnotation.objects.get(tile_position=0)
        locus.delete()
        with self.assertRaises(ValidationError) as cm:
            build_library.make_genome_variant(0, 24, 25, 'C', 'G', chrom=CHR_1)
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('missing_locus', cm.exception.message_dict)
    def test_failure_locus_end_int_smaller_than_start_int(self):
        with self.assertRaises(ValidationError) as cm:
            build_library.make_genome_variant(0, 25, 24, 'C', 'G')
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('locus_start_int-locus_end_int', cm.exception.message_dict)
    def test_failure_missing_locus_in_correct_range(self):
        locus = TileLocusAnnotation.objects.get(tile_position=0)
        locus.delete()
        with self.assertRaises(ValidationError) as cm:
            build_library.make_genome_variant(0, 24, 25, 'T', 'G')
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('missing_locus', cm.exception.message_dict)
    def test_failure_reference_bases_not_regex_sequence(self):
        with self.assertRaises(ValidationError) as cm:
            build_library.make_genome_variant(0, 24, 25, 'X', 'G')
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('reference_bases', cm.exception.message_dict)
    def test_failure_alternate_bases_not_regex_sequence(self):
        with self.assertRaises(ValidationError) as cm:
            build_library.make_genome_variant(0, 24, 25, 'C', 'X')
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('alternate_bases', cm.exception.message_dict)
    def test_failure_not_reference_sequence(self):
        with self.assertRaises(ValidationError) as cm:
            build_library.make_genome_variant(0, 24, 25, 'A', 'G')
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('reference_bases', cm.exception.message_dict)
    def test_failure_same_genome_variant(self):
        build_library.make_genome_variant(0, 24, 25, 'C', 'G')
        with self.assertRaises(ValidationError) as cm:
            build_library.make_genome_variant(1, 24, 25, 'C', 'G')
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('__all__', cm.exception.message_dict)
    def failure_same_reference_and_alternate_bases(self):
        with self.assertRaises(ValidationError) as cm:
            build_library.make_genome_variant(0, 24, 25, 'C', 'C')
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('reference_bases-alternate_bases', cm.exception.message_dict)
    def test_failure_info_not_json(self):
        with self.assertRaises(ValidationError) as cm:
            build_library.make_genome_variant(0, 24, 25, 'C', 'G', info="I don't know what the phenotype is")
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('info', cm.exception.message_dict)
    def test_success_snp(self):
        build_library.make_genome_variant(0, 24, 25, 'C', 'G')
        build_library.make_genome_variant(1, 24, 25, 'C', 'A', names="dbsnp120:rs12299\tdbsnp121:rs120")
        build_library.make_genome_variant(2, 24, 25, 'C', 'T', names="dbsnp120:rs12299\tdbsnp121:rs120", info='{"phenotype":"Unknown!"}')
        build_library.make_genome_variant(3, 25, 26, 'G', 'C', info='{"phenotype":"Unknown!"}')
    def test_success_insertion(self):
        build_library.make_genome_variant(0, 24, 24, '-', "AAAG")
    def test_success_deletion(self):
        build_library.make_genome_variant(0, 24, 28, 'CGTC', '-')
    def test_success_sub(self):
        build_library.make_genome_variant(0, 24, 28, 'CGTC', 'AAG')
    def test_success_snp_on_start_tag_unable_to_span(self):
        build_library.make_genome_variant(0, 23, 24, 'T', 'A')
    def test_success_deletion_on_start_tag_unable_to_span(self):
        build_library.make_genome_variant(0, 22, 24, 'GT', '-')
    def test_success_insertion_on_start_tag_unable_to_span(self):
        build_library.make_genome_variant(0, 22, 22, '-', 'AGAA')
    def test_success_sub_on_start_tag_unable_to_span(self):
        build_library.make_genome_variant(0, 22, 23, 'G', 'AGAA')
    def test_success_snp_on_end_tag_unable_to_span(self):
        build_library.make_genome_variant(0, 106, 107, 'G', 'A')
    def test_success_deletion_on_end_tag_unable_to_span(self):
        build_library.make_genome_variant(0, 105, 107, 'GG', '-')
    def test_success_insertion_on_end_tag_unable_to_span(self):
        build_library.make_genome_variant(0, 107, 107, '-', 'AG')
    def test_success_sub_on_end_tag_unable_to_span(self):
        build_library.make_genome_variant(0, 106, 107, 'G', 'ATG')
################################## TEST GenomeVariantTranslation model ###################################
class TestGenomeVariantTranslationModel(TestCase):
    #Check failures
    #tv missing gv assembly
    def test_failure_tile_variant_missing_genome_variant_assembly(self):
        build_library.make_reference()
        tv = build_library.make_tile_variant(1, "ACGGCAGTAGTTTTGCCGCTCGGTTGTCAGAATGTTTGGAGGGCGGTACG".lower(), 1, start_tag="ACGGCAGTAGTTTTGCCGCTCGGT")
        gv = build_library.make_genome_variant(0, 24, 25, 'C', 'T')
        locus = TileLocusAnnotation.objects.filter(tile_position=0).get(assembly_int=ASSEMBLY_19)
        locus.delete()
        with self.assertRaises(ValidationError) as cm:
            GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=24, end=25).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('assembly_int.get_locus_error', cm.exception.message_dict)
    def test_failure_spanning_tile_variant_missing_genome_variant_assembly_in_middle_tile(self):
        build_library.make_reference()
        tv = build_library.make_tile_variant(
            1,
            "ACGGCAGTAGTTTTGCCGCTCGGTCGTCAGAATGTTTGGAGGGCGGTACAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTG".lower(),
            3,
            start_tag="ACGGCAGTAGTTTTGCCGCTCGGT"
        )
        gv = build_library.make_genome_variant(0, 49, 53, 'GGCT', '-')
        locus = TileLocusAnnotation.objects.filter(tile_position=1).get(assembly_int=ASSEMBLY_19)
        locus.delete()
        with self.assertRaises(ValidationError) as cm:
            GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=49, end=49).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('assembly_int', cm.exception.message_dict)
    #gv on different chromosome
    @override_settings(CHR_PATH_LENGTHS = (0,2,3))
    def test_failure_tile_variant_different_chromosome_int(self):
        build_library.make_reference()
        chr2_tilevar = build_library.make_tile_variant(
            int('2'+step_min+variant_value_min,16)+1,
            "CTACCGTTTAGGCGGATATCGCGTGTTTCCTTAAACTCATCTCCTGGGGG".lower(),
            1,
            start_tag="CTACCGTTTAGGCGGATATCGCGT",
            end_tag="TTCCTTAAACTCATCTCCTGGGGG"
        )
        gv = build_library.make_genome_variant(0, 24, 25, 'C', 'G')
        with self.assertRaises(ValidationError) as cm:
            GenomeVariantTranslation(tile_variant=chr2_tilevar, genome_variant=gv, start=24, end=25).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('chromosome_int', cm.exception.message_dict)
    @override_settings(CHR_PATH_LENGTHS = (0,2,3))
    def test_failure_spanning_tile_variant_different_chromosome_in_middle_tile(self):
        build_library.make_reference()
        chr2_tilevar = build_library.make_tile_variant(
            int('2'+step_min+variant_value_min,16)+1,
            "CTACCGTTTAGGCGGATATCGCGTCTATCCTTAAACTCATCTCCTGGGGGGAGGTCGTGGTTTTGAGCCAGTTATGGGGTTCGGCTGACGGGCCGACACATG".lower(),
            3,
            start_tag="CTACCGTTTAGGCGGATATCGCGT",
            end_tag="GTTCGGCTGACGGGCCGACACATG"
        )
        gv = build_library.make_genome_variant(0, 26, 27, 'T', 'A')
        with self.assertRaises(ValidationError) as cm:
            GenomeVariantTranslation(tile_variant=chr2_tilevar, genome_variant=gv, start=24, end=25).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('chromosome_int', cm.exception.message_dict)
    #gv loci on different alternate chromosomes
    @override_settings(CHR_PATH_LENGTHS = (0,63,125,187,234,279,327,371,411,454,496,532,573,609,641,673,698,722,742,761,781,795,811,851,862,863,864))
    def test_failure_tile_variant_different_alternate_chromosome_name(self):
        build_library.make_alternate_reference()
        chr_other_path = hex(settings.CHR_PATH_LENGTHS[CHR_OTHER-1]).lstrip('0x').zfill(NUM_HEX_INDEXES_FOR_PATH)
        tv = build_library.make_tile_variant(
            int(chr_other_path+step_min+variant_value_min,16)+1,
            "ACGGCAGTAGTTTTGCCGCTCGGTGGTCAGAATGTTTGGAGGGCGGTACG".lower(),
            1,
            start_tag="ACGGCAGTAGTTTTGCCGCTCGGT"
        )
        gv = build_library.make_genome_variant(0,24,25, 'C', 'G', chrom=CHR_OTHER, chrom_name="bar")
        with self.assertRaises(ValidationError) as cm:
            GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=24, end=25).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('alternate_chromosome_name', cm.exception.message_dict)
    @override_settings(CHR_PATH_LENGTHS = (0,63,125,187,234,279,327,371,411,454,496,532,573,609,641,673,698,722,742,761,781,795,811,851,862,863,864))
    def test_failure_spanning_tile_variant_different_alternate_chromosome_name_in_middle_tile(self):
        build_library.make_alternate_reference()
        chr_other_path = hex(settings.CHR_PATH_LENGTHS[CHR_OTHER-1]).lstrip('0x').zfill(NUM_HEX_INDEXES_FOR_PATH)
        tv = build_library.make_tile_variant(
            int(chr_other_path+step_min+variant_value_min,16)+1,
            "ACGGCAGTAGTTTTGCCGCTCGGTCGACAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTGAACGCACCGGAACTTGTGTTTGTGTG".lower(),
            3,
            start_tag="ACGGCAGTAGTTTTGCCGCTCGGT"
        )
        gv = build_library.make_genome_variant(0, 25,26, 'T', 'A', chrom=CHR_OTHER, chrom_name="bar")
        with self.assertRaises(ValidationError) as cm:
            GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=24, end=25).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('alternate_chromosome_name', cm.exception.message_dict)
    #gv loci not covered
    def test_failure_tile_variant_loci_larger_than_genome_variant_loci(self):
        build_library.make_reference()
        gv = build_library.make_genome_variant(0, 24, 25, 'C', 'G')
        s = '0'*(NUM_HEX_INDEXES_FOR_STEP-1)+'1'
        vv = '0'*(NUM_HEX_INDEXES_FOR_VARIANT_VALUE-1)+'1'
        tv = build_library.make_tile_variant(int(s+vv,16), "TCAGAATGTTTGGAGGGCGGTACGGGTAGAGATATCACCCTCTGCTACTC".lower(), 1)
        with self.assertRaises(ValidationError) as cm:
            GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=24, end=25).save()
        self.assertEqual(len(cm.exception.message_dict), 2)
        self.assertIn('genome_variant.start_int', cm.exception.message_dict)
        self.assertIn('genome_variant.end_int', cm.exception.message_dict)
    def test_failure_spanning_tile_variant_loci_larger_than_genome_variant_loci(self):
        build_library.make_reference()
        gv = build_library.make_genome_variant(0, 24, 25, 'C', 'G')
        s = '0'*(NUM_HEX_INDEXES_FOR_STEP-1)+'1'
        vv = '0'*(NUM_HEX_INDEXES_FOR_VARIANT_VALUE-1)+'1'
        tv = build_library.make_tile_variant(int(s+vv,16), "TCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTGAAGGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATG".lower(), 3, end_tag="GTCGCCCACTACGCACGTTATATG")
        with self.assertRaises(ValidationError) as cm:
            GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=24, end=25).save()
        self.assertEqual(len(cm.exception.message_dict), 2)
        self.assertIn('genome_variant.start_int', cm.exception.message_dict)
        self.assertIn('genome_variant.end_int', cm.exception.message_dict)
    def test_failure_tile_variant_loci_smaller_than_genome_variant_loci(self):
        build_library.make_reference()
        gv = build_library.make_genome_variant(0, 75, 76, 'C', 'A')
        tv = build_library.make_tile_variant(1, "ACGGCAGTAGTTTTGCCGCTCGGTAGTCAGAATGTTTGGAGGGCGGTACG".lower(), 1, start_tag="ACGGCAGTAGTTTTGCCGCTCGGT")
        with self.assertRaises(ValidationError) as cm:
            GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=24, end=25).save()
        self.assertEqual(len(cm.exception.message_dict), 2)
        self.assertIn('genome_variant.start_int', cm.exception.message_dict)
        self.assertIn('genome_variant.end_int', cm.exception.message_dict)
    def test_failure_spanning_tile_variant_loci_smaller_than_genome_variant_loci(self):
        build_library.make_reference()
        gv = build_library.make_genome_variant(0, 102, 103, 'T', 'A')
        tv = build_library.make_tile_variant(1, "ACGGCAGTAGTTTTGCCGCTCGGTCGACAGAATGTTTGGAGGGCGGTACGGCAAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTG".lower(), 3, start_tag="ACGGCAGTAGTTTTGCCGCTCGGT")
        with self.assertRaises(ValidationError) as cm:
            GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=26, end=27).save()
        self.assertEqual(len(cm.exception.message_dict), 2)
        self.assertIn('genome_variant.start_int', cm.exception.message_dict)
        self.assertIn('genome_variant.end_int', cm.exception.message_dict)
    #gv loci partially covered (beginning and ending)
    def test_failure_tile_variant_loci_partially_larger_than_genome_variant_loci(self):
        build_library.make_reference()
        gv = build_library.make_genome_variant(0, 25, 51, 'GTCAGAATGTTTGGAGGGCGGTACGG', '-')
        s = '0'*(NUM_HEX_INDEXES_FOR_STEP-1)+'1'
        vv = '0'*(NUM_HEX_INDEXES_FOR_VARIANT_VALUE-1)+'1'
        tv = build_library.make_tile_variant(int(s+vv,16), "TCAGAATGTTTGGAGGGCGGTACGACTAGAGATATCACCCTCTGCTACTC".lower(), 1)
        with self.assertRaises(ValidationError) as cm:
            GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=24, end=24).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('genome_variant.start_int', cm.exception.message_dict)
    def test_failure_spanning_tile_variant_loci_partially_larger_than_genome_variant_loci(self):
        build_library.make_reference()
        gv = build_library.make_genome_variant(0, 25, 51, 'GTCAGAATGTTTGGAGGGCGGTACGG', '-')
        s = '0'*(NUM_HEX_INDEXES_FOR_STEP-1)+'1'
        vv = '0'*(NUM_HEX_INDEXES_FOR_VARIANT_VALUE-1)+'1'
        tv = build_library.make_tile_variant(int(s+vv,16), "TCAGAATGTTTGGAGGGCGGTACGACAGAGATATCACCCTCTGCTACTCAAGGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATG".lower(), 3, end_tag="GTCGCCCACTACGCACGTTATATG")
        with self.assertRaises(ValidationError) as cm:
            GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=24, end=24).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('genome_variant.start_int', cm.exception.message_dict)
    def test_failure_tile_variant_loci_partially_smaller_than_genome_variant_loci(self):
        build_library.make_reference()
        gv = build_library.make_genome_variant(0, 25, 51, 'GTCAGAATGTTTGGAGGGCGGTACGG', '-')
        tv = build_library.make_tile_variant(1, "ACGGCAGTAGTTTTGCCGCTCGGTAGTCAGAATGTTTGGAGGGCGGTACG".lower(), 1, start_tag="ACGGCAGTAGTTTTGCCGCTCGGT")
        with self.assertRaises(ValidationError) as cm:
            GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=24, end=24).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('genome_variant.end_int', cm.exception.message_dict)
    def test_failure_spanning_tile_variant_loci_partially_smaller_than_genome_variant_loci(self):
        build_library.make_reference()
        gv = build_library.make_genome_variant(0, 77, 103, 'ACGCACCGGAACTTGTGTTTGTGTGT', '-')
        tv = build_library.make_tile_variant(
            1,
            "ACGGCAGTAGTTTTGCCGCTCGGTCGACAGAATGTTTGGAGGGCGGTACGGCAAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTG".lower(),
            3,
            start_tag="ACGGCAGTAGTTTTGCCGCTCGGT"
        )
        with self.assertRaises(ValidationError) as cm:
            GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=26, end=26).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('genome_variant.end_int', cm.exception.message_dict)
    #gv loci partially in TAG (beginning and ending)
    def test_failure_genome_variant_partially_in_start_tag(self):
        build_library.make_reference()
        gv = build_library.make_genome_variant(0, 49, 51, 'GG', '-')
        tv = build_library.make_tile_variant(int('1'+variant_value_min,16)+1, "TCAGAATGTTTGGAGGGCGGTACCTAGAGATATCACCCTCTGCTACTC".lower(), 1, start_tag="TCAGAATGTTTGGAGGGCGGTACC")
        with self.assertRaises(ValidationError) as cm:
            GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=24, end=24).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('genome_variant.start_int', cm.exception.message_dict)
    def test_failure_genome_variant_partially_in_start_tag_for_spanning_tile_variant(self):
        build_library.make_reference()
        gv = build_library.make_genome_variant(0, 49, 51, 'GG', '-')
        tv = build_library.make_tile_variant(int('1'+variant_value_min,16)+1, "TCAGAATGTTTGGAGGGCGGTACCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTG".lower(), 2, start_tag="TCAGAATGTTTGGAGGGCGGTACC")
        with self.assertRaises(ValidationError) as cm:
            GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=24, end=24).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('genome_variant.start_int', cm.exception.message_dict)
    def test_failure_genome_variant_partially_in_end_tag(self):
        build_library.make_reference()
        gv = build_library.make_genome_variant(0, 25, 27, 'GT', 'A')
        tv = build_library.make_tile_variant(1, "ACGGCAGTAGTTTTGCCGCTCGGTCATCAGAATGTTTGGAGGGCGGTACG".lower(), 1,  start_tag="ACGGCAGTAGTTTTGCCGCTCGGT")
        with self.assertRaises(ValidationError) as cm:
            GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=25, end=26).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('genome_variant.end_int', cm.exception.message_dict)
    def test_failure_genome_variant_partially_in_end_tag_for_spanning_tile_variant(self):
        build_library.make_reference()
        gv = build_library.make_genome_variant(0, 77, 79, 'AC', 'T')
        tv = build_library.make_tile_variant(1, "ACGGCAGTAGTTTTGCCGCTCGGTCGTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCATCGCACCGGAACTTGTGTTTGTGTG".lower(), 3,  start_tag="ACGGCAGTAGTTTTGCCGCTCGGT")
        with self.assertRaises(ValidationError) as cm:
            GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=77, end=78).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('genome_variant.end_int', cm.exception.message_dict)
    #gv alternate bases not bases in variant
    def test_failure_alternate_bases_not_in_tile_variant(self):
        build_library.make_reference()
        gv = build_library.make_genome_variant(0, 24, 25, 'C', 'T')
        tv = build_library.make_tile_variant(1, "ACGGCAGTAGTTTTGCCGCTCGGTGGTCAGAATGTTTGGAGGGCGGTACG".lower(), 1,  start_tag="ACGGCAGTAGTTTTGCCGCTCGGT")
        with self.assertRaises(ValidationError) as cm:
            GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=24, end=25).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('genome_variant.alternate_bases', cm.exception.message_dict)
    def test_failure_start_or_end_is_negative(self):
        build_library.make_reference()
        gv = build_library.make_genome_variant(0, 24, 25, 'C', 'T')
        tv = build_library.make_tile_variant(1, "ACGGCAGTAGTTTTGCCGCTCGGTTGTCAGAATGTTTGGAGGGCGGTACG".lower(), 1,  start_tag="ACGGCAGTAGTTTTGCCGCTCGGT")
        with self.assertRaises(ValidationError) as cm:
            GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=-1, end=25).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('start', cm.exception.message_dict)
        with self.assertRaises(ValidationError) as cm:
            GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=24, end=-1).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertIn('end', cm.exception.message_dict)
    #gv on start or end of path
    def test_success_genome_variant_partially_in_start_tag_at_beginning_of_path(self):
        build_library.make_reference()
        gv = build_library.make_genome_variant(0, 23, 25, 'TC', 'A')
        tv = build_library.make_tile_variant(1, "ACGGCAGTAGTTTTGCCGCTCGGTAGTCAGAATGTTTGGAGGGCGGTACG".lower(), 1,  start_tag="ACGGCAGTAGTTTTGCCGCTCGGT")
        GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=24, end=25).save()
    def test_success_genome_variant_partially_in_start_tag_at_beginning_of_path_for_spanning_tile_variant(self):
        build_library.make_reference()
        gv = build_library.make_genome_variant(0, 23, 25, 'TC', 'A')
        tv = build_library.make_tile_variant(1, "ACGGCAGTAGTTTTGCCGCTCGGTAGTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTG".lower(), 3,  start_tag="ACGGCAGTAGTTTTGCCGCTCGGT")
        GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=24, end=25).save()
    def test_success_genome_variant_partially_in_end_tag_at_end_of_path(self):
        build_library.make_reference()
        gv = build_library.make_genome_variant(0, 105, 107, 'GG', 'A')
        tv = build_library.make_tile_variant(int('3'+variant_value_min,16)+1, "CGCACCGGAACTTGTGTTTGTGTGTGTATCGCCCACTACGCACGTTATATG".lower(), 1,  end_tag="ATCGCCCACTACGCACGTTATATG")
        GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=27, end=28).save()
    def test_success_genome_variant_partially_in_end_tag_at_end_of_path_for_spanning_tile_variant(self):
        build_library.make_reference()
        gv = build_library.make_genome_variant(0, 105, 107, 'GG', 'A')
        tv = build_library.make_tile_variant(int('1'+variant_value_min,16)+1, "TCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTGTGTATCGCCCACTACGCACGTTATATG".lower(), 3,  end_tag="ATCGCCCACTACGCACGTTATATG")
        GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=79, end=80).save()
    #SNP gv success on tv
    def test_success_snp_tile_variant(self):
        build_library.make_reference()
        build_library.make_basic_snp_genome_variant()
    #Insertion gv sucess
    def test_success_ins_tile_variant(self):
        build_library.make_reference()
        build_library.make_basic_ins_genome_variant()
    #Deletion gv success
    def test_success_del_tile_variant(self):
        build_library.make_reference()
        build_library.make_basic_del_genome_variant()
    #Substitution gv success
    def test_success_sub_tile_variant(self):
        build_library.make_reference()
        build_library.make_basic_sub_genome_variant()
    #gv loci in spanning tile where TAG would normally be
    #Test many-to-many relations, spanning variants, etc
    def test_success_complicated_library(self):
        build_library.make_entire_library()
################################## TEST GenomeStatistic model ###################################
class TestGenomeStatisticModel(TestCase):
    @skipIf(GENOME-1 in supported_statistics_type_ints, "Checking behavior for too small statistics type, but GENOME-1 is defined")
    def test_negative_statistics_int(self):
        with self.assertRaises(ValidationError) as cm:
            GenomeStatistic(statistics_type=GENOME-1, num_of_positions=0, num_of_tiles=0).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertTrue('statistics_type' in cm.exception.message_dict)
    @skipIf(PATH+1 in supported_statistics_type_ints, "Checking behavior for too big statistics type, but PATH+1 is defined")
    def test_too_big_statistics_int(self):
        with self.assertRaises(ValidationError) as cm:
            GenomeStatistic(statistics_type=PATH+1, num_of_positions=0, num_of_tiles=0).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertTrue('statistics_type' in cm.exception.message_dict)
    def test_too_small_path_name_for_genome_or_chrom_statistic(self):
        with self.assertRaises(ValidationError) as cm:
            GenomeStatistic(statistics_type=GENOME, path_name=-2, num_of_positions=0, num_of_tiles=0).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertTrue('path_name' in cm.exception.message_dict)
        with self.assertRaises(ValidationError) as cm:
            GenomeStatistic(statistics_type=CHR_1, path_name=-2, num_of_positions=0, num_of_tiles=0).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertTrue('path_name' in cm.exception.message_dict)
        with self.assertRaises(ValidationError) as cm:
            GenomeStatistic(statistics_type=CHR_OTHER, path_name=-2, num_of_positions=0, num_of_tiles=0).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertTrue('path_name' in cm.exception.message_dict)
    def test_too_big_path_name_for_genome_or_chrom_statistic(self):
        with self.assertRaises(ValidationError) as cm:
            GenomeStatistic(statistics_type=GENOME, path_name=0, num_of_positions=0, num_of_tiles=0).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertTrue('path_name' in cm.exception.message_dict)
        with self.assertRaises(ValidationError) as cm:
            GenomeStatistic(statistics_type=CHR_1, path_name=0, num_of_positions=0, num_of_tiles=0).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertTrue('path_name' in cm.exception.message_dict)
        with self.assertRaises(ValidationError) as cm:
            GenomeStatistic(statistics_type=CHR_OTHER, path_name=0, num_of_positions=0, num_of_tiles=0).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertTrue('path_name' in cm.exception.message_dict)
    def test_neg_one_path_name_for_path_statistic(self):
        with self.assertRaises(ValidationError) as cm:
            GenomeStatistic(statistics_type=PATH, path_name=-1, num_of_positions=0, num_of_tiles=0).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertTrue('path_name' in cm.exception.message_dict)
    def test_too_big_path_name_for_path_statistic(self):
        with self.assertRaises(ValidationError) as cm:
            GenomeStatistic(statistics_type=PATH, path_name=settings.CHR_PATH_LENGTHS[-1], num_of_positions=0, num_of_tiles=0).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertTrue('path_name' in cm.exception.message_dict)
    def test_negative_num_positions(self):
        with self.assertRaises(ValidationError) as cm:
            GenomeStatistic(statistics_type=GENOME, num_of_positions=-1, num_of_tiles=0).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertTrue('num_of_positions' in cm.exception.message_dict)
    def test_negative_num_tiles(self):
        with self.assertRaises(ValidationError) as cm:
            GenomeStatistic(statistics_type=GENOME, num_of_positions=0, num_of_tiles=-1).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertTrue('num_of_tiles' in cm.exception.message_dict)
    def test_more_positions_than_tiles(self):
        with self.assertRaises(ValidationError) as cm:
            GenomeStatistic(statistics_type=GENOME, num_of_positions=2, num_of_tiles=1).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertTrue('num_of_positions-num_of_tiles' in cm.exception.message_dict)
    def test_tiles_without_positions(self):
        with self.assertRaises(ValidationError) as cm:
            GenomeStatistic(statistics_type=GENOME, num_of_positions=0, num_of_tiles=1).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertTrue('num_of_positions-num_of_tiles' in cm.exception.message_dict)
    def test_weird_spanning_tiles(self):
        with self.assertRaises(ValidationError) as cm:
            GenomeStatistic(statistics_type=GENOME, num_of_positions=1, num_of_tiles=1, max_num_positions_spanned=0).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertTrue('max_num_positions_spanned' in cm.exception.message_dict)
    def test_duplicate_chromosome_statistics(self):
        GenomeStatistic(statistics_type=GENOME, num_of_positions=1, num_of_tiles=1).save()
        with self.assertRaises(ValidationError) as cm:
            GenomeStatistic(statistics_type=GENOME, num_of_positions=1, num_of_tiles=2).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertTrue('__all__' in cm.exception.message_dict)
    def test_duplicate_path_statistics(self):
        GenomeStatistic(statistics_type=PATH, path_name=1, num_of_positions=1, num_of_tiles=1).save()
        with self.assertRaises(ValidationError) as cm:
            GenomeStatistic(statistics_type=PATH, path_name=1, num_of_positions=1, num_of_tiles=2).save()
        self.assertEqual(len(cm.exception.message_dict), 1)
        self.assertTrue('__all__' in cm.exception.message_dict)
    def test_successful_save(self):
        GenomeStatistic(statistics_type=PATH, path_name=settings.CHR_PATH_LENGTHS[-1]-1, num_of_positions=0, num_of_tiles=0).save()
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
        self.assertEqual(GenomeStatistic.objects.count(), len(supported_statistics_type_ints)-1+settings.CHR_PATH_LENGTHS[-1])
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
        version, path, step = basic_fns.get_position_ints_from_position_int(tile_int)
        check_vals = {0:{'num_pos':5, 'num_tiles':10, 'max_num_spanned':3}, #Path 0
                      1:{'num_pos':1, 'num_tiles':5, 'max_num_spanned':1}, #Path 1
                      path:{'num_pos':2, 'num_tiles':6, 'max_num_spanned':2}} #Path 63
        for i in range(settings.CHR_PATH_LENGTHS[-1]):
            path_stats = GenomeStatistic.objects.filter(statistics_type=PATH).filter(path_name=i).all()
            self.assertEqual(len(path_stats), 1)
            path_stats = path_stats.first()
            if i in check_vals:
                self.assertEqual(path_stats.num_of_positions, check_vals[i]['num_pos'])
                self.assertEqual(path_stats.num_of_tiles, check_vals[i]['num_tiles'])
                self.assertEqual(path_stats.max_num_positions_spanned, check_vals[i]['max_num_spanned'])
            else:
                self.assertEqual(path_stats.num_of_positions, 0)
                self.assertEqual(path_stats.num_of_tiles, 0)
                self.assertIsNone(path_stats.max_num_positions_spanned)
    def test_initialize_failure_after_initializing_once(self):
        gen_stats.initialize(silent=True)
        self.assertRaises(ExistingStatisticsError, gen_stats.initialize)
    def test_update_on_same_library(self):
        gen_stats.initialize(silent=True)
        gen_stats.update(silent=True)
        self.assertEqual(GenomeStatistic.objects.count(), len(supported_statistics_type_ints)-1+settings.CHR_PATH_LENGTHS[-1])
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
        version, path, step = basic_fns.get_position_ints_from_position_int(tile_int)
        check_vals = {0:{'num_pos':5, 'num_tiles':10, 'max_num_spanned':3}, #Path 0
                      1:{'num_pos':1, 'num_tiles':5, 'max_num_spanned':1}, #Path 1
                      path:{'num_pos':2, 'num_tiles':6, 'max_num_spanned':2}} #Path 63
        for i in range(settings.CHR_PATH_LENGTHS[-1]):
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
        s='0'*NUM_HEX_INDEXES_FOR_STEP
        new_start_tag = Tile.objects.get(tile_position_int=int('1'+s, 16)).end_tag
        locus = TileLocusAnnotation.objects.filter(assembly_int=ASSEMBLY_19).filter(chromosome_int=CHR_1).order_by('start_int').last().end_int
        locus -= TAG_LENGTH
        chr1_path1_new_tiles = [
            {'vars':2, 'lengths':[220, 1130], 'spanning_nums':[1,4]},
            {'vars':1, 'lengths':[335], 'spanning_nums':[1]},
            {'vars':1, 'lengths':[346], 'spanning_nums':[1]},
            {'vars':1, 'lengths':[201], 'spanning_nums':[1]}
        ]
        tile_objects = []
        for i, position in enumerate(chr1_path1_new_tiles):
            pos_int = int('1'+hex(i+1).lstrip('0x').zfill(NUM_HEX_INDEXES_FOR_STEP), 16)
            t, ignore, new_start_tag, ignore = mk_tile(
                pos_int,
                locus,
                locus+position['lengths'][0],
                1,
                [position['lengths'][0]],
                spanning_nums=[position['spanning_nums'][0]],
                start_tag=new_start_tag,
                assembly=ASSEMBLY_19
            )
            tile_objects.append(t)
            locus += chr1_path1_new_tiles[i]['lengths'][0] - TAG_LENGTH
        for i, position in enumerate(chr1_path1_new_tiles):
            if position['vars'] > 1:
                tile = tile_objects[i]
                mk_tilevars(position['vars'], position['lengths'], tile, position['spanning_nums'], start_variant_value=1)
        chr3_paths = {
            CHR_3: {
                hex(settings.CHR_PATH_LENGTHS[CHR_2]).lstrip('0x'): [
                    {'vars':6, 'lengths':[250,300,300,310,260,275], 'spanning_nums':[1,1,1,1,1,1]},
                    {'vars':1, 'lengths':[301], 'spanning_nums':[1]},
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
        version, path_on_2, step = basic_fns.get_position_ints_from_position_int(tile_int)
        tile_int, foo = basic_fns.get_min_position_and_tile_variant_from_chromosome_int(CHR_3)
        version, path_on_3, step = basic_fns.get_position_ints_from_position_int(tile_int)
        check_vals = {0:{'num_pos':5, 'num_tiles':10, 'max_num_spanned':3},
                      1:{'num_pos':5, 'num_tiles':10, 'max_num_spanned':4},
                      path_on_2:{'num_pos':2, 'num_tiles':6, 'max_num_spanned':2},
                      path_on_3:{'num_pos':2, 'num_tiles':7, 'max_num_spanned':1},
                     }
        for i in range(settings.CHR_PATH_LENGTHS[-1]):
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
        make_tiles(INVALID_HUMAN_LIBRARY, ignore_loci=True)
        self.assertRaises(InvalidGenomeError, gen_stats.initialize)
    def test_update_failure_invalid_genome(self):
        ## Genome Statistics assumes a human genome (number of chromosomes)
        gen_stats.initialize(silent=True)
        make_tiles(INVALID_HUMAN_LIBRARY, ignore_loci=True)
        self.assertRaises(InvalidGenomeError, gen_stats.update)
################################## TEST lantern_query_functions ###################################
#Checking behavior for when lantern isn't running
#lantern_query_functions is a wrapper around lantern APIs, so actual behavior should be tested with actual lantern
class TestLanternQueryFunctionsWithoutPyLanternRunning(TestCase):
    def test_failure_get_population_names_and_check_lantern_version(self):
        with self.assertRaises(requests.ConnectionError) as cm:
            lantern_query_fns.get_population_names_and_check_lantern_version()
    def test_failure_make_sample_position_variant_query(self):
        with self.assertRaises(requests.ConnectionError) as cm:
            lantern_query_fns.make_sample_position_variant_query('000.00.0000')
    def test_failure_get_population_sequences_over_position_range(self):
        with self.assertRaises(requests.ConnectionError) as cm:
            lantern_query_fns.get_population_sequences_over_position_range(0, 3)
    def test_failure_get_sub_population_sequences_over_position_range(self):
        with self.assertRaises(requests.ConnectionError) as cm:
            lantern_query_fns.get_population_sequences_over_position_range(0, 3, sub_population_list=['sample1'])
##################################     TEST query_functions      ###################################
class TestQueryFunctionsSparsely(LiveServerTestCase):
    def setUp(self):
        self.v='0'*NUM_HEX_INDEXES_FOR_VERSION
        self.p='0'*NUM_HEX_INDEXES_FOR_PATH
        self.s='0'*NUM_HEX_INDEXES_FOR_STEP
        self.vv = '0'*(NUM_HEX_INDEXES_FOR_CGF_VARIANT_VALUE)
        self.min_name = string.join([self.p,self.v,self.s,self.vv], sep='.')
        tile, tilevar = make_tile_position_and_variant(0, 0, 250)
        self.tile = tile
        self.tilevar = tilevar
    def test_failure_due_to_deletion(self):
        LanternTranslator(lantern_name=self.min_name, tile_library_host=self.live_server_url.strip().lstrip('http://'), tile_variant_int=0).save()
        self.tilevar.delete()
        with self.assertRaises(LanternTranslator.DegradedVariantError) as cm:
            query_fns.get_bases_from_lantern_name(self.min_name)
    def test_success_return_empty_string_if_no_lantern_translator(self):
        bases = query_fns.get_bases_from_lantern_name(self.min_name)
        self.assertEqual(bases, "")
    def test_success_return_bases(self):
        LanternTranslator(lantern_name=self.min_name, tile_library_host=self.live_server_url.strip().lstrip('http://'), tile_variant_int=0).save()
        bases = query_fns.get_bases_from_lantern_name(self.min_name)
        self.assertEqual(bases, self.tilevar.sequence.upper())


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
