import time


from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Avg, Count, Max, Min

from tile_library import functions
from tile_library.models import Tile, TileVariant, GenomeStatistic
from errors import InvalidGenomeError, MissingStatisticsError, ExistingStatisticsError

def get_info(tiles, tilevars, silent=False):
    n = time.time()
    tile_info = tiles.aggregate(num_of_positions=Count('tilename'))
    x = time.time()
    if not silent:
        print "\tTile Queries:", x-n
    tile_var_info = tilevars.aggregate(
        num_of_tiles=Count('tile_variant_name'),
        max_pos_spanned=Max('num_positions_spanned'),
    )
    y = time.time()
    if not silent:
        print "\tTileVariant Queries:", y-x
    return tile_info, tile_var_info

def initialize(silent=False, quiet=True):
    impossible_name, impossible_varname = functions.get_min_position_and_tile_variant_from_chromosome_int(27)
    if Tile.objects.filter(tilename__gte=impossible_name).exists():
        raise InvalidGenomeError("Invalid human genome: no tile id should exist with this path according to Tile.CHR_PATH_LENGTHS")
    if GenomeStatistic.objects.count() > 0:
        raise ExistingStatisticsError("Genome Statistics have already been generated. Run update()")
    for i in range(27):
        if i == 0:
            if not silent:
                print "Entire Genome:"
            tile_info, tile_var_info = get_info(Tile.objects, TileVariant.objects, silent=quiet)
        else:
            if not silent:
                print "Chromosome", i, ":"
            min_pos, min_tile = functions.get_min_position_and_tile_variant_from_chromosome_int(i)
            max_pos, max_tile = functions.get_min_position_and_tile_variant_from_chromosome_int(i+1)
            max_pos -= 1
            max_tile -= 1
            tile_info, tile_var_info = get_info(Tile.objects.filter(tilename__range=(min_pos,max_pos)),
                                                                    TileVariant.objects.filter(tile_variant_name__range=(min_tile, max_tile)),
                                                                    silent=quiet)
        if not silent:
            print tile_info, tile_var_info
        s = GenomeStatistic(
            statistics_type=i,
            num_of_positions=tile_info['num_of_positions'],
            num_of_tiles=tile_var_info['num_of_tiles'],
            max_num_positions_spanned=tile_var_info['max_pos_spanned'],
        )
        s.save()
    for path in range(Tile.CHR_PATH_LENGTHS[-1]):
        if not silent and not quiet:
            print "Path", path
        min_path_pos, min_path_tile = functions.get_min_position_and_tile_variant_from_path_int(path)
        max_path_pos, max_path_tile = functions.get_min_position_and_tile_variant_from_path_int(path + 1)
        max_path_pos -= 1
        max_path_tile -= 1
        tile_info, tile_var_info = get_info(Tile.objects.filter(tilename__range=(min_path_pos,max_path_pos)),
                                                                TileVariant.objects.filter(tile_variant_name__range=(min_path_tile, max_path_tile)),
                                                                silent=quiet)
        s = GenomeStatistic(
            statistics_type=27,
            path_name=path,
            num_of_positions=tile_info['num_of_positions'],
            num_of_tiles=tile_var_info['num_of_tiles'],
            max_num_positions_spanned=tile_var_info['max_pos_spanned'],
        )
        s.save()

def update(path_only=False, silent=False, quiet=True):
    impossible_name, impossible_varname = functions.get_min_position_and_tile_variant_from_chromosome_int(27)
    if Tile.objects.filter(tilename__gte=impossible_name).exists():
        raise InvalidGenomeError("Invalid human genome: no tile id should exist with this path according to Tile.CHR_PATH_LENGTHS")
    try:
        if not path_only:
            for i in range(27):
                if i == 0:
                    if not silent:
                        print "Entire Genome:"
                    tile_info, tile_var_info = get_info(Tile.objects, TileVariant.objects, silent=quiet)
                else:
                    if not silent:
                        print "Chromosome", i, ":"
                    min_pos, min_tile = functions.get_min_position_and_tile_variant_from_chromosome_int(i)
                    max_pos, max_tile = functions.get_min_position_and_tile_variant_from_chromosome_int(i+1)
                    max_pos -= 1
                    max_tile -= 1
                    tile_info, tile_var_info = get_info(Tile.objects.filter(tilename__range=(min_pos,max_pos)),
                                                        TileVariant.objects.filter(tile_variant_name__range=(min_tile, max_tile)),
                                                        silent=quiet)
                if not silent:
                    print tile_info, tile_var_info
                s = GenomeStatistic.objects.get(statistics_type=i)
                s.num_of_positions = tile_info['num_of_positions']
                s.num_of_tiles = tile_var_info['num_of_tiles']
                s.max_num_positions_spanned = tile_var_info['max_pos_spanned']
                s.save()
        for path in range(Tile.CHR_PATH_LENGTHS[-1]):
            if not silent and not quiet:
                print "Path", path
            min_path_pos, min_path_tile = functions.get_min_position_and_tile_variant_from_path_int(path)
            max_path_pos, max_path_tile = functions.get_min_position_and_tile_variant_from_path_int(path + 1)
            max_path_pos -= 1
            max_path_tile -= 1
            tile_info, tile_var_info = get_info(Tile.objects.filter(tilename__range=(min_path_pos,max_path_pos)),
                                                TileVariant.objects.filter(tile_variant_name__range=(min_path_tile, max_path_tile)),
                                                silent=quiet)
            if not silent and not quiet:
                print tile_info, tile_var_info
            s = GenomeStatistic.objects.filter(statistics_type=27).get(path_name=path)
            s.num_of_positions = tile_info['num_of_positions']
            s.num_of_tiles = tile_var_info['num_of_tiles']
            s.max_num_positions_spanned = tile_var_info['max_pos_spanned']
            s.save()
    except GenomeStatistic.DoesNotExist:
        raise MissingStatisticsError("tile_library.generate_stats.update() requires tile_library.generate_stats.initialize() to have run")
