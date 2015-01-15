from django.test import TestCase

# To set up:
#   database similar to brca-lightning:
#       Assumptions that don't need to be preserved for testing:
#           len(tile_variant) >= 200 + TAG_LENGTH*2
#           TAG_LENGTH == 24
#
#       Assumptions that need to be preserved:
#           Each tile must overlap by exactly TAG_LENGTH bases
#           If a SNP or INDEL occurs on the tag, the tile should span
#           Spanning tiles are given the position they start on
#
#       TAG_LENGTH = 4 and TAG_LENGTH = 5 (tests should be run on both to ensure no assumptions about TAG_LENGTH were made)
#       (making min tile length 12 and 15, for simplicity)
#       TileLocusAnnotations must be 0 indexed, [start, end)
#

# Query Between Loci
#   Order of checking: assembly, chromosome, low_int too low, high_int too high

#   If assembly cannot be cast as integer, raise Exception
#       (It would be nice if it responded with accepted assembly integers)
#   If assembly is an integer, but not loaded into the database, raise Exception
#       (It would be nice if it responded with loaded assembly integers)
#   If
