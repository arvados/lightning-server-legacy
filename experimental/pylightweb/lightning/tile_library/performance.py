#Testing performance
import time

from django.core.exceptions import ObjectDoesNotExist
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

def run(silent=False):
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
    if not silent:
        print "Biggest Path:"
        print "\tTile count()", timeitarg(Tile.objects.filter(tilename__range=(min_path_pos, max_path_pos)).count)
        print "\tTile count via aggregate", timeitarg(Tile.objects.filter(tilename__range=(min_path_pos, max_path_pos)).aggregate, Count('tilename'))
        print "\tTile maxvar", timeitarg(Tile.objects.filter(tilename__range=(min_path_pos, max_path_pos)).annotate(num_variants=Count('variants')).aggregate, Max('num_variants'))
        print "\tTile avgvar", timeitarg(Tile.objects.filter(tilename__range=(min_path_pos, max_path_pos)).annotate(num_variants=Count('variants')).aggregate, Avg('num_variants'))
        print "\tTile aggregate", timeitarg(Tile.objects.filter(tilename__range=(min_path_pos, max_path_pos)).annotate(num_variants=Count('variants')).aggregate, Count('tilename'), Avg('num_variants'), Max('num_variants'))
        print "\tTileVar minlen", timeitarg(TileVariant.objects.filter(tile_variant_name__range=(min_path_tile, max_path_tile)).aggregate, Min('length'))
        print "\tTileVar avglen", timeitarg(TileVariant.objects.filter(tile_variant_name__range=(min_path_tile, max_path_tile)).aggregate, Avg('length'))
        print "\tTileVar maxlen", timeitarg(TileVariant.objects.filter(tile_variant_name__range=(min_path_tile, max_path_tile)).aggregate, Max('length'))
        print "\tTileVar aggregate", timeitarg(TileVariant.objects.filter(tile_variant_name__range=(min_path_tile, max_path_tile)).aggregate, Avg('length'), Min('length'), Max('length'))
        print ""
        print "Biggest Chromosome:"
        print "\tTile count()", timeitarg(Tile.objects.filter(tilename__range=(min_pos, max_pos)).count)
        print "\tTile count via aggregate", timeitarg(Tile.objects.filter(tilename__range=(min_pos, max_pos)).aggregate, Count('tilename'))
        print "\tTile maxvar", timeitarg(Tile.objects.filter(tilename__range=(min_pos, max_pos)).annotate(num_variants=Count('variants')).aggregate, Max('num_variants'))
        print "\tTile avgvar", timeitarg(Tile.objects.filter(tilename__range=(min_pos, max_pos)).annotate(num_variants=Count('variants')).aggregate, Avg('num_variants'))
        print "\tTile aggregate", timeitarg(Tile.objects.filter(tilename__range=(min_pos, max_pos)).annotate(num_variants=Count('variants')).aggregate, Count('tilename'), Avg('num_variants'), Max('num_variants'))
        print "\tTileVar minlen", timeitarg(TileVariant.objects.filter(tile_variant_name__range=(min_tile, max_tile)).aggregate, Min('length'))
        print "\tTileVar avglen", timeitarg(TileVariant.objects.filter(tile_variant_name__range=(min_tile, max_tile)).aggregate, Avg('length'))
        print "\tTileVar maxlen", timeitarg(TileVariant.objects.filter(tile_variant_name__range=(min_tile, max_tile)).aggregate, Max('length'))
        print "\tTileVar aggregate", timeitarg(TileVariant.objects.filter(tile_variant_name__range=(min_tile, max_tile)).aggregate, Avg('length'), Min('length'), Max('length'))
        print ""
        print "Entire Genome:"
        print "\tTile count()", timeitarg(Tile.objects.count)
        print "\tTile count via aggregate", timeitarg(Tile.objects.aggregate, Count('tilename'))
        print "\tTile maxvar", timeitarg(Tile.objects.annotate(num_variants=Count('variants')).aggregate, Max('num_variants'))
        print "\tTile avgvar", timeitarg(Tile.objects.annotate(num_variants=Count('variants')).aggregate, Avg('num_variants'))
        print "\tTile aggregate", timeitarg(Tile.objects.annotate(num_variants=Count('variants')).aggregate, Count('tilename'), Avg('num_variants'), Max('num_variants'))
        print "\tTileVar minlen", timeitarg(TileVariant.objects.aggregate, Min('length'))
        print "\tTileVar avglen", timeitarg(TileVariant.objects.aggregate, Avg('length'))
        print "\tTileVar maxlen", timeitarg(TileVariant.objects.aggregate, Max('length'))
        print "\tTileVar aggregate", timeitarg(TileVariant.objects.aggregate, Count('tile_variant_name'), Avg('length'), Min('length'), Avg('length'))
        
def run_chr1(silent=False):
    chrom = 1
    min_pos, min_tile = fns.get_min_position_and_tile_variant_from_chromosome_int(chrom)
    max_pos, max_tile = fns.get_min_position_and_tile_variant_from_chromosome_int(chrom+1)
    max_pos -= 1
    max_tile -= 1
    #Get Genome Statistics for chr1
    time1 = time.time()
    try:
        chr_stats = GenomeStatistic.objects.get(pk=chrom+1)
    except ObjectDoesNotExist:
        pass
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
        tile_info = positions.filter(tilename__range=(min_path_pos, max_path_pos)
                                     ).annotate(num_variants=Count('variants')
                                                ).aggregate(pos_num=Count('tilename'),
                                                            avg_var_val=Avg('num_variants'),
                                                            max_var_val=Max('num_variants'))
        t2 = time.time()
        info = tiles.filter(tile_variant_name__range=(min_path_tile, max_path_tile)).aggregate(
            min_len=Min('length'),
            avg_len=Avg('length'),
            max_len=Max('length'))
        t3 = time.time()
        times.append((t2-t1,t3-t2, path))
        if not silent:
            print "Path", path, "done"
    if not silent:
        print "Get Chr1 Statistics:", time2-time1
        print ""
        print chr_path_lengths[chrom]-chr_path_lengths[chrom-1], "Paths queried"
        print ""
    total_count = sum([i for i, j, k in times])
    total_aggr = sum([j for i, j, k in times])
    max_count = max(times, key=lambda x:x[0])
    min_count = min(times, key=lambda x:x[0])
    if not silent:
        print "Maximum time spent on Tile aggr:", max_count[0], "on path", max_count[2]
        print "Average time spent on Tile aggr:", total_count/float(len(times))
        print "Minimum time spent on Tile aggr:", min_count[0], "on path", min_count[2]
        print "Total time spent on Tile aggr:", total_count
        print ""
    max_count = max(times, key=lambda x:x[1])
    min_count = min(times, key=lambda x:x[1])
    if not silent:
        print "Maximum time spent on TileVariant aggr:", max_count[1], "on path", max_count[2]
        print "Average time spent on TileVariant aggr:", total_count/float(len(times))
        print "Minimum time spent on TileVariant aggr:", min_count[1], "on path", min_count[2]
        print "Total time spent on TileVariant aggr:", total_aggr
