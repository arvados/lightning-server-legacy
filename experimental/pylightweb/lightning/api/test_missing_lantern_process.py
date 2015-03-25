import json
import pprint

from django.test import TestCase, override_settings

from django.core.urlresolvers import reverse

import tile_library.test_scripts.complicated_library as build_library
from django.conf import settings


@override_settings(CHR_PATH_LENGTHS = (0,2,3))
class TestMissingLantern(TestCase):
    def setUp(self):
        build_library.make_entire_library(multiple_assemblies=True)
        build_library.make_lantern_translators()
    def test_between_loci_returns_500(self):
        response = self.client.get(reverse('api:pop_between_loci'), {'assembly':settings.ASSEMBLY_19, 'chromosome':settings.CHR_1, 'lower_base':24, 'upper_base':25})
        self.assertEqual(response.status_code, 500)
        print response.content
    def test_around_locus_returns_500(self):
        response = self.client.get(reverse('api:pop_around_locus'), {'assembly':settings.ASSEMBLY_19, 'chromosome':settings.CHR_1, 'target_base':24})
        self.assertEqual(response.status_code, 500)
        print response.content
