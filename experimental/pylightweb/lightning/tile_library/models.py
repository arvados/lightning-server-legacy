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
from errors import TileLibraryValidationError

TAG_LENGTH=24

def validate_json(text):
    try:
        json.loads(text)
    except ValueError:
        raise ValidationError("Expects json-formatted text")

def validate_tile_position_int(tile_position_int):
    if tile_position_int < 0:
        raise ValidationError("tile position int must be positive")
    max_tile_position = int('fffffffff', 16)
    if tile_position_int > max_tile_position:
        raise ValidationError("tile position int must be smaller than or equal to 'fff.ff.ffff'")

def validate_tile_variant_int(tile_variant_int):
    if tile_variant_int < 0:
        raise ValidationError("tile variant int must be positive")
    max_tile_variant = int('ffffffffffff', 16)
    if tile_variant_int > max_tile_variant:
        raise ValidationError("tile variant int must be smaller than or equal to 'fff.ff.ffff.fff'")

def validate_tag(tag):
    if len(tag) != TAG_LENGTH:
        raise ValidationError("Tag length must be equal to the set TAG_LENGTH")

class TileManage(models.Manager):
    """
    TileManage ensures correct ordering by the admin site
    """
    def get_by_natural_key(self, name):
        return self.get(tilename=name)

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
        tilename (bigint, primary key): _integer_ of the 9 digit hexidecimal identifier for the tile position
            First 3 digits of the hexidecimal identifier indicate the path
            Next 2 digits indicate the path version
            Next 4 digits indicate the step
        start_tag(charfield(24)): start Tag
        end_tag(charfield(24)): end Tag
        created(datetimefield): The day the tile was generated

    Functions:
        getTileString(): returns string: human readable tile name

    """
    CHR_PATH_LENGTHS = [0,63,125,187,234,279,327,371,411,454,496,532,573,609,641,673,698,722,742,761,781,795,811,851,862,863,863]
    CYTOMAP = ['p36.33', 'p36.32', 'p36.31', 'p36.23', 'p36.22', 'p36.21', 'p36.13', 'p36.12', 'p36.11', 'p35.3', 'p35.2', 'p35.1', 'p34.3', 'p34.2', 'p34.1', 'p33', 'p32.3', 'p32.2', 'p32.1', 'p31.3', 'p31.2', 'p31.1', 'p22.3', 'p22.2', 'p22.1', 'p21.3', 'p21.2', 'p21.1', 'p13.3', 'p13.2', 'p13.1', 'p12', 'p11.2', 'p11.1', 'q11', 'q12', 'q21.1', 'q21.2', 'q21.3', 'q22', 'q23.1', 'q23.2', 'q23.3', 'q24.1', 'q24.2', 'q24.3', 'q25.1', 'q25.2', 'q25.3', 'q31.1', 'q31.2', 'q31.3', 'q32.1', 'q32.2', 'q32.3', 'q41', 'q42.11', 'q42.12', 'q42.13', 'q42.2', 'q42.3', 'q43', 'q44', 'p25.3', 'p25.2', 'p25.1', 'p24.3', 'p24.2', 'p24.1', 'p23.3', 'p23.2', 'p23.1', 'p22.3', 'p22.2', 'p22.1', 'p21', 'p16.3', 'p16.2', 'p16.1', 'p15', 'p14', 'p13.3', 'p13.2', 'p13.1', 'p12', 'p11.2', 'p11.1', 'q11.1', 'q11.2', 'q12.1', 'q12.2', 'q12.3', 'q13', 'q14.1', 'q14.2', 'q14.3', 'q21.1', 'q21.2', 'q21.3', 'q22.1', 'q22.2', 'q22.3', 'q23.1', 'q23.2', 'q23.3', 'q24.1', 'q24.2', 'q24.3', 'q31.1', 'q31.2', 'q31.3', 'q32.1', 'q32.2', 'q32.3', 'q33.1', 'q33.2', 'q33.3', 'q34', 'q35', 'q36.1', 'q36.2', 'q36.3', 'q37.1', 'q37.2', 'q37.3', 'p26.3', 'p26.2', 'p26.1', 'p25.3', 'p25.2', 'p25.1', 'p24.3', 'p24.2', 'p24.1', 'p23', 'p22.3', 'p22.2', 'p22.1', 'p21.33', 'p21.32', 'p21.31', 'p21.2', 'p21.1', 'p14.3', 'p14.2', 'p14.1', 'p13', 'p12.3', 'p12.2', 'p12.1', 'p11.2', 'p11.1', 'q11.1', 'q11.2', 'q12.1', 'q12.2', 'q12.3', 'q13.11', 'q13.12', 'q13.13', 'q13.2', 'q13.31', 'q13.32', 'q13.33', 'q21.1', 'q21.2', 'q21.3', 'q22.1', 'q22.2', 'q22.3', 'q23', 'q24', 'q25.1', 'q25.2', 'q25.31', 'q25.32', 'q25.33', 'q26.1', 'q26.2', 'q26.31', 'q26.32', 'q26.33', 'q27.1', 'q27.2', 'q27.3', 'q28', 'q29', 'p16.3', 'p16.2', 'p16.1', 'p15.33', 'p15.32', 'p15.31', 'p15.2', 'p15.1', 'p14', 'p13', 'p12', 'p11', 'q11', 'q12', 'q13.1', 'q13.2', 'q13.3', 'q21.1', 'q21.21', 'q21.22', 'q21.23', 'q21.3', 'q22.1', 'q22.2', 'q22.3', 'q23', 'q24', 'q25', 'q26', 'q27', 'q28.1', 'q28.2', 'q28.3', 'q31.1', 'q31.21', 'q31.22', 'q31.23', 'q31.3', 'q32.1', 'q32.2', 'q32.3', 'q33', 'q34.1', 'q34.2', 'q34.3', 'q35.1', 'q35.2', 'p15.33', 'p15.32', 'p15.31', 'p15.2', 'p15.1', 'p14.3', 'p14.2', 'p14.1', 'p13.3', 'p13.2', 'p13.1', 'p12', 'p11', 'q11.1', 'q11.2', 'q12.1', 'q12.2', 'q12.3', 'q13.1', 'q13.2', 'q13.3', 'q14.1', 'q14.2', 'q14.3', 'q15', 'q21.1', 'q21.2', 'q21.3', 'q22.1', 'q22.2', 'q22.3', 'q23.1', 'q23.2', 'q23.3', 'q31.1', 'q31.2', 'q31.3', 'q32', 'q33.1', 'q33.2', 'q33.3', 'q34', 'q35.1', 'q35.2', 'q35.3', 'p25.3', 'p25.2', 'p25.1', 'p24.3', 'p24.2', 'p24.1', 'p23', 'p22.3', 'p22.2', 'p22.1', 'p21.33', 'p21.32', 'p21.31', 'p21.2', 'p21.1', 'p12.3', 'p12.2', 'p12.1', 'p11.2', 'p11.1', 'q11.1', 'q11.2', 'q12', 'q13', 'q14.1', 'q14.2', 'q14.3', 'q15', 'q16.1', 'q16.2', 'q16.3', 'q21', 'q22.1', 'q22.2', 'q22.31', 'q22.32', 'q22.33', 'q23.1', 'q23.2', 'q23.3', 'q24.1', 'q24.2', 'q24.3', 'q25.1', 'q25.2', 'q25.3', 'q26', 'q27', 'p22.3', 'p22.2', 'p22.1', 'p21.3', 'p21.2', 'p21.1', 'p15.3', 'p15.2', 'p15.1', 'p14.3', 'p14.2', 'p14.1', 'p13', 'p12.3', 'p12.2', 'p12.1', 'p11.2', 'p11.1', 'q11.1', 'q11.21', 'q11.22', 'q11.23', 'q21.11', 'q21.12', 'q21.13', 'q21.2', 'q21.3', 'q22.1', 'q22.2', 'q22.3', 'q31.1', 'q31.2', 'q31.31', 'q31.32', 'q31.33', 'q32.1', 'q32.2', 'q32.3', 'q33', 'q34', 'q35', 'q36.1', 'q36.2', 'q36.3', 'p23.3', 'p23.2', 'p23.1', 'p22', 'p21.3', 'p21.2', 'p21.1', 'p12', 'p11.23', 'p11.22', 'p11.21', 'p11.1', 'q11.1', 'q11.21', 'q11.22', 'q11.23', 'q12.1', 'q12.2', 'q12.3', 'q13.1', 'q13.2', 'q13.3', 'q21.11', 'q21.12', 'q21.13', 'q21.2', 'q21.3', 'q22.1', 'q22.2', 'q22.3', 'q23.1', 'q23.2', 'q23.3', 'q24.11', 'q24.12', 'q24.13', 'q24.21', 'q24.22', 'q24.23', 'q24.3', 'p24.3', 'p24.2', 'p24.1', 'p23', 'p22.3', 'p22.2', 'p22.1', 'p21.3', 'p21.2', 'p21.1', 'p13.3', 'p13.2', 'p13.1', 'p12', 'p11.2', 'p11.1', 'q11', 'q12', 'q13', 'q21.11', 'q21.12', 'q21.13', 'q21.2', 'q21.31', 'q21.32', 'q21.33', 'q22.1', 'q22.2', 'q22.31', 'q22.32', 'q22.33', 'q31.1', 'q31.2', 'q31.3', 'q32', 'q33.1', 'q33.2', 'q33.3', 'q34.11', 'q34.12', 'q34.13', 'q34.2', 'q34.3', 'p15.3', 'p15.2', 'p15.1', 'p14', 'p13', 'p12.33', 'p12.32', 'p12.31', 'p12.2', 'p12.1', 'p11.23', 'p11.22', 'p11.21', 'p11.1', 'q11.1', 'q11.21', 'q11.22', 'q11.23', 'q21.1', 'q21.2', 'q21.3', 'q22.1', 'q22.2', 'q22.3', 'q23.1', 'q23.2', 'q23.31', 'q23.32', 'q23.33', 'q24.1', 'q24.2', 'q24.31', 'q24.32', 'q24.33', 'q25.1', 'q25.2', 'q25.3', 'q26.11', 'q26.12', 'q26.13', 'q26.2', 'q26.3', 'p15.5', 'p15.4', 'p15.3', 'p15.2', 'p15.1', 'p14.3', 'p14.2', 'p14.1', 'p13', 'p12', 'p11.2', 'p11.12', 'p11.11', 'q11', 'q12.1', 'q12.2', 'q12.3', 'q13.1', 'q13.2', 'q13.3', 'q13.4', 'q13.5', 'q14.1', 'q14.2', 'q14.3', 'q21', 'q22.1', 'q22.2', 'q22.3', 'q23.1', 'q23.2', 'q23.3', 'q24.1', 'q24.2', 'q24.3', 'q25', 'p13.33', 'p13.32', 'p13.31', 'p13.2', 'p13.1', 'p12.3', 'p12.2', 'p12.1', 'p11.23', 'p11.22', 'p11.21', 'p11.1', 'q11', 'q12', 'q13.11', 'q13.12', 'q13.13', 'q13.2', 'q13.3', 'q14.1', 'q14.2', 'q14.3', 'q15', 'q21.1', 'q21.2', 'q21.31', 'q21.32', 'q21.33', 'q22', 'q23.1', 'q23.2', 'q23.3', 'q24.11', 'q24.12', 'q24.13', 'q24.21', 'q24.22', 'q24.23', 'q24.31', 'q24.32', 'q24.33', 'p13', 'p12', 'p11.2', 'p11.1', 'q11', 'q12.11', 'q12.12', 'q12.13', 'q12.2', 'q12.3', 'q13.1', 'q13.2', 'q13.3', 'q14.11', 'q14.12', 'q14.13', 'q14.2', 'q14.3', 'q21.1', 'q21.2', 'q21.31', 'q21.32', 'q21.33', 'q22.1', 'q22.2', 'q22.3', 'q31.1', 'q31.2', 'q31.3', 'q32.1', 'q32.2', 'q32.3', 'q33.1', 'q33.2', 'q33.3', 'q34', 'p13', 'p12', 'p11.2', 'p11.1', 'q11.1', 'q11.2', 'q12', 'q13.1', 'q13.2', 'q13.3', 'q21.1', 'q21.2', 'q21.3', 'q22.1', 'q22.2', 'q22.3', 'q23.1', 'q23.2', 'q23.3', 'q24.1', 'q24.2', 'q24.3', 'q31.1', 'q31.2', 'q31.3', 'q32.11', 'q32.12', 'q32.13', 'q32.2', 'q32.31', 'q32.32', 'q32.33', 'p13', 'p12', 'p11.2', 'p11.1', 'q11.1', 'q11.2', 'q12', 'q13.1', 'q13.2', 'q13.3', 'q14', 'q15.1', 'q15.2', 'q15.3', 'q21.1', 'q21.2', 'q21.3', 'q22.1', 'q22.2', 'q22.31', 'q22.32', 'q22.33', 'q23', 'q24.1', 'q24.2', 'q24.3', 'q25.1', 'q25.2', 'q25.3', 'q26.1', 'q26.2', 'q26.3', 'p13.3', 'p13.2', 'p13.13', 'p13.12', 'p13.11', 'p12.3', 'p12.2', 'p12.1', 'p11.2', 'p11.1', 'q11.1', 'q11.2', 'q12.1', 'q12.2', 'q13', 'q21', 'q22.1', 'q22.2', 'q22.3', 'q23.1', 'q23.2', 'q23.3', 'q24.1', 'q24.2', 'q24.3', 'p13.3', 'p13.2', 'p13.1', 'p12', 'p11.2', 'p11.1', 'q11.1', 'q11.2', 'q12', 'q21.1', 'q21.2', 'q21.31', 'q21.32', 'q21.33', 'q22', 'q23.1', 'q23.2', 'q23.3', 'q24.1', 'q24.2', 'q24.3', 'q25.1', 'q25.2', 'q25.3', 'p11.32', 'p11.31', 'p11.23', 'p11.22', 'p11.21', 'p11.1', 'q11.1', 'q11.2', 'q12.1', 'q12.2', 'q12.3', 'q21.1', 'q21.2', 'q21.31', 'q21.32', 'q21.33', 'q22.1', 'q22.2', 'q22.3', 'q23', 'p13.3', 'p13.2', 'p13.13', 'p13.12', 'p13.11', 'p12', 'p11', 'q11', 'q12', 'q13.11', 'q13.12', 'q13.13', 'q13.2', 'q13.31', 'q13.32', 'q13.33', 'q13.41', 'q13.42', 'q13.43', 'p13', 'p12.3', 'p12.2', 'p12.1', 'p11.23', 'p11.22', 'p11.21', 'p11.1', 'q11.1', 'q11.21', 'q11.22', 'q11.23', 'q12', 'q13.11', 'q13.12', 'q13.13', 'q13.2', 'q13.31', 'q13.32', 'q13.33', 'p13', 'p12', 'p11.2', 'p11.1', 'q11.1', 'q11.2', 'q21.1', 'q21.2', 'q21.3', 'q22.11', 'q22.12', 'q22.13', 'q22.2', 'q22.3', 'p13', 'p12', 'p11.2', 'p11.1', 'q11.1', 'q11.21', 'q11.22', 'q11.23', 'q12.1', 'q12.2', 'q12.3', 'q13.1', 'q13.2', 'q13.31', 'q13.32', 'q13.33', 'p22.33', 'p22.32', 'p22.31', 'p22.2', 'p22.13', 'p22.12', 'p22.11', 'p21.3', 'p21.2', 'p21.1', 'p11.4', 'p11.3', 'p11.23', 'p11.22', 'p11.21', 'p11.1', 'q11.1', 'q11.2', 'q12', 'q13.1', 'q13.2', 'q13.3', 'q21.1', 'q21.2', 'q21.31', 'q21.32', 'q21.33', 'q22.1', 'q22.2', 'q22.3', 'q23', 'q24', 'q25', 'q26.1', 'q26.2', 'q26.3', 'q27.1', 'q27.2', 'q27.3', 'q28', 'p11.32', 'p11.31', 'p11.2', 'p11.1', 'q11.1', 'q11.21', 'q11.221', 'q11.222', 'q11.223', 'q11.23', 'q12', '']

    tilename = models.BigIntegerField(primary_key=True, editable=False, db_index=True, validators=[validate_tile_position_int])
    start_tag = models.CharField(max_length=TAG_LENGTH, validators=[validate_tag])
    end_tag = models.CharField(max_length=TAG_LENGTH, validators=[validate_tag])
    created = models.DateTimeField(auto_now_add=True)
    def save(self, *args, **kwargs):
        try:
            validation_fns.validate_tile(self.tilename)
            super(Tile, self).save(*args, **kwargs)
        except TileLibraryValidationError as e:
            ValidationError("Unable to save TileVariant as it conflicts with validation expectations: " + str(e))
    def getTileString(self):
        """Displays hex indexing for tile """
        return basic_fns.get_position_string_from_position_int(int(self.tilename))
    getTileString.short_description='Tile Name'
    def __unicode__(self):
        return self.getTileString()
    class Meta:
        #Ensures ordering by tilename
        ordering = ['tilename']

class TileVariant(models.Model):
    """
    Implements a TileVariant. Each Tile can have many TileVariants (one-to-many relation).
        The reference tile is a TileVariant with a variant value of 000.
        Note that a tile can be reference and not the default and vice versa,
        since the default is determined by the size of the population containing a tile variant.
        Determining the population size should be done using the human npy files.

    Values in database:
        tile_variant_name (bigint; primary key):Includes the parent tile name to ensure uniqueness.
            xxx.xx.xxxx.xxx. Last three digits indicate the TileVariant value.
            The reference tile has a TileVariant value equal to 0 (000).
        tile (bigint; foreignkey): The parent tile
        num_positions_spanned (smallint; positive): The number of positions spanned by this tilevariant
        variant_value (int; positive): The variant value. 0 if reference
        length (int; positive): Length of the TileVariant in bases
        md5sum (charfield(40)): The hash for the TileVariant sequence
        created(datetimefield): The time the TileVariant was created
        last_modified(datetimefield): The last time the TileVariant was modified
        sequence (textfield): The sequence of the TileVariant
        start_tag (textfield): the start tag of the TileVariant iff the start tag varies from tile.start_tag
        end_tag (textfield): the end tag of the TileVariant iff the end tag varies from tile.end_tag

    Functions:
        getString(): returns string: human readable tile variant name
        isReference(): returns boolean: True if the variant is the reference variant.
            Depends on tile_variant_name (check if variant is equal to 000) (or variant_value)
    """
    tile_variant_name = models.BigIntegerField(primary_key=True, editable=False, db_index=True, validators=[validate_tile_variant_int])
    tile = models.ForeignKey(Tile, related_name='tile_variants', db_index=True)
    num_positions_spanned = models.PositiveSmallIntegerField()
    conversion_to_cgf = models.TextField(default='')
    variant_value = models.PositiveIntegerField(db_index=True)
    length = models.PositiveIntegerField(db_index=True)
    md5sum = models.CharField(max_length=40)
    created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    sequence = models.TextField()
    start_tag = models.TextField(blank=True)
    end_tag = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        try:
            start_tag = self.start_tag
            if start_tag == '':
                start_tag = self.tile.start_tag
            end_tag = self.end_tag
            if end_tag == '':
                end_tag = self.tile.end_tag
            validation_fns.validate_tile_variant(
                TAG_LENGTH, self.tile_id, self.tile_variant_name, self.variant_value, self.sequence, self.length, self.md5sum, start_tag, end_tag
            )
            super(TileVariant, self).save(*args, **kwargs)
        except TileLibraryValidationError as e:
            ValidationError("Unable to save TileVariant as it conflicts with validation expectations: " + str(e))

    def getString(self):
        """Displays hex indexing for tile variant"""
        return basic_fns.get_tile_variant_string_from_tile_variant_int(int(self.tile_variant_name))
    getString.short_description='Variant Name'
    def isReference(self):
        return int(self.variant_value) == 0
    def getBaseAtPosition(self, position_int):
        try:
            position_int = int(position_int)
        except ValueError:
            raise Exception('Position integer must be able to convert into an integer')
        assert position_int < self.length, "Expects the position integer to be 0-indexed and less than the length of the sequence"
        assert position_int > -1, "Expects the position integer to be positive"
        try:
            return self.sequence[position_int]
        except IndexError:
            raise Exception('Malformed tile: length is not the length of the sequence')
    def getBaseGroupBetweenPositions(self, lower_position_int, upper_position_int):
        try:
            lower_position_int = int(lower_position_int)
            upper_position_int = int(upper_position_int)
        except ValueError:
            raise Exception('Position integer must be able to convert into an integer')
        info_str = "Lower position int is: " + str(lower_position_int) + ", upper position int (exclusive and 0-indexed) is: " + \
            str(upper_position_int) + ", length of sequence is " + str(self.length) + ", name: " + self.getString()
        assert lower_position_int <= self.length, "Expects the lower position integer to be 0-indexed and not greater than the length of the sequence. " + info_str
        assert upper_position_int <= self.length, "Expects the upper position integer to be 0-indexed and not greater than the length of the sequence. " + info_str
        assert lower_position_int > -1, "Expects the lower position integer to be positive. " + info_str
        assert upper_position_int > -1, "Expects the upper position integer to be positive. " + info_str
        assert lower_position_int <= upper_position_int, "Expects lower position_int to be less than or equal to upper position int. " + info_str
        try:
            return self.sequence[lower_position_int:upper_position_int]
        except IndexError:
            raise Exception('Malformed tile: length is not the length of the sequence')

    def __unicode__(self):
        return self.getString()
    class Meta:
        #Ensures ordering by tilename
        ordering = ['tile_variant_name']

class GenomeVariant(models.Model):
    """
    Implements a variant (SNP, SUB, or INDEL) for a TileVariant.
    Many-to-Many relation with TileVariant.
    2 ForeignKey relations with Tile to indicate the start and end position of the GenomeVariant
    When uploading a GenomeVariant, start_tile_position and end_tile_position are checked to ensure they are on the same chromosome

    Values in database:
        id (big integer field): the id of the GenomeVariant. For indexing, when converted into hex,
            the first 3 integers are the path the genomevariant is on
        start_tile_position (foreignkey): the Tile position containing the first locus affected by the GenomeVariant
        start_increment(integer): Positive integer, zero-indexed, relative to start of Tile pointed at by start_tile_position
        end_tile_position (foreignkey): the Tile position containing the last locus affected by the GenomeVariant
        end_increment(integer): Positive integer, zero-indexed, exclusive, relative to the start of Tile pointed at by end_tile_position
            NOTE: since end_increment is exclusive, sometimes the end_tile_position Tile is adjacent to the GenomeVariant. Since the tags overlap,
            this is considered not a problem
        tile_variants (many-to-many-field): the TileVariants containing this GenomeVariant
        names (textfield): Tab-separated names for this variant
        reference_bases (textfield): Text of reference bases (currently hg19, variant 0), follows this regex pattern: [ACGT-]+
        alternate_bases (textfield): Text of variant bases, follows this regex pattern: [ACGT-]+

        info (textfield): Json-formatted. Includes {'source': [what generated the variant],
                                                    'phenotype': [phenotypes associated with this annotation]}
        created(datetimefield): time when the variant was created
        last_modified(datetimefield): time when the variant was last modified

    These values relate to GAVariant by:
        GAVariant.id -> GenomeVariant.id
        GAVariant.variantSetId -> N/A
        GAVariant.names -> GenomeVariant.names
        GAVariant.created -> GenomeVariant.created
        GAVariant.updated -> GenomeVariant.last_modified
        GAVariant.referenceName -> GenomeVariant.start_tile_position.tile_locus_annotations.get(assembly=[desired assembly]).get_readable_chr_name()
        GAVariant.start -> GenomeVariant.start_increment +
                           GenomeVariant.start_tile_position.tile_locus_annotations.get(assembly=[desired assembly]).begin_int
        GAVariant.end -> GenomeVariant.end_increment +
                         GenomeVariant.end_tile_position.tile_locus_annotations.get(assembly=[desired assembly]).begin_int
        GAVariant.referenceBases -> GenomeVariant.reference_bases or empty string if '-'
        GAVariant.alternateBases -> GenomeVariant.alternate_bases or empty string if '-'
        GAVariant.info -> GenomeVariant.info
        GAVariant.calls -> N/A
    """
    id = models.BigIntegerField(primary_key=True, editable=False)
    start_tile_position = models.ForeignKey(Tile, related_name='starting_genome_variants', db_index=True)
    start_increment = models.PositiveIntegerField()
    end_tile_position = models.ForeignKey(Tile, related_name='ending_genome_variants', db_index=True)
    end_increment = models.PositiveIntegerField()

    tile_variants = models.ManyToManyField(TileVariant, through='GenomeVariantTranslation',
                                           through_fields=('genome_variant', 'tile_variant'),
                                           related_name='genome_variants', db_index=True)

    names = models.TextField(help_text="Tab-separated aliases for this variant (rsID tags, RefSNP id, etc.",
                             blank=True)
    reference_bases = models.TextField(
        help_text="Text of variant bases, follows the regex pattern: [ACGT-]+\n'-' indicates an insertion",
        validators=[RegexValidator(regex='[ACGT-]+', message="Not a valid sequence")],
        )
    alternate_bases = models.TextField(
        help_text="Text of variant bases, follows the regex pattern: [ACGT-]+\n'-' indicates a deletion",
        validators=[RegexValidator(regex='[ACGT-]+', message="Not a valid sequence")],
        )
    info = models.TextField(
        help_text="Json-formatted. Known keys are 'source': [what generated the variant],\
                   'phenotype': [phenotypes associated with this annotation], 'amino_acid': [predicted amino-acid changes],\
                   'ucsc_trans': [UCSC translation (picked up from GFF files), and 'other': [Other GFF-file related annotations]",
        validators=[validate_json], db_index=True
        )
    created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    def __unicode__(self):
        length = len(self.alternate_bases) - len(self.reference_bases)
        if length > 0 or self.reference_bases == '-':
            humanReadable = 'Insertion'
        elif length < 0 or self.alternate_bases == '-':
            humanReadable = 'Deletion'
        else:
            humanReadable = 'SNP'
        return basic_fns.get_position_string_from_position_int(int(self.start_tile_position.tilename)) + ": " + humanReadable
    class Meta:
        #Ensures ordering by tilename
        ordering = ['start_tile_position', 'start_increment']

class GenomeVariantTranslation(models.Model):
    """
    Implements the Many-to-Many relation between GenomeVariant and TileVariant as well the translation between them

    Values in database:
        tile_variant (foreignkey): the id of the TileVariant
        genome_variant(foreignkey): the id of the GenomeVariant
        start (integer): Positive integer, zero-indexed, relative to start of the TileVariant
        end(integer): Positive integer, zero-indexed, exclusive, relative to the start of the TileVariant
    """
    tile_variant = models.ForeignKey(TileVariant, related_name='translation_to_genome_variant')
    genome_variant = models.ForeignKey(GenomeVariant, related_name='translation_to_tilevariant')
    start = models.PositiveIntegerField(help_text="Positive integer, zero-indexed, relative to start of that tilevariant")
    end = models.PositiveIntegerField(help_text="Positive integer, zero-indexed, relative to start of that tilevariant. Exclusive")
    def __unicode__(self):
        return self.tile_variant.__unicode__() + " translation to Genome Variant. (id: " + str(self.genome_variant.id) + ")"
    class Meta:
        unique_together = ("tile_variant", "genome_variant")

class TileLocusAnnotation(models.Model):
    """
    Implements mapping to enable translations between assembly loci and tile id.
    From looking at UCSC Genome Browser definitions of chromosome bands, we deduce these are currently:
        0-indexed.
        [begin_int, end_int) (exclusive end int)

    Example input from FASTJ:
        Tile x  : {"build":"hg19 chr9 135900000-24 135900225"} => begin_int: 135900000; end_int: 135900225
        Tile x+1: {"build":"hg19 chr9 135900201 135900450"} => begin_int: 135900201; end_int: 135900450

    Values in database:
        assembly(positive small integer): the integer mapping to the name of the assembly;
            Choices given by SUPPORTED_ASSEMBLY_CHOICES
        chromosome(positive small integer): the integer mapping to the chromosome the tile
            is on; Choices given by CHR_CHOICES
        begin_int(positive int): the beginning base, 0 indexed
        end_int(positive int): the ending base, 0 indexed
        chromosome_name(charfield(100)): the name of the chromosome if chromosome=26 (OTHER)
        tile(foreignkey): the tile associated with this locus annotation
            tile_locus_annotations: the related name for these annotations
    """
    ASSEMBLY_16 = 16
    ASSEMBLY_17 = 17
    ASSEMBLY_18 = 18
    ASSEMBLY_19 = 19
    ASSEMBLY_38 = 38
    SUPPORTED_ASSEMBLY_CHOICES = (
        (ASSEMBLY_16, 'NCBI34/hg16'),
        (ASSEMBLY_17, 'NCBI35/hg17'),
        (ASSEMBLY_18, 'NCBI36/hg18'),
        (ASSEMBLY_19, 'GRCh37/hg19'),
        (ASSEMBLY_38, 'GRCh38/hg38'),
    )
    CHR_1 = 1
    CHR_2 = 2
    CHR_3 = 3
    CHR_4 = 4
    CHR_5 = 5
    CHR_6 = 6
    CHR_7 = 7
    CHR_8 = 8
    CHR_9 = 9
    CHR_10 = 10
    CHR_11 = 11
    CHR_12 = 12
    CHR_13 = 13
    CHR_14 = 14
    CHR_15 = 15
    CHR_16 = 16
    CHR_17 = 17
    CHR_18 = 18
    CHR_19 = 19
    CHR_20 = 20
    CHR_21 = 21
    CHR_22 = 22
    CHR_X = 23
    CHR_Y = 24
    CHR_M = 25
    OTHER = 26
    CHR_CHOICES = (
        (CHR_1, 'chr1'),
        (CHR_2, 'chr2'),
        (CHR_3, 'chr3'),
        (CHR_4, 'chr4'),
        (CHR_5, 'chr5'),
        (CHR_6, 'chr6'),
        (CHR_7, 'chr7'),
        (CHR_8, 'chr8'),
        (CHR_9, 'chr9'),
        (CHR_10, 'chr10'),
        (CHR_11, 'chr11'),
        (CHR_12, 'chr12'),
        (CHR_13, 'chr13'),
        (CHR_14, 'chr14'),
        (CHR_15, 'chr15'),
        (CHR_16, 'chr16'),
        (CHR_17, 'chr17'),
        (CHR_18, 'chr18'),
        (CHR_19, 'chr19'),
        (CHR_20, 'chr20'),
        (CHR_21, 'chr21'),
        (CHR_22, 'chr22'),
        (CHR_X, 'chrX'),
        (CHR_Y, 'chrY'),
        (CHR_M, 'chrM'),
        (OTHER, 'Other'),
    )
    assembly= models.PositiveSmallIntegerField(choices=SUPPORTED_ASSEMBLY_CHOICES, db_index=True)
    chromosome = models.PositiveSmallIntegerField(choices=CHR_CHOICES, db_index=True)
    begin_int = models.PositiveIntegerField(db_index=True)
    end_int = models.PositiveIntegerField(db_index=True)
    chromosome_name = models.CharField(max_length=100)
    tile = models.ForeignKey(Tile, related_name="tile_locus_annotations", db_index=True)
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
    GENOME = 0
    CHR_1 = 1
    CHR_2 = 2
    CHR_3 = 3
    CHR_4 = 4
    CHR_5 = 5
    CHR_6 = 6
    CHR_7 = 7
    CHR_8 = 8
    CHR_9 = 9
    CHR_10 = 10
    CHR_11 = 11
    CHR_12 = 12
    CHR_13 = 13
    CHR_14 = 14
    CHR_15 = 15
    CHR_16 = 16
    CHR_17 = 17
    CHR_18 = 18
    CHR_19 = 19
    CHR_20 = 20
    CHR_21 = 21
    CHR_22 = 22
    CHR_X = 23
    CHR_Y = 24
    CHR_M = 25
    CHR_OTHER = 26
    PATH = 27
    NAME_CHOICES = (
        (GENOME, 'Entire Genome'),
        (CHR_1, 'chr1'),
        (CHR_2, 'chr2'),
        (CHR_3, 'chr3'),
        (CHR_4, 'chr4'),
        (CHR_5, 'chr5'),
        (CHR_6, 'chr6'),
        (CHR_7, 'chr7'),
        (CHR_8, 'chr8'),
        (CHR_9, 'chr9'),
        (CHR_10, 'chr10'),
        (CHR_11, 'chr11'),
        (CHR_12, 'chr12'),
        (CHR_13, 'chr13'),
        (CHR_14, 'chr14'),
        (CHR_15, 'chr15'),
        (CHR_16, 'chr16'),
        (CHR_17, 'chr17'),
        (CHR_18, 'chr18'),
        (CHR_19, 'chr19'),
        (CHR_20, 'chr20'),
        (CHR_21, 'chr21'),
        (CHR_22, 'chr22'),
        (CHR_X, 'chrX'),
        (CHR_Y, 'chrY'),
        (CHR_M, 'chrM'),
        (CHR_OTHER, 'Other Chromosomes'),
        (PATH, 'Path'),
    )

    statistics_type = models.PositiveSmallIntegerField(db_index=True, choices=NAME_CHOICES)

    path_name = models.PositiveIntegerField(db_index=True, blank=True, null=True)

    position_num = models.BigIntegerField()
    tile_num = models.BigIntegerField()

    max_num_positions_spanned = models.PositiveIntegerField(null=True)

    def __unicode__(self):
        if self.statistics_type < 27:
            name_index = [i for i,j in self.NAME_CHOICES]
            humanReadable = self.NAME_CHOICES[name_index.index(self.statistics_type)][1]
            return humanReadable + " Statistics"
        else:
            return "Path " + str(self.path_name) + " Statistics"
    class Meta:
        unique_together = ("statistics_type", "path_name")
