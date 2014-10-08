#Read UCSC xref data and add GeneReview articles

import string

# genes_genexref
#   (id), mrna, sp_id, sp_display_id, gene_aliases, ref_seq, prot_acc,
#   description, rfam_acc, trna_name, gene_id, gene_review_URLs,
#   has_gene_review
xrefs_to_add = []

gene_review_file = '../loadgenes/hide/GeneReview/NBKid_shortname_genesymbol.txt'
gene_review_phenotype_file = '../loadgenes/hide/GeneReview/GRtitle_shortname_NBKid.txt'
ucsc_genes_file = '../loadgenes/hide/UCSC/UCSC_Genes'
ucsc_genes_xref_file = '../loadgenes/hide/UCSC/UCSC_Genes_xref'

database_genes_file = '../genes/ucsc_gene.csv'

gene_review = {}
NBK_id_map = {}
with open(gene_review_file, 'r') as f:
    for line in f:
        if line[0] != '#':
            NBKid, shortname, geneName = line.strip('\n').split('\t')
            if geneName != 'Not applicable':
                if geneName in gene_review:
                    gene_review[geneName][0] += ';http://www.ncbi.nlm.nih.gov/books/' + NBKid
                    gene_review[geneName][2].append(NBKid)
                else:
                    gene_review[geneName] = ['http://www.ncbi.nlm.nih.gov/books/' + NBKid, False, [NBKid]]

with open(gene_review_phenotype_file, 'r') as f:
    for line in f:
        if line[0] != '#':
            shortname, phenotype, NBKid = line.strip('\n').split('\t')
            NBK_id_map[NBKid] = phenotype


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

ok_to_ignore = []
id_map = {}
with open(ucsc_genes_file, 'r') as gene_file:
    for line in gene_file:
        if not line.startswith('#'):
            ucsc_gene_id, human_chrom, human_strand, txStart, txEnd, cdsStart, cdsEnd, exonCount, exonStarts, exonEnds, proteinID, alignID = line.strip('\n').split('\t')
            if human_chrom not in CHR_CHOICES:
                ok_to_ignore.append(ucsc_gene_id)


with open(database_genes_file, 'r') as gene_file:
    for line in gene_file:
        info = line.strip('\n').split(',')
        id_map[info[1]] = info[0]

#kgID, mRNA, spID, spDisplayID, geneSymbol, refseq, protAcc, description, rfamAcc, tRnaName
with open(ucsc_genes_xref_file, 'r') as f:
    for line in f:
        if line[0] != '#':
            gene_id, mrna, spid, spdisplayid, gene_aliases, refseq, protacc, descr, rfam, trna = line.strip('\n').split('\t')
            if gene_id in id_map:
                gene = id_map[gene_id]
                if gene_aliases in gene_review:
                    phenotype = ""
                    for nbkid in gene_review[gene_aliases][2]:
                        phenotype += nbkid + ':' + NBK_id_map[nbkid] + ';'
                    xrefs_to_add.append([mrna, spid, spdisplayid, gene_aliases, refseq, protacc,
                                         '"'+descr+'"', rfam, trna, gene, gene_review[gene_aliases][0], 't', '"' + phenotype + '"'])
                    gene_review[gene_aliases][1] = True
                else:
                    xrefs_to_add.append([mrna, spid, spdisplayid, gene_aliases, refseq, protacc,
                                         '"'+descr+'"', rfam, trna, gene, '', 'f', ''])
            else:
                assert gene_id in ok_to_ignore
                
                    

for gene in gene_review:
    if not gene_review[gene][1]:
        print 'Gene', gene, 'ignored'

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

with open('../genes/genexref.csv', 'w') as f:
    f.writelines(manipulateList(xrefs_to_add))
