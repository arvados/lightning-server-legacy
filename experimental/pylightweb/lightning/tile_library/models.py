from django.db import models
import string 

#No population data for these models: all of that should be dealt with using the human models or npy file manipulation
#   Population data includes:
#       png representation of the tile
#       Color each variant is associated with
#       size of the population
#
#Annotations that span multiple tiles should be in loadgenes
#
#
#TODO: Add lift-over information/function for Tile?
#TODO: Check that all tilevariants for each tile have the same loci

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
        getPath(): returns string: human readable tile path
    
    """
    CHR_PATH_LENGTHS = [0,63,125,187,234,279,327,371,411,454,496,532,573,609,641,673,698,722,742,761,781,795,811,851,862,863,863]
    CYTOMAP = ['p36.33', 'p36.32', 'p36.31', 'p36.23', 'p36.22', 'p36.21', 'p36.13', 'p36.12', 'p36.11', 'p35.3', 'p35.2', 'p35.1', 'p34.3', 'p34.2', 'p34.1', 'p33', 'p32.3', 'p32.2', 'p32.1', 'p31.3', 'p31.2', 'p31.1', 'p22.3', 'p22.2', 'p22.1', 'p21.3', 'p21.2', 'p21.1', 'p13.3', 'p13.2', 'p13.1', 'p12', 'p11.2', 'p11.1', 'q11', 'q12', 'q21.1', 'q21.2', 'q21.3', 'q22', 'q23.1', 'q23.2', 'q23.3', 'q24.1', 'q24.2', 'q24.3', 'q25.1', 'q25.2', 'q25.3', 'q31.1', 'q31.2', 'q31.3', 'q32.1', 'q32.2', 'q32.3', 'q41', 'q42.11', 'q42.12', 'q42.13', 'q42.2', 'q42.3', 'q43', 'q44', 'p25.3', 'p25.2', 'p25.1', 'p24.3', 'p24.2', 'p24.1', 'p23.3', 'p23.2', 'p23.1', 'p22.3', 'p22.2', 'p22.1', 'p21', 'p16.3', 'p16.2', 'p16.1', 'p15', 'p14', 'p13.3', 'p13.2', 'p13.1', 'p12', 'p11.2', 'p11.1', 'q11.1', 'q11.2', 'q12.1', 'q12.2', 'q12.3', 'q13', 'q14.1', 'q14.2', 'q14.3', 'q21.1', 'q21.2', 'q21.3', 'q22.1', 'q22.2', 'q22.3', 'q23.1', 'q23.2', 'q23.3', 'q24.1', 'q24.2', 'q24.3', 'q31.1', 'q31.2', 'q31.3', 'q32.1', 'q32.2', 'q32.3', 'q33.1', 'q33.2', 'q33.3', 'q34', 'q35', 'q36.1', 'q36.2', 'q36.3', 'q37.1', 'q37.2', 'q37.3', 'p26.3', 'p26.2', 'p26.1', 'p25.3', 'p25.2', 'p25.1', 'p24.3', 'p24.2', 'p24.1', 'p23', 'p22.3', 'p22.2', 'p22.1', 'p21.33', 'p21.32', 'p21.31', 'p21.2', 'p21.1', 'p14.3', 'p14.2', 'p14.1', 'p13', 'p12.3', 'p12.2', 'p12.1', 'p11.2', 'p11.1', 'q11.1', 'q11.2', 'q12.1', 'q12.2', 'q12.3', 'q13.11', 'q13.12', 'q13.13', 'q13.2', 'q13.31', 'q13.32', 'q13.33', 'q21.1', 'q21.2', 'q21.3', 'q22.1', 'q22.2', 'q22.3', 'q23', 'q24', 'q25.1', 'q25.2', 'q25.31', 'q25.32', 'q25.33', 'q26.1', 'q26.2', 'q26.31', 'q26.32', 'q26.33', 'q27.1', 'q27.2', 'q27.3', 'q28', 'q29', 'p16.3', 'p16.2', 'p16.1', 'p15.33', 'p15.32', 'p15.31', 'p15.2', 'p15.1', 'p14', 'p13', 'p12', 'p11', 'q11', 'q12', 'q13.1', 'q13.2', 'q13.3', 'q21.1', 'q21.21', 'q21.22', 'q21.23', 'q21.3', 'q22.1', 'q22.2', 'q22.3', 'q23', 'q24', 'q25', 'q26', 'q27', 'q28.1', 'q28.2', 'q28.3', 'q31.1', 'q31.21', 'q31.22', 'q31.23', 'q31.3', 'q32.1', 'q32.2', 'q32.3', 'q33', 'q34.1', 'q34.2', 'q34.3', 'q35.1', 'q35.2', 'p15.33', 'p15.32', 'p15.31', 'p15.2', 'p15.1', 'p14.3', 'p14.2', 'p14.1', 'p13.3', 'p13.2', 'p13.1', 'p12', 'p11', 'q11.1', 'q11.2', 'q12.1', 'q12.2', 'q12.3', 'q13.1', 'q13.2', 'q13.3', 'q14.1', 'q14.2', 'q14.3', 'q15', 'q21.1', 'q21.2', 'q21.3', 'q22.1', 'q22.2', 'q22.3', 'q23.1', 'q23.2', 'q23.3', 'q31.1', 'q31.2', 'q31.3', 'q32', 'q33.1', 'q33.2', 'q33.3', 'q34', 'q35.1', 'q35.2', 'q35.3', 'p25.3', 'p25.2', 'p25.1', 'p24.3', 'p24.2', 'p24.1', 'p23', 'p22.3', 'p22.2', 'p22.1', 'p21.33', 'p21.32', 'p21.31', 'p21.2', 'p21.1', 'p12.3', 'p12.2', 'p12.1', 'p11.2', 'p11.1', 'q11.1', 'q11.2', 'q12', 'q13', 'q14.1', 'q14.2', 'q14.3', 'q15', 'q16.1', 'q16.2', 'q16.3', 'q21', 'q22.1', 'q22.2', 'q22.31', 'q22.32', 'q22.33', 'q23.1', 'q23.2', 'q23.3', 'q24.1', 'q24.2', 'q24.3', 'q25.1', 'q25.2', 'q25.3', 'q26', 'q27', 'p22.3', 'p22.2', 'p22.1', 'p21.3', 'p21.2', 'p21.1', 'p15.3', 'p15.2', 'p15.1', 'p14.3', 'p14.2', 'p14.1', 'p13', 'p12.3', 'p12.2', 'p12.1', 'p11.2', 'p11.1', 'q11.1', 'q11.21', 'q11.22', 'q11.23', 'q21.11', 'q21.12', 'q21.13', 'q21.2', 'q21.3', 'q22.1', 'q22.2', 'q22.3', 'q31.1', 'q31.2', 'q31.31', 'q31.32', 'q31.33', 'q32.1', 'q32.2', 'q32.3', 'q33', 'q34', 'q35', 'q36.1', 'q36.2', 'q36.3', 'p23.3', 'p23.2', 'p23.1', 'p22', 'p21.3', 'p21.2', 'p21.1', 'p12', 'p11.23', 'p11.22', 'p11.21', 'p11.1', 'q11.1', 'q11.21', 'q11.22', 'q11.23', 'q12.1', 'q12.2', 'q12.3', 'q13.1', 'q13.2', 'q13.3', 'q21.11', 'q21.12', 'q21.13', 'q21.2', 'q21.3', 'q22.1', 'q22.2', 'q22.3', 'q23.1', 'q23.2', 'q23.3', 'q24.11', 'q24.12', 'q24.13', 'q24.21', 'q24.22', 'q24.23', 'q24.3', 'p24.3', 'p24.2', 'p24.1', 'p23', 'p22.3', 'p22.2', 'p22.1', 'p21.3', 'p21.2', 'p21.1', 'p13.3', 'p13.2', 'p13.1', 'p12', 'p11.2', 'p11.1', 'q11', 'q12', 'q13', 'q21.11', 'q21.12', 'q21.13', 'q21.2', 'q21.31', 'q21.32', 'q21.33', 'q22.1', 'q22.2', 'q22.31', 'q22.32', 'q22.33', 'q31.1', 'q31.2', 'q31.3', 'q32', 'q33.1', 'q33.2', 'q33.3', 'q34.11', 'q34.12', 'q34.13', 'q34.2', 'q34.3', 'p15.3', 'p15.2', 'p15.1', 'p14', 'p13', 'p12.33', 'p12.32', 'p12.31', 'p12.2', 'p12.1', 'p11.23', 'p11.22', 'p11.21', 'p11.1', 'q11.1', 'q11.21', 'q11.22', 'q11.23', 'q21.1', 'q21.2', 'q21.3', 'q22.1', 'q22.2', 'q22.3', 'q23.1', 'q23.2', 'q23.31', 'q23.32', 'q23.33', 'q24.1', 'q24.2', 'q24.31', 'q24.32', 'q24.33', 'q25.1', 'q25.2', 'q25.3', 'q26.11', 'q26.12', 'q26.13', 'q26.2', 'q26.3', 'p15.5', 'p15.4', 'p15.3', 'p15.2', 'p15.1', 'p14.3', 'p14.2', 'p14.1', 'p13', 'p12', 'p11.2', 'p11.12', 'p11.11', 'q11', 'q12.1', 'q12.2', 'q12.3', 'q13.1', 'q13.2', 'q13.3', 'q13.4', 'q13.5', 'q14.1', 'q14.2', 'q14.3', 'q21', 'q22.1', 'q22.2', 'q22.3', 'q23.1', 'q23.2', 'q23.3', 'q24.1', 'q24.2', 'q24.3', 'q25', 'p13.33', 'p13.32', 'p13.31', 'p13.2', 'p13.1', 'p12.3', 'p12.2', 'p12.1', 'p11.23', 'p11.22', 'p11.21', 'p11.1', 'q11', 'q12', 'q13.11', 'q13.12', 'q13.13', 'q13.2', 'q13.3', 'q14.1', 'q14.2', 'q14.3', 'q15', 'q21.1', 'q21.2', 'q21.31', 'q21.32', 'q21.33', 'q22', 'q23.1', 'q23.2', 'q23.3', 'q24.11', 'q24.12', 'q24.13', 'q24.21', 'q24.22', 'q24.23', 'q24.31', 'q24.32', 'q24.33', 'p13', 'p12', 'p11.2', 'p11.1', 'q11', 'q12.11', 'q12.12', 'q12.13', 'q12.2', 'q12.3', 'q13.1', 'q13.2', 'q13.3', 'q14.11', 'q14.12', 'q14.13', 'q14.2', 'q14.3', 'q21.1', 'q21.2', 'q21.31', 'q21.32', 'q21.33', 'q22.1', 'q22.2', 'q22.3', 'q31.1', 'q31.2', 'q31.3', 'q32.1', 'q32.2', 'q32.3', 'q33.1', 'q33.2', 'q33.3', 'q34', 'p13', 'p12', 'p11.2', 'p11.1', 'q11.1', 'q11.2', 'q12', 'q13.1', 'q13.2', 'q13.3', 'q21.1', 'q21.2', 'q21.3', 'q22.1', 'q22.2', 'q22.3', 'q23.1', 'q23.2', 'q23.3', 'q24.1', 'q24.2', 'q24.3', 'q31.1', 'q31.2', 'q31.3', 'q32.11', 'q32.12', 'q32.13', 'q32.2', 'q32.31', 'q32.32', 'q32.33', 'p13', 'p12', 'p11.2', 'p11.1', 'q11.1', 'q11.2', 'q12', 'q13.1', 'q13.2', 'q13.3', 'q14', 'q15.1', 'q15.2', 'q15.3', 'q21.1', 'q21.2', 'q21.3', 'q22.1', 'q22.2', 'q22.31', 'q22.32', 'q22.33', 'q23', 'q24.1', 'q24.2', 'q24.3', 'q25.1', 'q25.2', 'q25.3', 'q26.1', 'q26.2', 'q26.3', 'p13.3', 'p13.2', 'p13.13', 'p13.12', 'p13.11', 'p12.3', 'p12.2', 'p12.1', 'p11.2', 'p11.1', 'q11.1', 'q11.2', 'q12.1', 'q12.2', 'q13', 'q21', 'q22.1', 'q22.2', 'q22.3', 'q23.1', 'q23.2', 'q23.3', 'q24.1', 'q24.2', 'q24.3', 'p13.3', 'p13.2', 'p13.1', 'p12', 'p11.2', 'p11.1', 'q11.1', 'q11.2', 'q12', 'q21.1', 'q21.2', 'q21.31', 'q21.32', 'q21.33', 'q22', 'q23.1', 'q23.2', 'q23.3', 'q24.1', 'q24.2', 'q24.3', 'q25.1', 'q25.2', 'q25.3', 'p11.32', 'p11.31', 'p11.23', 'p11.22', 'p11.21', 'p11.1', 'q11.1', 'q11.2', 'q12.1', 'q12.2', 'q12.3', 'q21.1', 'q21.2', 'q21.31', 'q21.32', 'q21.33', 'q22.1', 'q22.2', 'q22.3', 'q23', 'p13.3', 'p13.2', 'p13.13', 'p13.12', 'p13.11', 'p12', 'p11', 'q11', 'q12', 'q13.11', 'q13.12', 'q13.13', 'q13.2', 'q13.31', 'q13.32', 'q13.33', 'q13.41', 'q13.42', 'q13.43', 'p13', 'p12.3', 'p12.2', 'p12.1', 'p11.23', 'p11.22', 'p11.21', 'p11.1', 'q11.1', 'q11.21', 'q11.22', 'q11.23', 'q12', 'q13.11', 'q13.12', 'q13.13', 'q13.2', 'q13.31', 'q13.32', 'q13.33', 'p13', 'p12', 'p11.2', 'p11.1', 'q11.1', 'q11.2', 'q21.1', 'q21.2', 'q21.3', 'q22.11', 'q22.12', 'q22.13', 'q22.2', 'q22.3', 'p13', 'p12', 'p11.2', 'p11.1', 'q11.1', 'q11.21', 'q11.22', 'q11.23', 'q12.1', 'q12.2', 'q12.3', 'q13.1', 'q13.2', 'q13.31', 'q13.32', 'q13.33', 'p22.33', 'p22.32', 'p22.31', 'p22.2', 'p22.13', 'p22.12', 'p22.11', 'p21.3', 'p21.2', 'p21.1', 'p11.4', 'p11.3', 'p11.23', 'p11.22', 'p11.21', 'p11.1', 'q11.1', 'q11.2', 'q12', 'q13.1', 'q13.2', 'q13.3', 'q21.1', 'q21.2', 'q21.31', 'q21.32', 'q21.33', 'q22.1', 'q22.2', 'q22.3', 'q23', 'q24', 'q25', 'q26.1', 'q26.2', 'q26.3', 'q27.1', 'q27.2', 'q27.3', 'q28', 'p11.32', 'p11.31', 'p11.2', 'p11.1', 'q11.1', 'q11.21', 'q11.221', 'q11.222', 'q11.223', 'q11.23', 'q12', '']
    
    tilename = models.BigIntegerField(primary_key=True, editable=False, db_index=True) 
    start_tag = models.CharField(max_length=24)
    end_tag = models.CharField(max_length=24)
    created = models.DateTimeField(auto_now_add=True)
    
    def getTileString(self):
        """Displays hex indexing for tile """
        strTilename = hex(self.tilename).lstrip('0x').rstrip('L')
        strTilename = strTilename.zfill(9)
        path = strTilename[:3]
        version = strTilename[3:5]
        step = strTilename[5:]
        return string.join([path, version, step], ".")
    getTileString.short_description='Tile Name'
    def __unicode__(self):
        return self.getTileString()
    def getPath(self):
        strTilename = hex(self.tilename).lstrip('0x').rstrip('L')
        strTilename = strTilename.zfill(9)
        path = strTilename[:3]
        return int(path,16)
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
        getPath(): returns int: path integer
        getStep(): returns int: step integer
        
    """
    tile_variant_name = models.BigIntegerField(primary_key=True, editable=False, db_index=True)
    tile = models.ForeignKey(Tile, related_name='variants', db_index=True)
    variant_value = models.PositiveIntegerField(db_index=True)
    length = models.PositiveIntegerField(db_index=True)
    md5sum = models.CharField(max_length=40)
    created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    sequence = models.TextField()
    start_tag = models.TextField(blank=True)
    end_tag = models.TextField(blank=True)
    
    def getString(self):
        """Displays hex indexing for tile variant"""
        strTilename = hex(self.tile_variant_name).lstrip('0x').rstrip('L')
        strTilename = strTilename.zfill(12)
        path = strTilename[:3]
        version = strTilename[3:5]
        step = strTilename[5:9]
        var = strTilename[9:]
        return string.join([path, version, step, var], ".")
    getString.short_description='Variant Name'
    def isReference(self):
        return self.variant_value == 0
    def getPath(self):
        strTilename = hex(self.tile_variant_name).lstrip('0x').rstrip('L')
        strTilename = strTilename.zfill(12)
        path = strTilename[:3]
        return int(path,16)
    def getStep(self):
        strTilename = hex(self.tile_variant_name).lstrip('0x').rstrip('L')
        strTilename = strTilename.zfill(12)
        step = strTilename[5:9]
        return int(step,16)
    def __unicode__(self):
        return self.getString()
    class Meta:
        #Ensures ordering by tilename
        ordering = ['tile_variant_name']

class VarAnnotation(models.Model):
    """
    Implements an annotation for a TileVariant. Meant for annotations about the sequence, connect to
        other databases, or describe phenotypes that _do_not_ span Tile positions
    One-to-many relation with TileVariant. Currently not many-to-many to conserve memory in the postgres server.
    Note that some annotations apply to multiple tiles. They are currently represented by duplicate
        annotation_text's

    OTHER only used for debugging purposes
    
    Values in database:
        tile_variant (foreignkey): the tile_variant this annotation applies to
        annotation_type (charfield(10)): what the annotation describes; TYPE_CHOICES indicates valid choices
        source (charfield(100)):  indicates what generated the annotation (Human or code name)
        annotation_text(textfield): the text field of the annotation. Currently, no special parsing
            is applied during creation. Though this slows queries down, it speeds up tile generation
        phenotype(textfield): any phenotypes associated with this annotation
        created(datetimefield): time when the annotation was created
        last_modified(datetimefield): time when the annotation was last modified

    """
    SNP_OR_INDEL = 'SNP_INDEL'
    DATABASE = 'DATABASE'
    LOST_PHENOTYPE = 'PHEN'
    OTHER = 'OTHER'
    TYPE_CHOICES = (
        (SNP_OR_INDEL, 'SNP or Insert/Deletion Annotation'),
        (DATABASE, 'Database Annotation'),
        (LOST_PHENOTYPE, 'Phenotype Annotation not associated with a SNP or INDEL or database annotation'),
        (OTHER, 'Other type of Annotation'),
    )
    tile_variant = models.ForeignKey(TileVariant, related_name='annotations', db_index=True)
    annotation_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    source = models.CharField(max_length=100)
    annotation_text = models.TextField()
    phenotype = models.TextField(blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    def __unicode__(self):
        typeIndex = [i for i,j in self.TYPE_CHOICES]
        humanReadable = self.TYPE_CHOICES[typeIndex.index(self.annotation_type)][1]
        return self.tile_variant.getString() + ": " + humanReadable
    class Meta:
        #Ensures ordering by tilename
        ordering = ['tile_variant']

class TileLocusAnnotation(models.Model):
    """
    Implements mapping to enable translations between assembly loci and tile id

    Example input from FASTJ:
        Tile x  : {"build":"hg19 chr9 135900000-24 135900225"} => begin_int: 135899976; end_int: 135900225
        Tile x+1: {"build":"hg19 chr9 135900201 135900450"} => begin_int: 135900201; end_int: 135900450
    begin_int: max(0, eval(input["build"][2]))
    end_int: eval(input["build"][3])

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
    tile = models.ForeignKey(Tile, related_name="tile_locus_annotations")
    def __unicode__(self):
        assembly_index = [i for i,j in self.SUPPORTED_ASSEMBLY_CHOICES]
        humanReadable = self.SUPPORTED_ASSEMBLY_CHOICES[assembly_index.index(self.assembly)][1]
        return self.tile.getTileString() + ": " + humanReadable + " Translation"
    class Meta:
        #Ensures ordering by tilename
        ordering = ['tile']
