import json
import datetime
import gzip

now = datetime.date.today()
today = str(now.year) + "-" + str(now.month) + "-" + str(now.day)

input_file = 'chr10_band0_s0_e3000000.fj.gz'

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
        tiles_to_write = ['BEGIN;']
        tilevars_to_write = ['BEGIN;']
        annotations_to_write = ['BEGIN;']
        i = 0
        j = 0
        ignoreDuplicate = False
        for line in f:
            if line[:2] == '>{' and i > 0 and not ignoreDuplicate:
                #Append sql statements
                tiles_to_write.append('INSERT INTO "loadgenomes_tile" ("tilename", "startTag", "endTag", "visualization", "created") VALUES (' + str(tile[0]) +
                                      ", '" + tile[2] + "', '" + tile[3] + "', '', '" + today + "');\n")
                tilevars_to_write.append('INSERT INTO "loadgenomes_tilevariant" ("tile_id", "reference", "length", "populationSize", ' +
                                         '"startTag", "endTag", "sequence", "md5sum", "lastModified") VALUES (' + str(tile[0]) +
                                         ', true, ' + str(tilevar[0]) + ", 0, '', '', '" + tilevar[1] + "', '" + tilevar[2] + "', '" + today + "');\n")
                annotations_to_write.append('INSERT INTO "loadgenomes_varlocusannotation" ("assembly", "chromosome", "beginning", "end", "chromosomeName", ' +
                                            '"tilevar_id") VALUES ('  + str(annotation[0]) + ', ' + str(annotation[1]) + ', ' +
                                            str(annotation[2]) + ', ' + str(annotation[3]) + ", '', (select id from loadgenomes_tilevariant where md5sum = '" +
                                            str(tilevar[2]) + "'));\n")
            if line[:2] == '>{':
                ignoreDuplicate = False
                j = 0
                i += 1
                test = json.loads(line[1:])
                #currently will error if not in correct format
                if "Phase (REF) B" in str(test[u'notes']):
                    ignoreDuplicate = True
                tilename = str(test[u'tileID'])
                band, path, tile, variant = tilename.split('.')
                tile = tile.zfill(4)
                tilename = int(band+path+tile, 16)
                tile = [tilename, 19, str(test[u'startTag']), str(test[u'endTag'])]
                tilevar = [test[u'n'], '']
                try:
                    tilevar.append(str(test[u'md5sum']))
                except KeyError:
                    print "Could not find md5sum"
                    tilevar.append('')
                
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
            elif line != '\n' and not ignoreDuplicate:
                j += 1
                if j < 20000:
                    tilevar[1] += line.strip()
                elif j == 20000:
                    print "Tile was too long to reasonably store in memory"
                    tilevar[1] += " ERROR: READ IS TOO LONG TO REASONABLY STORE IN MEMORY "

tiles_to_write.append('COMMIT;')
tilevars_to_write.append('COMMIT;')
annotations_to_write.append('COMMIT;')
with open('hide/tile.sql', 'w') as f:
    f.writelines(tiles_to_write)
with open('hide/tilevariant.sql', 'w') as f:
    f.writelines(tilevars_to_write)
with open('hide/varlocusannotation.sql', 'w') as f:
    f.writelines(annotations_to_write)
