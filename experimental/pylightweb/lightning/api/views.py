import string
import requests
import traceback
import sys
import re
import json
import pprint

from django.http import Http404
from django.shortcuts import render
from django.core.urlresolvers import reverse
from django.conf import settings
from rest_framework import generics
from rest_framework import permissions
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.utils.serializer_helpers import ReturnDict

from api.serializers import TileVariantSerializer, RoughTileVariantSerializer, LocusSerializer, PopulationVariantSerializer, PopulationQuerySerializer, PopulationRangeQuerySerializer
from tile_library.models import Tile, TileVariant, TileLocusAnnotation, get_max_num_tiles_spanned_at_position
import tile_library.human_readable_functions as human_readable
import tile_library.query_functions as query_fns
import tile_library.lantern_query_functions as lantern_query_fns
import tile_library.basic_functions as basic_fns
from errors import MissingStatisticsError, LocusOutOfRangeException, UnexpectedLanternBehaviorError, CGFTranslatorError, EmptyPathError, EndOfChromosomeError

def documentation(request):
    """
    For each GET API call, the template needs:
	   id; title; description; GET_url; required_GET_parameters; optional_GET_parameters; request_body; RESPONSE_properties; try_it_url

	for each required_GET_parameter, optional_GET_parameter, and RESPONSE_property, the template needs:
		name; value; description
    """
    response = {
        'api_calls': [
            {
                'id': 'around-locus',
                'title': 'Find sequence around a specific locus',
                'description':'Lists the bases around the specified locus for the entire population loaded into Lightning. Currently assumes the population has two phases.',
                'GET_url':reverse('api:pop_around_locus'),
                'required_GET_parameters': [
                    {
                        'name':'assembly',
                        'value':'integer',
                        'description':'The integer representation of the assembly to use.'
                    },
                    {
                        'name':'chromosome',
                        'value':'integer',
                        'description':'The integer representation of the chromosome to query.'
                    },
                    {
                        'name':'target_base',
                        'value':'long',
                        'description':'The locus to query around. (0-based).'
                    }
                ],
                'optional_GET_parameters':[
                    {
                        'name':'number_around',
                        'value':'long',
                        'description':'The number of bases to retrieve around the locus. Defaults to 0.'
                    },
                    {
                        'name':'indexing',
                        'value':'integer',
                        'description':'Specifies whether to use 0-indexing or 1-indexing. Defaults to 0.'
                    }
                ],
                'request_body':'Do not supply a request body with this method.',
                'RESPONSE_properties':[
                    {
                        'name':'human_name',
                        'value':'string',
                        'description':'A unique identifier for the human who has this sequence. Contains the Personal Genome Project person ID.'
                    },
                    {
                        'name':'phase_A_sequence',
                        'value':'string',
                        'description':'<code>number_around</code> bases before locus <code>target_base</code>, the base at locus <code>target_base</code>,\
                            and <code>number_around</code> bases after locus <code>target_base</code> called as phase A by the Complete genomics variant caller.'
                    },
                    {
                        'name':'phase_B_sequence',
                        'value':'string',
                        'description':'<code>number_around</code> bases before locus <code>target_base</code>, the base at locus <code>target_base</code>,\
                            and <code>number_around</code> bases after locus <code>target_base</code> called as phase B by the Complete genomics variant caller.'
                    },
                    {
                        'name':'phase_groups_known',
                        'value':'boolean',
                        'description':'True if the sequence is well phased. False otherwise.'
                    }
                ],
                'try_it_url':reverse('population_sequence_query:around_locus_form'),
                'try_it_examples':[]
            },
            {
                'id': 'between-loci',
                'title': 'Find sequence between two loci',
                'description':'Lists the bases between two loci for the entire population loaded into Lightning. Currently assumes the population has two phases.',
                'GET_url':reverse('api:pop_between_loci'),
                'required_GET_parameters': [
                    {
                        'name':'assembly',
                        'value':'integer',
                        'description':'The integer representation of the assembly to use.'
                    },
                    {
                        'name':'chromosome',
                        'value':'integer',
                        'description':'The integer representation of the chromosome to query.'
                    },
                    {
                        'name':'lower_base',
                        'value':'long',
                        'description':'The locus to start querying at. (0-based).'
                    },
                    {
                        'name':'upper_base',
                        'value':'long',
                        'description':'The locus to end querying at. (0-based and exclusive).'
                    }
                ],
                'optional_GET_parameters':[
                    {
                        'name':'indexing',
                        'value':'integer',
                        'description':'Specifies whether to use 0-indexing or 1-indexing. Defaults to 0.'
                    }
                ],
                'request_body':'Do not supply a request body with this method.',
                'RESPONSE_properties':[
                    {
                        'name':'human_name',
                        'value':'string',
                        'description':'A unique identifier for the human who has this sequence. Contains the Personal Genome Project person ID.'
                    },
                    {
                        'name':'phase_A_sequence',
                        'value':'string',
                        'description':'Sequence called as phase A by the Complete genomics variant caller between <code>lower_base</code> and <code>upper_base</code>.'
                    },
                    {
                        'name':'phase_B_sequence',
                        'value':'string',
                        'description':'Sequence called as phase B by the Complete genomics variant caller between <code>lower_base</code> and <code>upper_base</code>.'
                    },
                    {
                        'name':'phase_groups_known',
                        'value':'boolean',
                        'description':'True if the sequence is well phased. False otherwise.'
                    }
                ],
                'try_it_url':reverse('population_sequence_query:between_loci_form'),
                'try_it_examples':[]
            }
        ]
    }
    return render(request, 'api/api_docs.html', response)
class TileVariantQuery(APIView):
    """
    Retrieve a tile variant (by its hex string) or retrieve all tile variants at a tile position (by a tile position hex string).
    """
    def get_tile_variant_info(self, tile_variant):
        tile_variant_info = {
            'tile_variant_hex_string': tile_variant.getString(),
            'tile_variant_cgf_string': tile_variant.conversion_to_cgf,
            'tile_variant_int': tile_variant.tile_variant_name,
            'num_positions_spanned': tile_variant.num_positions_spanned,
            'length': tile_variant.length,
            'genome_variants': [],
            'md5sum': tile_variant.md5sum,
            'sequence': tile_variant.sequence
        }
        translations = tile_variant.translation_to_genome_variant.all()
        for translation in translations:
            genome_variant = translation.genome_variant
            genome_variant_info = {
                'tile_variant_start_locus': translation.start,
                'tile_variant_end_locus': translation.end,
                'ref_start_locus': genome_variant.start_increment,
                'ref_end_locus': genome_variant.end_increment,
                'reference_bases': genome_variant.reference_bases,
                'alternate_bases': genome_variant.alternate_bases
            }
            tile_variant_info['genome_variants'].append(genome_variant_info)
        tile_variant_info['genome_variants'] = sorted(tile_variant_info['genome_variants'], key=lambda d: d['tile_variant_start_locus'])
        return tile_variant_info
    def get(self, request, hex_string, format=None):
        matching = re.match('^[0-9a-f]{3}\.[0-9a-f]{2}\.[0-9a-f]{4}(\.[0-9a-f]{3})?$', hex_string)
        assert matching != None, "%s is not recognized as a valid tile position or tile variant hex representation" % hex_string
        if len(hex_string.split('.')) == 4:
            #Tile Variant
            tile_variant_id = int(hex_string.replace('.', ''), 16)
            try:
                tile_variant = TileVariant.objects.get(tile_variant_name=tile_variant_id)
            except TileVariant.DoesNotExist:
                raise Http404
            tile_variant_info = self.get_tile_variant_info(tile_variant)
            serializer = TileVariantSerializer(tile_variant_info)
        else:
            tile_id = int(hex_string.replace('.', ''), 16)
            try:
                tile = Tile.objects.get(tilename=tile_id)
            except Tile.DoesNotExist:
                raise Http404
            tile_variant_list = []
            for tile_variant in tile.tile_variants.all():
                tile_variant_list.append(self.get_tile_variant_info(tile_variant))
            serializer = TileVariantSerializer(tile_variant_list, many=True)
        return Response(serializer.data)
class TileVariantDetail(generics.RetrieveAPIView):
    queryset = TileVariant.objects.all()
    serializer_class = RoughTileVariantSerializer
class TileLocusAnnotationList(APIView):
    """
    Retrieve the tile locus annotations for the tile position given by tile_hex_string.
    """
    def get(self, request, tile_hex_string, format=None):
        matching = re.match('^[0-9a-f]{3}\.[0-9a-f]{2}\.[0-9a-f]{4}$', tile_hex_string)
        assert matching != None, "%s is not recognized as a valid tile position" % tile_hex_string
        tile_id = int(tile_hex_string.replace('.', ''), 16)
        try:
            tile = Tile.objects.get(tilename=tile_id)
            locuses = TileLocusAnnotation.objects.get(tile_id=tile_id)
            serializer = LocusSerializer(locuses)
            return Response(serializer.data)
        except Tile.DoesNotExist:
            raise Http404
        except TileLocusAnnotation.DoesNotExist:
            raise Http404

class PopulationVariantQueryBetweenLoci(APIView):
    """
    Retrieve population sequences between position "lower_base" and "upper_base" (upper base is exclusive).
    If the positions are 1-indexed, set "indexing" to 1.
    Requires lantern version 0.0.3
    """
    def check_locus(self, assembly_int, chromosome_int, low_int, high_int, alt_chromosome_name):
        response = {}
        assembly_name = human_readable.get_readable_assembly_name(assembly_int)
        chromosome_name = human_readable.get_readable_chr_name(chromosome_int, alt_chromosome_name)
        base_query = TileLocusAnnotation.objects.filter(assembly_int=assembly_int)
        if base_query.count() == 0:
            response['assembly'] = ["Assembly %s (%i) not loaded into tile library" % (assembly_name, assembly_int)]
        else:
            base_query = base_query.filter(chromosome_int=chromosome_int)
            if base_query.count() == 0:
                response['chromosome'] = ["Chromosome %s (%i) not loaded into tile library" % (chromosome_name, chromosome_int)]
            else:
                smallest_int = base_query.order_by('start_int').first().start_int
                largest_int = base_query.order_by('start_int').reverse().first().end_int - 1
                if low_int < smallest_int:
                    response['lower_base'] = ["%i is smaller than the smallest locus (%i) in the tile library at chromosome %s, assembly %s" % (low_int, smallest_int, chromosome_name, assembly_name)]
                if high_int > largest_int:
                    response['upper_base'] = ["%i is larger than the largest locus (%i) in the tile library at chromosome %s, assembly %s" % (high_int, largest_int, chromosome_name, assembly_name)]
        if len(response) > 0:
            raise LocusOutOfRangeException(response)
    def get_variants_and_bases(self, assembly, chromosome, low_int, high_int):
        """
        Expects low_int and high_int to be 0-indexed. high_int is expected to be exclusive
        Returns list of dictionaries, keyed by cgf_string:
            cgf_string : bases of interest. Includes tags!
        Each entry in the list corresponds to a position
        """

        locuses = TileLocusAnnotation.objects.filter(assembly_int=assembly).filter(chromosome_int=chromosome).filter(
            start_int__lt=high_int).filter(end_int__gt=low_int).order_by('start_int')
        num_locuses = locuses.count()

        if num_locuses == 0:
            raise Exception("Should have caught this case in 'check_locus'") # Never raised in test cases, which is expected
        #Get framing tile position ints
        first_tile_position_int = int(locuses.first().tile_position_id)
        last_tile_position_int = max(int(locuses.last().tile_position_id), first_tile_position_int)

        #Get maximum number of spanning tiles
        max_num_spanning_tiles = get_max_num_tiles_spanned_at_position(first_tile_position_int)

        #Create cgf_translator (Dictionary keyed by cgf names where the values are the necessary bases)
        simple_cgf_translator = query_fns.get_simple_cgf_translator(locuses, low_int, high_int, assembly)

        #Add spanning tiles to cgf_translator
        spanning_tile_variants = query_fns.get_tile_variants_spanning_into_position(first_tile_position_int)
        for var in spanning_tile_variants:
            cgf_str, bases = query_fns.get_tile_variant_cgf_str_and_bases_between_loci_unknown_locus(var, low_int, high_int, assembly)
            if cgf_str != '':
                if cgf_str in simple_cgf_translator: # Never raised in test cases, which is expected. This checks for odd behavior before continuing
                    raise CGFTranslatorError("Repeat spanning cgf_string: %s. %s" % (non_spanning_cgf_string, cgf_translator))
                simple_cgf_translator[cgf_str] = bases
        return first_tile_position_int, last_tile_position_int, max_num_spanning_tiles, simple_cgf_translator
    def get_bases_for_human(self, human_name, positions_queried, first_tile_position_int, last_tile_position_int, cgf_translator):
        sequence = ""
        for human_tile_index, cgf_string in enumerate(positions_queried):
            num_positions_spanned = basic_fns.get_number_of_tiles_spanned_from_cgf_string(cgf_string) - 1
            non_spanning_cgf_string = cgf_string.split('+')[0]
            tile_position_int = basic_fns.get_position_from_cgf_string(cgf_string)
            tile_position_str = basic_fns.get_position_string_from_position_int(tile_position_int)
            if last_tile_position_int < tile_position_int:
                raise UnexpectedLanternBehaviorError( #Not raised in test cases, which is expected since this is lantern-specific
                    "Lantern query went over expected max position (Lantern response: %s, Max position: %s)" % (tile_position_str,
                        basic_fns.get_position_string_from_position_int(last_tile_position_int))
                )
            if first_tile_position_int <= tile_position_int+num_positions_spanned and tile_position_int <= last_tile_position_int:
                if non_spanning_cgf_string not in cgf_translator: #Not raised in test cases, which is expected. This checks for odd behavior before continuing
                    raise CGFTranslatorError("Translator doesn't include %s. %s" % (non_spanning_cgf_string, cgf_translator))
                num_to_skip = 0
                if len(sequence) > 0:
                    version, path, step = basic_fns.get_position_ints_from_position_int(tile_position_int)
                    assert human_tile_index > 0, "How did we get a sequence of non-zero length without going down the query?"
                    prev_tile_position_int = basic_fns.get_position_from_cgf_string(positions_queried[human_tile_index-1])
                    prev_version, prev_path, prev_step = basic_fns.get_position_ints_from_position_int(prev_tile_position_int)
                    if prev_version == version and prev_path == path:
                        #We are in the same path and version, so check TAGs
                        curr_ending_tag = sequence[-settings.TAG_LENGTH:]
                        new_starting_tag = cgf_translator[non_spanning_cgf_string][:settings.TAG_LENGTH]
                        if len(curr_ending_tag) >= len(new_starting_tag):
                            if not curr_ending_tag.endswith(new_starting_tag):
                                raise UnexpectedLanternBehaviorError( #Not raised in test cases, which is expected since this is lantern-specific
                                    "Tags do not match for human %s at position %s. Sequence length: %i, Ending Tag: %s. Starting Tag: %s. Positions Queried: %s" % (human_name,
                                        tile_position_str, len(sequence), curr_ending_tag, new_starting_tag, str(positions_queried))
                                )
                            num_to_skip = settings.TAG_LENGTH
                        else:
                            if not new_starting_tag.startswith(curr_ending_tag):
                                raise UnexpectedLanternBehaviorError( #Not raised in test cases, which is expected since this is lantern-specific
                                    "Tags do not match for human %s at position %s. Sequence length: %i, Ending Tag: %s. Starting Tag: %s. Positions Queried: %s" % (human_name,
                                        tile_position_str, len(sequence), curr_ending_tag, new_starting_tag, str(positions_queried))
                                )
                            num_to_skip = len(curr_ending_tag)
                sequence += cgf_translator[non_spanning_cgf_string][num_to_skip:]
        return sequence
    def get_population_sequences(self, first_tile_position_int, last_tile_position_int, max_num_spanning_variants, cgf_translator):
        humans = lantern_query_fns.get_population_sequences_over_position_range(first_tile_position_int-max_num_spanning_variants, last_tile_position_int)
        human_sequence_dict = {}
        for human in humans:
            short_name = human.strip('" ').split('/')[-1]
            human_sequence_dict[human] = []
            for positions_in_one_phase in humans[human]:
                human_sequence_dict[human].append(self.get_bases_for_human(short_name, positions_in_one_phase, first_tile_position_int, last_tile_position_int, cgf_translator))
        humans_with_sequences = []
        for human in human_sequence_dict:
            humans_with_sequences.append(
                {'callset':human.strip('" ').split('/')[-1],
                 'sequence':human_sequence_dict[human],
                 'phased':False}
            )
        return humans_with_sequences
    def get(self, request, format=None):
        query_serializer = PopulationRangeQuerySerializer(data=request.query_params)
        if query_serializer.is_valid():
            cgf_translator = None
            try:
                lower_base = int(query_serializer.data['lower_base'])
                upper_base = int(query_serializer.data['upper_base'])
                if query_serializer.data['indexing'] == 1:
                    lower_base -= 1
                    upper_base -= 1
                #Return useful info if cannot complete query
                if upper_base <= lower_base:
                    return Response(
                        {'lower_base-upper_base': ["lower_base (%i) must be lower than upper_base (%i)" % (lower_base, upper_base)]},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                self.check_locus(
                    int(query_serializer.data['assembly']),
                    int(query_serializer.data['chromosome']),
                    lower_base,
                    upper_base,
                    ''
                )
                first_tile_position_int, last_tile_position_int, max_num_spanning_tiles, cgf_translator = self.get_variants_and_bases(
                    int(query_serializer.data['assembly']),
                    int(query_serializer.data['chromosome']),
                    lower_base,
                    upper_base
                )
                humans_and_sequences = self.get_population_sequences(first_tile_position_int, last_tile_position_int, max_num_spanning_tiles, cgf_translator)
            except LocusOutOfRangeException as e:
                return Response(e.value, status=status.HTTP_404_NOT_FOUND)
            except (UnexpectedLanternBehaviorError, CGFTranslatorError) as e: # Not raised in test cases, which is expected since this is either Lantern-specific or a test case I haven't considered yet
                return Response(e.value, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            except (requests.ConnectionError, requests.Timeout) as e:
                return Response("Error querying Lantern: %s" % (str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            return_serializer = PopulationVariantSerializer(data=humans_and_sequences, many=True)
            if return_serializer.is_valid():
                return Response(return_serializer.data)
            return Response(return_serializer.errors, status=status.HTTP_500_INTERNAL_SERVER_ERROR) #Would only be returned if return serializer is off, not raised in test cases, which is expected
        return Response(query_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PopulationVariantQueryAroundLocus(APIView):
    """
    Retrieve population sequences at position "target_base" (with "number_around" bases around "target_base" also retrieved).
    If the positions are 1-indexed, set "indexing" to 1. Defaults to number_around=0.
    Requires lantern version 0.0.3
    """
    def check_locus(self, assembly_int, chromosome_int, target_int, number_bases_around, alt_chromosome_name):
        response = {}
        assembly_name = human_readable.get_readable_assembly_name(assembly_int)
        chromosome_name = human_readable.get_readable_chr_name(chromosome_int, alt_chromosome_name)
        base_query = TileLocusAnnotation.objects.filter(assembly_int=assembly_int)
        if base_query.count() == 0:
            response['assembly'] = ["Assembly %s (%i) not loaded into tile library" % (assembly_name, assembly_int)]
        else:
            base_query = base_query.filter(chromosome_int=chromosome_int)
            if base_query.count() == 0:
                response['chromosome'] = ["Chromosome %s (%i) not loaded into tile library" % (chromosome_name, chromosome_int)]
            else:
                smallest_int = base_query.order_by('start_int').first().start_int
                largest_int = base_query.order_by('start_int').reverse().first().end_int - 1
                if target_int-number_bases_around < smallest_int:
                    response['target_base-number_around'] = ["%i-%i is smaller than the smallest locus (%i) in the tile library at chromosome %s, assembly %s" % (target_int, number_bases_around, smallest_int, chromosome_name, assembly_name)]
                if target_int+number_bases_around > largest_int:
                    response['target_base+number_around'] = ["%i+%i is larger than the largest locus (%i) in the tile library at chromosome %s, assembly %s" % (target_int, number_bases_around, largest_int, chromosome_name, assembly_name)]
        if len(response) > 0:
            raise LocusOutOfRangeException(response)
    def get_variants_and_bases(self, assembly, chromosome, target_base_int, number_bases_around):
        """
        Expects target_base_int to be 0-indexed
        Returns 2 dictionaries, keyed by cgf_string:
            cgf_string : bases of interest. Includes tags!
        center_cgf_translator is used for locus of interest
        cgf_translator is used for any other lantern string
        """
        ######### Get center position #########
        center_locus = TileLocusAnnotation.objects.filter(assembly_int=assembly).filter(chromosome_int=chromosome).filter(
            start_int__lte=target_base_int).filter(end_int__gt=target_base_int)

        center_locus = center_locus.order_by('start_int').first()
        center_tile_position_int = int(center_locus.tile_position_id)

        ######### Get locuses #########
        rough_low_int = target_base_int - number_bases_around
        rough_high_int = target_base_int + number_bases_around + 1 #non_inclusive!
        locuses = TileLocusAnnotation.objects.filter(assembly_int=assembly).filter(chromosome_int=chromosome).filter(
            start_int__lt=rough_high_int).filter(end_int__gt=rough_low_int).order_by('start_int')

        #Get framing tile position ints
        first_tile_position_int =  int(locuses.first().tile_position_id)
        last_tile_position_int = max(int(locuses.last().tile_position_id), first_tile_position_int)

        #Get maximum number of spanning tiles
        max_num_spanning_tiles = get_max_num_tiles_spanned_at_position(first_tile_position_int)

        #Create cgf_translator for each position
        if locuses.count() == last_tile_position_int - first_tile_position_int + 1:
            center_index = center_tile_position_int-first_tile_position_int
        else:
            center_index = None
            for i, locus in enumerate(locuses):
                if locus.tile_position_id == center_tile_position_int:
                    if center_index != None:
                        raise CGFTranslatorError("Multiple center locuses when preparing to create cgf translator") # Not raised in test cases, which is expected
                    center_index = i
            if center_index == None:
                raise CGFTranslatorError("No center index found when creating cgf_translator") # Not raised in test cases, which is expected
        center_cgf_translator, cgf_translator = query_fns.get_cgf_translator_and_center_cgf_translator(locuses, target_base_int, center_index, max_num_spanning_tiles, assembly)
        return first_tile_position_int, last_tile_position_int, max_num_spanning_tiles, center_tile_position_int, center_index, cgf_translator, center_cgf_translator
    def helper_get_bases_forward(self, curr_sequence, cgf_string, translator, num_bases_around, string_to_print, cgf_translator_around, positions_queried, length_of_middle):
        non_spanning_cgf_string = cgf_string.split('+')[0]
        step_int = int(non_spanning_cgf_string.split('.')[2], 16)
        if non_spanning_cgf_string not in translator:
            raise CGFTranslatorError(string_to_print + "(Failed). Expects %s to be in translator (%s)" % (non_spanning_cgf_string, # Not raised in test cases, which is expected
                cgf_translator_around))
        if len(curr_sequence) > length_of_middle and step_int > 0:
            curr_ending_tag = curr_sequence[-settings.TAG_LENGTH:]
            new_starting_tag = translator[non_spanning_cgf_string][:settings.TAG_LENGTH]
            if len(curr_sequence) < settings.TAG_LENGTH:
                if not new_starting_tag.endswith(curr_ending_tag): #Not raised in test cases, which is expected since this is Lantern-specific
                    raise UnexpectedLanternBehaviorError("Tags do not match at %s. Ending Tag: %s, Starting Tag: %s. curr_seq is smaller than TAG_LENGTH. Positions_queried: %s" % (cgf_string,
                        curr_ending_tag, new_starting_tag, str(positions_queried)))
            elif len(curr_ending_tag) >= len(new_starting_tag):
                if not curr_ending_tag.endswith(new_starting_tag): # Not raised in test cases, which is expected since this is Lantern-specific
                    raise UnexpectedLanternBehaviorError("Tags do not match at %s. Ending Tag: %s, Starting Tag: %s. Ending tag is larger or equal to the starting tag. Positions queried: %s" % (cgf_string,
                        curr_ending_tag, new_starting_tag, str(positions_queried)))
            else: #Not raised in test cases. Unsure if this is to be expected or not, but I was being careful
                raise UnexpectedLanternBehaviorError("Unexpected TAG case. Ending tag: %s, Starting tag: %s, current sequence length: %i." % (curr_ending_tag, new_starting_tag, len(curr_sequence)))
            new_sequence = translator[non_spanning_cgf_string][settings.TAG_LENGTH:]
        else:
            new_sequence = translator[non_spanning_cgf_string]
        if len(curr_sequence) + len(new_sequence) >= num_bases_around + length_of_middle:
            amt_to_index_into = num_bases_around + length_of_middle - len(curr_sequence)
            return new_sequence[:amt_to_index_into], True
        else:
            return new_sequence, False
    def helper_get_bases_reverse(self, curr_sequence, cgf_string, translator, num_bases_around, string_to_print, cgf_translator_around, positions_queried, length_of_middle):
        non_spanning_cgf_string = cgf_string.split('+')[0]
        path, path_version, step, ignore = non_spanning_cgf_string.split('.')
        edge_path_version, edge_path_int, edge_path_step = basic_fns.get_position_ints_from_position_int(query_fns.get_highest_position_int_in_path(int(path,16)))
        if non_spanning_cgf_string not in translator: # Not raised in test cases, which is expected
            raise CGFTranslatorError(string_to_print + "(Failed). Expects %s to be in translator (%s)" % (non_spanning_cgf_string, cgf_translator_around))
        if len(curr_sequence) > length_of_middle and int(step,16) < edge_path_step: # Tags will only overlap if we are on the same path
            curr_starting_tag = curr_sequence[:settings.TAG_LENGTH]
            new_ending_tag = translator[non_spanning_cgf_string][-settings.TAG_LENGTH:]
            if len(curr_starting_tag) >= len(new_ending_tag):
                if not curr_starting_tag.startswith(new_ending_tag): #Not raised in test cases, which is expected since this is Lantern-specific
                    raise UnexpectedLanternBehaviorError("Tags do not match at %s. Prev Starting Tag: %s, New Ending Tag: %s. Positions queried: %s" % (cgf_string,
                        curr_starting_tag, new_ending_tag, str(positions_queried)))
            else: #Not raised in test cases, which is expected since this is not expected to happen
                raise CGFTranslatorError("Short tag fell on reverse helper. At lantern position %s. Positions queried: %s" % (cgf_string, str(positions_queried)))
            new_sequence = translator[non_spanning_cgf_string][:-settings.TAG_LENGTH]
        else:
            new_sequence = translator[non_spanning_cgf_string]
        if len(curr_sequence) + len(new_sequence) >= num_bases_around + length_of_middle:
            amt_to_index_into = len(new_sequence) + len(curr_sequence) - (num_bases_around + length_of_middle)
            return new_sequence[amt_to_index_into:], True
        else:
            return new_sequence, False
    def get_one_more_tile_forwards(self, human_name, phase, prev_cgf_string):
        prev_path = int(prev_cgf_string.split('.')[0], 16)
        prev_position = basic_fns.get_position_from_cgf_string(prev_cgf_string)
        curr_position = prev_position + basic_fns.get_number_of_tiles_spanned_from_cgf_string(prev_cgf_string)
        #Check to make sure we didn't go over the maximum position in the path
        check_position = query_fns.get_highest_position_int_in_path(prev_path)
        if curr_position > check_position:
            # Need to go to next path
            if prev_path > 0 and prev_path+1 in settings.CHR_PATH_LENGTHS:
                raise EndOfChromosomeError("")
            try:
                next_path_min_position, foo = basic_fns.get_min_position_and_tile_variant_from_path_int(prev_path+1)
                curr_position = curr_position - (check_position+1) + next_path_min_position
                t = Tile.objects.get(tile_position_int=curr_position)
            except Tile.DoesNotExist:
                next_position_name = basic_fns.get_position_string_from_position_int(curr_position)
                raise EmptyPathError("Unable to find tile %s. Path assumed to be empty" % (next_position_name))
        #Query lantern to get call at the next position
        cgf_string = lantern_query_fns.get_population_sequences_over_position_range(curr_position, curr_position, sub_population_list=[human_name])[human_name][phase][0]
        #Get bases (tile_variant from cgf_string)
        bases = query_fns.get_bases_from_lantern_name(cgf_string)
        return cgf_string, bases
    def get_one_more_tile_backwards(self, human_name, phase, prev_cgf_string):
        def get_next_position(prev_position):
            prev_path_version, prev_path, prev_step = basic_fns.get_position_ints_from_position_int(prev_position)
            if prev_step == 0:
                if prev_path in settings.CHR_PATH_LENGTHS:
                    raise EndOfChromosomeError("")
                next_position = query_fns.get_highest_position_int_in_path(prev_path-1) #Checks to see that the position exists in the Tile Library and throws an EmptyPathError if not
            else:
                next_position = prev_position - 1
            return next_position

        prev_position = basic_fns.get_position_from_cgf_string(prev_cgf_string)
        curr_position = get_next_position(prev_position)
        #Query lantern to get call at the next position
        curr_call = []
        while len(curr_call) == 0:
            curr_call = lantern_query_fns.get_population_sequences_over_position_range(curr_position, curr_position, sub_population_list=[human_name])[human_name][phase]
            curr_position = get_next_position(curr_position)

        cgf_string = curr_call[0]
        #Get bases (tile_variant from cgf_string)
        bases = query_fns.get_bases_from_lantern_name(cgf_string)
        return cgf_string, bases
    def get_bases_for_human(self, human, sequence_of_tile_variants, cgf_translator, center_cgf_translator, num_bases_around, middle_position, cgf_translator_middle_index, phase):
        middle_position_str = basic_fns.get_position_string_from_position_int(middle_position)
        middle_index = None
        for i, cgf_string in enumerate(sequence_of_tile_variants):
            curr_position = basic_fns.get_position_from_cgf_string(cgf_string)
            if curr_position <= middle_position:
                middle_index = i
        assert middle_index != None, "Human %s did not have a position less than the middle_position %s. Positions: %s, center_cgf_translator keys: (%s), not center_cgf_translator keys: (%s)" % (human,
            middle_position_str, str(sequence_of_tile_variants), center_cgf_translator, cgf_translator)
        center_cgf_string = sequence_of_tile_variants[middle_index].split('+')[0]
        assert center_cgf_string in center_cgf_translator[1], \
            "CGF string %s at middle index %i (for middle position %s) is not in center_cgf_translator" % (center_cgf_string, middle_index, middle_position_str)
        sequence = center_cgf_translator[1][center_cgf_string]
        forward_sequence = sequence
        reverse_sequence = sequence
        middle_sequence = sequence
        #Go forward
        #curr_cgf_translator_index = cgf_translator_middle_index
        for i, cgf_string in enumerate(sequence_of_tile_variants[middle_index:]):
            if i == 0:
                string_to_print = "cgf_translator length: %i. Query: center_cgf_translator, forward strand, position %s " % (len(cgf_translator), cgf_string)
                new_sequence, finished = self.helper_get_bases_forward(forward_sequence, cgf_string, center_cgf_translator[2], num_bases_around, string_to_print,
                    center_cgf_translator, sequence_of_tile_variants, len(middle_sequence))
                curr_position = basic_fns.get_position_from_cgf_string(cgf_string)
                if curr_position != middle_position:
                    curr_cgf_translator_index = cgf_translator_middle_index + curr_position-middle_position
                else:
                    curr_cgf_translator_index = cgf_translator_middle_index
            else:
                string_to_print += "Query: position %s " % (cgf_string)
                new_sequence, finished = self.helper_get_bases_forward(forward_sequence, cgf_string, cgf_translator,
                    num_bases_around, string_to_print, cgf_translator, sequence_of_tile_variants, len(middle_sequence))
            forward_sequence += new_sequence
            prev_cgf_translator_index = curr_cgf_translator_index
            curr_cgf_translator_index += basic_fns.get_number_of_tiles_spanned_from_cgf_string(cgf_string)
            string_to_print += "(Success). Prev_cgf_translator_index: %i, new one: %i. " % (prev_cgf_translator_index, curr_cgf_translator_index)
            if finished:
                break
            if curr_cgf_translator_index >= len(cgf_translator):
                break
        while not finished:
            try:
                cgf_string, bases = self.get_one_more_tile_forwards(human, phase, cgf_string)
                string_to_print += "(Success). Query: go forward one, position %s" % (cgf_string)
                new_sequence, finished = self.helper_get_bases_forward(forward_sequence, cgf_string, {cgf_string.split('+')[0]:bases}, num_bases_around, string_to_print,
                    [], sequence_of_tile_variants + [cgf_string], len(middle_sequence))
                forward_sequence += new_sequence
            except EndOfChromosomeError:
                finished = True

        ##################################################
        #go backward
        backward_tile_variant_seq = sequence_of_tile_variants[:middle_index+1]
        backward_tile_variant_seq.reverse()
        #curr_cgf_translator_index = cgf_translator_middle_index
        for i, cgf_string in enumerate(backward_tile_variant_seq):
            if i == 0:
                string_to_print = "cgf_translator length: %i. Query: center_cgf_translator, reverse strand, position %s " % (len(cgf_translator), cgf_string)
                new_sequence, finished = self.helper_get_bases_reverse(reverse_sequence, cgf_string, center_cgf_translator[0], num_bases_around, string_to_print,
                    center_cgf_translator, sequence_of_tile_variants, len(middle_sequence))
                curr_position = basic_fns.get_position_from_cgf_string(cgf_string)
                if curr_position != middle_position:
                    curr_cgf_translator_index = cgf_translator_middle_index + curr_position-middle_position
                else:
                    curr_cgf_translator_index = cgf_translator_middle_index
            else:
                string_to_print += "Query: position %s " % (cgf_string)
                new_sequence, finished = self.helper_get_bases_reverse(reverse_sequence, cgf_string, cgf_translator,
                    num_bases_around, string_to_print, cgf_translator, sequence_of_tile_variants, len(middle_sequence))
            reverse_sequence = new_sequence + reverse_sequence
            if finished:
                break
            #Break before we try to get the next one, since at the end of the loop we will hit an index error
            try:
                next_cgf_string = backward_tile_variant_seq[i+1]
                prev_cgf_translator_index = curr_cgf_translator_index
                curr_cgf_translator_index -= basic_fns.get_number_of_tiles_spanned_from_cgf_string(next_cgf_string)
                if curr_cgf_translator_index < 0:
                    break
                string_to_print += "(Success). Prev_cgf_translator_index: %i, new one: %i. " % (prev_cgf_translator_index, curr_cgf_translator_index)
            except IndexError:
                break
        while not finished:
            try:
                cgf_string, bases = self.get_one_more_tile_backwards(human, phase, cgf_string)
                string_to_print += "(Success). Query: go backward one, position %s" % (cgf_string)
                new_sequence, finished = self.helper_get_bases_reverse(reverse_sequence, cgf_string, {cgf_string.split('+')[0]:bases}, num_bases_around, string_to_print,
                    [], [cgf_string]+sequence_of_tile_variants, len(middle_sequence))
                reverse_sequence = new_sequence + reverse_sequence
            except EndOfChromosomeError:
                finished = True
        return reverse_sequence + forward_sequence[len(middle_sequence):]
    def get_population_sequences(self, first_tile_position_int, last_tile_position_int, max_num_spanning_variants, center_position_int, middle_index, cgf_translator, center_cgf_translator, num_bases_around):
        humans = lantern_query_fns.get_population_sequences_over_position_range(first_tile_position_int-max_num_spanning_variants, last_tile_position_int)
        human_sequence_dict = {}
        for human in humans:
            short_name = human.strip('" ').split('/')[-1]
            human_sequence_dict[human] = []
            for i, positions_in_one_phase in enumerate(humans[human]):
                if positions_in_one_phase == []: # Not raised in test cases, which is expected since this checks Lantern's behavior
                    raise UnexpectedLanternBehaviorError("Human sequence is empty for person %s. First int: %i, Last int: %i, number_spanning: %i" % (short_name, first_tile_position_int, last_tile_position_int, max_num_spanning_variants))
                human_sequence_dict[human].append(
                    self.get_bases_for_human(human, positions_in_one_phase, cgf_translator, center_cgf_translator, num_bases_around, center_position_int, middle_index, i)
                )
        humans_with_sequences = []
        for human in human_sequence_dict:
            humans_with_sequences.append(
                {'callset':human.strip('" ').split('/')[-1],
                 'sequence':human_sequence_dict[human],
                 'phased':False}
                 )
        return humans_with_sequences
    def get(self, request, format=None):
        query_serializer = PopulationQuerySerializer(data=request.query_params)
        if query_serializer.is_valid():
            try:
                target_base = int(query_serializer.data['target_base'])
                if query_serializer.data['indexing'] == 1:
                    target_base -= 1
                self.check_locus(
                    int(query_serializer.data['assembly']),
                    int(query_serializer.data['chromosome']),
                    target_base,
                    int(query_serializer.data['number_around']),
                    ''
                )
                first_tile_position_int, last_tile_position_int, max_num_spanning_tiles, center_position_int, center_index, cgf_translator, center_cgf_translator = self.get_variants_and_bases(
                    int(query_serializer.data['assembly']),
                    int(query_serializer.data['chromosome']),
                    target_base,
                    int(query_serializer.data['number_around']))
                humans_and_sequences = self.get_population_sequences(first_tile_position_int, last_tile_position_int, max_num_spanning_tiles, center_position_int, center_index,
                    cgf_translator, center_cgf_translator, int(query_serializer.data['number_around']))
            except EmptyPathError:
                return Response("Query includes loci that are not included in tile library", status=status.HTTP_404_NOT_FOUND)
            except LocusOutOfRangeException as e:
                return Response(e.value, status=status.HTTP_404_NOT_FOUND)
            except (UnexpectedLanternBehaviorError, CGFTranslatorError) as e: # Not run in test cases, which is expected
                return Response(e.value, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            except (requests.ConnectionError, requests.Timeout) as e:
                return Response("Error querying Lantern: %s" % (str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            return_serializer = PopulationVariantSerializer(data=humans_and_sequences, many=True)
            if return_serializer.is_valid():
                return Response(return_serializer.data)
            return Response(return_serializer.errors, status=status.HTTP_500_INTERNAL_SERVER_ERROR) # Not raised in test cases, which is expected, since only would be run if the return serializer had errors
        return Response(query_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
