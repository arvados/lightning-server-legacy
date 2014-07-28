import json
import datetime
import gzip

now = datetime.date.today()
today = str(now.year) + "-" + str(now.month) + "-" + str(now.day)

input_file = 'chrY_band10_s28800000_e59373566.fj.gz'

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

if ".fj.gz" in input_file:
    with gzip.open(input_file, 'rb') as f:
        tiles_to_write = []
        tilevars_to_write = []
        annotations_to_write = []
        i = 0
        j = 0
        for line in f:
            if line[:2] == '>{' and i > 0:
                #Append sql statements
                #print tile
                #print tilevar
                #print annotation
                tiles_to_write.append('INSERT INTO "loadGenomes_tile" ("tilename", "startTag", "endTag", "visualization", "created") VALUES (' + str(tile[0]) +
                                      ", '" + tile[2] + "', '" + tile[3] + "', '', '" + today + "');\n")
                tilevars_to_write.append('INSERT INTO "loadGenomes_tilevariant" ("id", "tile_id", "reference", "hasGap", "hasGapOnTag", "length", "populationSize", ' +
                                         '"startTag", "endTag", "sequence", "md5sum", "lastModified") VALUES (' + str(tile[0]) + ', ' + str(tile[0]) +
                                         ', true, false, false, ' + str(tilevar[0]) + ", 0, '', '', '" + tilevar[1] + "', '', '" + today + "');\n")
                annotations_to_write.append('INSERT INTO "loadGenomes_varlocusannotation" ("id", "assembly", "chromosome", "beginning", "end", "chromosomeName", ' +
                                            '"tilevar_id") VALUES (' + str(tile[0]) + ', ' + str(annotation[0]) + ', ' + str(annotation[1]) + ', ' +
                                            str(annotation[2]) + ', ' + str(annotation[3]) + ", '', " + str(tile[0]) + ');\n')
            if line[:2] == '>{':
                j = 0
                i += 1
                test = json.loads(line[1:])
                tilename = str(test[u'tileID'])
                band, path, tile, variant = tilename.split('.')
                tilename = int(band+path+tile, 16)
                tile = [tilename, 19, str(test[u'startTag']), str(test[u'endTag'])]
                tilevar = [test[u'n'], '']
                
                locus = str(test[u'locus'][0][u'build'])
                locus = locus.split()
                if locus[0] == 'hg19':
                    annotation = [19]
                if locus[1] in CHR_CHOICES:
                    annotation.append(CHR_CHOICES[locus[1]])
                else:
                    print "Unrecognized Chromosome"
                    annotation.append(26)
                try:
                    annotation.append(int(locus[2]))
                except ValueError:
                    annotation.append(max([0, eval(locus[2])]))
                try:
                    annotation.append(int(locus[3]))
                except ValueError:
                    annotation.append(eval(locus[3]))
            elif line != '\n':
                j += 1
                if j < 20000:
                    tilevar[1] += line.strip()
                elif j == 20000:
                    tilevar[1] += " ERROR: READ IS TOO LONG TO REASONABLY STORE IN MEMORY "
print len(tiles_to_write)
print len(tilevars_to_write)
print len(annotations_to_write)
