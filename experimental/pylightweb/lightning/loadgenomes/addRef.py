#Add only reference genome;
# Assumptions:
#   assumes Phase A == Phase B
import json
import datetime
import string

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

input_file = 'ref.fj'

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

#Add reference
with open(input_file, 'r') as f:   
    i = 0
    j = 0
    for line in f:
        if (line[:2] == '>{' or line[:3] == '> {') and i > 0:
            #Append csv statements
            # for loadgenomes_tile: tilename, start_tag, end_tag, created
            # for loadgenomes_tilevariant: tile_variant_name, tile_id, length, population_size, md5sum, last_modified, sequence, start_tag, end_tag
            # for loadgenomes_tilelocusannotation: tilevar_id, assembly, chromosome, begin_int, end_int, chromosome_name
            tile = toSaveData['tilename']
            #Only add the tile if it's new
            if tile not in curr_tilevars:
                curr_tilevars[tile] = True
                varname = hex(0)[2:].zfill(3)
                tilevarname = int(tile+varname, 16)
                tile = int(tile, 16)
                tiles_to_write.append([tile, toSaveData['start_tag'], toSaveData['end_tag'], today])
                loci_to_write.append([tile, toSaveData['assembly'], toSaveData['chromosome'], toSaveData['locus_begin'],
                                      toSaveData['locus_end'], toSaveData['chrom_name']])
                tilevars_to_write.append([tilevarname, tile, toSaveData['length'], 0, toSaveData['md5sum'], today,
                                          toSaveData['sequence'], "", ""])
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
            toSaveData['length'] = loadedData[u'n']
            toSaveData['sequence'] = ''
            toSaveData['md5sum'] = str(loadedData[u'md5sum'])
            
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


with open('hide/ref/tile.csv', 'wb') as f:
    f.writelines(manipulateList(tiles_to_write))
with open('hide/ref/tilevariant.csv', 'w') as f:
    f.writelines(manipulateList(tilevars_to_write))
with open('hide/ref/tilelocusannotation.csv', 'w') as f:
    f.writelines(manipulateList(loci_to_write))

with open('hide/ref/Library.csv', 'w') as f:
    for l in tilevars_to_write:
        tile_variant_name, tile_id, length, population_size, md5sum, last_modified, sequence, start_tag, end_tag = l
        tile_var_hex = hex(tile_variant_name)[2:]
        tile_var_hex = tile_var_hex.zfill(12)
        path = tile_var_hex[:3]
        version = tile_var_hex[3:5]
        step = tile_var_hex[5:9]
        var = tile_var_hex[9:]
        tile_var_period_sep = string.join([path, version, step, var], '.') 
        f.write(string.join([tile_var_period_sep, str(tile_variant_name), str(tile_id), str(population_size), md5sum+'\n'], sep=','))




