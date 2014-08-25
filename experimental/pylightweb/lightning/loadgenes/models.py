from django.db import models

# Create your models here.

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
    
    GENE = 0
    TRANSCRIPT = 1
    EXON = 2
    CDS = 3
    SELENOCYSTEINE = 4
    START_CODON = 5
    STOP_CODON = 6
    UTR = 7

    FEATURE_TYPE_CHOICES = (
        (GENE, 'Gene'),
        (TRANSCRIPT, 'Protein-coding Transcript'),
        (EXON, 'Exon'),
        (CDS, 'Coding Sequence'),
        (SELENOCYSTEINE, 'Contains'),
        (START_CODON, 'RNA (including smRNA and mRNA) Annotation'),
        (STOP_CODON, 'Gene and Protein-related Annotation'),
        (UTR, 'Histone modification Annotation'),
    )
    FRAME_CHOICES = (
        (0, 'The feature begins with a whole codon'),
        (1, '1 extra base at the start of the feature'),
        (2, '2 extra bases at the start of the feature'),
    )
    
    seqname = models.PositiveSmallIntegerField(choices=CHR_CHOICES)
    source = models.CharField(max_length=128)
    feature = models.PositiveSmallIntegerField(choices=FEATURE_TYPE_CHOICES)
    startCGF = models.BigIntegerField()
    endCGF = models.BigIntegerField()
    score = models.FloatField(blank=True)
    strand = models.BooleanField() #True => + ; False => -
    frame = models.PositiveSmallIntegerField(choices=FRAME_CHOICES, blank=True)
    #might want to include the start and end in original coordinates

    #gene_id is used by ensembl as a primary key
    gene_id = models.SlugField(blank=True)
    gene_source = models.CharField(max_length=20, blank=True)
    gene_name = models.CharField(max_length=100, blank=True)
    gene_biotype = models.CharField(max_length=40, blank=True)

    transcript_id = models.SlugField(blank=True)
    transcript_source = models.CharField(max_length=20, blank=True)
    transcript_biotype = models.CharField(max_length=40, blank=True)
    transcript_name = models.CharField(max_length=100, blank=True)

    exon_id = models.SlugField(blank=True)
    exon_number = models.PositiveSmallIntegerField(blank=True)

    protein_id = models.SlugField(blank=True)

