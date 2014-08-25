#Add person
import json
import datetime
import string

def addAnnotations(annotations, tile_variant_id, today):
    # for loadgenomes_tilevarannotation: tile_variant_id, annotation_type, trusted, annotation_text, created, last_modified
    lists_to_extend = []
    for annotation in annotations:
        add = True
        if annotation.startswith('hu') or ('GAP' in annotation):
            #These are population specific tags and should not be documented in the tile library
            add = False
        elif 'Phase' in annotation:
            #This is another population-sepecific tag
            add = False
            if 'REF' in annotation:
                pop_size_increment = 0
            else:
                pop_size_increment = 1
        elif 'SNP' in annotation or 'SUB' in annotation or 'INDEL' in annotation:
            t='SNP_INDEL'
        elif 'dbsnp' in annotation:
            t='DATABASE'
            annotation = annotation.replace(',', ' ')
        elif 'alleles' in annotation:
            #This is not a database annotation and is unhelpful
            add=False
        else:
            t='OTHER'
        if add:
            lists_to_extend.append([tile_variant_id, t, 't', annotation, today, today])
    #This will currently error if a Phase annotaiton is not in the json input
    return lists_to_extend, pop_size_increment

def manipulateList(inpList):
    retlist = []
    for l in inpList:
        thingsToJoin = []
        for foo in l:
            if not foo and type(foo) == str:
                thingsToJoin.append('""')
            else:
                thingsToJoin.append(str(foo))
        thingsToJoin[-1] += '\n'
        retlist.append(string.join(thingsToJoin, sep=','))
    return retlist
            
now = datetime.date.today()
today = str(now.year) + "-" + str(now.month) + "-" + str(now.day)

input_file = 'entire.fj'

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
curr_tilevars = {}
tiles_to_write = []
tilevars_to_write = []
loci_to_write = []
annotations_to_write = []

#Currently need to assume that ALL tiles in this band
#We already have loadgenomes_tile populated, so we won't need to
with open(input_file, 'r') as f:   
    i = 0
    j = 0
    for line in f:
        if (line[:2] == '>{' or line[:3] == '> {') and i > 0:
            #Append csv statements
            # NOTE: The population_size is going to be twice the number of humans
            # for loadgenomes_tile: tilename, start_tag, end_tag, visualization, created
            # for loadgenomes_tilevariant: tile_variant_name, tile_id, length, population_size, md5sum, last_modified, sequence, start_tag, end_tag
            # for loadgenomes_varlocusannotation: tilevar_id, assembly, chromosome, begin_int, end_int, chromosome_name
            # for loadgenomes_tilevarannotation: tile_variant_id, annotation_type, trusted, annotation_text
            write_new = True
            is_ref = False
            tile = toSaveData['tilename']
            #If we are still processing the reference genome, not all tilenames will be loaded yet
            if tile not in curr_tilevars:
                curr_tilevars[tile] = [len(tilevars_to_write)]
                is_ref = True
            #At least one tile with that tilename exists. Check if we already have it
            else:
                poss_tile_indices = curr_tilevars[tile]
                for index in poss_tile_indices:
                    if toSaveData['md5sum'] == tilevars_to_write[index][4]:
                        annotations, population_incr = addAnnotations(loadedData[u'notes'], tilevars_to_write[index][0], today)
                        write_new = False
                        tilevars_to_write[index][3] += population_incr
                if write_new:
                    curr_tilevars[tile].append(len(tilevars_to_write))
            if write_new:
                varname = hex(len(curr_tilevars[tile])-1)[2:].zfill(3)
                tilevarname = int(tile+varname, 16)
                tile = int(tile, 16)
                annotations, population_incr = addAnnotations(loadedData[u'notes'], tilevarname, today)
                if is_ref:
                    tiles_to_write.append([tile, toSaveData['start_tag'], toSaveData['end_tag'], "", today])
                tilevars_to_write.append([tilevarname, tile, toSaveData['length'], population_incr, toSaveData['md5sum'], today, toSaveData['sequence'],
                                          toSaveData['start_seq'], toSaveData['end_seq']])
                loci_to_write.append([tilevarname, toSaveData['assembly'], toSaveData['chromosome'], toSaveData['locus_begin'],
                                      toSaveData['locus_end'], toSaveData['chrom_name']])
                annotations_to_write.extend(annotations)
        if (line[:2] == '>{' or line[:3] == '> {'):
            j = 0
            i += 1
            toSaveData = {}
            loadedData = json.loads(line[1:])
            
            tilename = str(loadedData[u'tileID'])
            band, path, tile, variant = tilename.split('.')
            tile = tile.zfill(4)
            toSaveData['tilename'] = band+path+tile
            toSaveData['start_tag'] = str(loadedData[u'startTag'])
            toSaveData['end_tag'] = str(loadedData[u'endTag'])
            toSaveData['start_seq'] = ""
            toSaveData['end_seq'] = ""
            #Will only need to add 'start_tag' and 'end_tag' when using non-reference data which has SNPs on tags
            if u'startSeq' in loadedData:
                if str(loadedData[u'startTag']).lower() != str(loadedData[u'startSeq']).lower():
                    toSaveData['start_seq'] = str(loadedData[u'startSeq'])
                if str(loadedData[u'endTag']).lower() != str(loadedData[u'endSeq']).lower():
                    toSaveData['end_seq'] = str(loadedData[u'endSeq'])
            toSaveData['length'] = loadedData[u'n']
            toSaveData['sequence'] = ''
            toSaveData['md5sum'] = str(loadedData[u'md5sum'])
            
            toSaveData['chromosome'] = str
            locus = str(loadedData[u'locus'][0][u'build'])
            locus = locus.split()
            if locus[0] == 'hg19':
                toSaveData['assembly'] = 19
            if locus[1] in CHR_CHOICES:
                toSaveData['chromosome'] = CHR_CHOICES[locus[1]]
                toSaveData['chrom_name'] = ""
            else:
                toSaveData['chromosome'] = 26
                toSaveData['chrom_name'] = locus[1]
            toSaveData['locus_begin'] = max([0, eval(locus[2])])
            toSaveData['locus_end'] = eval(locus[3])
        elif line != '\n':
            j += 1
            if j < 20000:
                toSaveData['sequence'] += line.strip()
            elif j == 20000:
                print "Tile was too long to reasonably store in memory"
                toSaveData['sequence'] += " ERROR: READ IS TOO LONG TO REASONABLY STORE IN MEMORY "


with open('hide/tile.csv', 'wb') as f:
    f.writelines(manipulateList(tiles_to_write))
with open('hide/tilevariant.csv', 'w') as f:
    f.writelines(manipulateList(tilevars_to_write))
with open('hide/varlocusannotation.csv', 'w') as f:
    f.writelines(manipulateList(loci_to_write))
with open('hide/tilevarannotation.csv', 'w') as f:
    f.writelines(manipulateList(annotations_to_write))


