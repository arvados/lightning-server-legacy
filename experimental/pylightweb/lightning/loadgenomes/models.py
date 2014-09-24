from django.db import models
import string
import re

#TODO: Possibly want to Add a model for Annotations that span tiles. I could also see this working as a function
#TODO: Add lift-over information/function for Tile?
#TODO: Consider adding pointer to png for Tile
#TODO: Possibly add color the variant is associated with for TileVariant
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
        created(datefield): The day the tile was generated

    Functions:
        getTileString(): returns string: human readable tile variant name
    
    """
    tilename = models.BigIntegerField(primary_key=True, editable=False) 
    start_tag = models.CharField(max_length=24)
    end_tag = models.CharField(max_length=24)
    created = models.DateField(auto_now_add=True)
    
    def getTileString(self):
        """Displays hex indexing for tile """
        strTilename = hex(self.tilename)[2:-1] #-1 removes the L (from Long Integer)
        strTilename = strTilename.zfill(9)
        path = strTilename[:3]
        version = strTilename[3:5]
        step = strTilename[5:]
        return string.join([path, version, step, "xxx"], ".")
    getTileString.short_description='Tile Name'
    def __unicode__(self):
        return self.getTileString()
    class Meta:
        #Ensures ordering by tilename
        ordering = ['tilename']

class TileVariant(models.Model):
    """
    Implements a TileVariant. Each Tile can have many TileVariants (one-to-many relation).
        The reference tile is also a TileVariant with an instance value of 000.
        Note that a tile can be reference and not the default and vice versa,
        since the default is determined by the size of the population containing a tile variant.

    Values in database:
        tile_variant_name (bigint; primary key):Includes the parent tile name to ensure uniqueness.
            xxx.xx.xxxx.xxx. Last three digits indicate the TileVariant value.
            The reference tile has a TileVariant value equal to 000.
        tile (bigint; foreignkey): The parent tile
        length (int; positive): Length of the TileVariant in bases
        population_size (bigint): Number of people in the saved population who have this TileVariant. Each
            person counts for 2 (one for each haplotype)
        md5sum (charfield(40)): The hash for the TileVariant sequence
        last_modified(datefield): The last day the TileVariant was modified
        sequence (textfield): The sequence of the TileVariant
        start_tag (textfield): the start tag of the TileVariant iff the start tag varies from tile.start_tag
        end_tag (textfield): the end tag of the TileVariant iff the end tag varies from tile.end_tag

    Functions:
        getString(): returns string: human readable tile variant name
        isReference(): returns boolean: True if the variant is the reference variant.
            Depends on tile_variant_name (check if variant is equal to 000)
        getPosition(): returns string: index of self in the list of all tile variants for
            self.tile (sorted by population_size)
        isDefault(): returns boolean: True if the variant is the default for the population.
            Depends on population_size comparison with other TileVariants
    
    """
    
    tile_variant_name = models.BigIntegerField(primary_key=True, editable=False)
    tile = models.ForeignKey(Tile, related_name='variants')
    length = models.PositiveIntegerField()
    population_size = models.BigIntegerField()
    md5sum = models.CharField(max_length=40)
    last_modified = models.DateField(auto_now=True)
    sequence = models.TextField()
    start_tag = models.TextField(blank=True)
    end_tag = models.TextField(blank=True)
    
    def getString(self):
        """Displays hex indexing for tile variant"""
        strTilename = hex(self.tile_variant_name)[2:-1] #-1 removes the L (from Long Integer)
        strTilename = strTilename.zfill(12)
        path = strTilename[:3]
        version = strTilename[3:5]
        step = strTilename[5:9]
        var = strTilename[9:]
        return string.join([path, version, step, var], ".")
    getString.short_description='Variant Name'
    def isReference(self):
        strTilename = hex(self.tile_variant_name)[2:-1] #-1 removes the L (from Long Integer)
        strTilename = strTilename.zfill(12)
        var = strTilename[10:]
        return var == '000'
    def getPosition(self):
        allVariants = sorted(self.tile.variants.all(), key=lambda var: var.population_size)
        return str(allVariants.index(self))
    def isDefault(self):
        allVariants = sorted(self.tile.variants.all(), key=lambda var: var.population_size)
        return allVariants.index(self) == 0
    def getSequence(self):
        if re.match('[actgACTGnN\.]+', self.sequence):
            return self.sequence
        elif len(self.sequence) > 0 :
            with open(self.sequence, 'r') as f:
                for line in f:
                    if int(line.split(',')[0]) == self.tile_variant_name:
                        return line.split(',')[6]
        else:
            return None
    def __unicode__(self):
        return self.getString()

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
        created(datefield): date when the annotation was created
        last_modified(datefield): date when the annotation was last modified

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
    tile_variant = models.ForeignKey(TileVariant, related_name='annotations')
    annotation_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    source = models.CharField(max_length=100)
    annotation_text = models.TextField()
    phenotype = models.TextField(blank=True, null=True)
    created = models.DateField(auto_now_add=True)
    last_modified = models.DateField(auto_now=True)
    def __unicode__(self):
        typeIndex = [i for i,j in self.TYPE_CHOICES]
        humanReadable = self.TYPE_CHOICES[typeIndex.index(self.annotation_type)][1]
        return humanReadable + ' for ' +  self.tile_variant.getString()

class LocusAnnotation(models.Model):
    """
    Abstract Model of translations between assembly loci and tile id.
    Implemented by VarLocusAnnotation and TileLocusAnnotation

    Values in database:
        assembly(positive small integer): the integer mapping to the name of the assembly;
            Choices given by SUPPORTED_ASSEMBLY_CHOICES
        chromosome(positive small integer): the integer mapping to the chromosome the tile
            is on; Choices given by CHR_CHOICES
        begin_int(positive int): the beginning base
        end_int(positive int): the ending base
        chromosome_name(charfield(100)): the name of the chromosome if chromosome=26 (OTHER)
    
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
    assembly= models.PositiveSmallIntegerField(choices=SUPPORTED_ASSEMBLY_CHOICES)
    chromosome = models.PositiveSmallIntegerField(choices=CHR_CHOICES)
    begin_int = models.PositiveIntegerField()
    end_int = models.PositiveIntegerField()
    chromosome_name = models.CharField(max_length=100)
    class Meta:
        abstract = True

##This class does not appear necessary. We only need to add one locus annotation per tile position (not one per variant)
##class VarLocusAnnotation(LocusAnnotation):
##    """
##    Implement Tile Variant to Locus mapping
##
##    tilevar(foreignkey): the tile variant associated with this locus annotation
##        locus_annotations: the related name for these annotations
##    
##    """
##    tilevar = models.ForeignKey(TileVariant, related_name="locus_annotations")


class TileLocusAnnotation(LocusAnnotation):
    """
    Implement Tile to Locus mapping

    tile(foreignkey): the tile associated with this locus annotation
        tile_locus_annotations: the related name for these annotations
    
    """
    tile = models.ForeignKey(Tile, related_name="tile_locus_annotations")


    
