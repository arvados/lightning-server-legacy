#!/bin/bash

python manage.py flush 
psql -c "\copy tile_library_tile from play_data/247ref_tile.csv with csv" -d brca-lightning
psql -c "\copy tile_library_tilelocusannotation(tile_id, assembly, chromosome, begin_int, end_int, chromosome_name) from play_data/247ref_tilelocusannotation.csv with csv" -d brca-lightning
psql -c "\copy tile_library_tilevariant from play_data/247ref_tilevariant.csv with csv" -d brca-lightning
psql -c "\copy tile_library_tilevariant from play_data/247tilevariant.csv with csv" -d brca-lightning
psql -c "\copy tile_library_genomevariant(id, start_tile_position_id, start_increment, end_tile_position_id, end_increment, names, reference_bases, alternate_bases, info, created, last_modified) from play_data/247genomevariant.csv with csv" -d brca-lightning
psql -c '\copy tile_library_genomevarianttranslation("start", "end", genome_variant_id, tile_variant_id) from play_data/247genomevarianttranslation.csv with csv' -d brca-lightning

psql -c "\copy tile_library_tile from play_data/241ref_tile.csv with csv" -d brca-lightning
psql -c "\copy tile_library_tilelocusannotation(tile_id, assembly, chromosome, begin_int, end_int, chromosome_name) from play_data/241ref_tilelocusannotation.csv with csv" -d brca-lightning
psql -c "\copy tile_library_tilevariant from play_data/241ref_tilevariant.csv with csv" -d brca-lightning
psql -c "\copy tile_library_tilevariant from play_data/241tilevariant.csv with csv" -d brca-lightning
psql -c "\copy tile_library_genomevariant(id, start_tile_position_id, start_increment, end_tile_position_id, end_increment, names, reference_bases, alternate_bases, info, created, last_modified) from play_data/241genomevariant.csv with csv" -d brca-lightning
psql -c '\copy tile_library_genomevarianttranslation("start", "end", genome_variant_id, tile_variant_id) from play_data/241genomevarianttranslation.csv with csv' -d brca-lightning


