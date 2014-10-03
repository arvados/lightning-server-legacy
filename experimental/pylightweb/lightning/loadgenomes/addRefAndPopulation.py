#Add reference genome and however many people are attached to it
import json
import datetime
import string

def addAnnotations(annotations, tile_variant_id, today):
    """
    annotations: list of annotations read in from FASTJ format
    tile_variant_id: the primary key for the tile_variant to add the annotations to
    today: the date

    Requires Phase to be in annotation: determines whether reference or human!

    if SNP, SUB, or INDEL in an annotation, it is marked as SNP_INDEL
    if db_xref in an annotation, it is marked as DATABASE
    if none of the above, and 'alleles' is not in the annotation, it is marked as OTHER (only for debugging purposes)

    no phenotypic data is known to be passed from the FASTJ file
    """
    # for loadgenomes_tilevarannotation: tile_variant_id, annotation_type, source, annotation_text, phenotype, created, last_modified
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
        elif 'db_xref' in annotation:
            t='DATABASE'
            annotation = annotation.replace(',', ' ')
        elif 'alleles' in annotation:
            #Cannot be a database annotation; is identical to SNP annotation; is unhelpful.
            add=False
        else:
            t='OTHER'
        if add:
            lists_to_extend.append([tile_variant_id, t, 'library_generation', annotation, '', today, today])

    return lists_to_extend, pop_size_increment

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
            
now = datetime.datetime.now()
now = str(now)

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
loci_to_write = []
tilevars_to_write = []
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
            # for loadgenomes_tile: tilename, start_tag, end_tag, created
            # for loadgenomes_tilevariant: tile_variant_name, variant_value, length, md5sum, created, last_modified, sequence, start_tag, end_tag, tile_id, (population)
            # for loadgenomes_tilelocusannotation: tile_id, assembly, chromosome, begin_int, end_int, chromosome_name
            # for loadgenomes_varannotation: tile_variant_id, annotation_type, source, annotation_text, phenotype, created, last_modified
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
                    if toSaveData['md5sum'] == tilevars_to_write[index][3]:
                        annotations, population_incr = addAnnotations(loadedData[u'notes'], tilevars_to_write[index][0], now)
                        write_new = False
                        tilevars_to_write[index][-1] += population_incr
                if write_new:
                    curr_tilevars[tile].append(len(tilevars_to_write))
            if write_new:
                varname = hex(len(curr_tilevars[tile])-1)[2:].zfill(3)
                tilevarname = int(tile+varname, 16)
                tile = int(tile, 16)
                annotations, population_incr = addAnnotations(loadedData[u'notes'], tilevarname, now)
                if is_ref:
                    tiles_to_write.append([tile, toSaveData['start_tag'], toSaveData['end_tag'], now])
                    loci_to_write.append([tile, toSaveData['assembly'], toSaveData['chromosome'], toSaveData['locus_begin'],
                                          toSaveData['locus_end'], toSaveData['chrom_name']])
                tilevars_to_write.append([tilevarname, int(varname), toSaveData['length'], toSaveData['md5sum'], now, now, 
                                          toSaveData['sequence'], toSaveData['start_seq'], toSaveData['end_seq'], tile, population_incr])
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
            if toSaveData['md5sum'] == tilevars_to_write[index][3]:
                annotations, population_incr = addAnnotations(loadedData[u'notes'], tilevars_to_write[index][0], now)
                write_new = False
                tilevars_to_write[index][-1] += population_incr
        if write_new:
            curr_tilevars[tile].append(len(tilevars_to_write))
    if write_new:
        varname = hex(len(curr_tilevars[tile])-1)[2:].zfill(3)
        tilevarname = int(tile+varname, 16)
        tile = int(tile, 16)
        annotations, population_incr = addAnnotations(loadedData[u'notes'], tilevarname, now)
        if is_ref:
            tiles_to_write.append([tile, toSaveData['start_tag'], toSaveData['end_tag'], now])
            loci_to_write.append([tile, toSaveData['assembly'], toSaveData['chromosome'], toSaveData['locus_begin'],
                                  toSaveData['locus_end'], toSaveData['chrom_name']])
        tilevars_to_write.append([tilevarname, int(varname), toSaveData['length'], toSaveData['md5sum'], now, now, 
                                  toSaveData['sequence'], toSaveData['start_seq'], toSaveData['end_seq'], tile, population_incr])
        annotations_to_write.extend(annotations)  

with open('hide/chrM/tile.csv', 'wb') as f:
    f.writelines(manipulateList(tiles_to_write))
with open('hide/chrM/tilevariant.csv', 'w') as f:
    f.writelines(manipulateList(tilevars_to_write, 10))
with open('hide/chrM/tilelocusannotation.csv', 'w') as f:
    f.writelines(manipulateList(loci_to_write))
with open('hide/chrM/varannotation.csv', 'w') as f:
    f.writelines(manipulateList(annotations_to_write))
with open('hide/chrM/Library.csv', 'w') as f:
    # for loadgenomes_tilevariant: tile_variant_name, variant_value, length, md5sum, created, last_modified, sequence, start_tag, end_tag, tile_id, population
    for l in tilevars_to_write:
        tile_variant_name, variant_value, length, md5sum, created, last_modified, sequence, start_tag, end_tag, tile_id, population_size = l
        #tilevarname, popul, md5sum
        tile_var_hex = hex(tile_variant_name)[2:]
        tile_var_hex = tile_var_hex.zfill(12)
        path = tile_var_hex[:3]
        version = tile_var_hex[3:5]
        step = tile_var_hex[5:9]
        var = tile_var_hex[9:]
        tile_var_period_sep = string.join([path, version, step, var], '.') 
        f.write(string.join([tile_var_period_sep, str(tile_variant_name), str(tile_id), str(population_size), md5sum+'\n'], sep=','))


