#Testing performance

import timeit
from tile_library.models import Tile, TileVariant, TileLocusAnnotation, VarAnnotation
from tile_library import views

#largest chromosome
chrom = 2

#biggest path
path = 21

min_pos, min_tile = views.convert_chromosome_to_tilename(chrom)
max_pos, max_tile = views.convert_chromosome_to_tilename(chrom+1)

max_pos -= 1
max_tile -= 1

min_path_pos, min_path_tile = views.convert_path_to_tilename(path)
max_path_pos, max_path_tile = views.convert_path_to_tilename(path+1)

max_path_pos -= 1
max_path_tile -= 1

print "Entire Genome:"
print "\tTile count()", timeit.timeit("Tile.objects.all().count()")
print "\tTileVar count()", timeit.timeit("TileVariant.objects.all().count()")
print ""
print "Biggest Chromosome:"
print "\tTile count()", timeit.timeit("Tile.objects.filter(tilename__range=(min_pos, max_pos)).count()")
print "\tTileVar count()", timeit.timeit("TileVariant.objects.gilter(tile_variant_name__range=(min_tile, max_tile)).count()")
print ""
print "Biggest Path:"
print "\tTile count()", timeit.timeit("Tile.objects.filter(tilename__range=(min_path_pos, max_path_pos)).count()")
print "\tTileVar count()", timeit.timeit("TileVariant.objects.filter(tile_variant_name__range(min_path_tile, max_path_tile).count()")
