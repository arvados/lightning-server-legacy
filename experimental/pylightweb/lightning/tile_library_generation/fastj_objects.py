from tile_library.models import TAG_LENGTH
import tile_library.basic_functions as basic_fns

class TileObject(object):
    __slots__ = (
        'position_int', 'tile_variant_int',
        'start_tag', 'end_tag', 'start_seq', 'end_seq', 'sequence', 'reference_sequence', 'md5sum', 'assembly', 'chromosome',
        'chrom_name', 'locus_begin', 'locus_end', 'seed_tile_length'
    )
    def __init__(self, position_int, start_tag, end_tag, length, md5sum):
        self.position_int = position_int
        self.tile_variant_int = None
        self.start_tag = start_tag
        self.end_tag = end_tag
        self.start_seq = ""
        self.end_seq = ""
        self.sequence = ""
        self.reference_sequence = ""
        self.md5sum = md5sum
        self.seed_tile_length = None
        self.locus = LocusObject(None, None, "", None, None)

    def get_path(self):
        path, version, step = basic_fns.convert_position_int_to_position_hex_str(self.position_int)
        return path

    def get_position_hex(self):
        return basic_fns.get_position_string_from_position_int(self.position_int)

    def check_and_write(self, file_handle_to_write):
        #Make sure everything that is waiting for parsing was filled
        for attribute in [self.tile_variant_int, self.seed_tile_length]:
            assert attribute != None
        self.locus.check_self()
        assert self.start_seq != self.start_tag
        assert self.end_seq != self.end_tag

        #Run tile variant validation

    def add_loci(self, locus_object, end_locus_object=None):
        self.locus.check_same_assembly_and_chrom(locus_object)
        self.locus.begin = locus_object.begin
        if end_locus_object != None:
            locus_object.check_same_assembly_and_chrom(end_locus_object)
            self.locus_end = end_locus_object.end
        else:
            self.locus_end = locus_object.end

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
        assert self.begin <= self.end

class TileLibrary(object):
    def __init__(self, path):
        self.path = path
        self.library = {}
    def get_smaller_library(self, tile_position_int):
        path, version, step = basic_fns.convert_position_int_to_position_hex_str(tile_position_int)
        assert path == self.path
        trunc_tile_position = int(version+step, 16)
        if trunc_tile_position in self.library:
            return self.library[trunc_tile_position]
        else:
            self.library[trunc_tile_position] = TileLibraryAtPosition(self.path, trunc_tile_position)
    def check_correct_initialization():
        for trunc_tile_position in sorted(self.library.keys()):
            self.library[trunc_tile_position].check_correct_initialization()
    def write_library(self, out):
        for trunc_tile_position in sorted(self.library.keys()):
            self.library[trunc_tile_position].write_tile_library(out)

class TileLibraryAtPosition(object):
    __slots__ = ('path', 'position', 'locus', 'reference_seq', 'variants', 'unpaired_cgf_strings')
    def __init__(self, path, position):
        self.path = path
        self.position = position
        self.locus = None
        self.reference_seq = None
        self.variants = {} #keyed by md5sum, [var_val, pop_size, cgf_string]
        self.unpaired_cgf_strings = {} #keyed by md5sum, cgf_string

    def initialize_library(self, tile_variant_int, md5sum, population_incr, cgf_string):
        path, version, step, variant_value = basic_fns.convert_tile_variant_int_to_tile_hex_str(tile_variant_int)
        assert path == self.path
        trunc_tile_position = int(version+step, 16)
        assert trunc_tile_position == self.position
        assert md5sum not in self.variants

        cgf_position = basic_fns.get_position_from_cgf_string(cgf_string)
        path, version, step = basic_fns.convert_position_int_to_position_hex_str(cgf_position)
        assert path == self.path
        assert int(version+step,16) == self.position
        self.variants[md5sum] = [int(variant_value,16), population_incr, cgf_string]

    def add_cgf_string(self, cgf_string, md5sum):
        cgf_position = basic_fns.get_position_from_cgf_string(cgf_string)
        path, version, step = basic_fns.convert_position_int_to_position_hex_str(cgf_position)
        assert path == self.path
        assert int(version+step,16) == self.position
        assert md5sum not in self.variants, "Trying to add cgf_string with md5sum that already exists in variants"
        assert md5sum not in self.unpaired_cgf_strings, "Trying to add unmatched cgf string with md5sum that already exists"
        self.unpaired_cgf_strings[md5sum] = cgf_string

    def add_locus(self, locus):
        assert self.locus == None, "Trying to add locus when one already exists"
        locus.check_self()
        self.locus = locus

    def add_reference_sequence(self, sequence, md5sum, tile_variant_int):
        assert self.reference_seq == None, "Trying to add reference sequence when one already exists"
        assert len(sequence) == self.locus.get_length_of_locus(), "Given sequence is shorter than the locus"
        stored_md5sum = None
        for md5sum in self.variants:
            if self.variants[md5sum][0] == 0:
                stored_md5sum = md5sum
        assert stored_md5sum != None, "Missing md5sum"
        assert stored_md5sum == md5sum, "Expects equal md5sums"
        path, version, step, var_value = basic_fns.convert_tile_variant_int_to_tile_hex_str(tile_variant_int)
        assert int(var_value, 16) == 0
        assert path = self.path
        assert int(version+step,16) == self.position
        self.reference_seq = sequence

    def check_correct_initialization():
        reverse_variants = {}
        for md5sum in self.variants:
            variant_value, population_size, cgf_string = self.variants[md5sum]
            assert variant_value not in reverse_variants
            reverse_variants[variant_value] = md5sum
        assert type(self.locus) == LocusObject
        assert type(self.reference_seq) == str

    def extend_library(self, tile_position_int, md5sum, population_incr=1):
        path, version, step = basic_fns.convert_tile_position_int_to_position_hex_str(tile_position_int)
        assert path == self.path
        trunc_tile_position = int(version+step, 16)
        assert trunc_tile_position == self.position
        if md5sum not in self.variants:
            assert md5sum in self.unpaired_cgf_strings, "md5sum does not have cgf_string"
            self.variants[md5sum] = [len(self.variants), population_incr, self.unpaired_cgf_strings[md5sum]]
            del self.unpaired_cgf_strings[md5sum]
            return False, len(self.variants), self.variants[md5sum][2]
        else:
            self.variants[md5sum][1] += population_incr
            return True, self.variants[md5sum][0], self.variants[md5sum][2]

    def write_tile_library(self, out):
        reverse_variants = {}
        for md5sum in self.variants:
            variant_value, population_size, cgf_string = self.variants[md5sum]
            assert variant_value not in reverse_variants
            reverse_variants[variant_value] = (md5sum, population_size, cgf_string)
        for variant_value in sorted(reverse_variants.keys()):
            md5sum, population_size, cgf_string = reverse_variants[variant_value]
            assert population_size >= 0
            trunc_position_hex = hex(self.position).lstrip('0x').zfill(6)
            version = trunc_position_hex[:2]
            step = trunc_position_hex[2:]
            hex_variant_value = hex(variant_value).lstrip('0x').zfill(3)
            tile_variant_int = int(self.path+trunc_position_hex+hex_variant_value, 16)
            tile_position_int = basic_fns.convert_tile_variant_to_position_int(tile_variant_int)
            tile_var_period_sep = basic_fns.get_tile_variant_string_from_tile_variant_int(tile_variant_int)
            out.write(string.join([tile_var_period_sep, str(tile_variant_int), str(tile_position_int), str(population_size), md5sum, cgf_string+'\n'], sep=','))

    def write_unpaired_cgf_strings(self, out):
        for md5sum in self.unpaired_cgf_strings:
            out.write(string.join([md5sum, '-1', self.unpaired_cgf_strings[md5sum]+'\n'], sep=','))

class GenomeVariantLibrary(object):
    def __init__(self, path):
        self.path = path
        self.id_ = None
        self.genome_variants = {}
    def add_known_variant(self, chrom_name, begin_int, end_int, ref_seq, var_seq, id_):
        tuple_to_add = (chrom_name, locus_beg_int, locus_end_int, ref_seq, var_seq)
        assert tuple_to_add not in self.genome_variants
        self.genome_variants[tuple_to_add] = id_
    def check_initialization(self):
        num_genome_variants = len(self.genome_variants)
        seen_ids = []
        for tup in self.genome_variants:
            id_ = self.genome_variants[tup]
            hex_id = hex(id_).lstrip('0x')
            assert hex_id[:3] == self.path
            assert int(hex_id[3:],16) not in seen_ids
            seen_ids.append(id_)
        seen_ids.sort()
        next_id_available = max(seen_ids) + 1
        assert seen_ids == range(0, next_id_available )
        self.id_ = next_id_available
    def write_genome_variant_library(self, out):
        for gv in self.genome_variants:
            chrom_name, locus_beg_int, locus_end_int, ref_seq, var_seq = gv
            id_ = self.genome_variants[gv]
            out.write(string.join([chrom_name, locus_beg_int, locus_end_int, ref_seq, var_seq, id_+'\n'], sep=','))

class GenomeVariantObject(object):
    """Immutable genome object """
    __slots__ = ('_assembly', '_chromosome', '_chrom_name', '_begin', '_end', '_var_seq',)
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
        assert self.begin <= self.end


class GenomeVariantObject(object):
    __slots__ = []
    def __init__(self, genome_variant_locus, start_tile_position, start_int, end_tile_position, end_int):
        self.locus = genome_variant_locus
        self.id_ = None
        self.start_tile_position = start_tile_position
        self.start_int = start_int
        self.end_tile_position = end_tile_position
        self.end_int = end_int
        self.ref_seq = None
        self.var_seq = None
        self.known_aliases = []
        self.info = {}

    def __eq__(self, other):
        return self.__cmp__(other)

    def __cmp__(self, other):
        return all([
            self.start_tile_position==other.start_tile_position,
            self.start_int == other.start_int,
            self.end_tile_position==other.end_tile_position,
            self.end_int == other.end_int,
            self.ref_seq == other.ref_seq,
            self.var_seq == other.var_seq
        ])

    def check(self):
        assert self.ref_seq != None
        assert self.var_seq != None
        assert self.ref_seq != self.var_seq
