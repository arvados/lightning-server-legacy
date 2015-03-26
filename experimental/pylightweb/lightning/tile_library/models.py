"""
Tile Library Models

Does not include information about the population - Use Lantern for that case

TODO: Some type of 'entire-library' validation:
    There exist paths for all paths in CHR_PATH_LENGTHS
    For each path:
        There is exactly one true: 'is_start_of_path'
        There is exactly one true: 'is_end_of_path' and it is at the end of the path (no Tile positions come after it)
        The path starts at tile position 0 and increments by one each time

    For each tile position:
        Each tile variant starts with a variant value of 0 and increments by one

Things that are not checked:
    when adding a reference sequence, it does not check that the sequence matches the correct sequence,
    it just checks lengths
"""

import string

from django.db import models
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.conf import settings

import tile_library.basic_functions as basic_fns
import tile_library_generation.validators as validation_fns
import tile_library.human_readable_functions as human_readable_fns
from errors import TileLibraryValidationError, MissingLocusError

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
def validate_num_spanning_tiles(num_spanning):
    try:
        validation_fns.validate_num_spanning_tiles(num_spanning)
    except TileLibraryValidationError as e:
        raise ValidationError(e.value)
def get_tile_n_positions_forward(curr_tile_int, n):
    version, path, step = basic_fns.get_position_strings_from_position_int(curr_tile_int)
    next_path = hex(int(path,16)+1).lstrip('0x').zfill(settings.NUM_HEX_INDEXES_FOR_PATH)
    next_step = hex(n-1).lstrip('0x').zfill(settings.NUM_HEX_INDEXES_FOR_STEP)
    if n <= 0:
        raise Exception("asked to get current tile") #Not raised in tests, which is expected
    try:
        return Tile.objects.get(tile_position_int=curr_tile_int+n)
    except Tile.DoesNotExist:
        pass
    try:
        return Tile.objects.get(tile_position_int=int(version+next_path+next_step,16))
    except Tile.DoesNotExist:
        raise ValidationError({'spanning_tile_error_missing_tile': 'Unable to find tile %s or %s' % (string.join([version,path,step], sep='.'), string.join([version,next_path,next_step], sep='.'))})

def get_max_num_tiles_spanned_at_position(tile_position_int):
    #Find the maximum number to look back for a given position
    version_int, path_int, step_int = basic_fns.get_position_ints_from_position_int(tile_position_int)
    #raises AssertionError if tile_position_int is not an integer, negative, or an invalid tile position
    try:
        num_tiles_spanned = GenomeStatistic.objects.get(path_name=path_int).max_num_positions_spanned
    except GenomeStatistic.DoesNotExist:
        foo, min_path_tile = basic_fns.get_min_position_and_tile_variant_from_path_int(path_int)
        foo, max_path_tile = basic_fns.get_min_position_and_tile_variant_from_path_int(path_int + 1)
        tilevars = TileVariant.objects.filter(tile_variant_int__range=(min_path_tile, max_path_tile-1))
        num_tiles_spanned = tilevars.aggregate(max_pos_spanned=models.Max('num_positions_spanned'))['max_pos_spanned']
    if num_tiles_spanned == None: #Not raised in tests
        raise EmptyPathError('No tiles are loaded for path containing tile: %s' % (hex(tile_position_int).lstrip('0x').zfill(9)))
    num_tiles_spanned = min(int(num_tiles_spanned)-1, step_int) #Only need to look back as far as there are steps in this path
    return num_tiles_spanned

def get_locus(assembly, tile_position_int):
    qs = TileLocusAnnotation.objects.filter(assembly_int=assembly)
    try:
        return qs.get(tile_position_id=tile_position_int)
    except TileLocusAnnotation.DoesNotExist:
        num_look_back = 1
        max_look_back = get_max_num_tiles_spanned_at_position(tile_position_int)
        while num_look_back <= max_look_back:
            if qs.filter(tile_position_id=tile_position_int-num_look_back).exists():
                locus = qs.get(tile_position_id=tile_position_int-num_look_back)
                if locus.get_tile_variant().num_positions_spanned > num_look_back:
                    return locus
            num_look_back += 1
        raise TileLocusAnnotation.DoesNotExist("TileLocusAnnotation matching query does not exist.")

class Tile(models.Model):
    """
    Implements a Tile object - the meta-data associated with a tile position.
        Includes the tile position, the start-tag, end-tag, and when it was generated
        This representation of a tile library guarantees that every tile instance will
            have a path, path version, and step
        Theoretically, this will never be regenerated or modified. Modifications would
            result in a new path version and therefore a new Tile. All modifications happen
            to TileVariant's associated with a Tile.
        Once a path has been generated, it cannot be edited, since is_start_of_path and is_end_of_path
            are non-editable

    Values in database:
        tile_position_int (bigint, primary key): _integer_ of the 9 digit hexidecimal identifier for the tile position
            First 2 digits indicate the path version
            Next 3 digits of the hexidecimal identifier indicate the path
            Next 4 digits indicate the step
        is_start_of_path (boolean): True if tile is the start of path
        is_end_of_path (boolean): True if tile is at the end of path
        start_tag(charfield(24)): start Tag
        end_tag(charfield(24)): end Tag
        created(datetimefield): The day the tile was generated

    Functions:
        get_string(): returns string: human readable tile position

    """
    tile_position_int = models.BigIntegerField(primary_key=True, editable=False, db_index=True, validators=[validate_tile_position_int])
    is_start_of_path = models.BooleanField(default=False, editable=False)
    is_end_of_path = models.BooleanField(default=False, editable=False)
    start_tag = models.CharField(blank=True, max_length=settings.TAG_LENGTH, validators=[validate_tag])
    end_tag = models.CharField(blank=True, max_length=settings.TAG_LENGTH, validators=[validate_tag])
    created = models.DateTimeField(auto_now_add=True)
    def save(self, *args, **kwargs):
        self.full_clean()
        try:
            validation_fns.validate_tile_position(self.tile_position_int, self.is_start_of_path, self.is_end_of_path, self.start_tag, self.end_tag)
        except TileLibraryValidationError as e:
            raise ValidationError(e.value)
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
    assembly_int = models.PositiveSmallIntegerField(choices=settings.SUPPORTED_ASSEMBLY_CHOICES, db_index=True)
    chromosome_int = models.PositiveSmallIntegerField(choices=settings.CHR_CHOICES, db_index=True)
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
            validation_fns.validate_locus(int(self.chromosome_int), int(self.tile_position_id), settings.TAG_LENGTH, length, int(self.start_int), int(self.end_int))
        except TileVariant.DoesNotExist:
            raise ValidationError({'tile_variant_value':'tile does not have a tilevariant (with a variant value of %i) associated with it' % (self.tile_variant_value)})
        except TileLibraryValidationError as e:
            raise ValidationError(e.value)
        super(TileLocusAnnotation, self).save(*args, **kwargs)
    def get_reference_sequence(self):
        return TileVariant.objects.filter(tile_id=self.tile_position).get(variant_value=self.tile_variant_value).sequence
    def get_readable_chr_name(self):
        return human_readable_fns.get_readable_chr_name(self.chromosome_int, self.alternate_chromosome_name)
    def get_tile_variant(self):
        return TileVariant.objects.filter(tile_id=self.tile_position).get(variant_value=self.tile_variant_value)
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
        md5sum (charfield(32)): The m5sum of the TileVariant sequence (including upper and lowercases)
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
    md5sum = models.CharField(max_length=32)
    created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    sequence = models.TextField(blank=True, validators=[
        RegexValidator(
            regex='[acgtn]*',
            message="Not a valid sequence, must be lowercase, and can only include a,c,g,t, or n."
        )
    ])
    start_tag = models.CharField(default='', blank=True, max_length=settings.TAG_LENGTH, validators=[validate_tag])
    end_tag = models.CharField(default='', blank=True, max_length=settings.TAG_LENGTH, validators=[validate_tag])
    def save(self, *args, **kwargs):
        try:
            self.full_clean()
            end_tile = self.tile
            if self.num_positions_spanned > 1:
                end_tile = get_tile_n_positions_forward(int(self.tile_id), int(self.num_positions_spanned)-1)
                #Tiles need to be on same path and version (this also ensures they are on the same chromosome from TileLocusAnnotation checking)
                validation_fns.validate_spanning_tile(int(self.tile.tile_position_int), int(end_tile.tile_position_int), int(self.num_positions_spanned))

            is_start_of_path = self.tile.is_start_of_path
            is_end_of_path = end_tile.is_end_of_path

            start_tag = self.start_tag
            if start_tag == '':
                start_tag = self.tile.start_tag
            end_tag = self.end_tag
            if end_tag == '':
                end_tag = end_tile.end_tag
            validation_fns.validate_tile_variant(
                int(self.tile_id), int(self.tile_variant_int), int(self.variant_value), self.sequence, int(self.length), self.md5sum, start_tag, end_tag, is_start_of_path, is_end_of_path
            )
            super(TileVariant, self).save(*args, **kwargs)
        except TileLibraryValidationError as e:
            raise ValidationError(e.value)
    def get_string(self):
        """Displays hex indexing for tile variant"""
        return basic_fns.get_tile_variant_string_from_tile_variant_int(int(self.tile_variant_int))
    get_string.short_description='Variant Name'
    def is_reference(self, assembly_int):
        if type(assembly_int) != int:
            raise ValueError("assembly_int must be of type int")
        if assembly_int not in [i for i,j in settings.SUPPORTED_ASSEMBLY_CHOICES]:
            raise ValueError("%i not a supported assembly choice" % (assembly_int))
        try:
            return int(self.variant_value) == get_locus(assembly_int, self.tile_id).tile_variant_value
        except TileLocusAnnotation.DoesNotExist:
            raise MissingLocusError("A locus for assembly %i not found for tile %s" % (assembly_int, str(self.tile)))
    def get_locus(self, assembly_int):
        if type(assembly_int) != int:
            raise ValueError("assembly_int must be of type int")
        if assembly_int not in [i for i,j in settings.SUPPORTED_ASSEMBLY_CHOICES]:
            raise ValueError("%i not a supported assembly choice" % (assembly_int))
        start_tile = int(self.tile_id)
        end_tile = int(self.tile_id)+int(self.num_positions_spanned)-1
        try:
            start_locus = get_locus(assembly_int, start_tile)
            if start_tile == end_tile:
                return start_locus.start_int, start_locus.end_int
            end_locus = get_locus(assembly_int, end_tile)
            return start_locus.start_int, end_locus.end_int
        except TileLocusAnnotation.DoesNotExist:
            start_str = basic_fns.get_position_string_from_position_int(start_tile)
            end_str = basic_fns.get_position_string_from_position_int(end_tile)
            raise MissingLocusError("A locus for assembly %i not found for tiles %s-%s" % (assembly_int, start_str, end_str))
    def get_start_and_end_of_path_bools(self):
        end_tile = self.tile
        if self.num_positions_spanned > 1:
            end_tile = get_tile_n_positions_forward(int(self.tile_id), int(self.num_positions_spanned)-1)
        return self.tile.is_start_of_path, end_tile.is_end_of_path
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
    def get_conversion_list_between_genome_variant_loci_and_tile_loci(self, assembly, start_locus_int, end_locus_int):
        #print self.get_string()
        reference_to_tile_variant = [(0, 0, 0, 0), (end_locus_int-start_locus_int, self.length, end_locus_int-start_locus_int, self.length)]
        genome_variant_positions = self.translations_to_genome_variant.filter(genome_variant__assembly_int=assembly).all()
        for translation in genome_variant_positions:
            #print translation
            trans_locus_start = translation.genome_variant.locus_start_int - start_locus_int
            trans_locus_end = translation.genome_variant.locus_end_int - start_locus_int
            # we only need to add if the variant is an INDEL, but I'm adding all of them here since we iterate over all of them anyway
            reference_to_tile_variant.append((trans_locus_start, translation.start, trans_locus_end, translation.end))
        reference_to_tile_variant.sort()
        #print reference_to_tile_variant
        return reference_to_tile_variant
    def get_bases_between_loci_known_locus(self, assembly, queried_low_int, queried_high_int, start_locus_int, end_locus_int):
        def get_start(low_int, reference_to_tile_variant):
            for i, (locus_start, variant_start, locus_end, variant_end) in enumerate(reference_to_tile_variant):
                if low_int <= locus_start:
                    index = max(i-1, 0)
                    prev_locus_start, prev_variant_start, prev_locus_end, prev_variant_end = reference_to_tile_variant[index]
                    break
            assert low_int <= locus_start, "Low int (%i) should never be larger than the highest tuple (%i, %i, %i, %i) in 'reference_to_tile_variant'" % (low_int, locus_start, variant_start, locus_end, variant_end)
            if low_int <= prev_locus_start:
                #print "Extends below the tile variant. Low int (%i), return val (%i), reference_to_tile_variant %s" % (low_int, prev_variant_start, str(reference_to_tile_variant))
                #Extends below the tile variant
                return prev_variant_start
            if low_int <= prev_locus_end:
                #In the previous genome variant
                ref_seq_length = prev_locus_end - prev_locus_start
                var_seq_length = prev_variant_end - prev_variant_start
                if ref_seq_length == 0 or var_seq_length == 0:
                    #print "In the previous genome variant, which is an INDEL. Low int (%i), return val (%i), reference_to_tile_variant %s" % (low_int, prev_variant_start, str(reference_to_tile_variant))
                    return prev_variant_start
                #print "In the previous genome variant, which is a SUB/SNP. Low int (%i), return val (%i), reference_to_tile_variant %s" % (low_int, prev_variant_start + (low_int-prev_locus_start), str(reference_to_tile_variant))
                return prev_variant_start + (low_int-prev_locus_start)
            #In-between two genome-variants
            #print "In-between two genome variants. Low int (%i), return val (%i), reference_to_tile_variant %s" % (low_int, prev_variant_end + (low_int-prev_locus_end), str(reference_to_tile_variant))
            return prev_variant_end + (low_int-prev_locus_end)
        def get_end(high_int, reference_to_tile_variant):
            for i, (locus_start, variant_start, locus_end, variant_end) in enumerate(reference_to_tile_variant):
                if high_int <= locus_start:
                    index = max(i-1, 0)
                    prev_locus_start, prev_variant_start, prev_locus_end, prev_variant_end = reference_to_tile_variant[index]
                    break
            if high_int > locus_start:
                #print "Extends above the tile variant. High int (%i), return val (%i), reference_to_tile_variant %s" % (high_int, variant_end, str(reference_to_tile_variant))
                #Extends past the tile variant
                return variant_end
            if high_int < prev_locus_end:
                #In the previous genome variant
                ref_seq_length = prev_locus_end - prev_locus_start
                var_seq_length = prev_variant_end - prev_variant_start
                if ref_seq_length == 0 or var_seq_length == 0:
                    #print "In the previous genome variant, which is an INDEL. High int (%i), return val (%i), reference_to_tile_variant %s" % (high_int, prev_variant_end, str(reference_to_tile_variant))
                    return prev_variant_end
                #print "In the previous genome variant, which is an SNP/SUB. High int (%i), return val (%i), reference_to_tile_variant %s" % (high_int, prev_variant_start + (high_int-prev_locus_start), str(reference_to_tile_variant))
                return prev_variant_start + (high_int-prev_locus_start)
            #In-between two genome-variants
            #print "In-between two genome variants. High int (%i), return val (%i), reference_to_tile_variant %s" % (high_int, prev_variant_end + (high_int-prev_locus_end), str(reference_to_tile_variant))
            return prev_variant_end + (high_int-prev_locus_end)
        assert queried_low_int <= end_locus_int, "Asked to get out-of-range information for %s. Query: [%i, %i) Locus: [%i, %i)" % (self.get_string(), queried_low_int, queried_high_int, start_locus_int, end_locus_int)
        assert queried_high_int >= start_locus_int, "Asked to get out-of-range information for %s. Query: [%i, %i) Locus: [%i, %i)" % (self.get_string(), queried_low_int, queried_high_int, start_locus_int, end_locus_int)
        #If we are asked to retrieve the entire tile, our job is easy:
        if end_locus_int <= queried_high_int and start_locus_int >= queried_low_int:
            return self.sequence.upper()
        reference_to_tile_variant = self.get_conversion_list_between_genome_variant_loci_and_tile_loci(assembly, start_locus_int, end_locus_int)
        low_int = max(queried_low_int - start_locus_int, 0)
        high_int = queried_high_int - start_locus_int

        lower_base_index = get_start(low_int, reference_to_tile_variant)
        higher_base_index = get_end(high_int, reference_to_tile_variant)
        return self.get_base_group_between_positions(lower_base_index, higher_base_index).upper()
    def get_bases_between_loci(self, queried_low_int, queried_high_int, assembly):
        start_locus_int, end_locus_int = self.get_locus(assembly)
        return self.get_bases_between_loci_known_locus(assembly, queried_low_int, queried_high_int, start_locus_int, end_locus_int)
    def get_tile_variant_lantern_name(self):
        try:
            lantern_name = LanternTranslator.objects.filter(tile_variant_int=int(self.tile_variant_int)).get(tile_library_host='').lantern_name
            return lantern_name
        except LanternTranslator.DoesNotExist: #if there is no translation, we will never get it returned by lantern
            return ""
    def __unicode__(self):
        return self.get_string()
    class Meta:
        #Ensures ordering by tilename
        ordering = ['tile_variant_int']
        unique_together = ('tile','md5sum')
class LanternTranslator(models.Model):
    """
    Implements the translator between the lantern server and available tile libraries

    Values in database:
        lantern_name (textfield): The string matching LANTERN_NAME_FORMAT_STRING.
        tile_library_host (textfield): The host containing the tile_library
        tile_variant_int (bigint): The primary key of the tile in tile_library_access_point
        created(datetimefield): The time the translation was created
        last_modified(datetimefield): The last time the translation was modified

    Functions:
        get_string(): returns string
    """
    lantern_name = models.TextField(unique=True, validators=[RegexValidator(regex=settings.LANTERN_NAME_FORMAT_STRING, message="Not a valid lantern name format (specified in tile_library.constants.LANTERN_NAME_FORMAT_STRING)")])
    tile_library_host = models.TextField(blank=True, default="")
    tile_variant_int = models.BigIntegerField(db_index=True, validators=[validate_tile_variant_int])
    created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    def save(self, *args, **kwargs):
        self.full_clean()
        try:
            validation_fns.validate_lantern_translation(self.lantern_name, self.tile_variant_int)
            if self.tile_library_host == "":
                if not TileVariant.objects.filter(tile_variant_int=self.tile_variant_int).exists():
                    raise ValidationError({'tile_variant_int-tile_library_host':'A TileVariant with a tile_variant_int of %i does not exist in this database' % (self.tile_variant_int)})
            else:
                validation_fns.validate_lantern_translation_outside_database(self.tile_library_host, reverse('api:tile_variant_query_by_int', args=[self.tile_variant_int]))
            super(LanternTranslator, self).save(*args, **kwargs)
        except TileLibraryValidationError as e:
            raise ValidationError(e.value)
    def get_string(self):
        tile_variant_string = basic_fns.get_tile_variant_string_from_tile_variant_int(int(self.tile_variant_int))
        return "Variant %s (%i) is referred to by lantern as %s" % (tile_variant_string, self.tile_variant_int, self.lantern_name)
    get_string.short_description='Lantern Translation'
    def __unicode__(self):
        return self.get_string()
    class Meta:
        #Ensures ordering by tilename
        ordering = ['lantern_name']
        unique_together = ('tile_variant_int','tile_library_host')
    class DegradedVariantError(Exception):
        """
            Variant was accessible when translation was saved, but something went wrong accessing it again
        """
        def __init__(self, value):
            self.value = value
        def __str__(self):
            return repr(self.value)

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
    assembly_int = models.PositiveSmallIntegerField(choices=settings.SUPPORTED_ASSEMBLY_CHOICES, db_index=True)
    chromosome_int = models.PositiveSmallIntegerField(choices=settings.CHR_CHOICES, db_index=True)
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
        chrom_name = self.alternate_chromosome_name
        start = int(self.locus_start_int)
        end = int(self.locus_end_int)
        if end < start:
            raise ValidationError(
                {'locus_start_int-locus_end_int':'locus_end_int (%i) is smaller than locus_start_int (%i)' % (end, start)}
            )
        loci = TileLocusAnnotation.objects.filter(assembly_int=assembly).filter(chromosome_int=chrom).filter(alternate_chromosome_name=chrom_name).filter(start_int__lt=end).filter(end_int__gt=start).order_by('start_int')
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
                assert reference_seq[-settings.TAG_LENGTH:].upper() == reference_tile_variant_sequence[:settings.TAG_LENGTH].upper(), \
                    "Tags mismatching at locus %s: %s not %s" % (loci, reference_seq, reference_tile_variant_sequence)
                reference_seq += reference_tile_variant_sequence[settings.TAG_LENGTH:]
        try:
            validation_fns.validate_reference_bases(reference_seq, start-zero, end-zero, self.reference_bases)
            validation_fns.validate_reference_versus_alternate_bases(self.reference_bases, self.alternate_bases)
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
        unique_together = ('assembly_int', 'chromosome_int', 'alternate_chromosome_name', 'locus_start_int', 'locus_end_int', 'alternate_bases')
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
            is_start_of_path, is_end_of_path = tv.get_start_and_end_of_path_bools()
            for tile_position in range(int(tv.tile_id), int(tv.tile_id) + int(tv.num_positions_spanned)):
                locus = get_locus(gv.assembly_int, tile_position)
                validation_fns.validate_same_chromosome(locus.chromosome_int, gv.chromosome_int, locus.alternate_chromosome_name, gv.alternate_chromosome_name)
            validation_fns.validate_tile_variant_loci_encompass_genome_variant_loci(
                gv.locus_start_int, gv.locus_end_int, start_int, end_int, is_start_of_path, is_end_of_path
            )
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
    statistics_type = models.PositiveSmallIntegerField(db_index=True, choices=settings.STATISTICS_TYPE_CHOICES)
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
        if self.statistics_type == settings.PATH:
            if self.path_name < 0:
                raise ValidationError({'path_name': 'If statistics type is equal to %i, path name must be greater than -1' % (settings.PATH)})
            if self.path_name >= settings.CHR_PATH_LENGTHS[-1]:
                raise ValidationError({'path_name': 'Path name must be less than %i' % (settings.CHR_PATH_LENGTHS[-1])})
        if self.path_name != -1 and self.statistics_type != settings.PATH:
            raise ValidationError({'path_name': 'If statistics type is not equal to %i, path name must be exactly -1' % (settings.PATH)})
        super(GenomeStatistic, self).save(*args, **kwargs)
    def __unicode__(self):
        return human_readable_fns.get_readable_genome_statistics_name(self.statistic_type, path=self.path_name) + "Statistics"
    class Meta:
        unique_together = ("statistics_type", "path_name")
