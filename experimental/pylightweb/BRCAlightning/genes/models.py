"""
Notes: does not use Tile for performance reasons: takes too long to respond
Currently dependent on tile_library.models for TileLocusAnnotation constant definitions

"""

from django.db import models

from tile_library.models import TileLocusAnnotation

class UCSC_Gene(models.Model):
    """
    ucsc_gene_id: (known as kgID by ucsc), UCSC ID of a known gene:
        link to GeneDetail page in UCSC by https://genome.ucsc.edu/cgi-bin/hgGene?hgg_gene=[ucsc_gene_id]
    assembly: Integer mapping used by TileLocusAnnotation to indicate which assembly any base reference uses
    chrom: Integer mapping used by TileLocusAnnotation to indicate which chromosome the gene is on. This is
        not strictly necessary, but will be helpful in translating all locations more specific than tile
    strand: True if on the positive strand, False otherwise
    start_tx: Transcription start position, 0 indexed
    tile_start_tx: tile_id of transcription start position, inclusive. So:
        self.start_tx >= self.tile_start_tx.tile_locus_annotations.get(assembly=self.assembly).begin_int
        AND
        self.start_tx < self.tile_start_tx.tile_locus_annotations.get(assembly=self.assembly).end_int
    end_tx: Transcription end position, 0 indexed
    tile_end_tx: tile_id of transcription end position, inclusive. Follows the same rules as tile_start_tx
    start_cds: coding sequence start position, 0 indexed
    tile_start_cds: tile_id of coding sequence start position, inclusive.
    end_cds: coding sequence end position, 0 indexed
    tile_end_cds: tile_id of coding sequence end position, inclusive.
    exon_count: Number of exons in the gene (length of exon_starts and exon_ends)
    exon_starts: Comma-separated integers of exon start positions, 0 indexed
    exon_ends: Comma-separated integers of exon end positions, 0 indexed
    uniprot_display_id: uniprot display ID for known genes, uniprot accession or RefSeq protein ID for UCSC Genes
    align_id: unique identifier for each (known gene, alignment position) pair
    """
    ucsc_gene_id = models.CharField(max_length=255)
    assembly = models.PositiveSmallIntegerField(choices=TileLocusAnnotation.SUPPORTED_ASSEMBLY_CHOICES)
    chrom = models.PositiveSmallIntegerField(choices=TileLocusAnnotation.CHR_CHOICES, verbose_name="Chromosome Location", db_index=True)
    strand = models.NullBooleanField(verbose_name="On the positive strand") #True => +; False => -; None => unknown
    start_tx = models.PositiveIntegerField()
    tile_start_tx = models.BigIntegerField(db_index=True)
    end_tx = models.PositiveIntegerField()
    tile_end_tx = models.BigIntegerField(db_index=True)
    start_cds = models.PositiveIntegerField()
    tile_start_cds = models.BigIntegerField()
    end_cds = models.PositiveIntegerField()
    tile_end_cds = models.BigIntegerField()
    exon_count = models.PositiveIntegerField()
    exon_starts = models.TextField()
    exon_ends = models.TextField()
    uniprot_display_id = models.CharField(max_length=100)
    align_id = models.CharField(max_length=255)
    def getTileCoordInt(self, tile):
        """Returns integer for path, version, and step for tile """
        strTilename = hex(tile).lstrip('0x').rstrip('L')
        strTilename = strTilename.zfill(9)
        path = int(strTilename[:3], 16)
        version = int(strTilename[3:5], 16)
        step = int(strTilename[5:], 16)
        return path, version, step
    def getTileString(self, tile):
        """Returns human readable string tile """
        strTilename = hex(tile).lstrip('0x').rstrip('L')
        strTilename = strTilename.zfill(9)
        path = strTilename[:3]
        version = strTilename[3:5]
        step = strTilename[5:]
        return string.join([path, version, step], '.')
    getTileString.short_description='Get Tile Coordinates'
    def __unicode__(self):
        try:
            x_ref = self.x_ref
            return x_ref.gene_aliases
        except:
            return self.ucsc_gene_id
    def getNameAndDescription(self):
        try:
            x_ref = self.x_ref
            return x_ref.gene_aliases, x_ref.description
        except:
            return None, None
    def get_description(self):
        try:
            x_ref = self.x_ref
            return x_ref.description
        except:
            return None
    class Meta:
        ordering = ['chrom', 'start_tx']
        verbose_name = "Known Gene: UCSC"
        verbose_name_plural = "Known Genes: UCSC"
##class GeneNames(models.Model):
##    """
##    Table used for search functionality
##    """
##    alias = models.CharField(max_length=40)
##    gene = models.ForeignKey(Gene, related_name="names")

class GeneXRef(models.Model):
    """
    gene: kgID, UCSC ID of a known gene
    mrna: GenBank accession number of the gene's representative mRNA
    sp_id: UniProt (Swiss-Prot/TrEMBL) protein accession number: link by www.uniprot.org/uniprot/[sp_id]
    sp_display_id: UniProt protein display ID
    gene_aliases: GeneName entries (from HUGO or other sources)
    ref_seq: NCBI refseq ID
    prot_acc: NCBI protein accession number
    description: Description of the gene
    rfam_acc: Rfam (RNA family information)
    trna_name: name from tRNA track in UCSC
    """
    gene = models.OneToOneField(UCSC_Gene, related_name="x_ref")
    mrna = models.CharField(max_length=255)
    sp_id = models.CharField(max_length=255)
    sp_display_id = models.CharField(max_length=255)
    gene_aliases = models.CharField(max_length=255, db_index=True)
    ref_seq = models.CharField(max_length=255)
    prot_acc = models.CharField(max_length=255)
    description = models.TextField()
    rfam_acc = models.CharField(max_length=255)
    trna_name = models.CharField(max_length=255)
    has_gene_review = models.BooleanField(default=False)
    gene_review_URLs = models.TextField(blank=True, null=True)
    gene_review_phenotype_map = models.TextField(blank=True, null=True)
    def __unicode__(self):
        return self.gene_aliases
    class Meta:
        #order_with_respect_to = 'gene'
        verbose_name = "Gene database xref"
