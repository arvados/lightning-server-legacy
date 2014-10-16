#Testing performance

import time

import tile_library.functions as fns

from tile_library.models import Tile, TileVariant, TileLocusAnnotation, VarAnnotation, GenomeStatistic
from django.db.models import Avg, Count, Max, Min

def timeit(fn):
    n = time.time()
    x = fn()
    l = time.time()
    return l-n, x
def timeitarg(fn, *args):
    n = time.time()
    x = fn(*args)
    l = time.time()
    return l-n, x

def run():
    chrom = 2
    path = 21
    min_pos, min_tile = fns.get_min_position_and_tile_variant_from_chromosome_int(chrom)
    max_pos, max_tile = fns.get_min_position_and_tile_variant_from_chromosome_int(chrom+1)
    max_pos -= 1
    max_tile -= 1
    min_path_pos, min_path_tile = fns.get_min_position_and_tile_variant_from_path_int(path)
    max_path_pos, max_path_tile = fns.get_min_position_and_tile_variant_from_path_int(path+1)
    max_path_pos -= 1
    max_path_tile -= 1

    print "Entire Genome:"
    print "\tTile count()", timeitarg(Tile.objects.count)
    #print "\tTileVar count()", timeit(TileVariant.objects.count)
    print "\tTileVar avglen", timeitarg(TileVariant.objects.aggregate, Avg('length'))
    print "\tTileVar maxvar", timeitarg(TileVariant.objects.aggregate, Max('variant_value'))
    print "\tTileVar avgvar", timeitarg(TileVariant.objects.aggregate, Avg('variant_value'))
    print "\tTileVar allagg", timeitarg(TileVariant.objects.aggregate, Avg('length'), Max('variant_value'), Avg('variant_value'))
    print ""
    print "Biggest Chromosome:"
    print "\tTile count()", timeitarg(Tile.objects.filter(tilename__range=(min_pos, max_pos)).count)
    #print "\tTileVar count()", timeit(TileVariant.objects.filter(tile_variant_name__range=(min_tile, max_tile)).count)
    print "\tTileVar avglen", timeitarg(TileVariant.objects.filter(tile_variant_name__range=(min_tile, max_tile)).aggregate, Avg('length'))
    print "\tTileVar maxvar", timeitarg(TileVariant.objects.filter(tile_variant_name__range=(min_tile, max_tile)).aggregate, Max('variant_value'))
    print "\tTileVar avgvar", timeitarg(TileVariant.objects.filter(tile_variant_name__range=(min_tile, max_tile)).aggregate, Avg('variant_value'))
    print "\tTileVar allarg", timeitarg(TileVariant.objects.filter(tile_variant_name__range=(min_tile, max_tile)).aggregate, Avg('length'), Max('variant_value'), Avg('variant_value'))
    print ""
    print "Biggest Path:"
    print "\tTile count()", timeitarg(Tile.objects.filter(tilename__range=(min_path_pos, max_path_pos)).count)
    #print "\tTileVar count()", timeit(TileVariant.objects.filter(tile_variant_name__range=(min_path_tile, max_path_tile)).count)
    print "\tTileVar avglen", timeitarg(TileVariant.objects.filter(tile_variant_name__range=(min_path_tile, max_path_tile)).aggregate, Avg('length'))
    print "\tTileVar maxvar", timeitarg(TileVariant.objects.filter(tile_variant_name__range=(min_path_tile, max_path_tile)).aggregate, Max('variant_value'))
    print "\tTileVar avgvar", timeitarg(TileVariant.objects.filter(tile_variant_name__range=(min_path_tile, max_path_tile)).aggregate, Avg('variant_value'))
    print "\tTileVar allarg", timeitarg(TileVariant.objects.filter(tile_variant_name__range=(min_path_tile, max_path_tile)).aggregate, Avg('length'), Max('variant_value'), Avg('variant_value'))

def run_chr():
    chrom = 1
    min_pos, min_tile = fns.get_min_position_and_tile_variant_from_chromosome_int(chrom)
    max_pos, max_tile = fns.get_min_position_and_tile_variant_from_chromosome_int(chrom+1)
    max_pos -= 1
    max_tile -= 1
    #Get Genome Statistics for chr1
    time1 = time.time()
    chr_stats = GenomeStatistic.objects.get(pk=chrom+1)
    time2 = time.time()
    to_print = [('Get Chr1 Statistics', time2-time1)]
    
    positions = Tile.objects.filter(tilename__range=(min_pos, max_pos))
    tiles = TileVariant.objects.filter(tile_variant_name__range=(min_tile, max_tile))
    times = []
    chr_path_lengths=Tile.CHR_PATH_LENGTHS
    for path in range(chr_path_lengths[chrom-1], chr_path_lengths[chrom]):
        min_path_pos, min_path_tile = fns.get_min_position_and_tile_variant_from_path_int(path)
        max_path_pos, max_path_tile = fns.get_min_position_and_tile_variant_from_path_int(path + 1)
        max_path_pos -= 1
        max_path_tile -= 1
        t1 = time.time()
        c = positions.filter(tilename__range=(min_path_pos, max_path_pos)).count()
        t2 = time.time()
        info = tiles.filter(tile_variant_name__range=(min_path_tile, max_path_tile)).aggregate(
            avg_var_val=Avg('variant_value'),
            max_var_val=Max('variant_value'),
            min_len=Min('length'),
            avg_len=Avg('length'),
            max_len=Max('length'))
        t3 = time.time()
        times.append((t2-t1,t3-t2, path))
        print "Path", path, "done"
    print "Get Chr1 Statistics:", time2-time1
    print ""
    print chr_path_lengths[chrom]-chr_path_lengths[chrom-1], "Paths queried"
    print ""
    total_count = sum([i for i, j, k in times])
    total_aggr = sum([j for i, j, k in times])
    max_count = max(times, key=lambda x:x[0])
    min_count = min(times, key=lambda x:x[0])
    print "Maximum time spent on count():", max_count[0], "on path", max_count[2]
    print "Average time spent on count():", total_count/float(len(times))
    print "Minimum time spent on count():", min_count[0], "on path", min_count[2]
    print "Total time spent on count():", total_count
    print ""
    max_count = max(times, key=lambda x:x[1])
    min_count = min(times, key=lambda x:x[1])
    print "Maximum time spent on aggr:", max_count[1], "on path", max_count[2]
    print "Average time spent on aggr:", total_count/float(len(times))
    print "Minimum time spent on aggr:", min_count[1], "on path", min_count[2]
    print "Total time spent on aggr:", total_aggr
        

run_chr()












