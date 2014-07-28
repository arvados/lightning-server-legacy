#Creates the fixture/initial_data.json file

#Currently only uses 1 file from the google computer

import io
import json
from pprint import pprint
import datetime
import gzip

now = datetime.date.today()
today = str(now.year) + "-" + str(now.month) + "-" + str(now.day)


tiles_to_write = []
tilevars_to_write = []
annotations_to_write = []
#Reading the reference genome
with gzip.open('chr1_band0_s0_e2300000.fj.gz', 'rb') as f:
    #Currently everything here is default
    # 
    # tile = [tilename, assembly, startTag, endTag]
    # tile = [0, 0, '', '']
    #
    # tilevar = [length, sequence]
    # tilevar = [0, '']
    #
    # annotation = [assembly, chromosome, beginning, end]
    # annotation = [0, 0, -1, -1]
    i = 0
    for line in f:
        if line[:2] == '>{' and i > 0:
            # Append JSON-like dictionaries to lists
##            tiles_to_write.append({"pk": tile[0], "model": "loadGenomes.tile", "fields": {"startTag": tile[2], "endTag": tile[3],
##                                                                                          "visualization": "", "created": today, 
##                                                                                          }})
##
##            tilevars_to_write.append({"pk": tile[0], "model": "loadGenomes.tilevariant", "fields": {"tile": tile[0], "reference": True,
##                                                                                                    "hasGap": False, "hasGapOnTag": False,
##                                                                                                    "length": tilevar[0],
##                                                                                                    "populationSize": 0,
##                                                                                                    "startTag": "", "endTag": "",
##                                                                                                    "sequence": tilevar[1],
##                                                                                                    "md5sum": "", "lastModified":today,
##                                                                                                    }})
##            annotations_to_write.append({"pk": tile[0], "model": "loadGenomes.varlocusannotation", "fields": {"tilevar":tile[0],
##                                                                                                              "assembly":annotation[0],
##                                                                                                              "chromosome":annotation[1],
##                                                                                                              "beginning":annotation[2],
##                                                                                                              "end":annotation[3],
##                                                                                                              "chromosomeName":""}})
            #Append sql statements
            tiles_to_write.append('INSERT INTO "loadGenomes_tile" ("tilename", "startTag", "endTag", "visualization", "created") VALUES (' + str(tile[0]) +
                                  ", '" + tile[2] + "', '" + tile[3] + "', '', '" + today + "');")
            tilevars_to_write.append('INSERT INTO "loadGenomes_tilevariant" ("id", "tile_id", "reference", "hasGap", "hasGapOnTag", "length", "populationSize", ' +
                                     '"startTag", "endTag", "sequence", "md5sum", "lastModified") VALUES (' + str(tile[0]) + ', ' + str(tile[0]) +
                                     ', true, false, false, ' + str(tilevar[0]) + ", 0, '', '', '" + tilevar[1] + "', '', '" + today + "');")
            annotations_to_write.append('INSERT INTO "loadGenomes_varlocusannotation" ("id", "assembly", "chromosome", "beginning", "end", "chromosomeName", ' +
                                        '"tilevar_id") VALUES (' + str(tile[0]) + ', ' + str(annotation[0]) + ', ' + str(annotation[1]) + ', ' +
                                        str(annotation[2]) + ', ' + str(annotation[3]) + ", '', " + str(tile[0]) + ');')
        if line[:2] == '>{':
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
            if locus[1] == 'chr1':
                annotation.append(1)
            try:
                annotation.append(int(locus[2]))
            except ValueError:
                annotation.append(max([0, eval(locus[2])]))
            try:
                annotation.append(int(locus[3]))
            except ValueError:
                annotation.append(eval(locus[3]))
        elif line != '\n':
            tilevar[1] += line.strip()

##tiles_to_write.extend(tilevars_to_write)
##tiles_to_write.extend(annotations_to_write)
##with io.open('fixtures/initial_data.json', 'w', encoding='utf-8') as writeFile:
##    writeFile.write(unicode(json.dumps(tiles_to_write, ensure_ascii=False)))

with open('sql/tile.sql', 'w') as f:
    f.writelines(tiles_to_write)
with open('sql/tilevariant.sql', 'w') as f:
    f.writelines(tilevars_to_write)
with open('sql/varlocusannotation.sql', 'w') as f:
    f.writelines(annotations_to_write)

