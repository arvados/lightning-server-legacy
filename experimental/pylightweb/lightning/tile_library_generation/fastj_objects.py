from tile_library.models import TAG_LENGTH

class TileObject(object):
    __slots__ = [
        'position_int', 'tile_variant_int',
        'start_tag', 'end_tag', 'start_seq', 'end_seq', 'sequence', 'reference_sequence', 'md5sum', 'assembly', 'chromosome',
        'chrom_name', 'locus_begin', 'locus_end', 'seed_tile_length'
    ]
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
        return self.get_position_hex()[:3]
    def get_position_hex(self):
        return hex(self.position_int).lstrip('0x').zfill(9)

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
    __slots__ = []
    def __init__(self, assembly, chromosome, begin, end, chrom_name=""):
        self.assembly = assembly
        self.chromosome = chromosome
        self.chrom_name = chrom_name
        self.begin = begin
        self.end = end

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
