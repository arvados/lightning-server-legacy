#Add person
import json
import datetime
import string

def addAnnotations(annotations):
    for annotation in annotations:
        add = True
        if annotation.startswith('hu') or ('GAP' in annotation) or ('Phase' in annotation):
            add = False
        t= 'OTHER'
        if 'SNP' in annotation or 'dbsnp' in annotation:
            t='SNP'
        if 'dbsnp' in annotation:
            print annotation

            
now = datetime.date.today()
today = str(now.year) + "-" + str(now.month) + "-" + str(now.day)

input_file = 'chr10_band10_s29600000_e31300000.fj'

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

tilevars_to_write = []
locus_to_write = []
annotations_to_write = []

#Currently need to assume that ALL tiles in this band
#We already have loadgenomes_tile populated
with open(input_file, 'r') as f:   
    i = 0
    j = 0
    ignoreDuplicate = False
    for line in f:
        #if (line[:2] == '>{' or line[:3] == '> {') and i > 0 and not ignoreDuplicate:
            #Append csv statements
            # for loadgenomes_tile: tilename, start_tag, end_tag, visualization, created
            #                     : int     , string   , string , string       , string
            # for loadgenomes_tilevariant: tile_variant_name, tile_id, length, population_size, md5sum, last_modified, sequence, start_tag, end_tag
            # for loadgenomes_varlocusannotation: tilevar_id, assembly, chromosome, begin_int, end_int, chromosome_name
            # for loadgenomes_tilevarannotation:
            
            #tilevars_to_write.append([tilevar[0], tile[0], tilevar[1], '0', tilevar[3], today, tilevar[2], '""', '""\n'], sep=','))
            #annotations_to_write.append(string.join([str(tilevar[0]), str(annotation[0]), str(annotation[1]), str(annotation[2]), str(annotation[3]), '""\n'], sep=','))
        if (line[:2] == '>{' or line[:3] == '> {'):
            ignoreDuplicate = False
            j = 0
            i += 1
            print line[1:]
            test = json.loads(line[1:])
            addAnnotations(test[u'notes'])
            if "Phase (REF) B" in str(test[u'notes']):
                ignoreDuplicate = True
            tilename = str(test[u'tileID'])
            band, path, tile, variant = tilename.split('.')
            tile = tile.zfill(4)
            tilevarname = int(band+path+tile+'000', 16)
            tile = [tilename, 19, str(test[u'startTag']), str(test[u'endTag'])]
            tilevar = [tilevarname, test[u'n'], '']
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
                tilevar[2] += line.strip()
            elif j == 20000:
                print "Tile was too long to reasonably store in memory"
                tilevar[2] += " ERROR: READ IS TOO LONG TO REASONABLY STORE IN MEMORY "
                    

##with open('hide/tile.csv', 'wb') as f:
##    f.writelines(tiles_to_write)
##with open('hide/tilevariant.csv', 'wb') as f:
##    f.writelines(tilevars_to_write)
##with open('hide/varlocusannotation.sql', 'w') as f:
##    f.writelines(annotations_to_write)
