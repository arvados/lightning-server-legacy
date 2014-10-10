from tile_library.models import Tile, TileVariant, TileLocusAnnotation, VarAnnotation, GenomeStatistic
from tile_library import views
from django.db.models import Avg, Count, Max, Min
import time

def get_info(tiles, tilevars):
    n = time.time()
    pos_num = tiles.count()
    x = time.time()
    print "\tCount:", x-n
    tile_var_info = tilevars.aggregate(tile_num=Count('tile_variant_name'),
                                       avg_var_val=Avg('variant_value'),
                                       max_var_val=Max('variant_value'),
                                       min_len=Min('length'),
                                       avg_len=Avg('length'),
                                       max_len=Max('length')
                                       )
    y = time.time()
    print "\tAggregation:", y-x
    #annotate_info = annotations.aggregate(max_tile_ann=Max(
    return pos_num, tile_var_info

def initialize():
    if GenomeStatistic.objects.count() == 0:
        for i in range(27):
            if i == 0:
                print "Entire Genome:"
                pos_num, tile_var_info = get_info(Tile.objects, TileVariant.objects)
            else:
                print "Chromosome", i, ":"
                min_pos, min_tile = views.convert_chromosome_to_tilename(i)
                max_pos, max_tile = views.convert_chromosome_to_tilename(i+1)
                max_pos -= 1
                max_tile -= 1
                pos_num, tile_var_info = get_info(Tile.objects.filter(tilename__range=(min_pos,max_pos)),
                                                  TileVariant.objects.filter(tile_variant_name__range=(min_tile, max_tile)))
            print tile_var_info
            s = GenomeStatistic(statistics_type=i, position_num=pos_num, tile_num=tile_var_info['tile_num'],
                                avg_variant_val=tile_var_info['avg_var_val'], max_variant_val=tile_var_info['max_var_val'],
                                min_length=tile_var_info['min_len'], avg_length=tile_var_info['avg_len'],
                                max_length=tile_var_info['max_len'])
            s.save()

    assert GenomeStatistic.objects.count() == 27
    for path in range(Tile.CHR_PATH_LENGTHS[-1]):
        print "Path", path
        min_path_pos, min_path_tile = views.convert_path_to_tilename(path)
        max_path_pos, max_path_tile = views.convert_path_to_tilename(path + 1)
        max_path_pos -= 1
        max_path_tile -= 1
        pos_num, tile_var_info = get_info(Tile.objects.filter(tilename__range=(min_path_pos,max_path_pos)),
                                          TileVariant.objects.filter(tile_variant_name__range=(min_path_tile, max_path_tile)))
        s = GenomeStatistic(statistics_type=27, path_name=path, position_num=pos_num, tile_num=tile_var_info['tile_num'],
                            avg_variant_val=tile_var_info['avg_var_val'], max_variant_val=tile_var_info['max_var_val'],
                            min_length=tile_var_info['min_len'], avg_length=tile_var_info['avg_len'],
                            max_length=tile_var_info['max_len'])
        s.save()
            
def update():
    for i in range(27):
        if i == 0:
            print "Entire Genome:"
            pos_num, tile_var_info = get_info(Tile.objects, TileVariant.objects)
        else:
            print "Chromosome", i, ":"
            min_pos, min_tile = views.convert_chromosome_to_tilename(i)
            max_pos, max_tile = views.convert_chromosome_to_tilename(i+1)
            max_pos -= 1
            max_tile -= 1
            pos_num, tile_var_info = get_info(Tile.objects.filter(tilename__range=(min_pos,max_pos)),
                                              TileVariant.objects.filter(tile_variant_name__range=(min_tile, max_tile)))
        s = GenomeStatistic.objects.get(pk=i+1)
        assert s.statistics_type == i
        s.position_num = pos_num
        s.tile_num = tile_var_info['tile_num']
        s.avg_variant_val = tile_var_info['avg_var_val']
        s.max_variant_val = tile_var_info['max_var_val']
        s.min_length = tile_var_info['min_len']
        s.avg_length = tile_var_info['avg_len']
        s.max_length = tile_var_info['max_len']
        s.save()
    for path in range(Tile.CHR_PATH_LENGTHS[-1]):
        print "Path", path
        min_path_pos, min_path_tile = views.convert_path_to_tilename(path)
        max_path_pos, max_path_tile = views.convert_path_to_tilename(path + 1)
        max_path_pos -= 1
        max_path_tile -= 1
        pos_num, tile_var_info = get_info(Tile.objects.filter(tilename__range=(min_path_pos,max_path_pos)),
                                          TileVariant.objects.filter(tile_variant_name__range=(min_path_tile, max_path_tile)))
        s = GenomeStatistic.objects.get(pk=28+path)
        assert s.statistics_type == 27
        assert s.path_name == path
        s.position_num = pos_num
        s.tile_num = tile_var_info['tile_num']
        s.avg_variant_val = tile_var_info['avg_var_val']
        s.max_variant_val = tile_var_info['max_var_val']
        s.min_length = tile_var_info['min_len']
        s.avg_length = tile_var_info['avg_len']
        s.max_length = tile_var_info['max_len']
        s.save()
