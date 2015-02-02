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
#       TAG_LENGTH = 4 and TAG_LENGTH = 5 (tests should be run on both to ensure no assumptions
#           about TAG_LENGTH were made)
#       (making min tile length 12 and 15, for simplicity)
#       TileLocusAnnotations must be 0 indexed, [start, end)
#

# Check queries work with different path versions as well >.<

# Query Between Loci
#   Order of checking: assembly, chromosome, low_int too low, high_int too high

#   If assembly cannot be cast as integer, raise Exception
#       (It would be nice if it responded with accepted assembly integers)
#   If assembly is an integer, but not loaded into the database, raise Exception
#       (It would be nice if it responded with loaded assembly integers)
#   If

# Query Around Loci
#   Currently unable to test behavior at the end of a chromosome, since TileVariants are still truncated...


###COPIED FROM tile_library
def ignore_make_tiles(assembly_default=19):
    """
    creates the following structure:
            i,  min,     avg,  max
        Path
            0,  448,  448.67,  450 {'vars':3, 'lengths':[448,448,450]}, #1
            1,  301,  301.00,  301 {'vars':2, 'lengths':[301,301]}, #2
            2,  200,  257.67,  300 {'vars':3, 'lengths':[273,200,300]}, #3
            3,  149,  149.00,  149 {'vars':1, 'lengths':[149]}, #4
            4,  425,  425.00,  425 {'vars':1, 'lengths':[425]}, #5
            5,  500,  549.75,  600 {'vars':4, 'lengths':[549,500,600,550]}, #6
        Path 1:
            6,  198,  199.00,  200 {'vars':4, 'lengths':[199,198,200,199]}, #7
            7,  249,  249.00,  249 {'vars':2, 'lengths':[249,249]}, #8
            8,  199,  199.00,  199 {'vars':1, 'lengths':[199]}, #9
            9, 1200, 1200.00, 1200 {'vars':1, 'lengths':[1200]}, #10
           10,  264,  264.50,  265 {'vars':2, 'lengths':[264,265]}, #11
           11,  249,  250.50,  252 {'vars':6, 'lengths':[251,250,250,251,252,249]}, #12
           12,  275,  275.50,  276 {'vars':2, 'lengths':[275,276]}, #13
           13,  277,  277.00,  277 {'vars':2, 'lengths':[277,277]}, #14
           14,  267,  267.00,  267 {'vars':1, 'lengths':[267]}, #15
           15,  258,  258.00,  258 {'vars':1, 'lengths':[258]}, #16
           16,  248,  248.00,  248 {'vars':3, 'lengths':[248,248,248]}, #17
           17,  250,  250.00,  250 {'vars':1, 'lengths':[250]}, #18

    loci = [(0, 448),    #0 -> 448
            (448-24, 725),#1 -> 301
            (725-24, 974),#2 -> 273
            (974-24, 1099),#3 -> 149
            (1099-24,1500),#4 -> 425
            (1500-24,2025),#5 -> 549
            (2025-24,2200),#6 -> 199
            (2200-24,2425),#7 -> 249
            (2425-24,2600),#8 -> 199
            ]
    """
    tile_vars = [
            {'vars':3, 'lengths':[448,448,450]}, #1
            {'vars':2, 'lengths':[301,301]}, #2
            {'vars':3, 'lengths':[273,200,300]}, #3
            {'vars':1, 'lengths':[149]}, #4
            {'vars':1, 'lengths':[425]}, #5
            {'vars':4, 'lengths':[549,500,600,550]}, #6
            {'vars':4, 'lengths':[199,198,200,199]}, #7
            {'vars':2, 'lengths':[249,249]}, #8
            {'vars':1, 'lengths':[199]}, #9
            {'vars':1, 'lengths':[1200]}, #10
            {'vars':2, 'lengths':[264,265]}, #11
            {'vars':6, 'lengths':[251,250,250,251,252,249]}, #12
            {'vars':2, 'lengths':[275,276]}, #13
            {'vars':2, 'lengths':[277,277]}, #14
            {'vars':1, 'lengths':[267]}, #15
            {'vars':1, 'lengths':[258]}, #16
            {'vars':3, 'lengths':[248,248,248]}, #17
            {'vars':1, 'lengths':[250]}, #18
        ]
    locus = 0
    for j in range(18):
        if j == 0:
            t, foo, new_start_tag, annotation = mk_tile(
                j,
                locus,
                tile_vars[j]['lengths'][0]+locus,
                tile_vars[j]['vars'],
                tile_vars[j]['lengths'],
                assembly=assembly_default
            )
        else:
            t, foo, new_start_tag, annotation = mk_tile(
                j,
                locus,
                tile_vars[j]['lengths'][0]+locus,
                tile_vars[j]['vars'],
                tile_vars[j]['lengths'],
                start_tag=new_start_tag,
                assembly=assembly_default
            )
        #print j, locus, locus+tile_vars[j]['lengths'][0]
        locus += tile_vars[j]['lengths'][0] - 24

    locus = 0
    t, foo, new_start_tag, annotation = mk_tile(
        1000,
        locus,
        tile_vars[0]['lengths'][0]+locus,
        1,
        [tile_vars[0]['lengths'][0]],
        assembly=assembly_default,
        chrom=2
    )
    locus += tile_vars[0]['lengths'][0] - 24
    for i in range(1, 5):
        t, foo, new_start_tag, annotation = mk_tile(
            i+1000,
            locus,
            tile_vars[i]['lengths'][0]+locus,
            1,
            [tile_vars[i]['lengths'][0]],
            start_tag=new_start_tag,
            assembly=assembly_default,
            chrom=2
        )
        locus += tile_vars[i]['lengths'][0] - 24
#################################### TEST path_statistics_views ###################################
##class TestViewPathStatistics(TestCase):
##    fixtures = ['test_view_paths.json']
##    """
##        test_view_paths has the following structure:
##            i,  min,     avg,  max
##            0,  250,  250.67,  252 {'vars':3, 'lengths':[250,252,250]}, #1
##            1,  248,  248.00,  248 {'vars':2, 'lengths':[248,248]}, #2
##            2,  200,  250.00,  300 {'vars':3, 'lengths':[200,250,300]}, #3
##            3,  250,  250.00,  250 {'vars':1, 'lengths':[250]}, #4
##            4,  199,  199.00,  199 {'vars':1, 'lengths':[199]}, #5
##            5,  150,  205.00,  250 {'vars':4, 'lengths':[150,250,200,220]}, #6
##            6,  250,  250.25,  251 {'vars':4, 'lengths':[250,250,250,251]}, #7
##            7, 1200, 1200.00, 1200 {'vars':1, 'lengths':[1200]}, #8
##            8,  300,  300.33,  301 {'vars':3, 'lengths':[300,300,301]}, #9
##            9,  264,  264.50,  265 {'vars':2, 'lengths':[264,265]}, #10
##           10,  249,  250.50,  252 {'vars':6, 'lengths':[251,250,250,251,252,249]}, #11
##           11,  275,  275.50,  276 {'vars':2, 'lengths':[275,276]}, #12
##           12,  277,  277.00,  277 {'vars':2, 'lengths':[277,277]}, #13
##           13,  267,  267.00,  267 {'vars':1, 'lengths':[267]}, #14
##           14,  258,  258.00,  258 {'vars':1, 'lengths':[258]}, #15
##           15,  248,  248.00,  248 {'vars':3, 'lengths':[248,248,248]}, #16
##           16,  250,  250.00,  250 {'vars':1, 'lengths':[250]}, #17
##        Most view tests will be on path 0 (the first path)
##        """
##    def test_wrong_numbers_return_404(self):
##        response = self.client.get(reverse('tile_library:path_statistics', args=(0,0)))
##        self.assertEqual(response.status_code, 404)
##        response = self.client.get(reverse('tile_library:path_statistics', args=(27,0)))
##        self.assertEqual(response.status_code, 404)
##        response = self.client.get(reverse('tile_library:path_statistics', args=(2, Tile.CHR_PATH_LENGTHS[1]-1)))
##        self.assertEqual(response.status_code, 404)
##        response = self.client.get(reverse('tile_library:path_statistics', args=(2, Tile.CHR_PATH_LENGTHS[2])))
##        self.assertEqual(response.status_code, 404)
##
##    def test_path_no_statistics_view(self):
##        #highly doubt this will happen, but completeness...
##        response = self.client.get(reverse('tile_library:path_statistics', args=(1,0)))
##        self.assertEqual(response.status_code, 200)
##        self.assertFalse('path' in response.context)
##        self.assertFalse('positions' in response.context)
##        self.assertContains(response, "No statistics for this Tile Library are available.")
##
##    def test_path_empty_tiles_view(self):
##        gen_stats.initialize(silent=True)
##        response = self.client.get(reverse('tile_library:path_statistics', args=(1,1)))
##        self.assertEqual(response.status_code, 200)
##        for page in response.context['positions']:
##            self.assertEqual(page, [])
##        self.assertContains(response, "No tiles are in this path.")
##
##    def test_basic_statistics_view(self):
##        true_positions = views.get_positions(0, 17)
##        gen_stats.initialize(silent=True)
##        response = self.client.get(reverse('tile_library:path_statistics', args=(1,0)))
##        self.assertEqual(response.status_code, 200)
##        self.assertTrue('path' in response.context)
##        self.assertTrue('positions' in response.context)
##        self.assertEqual(response.context['chromosome_int'], 1)
##        self.assertEqual(response.context['chromosome'], 'chr1')
##        self.assertEqual(response.context['path_int'], 0)
##        self.assertEqual(response.context['path_hex'], '0')
##        self.assertEqual(response.context['path_cyto'], Tile.CYTOMAP[0])
##        path = response.context['path']
##        positions = response.context['positions']
##
##        self.assertEqual(len(positions), 16)
##        for i, pos in enumerate(positions):
##            self.assertEqual(pos, true_positions[i])
##        self.assertEqual(path.statistics_type, 27)
##        self.assertEqual(path.path_name, 0)
##        self.assertEqual(path.position_num, 17)
##        self.assertEqual(path.tile_num, 40)
##        self.assertEqual(path.max_variant_val, 6)
##        self.assertEqual(path.min_length, 150)
##        self.assertEqual(path.max_length, 1200)
##
##    def test_first_page_statistics_view(self):
##        """ Test asking for the first page is the same as the default page """
##        gen_stats.initialize(silent=True)
##        response_1 = self.client.get(reverse('tile_library:path_statistics', args=(1,0))+'?page=1')
##        response_2 = self.client.get(reverse('tile_library:path_statistics', args=(1,0)))
##        for item in ['chromosome_int', 'chromosome', 'path_int', 'path_hex', 'path_cyto', 'path']:
##            self.assertEqual(response_1.context[item], response_2.context[item])
##        self.assertEqual(len(response_1.context['positions']), len(response_2.context['positions']))
##        for pos1, pos2 in zip(response_1.context['positions'], response_2.context['positions']):
##            self.assertEqual(pos1, pos2)
##
##    def test_second_page_statistics_view(self):
##        """ Test asking for the first page is the same as the default page """
##        true_positions = views.get_positions(0, 17)
##        gen_stats.initialize(silent=True)
##        response_1 = self.client.get(reverse('tile_library:path_statistics', args=(1,0))+'?page=2')
##        response_2 = self.client.get(reverse('tile_library:path_statistics', args=(1,0)))
##        for item in ['chromosome_int', 'chromosome', 'path_int', 'path_hex', 'path_cyto', 'path']:
##            self.assertEqual(response_1.context[item], response_2.context[item])
##        self.assertEqual(len(response_1.context['positions']), len(true_positions[16:]))
##        for pos1, pos2 in zip(response_1.context['positions'], true_positions[16:]):
##            self.assertEqual(pos1, pos2)
##
##    def test_pagination_alteration_statistics_view(self):
##        true_positions = views.get_positions(0, 17)
##        gen_stats.initialize(silent=True)
##        response_1 = self.client.get(reverse('tile_library:path_statistics', args=(1,0))+'?num=10')
##        self.assertEqual(len(response_1.context['positions']),10)
##
##        response_2 = self.client.get(reverse('tile_library:path_statistics', args=(1,0)))
##        for item in ['chromosome_int', 'chromosome', 'path_int', 'path_hex', 'path_cyto', 'path']:
##            self.assertEqual(response_1.context[item], response_2.context[item])
##
##        self.assertNotEqual(len(response_1.context['positions']), len(response_2.context['positions']))
##        for pos1, pos2 in zip(response_1.context['positions'], response_2.context['positions']):
##            self.assertEqual(pos1, pos2)
##
##    def test_pagination_alteration_second_page_statistics_view(self):
##        true_positions = views.get_positions(0, 17)
##        gen_stats.initialize(silent=True)
##        response_1 = self.client.get(reverse('tile_library:path_statistics', args=(1,0))+'?num=10&page=2')
##        self.assertEqual(len(response_1.context['positions']),7)
##
##        response_2 = self.client.get(reverse('tile_library:path_statistics', args=(1,0)))
##        for item in ['chromosome_int', 'chromosome', 'path_int', 'path_hex', 'path_cyto', 'path']:
##            self.assertEqual(response_1.context[item], response_2.context[item])
##
##        self.assertEqual(len(response_1.context['positions']), len(true_positions[10:]))
##        for pos1, pos2 in zip(response_1.context['positions'], true_positions[10:]):
##            self.assertEqual(pos1, pos2)
##
##    def test_ordering_statistics_view(self):
##        rev_positions = list(views.get_positions(0, 17))
##        rev_positions.reverse()
##        gen_stats.initialize(silent=True)
##        response_1 = self.client.get(reverse('tile_library:path_statistics', args=(1,0))+'?ordering=desc_tile')
##        self.assertEqual(len(response_1.context['positions']),16)
##
##        response_2 = self.client.get(reverse('tile_library:path_statistics', args=(1,0)))
##        for item in ['chromosome_int', 'chromosome', 'path_int', 'path_hex', 'path_cyto', 'path']:
##            self.assertEqual(response_1.context[item], response_2.context[item])
##
##        self.assertEqual(len(response_1.context['positions']), len(rev_positions[:16]))
##        for pos1, pos2 in zip(response_1.context['positions'], rev_positions[:16]):
##            self.assertEqual(pos1, pos2)
##
##    def test_ordering_pagination_alteration_statistics_view(self):
##        rev_positions = list(views.get_positions(0, 17))
##        rev_positions.reverse()
##        gen_stats.initialize(silent=True)
##        response_1 = self.client.get(reverse('tile_library:path_statistics', args=(1,0))+'?ordering=desc_tile&num=10')
##        self.assertEqual(len(response_1.context['positions']),10)
##
##        response_2 = self.client.get(reverse('tile_library:path_statistics', args=(1,0)))
##        for item in ['chromosome_int', 'chromosome', 'path_int', 'path_hex', 'path_cyto', 'path']:
##            self.assertEqual(response_1.context[item], response_2.context[item])
##
##        self.assertEqual(len(response_1.context['positions']), len(rev_positions[:10]))
##        for pos1, pos2 in zip(response_1.context['positions'], rev_positions[:10]):
##            self.assertEqual(pos1, pos2)
##
##    def test_ordering_second_page_statistics_view(self):
##        rev_positions = list(views.get_positions(0, 17))
##        rev_positions.reverse()
##        gen_stats.initialize(silent=True)
##        response_1 = self.client.get(reverse('tile_library:path_statistics', args=(1,0))+'?ordering=desc_tile&page=2')
##        self.assertEqual(len(response_1.context['positions']),1)
##
##        response_2 = self.client.get(reverse('tile_library:path_statistics', args=(1,0)))
##        for item in ['chromosome_int', 'chromosome', 'path_int', 'path_hex', 'path_cyto', 'path']:
##            self.assertEqual(response_1.context[item], response_2.context[item])
##
##        self.assertEqual(len(response_1.context['positions']), len(rev_positions[16:]))
##        for pos1, pos2 in zip(response_1.context['positions'], rev_positions[16:]):
##            self.assertEqual(pos1, pos2)
##
##    def test_ordering_pagination_alteration_second_page_statistics_view(self):
##        rev_positions = list(views.get_positions(0, 17))
##        rev_positions.reverse()
##        gen_stats.initialize(silent=True)
##        response_1 = self.client.get(reverse('tile_library:path_statistics', args=(1,0))+'?ordering=desc_tile&num=10&page=2')
##        self.assertEqual(len(response_1.context['positions']),7)
##
##        response_2 = self.client.get(reverse('tile_library:path_statistics', args=(1,0)))
##        for item in ['chromosome_int', 'chromosome', 'path_int', 'path_hex', 'path_cyto', 'path']:
##            self.assertEqual(response_1.context[item], response_2.context[item])
##
##        self.assertEqual(len(response_1.context['positions']), len(rev_positions[10:]))
##        for pos1, pos2 in zip(response_1.context['positions'], rev_positions[10:]):
##            self.assertEqual(pos1, pos2)
##
##    def test_template_tags_reference_length(self):
##        positions = views.get_positions(0, 17)
##        lengths = [250, 248, 200, 250, 199, 150, 250, 1200, 300, 264, 251, 275, 277, 267, 258, 248, 250]
##        for i, position in enumerate(positions):
##            self.assertEqual(stat_filters.get_reference_length(position), lengths[i])
##
##    def test_template_tags_url_replace_with_view(self):
##        positions = views.get_positions(0, 17)
##        response_1 = self.client.get(reverse('tile_library:path_statistics', args=(1,0))+'?ordering=desc_tile&num=10&page=2')
##        r = response_1.context['request'].GET
##        self.assertEqual(stat_filters.url_replace(r, 'page', 1), 'ordering=desc_tile&num=10&page=1')
##        self.assertEqual(stat_filters.url_replace(r, 'ordering', 'desc_var'), 'ordering=desc_var&num=10&page=2')
##        self.assertEqual(stat_filters.url_replace(r, 'num', 15), 'ordering=desc_tile&num=15&page=2')
##
##        response_1 = self.client.get(reverse('tile_library:path_statistics', args=(1,0)))
##        r = response_1.context['request'].GET
##        self.assertEqual(stat_filters.url_replace(r, 'page', 2), 'page=2')
##        self.assertEqual(stat_filters.url_replace(r, 'ordering', 'desc_var'), 'ordering=desc_var')
##        self.assertEqual(stat_filters.url_replace(r, 'num', 15), 'num=15')
##
##        response_1 = self.client.get(reverse('tile_library:path_statistics', args=(1,0))+'?ordering=desc_tile&num=10')
##        r = response_1.context['request'].GET
##        self.assertEqual(stat_filters.url_replace(r, 'page', 2), 'ordering=desc_tile&num=10&page=2')
##        self.assertEqual(stat_filters.url_replace(r, 'ordering', 'desc_var'), 'ordering=desc_var&num=10')
##        self.assertEqual(stat_filters.url_replace(r, 'num', 15), 'ordering=desc_tile&num=15')
##
##class TestViewTileLibraryInteractive(StaticLiveServerTestCase):
##    @classmethod
##    def setUpClass(cls):
##        cls.selenium = webdriver.PhantomJS()
##        #cls.selenium = WebDriver()
##        super(TestViewTileLibraryInteractive, cls).setUpClass()
##
##    @classmethod
##    def tearDownClass(cls):
##        cls.selenium.quit()
##        super(TestViewTileLibraryInteractive, cls).tearDownClass()
##
##    def test_overall_statistics_breadcrumbs(self):
##        self.selenium.get('%s%s' % (self.live_server_url, reverse('tile_library:statistics')))
##        elements = self.selenium.find_element_by_class_name("breadcrumb").find_elements_by_tag_name('li')
##        self.assertEqual(len(elements), 2)
##        for element in elements:
##            self.assertTrue(element.is_displayed())
##            if element.text == 'Home':
##                self.assertFalse('active' in element.get_attribute('class'))
##                self.assertEqual(element.find_element_by_link_text('Home').get_attribute('href'), '%s/' % (self.live_server_url))
##
##            elif element.text == 'Library':
##                self.assertTrue('active' in element.get_attribute('class'))
##                self.assertEqual(element.find_element_by_link_text('Library').get_attribute('href'), '%s#' % (self.selenium.current_url))
##
##    def test_overall_statistics_view_hrefs(self):
##        gen_stats.initialize(silent=True)
##        self.selenium.get('%s%s' % (self.live_server_url, reverse('tile_library:statistics')))
##        elements = self.selenium.find_element_by_class_name("table-responsive").find_elements_by_tag_name('tr')
##        self.assertEqual(len(elements), 28)
##        for i, element in enumerate(elements):
##            self.assertTrue(element.is_displayed())
##            if i > 1:
##                self.assertEqual(element.find_element_by_tag_name('a').get_attribute('href'), '%s%s' % (self.live_server_url, reverse('tile_library:chr_statistics', args=(i-1,))))
##
##    def test_first_chr_statistics_breadcrumbs(self):
##        self.selenium.get('%s%s' % (self.live_server_url, reverse('tile_library:chr_statistics', args=(1,))))
##        elements = self.selenium.find_element_by_class_name("breadcrumb").find_elements_by_tag_name('li')
##        self.assertEqual(len(elements), 3)
##        for element in elements:
##            self.assertTrue(element.is_displayed())
##            if element.text == 'Home':
##                self.assertFalse('active' in element.get_attribute('class'))
##                self.assertEqual(element.find_element_by_link_text('Home').get_attribute('href'), '%s/' % (self.live_server_url))
##
##            elif element.text == 'Library':
##                self.assertFalse('active' in element.get_attribute('class'))
##                self.assertEqual(element.find_element_by_link_text('Library').get_attribute('href'), '%s%s' % (self.live_server_url, reverse('tile_library:statistics')))
##
##            else:
##                self.assertTrue('active' in element.get_attribute('class'))
##                #This will throw an error if the link does not exist
##                self.assertEqual(element.find_element_by_link_text('chr1').get_attribute('href'), '%s#' % (self.selenium.current_url))
##
##    def test_first_chr_statistics_view_hrefs(self):
##        gen_stats.initialize(silent=True)
##        self.selenium.get('%s%s' % (self.live_server_url, reverse('tile_library:chr_statistics', args=(1,))))
##        elements = self.selenium.find_element_by_class_name("table-responsive").find_elements_by_tag_name('tr')
##        self.assertEqual(len(elements), 2+Tile.CHR_PATH_LENGTHS[1])
##        for i, element in enumerate(elements):
##            self.assertTrue(element.is_displayed())
##            if i > 1:
##                self.assertEqual(element.find_element_by_tag_name('a').get_attribute('href'), '%s%s' % (self.live_server_url, reverse('tile_library:path_statistics', args=(1,i-2))))
##
##    def test_mitochondrial_chr_statistics_breadcrumbs(self):
##        self.selenium.get('%s%s' % (self.live_server_url, reverse('tile_library:chr_statistics', args=(25,))))
##        elements = self.selenium.find_element_by_class_name("breadcrumb").find_elements_by_tag_name('li')
##        self.assertEqual(len(elements), 3)
##        for element in elements:
##            self.assertEqual(element.is_displayed(), True)
##            if element.text == 'Home':
##                self.assertFalse('active' in element.get_attribute('class'))
##                self.assertEqual(element.find_element_by_link_text('Home').get_attribute('href'), '%s/' % (self.live_server_url))
##
##            elif element.text == 'Library':
##                self.assertFalse('active' in element.get_attribute('class'))
##                self.assertEqual(element.find_element_by_link_text('Library').get_attribute('href'), '%s%s' % (self.live_server_url, reverse('tile_library:statistics')))
##
##            else:
##                self.assertTrue('active' in element.get_attribute('class'))
##                #This will throw an error if the link does not exist
##                self.assertEqual(element.find_element_by_link_text('chrM').get_attribute('href'), '%s#' % (self.selenium.current_url))
##
##    def test_mitochondrial_chr_statistics_view_hrefs(self):
##        gen_stats.initialize(silent=True)
##        self.selenium.get('%s%s' % (self.live_server_url, reverse('tile_library:chr_statistics', args=(25,))))
##        elements = self.selenium.find_element_by_class_name("table-responsive").find_elements_by_tag_name('tr')
##
##        self.assertEqual(len(elements), 2+Tile.CHR_PATH_LENGTHS[25]-Tile.CHR_PATH_LENGTHS[24])
##        for i, element in enumerate(elements):
##            self.assertTrue(element.is_displayed())
##            if i > 1:
##                self.assertEqual(element.find_element_by_tag_name('a').get_attribute('href'), '%s%s' % (self.live_server_url,
##                                                                                                        reverse('tile_library:path_statistics', args=(25,i-2+Tile.CHR_PATH_LENGTHS[24]))))
##
##    def test_other_chr_statistics_breadcrumbs(self):
##        self.selenium.get('%s%s' % (self.live_server_url, reverse('tile_library:chr_statistics', args=(26,))))
##        elements = self.selenium.find_element_by_class_name("breadcrumb").find_elements_by_tag_name('li')
##        self.assertEqual(len(elements), 3)
##        for element in elements:
##            self.assertTrue(element.is_displayed())
##            if element.text == 'Home':
##                self.assertFalse('active' in element.get_attribute('class'))
##                self.assertEqual(element.find_element_by_link_text('Home').get_attribute('href'), '%s/' % (self.live_server_url))
##
##            elif element.text == 'Library':
##                self.assertFalse('active' in element.get_attribute('class'))
##                self.assertEqual(element.find_element_by_link_text('Library').get_attribute('href'), '%s%s' % (self.live_server_url, reverse('tile_library:statistics')))
##
##            else:
##                self.assertTrue('active' in element.get_attribute('class'))
##                #This will throw an error if the link does not exist
##                self.assertEqual(element.find_element_by_link_text('Other').get_attribute('href'), '%s#' % (self.selenium.current_url))
##
##    def test_other_chr_statistics_view_hrefs(self):
##        gen_stats.initialize(silent=True)
##        self.selenium.get('%s%s' % (self.live_server_url, reverse('tile_library:chr_statistics', args=(26,))))
##        elements = self.selenium.find_element_by_class_name("table-responsive").find_elements_by_tag_name('tr')
##
##        self.assertEqual(len(elements), 2+Tile.CHR_PATH_LENGTHS[26]-Tile.CHR_PATH_LENGTHS[25])
##        for i, element in enumerate(elements):
##            self.assertTrue(element.is_displayed())
##            if i > 1:
##                self.assertEqual(element.find_element_by_tag_name('a').get_attribute('href'), '%s%s' % (self.live_server_url,
##                                                                                                        reverse('tile_library:path_statistics', args=(26,i-2+Tile.CHR_PATH_LENGTHS[25]))))
##
##    def test_path_statistics_breadcrumbs(self):
##        self.selenium.get('%s%s' % (self.live_server_url, reverse('tile_library:path_statistics', args=(1,0))))
##        elements = self.selenium.find_element_by_class_name("breadcrumb").find_elements_by_tag_name('li')
##        self.assertEqual(len(elements), 4)
##        for element in elements:
##            self.assertTrue(element.is_displayed())
##            if element.text == 'Home':
##                self.assertFalse('active' in element.get_attribute('class'))
##                self.assertEqual(element.find_element_by_link_text('Home').get_attribute('href'), '%s/' % (self.live_server_url))
##
##            elif element.text == 'Library':
##                self.assertFalse('active' in element.get_attribute('class'))
##                self.assertEqual(element.find_element_by_link_text('Library').get_attribute('href'), '%s%s' % (self.live_server_url, reverse('tile_library:statistics')))
##
##            elif element.text == 'chr1':
##                self.assertFalse('active' in element.get_attribute('class'))
##                self.assertEqual(element.find_element_by_link_text('chr1').get_attribute('href'), '%s%s' % (self.live_server_url, reverse('tile_library:chr_statistics', args=(1,))))
##            else:
##                self.assertTrue('active' in element.get_attribute('class'))
##                #This will throw an error if the link does not exist
##                self.assertEqual(element.find_element_by_link_text('Path 0').get_attribute('href'), '%s#' % (self.selenium.current_url))
##
##    def test_path_statistics_view_no_statistics(self):
##        self.selenium.get('%s%s' % (self.live_server_url, reverse('tile_library:path_statistics', args=(1,0))))
##        #check that path 0 title shows the 0
##
##        title_element = self.selenium.find_element_by_class_name("page-header").find_element_by_tag_name('h1')
##        self.assertTrue('Path 0' in title_element.text)
##
##        #check that pagination and all tables are hidden if no statistics available
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        for element in elements:
##            self.assertFalse(element.is_displayed())
##
##        elements = self.selenium.find_elements_by_class_name("pagination")
##        for element in elements:
##            self.assertFalse(element.is_displayed())
##
##    def test_path_statistics_view_no_positions(self):
##        gen_stats.initialize(silent=True)
##        self.selenium.get('%s%s' % (self.live_server_url, reverse('tile_library:path_statistics', args=(1,1))))
##
##        #check that pagination and second table is hidden if no positions available
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 2)
##        for i, element in enumerate(elements):
##            if i == 0:
##                self.assertTrue(element.is_displayed())
##            else:
##                self.assertFalse(element.is_displayed())
##
##        elements = self.selenium.find_elements_by_class_name("pagination")
##        for element in elements:
##            self.assertFalse(element.is_displayed())
##
##    #For tile_view, no hrefs (other than snps, which don't have clear testing) are checkable outside the breadcrumbs
##    def test_tile_view_breadcrumbs(self):
##        self.selenium.get('%s%s' % (self.live_server_url, reverse('tile_library:tile_view', args=(1,0,0))))
##        elements = self.selenium.find_element_by_class_name("breadcrumb").find_elements_by_tag_name('li')
##        self.assertEqual(len(elements), 5)
##        for element in elements:
##            self.assertTrue(element.is_displayed())
##            if element.text == 'Home':
##                self.assertFalse('active' in element.get_attribute('class'))
##                self.assertEqual(element.find_element_by_link_text('Home').get_attribute('href'), '%s/' % (self.live_server_url))
##
##            elif element.text == 'Library':
##                self.assertFalse('active' in element.get_attribute('class'))
##                self.assertEqual(element.find_element_by_link_text('Library').get_attribute('href'), '%s%s' % (self.live_server_url, reverse('tile_library:statistics')))
##
##            elif element.text == 'chr1':
##                self.assertFalse('active' in element.get_attribute('class'))
##                self.assertEqual(element.find_element_by_link_text('chr1').get_attribute('href'), '%s%s' % (self.live_server_url, reverse('tile_library:chr_statistics', args=(1,))))
##
##            elif element.text == 'Path 0':
##                self.assertFalse('active' in element.get_attribute('class'))
##                self.assertEqual(element.find_element_by_link_text('Path 0').get_attribute('href'), '%s%s' % (self.live_server_url, reverse('tile_library:path_statistics', args=(1,0))))
##
##            else:
##                self.assertTrue('active' in element.get_attribute('class'))
##                #This will throw an error if the link does not exist
##                self.assertEqual(element.find_element_by_link_text('Tile 000.00.0000').get_attribute('href'), '%s#' % (self.selenium.current_url))
##
##    def test_gene_path_view_breadcrumbs(self):
##        make_long_gene1()
##        gene_id = GeneXRef.objects.all().first().id
##        self.selenium.get('%s%s' % (self.live_server_url, reverse('tile_library:gene_view', args=(gene_id,))))
##        elements = self.selenium.find_element_by_class_name("breadcrumb").find_elements_by_tag_name('li')
##        self.assertEqual(len(elements), 4)
##        for element in elements:
##            self.assertTrue(element.is_displayed())
##            if element.text == 'Home':
##                self.assertFalse('active' in element.get_attribute('class'))
##                self.assertEqual(element.find_element_by_link_text('Home').get_attribute('href'), '%s/' % (self.live_server_url))
##
##            elif element.text == 'Library':
##                self.assertFalse('active' in element.get_attribute('class'))
##                self.assertEqual(element.find_element_by_link_text('Library').get_attribute('href'), '%s%s' % (self.live_server_url, reverse('tile_library:statistics')))
##
##            elif element.text == 'chr1':
##                self.assertFalse('active' in element.get_attribute('class'))
##                self.assertEqual(element.find_element_by_link_text('chr1').get_attribute('href'), '%s%s' % (self.live_server_url, reverse('tile_library:chr_statistics', args=(1,))))
##
##            else:
##                self.assertTrue('active' in element.get_attribute('class'))
##                #This will throw an error if the link does not exist
##                self.assertEqual(element.find_element_by_link_text('Gene gene1').get_attribute('href'), '%s#' % (self.selenium.current_url))
##
##    #Gene view does not require statistics to be run, so don't need to test for that behavior
##    def test_gene_path_view_change_view_buttons(self):
##        make_long_gene1()
##        gene_id = GeneXRef.objects.all().first().id
##        gene_name = GeneXRef.objects.all().first().gene_aliases
##        self.selenium.get('%s%s' % (self.live_server_url, reverse('tile_library:gene_view', args=(gene_id,))))
##        elements = self.selenium.find_element_by_class_name("page-header").find_elements_by_class_name('btn-default')
##        self.assertEqual(len(elements), 3)
##        for element in elements:
##            self.assertTrue(element.is_displayed())
##            if element.text == 'Generic View':
##                self.assertFalse('active' in element.get_attribute('class'))
##                self.assertEqual(element.get_attribute('href'), '%s%s' % (self.live_server_url, reverse('genes:specific', args=(gene_id,))))
##
##            elif element.text == 'Map View':
##                self.assertFalse('active' in element.get_attribute('class'))
##                self.assertEqual(element.get_attribute('href'), '%s%s?exact=%s' % (self.live_server_url, reverse('slippy:slippymap'), gene_name))
##
##            else:
##                self.assertTrue('active' in element.get_attribute('class'))
##                self.assertTrue('disabled' in element.get_attribute('class'))
##                #This will throw an error if the link does not exist
##                self.assertEqual(element.get_attribute('href'), '%s' % (self.selenium.current_url))
##
##    def test_gene_path_view_no_positions(self):
##        make_long_gene1()
##        gene_id = GeneXRef.objects.all().first().id
##        self.selenium.get('%s%s' % (self.live_server_url, reverse('tile_library:gene_view', args=(gene_id,))))
##
##        #check that pagination and table is hidden if no positions available
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 1)
##        for element in elements:
##            self.assertFalse(element.is_displayed())
##
##        elements = self.selenium.find_elements_by_class_name("pagination")
##        for element in elements:
##            self.assertFalse(element.is_displayed())
##
##    def test_gene_path_view_exons_colored_positions(self):
##        make_tiles()
##        make_long_gene1()
##        gene_id = GeneXRef.objects.all().first().id
##        self.selenium.get('%s%s' % (self.live_server_url, reverse('tile_library:gene_view', args=(gene_id,))))
##        gene_id = GeneXRef.objects.all().first().id
##
##        #Check that 1 table exists and is visible. Check new rows for exon
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 1)
##        for element in elements:
##            self.assertTrue(element.is_displayed())
##            table_rows = element.find_elements_by_tag_name('tr')
##            self.assertEqual(len(table_rows[1:]), 16)
##            for j, row in enumerate(table_rows[1:]):
##                self.assertEqual('success' in row.get_attribute('class'), LONG_GENE1_CHECK_DICT[j])
##        #Switch pages to check the other 2
##        pagination_element = self.selenium.find_element_by_class_name("pagination")
##        pagination_element.find_elements_by_tag_name('li')[1].find_element_by_tag_name('a').click()
##
##        #Check that 1 table exist and is visible. Check new rows for exon
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 1)
##        for i, element in enumerate(elements):
##            self.assertTrue(element.is_displayed())
##            table_rows = element.find_elements_by_tag_name('tr')
##            self.assertEqual(len(table_rows[1:]), 2)
##            for j, row in enumerate(table_rows[1:]):
##                self.assertEqual('success' in row.get_attribute('class'), LONG_GENE1_CHECK_DICT[j+16])
##
##    def test_gene_path_view_smaller_exons_colored_positions(self):
##        make_tiles()
##        make_gene1()
##        gene_id = GeneXRef.objects.all().first().id
##        self.selenium.get('%s%s' % (self.live_server_url, reverse('tile_library:gene_view', args=(gene_id,))))
##
##        #Check that 1 table exists and is visible. Check new rows for exon
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 1)
##        check_dict = {1:True, 2:False, 3:False, 4:True, 5:True}
##        for element in elements:
##            self.assertTrue(element.is_displayed())
##            table_rows = element.find_elements_by_tag_name('tr')
##            self.assertEqual(len(table_rows[1:]), 5)
##            for j, row in enumerate(table_rows[1:]):
##                self.assertEqual('success' in row.get_attribute('class'), check_dict[j+1])
##        #Check pagination elements exist, are visible, and link correctly
##        elements = self.selenium.find_elements_by_class_name("pagination")
##        self.assertEqual(len(elements),2)
##        for element in elements:
##            self.assertTrue(element.is_displayed())
##            pages = element.find_elements_by_tag_name('li')
##            self.assertEqual(len(pages), 1)
##            for i, page in enumerate(pages):
##                self.assertTrue(page.is_displayed())
##                self.assertEqual(page.find_element_by_tag_name('a').get_attribute('href'), '%s#' % (self.selenium.current_url))
##
##    def test_gene_path_view_multiple_exons_colored_positions(self):
##        make_tiles()
##        make_long_gene1()
##        make_gene1pt5()
##        gene_id = GeneXRef.objects.all().first().id
##        self.selenium.get('%s%s' % (self.live_server_url, reverse('tile_library:gene_view', args=(gene_id,))))
##        gene_id = GeneXRef.objects.all().first().id
##
##        #Check that 1 table exists and is visible. Check new rows for exon
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 1)
##        check_dict = LONG_GENE1_CHECK_DICT
##        check_dict[2] = True
##        for element in elements:
##            self.assertTrue(element.is_displayed())
##            table_rows = element.find_elements_by_tag_name('tr')
##            self.assertEqual(len(table_rows[1:]), 16)
##            for j, row in enumerate(table_rows[1:]):
##                self.assertEqual('success' in row.get_attribute('class'), check_dict[j])
##
##        pagination_element = self.selenium.find_element_by_class_name("pagination")
##        pagination_element.find_elements_by_tag_name('li')[1].find_element_by_tag_name('a').click()
##
##        #Check that 1 table exists and is visible. Check new rows for exon
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 1)
##        for i, element in enumerate(elements):
##            self.assertTrue(element.is_displayed())
##            table_rows = element.find_elements_by_tag_name('tr')
##            self.assertEqual(len(table_rows[1:]), 2)
##            for j, row in enumerate(table_rows[1:]):
##                self.assertEqual('success' in row.get_attribute('class'), check_dict[j+16])
##
##    def test_gene_path_view_multiple_short_exons_colored_positions(self):
##        make_tiles()
##        make_gene1()
##        make_gene1pt5()
##        gene_id = GeneXRef.objects.all().first().id
##        self.selenium.get('%s%s' % (self.live_server_url, reverse('tile_library:gene_view', args=(gene_id,))))
##
##        #Check that 1 table exists and is visible. Check new rows for exon
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 1)
##        check_dict = {1:True, 2:True, 3:False, 4:True, 5:True}
##        for element in elements:
##            self.assertTrue(element.is_displayed())
##            table_rows = element.find_elements_by_tag_name('tr')
##            self.assertEqual(len(table_rows[1:]), 5)
##            for j, row in enumerate(table_rows[1:]):
##                self.assertEqual('success' in row.get_attribute('class'), check_dict[j+1])
##
##
##    def test_gene_tile_statistics_in_gene_breadcrumbs(self):
##        make_tiles()
##        make_gene1()
##        gene_id = GeneXRef.objects.all().first().id
##        self.selenium.get('%s%s' % (self.live_server_url, reverse('tile_library:tile_in_gene_view', args=(gene_id,1))))
##        elements = self.selenium.find_element_by_class_name("breadcrumb").find_elements_by_tag_name('li')
##        self.assertEqual(len(elements), 5)
##        for element in elements:
##            self.assertTrue(element.is_displayed())
##            if element.text == 'Home':
##                self.assertFalse('active' in element.get_attribute('class'))
##                self.assertEqual(element.find_element_by_link_text('Home').get_attribute('href'), '%s/' % (self.live_server_url))
##
##            elif element.text == 'Library':
##                self.assertFalse('active' in element.get_attribute('class'))
##                self.assertEqual(element.find_element_by_link_text('Library').get_attribute('href'), '%s%s' % (self.live_server_url, reverse('tile_library:statistics')))
##
##            elif element.text == 'chr1':
##                self.assertFalse('active' in element.get_attribute('class'))
##                self.assertEqual(element.find_element_by_link_text('chr1').get_attribute('href'), '%s%s' % (self.live_server_url, reverse('tile_library:chr_statistics', args=(1,))))
##
##            elif element.text == 'Gene gene1':
##                self.assertFalse('active' in element.get_attribute('class'))
##                self.assertEqual(element.find_element_by_link_text('Gene gene1').get_attribute('href'), '%s%s' % (self.live_server_url, reverse('tile_library:gene_view', args=(gene_id,))))
##
##            else:
##                self.assertTrue('active' in element.get_attribute('class'))
##                #This will throw an error if the link does not exist
##                self.assertEqual(element.find_element_by_link_text('Tile 000.00.0001').get_attribute('href'), '%s#' % (self.selenium.current_url))
##
##    def test_gene_tile_statistics_not_in_gene_breadcrumbs(self):
##        make_tiles()
##        make_gene1()
##        gene_id = GeneXRef.objects.all().first().id
##        self.selenium.get('%s%s' % (self.live_server_url, reverse('tile_library:tile_in_gene_view', args=(gene_id,2))))
##        elements = self.selenium.find_element_by_class_name("breadcrumb").find_elements_by_tag_name('li')
##        self.assertEqual(len(elements), 5)
##        for element in elements:
##            self.assertTrue(element.is_displayed())
##            if element.text == 'Home':
##                self.assertFalse('active' in element.get_attribute('class'))
##                self.assertEqual(element.find_element_by_link_text('Home').get_attribute('href'), '%s/' % (self.live_server_url))
##
##            elif element.text == 'Library':
##                self.assertFalse('active' in element.get_attribute('class'))
##                self.assertEqual(element.find_element_by_link_text('Library').get_attribute('href'), '%s%s' % (self.live_server_url, reverse('tile_library:statistics')))
##
##            elif element.text == 'chr1':
##                self.assertFalse('active' in element.get_attribute('class'))
##                self.assertEqual(element.find_element_by_link_text('chr1').get_attribute('href'), '%s%s' % (self.live_server_url, reverse('tile_library:chr_statistics', args=(1,))))
##
##            elif element.text == 'Gene gene1':
##                self.assertFalse('active' in element.get_attribute('class'))
##                self.assertEqual(element.find_element_by_link_text('Gene gene1').get_attribute('href'), '%s%s' % (self.live_server_url, reverse('tile_library:gene_view', args=(gene_id,))))
##
##            else:
##                self.assertTrue('active' in element.get_attribute('class'))
##                #This will throw an error if the link does not exist
##                self.assertEqual(element.find_element_by_link_text('Tile 000.00.0002').get_attribute('href'), '%s#' % (self.selenium.current_url))
##
##    def test_gene_tile_view_fast_nav(self):
##        #check buttons for swapping
##        make_tiles()
##        make_gene1()
##        gene_id = GeneXRef.objects.all().first().id
##        self.selenium.get('%s%s' % (self.live_server_url, reverse('tile_library:tile_in_gene_view', args=(gene_id,1))))
##        title = self.selenium.find_element_by_class_name("page-header").find_element_by_tag_name('h1').text
##        self.assertEqual(title, 'Tile Position 000.00.0001 (Path 0, chr1p36.33, Gene gene1)')
##        elements = self.selenium.find_element_by_class_name("page-header").find_elements_by_tag_name('a')
##        self.assertEqual(len(elements), 2)
##        self.assertTrue('disabled' in elements[0].get_attribute('class'))
##        self.assertFalse('disabled' in elements[1].get_attribute('class'))
##        elements[1].click()
##        for i in range(3):
##            title = self.selenium.find_element_by_class_name("page-header").find_element_by_tag_name('h1').text
##            self.assertEqual(title, 'Tile Position 000.00.000%i (Path 0, chr1p36.33, Gene gene1)' % (i+2))
##            elements = self.selenium.find_element_by_class_name("page-header").find_elements_by_tag_name('a')
##            self.assertEqual(len(elements), 2)
##            self.assertFalse('disabled' in elements[0].get_attribute('class'))
##            self.assertFalse('disabled' in elements[1].get_attribute('class'))
##            elements[1].click()
##        title = self.selenium.find_element_by_class_name("page-header").find_element_by_tag_name('h1').text
##        self.assertEqual(title, 'Tile Position 000.00.0005 (Path 0, chr1p36.33, Gene gene1)')
##        elements = self.selenium.find_element_by_class_name("page-header").find_elements_by_tag_name('a')
##        self.assertEqual(len(elements), 2)
##        self.assertFalse('disabled' in elements[0].get_attribute('class'))
##        self.assertTrue('disabled' in elements[1].get_attribute('class'))
##        elements[0].click()
##        title = self.selenium.find_element_by_class_name("page-header").find_element_by_tag_name('h1').text
##        self.assertEqual(title, 'Tile Position 000.00.0004 (Path 0, chr1p36.33, Gene gene1)')
##
##
##    def test_gene_tile_in_gene_view_exon_splicing_table(self):
##        #check Exon Splicing table exist
##        make_tiles()
##        make_gene1pt5()
##        gene_id = GeneXRef.objects.all().first().id
##        self.selenium.get('%s%s' % (self.live_server_url, reverse('tile_library:tile_in_gene_view', args=(gene_id,2))))
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 2)
##        for i, element in enumerate(elements):
##            self.assertTrue(element.is_displayed())
##            table_rows = element.find_elements_by_tag_name('tr')
##            if i == 0:
##                self.assertEqual(len(table_rows[1:]), 2)
##            else:
##                self.assertEqual(len(table_rows[1:]), 3)
##
##    def test_gene_tile_in_gene_view_exon_splicing_table_multiple_genes(self):
##        #check Exon Splicing table exist
##        make_tiles()
##        make_gene1()
##        make_gene1pt5()
##        gene_id = GeneXRef.objects.all().first().id
##        self.selenium.get('%s%s' % (self.live_server_url, reverse('tile_library:tile_in_gene_view', args=(gene_id,1))))
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 2)
##        for i, element in enumerate(elements):
##            self.assertTrue(element.is_displayed())
##            table_rows = element.find_elements_by_tag_name('tr')
##            if i == 0:
##                self.assertEqual(len(table_rows[1:]), 3)
##            else:
##                self.assertEqual(len(table_rows[1:]), 2)
##
##    def test_gene_tile_not_in_gene_view_splicing_table_nonexistant(self):
##        #check Exon Splicing table does not exist
##        make_tiles()
##        make_gene1()
##        gene_id = GeneXRef.objects.all().first().id
##        self.selenium.get('%s%s' % (self.live_server_url, reverse('tile_library:tile_in_gene_view', args=(gene_id,2))))
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 1)
##        for i, element in enumerate(elements):
##            table_rows = element.find_elements_by_tag_name('tr')
##            self.assertTrue(element.is_displayed())
##            self.assertEqual(len(table_rows[1:]), 3)
##
##class TestViewPopulatedPathInteractive(StaticLiveServerTestCase):
##    fixtures = ['test_view_paths.json']
##
##    @classmethod
##    def setUpClass(cls):
##        cls.selenium = webdriver.PhantomJS()
##        super(TestViewPopulatedPathInteractive, cls).setUpClass()
##
##    @classmethod
##    def tearDownClass(cls):
##        cls.selenium.quit()
##        super(TestViewPopulatedPathInteractive, cls).tearDownClass()
##
##    def setUp(self):
##        gen_stats.initialize(silent=True)
##        self.selenium.get('%s%s' % (self.live_server_url, reverse('tile_library:path_statistics', args=(1,0))))
##        super(TestViewPopulatedPathInteractive, self).setUp()
##
##    def test_view_native_full_page(self):
##        #Check that 2 tables exist and are visible. Check that hrefs in second table link correctly
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 2)
##        for i, element in enumerate(elements):
##            self.assertTrue(element.is_displayed())
##            if i > 0:
##                table_rows = element.find_elements_by_tag_name('tr')
##                self.assertEqual(len(table_rows[1:]), 16)
##                for j, row in enumerate(table_rows[1:]):
##                    self.assertEqual(row.find_element_by_tag_name('a').get_attribute('href'), '%s%s' % (self.live_server_url,
##                                                                                                        reverse('tile_library:tile_view', args=(1,0,j))))
##
##        #Check pagination elements exist, are visible, and link correctly
##        elements = self.selenium.find_elements_by_class_name("pagination")
##        self.assertEqual(len(elements),2)
##        for element in elements:
##            self.assertTrue(element.is_displayed())
##            pages = element.find_elements_by_tag_name('li')
##            self.assertEqual(len(pages), 2)
##            for i, page in enumerate(pages):
##                self.assertTrue(page.is_displayed())
##                if i == 0:
##                    self.assertEqual(page.find_element_by_tag_name('a').get_attribute('href'), '%s#' % (self.selenium.current_url))
##                else:
##                    self.assertEqual(page.find_element_by_tag_name('a').get_attribute('href'), '%s%s?page=2' % (self.live_server_url, reverse('tile_library:path_statistics', args=(1,0))))
##
##    def test_go_to_page_native_view(self):
##        #Go to next page (using top pagination)
##        pagination_element = self.selenium.find_element_by_class_name("pagination")
##        pagination_element.find_elements_by_tag_name('li')[1].find_element_by_tag_name('a').click()
##
##        #Check that 2 tables exist and are visible. Check new hrefs for correctness
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 2)
##        for i, element in enumerate(elements):
##            self.assertTrue(element.is_displayed())
##            if i > 0:
##                table_rows = element.find_elements_by_tag_name('tr')
##                self.assertEqual(len(table_rows[1:]), 1)
##                for j, row in enumerate(table_rows[1:]):
##                    self.assertEqual(row.find_element_by_tag_name('a').get_attribute('href'), '%s%s' % (self.live_server_url,
##                                                                                                        reverse('tile_library:tile_view', args=(1,0,j+16))))
##
##        #Check pagination elements exist, are visible, and link correctly
##        elements = self.selenium.find_elements_by_class_name("pagination")
##        self.assertEqual(len(elements),2)
##        for element in elements:
##            self.assertTrue(element.is_displayed())
##            pages = element.find_elements_by_tag_name('li')
##            self.assertEqual(len(pages), 2)
##            for i, page in enumerate(pages):
##                self.assertTrue(page.is_displayed())
##                if i == 0:
##                    self.assertEqual(page.find_element_by_tag_name('a').get_attribute('href'), '%s%s?page=1' % (self.live_server_url, reverse('tile_library:path_statistics', args=(1,0))))
##                else:
##                    self.assertEqual(page.find_element_by_tag_name('a').get_attribute('href'), '%s#' % (self.selenium.current_url))
##        #Go to prev page (using lower pagination)
##        pagination_element = elements[1]
##        pagination_element.find_elements_by_tag_name('li')[0].find_element_by_tag_name('a').click()
##
##        #Check this page has first tables
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 2)
##        for i, element in enumerate(elements):
##            self.assertTrue(element.is_displayed())
##            if i > 0:
##                table_rows = element.find_elements_by_tag_name('tr')
##                self.assertEqual(len(table_rows[1:]), 16)
##                for j, row in enumerate(table_rows[1:]):
##                    self.assertEqual(row.find_element_by_tag_name('a').get_attribute('href'), '%s%s' % (self.live_server_url,
##                                                                                                        reverse('tile_library:tile_view', args=(1,0,j))))
##    def test_sort_by_desc_position(self):
##        #Click button to sort the table contents by ascending position
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        table_buttons = elements[1].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('button')
##        table_buttons[0].click()
##        elements[1].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('a')[1].click()
##
##        #Check the table has the requested order (descending position)
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 2)
##        for i, element in enumerate(elements):
##            self.assertTrue(element.is_displayed())
##            if i > 0:
##                table_rows = element.find_elements_by_tag_name('tr')
##                self.assertEqual(len(table_rows[1:]), 16)
##                for j, row in enumerate(table_rows[1:]):
##                    self.assertEqual(row.find_element_by_tag_name('a').get_attribute('href'), '%s%s' % (self.live_server_url,
##                                                                                                        reverse('tile_library:tile_view', args=(1,0,j))))
##
##    def test_sort_by_ascending_position(self):
##        #Click button to sort the table contents by ascending position
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        table_buttons = elements[1].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('button')
##        table_buttons[0].click()
##        elements[1].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('a')[0].click()
##
##        #Check the table has the requested order (ascending position)
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 2)
##        for i, element in enumerate(elements):
##            self.assertTrue(element.is_displayed())
##            if i > 0:
##                table_rows = element.find_elements_by_tag_name('tr')
##                self.assertEqual(len(table_rows[1:]), 16)
##                for j, row in enumerate(table_rows[1:]):
##                    self.assertEqual(row.find_element_by_tag_name('a').get_attribute('href'), '%s%s' % (self.live_server_url,
##                                                                                                        reverse('tile_library:tile_view', args=(1,0,16-j))))
##
##    def test_sort_by_desc_min_len(self):
##        #Click button to sort the table contents by descending minimum length
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        table_buttons = elements[1].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('button')
##        table_buttons[2].click()
##        elements[1].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('a')[4].click()
##
##        #Check the table has the requested order (descending minimum length)
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 2)
##        for i, element in enumerate(elements):
##            self.assertTrue(element.is_displayed())
##            if i > 0:
##                table_rows = element.find_elements_by_tag_name('tr')
##                self.assertEqual(len(table_rows[1:]), 16)
##                prev = 1300
##                for j, row in enumerate(table_rows[1:]):
##                    curr = row.find_elements_by_tag_name('td')[3].text.strip()
##                    if curr == '-':
##                        #Make sure variant number is 1 if the length is displayed as '-'
##                        self.assertEqual(int(row.find_elements_by_tag_name('td')[1].text.strip()), 1)
##                        curr = int(row.find_elements_by_tag_name('td')[2].text.strip())
##                    else:
##                        curr = int(curr)
##                    self.assertGreaterEqual(prev, curr)
##                    prev = curr
##
##
##    def test_sort_by_ascending_min_len(self):
##        #Click button to sort the table contents by ascending minimum length
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        table_buttons = elements[1].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('button')
##        table_buttons[2].click()
##        elements[1].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('a')[5].click()
##
##        #Check the table has the requested order (ascending minimum length)
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 2)
##        for i, element in enumerate(elements):
##            self.assertTrue(element.is_displayed())
##            if i > 0:
##                table_rows = element.find_elements_by_tag_name('tr')
##                self.assertEqual(len(table_rows[1:]), 16)
##                prev = 0
##                for j, row in enumerate(table_rows[1:]):
##                    curr = row.find_elements_by_tag_name('td')[3].text.strip()
##                    if curr == '-':
##                        #Make sure variant number is 1 if the length is displayed as '-'
##                        self.assertEqual(int(row.find_elements_by_tag_name('td')[1].text.strip()), 1)
##                        curr = int(row.find_elements_by_tag_name('td')[2].text.strip())
##                    else:
##                        curr = int(curr)
##                    self.assertLessEqual(prev, curr)
##                    prev = curr
##
##    def test_sort_by_desc_avg_len(self):
##        #Click button to sort the table contents by descending minimum length
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        table_buttons = elements[1].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('button')
##        table_buttons[3].click()
##        elements[1].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('a')[6].click()
##
##        #Check the table has the requested order (descending minimum length)
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 2)
##        for i, element in enumerate(elements):
##            self.assertTrue(element.is_displayed())
##            if i > 0:
##                table_rows = element.find_elements_by_tag_name('tr')
##                self.assertEqual(len(table_rows[1:]), 16)
##                prev = 1300
##                for j, row in enumerate(table_rows[1:]):
##                    curr = row.find_elements_by_tag_name('td')[4].text.strip()
##                    if curr == '-':
##                        #Make sure variant number is 1 if the length is displayed as '-'
##                        self.assertEqual(int(row.find_elements_by_tag_name('td')[1].text.strip()), 1)
##                        curr = float(row.find_elements_by_tag_name('td')[2].text.strip())
##                    else:
##                        curr = float(curr)
##                    self.assertGreaterEqual(prev, curr)
##                    prev = curr
##
##
##    def test_sort_by_ascending_avg_len(self):
##        #Click button to sort the table contents by ascending minimum length
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        table_buttons = elements[1].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('button')
##        table_buttons[3].click()
##        elements[1].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('a')[7].click()
##
##        #Check the table has the requested order (ascending minimum length)
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 2)
##        for i, element in enumerate(elements):
##            self.assertTrue(element.is_displayed())
##            if i > 0:
##                table_rows = element.find_elements_by_tag_name('tr')
##                self.assertEqual(len(table_rows[1:]), 16)
##                prev = 0
##                for j, row in enumerate(table_rows[1:]):
##                    curr = row.find_elements_by_tag_name('td')[4].text.strip()
##                    if curr == '-':
##                        #Make sure variant number is 1 if the length is displayed as '-'
##                        self.assertEqual(int(row.find_elements_by_tag_name('td')[1].text.strip()), 1)
##                        curr = float(row.find_elements_by_tag_name('td')[2].text.strip())
##                    else:
##                        curr = float(curr)
##                    self.assertLessEqual(prev, curr)
##                    prev = curr
##
##    def test_sort_by_desc_max_len(self):
##        #Click button to sort the table contents by descending minimum length
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        table_buttons = elements[1].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('button')
##        table_buttons[4].click()
##        elements[1].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('a')[8].click()
##
##        #Check the table has the requested order (descending minimum length)
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 2)
##        for i, element in enumerate(elements):
##            self.assertTrue(element.is_displayed())
##            if i > 0:
##                table_rows = element.find_elements_by_tag_name('tr')
##                self.assertEqual(len(table_rows[1:]), 16)
##                prev = 1300
##                for j, row in enumerate(table_rows[1:]):
##                    curr = row.find_elements_by_tag_name('td')[5].text.strip()
##                    if curr == '-':
##                        #Make sure variant number is 1 if the length is displayed as '-'
##                        self.assertEqual(int(row.find_elements_by_tag_name('td')[1].text.strip()), 1)
##                        curr = int(row.find_elements_by_tag_name('td')[2].text.strip())
##                    else:
##                        curr = int(curr)
##                    self.assertGreaterEqual(prev, curr)
##                    prev = curr
##
##
##    def test_sort_by_ascending_max_len(self):
##        #Click button to sort the table contents by ascending minimum length
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        table_buttons = elements[1].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('button')
##        table_buttons[4].click()
##        elements[1].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('a')[9].click()
##
##        #Check the table has the requested order (ascending minimum length)
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 2)
##        for i, element in enumerate(elements):
##            self.assertTrue(element.is_displayed())
##            if i > 0:
##                table_rows = element.find_elements_by_tag_name('tr')
##                self.assertEqual(len(table_rows[1:]), 16)
##                prev = 0
##                for j, row in enumerate(table_rows[1:]):
##                    curr = row.find_elements_by_tag_name('td')[5].text.strip()
##                    if curr == '-':
##                        #Make sure variant number is 1 if the length is displayed as '-'
##                        self.assertEqual(int(row.find_elements_by_tag_name('td')[1].text.strip()), 1)
##                        curr = int(row.find_elements_by_tag_name('td')[2].text.strip())
##                    else:
##                        curr = int(curr)
##                    self.assertLessEqual(prev, curr)
##                    prev = curr
##
##    def test_sort_by_desc_var(self):
##        #Click button to sort the table contents by descending number of variants
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        table_buttons = elements[1].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('button')
##        table_buttons[1].click()
##        elements[1].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('a')[2].click()
##
##        #Check the table has the requested order (descending number of variants)!
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 2)
##        for i, element in enumerate(elements):
##            self.assertTrue(element.is_displayed())
##            if i > 0:
##                table_rows = element.find_elements_by_tag_name('tr')
##                self.assertEqual(len(table_rows[1:]), 16)
##                prev = 10
##                for row in table_rows[1:]:
##                    curr = int(row.find_elements_by_tag_name('td')[1].text.strip())
##                    self.assertGreaterEqual(prev, curr)
##                    prev = curr
##
##    def test_sort_by_asc_var_and_change_page(self):
##        #Click button to sort the table contents by ascending number of variants
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        table_buttons = elements[1].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('button')
##        table_buttons[1].click()
##        elements[1].find_elements_by_tag_name('tr')[0].find_elements_by_tag_name('a')[3].click()
##
##        #Check the table has the requested order(ascending number of variants)!
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 2)
##        for i, element in enumerate(elements):
##            self.assertTrue(element.is_displayed())
##            if i > 0:
##                table_rows = element.find_elements_by_tag_name('tr')
##                self.assertEqual(len(table_rows[1:]), 16)
##                prev = 0
##                for row in table_rows[1:]:
##                    curr = int(row.find_elements_by_tag_name('td')[1].text.strip())
##                    self.assertLessEqual(prev, curr)
##                    prev = curr
##
##        #Go to next page (using lower pagination)
##        pagination_element = self.selenium.find_elements_by_class_name("pagination")[1]
##        pagination_element.find_elements_by_tag_name('li')[1].find_element_by_tag_name('a').click()
##
##        #Check the table has the requested order (still ascending number of variants)!
##        elements = self.selenium.find_elements_by_class_name("table-responsive")
##        self.assertEqual(len(elements), 2)
##        for i, element in enumerate(elements):
##            self.assertTrue(element.is_displayed())
##            if i > 0:
##                table_rows = element.find_elements_by_tag_name('tr')
##                self.assertEqual(len(table_rows[1:]), 1)
##                for row in table_rows[1:]:
##                    curr = int(row.find_elements_by_tag_name('td')[1].text.strip())
##                    self.assertLessEqual(prev, curr)
##                    prev = curr
