from django.db import models
import string

#TODO: Possibly want to Add a model for Annotations that span tiles. I could also see this working as a function
#TODO: Add lift-over information/function for Tile?
#TODO: Consider adding pointer to png for Tile
#TODO: Possibly add color variant is associated with for TileVariant

class TileManage(models.Manager):
    def get_by_natural_key(self, name):
        return self.get(tilename=name)

class Tile(models.Model):
    """This implementation might benefit from verbose_name field additions
    
    Implements a Tile object. The tilename given must be unique and
    in integer format (not hex)

    tilename: integer of the 9 digit hexidecimal identifier for the tile
        First 3 digits of the hexidecimal identifier indicate the band
        Next 2 digits indicate the path
        Next 4 digits indicate the tile

    This representation guarantees that the supertile, path, and tile ID
    will be present in any tile

    start_tag: start Tag (24 character limit)
    end_tag: end Tag (24 character limit)

    visualization: CommaSeparatedIntegerField, currently allowed to be blank
        because visualization indices can vary without the tile information varying.
        (A,B,C,D): A is x position (which tile in the band), B is y position (which band),
            C is number of pixels along the x-axis the tile covers, D is the number of pixels
            along the y-axis the tile covers

    created: When the tile was generated

    TODO: possible pointer to png
    """
    tilename = models.BigIntegerField(primary_key=True) 
    start_tag = models.CharField(max_length=24)
    end_tag = models.CharField(max_length=24)
    visualization = models.CommaSeparatedIntegerField(max_length=4, blank=True)
    created = models.DateField(auto_now_add=True)
    
    def getTileString(self):
        """Displays hex indexing for tile """
        strTilename = hex(self.tilename)[2:-1] #-1 removes the L (from Long Integer)
        strTilename = strTilename.zfill(9)
        supertile = strTilename[:3]
        path = strTilename[3:5]
        tile = strTilename[5:]
        return string.join([supertile, path, tile, "xxx"], ".")
    getTileString.short_description='Tile Name'
    def __unicode__(self):
        return self.getTileString()
    class Meta:
        ordering = ['tilename']

class TileVariant(models.Model):
    """
    Implements a TileVariant. Each Tile can have many TileVariants. A reference tile is also a TileVariant

    Values in database:
        tile_variant_name (bigint; primary key):Includes the parent tile name to ensure uniqueness.
            xxx.xx.xxxx.xxx. Last three digits indicate the TileVariant value.
            The reference tile has a TileVariant value equal to 000.
        tile (bigint; foreignkey): The parent tile
        length (int; positive): Length of the TileVariant in bases
        population_size (bigint): Number of people in the saved population who have this TileVariant
        md5sum (charfield(40)): The hash for the TileVariant sequence
        last_modified(datefield): The last day the TileVariant was modified
        sequence (textfield): The sequence of the TileVariant
        start_tag (textfield): the start tag of the TileVariant if the start tag varies from tile.start_tag
        end_tag (textfield): the end tag of the TileVariant if the end tag varies from tile.end_tag

    Functions:
        getString(): returns string: human readable tile variant name
        isReference(): returns boolean: True if the variant is the reference variant.
            Depends on tile_variant_name (check if variant is equal to 000)
        getPosition(): returns string: index of self in the list of all tile variants for
            self.tile (sorted by population_size)
        isDefault(): returns boolean: True if the variant is the default for the population.
            Depends on population_size comparison with other TileVariants
        TODO: color of visualization
    """
    
    tile_variant_name = models.BigIntegerField(primary_key=True)
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
        supertile = strTilename[:3]
        path = strTilename[3:5]
        tile = strTilename[5:9]
        var = strTilename[9:]
        return string.join([supertile, path, tile, var], ".")
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
    def __unicode__(self):
        return self.getString()

class TileVarAnnotation(models.Model):
    """Model of Annotations on TileVariants
    Currently one-to-many relation with TileVariant

    tile_variant
    annotation_type indicates what the annotation describes; TYPE_CHOICES is ordered
        by proximity to the DNA sequence
    trusted indicates whether the annotation was generated by a user or the code.
        Could change trusted to a Field that supports choices to have a wider range
        of possible sources: the code that generated it vs people, etc
    annotation_text is the text field of the annotation. Currently, it is completely
        unorganized, which will slow queries down
    created
    last_modified

    """
    SNP_OR_INDEL = 'SNP_INDEL'
    DNA_MODIFICATION = 'DNA_MOD'
    BINDING_SITE = 'BIND'
    PROMOTER = 'PRO'
    EXON_OR_INTRON = 'EXON'
    RNA = 'RNA'
    GENE_PROTEIN = 'GENE'
    HISTONE = 'HIST'
    CHROMATIN_INFORMATION = 'CHROMATIN'
    GROSS_PHENOTYPE = 'PHEN'
    DATABASE = 'DATABASE'
    OTHER = 'OTHER'
    TYPE_CHOICES = (
        (SNP_OR_INDEL, 'SNP or Insert/Deletion Annotation'),
        (DNA_MODIFICATION, 'DNA Modification Annotation'),
        (BINDING_SITE, 'Protein Binding Site Annotation'),
        (PROMOTER, 'Promoter region Annotation'),
        (EXON_OR_INTRON, 'Exon or Intron Annotation'),
        (RNA, 'RNA (including smRNA and mRNA) Annotation'),
        (GENE_PROTEIN, 'Gene and Protein-related Annotation'),
        (HISTONE, 'Histone modification Annotation'),
        (CHROMATIN_INFORMATION, 'Chromatin Annotation'),
        (GROSS_PHENOTYPE, 'Phenotype Annotation'),
        (DATABASE, 'Database Annotation'),
        (OTHER, 'Other Type of Annotation'),
    )
    tile_variant = models.ForeignKey(TileVariant, related_name='annotations')
    annotation_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    trusted = models.BooleanField()
    annotation_text = models.TextField()
    created = models.DateField(auto_now_add=True)
    last_modified = models.DateField(auto_now=True)
    def __unicode__(self):
        typeIndex = [i for i,j in self.TYPE_CHOICES]
        humanReadable = self.TYPE_CHOICES[typeIndex.index(self.annotation_type)][1]
        return humanReadable + ' for ' +  self.tile_variant.getString()

class locusAnnotation(models.Model):
    """Abstract Model of translations between assembly and tiles
    assembly is the integer mapping to the name of the assembly
    chromosome is the integer mapping to the name of the chromosome the tile is associated with
    begin_int is the integer for the beginning
    end_int is the integer for the ending
    chromosome_name is the text for the name of the chromosome if chromosome=26 (OTHER)
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

#YAY! These aren't necessary. We only need to add one locus annotation per tile position (not one per variant)
class varLocusAnnotation(locusAnnotation):
    """Model of translations for a TileVariant
    locus_annotations is the related name for these types of annotations
    """
    tilevar = models.ForeignKey(TileVariant, related_name="locus_annotations")


class tileLocusAnnotation(locusAnnotation):
    """Model of translations for a Tile
    tile_locus_annotations is the related name for these types of annotations
    """
    tile = models.ForeignKey(Tile, related_name="tile_locus_annotations")


    
