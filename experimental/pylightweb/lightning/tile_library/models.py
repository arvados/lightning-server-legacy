"""
Tile Library Models

Does not include information about the population - Use Lantern for that case

"""

import string

from django.db import models
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError

import tile_library.basic_functions as basic_fns
import tile_library_generation.validators as validation_fns
import tile_library.human_readable_functions as human_readable_fns
from errors import TileLibraryValidationError, MissingLocusError
from tile_library.constants import TAG_LENGTH, SUPPORTED_ASSEMBLY_CHOICES, \
    CHR_CHOICES, STATISTICS_TYPE_CHOICES, PATH, CHR_PATH_LENGTHS

def validate_json(text):
    try:
        validation_fns.validate_json(text)
    except TileLibraryValidationError as e:
        raise ValidationError(e.value)
def validate_positive(integer):
    if integer < 0:
        raise ValidationError("Expects integer to be positive")
def validate_tile_position_int(tile_position_int):
    try:
        validation_fns.validate_tile_position_int(tile_position_int)
    except TileLibraryValidationError as e:
        raise ValidationError(e.value['tile_position_int'])
def validate_tile_variant_int(tile_variant_int):
    try:
        validation_fns.validate_tile_variant_int(tile_variant_int)
    except TileLibraryValidationError as e:
        raise ValidationError(e.value['tile_variant_int'])
def validate_tag(tag):
    try:
        validation_fns.validate_tag(tag)
    except TileLibraryValidationError as e:
        raise ValidationError(e.value)
def validate_variant_tag(tag):
    try:
        validation_fns.validate_variant_tag(tag)
    except TileLibraryValidationError as e:
        raise ValidationError(e.value)
def validate_num_spanning_tiles(num_spanning):
    try:
        validation_fns.validate_num_spanning_tiles(num_spanning)
    except TileLibraryValidationError as e:
        raise ValidationError(e.value)
class Tile(models.Model):
    """
    Implements a Tile object - the meta-data associated with a tile position.
        Includes the tile position, the start-tag, end-tag, and when it was generated
        This representation of a tile library guarantees that every tile instance will
            have a path, path version, and step
        Theoretically, this will never be regenerated or modified. Modifications would
            result in a new path version and therefore a new Tile. All modifications happen
            to TileVariant's associated with a Tile.

    Values in database:
        tile_position_int (bigint, primary key): _integer_ of the 9 digit hexidecimal identifier for the tile position
            First 2 digits indicate the path version
            Next 3 digits of the hexidecimal identifier indicate the path
            Next 4 digits indicate the step
        start_tag(charfield(24)): start Tag
        end_tag(charfield(24)): end Tag
        created(datetimefield): The day the tile was generated

    Functions:
        get_string(): returns string: human readable tile position

    """
    tile_position_int = models.BigIntegerField(primary_key=True, editable=False, db_index=True, validators=[validate_tile_position_int])
    start_tag = models.CharField(max_length=TAG_LENGTH, validators=[validate_tag])
    end_tag = models.CharField(max_length=TAG_LENGTH, validators=[validate_tag])
    created = models.DateTimeField(auto_now_add=True)
    def save(self, *args, **kwargs):
        self.full_clean()
        super(Tile, self).save(*args, **kwargs)
    def get_string(self):
        """Displays hex indexing for tile """
        return basic_fns.get_position_string_from_position_int(int(self.tile_position_int))
    get_string.short_description='Tile Name'
    def __unicode__(self):
        return self.get_string()
    class Meta:
        #Ensures ordering by tilename
        ordering = ['tile_position_int']
class TileLocusAnnotation(models.Model):
    """
        Warning on checking: though it checks if the length of the reference sequence is correct, it
            does not know what the sequence should be. That is left to the person populating the database

        Implements translations between assemblies and tile id.
        From looking at UCSC Genome Browser definitions of chromosome bands, we deduce these are currently:
            0-indexed.
            [begin_int, end_int) (exclusive end int)

        Example input from FASTJ:
            Tile x  : {"build":"hg19 chr9 135900000-24 135900225"} => begin_int: 135900000; end_int: 135900225
            Tile x+1: {"build":"hg19 chr9 135900201 135900450"} => begin_int: 135900201; end_int: 135900450

        Values in database:
            assembly_int (positive small integer): the integer mapping to the name of the assembly;
                Choices given by SUPPORTED_ASSEMBLY_CHOICES (defined in tile_library.constants.py)
            chromosome_int (positive small integer): the integer mapping to the chromosome the tile is on;
                Choices given by CHR_CHOICES (defined in tile_library.constants.py)
            alternate_chromosome_name(charfield(100)): the name of the chromosome if chromosome=26 (OTHER)
            start_int(positive int): the 0 indexed start locus
            end_int(positive int): the 0 indexed end locus (exclusive)

            tile_position(foreignkey): the Tile associated with this locus annotation
                tile_locus_annotations: the related name for these annotations
            tile_variant_value(positive int): the variant value of the tile variant containing the
                reference sequence
    """
    assembly_int = models.PositiveSmallIntegerField(choices=SUPPORTED_ASSEMBLY_CHOICES, db_index=True)
    chromosome_int = models.PositiveSmallIntegerField(choices=CHR_CHOICES, db_index=True)
    alternate_chromosome_name = models.CharField(max_length=100, blank=True)
    start_int = models.PositiveIntegerField(db_index=True)
    end_int = models.PositiveIntegerField(db_index=True)
    tile_position = models.ForeignKey(Tile, related_name="tile_locus_annotations", db_index=True)
    tile_variant_value = models.PositiveIntegerField()
    def save(self, *args, **kwargs):
        self.full_clean()
        try:
            tile_var_int = basic_fns.convert_position_int_to_tile_variant_int(int(self.tile_position_id), variant_value=int(self.tile_variant_value))
            length = int(TileVariant.objects.get(tile_variant_int=tile_var_int).length)
            validation_fns.validate_locus(int(self.chromosome_int), int(self.tile_position_id), TAG_LENGTH, length, int(self.start_int), int(self.end_int))
        except TileVariant.DoesNotExist:
            raise ValidationError({'tile_variant_value':'tile does not have a tilevariant (with a variant value of %i) associated with it' % (self.tile_variant_value)})
        except TileLibraryValidationError as e:
            raise ValidationError(e.value)
        super(TileLocusAnnotation, self).save(*args, **kwargs)
    def get_reference_sequence(self):
        return TileVariant.objects.filter(tile_id=self.tile_position).get(variant_value=self.tile_variant_value).sequence
    def get_readable_chr_name(self):
        return human_readable_fns.get_readable_chr_name(self.chromosome_int, self.alternate_chromosome_name)
    def __unicode__(self):
        assembly = human_readable_fns.get_readable_assembly_name(self.assembly_int)
        return "%s: %s Translation" % (self.tile_position.get_string(), assembly)
    class Meta:
        #Ensures ordering by tilename
        ordering = ['tile_position']
        unique_together = ("tile_position", "assembly_int")
class TileVariant(models.Model):
    """
    Implements a TileVariant. Each Tile can have many TileVariants (one-to-many relation).

    Values in database:
        tile_variant_int (bigint; primary key): integer of the 12 digit hexidecimal identifier for the TileVariant.
            The first 9 digits are the same as the hexidecimal identifier of the parent Tile
            xxx.xx.xxxx.xxx. Last three digits indicate the TileVariant value.
        tile (bigint; foreignkey): The parent Tile
        num_positions_spanned (smallint; positive): The number of positions spanned by this TileVariant
        variant_value (int; positive): The variant value (int(last 3 digits of tile_variant_int in hex form))
        length (int; positive): Length of the TileVariant in bases
        md5sum (charfield(40)): The m5sum of the TileVariant sequence (including upper and lowercases)
        created(datetimefield): The time the TileVariant was created
        last_modified(datetimefield): The last time the TileVariant was modified
        sequence (textfield): The sequence of the TileVariant
        start_tag (textfield): the start tag of the TileVariant iff the start tag varies from tile.start_tag
        end_tag (textfield): the end tag of the TileVariant iff the end tag varies from tile.end_tag

    Functions:
        get_string(): returns string: human readable tile variant name
        is_reference(assembly_int): returns boolean: True if the variant is the reference variant for that assembly.
            Depends on variant_value
    """
    tile_variant_int = models.BigIntegerField(primary_key=True, editable=False, db_index=True, validators=[validate_tile_variant_int])
    tile = models.ForeignKey(Tile, related_name='tile_variants', db_index=True)
    num_positions_spanned = models.PositiveSmallIntegerField(validators=[validate_num_spanning_tiles])
    variant_value = models.PositiveIntegerField(db_index=True)
    length = models.PositiveIntegerField(db_index=True)
    md5sum = models.CharField(max_length=40)
    created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    sequence = models.TextField()
    start_tag = models.CharField(default='', blank=True, max_length=TAG_LENGTH, validators=[validate_variant_tag])
    end_tag = models.CharField(default='', blank=True, max_length=TAG_LENGTH, validators=[validate_variant_tag])
    def save(self, *args, **kwargs):
        try:
            self.full_clean()
            end_tile = None
            if self.num_positions_spanned > 1:
                end_tile = Tile.objects.get(tile_position_int=self.tile_id+self.num_positions_spanned-1)
                #Tiles need to be on same path and version (this also ensures they are on the same chromosome from TileLocusAnnotation checking)
                validation_fns.validate_spanning_tile(int(self.tile.tile_position_int), int(end_tile.tile_position_int), int(self.num_positions_spanned))
            start_tag = self.start_tag
            if start_tag == '':
                start_tag = self.tile.start_tag
            end_tag = self.end_tag
            if end_tag == '':
                end_tag = self.tile.end_tag
                if end_tile != None:
                    end_tag = end_tile.end_tag
            validation_fns.validate_tile_variant(
                int(self.tile_id), int(self.tile_variant_int), int(self.variant_value), self.sequence, int(self.length), self.md5sum, start_tag, end_tag
            )
            super(TileVariant, self).save(*args, **kwargs)
        except TileLibraryValidationError as e:
            raise ValidationError(e.value)
        except Tile.DoesNotExist as e:
            raise ValidationError({'spanning_tile_error_missing_tile': 'tile with pk=%i does not exist' % (self.tile_id+self.num_positions_spanned-1)})
    def get_string(self):
        """Displays hex indexing for tile variant"""
        return basic_fns.get_tile_variant_string_from_tile_variant_int(int(self.tile_variant_int))
    get_string.short_description='Variant Name'
    def is_reference(self, assembly_int):
        if type(assembly_int) != int:
            raise ValueError("assembly_int must be of type int")
        if assembly_int not in [i for i,j in SUPPORTED_ASSEMBLY_CHOICES]:
            raise ValueError("%i not a supported assembly choice" % (assembly_int))
        try:
            return int(self.variant_value) == TileLocusAnnotation.objects.filter(tile_position_id=self.tile_id).get(assembly_int=assembly_int).tile_variant_value
        except TileLocusAnnotation.DoesNotExist:
            raise MissingLocusError("A locus for assembly %i not found for tile %s" % (assembly_int, str(self.tile)))
    def get_locus(self, assembly_int):
        if type(assembly_int) != int:
            raise ValueError("assembly_int must be of type int")
        if assembly_int not in [i for i,j in SUPPORTED_ASSEMBLY_CHOICES]:
            raise ValueError("%i not a supported assembly choice" % (assembly_int))
        try:
            start_tile = self.tile_id
            end_tile = self.tile_id+self.num_positions_spanned-1
            start_locus = TileLocusAnnotation.objects.filter(tile_position_id=start_tile).get(assembly_int=assembly_int)
            if start_tile == end_tile:
                return start_locus.start_int, start_locus.end_int
            end_locus = TileLocusAnnotation.objects.filter(tile_position_id=end_tile).get(assembly_int=assembly_int)
            return start_locus.start_int, end_locus.end_int
        except TileLocusAnnotation.DoesNotExist:
            start_str = basic_fns.get_position_string_from_position_int(start_tile)
            end_str = basic_fns.get_position_string_from_position_int(end_tile)
            raise MissingLocusError("A locus for assembly %i not found for tiles %s-%s" % (assembly_int, start_str, end_str))
    def get_base_at_position(self, position_int):
        position_int = int(position_int) # can raise value error: will be caught downstream
        if position_int >= self.length:
            raise ValueError("Expects the position integer (%i) to be 0-indexed and less than the length of the sequence (%i)" % (position_int, self.length))
        if position_int < 0:
            raise ValueError("Expects the position integer (%i) to be positive" % (position_int))
        return self.sequence[position_int]
    def get_base_group_between_positions(self, lower_position_int, upper_position_int):
        lower_position_int = int(lower_position_int) #ValueError is expected to be caught downstream
        upper_position_int = int(upper_position_int) #ValueError is expected to be caught downstream
        #create string of useful info for debugging
        info_str = "Lower position int is: " + str(lower_position_int) + ", upper position int (exclusive and 0-indexed) is: " + \
            str(upper_position_int) + ", length of sequence is " + str(self.length) + ", name: " + self.get_string()
        if lower_position_int > self.length:
            raise ValueError("Expects the lower position integer to be 0-indexed and not greater than the length of the sequence. " + info_str)
        if upper_position_int > self.length:
            raise ValueError("Expects the upper position integer to be 0-indexed and not greater than the length of the sequence. " + info_str)
        if lower_position_int < 0:
            raise ValueError("Expects the lower position integer to be positive. " + info_str)
        if upper_position_int < 0:
            raise ValueError("Expects the upper position integer to be positive. " + info_str)
        if lower_position_int > upper_position_int:
            raise ValueError("Expects lower position_int to be less than or equal to upper position int. " + info_str)
        return self.sequence[lower_position_int:upper_position_int]
    def __unicode__(self):
        return self.get_string()
    class Meta:
        #Ensures ordering by tilename
        ordering = ['tile_variant_int']
class GenomeVariant(models.Model):
    """
        Implements a Genome Variant object (SNP, SUB, or INDEL) that can be associated with multiple TileVariants.
        Many-to-Many relation with TileVariant.
        Designed to preserve variants called from a particular variant caller, run on data before loaded into lightning
        Eventually expected to fade out of use, to be replaced by annotations on TileVariant directly

        Values in database:
            id (big integer field): the id of the GenomeVariant. For indexing, when converted into hex,
                the first 3 integers are the path the genomevariant is on

            assembly_int(positive small integer): the integer mapping to the name of the assembly used to generate variant annotation;
                Choices given by SUPPORTED_ASSEMBLY_CHOICES (defined in tile_library.constants.py)
            chromosome_int(positive small integer): the integer mapping to the chromosome the the variant is on
                Choices given by CHR_CHOICES (defined in tile_library.constants.py)
            alternate_chromosome_name(charfield(100)): the name of the chromosome if chromosome=(CHR_OTHER)
            locus_start_int(positive int): the 0 indexed locus where the genome variant starts
            locus_end_int(positive int): the 0 indexed locus where the genome variant ends (exclusive)

            tile_variants (many-to-many-field): the TileVariants containing this GenomeVariant
            reference_bases (textfield): Text of reference bases, follows this regex pattern: [ACGT-]+
            alternate_bases (textfield): Text of variant bases, follows this regex pattern: [ACGT-]+
            names (textfield): Tab-separated names for this variant
            info (textfield): Json-formatted. Includes {'source': [what generated the variant],
                                                        'phenotype': [phenotypes associated with this annotation]}
            created(datetimefield): time when the variant was created
            last_modified(datetimefield): time when the variant was last modified

        These values relate to GAVariant by:
            GAVariant.id -> GenomeVariant.id
            GAVariant.variantSetId -> A table id
            GAVariant.names -> GenomeVariant.names
            GAVariant.created -> GenomeVariant.created
            GAVariant.updated -> GenomeVariant.last_modified
            GAVariant.referenceName -> GenomeVariant.get_readable_chr_name()
            GAVariant.start -> GenomeVariant.locus_start_int
            GAVariant.end -> GenomeVariant.locus_end_int
            GAVariant.referenceBases -> GenomeVariant.reference_bases or empty string if '-'
            GAVariant.alternateBases -> GenomeVariant.alternate_bases or empty string if '-'
            GAVariant.info -> GenomeVariant.info
            GAVariant.calls -> A list of the samples containing TileVariants in tile_variants
    """
    id = models.BigIntegerField(primary_key=True, editable=False)
    assembly_int = models.PositiveSmallIntegerField(choices=SUPPORTED_ASSEMBLY_CHOICES, db_index=True)
    chromosome_int = models.PositiveSmallIntegerField(choices=CHR_CHOICES, db_index=True)
    alternate_chromosome_name = models.CharField(max_length=100, blank=True)
    locus_start_int = models.PositiveIntegerField(db_index=True)
    locus_end_int = models.PositiveIntegerField(db_index=True)
    tile_variants = models.ManyToManyField(TileVariant, through='GenomeVariantTranslation',
                                           through_fields=('genome_variant', 'tile_variant'),
                                           related_name='genome_variants', db_index=True)
    reference_bases = models.TextField(
        help_text="Text of variant bases, follows the regex pattern: [ACGT-]+\n'-' indicates an insertion",
        validators=[RegexValidator(regex='[ACGT-]+', message="Not a valid sequence")],
        )
    alternate_bases = models.TextField(
        help_text="Text of variant bases, follows the regex pattern: [ACGT-]+\n'-' indicates a deletion",
        validators=[RegexValidator(regex='[ACGT-]+', message="Not a valid sequence")],
        )
    names = models.TextField(help_text="Tab-separated aliases for this variant (rsID tags, RefSNP id, etc.",
                             blank=True, db_index=True)
    info = models.TextField(
        help_text="Json-formatted. Known keys are 'source': [what generated the variant],\
                   'phenotype': [phenotypes associated with this annotation], 'amino_acid': [predicted amino-acid changes],\
                   'ucsc_trans': [UCSC translation (picked up from GFF files), and 'other': [Other GFF-file related annotations]",
        validators=[validate_json], db_index=True, blank=True
        )
    created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    def save(self, *args, **kwargs):
        self.full_clean()
        assembly = int(self.assembly_int)
        chrom = int(self.chromosome_int)
        start = int(self.locus_start_int)
        end = int(self.locus_end_int)
        if end < start:
            raise ValidationError(
                {'locus_start_int-locus_end_int':'locus_end_int (%i) is smaller than locus_start_int (%i)' % (end, start)}
            )
        loci = TileLocusAnnotation.objects.filter(assembly_int=assembly).filter(chromosome_int=chrom).filter(start_int__lt=end).filter(end_int__gt=start).order_by('start_int')
        if loci.count() == 0:
            raise ValidationError(
                {'missing_locus':'Unable to find any loci in assembly %i, chromosome %i, with a begin_int less than %i and an end in greater than %i' % (assembly, chrom, end, start)}
            )
        reference_seq = ''
        zero = 0
        for locus in loci:
            reference_tile_variant_sequence = locus.get_reference_sequence()
            if reference_seq == '':
                zero = locus.start_int
                reference_seq += reference_tile_variant_sequence
            else:
                assert reference_seq[-TAG_LENGTH:].upper() == reference_tile_variant_sequence[:TAG_LENGTH].upper(), \
                    "Tags mismatching at locus %s: %s not %s" % (loci, reference_seq, reference_tile_variant_sequence)
                reference_seq += reference_tile_variant_sequence[TAG_LENGTH:]
        try:
            validation_fns.validate_reference_bases(reference_seq, start-zero, end-zero, self.reference_bases)
            super(GenomeVariant, self).save(*args, **kwargs)
        except TileLibraryValidationError as e:
            raise ValidationError(e.value)
    def __unicode__(self):
        return "Assembly %s, Chromosome %s, [%i, %i), %s => %s" % (
            human_readable_fns.get_readable_assembly_name(self.assembly_int),
            human_readable_fns.get_readable_chr_name(self.chromosome_int, self.alternate_chromosome_name),
            self.locus_start_int,
            self.locus_end_int,
            self.reference_bases,
            self.alternate_bases
        )
    def get_readable_chr_name(self):
        return human_readable_fns.get_readable_chr_name(self.chromosome_int, self.alternate_chromosome_name)
    class Meta:
        #Ensures ordering by tilename
        ordering = ['chromosome_int', 'alternate_chromosome_name', 'locus_start_int']
        unique_together = ('assembly_int', 'chromosome_int', 'alternate_chromosome_name', 'locus_start_int', 'alternate_bases')

class GenomeVariantTranslation(models.Model):
    """
        Implements the Many-to-Many relation between GenomeVariant and TileVariant as well the translation between them
        As with GenomeVariant, expected to fade out as annotations on TileVariants become more popular

        Values in database:
            tile_variant (foreignkey): the id of the TileVariant
            genome_variant(foreignkey): the id of the GenomeVariant
            start (integer): Positive integer, zero-indexed, relative to start of the TileVariant
            end (integer): Positive integer, zero-indexed, exclusive, relative to the start of the TileVariant
    """
    tile_variant = models.ForeignKey(TileVariant, related_name='translations_to_genome_variant')
    genome_variant = models.ForeignKey(GenomeVariant, related_name='translations_to_tile_variant')
    start = models.PositiveIntegerField(help_text="Positive integer, zero-indexed, relative to start of that tilevariant")
    end = models.PositiveIntegerField(help_text="Positive integer, zero-indexed, relative to start of that tilevariant. Exclusive")
    def save(self, *args, **kwargs):
        self.full_clean()
        try:
            gv = self.genome_variant
            tv = self.tile_variant
            start_int, end_int = tv.get_locus(gv.assembly_int)
            for tile_position in range(int(tv.tile_id), int(tv.tile_id) + int(tv.num_positions_spanned)):
                locus = TileLocusAnnotation.objects.filter(tile_position=tile_position).get(assembly_int=gv.assembly_int)
                validation_fns.validate_same_chromosome(locus.chromosome_int, gv.chromosome_int, locus.alternate_chromosome_name, gv.alternate_chromosome_name)
            validation_fns.validate_tile_variant_loci_encompass_genome_variant_loci(gv.locus_start_int, gv.locus_end_int, start_int, end_int)
            validation_fns.validate_alternate_bases(tv.sequence, gv.alternate_bases, self.start, self.end)
            super(GenomeVariantTranslation, self).save(*args, **kwargs)
        except TileLibraryValidationError as e:
            raise ValidationError(e.value)
        except MissingLocusError as e:
            raise ValidationError({'assembly_int.get_locus_error':str(e)})
        except TileLocusAnnotation.DoesNotExist:
            raise ValidationError({'assembly_int':'Locus for assembly %i not found for tile variant' % (self.genome_variant.assembly_int)})
    def __unicode__(self):
        return "Tile Variant %s to Genome Variant %s (id: %i)" % (self.tile_variant.__unicode__(), self.genome_variant.__unicode__(), self.genome_variant.id)
    class Meta:
        unique_together = ("tile_variant", "genome_variant")

class GenomeStatistic(models.Model):
    """
        Provides some basic statistics capabilites and a running counter of the maximum
        number of positions spanned in each path
    """
    statistics_type = models.PositiveSmallIntegerField(db_index=True, choices=STATISTICS_TYPE_CHOICES)
    path_name = models.IntegerField(db_index=True, default=-1)
    num_of_positions = models.BigIntegerField(validators=[validate_positive])
    num_of_tiles = models.BigIntegerField(validators=[validate_positive])
    max_num_positions_spanned = models.PositiveIntegerField(blank=True, null=True, validators=[validate_num_spanning_tiles])
    def save(self, *args, **kwargs):
        self.full_clean()
        if self.num_of_positions == 0 and self.num_of_tiles > 0:
            raise ValidationError({'num_of_positions-num_of_tiles': "No tiles can exist if no positions exist"})
        if self.num_of_positions  > self.num_of_tiles:
            raise ValidationError({'num_of_positions-num_of_tiles': "Number of tiles must be larger than or equal to the number of positions"})
        if self.statistics_type == PATH:
            if self.path_name < 0:
                raise ValidationError({'path_name': 'If statistics type is equal to %i, path name must be greater than -1' % (PATH)})
            if self.path_name >= CHR_PATH_LENGTHS[-1]:
                raise ValidationError({'path_name': 'Path name must be less than %i' % (CHR_PATH_LENGTHS[-1])})
        if self.path_name != -1 and self.statistics_type != PATH:
            raise ValidationError({'path_name': 'If statistics type is not equal to %i, path name must be exactly -1' % (PATH)})
        super(GenomeStatistic, self).save(*args, **kwargs)
    def __unicode__(self):
        return human_readable_fns.get_readable_genome_statistics_name(self.statistic_type, path=self.path_name) + "Statistics"
    class Meta:
        unique_together = ("statistics_type", "path_name")
