from django.test import TestCase

from tile_library.models import Tile, TileVariant

import tile_library.functions as functions
#Currently testing functions defined by models and 'functions'. Very basic

#NO testing for views yet
#from django.core.urlresolvers import reverse

#Testing for VarAnnotation will wait until revamp of annotation model (Story #4067)
#Currently no functions are defined for TileLocusAnnotation

#Want to enforce for all Tiles:
#   for all assemblies in TileLocusAnnotation.SUPPORTED_ASSEMBLY_CHOICES
#      len(tile.tile_locus_annotation.filter(assembly=assembly)) <= 1
#   (Essentially, we should only have one translation per
#    supported assembly per tile)
#   This might be feasible using unique when combined-with feature...



class TestTileMethods(TestCase):
    def test_get_tile_string(self):
        """
        Tile.getTileString() returns str
        Testing with Tile 1c4.03.002f
        """
        tile_int = int('1c403002f', 16)
        new_tile = Tile(tilename=tile_int, start_tag="ACGT", end_tag="CCCG")
        self.assertEqual(type(new_tile.getTileString()), str)
        self.assertEqual(new_tile.getTileString(), '1c4.03.002f')

    def test_tile_constants(self):
        """
        Tile defines CHR_PATH_LENGTHS and CYTOMAP, check that these definitions
        are as expected
        """
        chr_list = Tile.CHR_PATH_LENGTHS
        cytomap = Tile.CYTOMAP
        #Check type of lists
        self.assertEqual(type(chr_list), list)
        self.assertEqual(type(cytomap), list)
        #Check format of CHR_PATH_LENGTHS
        for i, length in enumerate(chr_list):
            self.assertEqual(type(length), int)
            if i > 0:
                self.assertGreaterEqual(length, chr_list[i-1])
            else:
                self.assertEqual(length, 0)
        self.assertEqual(len(chr_list), 27)
        self.assertEqual(len(cytomap), chr_list[-1])
        for s in cytomap:
            self.assertEqual(type(s), str)

class TestTileVariantMethods(TestCase):
    def test_get_string(self):
        """
        TileVariant.getString() returns str
        Testing with Tile 1c4.03.002f variant 0f3
        """
        tile_int = int('1c403002f', 16)
        new_tile = Tile(tilename=tile_int, start_tag="ACGT", end_tag="CCCG")
        tile_variant_int = int('1c403002f0f3', 16)
        new_tile_variant = TileVariant(tile_variant_name=tile_variant_int,tile=new_tile, variant_value=int('f3',16),
                                       length=250, md5sum="05fee", sequence="TO BIG TO STORE")
        self.assertEqual(type(new_tile_variant.getString()), str)
        self.assertEqual(new_tile_variant.getString(), '1c4.03.002f.0f3')

    def test_is_reference(self):
        """
        Tile.getPath() returns int of path
        Testing with Tile 0a1.00.1004
        """
        tilename = int('a1001004', 16)
        new_tile = Tile(tilename=tilename, start_tag="ACGT", end_tag="CCCG")
        tile_variant_int = int('a1001004003', 16)
        new_tile_variant = TileVariant(tile_variant_name=tile_variant_int,tile=new_tile, variant_value=3,
                                       length=250, md5sum="05fee", sequence="TO BIG TO STORE")
        self.assertEqual(type(new_tile_variant.isReference()), bool)
        self.assertEqual(new_tile_variant.isReference(), False)
        
        tile_variant_int = int('a1001004001', 16)
        new_tile_variant = TileVariant(tile_variant_name=tile_variant_int,tile=new_tile, variant_value=1,
                                       length=250, md5sum="05fee", sequence="TO BIG TO STORE")
        self.assertEqual(new_tile_variant.isReference(), False)

        tile_variant_int = int('a1001004000', 16)
        new_tile_variant = TileVariant(tile_variant_name=tile_variant_int,tile=new_tile, variant_value=0,
                                       length=250, md5sum="05fee", sequence="TO BIG TO STORE")
        self.assertEqual(new_tile_variant.isReference(), True)
    
class TestViewFunctions(TestCase):
    fixtures = ['highest_path.json.gz']
    def test_get_min_position_and_tile_variant_from_chromosome_int(self):
        wierdname, weirdvarname = functions.get_min_position_and_tile_variant_from_chromosome_int(26)
        name, varname = functions.get_min_position_and_tile_variant_from_chromosome_int(1)
        self.assertEqual(name, 0)
        self.assertEqual(varname, 0)
        self.assertRaises(BaseException, functions.get_min_position_and_tile_variant_from_chromosome_int, 0)
        self.assertRaises(BaseException, functions.get_min_position_and_tile_variant_from_chromosome_int, 28)
    def test_assumptions_of_convert_chromosome(self):
        maximumname, maximumvarname = functions.get_min_position_and_tile_variant_from_chromosome_int(27)
        self.assertEqual(Tile.objects.filter(tilename__gte=maximumname).exists(), False)
        self.assertEqual(TileVariant.objects.filter(tile_variant_name__gte=maximumvarname).exists(), False)
        maximumname, maximumvarname = functions.get_min_position_and_tile_variant_from_chromosome_int(26)
        self.assertEqual(Tile.objects.filter(tilename__gte=maximumname).exists(), False)
        self.assertEqual(TileVariant.objects.filter(tile_variant_name__gte=maximumvarname).exists(), False)
        maximumname, maximumvarname = functions.get_min_position_and_tile_variant_from_chromosome_int(25)
        self.assertEqual(Tile.objects.filter(tilename__gte=maximumname).exists(), True)
        self.assertEqual(TileVariant.objects.filter(tile_variant_name__gte=maximumvarname).exists(), True)
    def test_get_min_position_and_tile_variant_from_path_int(self):
        name, varname = functions.get_min_position_and_tile_variant_from_path_int(0)
        self.assertEqual(name, 0)
        self.assertEqual(varname, 0)
    
#class TestViewTileLibrary(TestCase):
    
