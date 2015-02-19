"""
Tile Library Models

Does not include information about the population - Use Lantern for that
Population data includes:
    number of people with particular variant
    color mapping for slippy map
"""

import string
import json
import warnings

from django.db import models
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError

import tile_library.basic_functions as basic_fns
import tile_library_generation.validators as validation_fns
import tile_library.human_readable_functions as human_readable_fns
from errors import TileLibraryValidationError
from tile_library.constants import TAG_LENGTH, SUPPORTED_ASSEMBLY_CHOICES, CHR_CHOICES, STATISTICS_TYPE_CHOICES

def validate_json(text):
    try:
        json.loads(text)
    except ValueError:
        raise ValidationError("Expects json-formatted text")
def validate_gte_neg_one(integer):
    if integer < -1:
        raise ValidationError("integer must be greater than or equal to negative one")
def validate_positive(integer):
    if integer < 0:
        raise ValidationError("integer must be positive")
def validate_tile_position_int(tile_position_int):
    validate_positive(tile_position_int)
    max_tile_position = int('fffffffff', 16)
    if tile_position_int > max_tile_position:
        raise ValidationError("tile position int must be smaller than or equal to 'fff.ff.ffff'")
def validate_tile_variant_int(tile_variant_int):
    validate_positive(tile_variant_int)
    max_tile_variant = int('ffffffffffff', 16)
    if tile_variant_int > max_tile_variant:
        raise ValidationError("tile variant int must be smaller than or equal to 'fff.ff.ffff.fff'")
def validate_tag(tag):
    if len(tag) != TAG_LENGTH:
        raise ValidationError("Tag length must be equal to the set TAG_LENGTH")
def validate_variant_tag(tag):
    if len(tag) != TAG_LENGTH and len(tag) != 0:
        raise ValidationError("Tag length must be equal to the set TAG_LENGTH or must be empty")
def validate_num_spanning_tiles(num_spanning):
    if num_spanning < 1:
        raise ValidationError("num positions spanned must be greater than or equal to 1")
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
            First 3 digits of the hexidecimal identifier indicate the path
            Next 2 digits indicate the path version
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
        try:
            self.full_clean()
            validation_fns.validate_tile(self.tile_position_int)
            super(Tile, self).save(*args, **kwargs)
        except TileLibraryValidationError as e:
            raise ValidationError("Unable to save TileVariant as it conflicts with validation expectations: " + str(e))
    def get_string(self):
        """Displays hex indexing for tile """
        return basic_fns.get_position_string_from_position_int(int(self.tile_position_int))
    get_string.short_description='Tile Name'
    def __unicode__(self):
        return self.get_string()
    class Meta:
        #Ensures ordering by tilename
        ordering = ['tile_position_int']

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
            start_tag = self.start_tag
            if start_tag == '':
                start_tag = self.tile.start_tag
            end_tag = self.end_tag
            if end_tag == '':
                end_tag = self.tile.end_tag
            validation_fns.validate_tile_variant(
                TAG_LENGTH, self.tile_id, self.tile_variant_int, self.variant_value, self.sequence, self.length, self.md5sum, start_tag, end_tag
            )
            super(TileVariant, self).save(*args, **kwargs)
        except TileLibraryValidationError as e:
            raise ValidationError("Unable to save TileVariant as it conflicts with validation expectations: " + str(e))
    def get_string(self):
        """Displays hex indexing for tile variant"""
        return basic_fns.get_tile_variant_string_from_tile_variant_int(int(self.tile_variant_int))
    get_string.short_description='Variant Name'
    def is_reference(self, assembly_int):
        return int(self.variant_value) == TileLocusAnnotations.objects.filter(tile_id=self.tile_id).get(assembly=assembly_int).variant_value
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
            str(upper_position_int) + ", length of sequence is " + str(self.length) + ", name: " + self.getString()
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
                             blank=True)
    info = models.TextField(
        help_text="Json-formatted. Known keys are 'source': [what generated the variant],\
                   'phenotype': [phenotypes associated with this annotation], 'amino_acid': [predicted amino-acid changes],\
                   'ucsc_trans': [UCSC translation (picked up from GFF files), and 'other': [Other GFF-file related annotations]",
        validators=[validate_json], db_index=True
        )
    created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    def save(self, *args, **kwargs):
        self.full_clean()
        super(GenomeVariant, self).save(*args, **kwargs)
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
        return human_readable_fns.get_readable_chr_name(self.chromosome, self.alternate_chromosome_name)
    class Meta:
        #Ensures ordering by tilename
        ordering = ['chromosome', 'alternate_chromosome_name', 'locus_start_int']
        unique_together = ('assembly', 'chromosome', 'alternate_chromosome_name', 'locus_start_int', 'alternate_bases')

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
    tile_variant = models.ForeignKey(TileVariant, related_name='translation_to_genome_variant')
    genome_variant = models.ForeignKey(GenomeVariant, related_name='translation_to_tile_variant')
    start = models.PositiveIntegerField(help_text="Positive integer, zero-indexed, relative to start of that tilevariant")
    end = models.PositiveIntegerField(help_text="Positive integer, zero-indexed, relative to start of that tilevariant. Exclusive")
    def save(self, *args, **kwargs):
        self.full_clean()
        super(GenomeVariantTranslation, self).save(*args, **kwargs)
    def __unicode__(self):
        return "Tile Variant %s to Genome Variant %s (id: %i)" % (self.tile_variant.__unicode__(), self.genome_variant.__unicode__(), self.genome_variant.id)
    class Meta:
        unique_together = ("tile_variant", "genome_variant")

class TileLocusAnnotation(models.Model):
    """
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

        tile(foreignkey): the Tile associated with this locus annotation
            tile_locus_annotations: the related name for these annotations
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
            tile_var_int = basic_fns.convert_position_int_to_tile_variant_int(int(self.tile.tile_position_int), variant_value=self.tile_variant_value)
            length = TileVariant.objects.get(tile_variant_name=tile_var_int).length
            validation_fns.validate_locus(TAG_LENGTH, length, self.begin_int, self.end_int)
        except TileVariant.DoesNotExist:
            raise ValidationError({'tile':'tile does not have a tilevariant (with a variant value of 0) associated with it'})
        except TileLibraryValidationError as e:
            raise ValidationError("Unable to save TileVariant as it conflicts with validation expectations: " + str(e))
        super(TileLocusAnnotation, self).save(*args, **kwargs)
    def get_readable_chr_name(self):
        if self.chromosome == 26:
            return self.chromosome_name
        else:
            chrom_index = [i for i,j in self.CHR_CHOICES]
            return self.CHR_CHOICES[chrom_index.index(self.chromosome)][1]
    def __unicode__(self):
        assembly_index = [i for i,j in self.SUPPORTED_ASSEMBLY_CHOICES]
        humanReadable = self.SUPPORTED_ASSEMBLY_CHOICES[assembly_index.index(self.assembly)][1]
        return self.tile.getTileString() + ": " + humanReadable + " Translation"
    class Meta:
        #Ensures ordering by tilename
        ordering = ['tile']
        unique_together = ("tile", "assembly")

class GenomeStatistic(models.Model):
    """
    postgres provides good querying capability, but scientists also want statistics...
    """

    statistics_type = models.PositiveSmallIntegerField(db_index=True, choices=NAME_CHOICES)
    path_name = models.IntegerField(db_index=True, default=-1, validators=[validate_gte_neg_one])
    num_of_positions = models.BigIntegerField(validators=[validate_positive])
    num_of_tiles = models.BigIntegerField(validators=[validate_positive])
    max_num_positions_spanned = models.PositiveIntegerField(blank=True, null=True, validators=[validate_num_spanning_tiles])
    def save(self, *args, **kwargs):
        self.full_clean()
        if self.num_of_positions == 0 and self.num_of_tiles > 0:
            raise ValidationError({'num_of_positions-num_of_tiles': "No tiles can exist if no positions exist"})
        if self.num_of_positions  > self.num_of_tiles:
            raise ValidationError({'num_of_positions-num_of_tiles': "Number of tiles must be larger than or equal to the number of positions"})
        if self.path_name == -1 and self.statistics_type == 27:
            raise ValidationError({'path_name_too_low': 'If statistics type is equal to 27, path name must be greater than -1'})
        super(GenomeStatistic, self).save(*args, **kwargs)
    def __unicode__(self):
        if self.statistics_type < 27:
            name_index = [i for i,j in self.NAME_CHOICES]
            humanReadable = self.NAME_CHOICES[name_index.index(self.statistics_type)][1]
            return humanReadable + " Statistics"
        else:
            return "Path " + str(self.path_name) + " Statistics"
    class Meta:
        unique_together = ("statistics_type", "path_name")
