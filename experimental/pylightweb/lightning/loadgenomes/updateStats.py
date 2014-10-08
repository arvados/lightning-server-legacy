from django.core.files import File
from loadgenomes.models import Tile, TileVariant
import string

chr_path_lengths = [0,63,125,187,234,279,327,371,411,454,496,532,573,609,641,673,698,722,742,761,781,795,811,851,862,863]
def updateStats(path_to_stat_file, check=False, expected_popul_size=None):
    with open(path_to_stat_file, 'w') as f:
        retval = True
        myfile = File(f)
        myfile.write("path_as_int,chromosome,total_positions,default_is_ref,default_is_not_ref,total_tiles,avg_tile_len,avg_people_with_ref\n")
        chrom_int=1
        path = 0
        next_position_in_hex = '1'+'00'+'0000'
        positions = Tile.objects.filter(tilename__gte=0).filter(tilename__lt=int(next_position_in_hex, 16))
        tiles = TileVariant.objects.filter(tile_variant_name__gte=0).filter(tile_variant_name__lt=int(next_position_in_hex+'000', 16))
        while path < chr_path_lengths[-1]:
            total_pos = 0
            default_is_ref = 0
            default_is_not_ref = 0
            total_tiles = 0
            tile_len_sum = 0
            people_with_ref_sum = 0
            for pos in positions:
                total_pos += 1
                if pos.defaultIsRef():
                    default_is_ref += 1
                else:
                    default_is_not_ref += 1
            if check:
                curr_popul = 0
                curr_step = 0
            for tile in tiles:
                total_tiles += 1
                tile_len_sum += tile.length
                if tile.isReference():
                    people_with_ref_sum += tile.population_size
                if check:
                    this_step = tile.getStep()
                    if this_step != curr_tile:
                        curr_tile = tile.getStep()
                        if curr_popul != expected_popul_size and chrom_int != 24:
                            retval = False
                        curr_popul = tile.population_size
                    else:
                        curr_popul += tile.population_size
            if total_tiles > 0:            
                myfile.write(string.join([str(path), str(chrom_int), str(total_pos), str(default_is_ref), str(default_is_not_ref), str(total_tiles),
                                      str(tile_len_sum/float(total_tiles)), str(people_with_ref_sum/float(total_tiles))+'\n'], ','))
            else:
                myfile.write(string.join([str(path), str(chrom_int), str(total_pos), str(default_is_ref), str(default_is_not_ref), str(total_tiles),
                                      '-', '-\n'], ','))
            path += 1
            if chr_path_lengths[chrom_int] == path:
                chrom_int += 1
            position_in_hex = hex(path)[2:]+'00'+'0000'
            next_position_in_hex = hex(path+1)[2:]+'00'+'0000'
            positions = Tile.objects.filter(tilename__gte=int(position_in_hex, 16)).filter(tilename__lt=int(next_position_in_hex, 16))
            tiles = TileVariant.objects.filter(tile_variant_name__gte=int(position_in_hex+'000', 16)).filter(tile_variant_name__lt=int(next_position_in_hex+'000', 16))

    return retval
        
