#convert from tile_length_count to a csv format

#Notes: Hacky...
#1-22, X, Y, M is the order; odd chromosome types are discarded

#Current time stats:
    #real	3m32.839s
    #user	3m25.393s
    #sys	0m7.358s



import re
import itertools
import numpy as np
import sys

class Tile:
    def __init__(self, tile_id, supertile_id, default_count, size):
        #tile_id is a string
        self.id = tile_id
        self.supertile_id = supertile_id
        self.nums = [count]
        self.sizes = [size]
    def add_count(self, count):
        self.nums.append(count)
    def add_size(self, s):
        self.sizes.append(s)
            
#We will also want to see how many tiles compose each supertile, since that will bias the data
class SuperTile:
    chromosome = ''
    arm = ''
    region = ''
    band = ''
    subband = ''
    subsubband = ''
    def __init__(self, supertile_id):
        self.id = supertile_id
        self.nums = []
        self.sizes = []
        self.tiles = []
    def add_tile(self, tile):
        self.tiles.append(tile)
        self.nums.extend(tile.nums)
        self.sizes.extend(tile.sizes)
    def organize(self):
        self.tiles = sorted(self.tiles, key=lambda tile: int(tile.id, 16))
    def set_label(self, i, label):
        if i == 0:
            self.arm = label
        elif i == 1:
            self.region = label
        elif i == 2:
            self.band = label
        elif i == 3:
            self.subband = label
        elif i == 4:
            self.subsubband = label
    def print_info(self):
        print self.id, self.nums
        print self.chromosome, self.arm, self.region, self.band, self.subband, self.subsubband
    def name(self):
        return self.chromosome + self.arm + self.region + self.band + self.subband + self.subsubband
    def subband_name(self):
        return self.chromosome + self.arm + self.region + self.band + self.subband
    def band_name(self):
        return self.chromosome + self.arm + self.region + self.band
    def region_name(self):
        return self.chromosome + self.arm + self.region
    def arm_name(self):
        return self.chromosome + self.arm
    def chr_name(self):
        return self.chromosome

def cmp_chr (chr1, chr2):
    chr1 = chr1.lstrip('chr')
    chr2 = chr2.lstrip('chr')
    #Test to see if we are comparing Large chromosomes; set test and ext accordingly
    rext = '[XYM0-9]+(?=[pq])'
    srext = '[XYM0-9]+'
    m1 = re.search(rext, chr1)
    m12 = re.search(srext, chr1)
    if m1 == None and m12 != None:
        test = '[0-9]+'
        ext = '[XYM0-9]+'
    else:
        test = '[0-9]+(?=[pq])'
        ext = '[XYM0-9]+(?=[pq])'
    oddballs = {'X':'23', 'Y':'24', 'M':'25'} 
    m1 = re.search(test, chr1)
    m2 = re.search(test, chr2)
    if m1 == None:
        foo = oddballs[chr1[0]]
    else:
        foo = m1.group(0)
    if m2 == None:
        bar = oddballs[chr2[0]]
    else:
        bar = m2.group(0)
    tr1 = re.sub(ext, '', chr1)
    tr2 = re.sub(ext, '', chr2)
    if foo != bar:
        return cmp(int(foo), int(bar))
    elif tr1[0] != tr2[0]:
        return cmp(tr1[0], tr2[0])
    else:
        return cmp(float(tr1[1:]), float(tr2[1:]))

def router(stile, i):
    retvals = [stile.name(), stile.subband_name(), stile.band_name(), stile.region_name(), stile.arm_name(), stile.chr_name()]
    return retvals[i]


def print_len_stats(supertiles, filename, level_index):
    flen = open('LenStats' + filename, 'w')
    #This first line is necessary for the .html file to correctly read in the data. Changing this line
    #requires changing the .html file as well    
    flen.write('State,25th percentile,50th percentile,75th percentile\n')
    arms = {}
    for supertile in supertiles:
        supertile = supertiles[supertile]
        name = router(supertile, level_index)
        if name in arms:
            arms[name]['nums'].extend(supertile.nums)
            arms[name]['sizes'].extend(supertile.sizes)
        else:
            arms[name] = {'nums': supertile.nums, 'sizes': supertile.sizes}

    names = sorted(arms.keys(), cmp=cmp_chr)
    for arm in names:
        if len(arms[arm]['sizes']) == 0:
            tilestr = arm + ',0,0,0\n'
        else:
            a = arms[arm]['sizes']
            tfp = np.percentile(a, 25)
            med = np.percentile(a, 50)
            sfp = np.percentile(a, 75)
            tilestr = arm + ',' + str(tfp) + ',' + str(med-tfp) + ',' + str(sfp-med) + '\n'
        flen.write(tilestr)
    flen.close()

if __name__ == '__main__':
    args = sys.argv
    if len(args) < 3:
        print "Usage: python sorted2csv.py tile_length_count ucsc.cytomap.hg19.txt"
        exit(1)
    slenfile = args[1]
    mapfile = args[2]

    print "Reading Tiles"
    #Read tile counts and form tile dictionary           
    f1 = open(slenfile, 'r') 
    tiles = {}
    for line in f1:
        info = line.split()
        #Note these reads indicates each line of the file is ordered as follows:
        #   [count] [tileid, not separated by periods] [length]
        tileid = info[1]
        count = info[0]
        length = info[2].strip('"\n')
        supertile = tileid[1:4]
        tilename = tileid[4:]
        if tileid in tiles:
            tiles[tileid].add_count(int(count))
            tiles[tileid].add_size(int(length))
        else:
            tiles[tileid] = Tile(tilename, supertile, int(count), int(length))
    f1.close()

    print "Reorganizing tiles into supertiles"
    #organize tiles into supertiles, stored in supertile dictionary
    supertiles = {}
    for tileid in tiles:
        tile = tiles[tileid]
        supertile_id = tile.supertile_id
        if supertile_id in supertiles:
            supertiles[supertile_id].add_tile(tile)
        else:
            supertiles[supertile_id] = SuperTile(supertile_id)
            supertiles[supertile_id].add_tile(tile)

    #Release the dictionary tiles from memory
    print "Releasing the tile dictionary from memory"
    del tiles

    print "Organizing supertiles"
    for supertile_id in supertiles:
        supertile = supertiles[supertile_id]
        supertile.organize()

        
    granularity = ['[pq]', '(?<=[pq])[0-9]', '(?<=[pq][0-9])[0-9]',
                   '(?<=[pq][0-9]{2}\.)[0-9]', '(?<=[pq][0-9]{2}\.[0-9])[0-9]']

    print "Naming supertiles"
    chr_org_file = open(mapfile, 'r')
    for i, line in enumerate(chr_org_file):
        chrom, s_chrom, e_chrom, name, stain = line.split()
        supertile_id = hex(i)[2:]
        supertile_id = supertile_id.zfill(3)
        if supertile_id not in supertiles:
            supertiles[supertile_id] = SuperTile(supertile_id)
        supertile = supertiles[supertile_id]
        supertile.chromosome = chrom
        for i, regex in enumerate(granularity):
            m = re.search(regex, name)
            if m != None:
                supertile.set_label(i, m.group(0))
    chr_org_file.close()

    for i, f in enumerate(['Subbands.csv', 'Bands.csv', 'Regions.csv', 'Arms.csv', 'Chromosomes.csv']):
        print "Printing " + f
        print_len_stats(supertiles, f, i+1)




