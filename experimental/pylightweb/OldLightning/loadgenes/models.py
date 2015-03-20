from django.db import models

#Annotations that span tiles (taken from loadgenomes):
#    PROMOTER = 'PRO'
#    EXON_OR_INTRON = 'EXON'
#    RNA = 'RNA'
#    GENE_PROTEIN = 'GENE'
#    HISTONE = 'HIST'
#    CHROMATIN_INFORMATION = 'CHROMATIN'
#    PHENOTYPES will also want a presence in loadgenes
#    DNA_MODIFICATION = 'DNA_MOD'
#    BINDING_SITE = 'BIND'
#    OTHER => want to force this to a wider scope and not allow
##        (DNA_MODIFICATION, 'DNA Modification Annotation'),
##        (BINDING_SITE, 'Protein Binding Site Annotation'),
##        (PROMOTER, 'Promoter region Annotation'),
##        (EXON_OR_INTRON, 'Exon or Intron Annotation'),
##        (RNA, 'RNA (including smRNA and mRNA) Annotation'),
##        (GENE_PROTEIN, 'Gene and Protein-related Annotation'),
##        (HISTONE, 'Histone modification Annotation'),
##        (CHROMATIN_INFORMATION, 'Chromatin Annotation'),

class Gene(models.Model):
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
    
    GENE = 'gene'
    TRANSCRIPT = 'transcript'
    EXON = 'exon'
    CDS = 'CDS'
    SELENOCYSTEINE = 'Selenocysteine'
    START_CODON = 'start_codon'
    STOP_CODON = 'end_codon'
    UTR = 'UTR'

    FEATURE_TYPE_CHOICES = (
        (GENE, 'Gene'),
        (TRANSCRIPT, 'Protein-coding Transcript'),
        (EXON, 'Exon'),
        (CDS, 'Coding Sequence'),
        (SELENOCYSTEINE, 'Selenocysteine present at this point'),
        (START_CODON, 'Start codon'),
        (STOP_CODON, 'End codon'),
        (UTR, 'Untranslated region'),
    )
    FRAME_CHOICES = (
        (0, 'The feature begins with a whole codon'),
        (1, '1 extra base at the start of the feature'),
        (2, '2 extra bases at the start of the feature'),
    )
    
    seqname = models.PositiveSmallIntegerField(choices=CHR_CHOICES, verbose_name="Chromosome Location")
    source = models.CharField(max_length=128)
    feature = models.CharField(max_length=50, choices=FEATURE_TYPE_CHOICES)
    startCGF = models.BigIntegerField()
    endCGF = models.BigIntegerField()
    strand = models.BooleanField(verbose_name="On the positive strand") #True => + ; False => -
    score = models.FloatField(blank=True, null=True)
    frame = models.PositiveSmallIntegerField(choices=FRAME_CHOICES, blank=True, null=True)
    #might want to include the start and end in original coordinates

    #gene_id is used by ensembl as a primary key
    gene_id = models.SlugField(blank=True, null=True, verbose_name="Ensembl gene_id")
    gene_source = models.CharField(max_length=20, blank=True, null=True)
    gene_name = models.CharField(max_length=100, blank=True, null=True)
    gene_biotype = models.CharField(max_length=40, blank=True, null=True)

    transcript_id = models.SlugField(blank=True, null=True, verbose_name="Ensembl transcript_id")
    transcript_source = models.CharField(max_length=20, blank=True, null=True)
    transcript_biotype = models.CharField(max_length=40, blank=True, null=True)
    transcript_name = models.CharField(max_length=100, blank=True, null=True)

    exon_id = models.SlugField(blank=True, null=True, verbose_name="Ensembl exon_id")
    exon_number = models.PositiveSmallIntegerField(blank=True, null=True)

    protein_id = models.SlugField(blank=True, null=True, verbose_name="Ensembl protein_id")

    genereview = models.BooleanField(default=False)
    genereviewURLs = models.TextField(blank=True, null=True)
    def getTileCoord(self, CGF):
        """Displays hex indexing for tile """
        strTilename = hex(CGF)[2:-1] #-1 removes the L (from Long Integer)
        strTilename = strTilename.zfill(9)
        path = int(strTilename[:3], 16)
        version = int(strTilename[3:5], 16)
        step = int(strTilename[5:], 16)
        return path, version, step
    getTileCoord.short_description='Get Tile Coordinates'
    def __unicode__(self):
        if len(self.gene_name) > 0:
            return self.gene_name
        else:
            return self.feature + " generated by " + self.source
    class Meta:
        ordering = ['gene_name']
