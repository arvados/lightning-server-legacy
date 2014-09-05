import csv
import sys
import string      

genes = {}
fname = 'hide/gene.csv'                
with open(fname, 'rb') as csvfile:
    reader = csv.reader(csvfile, delimiter=',')
    for line in reader:
        # line organization:
        #   seqname, source, feature, startCGF, endCGF, score, strand, frame, ...
        #   gene_id, gene_source, gene_name, gene_biotype, transcript_id, ...
        #   transcript_source, transcript_biotype, transcript_name, exon_id, ...
        #   exon_number, protein_id, genereview, genereviewURLs
        geneName = line[10]
        if geneName in genes:
            genes[geneName] += 1
        else:
            genes[geneName] = 1

known_genes_file = 'hide/GeneReview/NBKid_shortname_genesymbol.txt'
unknown = []

with open(known_genes_file, 'r') as f:
    for line in f:
        if line[0] != '#':
            NBKid, shortname, geneName = line.split('\t')
            geneName = geneName.split('\n')[0]
            if geneName != 'Not applicable':
                if geneName not in genes:
                    unknown.append([NBKid, shortname, geneName])

print unknown
print len(unknown)
