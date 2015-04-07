import time

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Avg, Count, Max, Min

import tile_library.basic_functions as functions
import tile_library.human_readable_functions as humanize
from tile_library.constants import GENOME, PATH, SUPPORTED_STATISTICS_TYPE_INTS, CHR_PATH_LENGTHS
from tile_library.models import Tile, TileVariant, GenomeStatistic
from errors import InvalidGenomeError, MissingStatisticsError, ExistingStatisticsError

genomes_and_chromosomes = SUPPORTED_STATISTICS_TYPE_INTS
genomes_and_chromosomes.remove(PATH)

def get_info(tiles, tilevars, silent=False):
    n = time.time()
    tile_info = tiles.aggregate(num_of_positions=Count('tile_position_int'))
    x = time.time()
    if not silent:
        print "\tTile Queries:", x-n
    tile_var_info = tilevars.aggregate(
        num_of_tiles=Count('tile_variant_int'),
        max_pos_spanned=Max('num_positions_spanned'),
    )
    y = time.time()
    if not silent:
        print "\tTileVariant Queries:", y-x
    return tile_info, tile_var_info

def initialize(silent=False, quiet=True):
    impossible_name, impossible_varname = functions.get_min_position_and_tile_variant_from_chromosome_int(PATH)
    if Tile.objects.filter(tile_position_int__gte=impossible_name).exists():
        raise InvalidGenomeError("Invalid human genome: no tile id should exist with this path according to constants (PATH value)")
    if GenomeStatistic.objects.count() > 0:
        raise ExistingStatisticsError("Genome Statistics have already been generated. Run update()")
    for i in genomes_and_chromosomes:
        if not silent:
            print humanize.get_readable_genome_statistics_name(i)
        if i == GENOME:
            tile_info, tile_var_info = get_info(Tile.objects, TileVariant.objects, silent=quiet)
        else:
            min_pos, min_tile = functions.get_min_position_and_tile_variant_from_chromosome_int(i)
            max_pos, max_tile = functions.get_min_position_and_tile_variant_from_chromosome_int(i+1)
            max_pos -= 1
            max_tile -= 1
            tile_info, tile_var_info = get_info(Tile.objects.filter(tile_position_int__range=(min_pos,max_pos)),
                                                                    TileVariant.objects.filter(tile_variant_int__range=(min_tile, max_tile)),
                                                                    silent=quiet)
        if not silent:
            print tile_info, tile_var_info
        GenomeStatistic(
            statistics_type=i,
            num_of_positions=tile_info['num_of_positions'],
            num_of_tiles=tile_var_info['num_of_tiles'],
            max_num_positions_spanned=tile_var_info['max_pos_spanned'],
        ).save()
    for path in range(CHR_PATH_LENGTHS[-1]):
        if not silent and not quiet:
            print humanize.get_readable_genome_statistics_name(i, path=path)
        min_path_pos, min_path_tile = functions.get_min_position_and_tile_variant_from_path_int(path)
        max_path_pos, max_path_tile = functions.get_min_position_and_tile_variant_from_path_int(path + 1)
        max_path_pos -= 1
        max_path_tile -= 1
        tile_info, tile_var_info = get_info(Tile.objects.filter(tile_position_int__range=(min_path_pos,max_path_pos)),
                                                                TileVariant.objects.filter(tile_variant_int__range=(min_path_tile, max_path_tile)),
                                                                silent=quiet)
        GenomeStatistic(
            statistics_type=PATH,
            path_name=path,
            num_of_positions=tile_info['num_of_positions'],
            num_of_tiles=tile_var_info['num_of_tiles'],
            max_num_positions_spanned=tile_var_info['max_pos_spanned'],
        ).save()

def update(path_only=False, silent=False, quiet=True):
    impossible_name, impossible_varname = functions.get_min_position_and_tile_variant_from_chromosome_int(PATH)
    if Tile.objects.filter(tile_position_int__gte=impossible_name).exists():
        raise InvalidGenomeError("Invalid human genome: no tile id should exist with this path according to constants (PATH value)")
    try:
        if not path_only:
            for i in genomes_and_chromosomes:
                if not silent:
                    print humanize.get_readable_genome_statistics_name(i)
                if i == GENOME:
                    tile_info, tile_var_info = get_info(Tile.objects, TileVariant.objects, silent=quiet)
                else:
                    min_pos, min_tile = functions.get_min_position_and_tile_variant_from_chromosome_int(i)
                    max_pos, max_tile = functions.get_min_position_and_tile_variant_from_chromosome_int(i+1)
                    max_pos -= 1
                    max_tile -= 1
                    tile_info, tile_var_info = get_info(Tile.objects.filter(tile_position_int__range=(min_pos,max_pos)),
                                                        TileVariant.objects.filter(tile_variant_int__range=(min_tile, max_tile)),
                                                        silent=quiet)
                if not silent:
                    print tile_info, tile_var_info
                s = GenomeStatistic.objects.get(statistics_type=i)
                s.num_of_positions = tile_info['num_of_positions']
                s.num_of_tiles = tile_var_info['num_of_tiles']
                s.max_num_positions_spanned = tile_var_info['max_pos_spanned']
                s.save()
        for path in range(CHR_PATH_LENGTHS[-1]):
            if not silent and not quiet:
                humanize.get_readable_genome_statistics_name(i, path=path)
            min_path_pos, min_path_tile = functions.get_min_position_and_tile_variant_from_path_int(path)
            max_path_pos, max_path_tile = functions.get_min_position_and_tile_variant_from_path_int(path + 1)
            max_path_pos -= 1
            max_path_tile -= 1
            tile_info, tile_var_info = get_info(Tile.objects.filter(tile_position_int__range=(min_path_pos,max_path_pos)),
                                                TileVariant.objects.filter(tile_variant_int__range=(min_path_tile, max_path_tile)),
                                                silent=quiet)
            if not silent and not quiet:
                print tile_info, tile_var_info
            s = GenomeStatistic.objects.filter(statistics_type=PATH).get(path_name=path)
            s.num_of_positions = tile_info['num_of_positions']
            s.num_of_tiles = tile_var_info['num_of_tiles']
            s.max_num_positions_spanned = tile_var_info['max_pos_spanned']
            s.save()
    except GenomeStatistic.DoesNotExist:
        raise MissingStatisticsError("tile_library.generate_stats.update() requires tile_library.generate_stats.initialize() to have run")
