import csv
supported_chr = {str(i+1):i+1 for i in range(22)}
supported_chr['X'] = 23
supported_chr['Y'] = 24
supported_chr['MT'] = 25


poss_sources = set()
fname = 'Homo_sapiens.GRCh37.75.gtf'
towrite = []
with open(fname, 'rb') as csvfile:
    reader = csv.reader(csvfile, delimiter='\t')
    for line in reader:
        if line[0][0] != '#':
            # seqname, source, feature, startCGF, endCGF, score, strand, frame
            towriteline = []
            if line[0] in supported_chr:
                towriteline.append(supported_chr[line[0]])
            else:
                towriteline.append(26)
            towriteline.append(line[1])
            poss_sources.add(line[1])
            #attributes = line[8].split(';')
            
for i in poss_chr:
    print i
                    
