#Generate tile info for cgf generation

import json
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
tilevars_to_write = []

#Currently need to assume that ALL tiles in this band
#We already have loadgenomes_tile populated, so we won't need to
with open(input_file, 'r') as f:   
    i = 0
    j = 0
    for line in f:
        if (line[:2] == '>{' or line[:3] == '> {') and i > 0:
            #Append csv statements
            # NOTE: The population_size is going to be twice the number of humans
            # for loadgenomes_tilevariant: tile_variant_name, population_size, md5sum, 
            write_new = True
            tile = toSaveData['tilename']
            #If we are processing the first genome not all tilenames will be loaded yet
            if tile not in curr_tilevars:
                curr_tilevars[tile] = [len(tilevars_to_write)]
            #At least one tile with that tilename exists. Check if we already have it
            else:
                poss_tile_indices = curr_tilevars[tile]
                for index in poss_tile_indices:
                    if toSaveData['md5sum'] == tilevars_to_write[index][2]:
                        write_new = False
                        tilevars_to_write[index][1] += 1
                if write_new:
                    curr_tilevars[tile].append(len(tilevars_to_write))
            if write_new:
                varname = hex(len(curr_tilevars[tile])-1)[2:].zfill(3)
                tilevarname = string.join([tile,varname], sep='.')
                tilevars_to_write.append([tilevarname, 1, toSaveData['md5sum']])
        if (line[:2] == '>{' or line[:3] == '> {'):
            j = 0
            i += 1
            toSaveData = {}
            loadedData = json.loads(line[1:])
            tilename = str(loadedData[u'tileID'])
            band, path, tile, variant = tilename.split('.')
            tile = tile.zfill(4)
            toSaveData['tilename'] = string.join([band,path,tile], '.')
            toSaveData['md5sum'] = str(loadedData[u'md5sum'])

with open('hide/testlibrary.csv', 'w') as f:
    f.writelines(manipulateList(tilevars_to_write))



