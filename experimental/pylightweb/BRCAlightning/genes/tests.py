from django.test import TestCase, LiveServerTestCase
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
import random
import string
import hashlib

import genes.functions as fns
from genes.models import UCSC_Gene, GeneXRef
from tile_library.models import Tile, TileVariant, TileLocusAnnotation
import tile_library.basic_functions as basic_fns

def mk_gene_xref(gene, random_letters, alias):
    g = GeneXRef(gene=gene,mrna=random_letters, sp_id=random_letters, sp_display_id=random_letters,
                 gene_aliases=alias, ref_seq=random_letters, description=random_letters, rfam_acc=random_letters,
                 trna_name=random_letters, has_gene_review=False)
    g.save()


def make_gene1():
    """(Assembly 19, chr1)
              gene1: 500   |___|       |_____|   2000
                          600-700     1100-1900
    gene1 (by tile): 1    1                5     5
    """
    random_letters = 'foo'
    g = UCSC_Gene(ucsc_gene_id=random_letters, assembly=19, chrom=1, strand=True, start_tx=500,
                           tile_start_tx=1, end_tx=2000, tile_end_tx=5, start_cds=600,
                           tile_start_cds=1, end_cds=1900, tile_end_cds=5, exon_count=2,
                           exon_starts='600,1100', exon_ends='700, 1900', uniprot_display_id=random_letters,
                           align_id=random_letters)
    g.save()
    mk_gene_xref(g, random_letters, 'gene1')

def make_gene1pt5():
    """ gene1pt5 overlaps gene1 (it's a splicing variant)
        (Assembly 19, chr1)
              gene1.5: 500   |___|    |___|    |____|         2000
                            600-700  800-900  1100-1500
    gene1.5 (by tile): 1    1                      4          5
    """
    random_letters = 'foo1.5'
    g = UCSC_Gene(ucsc_gene_id=random_letters, assembly=19, chrom=1, strand=True,
                  start_tx=500, tile_start_tx=1, end_tx=2000, tile_end_tx=5,
                  start_cds=600, tile_start_cds=1, end_cds=1500, tile_end_cds=4,
                  exon_count=2, exon_starts='600,800,1100', exon_ends='700, 900, 1475',
                  uniprot_display_id=random_letters, align_id=random_letters)
    g.save()
    
    mk_gene_xref(g, random_letters, 'gene1')
    
def make_diff_assembly():
    """ (Assembly 18, chr1)
              gene1: 500   |___|       |____|   2000
                          600-700     1100-1900
    gene1 (by tile): 1    1                5    5
    """
    random_letters = 'bar'
    g = UCSC_Gene(ucsc_gene_id=random_letters, assembly=18, chrom=1, strand=True, start_tx=500,
                           tile_start_tx=1, end_tx=2000, tile_end_tx=5, start_cds=600,
                           tile_start_cds=1, end_cds=1900, tile_end_cds=5, exon_count=2,
                           exon_starts='600,1100', exon_ends='700, 1900', uniprot_display_id=random_letters,
                           align_id=random_letters)
    g.save()
    mk_gene_xref(g, random_letters, 'gene1')
    
def make_chr2_gene():
    """ (Assembly 19, chr2)
              gene1: 500    |___|       |____|    2000
                           600-700     1100-1900
    gene1 (by tile): 1000  1000             1005  1005
    """
    chr2 = UCSC_Gene(ucsc_gene_id='bar2', assembly=19, chrom=2, strand=True, start_tx=500,
                           tile_start_tx=1000, end_tx=2000, tile_end_tx=1005, start_cds=600,
                           tile_start_cds=1000, end_cds=1900, tile_end_cds=1005, exon_count=2,
                           exon_starts='600,1100', exon_ends='700, 1900', uniprot_display_id='bar2',
                           align_id='bar2')
    chr2.save()
    mk_gene_xref(chr2, 'bar2', 'gene1')
    
def make_gene2():
    """ gene2 does not overlap gene1 in start_tx
        gene2 overlaps gene1 by tile
        (Assembly 19, chr1)
              gene1: 2001   |____|    2500
                           2050-2400
    gene1 (by tile): 5     6    7     8
    """
    gene2_ucsc = UCSC_Gene(ucsc_gene_id='foo1', assembly=19, chrom=1, strand=True, start_tx=2001,
                           tile_start_tx=5, end_tx=2500, tile_end_tx=8, start_cds=2050,
                           tile_start_cds=6, end_cds=2400, tile_end_cds=7, exon_count=1,
                           exon_starts='2050', exon_ends='2400', uniprot_display_id='foo1',
                           align_id='foo1')
    gene2_ucsc.save()
    mk_gene_xref(gene2_ucsc, 'foo1', 'gene2')
def make_gene3():
    """ gene3 overlaps gene1 and gene2 
        (Assembly 19, chr1)
              gene1: 1901   |____|    2399
                           2050-2300
    gene1 (by tile): 5     6    7     7
    """
    #gene3 (overlaps gene1 and gene2)
    gene3_ucsc = UCSC_Gene(ucsc_gene_id='foo2', assembly=19, chrom=1, strand=True, start_tx=1901,
                           tile_start_tx=5, end_tx=2399, tile_end_tx=7, start_cds=2050,
                           tile_start_cds=6, end_cds=2300, tile_end_cds=7, exon_count=1,
                           exon_starts='2050', exon_ends='2300', uniprot_display_id='foo2',
                           align_id='foo2')
    gene3_ucsc.save()
    mk_gene_xref(gene3_ucsc, 'foo2', 'gene3')
def make_gene4():
    """ gene4 overlaps gene2, not gene3,gene1, or gene1.5 
        (Assembly 19, chr1)
              gene1: 2450   |____|    2550
                           2460-2550
    gene1 (by tile): 8     8    8     8
    """
    
    gene4_ucsc = UCSC_Gene(ucsc_gene_id='foo4', assembly=19, chrom=1, strand=True, start_tx=2450,
                           tile_start_tx=8, end_tx=2550, tile_end_tx=8, start_cds=2460,
                           tile_start_cds=8, end_cds=2550, tile_end_cds=8, exon_count=1,
                           exon_starts='2460', exon_ends='2550', uniprot_display_id='foo4',
                           align_id='foo4')
    gene4_ucsc.save()
    mk_gene_xref(gene4_ucsc, 'foo4', 'gene4')



def make_tiles(assembly_default=19):
    def mk_genome_seq(length, uppercase=True):
        if uppercase:
            choices = ['A','G','C','T']
        else:
            choices = ['a','g','c','t']
        s = ''
        for i in range(length):
            s += random.choice(choices)
        return s

    def mk_tile(tile_int, start_pos, end_pos, start_tag=None, end_tag=None, assembly=19, chrom=1):
        if start_tag == None:
            start_tag = mk_genome_seq(24)
        if end_tag == None:
            end_tag = mk_genome_seq(24)
        new = Tile(tilename=tile_int, start_tag=start_tag, end_tag=end_tag)
        new.save()
        locus = TileLocusAnnotation(assembly=assembly, chromosome=chrom, begin_int=start_pos, end_int=end_pos, tile=new)
        locus.save()
        mk_tilevars(1, [end_pos-start_pos], start_tag, end_tag, new, tile_int)
        return new, start_tag, end_tag, locus

    def mk_tilevars(num_vars, lengths, start_tag, end_tag, tile, tile_int):
        assert len(lengths) == num_vars
        for i in range(num_vars):
            tile_hex = string.join(basic_fns.convert_position_int_to_position_hex_str(tile_int), "")
            tile_hex += hex(i).lstrip('0x').zfill(3)
            tile_var_int = int(tile_hex, 16)
            length = lengths[i]
            randseq_len = length - 24*2
            seq = start_tag
            seq += mk_genome_seq(randseq_len, uppercase=False)
            seq += end_tag
            digestor = hashlib.new('md5', seq)
            new = TileVariant(tile_variant_name=tile_var_int, tile=tile, variant_value=i, length=length,
                              md5sum=digestor.hexdigest(), sequence=seq, num_positions_spanned=1)
            new.save()
    
    loci = [(0, 448),    #0
            (448-24, 725),#1
            (725-24, 974),#2
            (974-24, 1099),#3
            (1099-24,1500),#4
            (1500-24,2025),#5
            (2025-24,2200),#6
            (2200-24,2425),#7
            (2425-24,2600),#8
            ]
    t, foo, new_start_tag, annotation = mk_tile(0, loci[0][0], loci[0][1], assembly=assembly_default)
    for i in range(1, 9):
        t, foo, new_start_tag, annotation = mk_tile(i, loci[i][0], loci[i][1], start_tag=new_start_tag, assembly=assembly_default)
    t, foo, new_start_tag, annotation = mk_tile(1000, loci[0][0], loci[0][1], assembly=assembly_default, chrom=2)
    for i in range(1, 5):
        t, foo, new_start_tag, annotation = mk_tile(i+1000, loci[i][0], loci[i][1], start_tag=new_start_tag,
                                                    assembly=assembly_default, chrom=2)

######################### TEST functions ###################################
class TestFunctions(TestCase):
    def test_color_empty_exons(self):
        exons = []
        colors = fns.color_exons(exons, 0, 100)
        self.assertEqual(colors, [(100, 0)])
    def test_color_one_exon(self):
        #Beginning
        exons = [(0, 75)]
        colors = fns.color_exons(exons, 0, 100)
        self.assertEqual(colors, [(0, 75), (25, 0)])
        #Middle
        exons = [(25, 75)]
        colors = fns.color_exons(exons, 0, 100)
        self.assertEqual(colors, [(25, 50), (25, 0)])
        #End
        exons = [(75, 100)]
        colors = fns.color_exons(exons, 0, 100)
        self.assertEqual(colors, [(75, 25), (0, 0)])
    def test_color_two_exons(self):
        #Beginning next to each other (same size)
        exons = [(0, 10), (10, 20)]
        colors = fns.color_exons(exons, 0, 100)
        self.assertEqual(colors, [(0, 10), (0, 10), (80, 0)])
        #Beginning and middle (different sizes)
        exons = [(0, 10), (20, 35)]
        colors = fns.color_exons(exons, 0, 100)
        self.assertEqual(colors, [(0, 10), (10, 15), (65, 0)])
        #Beginning and end (different sizes)
        exons = [(0, 10), (95, 100)]
        colors = fns.color_exons(exons, 0, 100)
        self.assertEqual(colors, [(0, 10), (85, 5), (0, 0)])
        #Middle next to each other (different sizes)
        exons = [(25, 75), (75, 80)]
        colors = fns.color_exons(exons, 0, 100)
        self.assertEqual(colors, [(25, 50), (0, 5), (20, 0)])
        #Middle and middle (same sizes)
        exons = [(25, 50), (70, 95)]
        colors = fns.color_exons(exons, 0, 100)
        self.assertEqual(colors, [(25, 25), (20, 25), (5, 0)])
        #Middle and end (different sizes)
        exons = [(25, 75), (90, 100)]
        colors = fns.color_exons(exons, 0, 100)
        self.assertEqual(colors, [(25, 50), (15, 10), (0, 0)])
        #End next to each other (different sizes)
        exons = [(75, 90), (90, 100)]
        colors = fns.color_exons(exons, 0, 100)
        self.assertEqual(colors, [(75, 15), (0, 10), (0,0)])
    def test_color_exons_wrong_type(self):
        self.assertRaises(AssertionError, fns.color_exons, [], 0.5, '0')
        self.assertRaises(AssertionError, fns.color_exons, [], 0, 0.5)
        self.assertRaises(AssertionError, fns.color_exons, [], 0.5, 0)
        self.assertRaises(AssertionError, fns.color_exons, [], 0, 0)
        self.assertRaises(AssertionError, fns.color_exons, [], -1, 1)
        self.assertRaises(AssertionError, fns.color_exons, [], 2, 1)
    def test_color_exons_poor_exons(self):
        #Exons overlap
        exons = [(0, 10), (9, 11)]
        self.assertRaises(AssertionError, fns.color_exons, exons, 0, 12)
        #Exon start after end
        exons = [(2, 1)]
        self.assertRaises(AssertionError, fns.color_exons, exons, 1, 12)
        exons = [(0, 5), (6, 7)]
        #Exons start before zero
        self.assertRaises(AssertionError, fns.color_exons, exons, 1, 12)
        #Exons end after total
        self.assertRaises(AssertionError, fns.color_exons, exons, 0, 6)
        #Entire exons before zero
        self.assertRaises(AssertionError, fns.color_exons, exons, 10, 12)
        #Entire exons after total
        exons = [(10, 11), (15, 20)]
        self.assertRaises(AssertionError, fns.color_exons, exons, 1, 5)
        
    ####Test Overlap####
    def test_overlap(self):
        #Complete overlap
        self.assertTrue(fns.overlap(0, 1, 0, 1))
        #Half overlap
        self.assertTrue(fns.overlap(0, 2, 1, 4))
        self.assertTrue(fns.overlap(1, 4, 0, 2))
        #No overlap
        self.assertFalse(fns.overlap(0, 3, 5, 6))
        self.assertFalse(fns.overlap(5, 6, 0, 3))
    def test_overlap_wrong_type(self):
        self.assertRaises(AssertionError, fns.overlap, 0.5, 1, 0, 0)
        self.assertRaises(AssertionError, fns.overlap, 0, 0.7, 0, 0)
        self.assertRaises(AssertionError, fns.overlap, 0, 1, 0.5, 1)
        self.assertRaises(AssertionError, fns.overlap, 0, 1, 0, 1.5)
        self.assertRaises(AssertionError, fns.overlap, 1, 0, 0, 1)
        self.assertRaises(AssertionError, fns.overlap, 0, 1, 1, 0)



class TestSplitGenesIntoGroups(TestCase):
    ####Test Split Genes####
    ##These tests enforce an ordering that is not necessary.
    ##The ordering is not really important as long as the genes are correctly matched
    def test_split_genes_into_groups_diff_chrom(self):
        #gene1, gene_chr2
        make_gene1()
        make_chr2_gene()
        genes = GeneXRef.objects.all()
        overlapping_genes = fns.split_genes_into_groups(genes)
        self.assertEqual(len(overlapping_genes),2)
        for i, g in enumerate(overlapping_genes):
            self.assertEqual(len(g),5)
            self.assertEqual(g[0],19)
            self.assertEqual(g[1],i+1)
            self.assertEqual(g[2],500)
            self.assertEqual(g[3],2000)
            self.assertEqual(g[4], genes[i])
    def test_split_genes_into_groups_diff_chrom_by_tile(self):
        #gene1, gene_chr2
        make_gene1()
        make_chr2_gene()
        genes = GeneXRef.objects.all()
        overlapping_genes = fns.split_genes_into_groups(genes, by_tile=True)
        self.assertEqual(len(overlapping_genes),2)
        checks = [{'s':1,'e':5},{'s':1000, 'e':1005}]
        for i, g in enumerate(overlapping_genes):
            self.assertEqual(len(g),5)
            self.assertEqual(g[0],19)
            self.assertEqual(g[1],i+1)
            self.assertEqual(g[2],checks[i]['s'])
            self.assertEqual(g[3],checks[i]['e'])
            self.assertEqual(g[4], genes[i])
    def test_split_genes_into_groups_not_overlapping(self):
        #gene1, gene2
        make_gene1()
        make_gene2()
        genes = GeneXRef.objects.all()
        overlapping_genes = fns.split_genes_into_groups(genes)
        self.assertEqual(len(overlapping_genes),2)
        checks = [{'s':500,'e':2000},{'s':2001, 'e':2500}]
        for i, g in enumerate(overlapping_genes):
            self.assertEqual(len(g),5)
            self.assertEqual(g[0],19)
            self.assertEqual(g[1],1)
            self.assertEqual(g[2],checks[i]['s'])
            self.assertEqual(g[3],checks[i]['e'])
            self.assertEqual(g[4], genes[i])
    def test_split_genes_into_groups_not_overlapping_by_tile(self):
        #gene1, gene2
        make_gene1()
        make_gene2()
        genes = GeneXRef.objects.all()
        overlapping_genes = fns.split_genes_into_groups(genes, by_tile=True)
        self.assertEqual(len(overlapping_genes),1)
        g = overlapping_genes[0]
        self.assertEqual(g[0],19)
        self.assertEqual(g[1],1)
        self.assertEqual(g[2],1)
        self.assertEqual(g[3],8)
        self.assertEqual(len(g[4:]), len(genes))
        self.assertItemsEqual(g[4:], genes)
        
    def test_split_genes_into_groups_actually_not_overlapping_by_tile(self):
        #gene1, gene4
        make_gene1()
        make_gene4()
        genes = GeneXRef.objects.all()
        overlapping_genes = fns.split_genes_into_groups(genes, by_tile=True)
        self.assertEqual(len(overlapping_genes),2)
        checks = [{'s':1,'e':5},{'s':8, 'e':8}]
        for i, g in enumerate(overlapping_genes):
            self.assertEqual(len(g),5)
            self.assertEqual(g[0],19)
            self.assertEqual(g[1],1)
            self.assertEqual(g[2],checks[i]['s'])
            self.assertEqual(g[3],checks[i]['e'])
            self.assertEqual(g[4], genes[i])
        
    def test_split_genes_into_groups_overlapping_only(self):
        #gene1, gene2, gene3
        make_gene1()
        make_gene2()
        make_gene3()
        genes = GeneXRef.objects.all()
        overlapping_genes = fns.split_genes_into_groups(genes)
        self.assertEqual(len(overlapping_genes),1)
        self.assertEqual(overlapping_genes[0][0],19)
        self.assertEqual(overlapping_genes[0][1],1)
        self.assertEqual(overlapping_genes[0][2],500)
        self.assertEqual(overlapping_genes[0][3],2500)
        self.assertEqual(len(overlapping_genes[0][4:]), len(genes))
        self.assertItemsEqual(overlapping_genes[0][4:], genes)

    def test_split_genes_into_groups_overlapping_only_by_tile(self):
        #gene1, gene2, gene3
        make_gene1()
        make_gene2()
        make_gene3()
        genes = GeneXRef.objects.all()
        overlapping_genes = fns.split_genes_into_groups(genes, by_tile=True)
        self.assertEqual(len(overlapping_genes),1)
        self.assertEqual(overlapping_genes[0][0],19)
        self.assertEqual(overlapping_genes[0][1],1)
        self.assertEqual(overlapping_genes[0][2],1)
        self.assertEqual(overlapping_genes[0][3],8)
        self.assertEqual(len(overlapping_genes[0][4:]), len(genes))
        self.assertItemsEqual(overlapping_genes[0][4:], genes)
            
    def test_split_genes_into_groups_overlapping_and_not(self):
        #gene1, gene2, gene4, gene_chr2
        make_gene1()
        make_gene2()
        make_gene4()
        make_chr2_gene()
        genes = GeneXRef.objects.all()
        overlapping_genes = fns.split_genes_into_groups(genes)
        self.assertEqual(len(overlapping_genes),3)
        checks = [{'s':500,'e':2000, 'genes':[GeneXRef.objects.get(gene__ucsc_gene_id='foo')]},
                  {'s':500,'e':2000, 'genes':[GeneXRef.objects.get(gene__ucsc_gene_id='bar2')]},
                  {'s':2001, 'e':2550, 'genes':[GeneXRef.objects.get(gene_aliases='gene2'),
                                                GeneXRef.objects.get(gene_aliases='gene4')]},
                  ]
        for i, g in enumerate(overlapping_genes):
            self.assertEqual(g[0],19)
            if i == 1:
                self.assertEqual(g[1],2)
            else:
                self.assertEqual(g[1],1)
            self.assertEqual(g[2],checks[i]['s'])
            self.assertEqual(g[3],checks[i]['e'])
            self.assertEqual(len(g[4:]), len(checks[i]['genes']))
            self.assertItemsEqual(g[4:], checks[i]['genes'])

    def test_split_genes_into_groups_overlapping_and_not_by_tile(self):
        #gene1, gene2, gene4, gene_chr2
        make_gene1()
        make_gene2()
        make_gene4()
        make_chr2_gene()
        genes = GeneXRef.objects.all()
        overlapping_genes = fns.split_genes_into_groups(genes, by_tile=True)
        self.assertEqual(len(overlapping_genes),2)
        checks = [{'s':1,'e':8, 'genes':[GeneXRef.objects.get(gene__ucsc_gene_id='foo'),
                                         GeneXRef.objects.get(gene_aliases='gene2'),
                                         GeneXRef.objects.get(gene_aliases='gene4')]},
                  {'s':1000,'e':1005, 'genes':[GeneXRef.objects.get(gene__ucsc_gene_id='bar2')]},
                  ]
        for i, g in enumerate(overlapping_genes):
            self.assertEqual(g[0],19)
            if i == 1:
                self.assertEqual(g[1],2)
            else:
                self.assertEqual(g[1],1)
            self.assertEqual(g[2],checks[i]['s'])
            self.assertEqual(g[3],checks[i]['e'])
            self.assertEqual(len(g[4:]), len(checks[i]['genes']))
            self.assertItemsEqual(g[4:], checks[i]['genes'])
    def test_split_genes_into_groups_len_0(self):
        genes = GeneXRef.objects.all()
        overlapping_genes = fns.split_genes_into_groups(genes)
        self.assertEqual(overlapping_genes, [])
    def test_split_genes_into_groups_len_1(self):
        make_gene1()
        genes = GeneXRef.objects.all()
        overlapping_genes = fns.split_genes_into_groups(genes)
        self.assertEqual(len(overlapping_genes), 1)
        self.assertEqual(overlapping_genes[0], [19, 1, 500, 2000, genes[0]])
    #Make sure if all genes are not in the same assembly, an error is thrown
    def test_split_genes_into_groups_diff_assemblies(self):
        make_gene1()
        make_diff_assembly()
        genes = GeneXRef.objects.all()
        self.assertRaises(BaseException, fns.split_genes_into_groups, genes)
    #Make sure non-queryset is not accepted
    def test_split_genes_into_groups_wrong_type_inputs(self):
        make_gene1()
        make_gene2()
        genes = list(GeneXRef.objects.all())
        self.assertRaises(AssertionError, fns.split_genes_into_groups, genes)
        genes = GeneXRef.objects.all()
        self.assertRaises(AssertionError, fns.split_genes_into_groups, genes, by_tile=None)
    #Make sure if wrong type of queryset, error is thrown
    def test_split_genes_into_groups_wrong_query_set(self):
        make_gene1()
        make_gene2()
        make_gene3()
        genes = UCSC_Gene.objects.filter(ucsc_gene_id__icontains='foo')
        self.assertRaises(BaseException, fns.split_genes_into_groups, genes)
        
    
class TestSplitExons(TestCase):
    ####Test Split Exons####
    #####################split_exons_and_get_length#################
    ##These tests also enforce an ordering that is not necessary.
    ##As long as ret_genes is matched with the ordering of all_exons, the ordering of
    ## ret_genes can be fluid

    def test_split_exons_and_get_length_diff_chrom(self):
        #gene1 and chr2
        make_gene1()
        make_chr2_gene()
        genes = GeneXRef.objects.all()
        overlapping_genes = fns.split_genes_into_groups(genes)
        ret_genes, all_exons, len_genes, len_overlapping_genes = fns.split_exons_and_get_length(genes)
        self.assertItemsEqual(genes, ret_genes)
        self.assertEqual(len(ret_genes), len_genes)
        self.assertEqual(len(overlapping_genes), len_overlapping_genes)
        #Since neither of these genes overlap, this should behave as if I just ran color_exons on both of them
        for g, exon_info in zip(ret_genes, all_exons):
            exons = [(600,700),(1100,1900)]
            check_info = fns.color_exons(exons, 500, 2000)
            self.assertEqual(check_info, exon_info)
    def test_split_exons_and_get_length_not_overlapping(self):
        #gene1, gene2
        make_gene1()
        make_gene2()
        genes = GeneXRef.objects.all()
        overlapping_genes = fns.split_genes_into_groups(genes)
        ret_genes, all_exons, len_genes, len_overlapping_genes = fns.split_exons_and_get_length(genes)
        self.assertItemsEqual(genes, ret_genes)
        self.assertEqual(len(ret_genes), len_genes)
        self.assertEqual(len(overlapping_genes), len_overlapping_genes)
        #Since neither of these genes overlap, this should behave as if I just ran color_exons on both of them
        check_exons = [[(600,700),(1100,1900)],
                       [(2050, 2400)]]
        
        for i, (g, exon_info) in enumerate(zip(ret_genes, all_exons)):
            #Check to make sure that the gene and exon info are matching
            begins = g.gene.exon_starts.strip(',').split(',')
            ends = g.gene.exon_ends.strip(',').split(',')
            exons = [(int(b), int(e)) for b, e in zip(begins, ends)]
            self.assertEqual(exons, check_exons[i])
            if i == 0:
                check_info = fns.color_exons(exons, 500, 2000)
            else:
                check_info = fns.color_exons(exons, 2001, 2500)
            self.assertEqual(check_info, exon_info)
    def test_split_exons_and_get_length_overlapping_only(self):
        #gene1, gene2, gene3
        make_gene1()
        make_gene2()
        make_gene3()
        genes = GeneXRef.objects.all()
        overlapping_genes = fns.split_genes_into_groups(genes)
        ret_genes, all_exons, len_genes, len_overlapping_genes = fns.split_exons_and_get_length(genes)
        self.assertItemsEqual(genes, ret_genes)
        self.assertEqual(len(ret_genes), len_genes)
        self.assertEqual(len(overlapping_genes), len_overlapping_genes)
        check_exons = [[(600,700),(1100,1900)],
                       [(2050, 2300)],
                       [(2050, 2400)]]
        #All 3 genes interlap, run color exons with the minimum start_tx and maximum end_tx as zero and total
        for i, (g, exon_info) in enumerate(zip(ret_genes, all_exons)):
            #Check to make sure that the gene and exon info are matching
            begins = g.gene.exon_starts.strip(',').split(',')
            ends = g.gene.exon_ends.strip(',').split(',')
            exons = [(int(b), int(e)) for b, e in zip(begins, ends)]
            self.assertEqual(exons, check_exons[i])
            check_info = fns.color_exons(exons, 500, 2500)
            self.assertEqual(check_info, exon_info)

    def test_split_exons_and_get_length_overlapping_and_not(self):
        #gene1, gene2, gene4, gene_chr2
        make_gene1()
        make_gene2()
        make_gene4()
        make_chr2_gene()
        genes = GeneXRef.objects.all()
        overlapping_genes = fns.split_genes_into_groups(genes)
        ret_genes, all_exons, len_genes, len_overlapping_genes = fns.split_exons_and_get_length(genes)
        self.assertItemsEqual(genes, ret_genes)
        self.assertEqual(len(ret_genes), len_genes)
        self.assertEqual(len(overlapping_genes), len_overlapping_genes)
        check_exons = [[(600,700),(1100,1900)],
                       [(600,700),(1100,1900)],
                       [(2050, 2400)],
                       [(2460, 2550)],
                       ]
        ranges = [{'s':500, 'e':2000},
                  {'s':500, 'e':2000},
                  {'s':2001, 'e':2550},
                  {'s':2001, 'e':2550},
                  ]
        for i, (g, exon_info) in enumerate(zip(ret_genes, all_exons)):
            #Check to make sure that the gene and exon info are matching
            begins = g.gene.exon_starts.strip(',').split(',')
            ends = g.gene.exon_ends.strip(',').split(',')
            exons = [(int(b), int(e)) for b, e in zip(begins, ends)]
            self.assertEqual(exons, check_exons[i])
            check_info = fns.color_exons(exons, ranges[i]['s'], ranges[i]['e'])
            self.assertEqual(check_info, exon_info)
    def test_split_exons_and_get_length_len_0(self):
        genes = GeneXRef.objects.all()
        overlapping_genes = fns.split_genes_into_groups(genes)
        ret_genes, all_exons, len_genes, len_overlapping_genes = fns.split_exons_and_get_length(genes)
        self.assertItemsEqual(genes, ret_genes)
        self.assertEqual(len(ret_genes), len_genes)
        self.assertEqual(len(overlapping_genes), len_overlapping_genes)
        self.assertEqual(all_exons, [])
    def test_split_exons_and_get_length_len_1(self):
        make_gene1()
        genes = GeneXRef.objects.all()
        overlapping_genes = fns.split_genes_into_groups(genes)
        ret_genes, all_exons, len_genes, len_overlapping_genes = fns.split_exons_and_get_length(genes)
        self.assertItemsEqual(genes, ret_genes)
        self.assertEqual(len(ret_genes), len_genes)
        self.assertEqual(len(overlapping_genes), len_overlapping_genes)
        check_exons = [[(600,700),(1100,1900)]]
        for i, (g, exon_info) in enumerate(zip(ret_genes, all_exons)):
            #Check to make sure that the gene and exon info are matching
            begins = g.gene.exon_starts.strip(',').split(',')
            ends = g.gene.exon_ends.strip(',').split(',')
            exons = [(int(b), int(e)) for b, e in zip(begins, ends)]
            self.assertEqual(exons, check_exons[i])
            check_info = fns.color_exons(exons, 500, 2000)
            self.assertEqual(check_info, exon_info)
    #Make sure if all genes are not in the same assembly, an error is thrown
    def test_split_exons_and_get_length_diff_assemblies(self):
        make_gene1()
        make_diff_assembly()
        genes = GeneXRef.objects.all()
        self.assertRaises(BaseException, fns.split_exons_and_get_length, genes)
    #Make sure non-queryset is not accepted
    def test_split_exons_and_get_length_wrong_type_inputs(self):
        make_gene1()
        make_gene2()
        genes = list(GeneXRef.objects.all())
        self.assertRaises(AssertionError, fns.split_exons_and_get_length, genes)
    #Make sure if wrong type of queryset, error is thrown
    def test_split_exons_and_get_length_wrong_query_set(self):
        make_gene1()
        make_gene2()
        make_gene3()
        genes = UCSC_Gene.objects.filter(ucsc_gene_id='foo')
        self.assertRaises(BaseException, fns.split_exons_and_get_length, genes)


class TestAnnotatePositionsWithExonsOverlappingGenes(TestCase):
    ####Test Annotate Positions With Exons Overlapping Genes####
    def test_annotate_positions_no_genes(self):
        make_tiles()
        positions = Tile.objects.filter(tilename__range=(0,9))
        genes = GeneXRef.objects.all()
        overlapping_genes = fns.split_genes_into_groups(genes)
        exon_dict = fns.annotate_positions_with_exons_overlapping_genes(overlapping_genes, positions)
        self.assertEqual(len(exon_dict), len(positions))
        for pos in positions:
            name = int(pos.tilename)
            self.assertFalse(exon_dict[name])

    def test_annotate_positions_gene_one(self):
        make_tiles()
        make_gene1()
        positions = Tile.objects.filter(tilename__range=(0,9))
        genes = GeneXRef.objects.all()
        overlapping_genes = fns.split_genes_into_groups(genes)
        exon_dict = fns.annotate_positions_with_exons_overlapping_genes(overlapping_genes, positions)
        self.assertEqual(len(exon_dict), len(positions))
        check_dict = {0:False, 1:True, 2:False, 3:False, 4:True, 5:True,
                      6:False, 7:False, 8:False}
        for pos in positions:
            name = int(pos.tilename)
            self.assertEqual(exon_dict[name], check_dict[name])
            
    def test_annotate_positions_gene_one_pt_five(self):
        make_tiles()
        make_gene1pt5()
        positions = Tile.objects.filter(tilename__range=(0,9))
        genes = GeneXRef.objects.all()
        overlapping_genes = fns.split_genes_into_groups(genes)
        exon_dict = fns.annotate_positions_with_exons_overlapping_genes(overlapping_genes, positions)
        self.assertEqual(len(exon_dict), len(positions))
        check_dict = {0:False, 1:True, 2:True, 3:False, 4:True, 5:False,
                      6:False, 7:False, 8:False}
        for pos in positions:
            name = int(pos.tilename)
            self.assertEqual(exon_dict[name], check_dict[name])

    def test_annotate_positions_both_splice_variants(self):
        #Should be the "OR" of the previous two check_dict's
        make_tiles()
        make_gene1()
        make_gene1pt5()
        positions = Tile.objects.filter(tilename__range=(0,9))
        genes = GeneXRef.objects.all()
        overlapping_genes = fns.split_genes_into_groups(genes)
        exon_dict = fns.annotate_positions_with_exons_overlapping_genes(overlapping_genes, positions)
        self.assertEqual(len(exon_dict), len(positions))
        check_dict = {0:False, 1:True, 2:True, 3:False, 4:True, 5:True,
                      6:False, 7:False, 8:False}
        for pos in positions:
            name = int(pos.tilename)
            self.assertEqual(exon_dict[name], check_dict[name])

    def test_annotate_positions_gene_four(self):
        make_tiles()
        make_gene4()
        genes = GeneXRef.objects.all()
        overlapping_genes = fns.split_genes_into_groups(genes)
        positions = Tile.objects.filter(tilename__range=(0,9))
        exon_dict = fns.annotate_positions_with_exons_overlapping_genes(overlapping_genes, positions)
        self.assertEqual(len(exon_dict), len(positions))
        check_dict = {0:False, 1:False, 2:False, 3:False, 4:False, 5:False,
                      6:False, 7:False, 8:True}
        for pos in positions:
            name = int(pos.tilename)
            self.assertEqual(exon_dict[name], check_dict[name])

    def test_annotate_positions_gene_two(self):
        make_tiles()
        make_gene2()
        genes = GeneXRef.objects.all()
        overlapping_genes = fns.split_genes_into_groups(genes)
        positions = Tile.objects.filter(tilename__range=(0,9))
        exon_dict = fns.annotate_positions_with_exons_overlapping_genes(overlapping_genes, positions)
        self.assertEqual(len(exon_dict), len(positions))
        check_dict = {0:False, 1:False, 2:False, 3:False, 4:False, 5:False,
                      6:True, 7:True, 8:False}
        for pos in positions:
            name = int(pos.tilename)
            self.assertEqual(exon_dict[name], check_dict[name])

    def test_annotate_positions_gene_three(self):
        make_tiles()
        make_gene3()
        genes = GeneXRef.objects.all()
        overlapping_genes = fns.split_genes_into_groups(genes)
        positions = Tile.objects.filter(tilename__range=(0,9))
        exon_dict = fns.annotate_positions_with_exons_overlapping_genes(overlapping_genes, positions)
        self.assertEqual(len(exon_dict), len(positions))
        check_dict = {0:False, 1:False, 2:False, 3:False, 4:False, 5:False,
                      6:True, 7:True, 8:False}
        for pos in positions:
            name = int(pos.tilename)
            self.assertEqual(exon_dict[name], check_dict[name])

    def test_annotate_positions_gene_two_and_three(self):
        make_tiles()
        make_gene2()
        make_gene3()
        genes = GeneXRef.objects.all()
        overlapping_genes = fns.split_genes_into_groups(genes)
        positions = Tile.objects.filter(tilename__range=(0,9))
        exon_dict = fns.annotate_positions_with_exons_overlapping_genes(overlapping_genes, positions)
        self.assertEqual(len(exon_dict), len(positions))
        check_dict = {0:False, 1:False, 2:False, 3:False, 4:False, 5:False,
                      6:True, 7:True, 8:False}
        for pos in positions:
            name = int(pos.tilename)
            self.assertEqual(exon_dict[name], check_dict[name])

    def test_annotate_positions_later_genes(self):
        make_tiles()
        make_gene2()
        make_gene3()
        make_gene4()
        genes = GeneXRef.objects.all()
        overlapping_genes = fns.split_genes_into_groups(genes)
        positions = Tile.objects.filter(tilename__range=(0,9))
        exon_dict = fns.annotate_positions_with_exons_overlapping_genes(overlapping_genes, positions)
        self.assertEqual(len(exon_dict), len(positions))
        check_dict = {0:False, 1:False, 2:False, 3:False, 4:False, 5:False,
                      6:True, 7:True, 8:True}
        for pos in positions:
            name = int(pos.tilename)
            self.assertEqual(exon_dict[name], check_dict[name])
        
    def test_annotate_positions_all_genes(self):
        make_tiles()
        make_gene1()
        make_gene2()
        make_gene3()
        make_gene4()
        genes = GeneXRef.objects.all()
        overlapping_genes = fns.split_genes_into_groups(genes)
        positions = Tile.objects.filter(tilename__range=(0,9))
        exon_dict = fns.annotate_positions_with_exons_overlapping_genes(overlapping_genes, positions)
        self.assertEqual(len(exon_dict), len(positions))
        check_dict = {0:False, 1:True, 2:False, 3:False, 4:True, 5:True,
                      6:True, 7:True, 8:True}
        for pos in positions:
            name = int(pos.tilename)
            self.assertEqual(exon_dict[name], check_dict[name])
    
    #Error checking
    #Requires overlapping_genes to run, so assembly checking of the genes is not necessary
    #Make sure wrongly-formatted overlapping_genes is not accepted
    def test_annotate_positions_wrong_format_overlapping_genes(self):
        make_tiles()
        make_gene1()
        make_gene2()
        make_gene3()
        genes = GeneXRef.objects.all()
        positions = Tile.objects.all()
        self.assertRaises(AssertionError, fns.annotate_positions_with_exons_overlapping_genes, genes, positions)
        genes = UCSC_Gene.objects.filter(ucsc_gene_id='foo')
        self.assertRaises(AssertionError, fns.annotate_positions_with_exons_overlapping_genes, genes, positions)
        oops = [1, 1, 0, 15]
        oops.extend(list(genes))
        self.assertRaises(AssertionError, fns.annotate_positions_with_exons_overlapping_genes, oops, positions)
        oops[0] = 19
        oops[1] = 0
        self.assertRaises(AssertionError, fns.annotate_positions_with_exons_overlapping_genes, oops, positions)
        oops[1] = 1
        oops[2] = '100'
        self.assertRaises(AssertionError, fns.annotate_positions_with_exons_overlapping_genes, oops, positions)
        oops[2] = 100
        oops[3] = '15'
        self.assertRaises(AssertionError, fns.annotate_positions_with_exons_overlapping_genes, oops, positions)
        oops[3] = 15
        self.assertRaises(AssertionError, fns.annotate_positions_with_exons_overlapping_genes, oops, positions)
        oops[4] = 'whee'
        self.assertRaises(AssertionError, fns.annotate_positions_with_exons_overlapping_genes, oops, positions)

    #Make sure an error is thrown if positions is not a queryset 
    def test_annotate_positions_wrong_format_positions(self):
        make_tiles()
        make_gene1()
        make_gene2()
        make_gene3()
        genes = GeneXRef.objects.all()
        overlapping_genes = fns.split_genes_into_groups(genes)
        positions = list(Tile.objects.all())
        self.assertRaises(AssertionError, fns.annotate_positions_with_exons_overlapping_genes, overlapping_genes, positions)
        
    #Make sure an error is thrown if positions is a queryset of the wrong type
    def test_annotate_positions_wrong_queryset_positions(self):
        make_tiles()
        make_gene1()
        make_gene2()
        make_gene3()
        genes = GeneXRef.objects.all()
        overlapping_genes = fns.split_genes_into_groups(genes)
        positions = TileVariant.objects.all()
        self.assertRaises(AssertionError, fns.annotate_positions_with_exons_overlapping_genes, overlapping_genes, positions)

    #If genes do not overlap, an error is thrown
    def test_annotate_positions_non_overlapping_genes(self):
        make_tiles()
        make_gene1()
        make_gene4()
        genes = GeneXRef.objects.all()
        overlapping_genes = fns.split_genes_into_groups(genes)
        positions = Tile.objects.all()
        self.assertRaises(AssertionError, fns.annotate_positions_with_exons_overlapping_genes, overlapping_genes, positions)
    
    #If genes are on different chromosomes, throw error
    def test_annotate_positions_diff_chrom(self):
        make_tiles()
        make_gene1()
        make_chr2_gene()
        genes = GeneXRef.objects.all()
        overlapping_genes = fns.split_genes_into_groups(genes)
        positions = Tile.objects.all()
        self.assertRaises(AssertionError, fns.annotate_positions_with_exons_overlapping_genes, overlapping_genes, positions)

    #If positions don't have TileLocusAnnotations in the correct Assembly, throw error
    def test_annotate_positions_wrong_tile_locus_annotations(self):
        make_tiles(assembly_default=18)
        make_gene1()
        make_gene2()
        make_gene3()
        genes = GeneXRef.objects.all()
        overlapping_genes = fns.split_genes_into_groups(genes)
        positions = Tile.objects.all()
        self.assertRaises(BaseException, fns.annotate_positions_with_exons_overlapping_genes, overlapping_genes, positions)


class TestAnnotatePositionsWithExons(TestCase):
    def test_annotate_positions_no_genes(self):
        make_tiles()
        positions = Tile.objects.filter(tilename__range=(0,9))
        genes = GeneXRef.objects.all()
        exon_dict = fns.annotate_positions_with_exons(genes, positions)
        self.assertEqual(len(exon_dict), len(positions))
        for pos in positions:
            name = int(pos.tilename)
            self.assertFalse(exon_dict[name])

    def test_annotate_positions_gene_one(self):
        make_tiles()
        make_gene1()
        positions = Tile.objects.filter(tilename__range=(0,9))
        genes = GeneXRef.objects.all()
        exon_dict = fns.annotate_positions_with_exons(genes, positions)
        self.assertEqual(len(exon_dict), len(positions))
        check_dict = {0:False, 1:True, 2:False, 3:False, 4:True, 5:True,
                      6:False, 7:False, 8:False}
        for pos in positions:
            name = int(pos.tilename)
            self.assertEqual(exon_dict[name], check_dict[name])
            
    def test_annotate_positions_gene_one_pt_five(self):
        make_tiles()
        make_gene1pt5()
        positions = Tile.objects.filter(tilename__range=(0,9))
        genes = GeneXRef.objects.all()
        overlapping_genes = fns.split_genes_into_groups(genes)
        exon_dict = fns.annotate_positions_with_exons(genes, positions)
        self.assertEqual(len(exon_dict), len(positions))
        check_dict = {0:False, 1:True, 2:True, 3:False, 4:True, 5:False,
                      6:False, 7:False, 8:False}
        for pos in positions:
            name = int(pos.tilename)
            self.assertEqual(exon_dict[name], check_dict[name])

    def test_annotate_positions_both_splice_variants(self):
        #Should be the "OR" of the previous two check_dict's
        make_tiles()
        make_gene1()
        make_gene1pt5()
        positions = Tile.objects.filter(tilename__range=(0,9))
        genes = GeneXRef.objects.all()
        exon_dict = fns.annotate_positions_with_exons(genes, positions)
        self.assertEqual(len(exon_dict), len(positions))
        check_dict = {0:False, 1:True, 2:True, 3:False, 4:True, 5:True,
                      6:False, 7:False, 8:False}
        for pos in positions:
            name = int(pos.tilename)
            self.assertEqual(exon_dict[name], check_dict[name])

    def test_annotate_positions_gene_four(self):
        make_tiles()
        make_gene4()
        genes = GeneXRef.objects.all()
        positions = Tile.objects.filter(tilename__range=(0,9))
        exon_dict = fns.annotate_positions_with_exons(genes, positions)
        self.assertEqual(len(exon_dict), len(positions))
        check_dict = {0:False, 1:False, 2:False, 3:False, 4:False, 5:False,
                      6:False, 7:False, 8:True}
        for pos in positions:
            name = int(pos.tilename)
            self.assertEqual(exon_dict[name], check_dict[name])

    def test_annotate_positions_gene_two(self):
        make_tiles()
        make_gene2()
        genes = GeneXRef.objects.all()
        positions = Tile.objects.filter(tilename__range=(0,9))
        exon_dict = fns.annotate_positions_with_exons(genes, positions)
        self.assertEqual(len(exon_dict), len(positions))
        check_dict = {0:False, 1:False, 2:False, 3:False, 4:False, 5:False,
                      6:True, 7:True, 8:False}
        for pos in positions:
            name = int(pos.tilename)
            self.assertEqual(exon_dict[name], check_dict[name])

    def test_annotate_positions_gene_three(self):
        make_tiles()
        make_gene3()
        genes = GeneXRef.objects.all()
        positions = Tile.objects.filter(tilename__range=(0,9))
        exon_dict = fns.annotate_positions_with_exons(genes, positions)
        self.assertEqual(len(exon_dict), len(positions))
        check_dict = {0:False, 1:False, 2:False, 3:False, 4:False, 5:False,
                      6:True, 7:True, 8:False}
        for pos in positions:
            name = int(pos.tilename)
            self.assertEqual(exon_dict[name], check_dict[name])

    def test_annotate_positions_gene_two_and_three(self):
        make_tiles()
        make_gene2()
        make_gene3()
        genes = GeneXRef.objects.all()
        positions = Tile.objects.filter(tilename__range=(0,9))
        exon_dict = fns.annotate_positions_with_exons(genes, positions)
        self.assertEqual(len(exon_dict), len(positions))
        check_dict = {0:False, 1:False, 2:False, 3:False, 4:False, 5:False,
                      6:True, 7:True, 8:False}
        for pos in positions:
            name = int(pos.tilename)
            self.assertEqual(exon_dict[name], check_dict[name])

    def test_annotate_positions_later_genes(self):
        make_tiles()
        make_gene2()
        make_gene3()
        make_gene4()
        genes = GeneXRef.objects.all()
        positions = Tile.objects.filter(tilename__range=(0,9))
        exon_dict = fns.annotate_positions_with_exons(genes, positions)
        self.assertEqual(len(exon_dict), len(positions))
        check_dict = {0:False, 1:False, 2:False, 3:False, 4:False, 5:False,
                      6:True, 7:True, 8:True}
        for pos in positions:
            name = int(pos.tilename)
            self.assertEqual(exon_dict[name], check_dict[name])
        
    def test_annotate_positions_all_genes(self):
        make_tiles()
        make_gene1()
        make_gene2()
        make_gene3()
        make_gene4()
        genes = GeneXRef.objects.all()
        positions = Tile.objects.filter(tilename__range=(0,9))
        exon_dict = fns.annotate_positions_with_exons(genes, positions)
        self.assertEqual(len(exon_dict), len(positions))
        check_dict = {0:False, 1:True, 2:False, 3:False, 4:True, 5:True,
                      6:True, 7:True, 8:True}
        for pos in positions:
            name = int(pos.tilename)
            self.assertEqual(exon_dict[name], check_dict[name])

    #Error checking
    #Make sure if all genes are not in the same assembly, an error is thrown
    def test_annotate_positions_gene_diff_assemblies(self):
        make_tiles()
        make_gene1()
        make_diff_assembly()
        positions = Tile.objects.all()
        genes = GeneXRef.objects.all()
        self.assertRaises(BaseException, fns.annotate_positions_with_exons, genes, positions)

    #Make sure if wrong type of gene queryset, error is thrown
    def test_annotate_positions_wrong_genes_query_set(self):
        make_tiles()
        make_gene1()
        make_gene2()
        make_gene3()
        positions = Tile.objects.all()
        genes = UCSC_Gene.objects.filter(ucsc_gene_id__icontains='foo')
        self.assertRaises(BaseException, fns.annotate_positions_with_exons, genes, positions)

    #Make sure gene non-queryset is not accepted
    def test_annotate_positions_wrong_gene_type_inputs(self):
        make_tiles()
        make_gene1()
        make_gene2()
        positions = Tile.objects.all()
        genes = list(GeneXRef.objects.all())
        self.assertRaises(AssertionError, fns.annotate_positions_with_exons, genes, positions)

    #Make sure an error is thrown if positions is a queryset of the wrong type
    def test_annotate_positions_wrong_positions_queryset(self):
        make_tiles()
        make_gene1()
        make_gene2()
        make_gene3()
        genes = GeneXRef.objects.all()
        positions = TileVariant.objects.all()
        self.assertRaises(AssertionError, fns.annotate_positions_with_exons, genes, positions)

    #Make sure an error is thrown if positions is not a queryset 
    def test_annotate_positions_wrong_positions_format(self):
        make_tiles()
        make_gene1()
        make_gene2()
        make_gene3()
        genes = GeneXRef.objects.all()
        positions = list(Tile.objects.all())
        self.assertRaises(AssertionError, fns.annotate_positions_with_exons, genes, positions)

    #If genes do not overlap, an error is thrown
    def test_annotate_positions_non_overlapping_genes(self):
        make_tiles()
        make_gene1()
        make_gene4()
        genes = GeneXRef.objects.all()
        positions = Tile.objects.all()
        self.assertRaises(AssertionError, fns.annotate_positions_with_exons, genes, positions)
    
    #If genes are on different chromosomes, throw error
    def test_annotate_positions_diff_chrom(self):
        make_tiles()
        make_gene1()
        make_chr2_gene()
        genes = GeneXRef.objects.all()
        positions = Tile.objects.all()
        self.assertRaises(AssertionError, fns.annotate_positions_with_exons, genes, positions)

    #If positions don't have TileLocusAnnotations in the correct Assembly, throw error
    def test_annotate_positions_wrong_tile_locus_annotations(self):
        make_tiles(assembly_default=18)
        make_gene1()
        make_gene2()
        make_gene3()
        genes = GeneXRef.objects.all()
        positions = Tile.objects.all()
        self.assertRaises(BaseException, fns.annotate_positions_with_exons, genes, positions)

#######
class TestColorExonParts(TestCase):
    loci = [(0, 448),    #0
            (448-24, 725),#1
            (725-24, 974),#2
            (974-24, 1099),#3
            (1099-24,1500),#4
            (1500-24,2025),#5
            (2025-24,2200),#6
            (2200-24,2425),#7
            (2425-24,2600),#8
            ]
    def test_color_exon_parts_no_genes(self):
        make_tiles()
        genes = GeneXRef.objects.all()
        position = Tile.objects.get(tilename=0)
        has_exons, all_exons = fns.color_exon_parts(genes, position)
        self.assertFalse(has_exons)
        self.assertEqual(all_exons, [])
        position = Tile.objects.get(tilename=1)
        has_exons, all_exons = fns.color_exon_parts(genes, position)
        self.assertFalse(has_exons)
        self.assertEqual(all_exons, [])

    def test_color_exon_parts_gene_one(self):
        make_tiles()
        make_gene1()
        positions = Tile.objects.filter(tilename__range=(0,9))
        genes = GeneXRef.objects.all()
        check = [(False, []), (True, [(600,700)]), (False, []), (False, []), (True, [(1100,1500)]), (True, [(1500-24, 1900)]), (False, []), (False, []), (False, [])] 
        for i, position in enumerate(positions):
            has_exons, all_exons = fns.color_exon_parts(genes, position)
            self.assertEqual(has_exons, check[i][0])
            check_all_exons = []
            for gene in genes:
                check_all_exons.append(fns.color_exons(check[i][1], self.loci[i][0], self.loci[i][1]))
            self.assertItemsEqual(check_all_exons, all_exons)
        
    def test_color_exon_parts_gene_one_assembly_indifference(self):
        make_tiles(assembly_default=18)
        make_diff_assembly()
        positions = Tile.objects.filter(tilename__range=(0,9))
        genes = GeneXRef.objects.all()
        check = [(False, []), (True, [(600,700)]), (False, []), (False, []), (True, [(1100,1500)]), (True, [(1500-24, 1900)]), (False, []), (False, []), (False, [])] 
        for i, position in enumerate(positions):
            has_exons, all_exons = fns.color_exon_parts(genes, position)
            self.assertEqual(has_exons, check[i][0])
            check_all_exons = []
            for gene in genes:
                check_all_exons.append(fns.color_exons(check[i][1], self.loci[i][0], self.loci[i][1]))
            self.assertItemsEqual(check_all_exons, all_exons)
    def test_color_exon_parts_gene_one_pt_five(self):
        make_tiles()
        make_gene1pt5()
        positions = Tile.objects.filter(tilename__range=(0,9))
        genes = GeneXRef.objects.all()
        check = [(False, []), (True, [(600,700)]), (True, [(800,900)]), (False, []), (True, [(1100,1475)]), (False, []), (False, []), (False, []), (False, [])] 
        for i, position in enumerate(positions):
            has_exons, all_exons = fns.color_exon_parts(genes, position)
            self.assertEqual(has_exons, check[i][0])
            check_all_exons = []
            for gene in genes:
                check_all_exons.append(fns.color_exons(check[i][1], self.loci[i][0], self.loci[i][1]))
            self.assertItemsEqual(check_all_exons, all_exons)
    

    def test_color_exon_parts_both_splice_variants(self):
        #Should be the "OR" of the previous two check_dict's
        make_tiles()
        make_gene1()
        make_gene1pt5()
        positions = Tile.objects.filter(tilename__range=(0,9))
        genes = GeneXRef.objects.all()

        check_overall = [False, True, True, False, True, True, False, False, False] 
        check_gene1 = [[], [(600,700)], [], [], [(1100,1500)], [(1500-24, 1900)], [], [], []]
        check_gene1pt5 = [[], [(600,700)], [(800,900)], [], [(1100,1475)], [], [], [], []]
        check = [check_gene1, check_gene1pt5]
        for i, position in enumerate(positions):
            has_exons, all_exons = fns.color_exon_parts(genes, position)
            self.assertEqual(has_exons, check_overall[i])
            check_all_exons = []
            for j, gene in enumerate(genes):
                check_all_exons.append(fns.color_exons(check[j][i], self.loci[i][0], self.loci[i][1]))
            self.assertItemsEqual(check_all_exons, all_exons)

    def test_color_exon_parts_gene_four(self):
        make_tiles()
        make_gene4()
        genes = GeneXRef.objects.all()
        positions = Tile.objects.filter(tilename__range=(0,9))

        check_overall = [False, False, False, False, False, False, False, False, True] 
        check_gene1 = [[], [], [], [], [], [], [], [], [(2460, 2550)]]
        check = [check_gene1]
        for i, position in enumerate(positions):
            has_exons, all_exons = fns.color_exon_parts(genes, position)
            self.assertEqual(has_exons, check_overall[i])
            check_all_exons = []
            for j, gene in enumerate(genes):
                check_all_exons.append(fns.color_exons(check[j][i], self.loci[i][0], self.loci[i][1]))
            self.assertItemsEqual(check_all_exons, all_exons)

    def test_color_exon_parts_gene_two(self):
        make_tiles()
        make_gene2()
        genes = GeneXRef.objects.all()
        positions = Tile.objects.filter(tilename__range=(0,9))

        check_overall = [False, False, False, False, False, False, True, True, False] 
        check_gene1 = [[], [], [], [], [], [], [(2050, 2200)], [(2200-24,2400)], []]
        check = [check_gene1]
        for i, position in enumerate(positions):
            has_exons, all_exons = fns.color_exon_parts(genes, position)
            self.assertEqual(has_exons, check_overall[i])
            check_all_exons = []
            for j, gene in enumerate(genes):
                check_all_exons.append(fns.color_exons(check[j][i], self.loci[i][0], self.loci[i][1]))
            self.assertItemsEqual(check_all_exons, all_exons)

    def test_color_exon_parts_gene_three(self):
        make_tiles()
        make_gene3()
        genes = GeneXRef.objects.all()
        positions = Tile.objects.filter(tilename__range=(0,9))

        check_overall = [False, False, False, False, False, False, True, True, False] 
        check_gene1 = [[], [], [], [], [], [], [(2050, 2200)], [(2200-24,2300)], []]
        check = [check_gene1]
        for i, position in enumerate(positions):
            has_exons, all_exons = fns.color_exon_parts(genes, position)
            self.assertEqual(has_exons, check_overall[i])
            check_all_exons = []
            for j, gene in enumerate(genes):
                check_all_exons.append(fns.color_exons(check[j][i], self.loci[i][0], self.loci[i][1]))
            self.assertItemsEqual(check_all_exons, all_exons)

    def test_color_exon_parts_gene_two_and_three(self):
        make_tiles()
        make_gene2()
        make_gene3()
        genes = GeneXRef.objects.all()
        positions = Tile.objects.filter(tilename__range=(0,9))

        check_overall = [False, False, False, False, False, False, True, True, False] 
        check_gene2 = [[], [], [], [], [], [], [(2050, 2200)], [(2200-24,2400)], []]
        check_gene3 = [[], [], [], [], [], [], [(2050, 2200)], [(2200-24,2300)], []]
        check = [check_gene2, check_gene3]
        for i, position in enumerate(positions):
            has_exons, all_exons = fns.color_exon_parts(genes, position)
            self.assertEqual(has_exons, check_overall[i])
            check_all_exons = []
            for j, gene in enumerate(genes):
                check_all_exons.append(fns.color_exons(check[j][i], self.loci[i][0], self.loci[i][1]))
            self.assertItemsEqual(check_all_exons, all_exons)

    def test_color_exon_parts_later_genes(self):
        make_tiles()
        make_gene2()
        make_gene3()
        make_gene4()
        genes = GeneXRef.objects.all()
        positions = Tile.objects.filter(tilename__range=(0,9))

        check_overall = [False, False, False, False, False, False, True, True, True] 
        check_gene2 = [[], [], [], [], [], [], [(2050, 2200)], [(2200-24,2400)], []]
        check_gene3 = [[], [], [], [], [], [], [(2050, 2200)], [(2200-24,2300)], []]
        check_gene4 = [[], [], [], [], [], [], [], [], [(2460, 2550)]]
        check = [check_gene2, check_gene3, check_gene4]
        for i, position in enumerate(positions):
            has_exons, all_exons = fns.color_exon_parts(genes, position)
            self.assertEqual(has_exons, check_overall[i])
            check_all_exons = []
            for j, gene in enumerate(genes):
                check_all_exons.append(fns.color_exons(check[j][i], self.loci[i][0], self.loci[i][1]))
            self.assertItemsEqual(check_all_exons, all_exons)
        
    def test_color_exon_parts_all_genes(self):
        make_tiles()
        make_gene1()
        make_gene2()
        make_gene3()
        make_gene4()
        genes = GeneXRef.objects.all()
        positions = Tile.objects.filter(tilename__range=(0,9))

        check_overall = [False, True, False, False, True, True, True, True, True]
        check_gene1 = [[], [(600,700)], [], [], [(1100,1500)], [(1500-24, 1900)], [], [], []]
        check_gene2 = [[], [], [], [], [], [], [(2050, 2200)], [(2200-24,2400)], []]
        check_gene3 = [[], [], [], [], [], [], [(2050, 2200)], [(2200-24,2300)], []]
        check_gene4 = [[], [], [], [], [], [], [], [], [(2460, 2550)]]
        check = [check_gene1, check_gene2, check_gene3, check_gene4]
        for i, position in enumerate(positions):
            has_exons, all_exons = fns.color_exon_parts(genes, position)
            self.assertEqual(has_exons, check_overall[i])
            check_all_exons = []
            for j, gene in enumerate(genes):
                check_all_exons.append(fns.color_exons(check[j][i], self.loci[i][0], self.loci[i][1]))
            self.assertItemsEqual(check_all_exons, all_exons)

    def test_color_exon_parts_non_overlapping_genes(self):
        make_tiles()
        make_gene1()
        make_gene4()
        genes = GeneXRef.objects.all()
        positions = Tile.objects.filter(tilename__range=(0,9))
        
        check_overall = [False, True, False, False, True, True, False, False, True]
        check_gene1 = [[], [(600,700)], [], [], [(1100,1500)], [(1500-24, 1900)], [], [], []]
        check_gene4 = [[], [], [], [], [], [], [], [], [(2460, 2550)]]
        check = [check_gene1, check_gene4]
        for i, position in enumerate(positions):
            has_exons, all_exons = fns.color_exon_parts(genes, position)
            self.assertEqual(has_exons, check_overall[i])
            check_all_exons = []
            for j, gene in enumerate(genes):
                check_all_exons.append(fns.color_exons(check[j][i], self.loci[i][0], self.loci[i][1]))
            self.assertItemsEqual(check_all_exons, all_exons)

    #Error checking
    #Make sure if a gene has an unsupported assembly, an error is thrown
    def test_color_exon_parts_diff_assemblies(self):
        make_tiles()
        make_gene1()
        make_diff_assembly()
        position = Tile.objects.get(tilename=0)
        genes = GeneXRef.objects.all()
        self.assertRaises(BaseException, fns.color_exon_parts, genes, position)

    #Make sure if wrong type of gene queryset, error is thrown
    def test_color_exon_parts_wrong_genes_query_set(self):
        make_tiles()
        make_gene1()
        make_gene2()
        make_gene3()
        position = Tile.objects.get(tilename=0)
        genes = UCSC_Gene.objects.filter(ucsc_gene_id__icontains='foo')
        self.assertRaises(BaseException, fns.color_exon_parts, genes, position)

    #Make sure gene non-queryset is not accepted
    def test_color_exon_parts_wrong_gene_type_inputs(self):
        make_tiles()
        make_gene1()
        make_gene2()
        position = Tile.objects.get(tilename=0)
        genes = list(GeneXRef.objects.all())
        self.assertRaises(AssertionError, fns.color_exon_parts, genes, position)

    #Make sure an error is thrown if positions is a queryset
    def test_color_exon_parts_queryset_for_position(self):
        make_tiles()
        make_gene1()
        make_gene2()
        make_gene3()
        genes = GeneXRef.objects.all()
        positions = Tile.objects.all()
        self.assertRaises(AssertionError, fns.color_exon_parts, genes, positions)

    #Make sure an error is thrown if positions is not a Tile
    def test_annotate_positions_wrong_positions_format(self):
        make_tiles()
        make_gene1()
        make_gene2()
        make_gene3()
        genes = GeneXRef.objects.all()
        position = TileVariant.objects.get(tile_variant_name=0)
        self.assertRaises(AssertionError, fns.color_exon_parts, genes, position)
    
    #If genes are on different chromosomes, throw error
    def test_annotate_positions_diff_chrom(self):
        make_tiles()
        make_gene1()
        make_chr2_gene()
        genes = GeneXRef.objects.all()
        position = Tile.objects.get(tilename=0)
        self.assertRaises(AssertionError, fns.color_exon_parts, genes, position)

    #If positions don't have TileLocusAnnotations in the correct Assembly, throw error
    def test_annotate_positions_wrong_tile_locus_annotations(self):
        make_tiles(assembly_default=18)
        make_gene1()
        make_gene2()
        make_gene3()
        genes = GeneXRef.objects.all()
        positions = Tile.objects.all()
        self.assertRaises(BaseException, fns.annotate_positions_with_exons, genes, positions)        


#Gene aliases with odd cases (need to test):
#   abParts
#   5S_rRNA (138 GeneXRef matches, none overlap, multiple chromosomes)
#   CP
