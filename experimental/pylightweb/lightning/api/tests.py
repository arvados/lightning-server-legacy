import json
import pprint

from django.test import TestCase

from unittest import skipIf, skip

from wsgiref.simple_server import make_server, WSGIRequestHandler
import multiprocessing

from django.core.urlresolvers import reverse

from errors import MissingStatisticsError, InvalidGenomeError, ExistingStatisticsError, MissingLocusError
from tile_library.constants import TAG_LENGTH, CHR_1, CHR_2, CHR_3, CHR_Y, CHR_M, \
    CHR_OTHER, CHR_NONEXISTANT, SUPPORTED_ASSEMBLY_CHOICES, CHR_CHOICES, \
    ASSEMBLY_16, ASSEMBLY_18, ASSEMBLY_19, GENOME, PATH
import tile_library.test_scripts.complicated_library as build_library
import tile_library.test_scripts.python_lantern as python_lantern

curr_debugging=False
spanning_assemblies_known_to_fail=True

#### TODO: Check different assembly
#### TODO: Implement functionality for assembly with spanning tiles

population = {
    'person1':[
        "ACGGCAGTAGTTTTGCCGCTCGGT C    G  T    CAGAATGTTTGGAGGGCGGTAC                                  GCACCGGAACTTGTGTTTGTGTG TGTG GTCGCCCACTACGCACGTTATATG",
        "ACGGCAGTAGTTTTGCCGCTCGGT T    A       CAGAATGTTTGGAGGGCGGTACG GC TAGAGATATCACCCTCTGCTACTC    CGCACCGGAACTTGTGTTTGTGTG TGTG GTCGCCCACTACGCACGTTATATG"
    ],
    'person2':[
        "ACGGCAGTAGTTTTGCCGCTCGGT         TTTT CAGAATGTTTGGAGGGCGGTACG GC TAGAGATATCACCCTCTGCTACTC AA CGCACCGGAACTTGTGTTTGTGTT TGTG GTCGCCCACTACGCACGTTATATG",
        "ACGGCAGTAGTTTTGCCGCTCGGT T    G  T    CAGAATGTTTGGAGGGCGGTACG GC TAGAGATATCACCCTCTGCTACTC AA CGCACCGGAACTTGTGTTTGTGTT TGTG GTCGCCCACTACGCACGTTATATG"
    ],
    'person3':[
        "ACGGCAGTAGTTTTGCCGCTCGGT T    TT T    CAGAATGTTTGGAGGGCGGTACG GC TAGAGATATCACCCTCTGCTACTC    CGCACCGGAACTTGTGTTTGTGTG TGTG GTCGCCCACTACGCACGTTATATG",
        "ACGGCAGTAGTTTTGCCGCTCGGT         T    CAGAATGTTTGGAGGGCGGTACG GC TAGAGATATCACCCTCTGCTACTC AA CGCACCGGAACTTGTGTTTGTGTT TGTG GTCGCCCACTACGCACGTTATATG"
    ],
    'person4':[
        "ACGGCAGTAGTTTTGCCGCTCGGT AAAC G  T    CAGAATGTTTGGAGGGCGGTACG GC TAGAGATATCACCCTCTGCTACTC AA CGCACCGGAACTTGTGTTTGTGTG TGTG GTCGCCCACTACGCACGTTATATG",
        "ACGGCAGTAGTTTTGCCGCTCGGT C    G  A    CAGAATGTTTGGAGGGCGGTACG GC TAGAGATATCACCCTCTGCTACTC AA CGCACCGGAACTTGTGTTTGTGTG TGTG GTCGCCCACTACGCACGTTATATG"
    ],
    'person5':[
        "ACGGCAGTAGTTTTGCCGCTCGGT C    A       CAGAATGTTTGGAGGGCGGTACG GC TAGAGATATCACCCTCTGCTACTC AA CGCACCGGAACTTGTGTTTGTGTT TGTG GTCGCCCACTACGCACGTTATATG",
        "ACGGCAGTAGTTTTGCCGCTCGGT C    G       CAGAATGTTTGGAGGGCGGTACG GC TAGAGATATCACCCTCTGCTACTC    CGCACCGGAACTTGTGTTTGTGTG TGTG GTCGCCCACTACGCACGTTATATG"
    ],
    'person6':[
        "ACGGCAGTAGTTTTGCCGCTCGGT C    G  TTTT CAGAATGTTTGGAGGGCGGTACG GC TAGAGATATCACCCTCTGCTACTC AA CGCACCGGAACTTGTGTTTGTGTG TGTG GTCGCCCACTACGCACGTTATATG",
        "ACGGCAGTAGTTTTGCCGCTCGGT C    G  T    CAGAATGTTTGGAGGGCGGTAC      AGAGATATCACCCTCTGCTACTC AA CGCACCGGAACTTGTGTTTGTGTG TGTG GTCGCCCACTACGCACGTTATATG"
    ],
    'person7':[
        "ACGGCAGTAGTTTTGCCGCTCGG  C    G  T    CAGAATGTTTGGAGGGCGGTACG GC TAGAGATATCACCCTCTGCTACTC AA CGCACCGGAACTTGTGTTTGTGTT TGTG GTCGCCCACTACGCACGTTATATG",
        "ACGGCAGTAGTTTTGCCGCTCGGT T    G  T    CAGAATGTTTGGAGGGCGGTACG GC TAGAGATATCACCCTCTGCTACTC    CGCACCGGAACTTGTGTTTGTGTG TGTG ATCGCCCACTACGCACGTTATATG"
    ]
}

class QuietHandler(WSGIRequestHandler):
    def log_request(*args, **kwargs):
        pass
httpd = make_server('', python_lantern.LANTERN_PORT, python_lantern.lantern_application, handler_class=QuietHandler)
httpd.quiet = True
server_process = multiprocessing.Process(target=httpd.serve_forever)
def setUpModule():
    global server_process
    #print "Starting python-lantern on port %i ..." % (python_lantern.LANTERN_PORT)
    server_process.start()
def tearDownModule():
    global server_process
    #print "\nClosing python-lantern ..."
    server_process.terminate()
    server_process.join()
    del(server_process)

@skipIf(curr_debugging, "Prevent noise")
class TestBetweenLoci(TestCase):
    def setUp(self):
        build_library.make_entire_library(multiple_assemblies=True)
        build_library.make_lantern_translators()
    def test_failure_non_integer_assembly(self):
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':'fail', 'chromosome':CHR_1, 'lower_base':24, 'upper_base':25})
        self.assertEqual(response.status_code, 400)
        content = json.loads(response.content)
        self.assertEqual(len(content), 1)
        self.assertIn('assembly', content)
    @skipIf(0 in SUPPORTED_ASSEMBLY_CHOICES, "Testing behavior if assembly integer not in choices, but 0 is in choices")
    def test_failure_assembly_not_in_ASSEMBLY_CHOICES(self):
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':0, 'chromosome':CHR_1, 'lower_base':24, 'upper_base':25})
        self.assertEqual(response.status_code, 400)
        content = json.loads(response.content)
        self.assertEqual(len(content), 1)
        self.assertIn('assembly', content)
    def test_failure_assembly_not_loaded_in_database(self):
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_16, 'chromosome':CHR_1, 'lower_base':24, 'upper_base':25})
        self.assertEqual(response.status_code, 404)
        content = json.loads(response.content)
        self.assertEqual(len(content), 1)
        self.assertIn('assembly', content)
    def test_failure_non_integer_chromosome(self):
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_19, 'chromosome':'fail', 'lower_base':24, 'upper_base':25})
        self.assertEqual(response.status_code, 400)
        content = json.loads(response.content)
        self.assertEqual(len(content), 1)
        self.assertIn('chromosome', content)
    @skipIf(0 in CHR_CHOICES, "Testing behavior if chromosome integer not in choices, but 0 is in choices")
    def test_failure_chromosome_not_in_CHROMOSOME_CHOICES(self):
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_19, 'chromosome':0, 'lower_base':24, 'upper_base':25})
        self.assertEqual(response.status_code, 400)
        content = json.loads(response.content)
        self.assertEqual(len(content), 1)
        self.assertIn('chromosome', content)
    def test_failure_chromosome_not_loaded_in_database(self):
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_3, 'lower_base':24, 'upper_base':25})
        self.assertEqual(response.status_code, 404)
        content = json.loads(response.content)
        self.assertEqual(len(content), 1)
        self.assertIn('chromosome', content)
    def test_failure_non_integer_lower_base(self):
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'lower_base':'fail', 'upper_base':25})
        self.assertEqual(response.status_code, 400)
        content = json.loads(response.content)
        self.assertEqual(len(content), 1)
        self.assertIn('lower_base', content)
    def test_failure_too_low_lower_base(self):
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'lower_base':-1, 'upper_base':25})
        self.assertEqual(response.status_code, 404)
        content = json.loads(response.content)
        self.assertEqual(len(content), 1)
        self.assertIn('lower_base', content)
    def test_failure_non_integer_upper_base(self):
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'lower_base':24, 'upper_base':'fail'})
        self.assertEqual(response.status_code, 400)
        content = json.loads(response.content)
        self.assertEqual(len(content), 1)
        self.assertIn('upper_base', content)
    def test_failure_too_high_upper_base(self):
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'lower_base':24, 'upper_base':261})
        self.assertEqual(response.status_code, 404)
        content = json.loads(response.content)
        self.assertEqual(len(content), 1)
        self.assertIn('upper_base', content)
    def test_failure_lower_base_higher_than_upper_base_empty_query_returns_empty_strings(self):
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'lower_base':25, 'upper_base':24})
        self.assertEqual(response.status_code, 400)
        content = json.loads(response.content)
        self.assertEqual(len(content), 1)
        self.assertIn('lower_base-upper_base', content)
    def test_failure_lower_base_equals_upper_base_empty_query_returns_empty_strings(self):
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'lower_base':24, 'upper_base':24})
        self.assertEqual(response.status_code, 400)
        content = json.loads(response.content)
        self.assertEqual(len(content), 1)
        self.assertIn('lower_base-upper_base', content)
    def test_query_in_only_tile_0(self):
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'lower_base':24, 'upper_base':25})
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':["C", "T"],
            'person2':["", "T"],
            'person3':["T", ""],
            'person4':["AAAC", "C"],
            'person5':["C", "C"],
            'person6':["C", "C"],
            'person7':["C", "T"]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_in_only_tile_0_explicit_0_indexing(self):
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'lower_base':24, 'upper_base':25, 'indexing':0})
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':["C", "T"],
            'person2':["", "T"],
            'person3':["T", ""],
            'person4':["AAAC", "C"],
            'person5':["C", "C"],
            'person6':["C", "C"],
            'person7':["C", "T"]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_in_only_tile_0_explicit_1_indexing(self):
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'lower_base':25, 'upper_base':26, 'indexing':1})
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':["C", "T"],
            'person2':["", "T"],
            'person3':["T", ""],
            'person4':["AAAC", "C"],
            'person5':["C", "C"],
            'person6':["C", "C"],
            'person7':["C", "T"]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_in_only_tile_1(self):
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'lower_base':51, 'upper_base':52})
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':["", "C"],
            'person2':["C", "C"],
            'person3':["C", "C"],
            'person4':["C", "C"],
            'person5':["C", "C"],
            'person6':["C", ""],
            'person7':["C", "C"]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_in_only_tile_2(self):
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'lower_base':76, 'upper_base':78})
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':["", ""],
            'person2':["AA", "AA"],
            'person3':["", "AA"],
            'person4':["AA", "AA"],
            'person5':["AA", ""],
            'person6':["AA", "AA"],
            'person7':["AA", ""]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_in_only_tile_3(self):
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'lower_base':102, 'upper_base':106})
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, "TGTG")
    def test_query_in_tile_0_hits_start_tag(self):
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'lower_base':23, 'upper_base':25})
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':["TC", "TT"],
            'person2':["T", "TT"],
            'person3':["TT", "T"],
            'person4':["TAAAC", "TC"],
            'person5':["TC", "TC"],
            'person6':["TC", "TC"],
            'person7':["C", "TT"]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_in_last_tile_in_path_hits_end_tag(self):
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'lower_base':105, 'upper_base':107})
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':["GG", "GG"],
            'person2':["GG", "GG"],
            'person3':["GG", "GG"],
            'person4':["GG", "GG"],
            'person5':["GG", "GG"],
            'person6':["GG", "GG"],
            'person7':["GG", "GA"],
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_in_tile_0_hits_start_and_end_tag(self):
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'lower_base':23, 'upper_base':27})
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':["TCGT", "TTA"],
            'person2':["TTTTT", "TTGT"],
            'person3':["TTTTT", "TT"],
            'person4':["TAAACGT", "TCGA"],
            'person5':["TCA", "TCG"],
            'person6':["TCGTTTT", "TCGT"],
            'person7':["CGT", "TTGT"]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_in_tile_1_hits_start_and_end_tag(self):
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'lower_base':49, 'upper_base':53})
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':["", "GGCT"],
            'person2':["GGCT", "GGCT"],
            'person3':["GGCT", "GGCT"],
            'person4':["GGCT", "GGCT"],
            'person5':["GGCT", "GGCT"],
            'person6':["GGCT", ""],
            'person7':["GGCT", "GGCT"]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_in_tile_2_hits_start_and_end_tag(self):
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'lower_base':75, 'upper_base':79}) #CAAC
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':["", "CC"],
            'person2':["CAAC", "CAAC"],
            'person3':["CC", "CAAC"],
            'person4':["CAAC", "CAAC"],
            'person5':["CAAC", "CC"],
            'person6':["CAAC", "CAAC"],
            'person7':["CAAC", "CC"]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_in_tile_3_hits_start_and_end_tag(self):
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'lower_base':101, 'upper_base':107}) #GTGTGG
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':["GTGTGG", "GTGTGG"],
            'person2':["TTGTGG", "TTGTGG"],
            'person3':["GTGTGG", "TTGTGG"],
            'person4':["GTGTGG", "GTGTGG"],
            'person5':["TTGTGG", "GTGTGG"],
            'person6':["GTGTGG", "GTGTGG"],
            'person7':["TTGTGG", "GTGTGA"]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_in_tiles_0_and_1(self):
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'lower_base':23, 'upper_base':51}) #T | CG | TCAGAATGTTTGGAGGGCGGTACG | G
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':[
                "TCGTCAGAATGTTTGGAGGGCGGTAC",
                "TTACAGAATGTTTGGAGGGCGGTACGG"
            ],
            'person2':[
                "TTTTTCAGAATGTTTGGAGGGCGGTACGG",
                "TTGTCAGAATGTTTGGAGGGCGGTACGG"
            ],
            'person3':[
                "TTTTTCAGAATGTTTGGAGGGCGGTACGG",
                "TTCAGAATGTTTGGAGGGCGGTACGG"
            ],
            'person4':[
                "TAAACGTCAGAATGTTTGGAGGGCGGTACGG",
                "TCGACAGAATGTTTGGAGGGCGGTACGG"
            ],
            'person5':[
                "TCACAGAATGTTTGGAGGGCGGTACGG",
                "TCGCAGAATGTTTGGAGGGCGGTACGG"
            ],
            'person6':[
                "TCGTTTTCAGAATGTTTGGAGGGCGGTACGG",
                "TCGTCAGAATGTTTGGAGGGCGGTAC"
            ],
            'person7':[
                "CGTCAGAATGTTTGGAGGGCGGTACGG",
                "TTGTCAGAATGTTTGGAGGGCGGTACGG"
            ]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_in_tiles_1_and_2(self):
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'lower_base':51, 'upper_base':77}) #C | TAGAGATATCACCCTCTGCTACTC | A
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':[
                "",
                "CTAGAGATATCACCCTCTGCTACTC"
            ],
            'person2':[
                "CTAGAGATATCACCCTCTGCTACTCA",
                "CTAGAGATATCACCCTCTGCTACTCA"
            ],
            'person3':[
                "CTAGAGATATCACCCTCTGCTACTC",
                "CTAGAGATATCACCCTCTGCTACTCA"
            ],
            'person4':[
                "CTAGAGATATCACCCTCTGCTACTCA",
                "CTAGAGATATCACCCTCTGCTACTCA"
            ],
            'person5':[
                "CTAGAGATATCACCCTCTGCTACTCA",
                "CTAGAGATATCACCCTCTGCTACTC"
            ],
            'person6':[
                "CTAGAGATATCACCCTCTGCTACTCA",
                "AGAGATATCACCCTCTGCTACTCA"
            ],
            'person7':[
                "CTAGAGATATCACCCTCTGCTACTCA",
                "CTAGAGATATCACCCTCTGCTACTC"
            ]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_in_tiles_1_and_2_wider_range(self):
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'lower_base':50, 'upper_base':78}) #GC | TAGAGATATCACCCTCTGCTACTC | AA
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':[
                "",
                "GCTAGAGATATCACCCTCTGCTACTC"
            ],
            'person2':[
                "GCTAGAGATATCACCCTCTGCTACTCAA",
                "GCTAGAGATATCACCCTCTGCTACTCAA"
            ],
            'person3':[
                "GCTAGAGATATCACCCTCTGCTACTC",
                "GCTAGAGATATCACCCTCTGCTACTCAA"
            ],
            'person4':[
                "GCTAGAGATATCACCCTCTGCTACTCAA",
                "GCTAGAGATATCACCCTCTGCTACTCAA"
            ],
            'person5':[
                "GCTAGAGATATCACCCTCTGCTACTCAA",
                "GCTAGAGATATCACCCTCTGCTACTC"
            ],
            'person6':[
                "GCTAGAGATATCACCCTCTGCTACTCAA",
                "AGAGATATCACCCTCTGCTACTCAA"
            ],
            'person7':[
                "GCTAGAGATATCACCCTCTGCTACTCAA",
                "GCTAGAGATATCACCCTCTGCTACTC"
            ]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_in_tiles_2_and_3(self):
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'lower_base':77, 'upper_base':107}) #A | CGCACCGGAACTTGTGTTTGTGTG | TGTG | G
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':[
                "GCACCGGAACTTGTGTTTGTGTGTGTGG",
                "CGCACCGGAACTTGTGTTTGTGTGTGTGG"
            ],
            'person2':[
                "ACGCACCGGAACTTGTGTTTGTGTTTGTGG",
                "ACGCACCGGAACTTGTGTTTGTGTTTGTGG"
            ],
            'person3':[
                "CGCACCGGAACTTGTGTTTGTGTGTGTGG",
                "ACGCACCGGAACTTGTGTTTGTGTTTGTGG"
            ],
            'person4':[
                "ACGCACCGGAACTTGTGTTTGTGTGTGTGG",
                "ACGCACCGGAACTTGTGTTTGTGTGTGTGG"
            ],
            'person5':[
                "ACGCACCGGAACTTGTGTTTGTGTTTGTGG",
                "CGCACCGGAACTTGTGTTTGTGTGTGTGG"
            ],
            'person6':[
                "ACGCACCGGAACTTGTGTTTGTGTGTGTGG",
                "ACGCACCGGAACTTGTGTTTGTGTGTGTGG"
            ],
            'person7':[
                "ACGCACCGGAACTTGTGTTTGTGTTTGTGG",
                "CGCACCGGAACTTGTGTTTGTGTGTGTGA"
            ]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_over_paths_simplest(self):
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'lower_base':129, 'upper_base':131}) #G || A
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, "GA")
    def test_query_in_tiles_0_1_and_2(self):
        #T | CG | TCAGAATGTTTGGAGGGCGGTACG | GC | TAGAGATATCACCCTCTGCTACTC | A
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'lower_base':23, 'upper_base':77})
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':[
                "TCGTCAGAATGTTTGGAGGGCGGTAC",
                "TTACAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTC"
            ],
            'person2':[
                "TTTTTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCA",
                "TTGTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCA"
            ],
            'person3':[
                "TTTTTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTC",
                "TTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCA"
            ],
            'person4':[
                "TAAACGTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCA",
                "TCGACAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCA"
            ],
            'person5':[
                "TCACAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCA",
                "TCGCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTC"
            ],
            'person6':[
                "TCGTTTTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCA",
                "TCGTCAGAATGTTTGGAGGGCGGTACAGAGATATCACCCTCTGCTACTCA"
            ],
            'person7':[
                "CGTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCA",
                "TTGTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTC"
            ]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_in_tiles_1_2_and_3(self):
        #C | TAGAGATATCACCCTCTGCTACTC | AA | CGCACCGGAACTTGTGTTTGTGTG | TGTG | G
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'lower_base':51, 'upper_base':107})
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':[
                "GCACCGGAACTTGTGTTTGTGTGTGTGG",
                "CTAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTGTGTGG"
            ],
            'person2':[
                "CTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGG",
                "CTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGG"
            ],
            'person3':[
                "CTAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTGTGTGG",
                "CTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGG"
            ],
            'person4':[
                "CTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTGTGTGG",
                "CTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTGTGTGG"
            ],
            'person5':[
                "CTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGG",
                "CTAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTGTGTGG"
            ],
            'person6':[
                "CTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTGTGTGG",
                "AGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTGTGTGG"
            ],
            'person7':[
                "CTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGG",
                "CTAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTGTGTGA"
            ]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_in_tiles_2_3_and_next_path(self):
        #A | CGCACCGGAACTTGTGTTTGTGTG | TGTG | GTCGCCCACTACGCACGTTATATG || A
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'lower_base':77, 'upper_base':131})
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':[
                "GCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA",
                "CGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA"
            ],
            'person2':[
                "ACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATGA",
                "ACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATGA"
            ],
            'person3':[
                "CGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA",
                "ACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATGA"
            ],
            'person4':[
                "ACGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA",
                "ACGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA"
            ],
            'person5':[
                "ACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATGA",
                "CGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA"
            ],
            'person6':[
                "ACGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA",
                "ACGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA"
            ],
            'person7':[
                "ACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATGA",
                "CGCACCGGAACTTGTGTTTGTGTGTGTGATCGCCCACTACGCACGTTATATGA"
            ]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_in_tiles_0_1_2_and_3(self):
        #T | CG | TCAGAATGTTTGGAGGGCGGTACG | GC | TAGAGATATCACCCTCTGCTACTC | AA | CGCACCGGAACTTGTGTTTGTGTG | TGTG | G
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'lower_base':23, 'upper_base':107})
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':[
                "TCGTCAGAATGTTTGGAGGGCGGTACGCACCGGAACTTGTGTTTGTGTGTGTGG",
                "TTACAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTGTGTGG"
            ],
            'person2':[
                "TTTTTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGG",
                "TTGTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGG"
            ],
            'person3':[
                "TTTTTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTGTGTGG",
                "TTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGG"
            ],
            'person4':[
                "TAAACGTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTGTGTGG",
                "TCGACAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTGTGTGG"
            ],
            'person5':[
                "TCACAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGG",
                "TCGCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTGTGTGG"
            ],
            'person6':[
                "TCGTTTTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTGTGTGG",
                "TCGTCAGAATGTTTGGAGGGCGGTACAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTGTGTGG"
            ],
            'person7':[
                "CGTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGG",
                "TTGTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTGTGTGA"
            ]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_in_tiles_1_2_3_and_next_path(self):
        #C | TAGAGATATCACCCTCTGCTACTC | AA | CGCACCGGAACTTGTGTTTGTGTG | TGTG | GTCGCCCACTACGCACGTTATATG || A
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'lower_base':51, 'upper_base':131})
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':[
                "GCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA",
                "CTAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA"
            ],
            'person2':[
                "CTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATGA",
                "CTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATGA"
            ],
            'person3':[
                "CTAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA",
                "CTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATGA"
            ],
            'person4':[
                "CTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA",
                "CTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA"
            ],
            'person5':[
                "CTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATGA",
                "CTAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA"
            ],
            'person6':[
                "CTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA",
                "AGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA"
            ],
            'person7':[
                "CTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATGA",
                "CTAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTGTGTGATCGCCCACTACGCACGTTATATGA"
            ]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_in_tiles_0_1_2_3_and_next_path(self):
        #T | CG | TCAGAATGTTTGGAGGGCGGTACG | GC | TAGAGATATCACCCTCTGCTACTC | AA | CGCACCGGAACTTGTGTTTGTGTG | TGTG | GTCGCCCACTACGCACGTTATATG || A
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'lower_base':23, 'upper_base':131})
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':[
                "TCGTCAGAATGTTTGGAGGGCGGTACGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA",
                "TTACAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA"
            ],
            'person2':[
                "TTTTTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATGA",
                "TTGTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATGA"
            ],
            'person3':[
                "TTTTTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA",
                "TTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATGA"
            ],
            'person4':[
                "TAAACGTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA",
                "TCGACAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA"
            ],
            'person5':[
                "TCACAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATGA",
                "TCGCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA"
            ],
            'person6':[
                "TCGTTTTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA",
                "TCGTCAGAATGTTTGGAGGGCGGTACAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA"
            ],
            'person7':[
                "CGTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATGA",
                "TTGTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTGTGTGATCGCCCACTACGCACGTTATATGA"
            ]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_entire_first_path_and_first_base_of_next_path(self):
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'lower_base':0, 'upper_base':131})
        content = json.loads(response.content)
        checking = {
            'person1':[
                "ACGGCAGTAGTTTTGCCGCTCGGTCGTCAGAATGTTTGGAGGGCGGTACGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA",
                "ACGGCAGTAGTTTTGCCGCTCGGTTACAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA"
            ],
            'person2':[
                "ACGGCAGTAGTTTTGCCGCTCGGTTTTTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATGA",
                "ACGGCAGTAGTTTTGCCGCTCGGTTGTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATGA"
            ],
            'person3':[
                "ACGGCAGTAGTTTTGCCGCTCGGTTTTTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA",
                "ACGGCAGTAGTTTTGCCGCTCGGTTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATGA"
            ],
            'person4':[
                "ACGGCAGTAGTTTTGCCGCTCGGTAAACGTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA",
                "ACGGCAGTAGTTTTGCCGCTCGGTCGACAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA"
            ],
            'person5':[
                "ACGGCAGTAGTTTTGCCGCTCGGTCACAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATGA",
                "ACGGCAGTAGTTTTGCCGCTCGGTCGCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA"
            ],
            'person6':[
                "ACGGCAGTAGTTTTGCCGCTCGGTCGTTTTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA",
                "ACGGCAGTAGTTTTGCCGCTCGGTCGTCAGAATGTTTGGAGGGCGGTACAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA"
            ],
            'person7':[
                "ACGGCAGTAGTTTTGCCGCTCGGCGTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATGA",
                "ACGGCAGTAGTTTTGCCGCTCGGTTGTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTGTGTGATCGCCCACTACGCACGTTATATGA"
            ]
        }
        self.assertEqual(len(content), len(population))
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_different_chromosome(self):
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_2, 'lower_base':0, 'upper_base':1})
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, 'C')

@skipIf(spanning_assemblies_known_to_fail, "Assembly 18 contains spanning tiles as the default")
class TestBetweenLociAssembly18(TestCase):
    def setUp(self):
        build_library.make_entire_library(multiple_assemblies=True)
        build_library.make_lantern_translators()
    def test_query_in_only_tile_0(self):
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_18, 'chromosome':CHR_1, 'lower_base':24, 'upper_base':25})
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':["C", "T"],
            'person2':["", "T"],
            'person3':["T", ""],
            'person4':["AAAC", "C"],
            'person5':["C", "C"],
            'person6':["C", "C"],
            'person7':["C", "T"]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_in_only_tile_0_explicit_0_indexing(self):
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_18, 'chromosome':CHR_1, 'lower_base':24, 'upper_base':25, 'indexing':0})
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':["C", "T"],
            'person2':["", "T"],
            'person3':["T", ""],
            'person4':["AAAC", "C"],
            'person5':["C", "C"],
            'person6':["C", "C"],
            'person7':["C", "T"]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_in_only_tile_0_explicit_1_indexing(self):
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_18, 'chromosome':CHR_1, 'lower_base':25, 'upper_base':26, 'indexing':1})
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':["C", "T"],
            'person2':["", "T"],
            'person3':["T", ""],
            'person4':["AAAC", "C"],
            'person5':["C", "C"],
            'person6':["C", "C"],
            'person7':["C", "T"]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_in_only_tile_1(self):
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'lower_base':51, 'upper_base':52})
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':["", "C"],
            'person2':["C", "C"],
            'person3':["C", "C"],
            'person4':["C", "C"],
            'person5':["C", "C"],
            'person6':["C", ""],
            'person7':["C", "C"]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_in_only_tile_2(self):
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'lower_base':76, 'upper_base':78})
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':["", ""],
            'person2':["AA", "AA"],
            'person3':["", "AA"],
            'person4':["AA", "AA"],
            'person5':["AA", ""],
            'person6':["AA", "AA"],
            'person7':["AA", ""]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_in_only_tile_3(self):
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'lower_base':102, 'upper_base':106})
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, "TGTG")
    def test_query_in_tile_0_hits_start_tag(self):
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'lower_base':23, 'upper_base':25})
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':["TC", "TT"],
            'person2':["T", "TT"],
            'person3':["TT", "T"],
            'person4':["TAAAC", "TC"],
            'person5':["TC", "TC"],
            'person6':["TC", "TC"],
            'person7':["C", "TT"]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_in_last_tile_in_path_hits_end_tag(self):
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'lower_base':105, 'upper_base':107})
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':["GG", "GG"],
            'person2':["GG", "GG"],
            'person3':["GG", "GG"],
            'person4':["GG", "GG"],
            'person5':["GG", "GG"],
            'person6':["GG", "GG"],
            'person7':["GG", "GA"],
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_in_tile_0_hits_start_and_end_tag(self):
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'lower_base':23, 'upper_base':27})
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':["TCGT", "TTA"],
            'person2':["TTTTT", "TTGT"],
            'person3':["TTTTT", "TT"],
            'person4':["TAAACGT", "TCGA"],
            'person5':["TCA", "TCG"],
            'person6':["TCGTTTT", "TCGT"],
            'person7':["CGT", "TTGT"]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_in_tile_1_hits_start_and_end_tag(self):
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'lower_base':49, 'upper_base':53})
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':["", "GGCT"],
            'person2':["GGCT", "GGCT"],
            'person3':["GGCT", "GGCT"],
            'person4':["GGCT", "GGCT"],
            'person5':["GGCT", "GGCT"],
            'person6':["GGCT", ""],
            'person7':["GGCT", "GGCT"]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_in_tile_2_hits_start_and_end_tag(self):
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'lower_base':75, 'upper_base':79}) #CAAC
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':["", "CC"],
            'person2':["CAAC", "CAAC"],
            'person3':["CC", "CAAC"],
            'person4':["CAAC", "CAAC"],
            'person5':["CAAC", "CC"],
            'person6':["CAAC", "CAAC"],
            'person7':["CAAC", "CC"]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_in_tile_3_hits_start_and_end_tag(self):
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'lower_base':101, 'upper_base':107}) #GTGTGG
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':["GTGTGG", "GTGTGG"],
            'person2':["TTGTGG", "TTGTGG"],
            'person3':["GTGTGG", "TTGTGG"],
            'person4':["GTGTGG", "GTGTGG"],
            'person5':["TTGTGG", "GTGTGG"],
            'person6':["GTGTGG", "GTGTGG"],
            'person7':["TTGTGG", "GTGTGA"]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_in_tiles_0_and_1(self):
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'lower_base':23, 'upper_base':51}) #T | CG | TCAGAATGTTTGGAGGGCGGTACG | G
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':[
                "TCGTCAGAATGTTTGGAGGGCGGTAC",
                "TTACAGAATGTTTGGAGGGCGGTACGG"
            ],
            'person2':[
                "TTTTTCAGAATGTTTGGAGGGCGGTACGG",
                "TTGTCAGAATGTTTGGAGGGCGGTACGG"
            ],
            'person3':[
                "TTTTTCAGAATGTTTGGAGGGCGGTACGG",
                "TTCAGAATGTTTGGAGGGCGGTACGG"
            ],
            'person4':[
                "TAAACGTCAGAATGTTTGGAGGGCGGTACGG",
                "TCGACAGAATGTTTGGAGGGCGGTACGG"
            ],
            'person5':[
                "TCACAGAATGTTTGGAGGGCGGTACGG",
                "TCGCAGAATGTTTGGAGGGCGGTACGG"
            ],
            'person6':[
                "TCGTTTTCAGAATGTTTGGAGGGCGGTACGG",
                "TCGTCAGAATGTTTGGAGGGCGGTAC"
            ],
            'person7':[
                "CGTCAGAATGTTTGGAGGGCGGTACGG",
                "TTGTCAGAATGTTTGGAGGGCGGTACGG"
            ]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_in_tiles_1_and_2(self):
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'lower_base':51, 'upper_base':77}) #C | TAGAGATATCACCCTCTGCTACTC | A
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':[
                "",
                "CTAGAGATATCACCCTCTGCTACTC"
            ],
            'person2':[
                "CTAGAGATATCACCCTCTGCTACTCA",
                "CTAGAGATATCACCCTCTGCTACTCA"
            ],
            'person3':[
                "CTAGAGATATCACCCTCTGCTACTC",
                "CTAGAGATATCACCCTCTGCTACTCA"
            ],
            'person4':[
                "CTAGAGATATCACCCTCTGCTACTCA",
                "CTAGAGATATCACCCTCTGCTACTCA"
            ],
            'person5':[
                "CTAGAGATATCACCCTCTGCTACTCA",
                "CTAGAGATATCACCCTCTGCTACTC"
            ],
            'person6':[
                "CTAGAGATATCACCCTCTGCTACTCA",
                "AGAGATATCACCCTCTGCTACTCA"
            ],
            'person7':[
                "CTAGAGATATCACCCTCTGCTACTCA",
                "CTAGAGATATCACCCTCTGCTACTC"
            ]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_in_tiles_1_and_2_wider_range(self):
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'lower_base':50, 'upper_base':78}) #GC | TAGAGATATCACCCTCTGCTACTC | AA
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':[
                "",
                "GCTAGAGATATCACCCTCTGCTACTC"
            ],
            'person2':[
                "GCTAGAGATATCACCCTCTGCTACTCAA",
                "GCTAGAGATATCACCCTCTGCTACTCAA"
            ],
            'person3':[
                "GCTAGAGATATCACCCTCTGCTACTC",
                "GCTAGAGATATCACCCTCTGCTACTCAA"
            ],
            'person4':[
                "GCTAGAGATATCACCCTCTGCTACTCAA",
                "GCTAGAGATATCACCCTCTGCTACTCAA"
            ],
            'person5':[
                "GCTAGAGATATCACCCTCTGCTACTCAA",
                "GCTAGAGATATCACCCTCTGCTACTC"
            ],
            'person6':[
                "GCTAGAGATATCACCCTCTGCTACTCAA",
                "AGAGATATCACCCTCTGCTACTCAA"
            ],
            'person7':[
                "GCTAGAGATATCACCCTCTGCTACTCAA",
                "GCTAGAGATATCACCCTCTGCTACTC"
            ]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_in_tiles_2_and_3(self):
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'lower_base':77, 'upper_base':107}) #A | CGCACCGGAACTTGTGTTTGTGTG | TGTG | G
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':[
                "GCACCGGAACTTGTGTTTGTGTGTGTGG",
                "CGCACCGGAACTTGTGTTTGTGTGTGTGG"
            ],
            'person2':[
                "ACGCACCGGAACTTGTGTTTGTGTTTGTGG",
                "ACGCACCGGAACTTGTGTTTGTGTTTGTGG"
            ],
            'person3':[
                "CGCACCGGAACTTGTGTTTGTGTGTGTGG",
                "ACGCACCGGAACTTGTGTTTGTGTTTGTGG"
            ],
            'person4':[
                "ACGCACCGGAACTTGTGTTTGTGTGTGTGG",
                "ACGCACCGGAACTTGTGTTTGTGTGTGTGG"
            ],
            'person5':[
                "ACGCACCGGAACTTGTGTTTGTGTTTGTGG",
                "CGCACCGGAACTTGTGTTTGTGTGTGTGG"
            ],
            'person6':[
                "ACGCACCGGAACTTGTGTTTGTGTGTGTGG",
                "ACGCACCGGAACTTGTGTTTGTGTGTGTGG"
            ],
            'person7':[
                "ACGCACCGGAACTTGTGTTTGTGTTTGTGG",
                "CGCACCGGAACTTGTGTTTGTGTGTGTGA"
            ]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_over_paths_simplest(self):
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'lower_base':129, 'upper_base':131}) #G || A
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, "GA")
    def test_query_in_tiles_0_1_and_2(self):
        #T | CG | TCAGAATGTTTGGAGGGCGGTACG | GC | TAGAGATATCACCCTCTGCTACTC | A
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'lower_base':23, 'upper_base':77})
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':[
                "TCGTCAGAATGTTTGGAGGGCGGTAC",
                "TTACAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTC"
            ],
            'person2':[
                "TTTTTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCA",
                "TTGTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCA"
            ],
            'person3':[
                "TTTTTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTC",
                "TTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCA"
            ],
            'person4':[
                "TAAACGTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCA",
                "TCGACAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCA"
            ],
            'person5':[
                "TCACAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCA",
                "TCGCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTC"
            ],
            'person6':[
                "TCGTTTTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCA",
                "TCGTCAGAATGTTTGGAGGGCGGTACAGAGATATCACCCTCTGCTACTCA"
            ],
            'person7':[
                "CGTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCA",
                "TTGTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTC"
            ]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_in_tiles_1_2_and_3(self):
        #C | TAGAGATATCACCCTCTGCTACTC | AA | CGCACCGGAACTTGTGTTTGTGTG | TGTG | G
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'lower_base':51, 'upper_base':107})
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':[
                "GCACCGGAACTTGTGTTTGTGTGTGTGG",
                "CTAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTGTGTGG"
            ],
            'person2':[
                "CTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGG",
                "CTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGG"
            ],
            'person3':[
                "CTAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTGTGTGG",
                "CTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGG"
            ],
            'person4':[
                "CTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTGTGTGG",
                "CTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTGTGTGG"
            ],
            'person5':[
                "CTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGG",
                "CTAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTGTGTGG"
            ],
            'person6':[
                "CTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTGTGTGG",
                "AGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTGTGTGG"
            ],
            'person7':[
                "CTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGG",
                "CTAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTGTGTGA"
            ]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_in_tiles_2_3_and_next_path(self):
        #A | CGCACCGGAACTTGTGTTTGTGTG | TGTG | GTCGCCCACTACGCACGTTATATG || A
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'lower_base':77, 'upper_base':131})
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':[
                "GCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA",
                "CGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA"
            ],
            'person2':[
                "ACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATGA",
                "ACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATGA"
            ],
            'person3':[
                "CGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA",
                "ACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATGA"
            ],
            'person4':[
                "ACGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA",
                "ACGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA"
            ],
            'person5':[
                "ACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATGA",
                "CGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA"
            ],
            'person6':[
                "ACGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA",
                "ACGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA"
            ],
            'person7':[
                "ACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATGA",
                "CGCACCGGAACTTGTGTTTGTGTGTGTGATCGCCCACTACGCACGTTATATGA"
            ]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_in_tiles_0_1_2_and_3(self):
        #T | CG | TCAGAATGTTTGGAGGGCGGTACG | GC | TAGAGATATCACCCTCTGCTACTC | AA | CGCACCGGAACTTGTGTTTGTGTG | TGTG | G
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'lower_base':23, 'upper_base':107})
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':[
                "TCGTCAGAATGTTTGGAGGGCGGTACGCACCGGAACTTGTGTTTGTGTGTGTGG",
                "TTACAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTGTGTGG"
            ],
            'person2':[
                "TTTTTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGG",
                "TTGTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGG"
            ],
            'person3':[
                "TTTTTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTGTGTGG",
                "TTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGG"
            ],
            'person4':[
                "TAAACGTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTGTGTGG",
                "TCGACAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTGTGTGG"
            ],
            'person5':[
                "TCACAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGG",
                "TCGCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTGTGTGG"
            ],
            'person6':[
                "TCGTTTTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTGTGTGG",
                "TCGTCAGAATGTTTGGAGGGCGGTACAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTGTGTGG"
            ],
            'person7':[
                "CGTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGG",
                "TTGTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTGTGTGA"
            ]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_in_tiles_1_2_3_and_next_path(self):
        #C | TAGAGATATCACCCTCTGCTACTC | AA | CGCACCGGAACTTGTGTTTGTGTG | TGTG | GTCGCCCACTACGCACGTTATATG || A
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'lower_base':51, 'upper_base':131})
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':[
                "GCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA",
                "CTAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA"
            ],
            'person2':[
                "CTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATGA",
                "CTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATGA"
            ],
            'person3':[
                "CTAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA",
                "CTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATGA"
            ],
            'person4':[
                "CTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA",
                "CTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA"
            ],
            'person5':[
                "CTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATGA",
                "CTAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA"
            ],
            'person6':[
                "CTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA",
                "AGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA"
            ],
            'person7':[
                "CTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATGA",
                "CTAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTGTGTGATCGCCCACTACGCACGTTATATGA"
            ]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_in_tiles_0_1_2_3_and_next_path(self):
        #T | CG | TCAGAATGTTTGGAGGGCGGTACG | GC | TAGAGATATCACCCTCTGCTACTC | AA | CGCACCGGAACTTGTGTTTGTGTG | TGTG | GTCGCCCACTACGCACGTTATATG || A
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'lower_base':23, 'upper_base':131})
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':[
                "TCGTCAGAATGTTTGGAGGGCGGTACGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA",
                "TTACAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA"
            ],
            'person2':[
                "TTTTTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATGA",
                "TTGTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATGA"
            ],
            'person3':[
                "TTTTTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA",
                "TTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATGA"
            ],
            'person4':[
                "TAAACGTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA",
                "TCGACAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA"
            ],
            'person5':[
                "TCACAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATGA",
                "TCGCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA"
            ],
            'person6':[
                "TCGTTTTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA",
                "TCGTCAGAATGTTTGGAGGGCGGTACAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA"
            ],
            'person7':[
                "CGTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATGA",
                "TTGTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTGTGTGATCGCCCACTACGCACGTTATATGA"
            ]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_entire_first_path_and_first_base_of_next_path(self):
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'lower_base':0, 'upper_base':131})
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, population[person_name][i]+'A')
    def test_query_different_chromosome(self):
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_2, 'lower_base':0, 'upper_base':1})
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, 'C')

@skipIf(curr_debugging, "Prevent noise")
class TestAroundLocus(TestCase):
    def setUp(self):
        build_library.make_entire_library(multiple_assemblies=True)
        build_library.make_lantern_translators()
    def test_failure_non_integer_assembly(self):
        response = self.client.get(reverse('api:pop_around_locus'), {'assembly':'fail', 'chromosome':CHR_1, 'target_base':25})
        self.assertEqual(response.status_code, 400)
        content = json.loads(response.content)
        self.assertEqual(len(content), 1)
        self.assertIn('assembly', content)
    @skipIf(0 in SUPPORTED_ASSEMBLY_CHOICES, "Testing behavior if assembly integer not in choices, but 0 is in choices")
    def test_failure_assembly_not_in_ASSEMBLY_CHOICES(self):
        response = self.client.get(reverse('api:pop_around_locus'), {'assembly':0, 'chromosome':CHR_1, 'target_base':25})
        self.assertEqual(response.status_code, 400)
        content = json.loads(response.content)
        self.assertEqual(len(content), 1)
        self.assertIn('assembly', content)
    def test_failure_assembly_not_loaded_in_database(self):
        response = self.client.get(reverse('api:pop_around_locus'), {'assembly':ASSEMBLY_16, 'chromosome':CHR_1, 'target_base':25})
        self.assertEqual(response.status_code, 404)
        content = json.loads(response.content)
        self.assertEqual(len(content), 1)
        self.assertIn('assembly', content)
    def test_failure_non_integer_chromosome(self):
        response = self.client.get(reverse('api:pop_around_locus'), {'assembly':ASSEMBLY_19, 'chromosome':'fail', 'target_base':25})
        self.assertEqual(response.status_code, 400)
        content = json.loads(response.content)
        self.assertEqual(len(content), 1)
        self.assertIn('chromosome', content)
    @skipIf(0 in CHR_CHOICES, "Testing behavior if chromosome integer not in choices, but 0 is in choices")
    def test_failure_chromosome_not_in_CHROMOSOME_CHOICES(self):
        response = self.client.get(reverse('api:pop_around_locus'), {'assembly':ASSEMBLY_19, 'chromosome':0, 'target_base':25})
        self.assertEqual(response.status_code, 400)
        content = json.loads(response.content)
        self.assertEqual(len(content), 1)
        self.assertIn('chromosome', content)
    def test_failure_chromosome_not_loaded_in_database(self):
        response = self.client.get(reverse('api:pop_around_locus'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_3, 'target_base':25})
        self.assertEqual(response.status_code, 404)
        content = json.loads(response.content)
        self.assertEqual(len(content), 1)
        self.assertIn('chromosome', content)
    def test_failure_non_integer_target_base(self):
        response = self.client.get(reverse('api:pop_around_locus'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'target_base':'fail'})
        self.assertEqual(response.status_code, 400)
        content = json.loads(response.content)
        self.assertEqual(len(content), 1)
        self.assertIn('target_base', content)
    def test_failure_too_low_target_base(self):
        response = self.client.get(reverse('api:pop_around_locus'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'target_base':-1})
        self.assertEqual(response.status_code, 404)
        content = json.loads(response.content)
        self.assertEqual(len(content), 1)
        self.assertIn('target_base-number_around', content)
    def test_failure_too_low_target_base_with_number_around(self):
        response = self.client.get(reverse('api:pop_around_locus'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'target_base':0})
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('api:pop_around_locus'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'target_base':0, 'number_around':1})
        self.assertEqual(response.status_code, 404)
        content = json.loads(response.content)
        self.assertEqual(len(content), 1)
        self.assertIn('target_base-number_around', content)
    def test_failure_too_high_target_base(self):
        response = self.client.get(reverse('api:pop_around_locus'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'target_base':260})
        self.assertEqual(response.status_code, 404)
        content = json.loads(response.content)
        self.assertEqual(len(content), 1)
        self.assertIn('target_base+number_around', content)
    def test_failure_too_high_target_base_with_number_around(self):
        #Requires defining a lot more variables for path 1, so not going to call it right now
        #response = self.client.get(reverse('api:pop_around_locus'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'target_base':259})
        #self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('api:pop_around_locus'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'target_base':259, 'number_around':1})
        self.assertEqual(response.status_code, 404)
        content = json.loads(response.content)
        self.assertEqual(len(content), 1)
        self.assertIn('target_base+number_around', content)
    def test_failure_non_integer_number_around(self):
        response = self.client.get(reverse('api:pop_around_locus'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'target_base':25, 'number_around':'fail'})
        self.assertEqual(response.status_code, 400)
        content = json.loads(response.content)
        self.assertEqual(len(content), 1)
        self.assertIn('number_around', content)
    def test_failure_negative_number_around(self):
        response = self.client.get(reverse('api:pop_around_locus'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'target_base':25, 'number_around':-1})
        self.assertEqual(response.status_code, 400)
        content = json.loads(response.content)
        self.assertEqual(len(content), 1)
        self.assertIn('number_around', content)
    def test_query_in_only_tile_0(self):
        response = self.client.get(reverse('api:pop_around_locus'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'target_base':24})
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':["C", "T"],
            'person2':["", "T"],
            'person3':["T", ""],
            'person4':["AAAC", "C"],
            'person5':["C", "C"],
            'person6':["C", "C"],
            'person7':["C", "T"]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_in_only_tile_0_not_touching_tags(self):
        response = self.client.get(reverse('api:pop_around_locus'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'target_base':25})
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':['G', 'A'],
            'person2':['', 'G'],
            'person3':['TT', ''],
            'person4':['G', 'G'],
            'person5':['A', 'G'],
            'person6':['G', 'G'],
            'person7':['G', 'G']
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_in_only_tile_0_explicit_0_indexing(self):
        response = self.client.get(reverse('api:pop_around_locus'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'target_base':24, 'indexing':0})
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':["C", "T"],
            'person2':["", "T"],
            'person3':["T", ""],
            'person4':["AAAC", "C"],
            'person5':["C", "C"],
            'person6':["C", "C"],
            'person7':["C", "T"]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_in_only_tile_0_explicit_1_indexing(self):
        response = self.client.get(reverse('api:pop_around_locus'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'target_base':25, 'indexing':1})
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':["C", "T"],
            'person2':["", "T"],
            'person3':["T", ""],
            'person4':["AAAC", "C"],
            'person5':["C", "C"],
            'person6':["C", "C"],
            'person7':["C", "T"]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_in_only_tile_1(self):
        response = self.client.get(reverse('api:pop_around_locus'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'target_base':51})
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':["", "C"],
            'person2':["C", "C"],
            'person3':["C", "C"],
            'person4':["C", "C"],
            'person5':["C", "C"],
            'person6':["C", ""],
            'person7':["C", "C"]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_in_only_tile_2(self):
        response = self.client.get(reverse('api:pop_around_locus'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'target_base':76})
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':["", ""],
            'person2':["A", "A"],
            'person3':["", "A"],
            'person4':["A", "A"],
            'person5':["A", ""],
            'person6':["A", "A"],
            'person7':["A", ""]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_in_only_tile_3(self):
        response = self.client.get(reverse('api:pop_around_locus'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'target_base':103, 'number_around':1})
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, "TGT")
    def test_query_in_tile_0_hits_start_tag(self):
        response = self.client.get(reverse('api:pop_around_locus'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'target_base':24, 'number_around':1})
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':["TCG", "TTA"],
            'person2':["TT", "TTG"],
            'person3':["TTT", "TT"],
            'person4':["TAAACG", "TCG"],
            'person5':["TCA", "TCG"],
            'person6':["TCG", "TCG"],
            'person7':["GCG", "TTG"]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_in_last_tile_in_path_hits_end_tag(self):
        response = self.client.get(reverse('api:pop_around_locus'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'target_base':105, 'number_around':1})
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':["TGG", "TGG"],
            'person2':["TGG", "TGG"],
            'person3':["TGG", "TGG"],
            'person4':["TGG", "TGG"],
            'person5':["TGG", "TGG"],
            'person6':["TGG", "TGG"],
            'person7':["TGG", "TGA"],
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_in_tile_0_hits_start_and_end_tag(self):
        response = self.client.get(reverse('api:pop_around_locus'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'target_base':24, 'number_around':2})
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':["GTCGT", "GTTAC"],
            'person2':["GTTT", "GTTGT"],
            'person3':["GTTTT", "GTTC"],
            'person4':["GTAAACGT", "GTCGA"],
            'person5':["GTCAC", "GTCGC"],
            'person6':["GTCGT", "GTCGT"],
            'person7':["GGCGT", "GTTGT"]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_in_tile_1_hits_start_and_end_tag(self):
        response = self.client.get(reverse('api:pop_around_locus'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'target_base':50, 'number_around':2})
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':["ACGC", "CGGCT"],
            'person2':["CGGCT", "CGGCT"],
            'person3':["CGGCT", "CGGCT"],
            'person4':["CGGCT", "CGGCT"],
            'person5':["CGGCT", "CGGCT"],
            'person6':["CGGCT", "ACAG"],
            'person7':["CGGCT", "CGGCT"]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_in_tile_2_hits_start_and_end_tag(self):
        response = self.client.get(reverse('api:pop_around_locus'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'target_base':76, 'number_around':2}) #CAAC
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':["ACGC", "TCCG"],
            'person2':["TCAAC", "TCAAC"],
            'person3':["TCCG", "TCAAC"],
            'person4':["TCAAC", "TCAAC"],
            'person5':["TCAAC", "TCCG"],
            'person6':["TCAAC", "TCAAC"],
            'person7':["TCAAC", "TCCG"]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_in_tile_3_hits_start_and_end_tag(self):
        response = self.client.get(reverse('api:pop_around_locus'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'target_base':103, 'number_around':3})
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':["TGTGTGG", "TGTGTGG"],
            'person2':["TTTGTGG", "TTTGTGG"],
            'person3':["TGTGTGG", "TTTGTGG"],
            'person4':["TGTGTGG", "TGTGTGG"],
            'person5':["TTTGTGG", "TGTGTGG"],
            'person6':["TGTGTGG", "TGTGTGG"],
            'person7':["TTTGTGG", "TGTGTGA"]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_in_tiles_0_and_1(self):
        response = self.client.get(reverse('api:pop_around_locus'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'target_base':37, 'number_around':14}) #T | CG | TCAGAATGTTTGGAGGGCGGTACG | G
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':[
                "TCGTCAGAATGTTTGGAGGGCGGTACGCA",
                "GTTACAGAATGTTTGGAGGGCGGTACGGC"
            ],
            'person2':[
                "TTTTCAGAATGTTTGGAGGGCGGTACGGC",
                "TTGTCAGAATGTTTGGAGGGCGGTACGGC"
            ],
            'person3':[
                "TTTTCAGAATGTTTGGAGGGCGGTACGGC",
                "GGTTCAGAATGTTTGGAGGGCGGTACGGC"
            ],
            'person4':[
                "ACGTCAGAATGTTTGGAGGGCGGTACGGC",
                "TCGACAGAATGTTTGGAGGGCGGTACGGC"
            ],
            'person5':[
                "GTCACAGAATGTTTGGAGGGCGGTACGGC",
                "GTCGCAGAATGTTTGGAGGGCGGTACGGC"
            ],
            'person6':[
                "TTTTCAGAATGTTTGGAGGGCGGTACGGC",
                "TCGTCAGAATGTTTGGAGGGCGGTACAGA"
            ],
            'person7':[
                "GCGTCAGAATGTTTGGAGGGCGGTACGGC",
                "TTGTCAGAATGTTTGGAGGGCGGTACGGC"
            ]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_in_tiles_1_and_2(self):
        response = self.client.get(reverse('api:pop_around_locus'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'target_base':64, 'number_around':13}) #C | TAGAGATATCACCCTCTGCTACTC | AA
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':[
                "TGGAGGGCGGTACGCACCGGAACTTG",
                "CTAGAGATATCACCCTCTGCTACTCCG"
            ],
            'person2':[
                "CTAGAGATATCACCCTCTGCTACTCAA",
                "CTAGAGATATCACCCTCTGCTACTCAA"
            ],
            'person3':[
                "CTAGAGATATCACCCTCTGCTACTCCG",
                "CTAGAGATATCACCCTCTGCTACTCAA"
            ],
            'person4':[
                "CTAGAGATATCACCCTCTGCTACTCAA",
                "CTAGAGATATCACCCTCTGCTACTCAA"
            ],
            'person5':[
                "CTAGAGATATCACCCTCTGCTACTCAA",
                "CTAGAGATATCACCCTCTGCTACTCCG"
            ],
            'person6':[
                "CTAGAGATATCACCCTCTGCTACTCAA",
                "ACAGAGATATCACCCTCTGCTACTCAA"
            ],
            'person7':[
                "CTAGAGATATCACCCTCTGCTACTCAA",
                "CTAGAGATATCACCCTCTGCTACTCCG"
            ]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_in_tiles_2_and_3(self):
        response = self.client.get(reverse('api:pop_around_locus'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'target_base':91, 'number_around':15}) #AA | CGCACCGGAACTTGTGTTTGTGTG | TGTG | G
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':[
                "TACGCACCGGAACTTGTGTTTGTGTGTGTGG",
                "TCCGCACCGGAACTTGTGTTTGTGTGTGTGG"
            ],
            'person2':[
                "AACGCACCGGAACTTGTGTTTGTGTTTGTGG",
                "AACGCACCGGAACTTGTGTTTGTGTTTGTGG"
            ],
            'person3':[
                "TCCGCACCGGAACTTGTGTTTGTGTGTGTGG",
                "AACGCACCGGAACTTGTGTTTGTGTTTGTGG"
            ],
            'person4':[
                "AACGCACCGGAACTTGTGTTTGTGTGTGTGG",
                "AACGCACCGGAACTTGTGTTTGTGTGTGTGG"
            ],
            'person5':[
                "AACGCACCGGAACTTGTGTTTGTGTTTGTGG",
                "TCCGCACCGGAACTTGTGTTTGTGTGTGTGG"
            ],
            'person6':[
                "AACGCACCGGAACTTGTGTTTGTGTGTGTGG",
                "AACGCACCGGAACTTGTGTTTGTGTGTGTGG"
            ],
            'person7':[
                "AACGCACCGGAACTTGTGTTTGTGTTTGTGG",
                "TCCGCACCGGAACTTGTGTTTGTGTGTGTGA"
            ]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_over_paths_simplest(self):
        response = self.client.get(reverse('api:pop_around_locus'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'target_base':130, 'number_around':1}) #G || AG
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, "GAG")
    def test_query_in_tiles_0_1_and_2(self):
        #T | CG | TCAGAATGTTTGGAGGGCGGTACG | GC | TAGAGATATCACCCTCTGCTACTC | AA
        response = self.client.get(reverse('api:pop_around_locus'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'target_base':50, 'number_around':27})
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':[
                "GTCGTCAGAATGTTTGGAGGGCGGTACGCACCGGAACTTGTGTTTGTGTGTGTG",
                "GTTACAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCCG"
            ],
            'person2':[
                "TTTTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAA",
                "TTGTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAA"
            ],
            'person3':[
                "TTTTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCCG",
                "GGTTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAA"
            ],
            'person4':[
                "ACGTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAA",
                "TCGACAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAA"
            ],
            'person5':[
                "GTCACAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAA",
                "GTCGCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCCG"
            ],
            'person6':[
                "TTTTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAA",
                "GTCGTCAGAATGTTTGGAGGGCGGTACAGAGATATCACCCTCTGCTACTCAACG"
            ],
            'person7':[
                "GCGTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAA",
                "TTGTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCCG"
            ]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_in_tiles_1_2_and_3(self):
        #GC | TAGAGATATCACCCTCTGCTACTC | AA | CGCACCGGAACTTGTGTTTGTGTG | TGTG | G
        response = self.client.get(reverse('api:pop_around_locus'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'target_base':78, 'number_around':28})
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':[
                "GGTCGTCAGAATGTTTGGAGGGCGGTACGCACCGGAACTTGTGTTTGTGTGTGTGG",
                "CGGCTAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTGTGTGG"
            ],
            'person2':[
                "GCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGG",
                "GCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGG"
            ],
            'person3':[
                "CGGCTAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTGTGTGG",
                "GCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGG"
            ],
            'person4':[
                "GCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTGTGTGG",
                "GCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTGTGTGG"
            ],
            'person5':[
                "GCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGG",
                "CGGCTAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTGTGTGG"
            ],
            'person6':[
                "GCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTGTGTGG",
                "TACAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTGTGTGG"
            ],
            'person7':[
                "GCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGG",
                "CGGCTAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTGTGTGA"
            ]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_in_tiles_2_3_and_next_path(self):
        #A | CGCACCGGAACTTGTGTTTGTGTG | TGTG | GTCGCCCACTACGCACGTTATATG || AG
        response = self.client.get(reverse('api:pop_around_locus'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'target_base':104, 'number_around':27})
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':[
                "ACGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGAG",
                "CCGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGAG"
            ],
            'person2':[
                "ACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATGAG",
                "ACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATGAG"
            ],
            'person3':[
                "CCGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGAG",
                "ACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATGAG"
            ],
            'person4':[
                "ACGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGAG",
                "ACGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGAG"
            ],
            'person5':[
                "ACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATGAG",
                "CCGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGAG"
            ],
            'person6':[
                "ACGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGAG",
                "ACGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGAG"
            ],
            'person7':[
                "ACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATGAG",
                "CCGCACCGGAACTTGTGTTTGTGTGTGTGATCGCCCACTACGCACGTTATATGAG"
            ]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_in_tiles_0_1_2_and_3(self):
        #GT | CG | TCAGAATGTTTGGAGGGCGGTACG | GC | TAGAGATATCACCCTCTGCTACTC | AA | CGCACCGGAACTTGTGTTTGTGTG | TGTG | G
        response = self.client.get(reverse('api:pop_around_locus'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'target_base':64, 'number_around':42})
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':[
                "TAGTTTTGCCGCTCGGTCGTCAGAATGTTTGGAGGGCGGTACGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCA",
                "GGTTACAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTGTGTGGTC"
            ],
            'person2':[
                "TTTTTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGG",
                "GTTGTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGG"
            ],
            'person3':[
                "TTTTTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTGTGTGGTC",
                "CGGTTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGG"
            ],
            'person4':[
                "AACGTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTGTGTGG",
                "GTCGACAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTGTGTGG"
            ],
            'person5':[
                "GGTCACAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGG",
                "GGTCGCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTGTGTGGTC"
            ],
            'person6':[
                "GTTTTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTGTGTGG",
                "CTCGGTCGTCAGAATGTTTGGAGGGCGGTACAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTGTGTGG"
            ],
            'person7':[
                "GGCGTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGG",
                "GTTGTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTGTGTGATC"
            ]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_in_tiles_1_2_3_and_next_path(self):
        #C | TAGAGATATCACCCTCTGCTACTC | AA | CGCACCGGAACT T GTGTTTGTGTG | TGTG | GTCGCCCACTACGCACGTTATATG || AG
        response = self.client.get(reverse('api:pop_around_locus'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'target_base':91, 'number_around':40})
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':[
                "GGTCGTCAGAATGTTTGGAGGGCGGTACGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGAG",
                "GGCTAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGAG"
            ],
            'person2':[
                "CTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATGAG",
                "CTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATGAG"
            ],
            'person3':[
                "GGCTAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGAG",
                "CTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATGAG"
            ],
            'person4':[
                "CTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGAG",
                "CTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGAG"
            ],
            'person5':[
                "CTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATGAG",
                "GGCTAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGAG"
            ],
            'person6':[
                "CTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGAG",
                "ACAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGAG"
            ],
            'person7':[
                "CTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATGAG",
                "GGCTAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTGTGTGATCGCCCACTACGCACGTTATATGAG"
            ]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_in_tiles_0_1_2_3_and_next_path(self):
        #T | CG | TCAGAATGTTTGGAGGGCGGTACG | GC | TAGAGATATCACCCTCTGCTACTC | AA | CGCACCGGAACTTGTGTTTGTGTG | TGTG | GTCGCCCACTACGCACGTTATATG || A
        response = self.client.get(reverse('api:pop_around_locus'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'target_base':76, 'number_around':54})
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        checking = {
            'person1':[
                "ACGGCAGTAGTTTTGCCGCTCGGTCGTCAGAATGTTTGGAGGGCGGTACGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGAGA",
                "GGTTACAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGAG"
            ],
            'person2':[
                "TTTTTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATGA",
                "GTTGTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATGA"
            ],
            'person3':[
                "TTTTTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGAG",
                "CGGTTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATGA"
            ],
            'person4':[
                "AACGTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA",
                "GTCGACAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA"
            ],
            'person5':[
                "GGTCACAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATGA",
                "GGTCGCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGAG"
            ],
            'person6':[
                "GTTTTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA",
                "CTCGGTCGTCAGAATGTTTGGAGGGCGGTACAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA"
            ],
            'person7':[
                "GGCGTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATGA",
                "GTTGTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTGTGTGATCGCCCACTACGCACGTTATATGAG"
            ]
        }
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, checking[person_name][i])
    def test_query_entire_first_path_and_some_of_next_path(self):
        #   AGAGAGCTGGCAGA
        response = self.client.get(reverse('api:pop_around_locus'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_1, 'target_base':65, 'number_around':65})
        content = json.loads(response.content)
        checking = {
            'person1':[
                "ACGGCAGTAGTTTTGCCGCTCGGTCGTCAGAATGTTTGGAGGGCGGTACGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGAGAGAGCTGGCAGA",
                "ACGGCAGTAGTTTTGCCGCTCGGTTACAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGAGA"
            ],
            'person2':[
                "CGGCAGTAGTTTTGCCGCTCGGTTTTTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATGA",
                "ACGGCAGTAGTTTTGCCGCTCGGTTGTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATGA"
            ],
            'person3':[
                "CGGCAGTAGTTTTGCCGCTCGGTTTTTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGAGA",
                "ACGGCAGTAGTTTTGCCGCTCGGTTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATGA"
            ],
            'person4':[
                "GCAGTAGTTTTGCCGCTCGGTAAACGTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA",
                "ACGGCAGTAGTTTTGCCGCTCGGTCGACAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA"
            ],
            'person5':[
                "ACGGCAGTAGTTTTGCCGCTCGGTCACAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATGA",
                "ACGGCAGTAGTTTTGCCGCTCGGTCGCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGAGA"
            ],
            'person6':[
                "GCAGTAGTTTTGCCGCTCGGTCGTTTTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA",
                "ACGGCAGTAGTTTTGCCGCTCGGTCGTCAGAATGTTTGGAGGGCGGTACAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGA"
            ],
            'person7':[
                "ACGGCAGTAGTTTTGCCGCTCGGCGTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATGA",
                "ACGGCAGTAGTTTTGCCGCTCGGTTGTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTGTGTGATCGCCCACTACGCACGTTATATGAGA"
            ]
        }
        self.assertEqual(len(content), len(population))
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):

                self.assertEqual(phase, checking[person_name][i])
    def test_query_different_chromosome(self):
        response = self.client.get(reverse('api:pop_around_locus'), {'assembly':ASSEMBLY_19, 'chromosome':CHR_2, 'target_base':0})
        content = json.loads(response.content)
        self.assertEqual(len(content), len(population))
        for person in content:
            person_name = person['human_name']
            for i, phase in enumerate(person['sequence']):
                self.assertEqual(phase, 'C')

class TestDevelopmentSandbox(TestCase):
    def setUp(self):
        build_library.make_entire_library(multiple_assemblies=True)
        build_library.make_lantern_translators()



#################################### TEST path_statistics_views ###################################
##class TestViewPathStatistics(TestCase):
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
