"""
Notes for later: maybe collections.namedtuple is better suited for this?
"""
import json
import hashlib
import datetime
import string
import re

import basic_functions as basic_fns
import validators as validation_fns

from errors import TileLibraryValidationError

def write_line(inp_list, out, num_to_keep=None):
    thingsToJoin = []
    for i, foo in enumerate(inp_list):
        if num_to_keep == None or i < num_to_keep:
            if not foo and type(foo) == str:
                thingsToJoin.append('""')
            else:
                thingsToJoin.append(str(foo))
    thingsToJoin[-1] += '\n'
    out.write(string.join(thingsToJoin, sep=','))

class TileObject(object):
    """
    Meant to be holder for both tile and tilevariant
    tile.csv  (tile_position_int, is_start_of_path, is_end_of_path, start_tag, end_tag, created)
    tilelocusannotation.csv (assembly_int, chromosome_int, alternate_chromosome_name, start_int, end_int, tile_position_id, tile_variant_value)
    tilevariant.csv (tile_variant_int, tile_id, num_positions_spanned, variant_value, length, md5sum, created, last_modified, sequence, start_tag, end_tag)

    """
    def __init__(self, fastj_line, version, path, num_hex_digits_for_version, num_hex_digits_for_path, num_hex_digits_for_step, num_hex_digits_for_variant_value, tag_length, chr_choices, chr_other, reference=True):
        self.version = version
        self.path = path
        self.num_hex_digits_for_version = num_hex_digits_for_version
        self.num_hex_digits_for_path = num_hex_digits_for_path
        self.num_hex_digits_for_step = num_hex_digits_for_step
        self.num_hex_digits_for_variant_value = num_hex_digits_for_variant_value
        self.tag_length = tag_length
        if reference:
            self.read_ref_line(fastj_line, {j:i for i,j in chr_choices}, chr_other)
        else:
            self.read_line(fastj_line, {j:i for i,j in chr_choices}, chr_other)
    def read_ref_line(self, fastj_line, chr_names, chr_other):
        """
        Does not initialize start_seq, end_seq, sequence, or md5sum, since these require knowing the sequence and are not passed in for reference fj
        Does not initialize the tile variant value, since this requires knowledge about the library

        If the tile starts or ends the position, it checks the line input (that it is periods), then replaces it with the empty string, so the start_tag/end_tag pair is correct
        """
        fastj_data = json.loads(fastj_line.strip().lstrip('> '))
        assert sorted(fastj_data.keys()) == ['copy', 'endTag', 'locus', 'n', 'startTag', 'tileID'], "%s" % (sorted(fastj_data.keys()))
        preliminary_cgf_like_tile_name = str(fastj_data['tileID'])
        path, foo, step, foo = preliminary_cgf_like_tile_name.split('.')
        assert path == self.path, "passed in FASTJ entry has incorrect path"
        step = step.zfill(self.num_hex_digits_for_step)
        self.step = step
        self.tile_position_int = int(self.version+self.path+step, 16)
        self.start_tag = str(fastj_data[u'startTag']).lower()
        self.end_tag = str(fastj_data[u'endTag']).lower()
        self.start_seq = None
        self.end_seq = None
        self.length = int(fastj_data[u'n'])
        self.sequence = None
        self.md5sum = None
        self.variant_value = None
        self.tile_variant_int = None

        locus_str = str(fastj_data[u'locus'][0][u'build'])
        locus_str = locus_str.split(' ')
        assert locus_str[0] == 'hg19', "Currently only can read in assembly hg19"
        if locus_str[1] in chr_names:
            chromosome = chr_names[locus_str[1]]
            chromosome_name = ""
        else:
            chromosome = chr_other
            chromosome_name = locus_str[1]
        if '-' in locus_str[2]:
            self.is_start_of_path = True
            assert self.start_tag == '.'*self.tag_length, "Expects the FASTJ entry to have a start tag of '%s' if it starts the path" % ('.'*self.tag_length)
            self.start_tag = ''
            self.length = self.length - self.tag_length
            locus_start = int(locus_str[2].split('-')[0])
        else:
            self.is_start_of_path = False
            locus_start = int(locus_str[2])
        if '+' in locus_str[3]:
            self.is_end_of_path = True
            assert self.end_tag == '.'*self.tag_length, "Expects the FASTJ entry to have a end tag of '%s' if it ends the path" % ('.'*self.tag_length)
            self.end_tag = ''
            self.length = self.length -self.tag_length
            locus_end = int(locus_str[3].split('+')[0])
        else:
            self.is_end_of_path = False
            locus_end = int(locus_str[3])
        self.locus = LocusObject(19, chromosome, locus_start, locus_end, chrom_name=chromosome_name)
        self.seed_tile_length = 1
        self.tile_position_hex = self.version+self.path+step
    def read_line(self, fastj_line, chr_names, chr_other):
        """
        Does not check initialization of start_seq, end_seq, md5sum, or length since these require knowing the sequence
        Does not initialize sequence
        Does not initialize the tile variant value, since this requires knowledge about the library

        Checks that the locus, the start/ending flags, and start/end tags match
        """
        expected_keys = ['endSeq', 'endTag', 'endTile', 'locus', 'md5sum', 'n', 'nocallCount', 'notes', 'seedTileLength', 'startSeq', 'startTag', 'startTile', 'tileID']
        fastj_data = json.loads(fastj_line.strip().lstrip('> '))
        assert sorted(fastj_data.keys()) == expected_keys, "FASTJ line did not have expected keys: FASTJ lines %s" % (sorted(fastj_data.keys()))
        preliminary_cgf_like_tile_name = str(fastj_data['tileID'])
        path, foo, step, foo = preliminary_cgf_like_tile_name.split('.')
        assert path == self.path, "passed in FASTJ entry has incorrect path"
        step = step.zfill(self.num_hex_digits_for_step)
        self.step = step
        self.tile_position_int = int(self.version+self.path+step, 16)
        self.start_tag = str(fastj_data[u'startTag']).lower()
        self.end_tag = str(fastj_data[u'endTag']).lower()
        self.start_seq = str(fastj_data[u'startSeq']).lower()
        self.end_seq = str(fastj_data[u'endSeq']).lower()
        self.length = int(fastj_data[u'n'])
        self.sequence = None
        self.md5sum = str(fastj_data[u'md5sum'])
        self.variant_value = None
        self.tile_variant_int = None

        self.is_start_of_path = fastj_data['startTile']
        self.is_end_of_path = fastj_data['endTile']

        if self.is_start_of_path:
            assert self.start_tag == "", "Expects the FASTJ entry to have an empty start tag if it starts the path"
        if self.is_end_of_path:
            assert self.end_tag == "", "Expects the FASTJ entry to have an empty end tag if it ends the path"

        self.seed_tile_length = int(fastj_data[u'seedTileLength'])
        self.tile_position_hex = self.version+self.path+step

        #Note well_sequenced or not
        if fastj_data[u'nocallCount'] > 0:
            self.well_sequenced = False
        else:
            self.well_sequenced = True

        #Parse notes to get phase
        for note in fastj_data[u'notes']:
            if note.startswith('Phase'):
                if note.endswith(' A'):
                    self.phase = 0
                elif note.endswith(' B'):
                    self.phase = 1
                else:
                    raise Exception("notes Phase did not end with ' A' or ' B'")

        #Initialize locus
        locus_str = str(fastj_data[u'locus'][0][u'build'])
        locus_str = locus_str.split(' ')
        assert locus_str[0] == 'hg19', "Currently only can read in assembly hg19"
        if locus_str[1] in chr_names:
            chromosome = chr_names[locus_str[1]]
            chromosome_name = ""
        else:
            chromosome = chr_other
            chromosome_name = locus_str[1]
        locus_start = int(locus_str[2])
        locus_end = int(locus_str[3])
        self.locus = LocusObject(19, chromosome, locus_start, locus_end, chrom_name=chromosome_name)
    def add_sequence(self, sequence, logging_file_handle=None):
        sequence = sequence.lower().strip('.')
        digestor = hashlib.new('md5', sequence)
        assert self.sequence == None, "Trying to add sequence to a tile_object that has one already"
        self.sequence = sequence
        #Initialize start sequence
        if self.start_tag != sequence[:self.tag_length]:
            if self.start_seq != None and self.start_seq != sequence[:self.tag_length]:
                logging_file_handle.write("Tile %s: Start sequence (%s) does not match actual start of the sequence (%s)\n" % (str(self.tile_position_hex), str(self.start_seq), str(sequence[:self.tag_length])))
            self.start_seq = sequence[:self.tag_length]
        else:
            self.start_seq = ''
        #Initialize end sequence
        if self.end_tag != sequence[-self.tag_length:]:
            if self.end_seq != None and self.end_seq != sequence[-self.tag_length:]:
                logging_file_handle.write("Tile %s: End sequence (%s) does not match actual end of the sequence (%s)\n" % (str(self.tile_position_hex), str(self.end_seq), str(sequence[-self.tag_length:])))
            self.end_seq = sequence[-self.tag_length:]
        else:
            self.end_seq = ''
        actual_sequence_md5sum = digestor.hexdigest()
        if self.md5sum != None and self.md5sum != actual_sequence_md5sum:
            logging_file_handle.write("Tile %s: sequence md5sum passed in (%s) does not match actual sequence md5sum (%s)\n" % (str(self.tile_position_hex), str(self.md5sum), str(actual_sequence_md5sum)))
        self.md5sum = actual_sequence_md5sum
        assert self.length == len(self.sequence), "%i is not %i, sequence: %s" % (self.length, len(self.sequence), self.sequence)
    def add_variant_value(self, variant_value):
        assert self.variant_value == None, "Trying to add variant value to a tile_object that already has one"
        assert self.tile_variant_int == None, "Trying to add variant value to a tile_object that already has one"
        self.variant_value = variant_value
        hex_var_value = hex(variant_value).lstrip('0x').zfill(self.num_hex_digits_for_variant_value)
        self.tile_variant_int = int(self.version+self.path+self.step+hex_var_value, 16)
    def check_and_write_tile_position(self, file_handle_to_write):
        #(tile_position_int, is_start_of_path, is_end_of_path, start_tag, end_tag, created)
        for attribute in [self.tile_position_int, self.is_start_of_path, self.is_end_of_path, self.start_tag, self.end_tag]:
            assert attribute != None
        version, path, step = basic_fns.get_position_ints_from_position_int(
            self.tile_position_int,
            self.num_hex_digits_for_version,
            self.num_hex_digits_for_path,
            self.num_hex_digits_for_step
        )
        try:
            validation_fns.validate_tile_position_int(
                self.tile_position_int,
                self.num_hex_digits_for_version,
                self.num_hex_digits_for_path,
                self.num_hex_digits_for_step
            )
            validation_fns.validate_tile_position(step, self.is_start_of_path, self.is_end_of_path, self.start_tag, self.end_tag, self.tag_length)
        except TileLibraryValidationError as e:
            raise Exception(e.value)
        write_line([self.tile_position_int, self.is_start_of_path, self.is_end_of_path, self.start_tag, self.end_tag, datetime.datetime.now()], file_handle_to_write)
    def check_and_write_locus(self, chr_path_lengths, file_handle_to_write):
        #(assembly_int, chromosome_int, alternate_chromosome_name, start_int, end_int, tile_position_id, tile_variant_value)
        #chromosome_int, tile_position_int, tile_sequence_length, begin_int, end_int, tag_length, chr_path_lengths, num_v_digits, num_p_digits, num_s_digits, num_vv_digits
        for attribute in [self.locus, self.tile_position_int, self.variant_value]:
            assert attribute != None
        self.locus.check_self()
        try:
            validation_fns.validate_locus(
                self.locus.chromosome,
                self.tile_position_int,
                self.length,
                self.locus.begin,
                self.locus.end,
                self.tag_length,
                chr_path_lengths,
                self.num_hex_digits_for_version,
                self.num_hex_digits_for_path,
                self.num_hex_digits_for_step,
                self.num_hex_digits_for_variant_value
            )
        except TileLibraryValidationError as e:
            raise Exception(e.value)
        write_line([self.locus.assembly, self.locus.chromosome, self.locus.chrom_name, self.locus.begin, self.locus.end, self.tile_position_int, self.variant_value], file_handle_to_write)
    def check_and_write_tile_variant(self, file_handle_to_write):
        #(tile_variant_int, tile_id, num_positions_spanned, variant_value, length, md5sum, created, last_modified, sequence, start_tag, end_tag)
        #   tile_position_int, tile_variant_int, variant_value, sequence, seq_length, seq_md5sum, start_tag, end_tag, is_start_of_path,
        #   is_end_of_path, tag_length, num_v_digits, num_p_digits, num_s_digits, num_vv_digits
        for attribute in [self.tile_variant_int, self.tile_position_int, self.seed_tile_length, self.variant_value, self.length, self.md5sum, self.sequence, self.start_seq, self.end_seq]:
            assert attribute != None
        assert re.match('^[acgtn]*$', self.sequence) != None

        start_to_check = self.start_seq
        if start_to_check == '':
            start_to_check = self.start_tag
        end_to_check = self.end_seq
        if end_to_check == '':
            end_to_check = self.end_tag
        try:
            validation_fns.validate_tile_variant_int(
                self.tile_variant_int,
                self.num_hex_digits_for_version,
                self.num_hex_digits_for_path,
                self.num_hex_digits_for_step,
                self.num_hex_digits_for_variant_value
            )
            validation_fns.validate_num_spanning_tiles(self.seed_tile_length)
            validation_fns.validate_tile_variant(
                self.tile_position_int,
                self.tile_variant_int,
                self.variant_value,
                self.sequence,
                self.length,
                self.md5sum,
                start_to_check,
                end_to_check,
                self.is_start_of_path,
                self.is_end_of_path,
                self.tag_length,
                self.num_hex_digits_for_version,
                self.num_hex_digits_for_path,
                self.num_hex_digits_for_step,
                self.num_hex_digits_for_variant_value
            )
        except TileLibraryValidationError as e:
            raise Exception(e.value)
        write_line(
            [
                self.tile_variant_int,
                self.tile_position_int,
                self.seed_tile_length,
                self.variant_value,
                self.length,
                self.md5sum,
                datetime.datetime.now(),
                datetime.datetime.now(),
                self.sequence,
                self.start_seq,
                self.end_seq
            ],
            file_handle_to_write
        )

class LocusObject(object):
    """Immutable locus object """
    __slots__ = ('_assembly', '_chromosome', '_chrom_name', '_begin', '_end')
    def __init__(self, assembly, chromosome, begin, end, chrom_name=""):
        self._assembly = assembly
        self._chromosome = chromosome
        self._chrom_name = chrom_name
        self._begin = begin
        self._end = end
    @property
    def assembly(self):
        return self._assembly
    @property
    def chromosome(self):
        return self._chromosome
    @property
    def chrom_name(self):
        return self._chrom_name
    @property
    def begin(self):
        return self._begin
    @property
    def end(self):
        return self._end
    def __str__(self):
        if self.chrom_name != "":
            return "Assembly: %s, chromosome: %s, [%s, %s)" % (str(self.assembly), str(self.chrom_name), str(self.begin), str(self.end))
        else:
            return "Assembly: %s, chromosome: %s, [%s, %s)" % (str(self.assembly), str(self.chromosome), str(self.begin), str(self.end))
    def __eq__(self, other):
        return all([
            self.assembly == other.assembly,
            self.chromosome == other.chromosome,
            self.chrom_name == other.chrom_name,
            self.begin == other.begin,
            self.end == other.end,
        ])
    # __cmp__ is difficult without liftover capabilities
    def __hash__(self):
        return hash((self.assembly, self.chromosome, self.chrom_name, self.begin, self.end))
    def get_length_of_locus(self):
        return self.end - self.begin
    def check_same_assembly_and_chrom(self, locus_object):
        assert locus_object.assembly == self.assembly, "Mismatching assembly"
        assert locus_object.chromosome == self.chromosome, "Mismatching chromosome"
        assert locus_object.chrom_name == self.chrom_name, "Mismatching chromosome name"
    def check_self(self):
        assert self.assembly != None
        assert self.chromosome != None
        assert self.chrom_name != None
        assert self.begin != None
        assert self.end != None
        assert self.begin <= self.end, "Expect begin to be smaller than or equal to end [%i, %i]" % (self.begin, self.end)

class TileLibrary(object):
    def __init__(self, version, path):
        #version and path are hex strings
        self.version = version
        self.path = path
        self.library = {}
    def get_size(self):
        return len(self.library), sum(self.library[step].get_size() for step in self.library)
    def get_smaller_library(self, tile_object):
        assert tile_object.version == self.version, "Trying to retrieve Position Tile Library for different version"
        assert tile_object.path == self.path, "Trying to retrieve Position Tile Library for different path"
        step_int = int(tile_object.step,16)
        if step_int in self.library:
            return self.library[step_int]
        else:
            self.library[step_int] = TileLibraryAtPosition(self.version, self.path, tile_object.step)
            return self.library[step_int]
    def get_smaller_library_from_strings(self, version, path, step):
        assert version == self.version, "Trying to retrieve Position Tile Library for different version: %s, %s" % (version, self.version)
        assert path == self.path, "Trying to retrieve Position Tile Library for different path: %s, %s" % (path, self.path)
        step_int = int(step,16)
        if step_int in self.library:
            return self.library[step_int]
        else:
            self.library[step_int] = TileLibraryAtPosition(self.version, self.path, step)
            return self.library[step_int]
    def extend_library(self, tile_object, population_incr=1):
        small_library = self.get_smaller_library(tile_object)
        return small_library.extend_library(tile_object, population_incr=population_incr)
    def check_correct_initialization(self):
        for step in sorted(self.library.keys()):
            self.library[step].check_correct_initialization()
    def write_library(self, num_hex_digits_for_variant_value, out_file_handle):
        for step in sorted(self.library.keys()):
            self.library[step].write_tile_library(num_hex_digits_for_variant_value, out_file_handle)

class TileLibraryAtPosition(object):
    __slots__ = ('version', 'path', 'step', 'locus', 'reference_seq', 'variants')
    def __init__(self, version, path, step):
        self.version = version
        self.path = path
        self.step = step
        self.variants = {} #keyed by md5sum, [var_val, pop_size]
    def initialize_library(self, tile_variant_int, md5sum, population_size, num_hex_digits_for_version, num_hex_digits_for_path, num_hex_digits_for_step, num_hex_digits_for_variant_value):
        version, path, step, variant_value = basic_fns.get_tile_variant_strings_from_tile_variant_int(
            tile_variant_int,
            num_hex_digits_for_version,
            num_hex_digits_for_path,
            num_hex_digits_for_step,
            num_hex_digits_for_variant_value
        )
        assert version == self.version
        assert path == self.path
        assert step == self.step
        assert md5sum not in self.variants
        self.variants[md5sum] = [int(variant_value,16), population_size]
    def check_correct_initialization(self):
        reverse_variants = {}
        for md5sum in self.variants:
            variant_value, population_size = self.variants[md5sum]
            assert population_size >= 0
            assert variant_value not in reverse_variants
            reverse_variants[variant_value] = md5sum
    def get_size(self):
        return len(self.variants)
    def extend_library(self, tile_object, population_incr=1):
        assert tile_object.version == self.version
        assert tile_object.path == self.path
        assert tile_object.step == self.step, "step %s is not step %s" % (tile_object.step, self.step)
        if tile_object.md5sum not in self.variants:
            self.variants[tile_object.md5sum] = [len(self.variants), population_incr]
            return False, len(self.variants)
        else:
            self.variants[tile_object.md5sum][1] += population_incr
            return True, self.variants[tile_object.md5sum][0]
    def write_tile_library(self, num_hex_digits_for_variant_value, out):
        reverse_variants = {}
        for md5sum in self.variants:
            variant_value, population_size = self.variants[md5sum]
            assert variant_value not in reverse_variants
            reverse_variants[variant_value] = (md5sum, population_size)
        for variant_value in sorted(reverse_variants.keys()):
            md5sum, population_size = reverse_variants[variant_value]
            assert population_size >= 0
            hex_variant_value = hex(variant_value).lstrip('0x').zfill(num_hex_digits_for_variant_value)
            tile_variant_int = int(self.version+self.path+self.step+hex_variant_value, 16)
            tile_position_int = int(self.version+self.path+self.step, 16)
            tile_var_period_sep = string.join([self.version, self.path, self.step, hex_variant_value], sep='.')
            write_line([tile_var_period_sep, tile_variant_int, tile_position_int, population_size, md5sum], out)
