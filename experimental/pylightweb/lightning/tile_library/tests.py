from django.test import TestCase

from tile_library.models import Tile

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

    def test_get_path(self):
        """
        Tile.getPath() returns int of path
        Testing with Tile 0a1.00.1004
        """
        tilename = int('a1001004', 16)
        new_tile = Tile(tilename=tilename, start_tag="ACGT", end_tag="CCCG")
        self.assertEqual(type(new_tile.getPath()), int)
        self.assertEqual(new_tile.getPath(), int('a1', 16))

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
        
class TestFixtureLoading(TestCase):
    fixtures = ['path1c4.json.gz']
    def test_fixture_loading(self):
        first = Tile.objects.get(pk=7583301632)
        self.assertNotEqual(first, None)
    
