import string
import csv

#Read UCSC_Genes (the knownGenes table in UCSC)

loci = []

with open('../tile_library/fixtures/tilelocusannotation.csv') as csvfile:
    reader = csv.reader(csvfile, delimiter=',')
    for line in reader:
        tilename = int(line[0])
        chrom = int(line[2])
        chr_start = int(line[3])
        chr_end = int(line[4])
        loci.append((tilename, chrom, chr_start, chr_end))

loci.sort(key = lambda x: x[0])

def getTileString(tilename):
    strTilename = hex(tilename).lstrip('0x').rstrip('L')
    strTilename = strTilename.zfill(9)
    path = strTilename[:3]
    version = strTilename[3:5]
    step = strTilename[5:]
    return string.join([path, version, step], ".")

def find_tile_id(estimate_i, locus, chrom):
    estimate = loci[estimate_i][0]
    curr_chrom = loci[estimate_i][1]
    while chrom != curr_chrom:
        if chrom > curr_chrom:
            estimate_i += 1
            estimate = loci[estimate_i][0]
            curr_chrom = loci[estimate_i][1]
        elif chrom < curr_chrom:
            estimate_i -= 1
            estimate = loci[estimate_i][0]
            curr_chrom = loci[estimate_i][1]
    begin_int = loci[estimate_i][2]
    end_int = loci[estimate_i][3]
    while locus < begin_int or locus > end_int:
        if curr_chrom != chrom:
            print "Estimate", getTileString(estimate)
            print estimate_i, curr_chrom, chrom, begin_int, end_int, locus
            assert False
        if locus < begin_int:
            estimate_i -= 1
        else:
            estimate_i += 1
        estimate = loci[estimate_i][0]
        begin_int = loci[estimate_i][2]
        end_int = loci[estimate_i][3]
    return estimate, estimate_i


CHR_CHOICES = {
    'chr1': 1,
    'chr2': 2,
    'chr3': 3,
    'chr4': 4,
    'chr5': 5,
    'chr6': 6,
    'chr7': 7,
    'chr8': 8,
    'chr9': 9,
    'chr10': 10,
    'chr11': 11,
    'chr12': 12,
    'chr13': 13,
    'chr14': 14,
    'chr15': 15,
    'chr16': 16,
    'chr17': 17,
    'chr18': 18,
    'chr19': 19,
    'chr20': 20,
    'chr21': 21,
    'chr22': 22,
    'chrX': 23,
    'chrY': 24,
    'chrM': 25,
}

genes_to_add = []

# genes_ucsc_gene table:
#   (id), ucsc_gene_id, assembly, chrom, strand, start_tx, end_tx,
#   start_cds, end_cds, exon_count, exon_starts, exon_ends,
#   uniprot_display_id, align_id, 
#   tile_end_cds_id, tile_end_tx_id, tile_start_cds_id, tile_start_tx_id

# UCSC_Genes:
#   name, chrom, strand, txStart, txEnd, cdsStart, cdsEnd,
#   exonCount, exonStarts, exonEnds, proteinID, alignID

curr_start_i = 0
curr_end_i = 0
with open('hide/UCSC/UCSC_Genes', 'r') as gene_file:
    gene_incr_id = 1
    for line in gene_file:
        if not line.startswith('#'):
            ucsc_gene_id, human_chrom, human_strand, txStart, txEnd, cdsStart, cdsEnd, exonCount, exonStarts, exonEnds, proteinID, alignID = line.strip('\n').split('\t')
            if human_chrom in CHR_CHOICES:
                chrom = CHR_CHOICES[human_chrom]
##            else: #unfortunately, we don't have the loci for odd chromosomes... >.<
##                print line
##                chrom = 26
                if human_strand == '+':
                    strand = 't'
                elif human_strand == '-':
                    strand = 'f'
                else:
                    strand = ''
                tile_start, curr_start_i = find_tile_id(curr_start_i, int(txStart), chrom)
                tile_end, curr_end_i = find_tile_id(curr_end_i, int(txEnd), chrom)
                tile_cds_start, ignore = find_tile_id(curr_start_i, int(cdsStart), chrom)
                tile_cds_end, ignore = find_tile_id(curr_end_i, int(cdsEnd), chrom)
                genes_to_add.append([gene_incr_id, ucsc_gene_id, 19, chrom, strand, txStart,
                                     txEnd, cdsStart, cdsEnd, exonCount,'"'+exonStarts+'"',
                                     '"'+exonEnds+'"', proteinID, alignID,
                                     tile_cds_end, tile_end, tile_cds_start, tile_start])
                gene_incr_id += 1


def manipulateList(inpList, num_to_keep=None):
    retlist = []
    for l in inpList:
        thingsToJoin = []
        for i, foo in enumerate(l):
            if num_to_keep == None or i < num_to_keep:
                if not foo and type(foo) == str:
                    thingsToJoin.append('""')
                else:
                    thingsToJoin.append(str(foo))
        thingsToJoin[-1] += '\n'
        retlist.append(string.join(thingsToJoin, sep=','))
    return retlist

with open('../genes/ucsc_gene.csv', 'w') as gene_file:
    gene_file.writelines(manipulateList(genes_to_add))
    
