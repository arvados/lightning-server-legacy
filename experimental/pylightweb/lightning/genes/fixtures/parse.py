

ids = []
with open('brca_gene_xrefs.csv', 'r') as read_file:
    for line in read_file:
        of_interest = line.strip('\n').split(',')
        ids.append(str(int(of_interest[-4])))

with open('ucsc_gene.csv', 'r') as read_file:
    with open('brca_ucsc_genes.csv', 'w') as out_file:
        for line in read_file:
            of_interest = line.strip('\n').split(',')
            if of_interest[0] in ids:
                out_file.write(line)
