import string
import traceback
import sys

from django.http import Http404
from api.serializers import VariantSerializer, LocusSerializer, GenomeVariantInTileVariantSerializer, PopulationQuerySerializer, PopulationRangeQuerySerializer, PopulationVariantSerializer
from rest_framework import generics
from rest_framework import permissions
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from tile_library.models import TileVariant, TileLocusAnnotation, TAG_LENGTH
import tile_library.query_functions as query_fns
import tile_library.basic_functions as basic_fns

class TileVariantList(generics.ListAPIView):
    """
    List tile variants
    """
    queryset = TileVariant.objects.all()
    serializer_class = VariantSerializer

class TileVariantDetail(generics.RetrieveAPIView):
    """
    Retrieve a tile variant
    """
    queryset = TileVariant.objects.all()
    serializer_class = VariantSerializer

class TileLocusAnnotationList(APIView):
    """
    Retrieve the tile locus annotations for the tile position given by tile_hex_string
    """
    def get(self, request, tile_hex_string, format=None):
        tile_id = int(tile_hex_string.replace('.', ''), 16)
        locuses = TileLocusAnnotation.objects.filter(tile_id=tile_id).all()
        serializer = LocusSerializer(locuses, many=True)
        return Response(serializer.data)

class GenomeVariantsInTileList(APIView):
    """
    Retrieve the GenomeVariants for the tile given by the tile_hex_string
    """
    def get(self, request, tile_hex_string, format=None):
        try:
            tile_id = int(tile_hex_string.replace('.', ''), 16)
            lower_tile_variant_int = basic_fns.convert_position_int_to_tile_variant_int(tile_id)
            upper_tile_variant_int = basic_fns.convert_position_int_to_tile_variant_int(tile_id+1)-1
            tile_variants = TileVariant.objects.filter(tile_variant_name__range=(lower_tile_variant_int, upper_tile_variant_int))
            wonky_info = []
            for tile_variant in tile_variants:
                translations = tile_variant.translation_to_genome_variant.all()
                for translation in translations:
                    genome_variant = translation.genome_variant
                    wonky_info.append({
                        'tile_variant_hex_string': tile_variant,
                        'start_locus_relative_to_tile': translation.start,
                        'end_locus_relative_to_tile': translation.end,
                        'start_locus_relative_to_ref': genome_variant.start_increment,
                        'end_locus_relative_to_ref': genome_variant.end_increment,
                        'reference_bases': genome_variant.reference_bases,
                        'alternate_bases': genome_variant.alternate_bases
                    })
            serializer = GenomeVariantInTileVariantSerializer(wonky_info, many=True)
            return Response(serializer.data)
        except TileVariant.DoesNotExist:
            raise Http404

class GenomeVariantsInTileVariantList(APIView):
    """
    Retrieve the GenomeVariants for the tile variant given by the tile_variant_hex_string
    """
    def get(self, request, tile_variant_hex_string, format=None):
        try:
            tile_variant_id = int(tile_variant_hex_string.replace('.', ''), 16)
            translations = TileVariant.objects.get(tile_variant_name=tile_variant_id).translation_to_genome_variant.all()
            wonky_info = []
            for translation in translations:
                genome_variant = translation.genome_variant
                wonky_info.append({
                    'tile_variant_hex_string': tile_variant_hex_string,
                    'start_locus_relative_to_tile': translation.start,
                    'end_locus_relative_to_tile': translation.end,
                    'start_locus_relative_to_ref': genome_variant.start_increment,
                    'end_locus_relative_to_ref': genome_variant.end_increment,
                    'reference_bases': genome_variant.reference_bases,
                    'alternate_bases': genome_variant.alternate_bases
                })
            serializer = GenomeVariantInTileVariantSerializer(wonky_info, many=True)
            return Response(serializer.data)
        except TileVariant.DoesNotExist:
            raise Http404

class PopulationVariantQueryBetweenLoci(APIView):
    """
    Retrieve population sequences between position "lower_base" and "upper_base" (upper base is exclusive)
    """
    def get_variants_and_bases(self, assembly, chromosome, low_int, high_int):
        """
        Expects low_int and high_int to be 0-indexed. high_int is expected to be exclusive
        Returns list of dictionaries, keyed by cgf_string:
            cgf_string : bases of interest. Includes tags!
        Each entry in the list corresponds to a position
        """
        locuses = TileLocusAnnotation.objects.filter(assembly=assembly).filter(chromosome=chromosome).filter(
            begin_int__lt=high_int).filter(end_int__gte=low_int)
        num_locuses = locuses.count()
        #Return useful info if cannot complete query
        if num_locuses == 0:
            base_query = TileLocusAnnotation.objects.filter(assembly=assembly)
            if base_query.count() == 0:
                response_text = "Specified locus is not in this server. Try a different assembly"
            else:
                base_query = base_query.filter(chromosome=chromosome)
                if base_query.count() == 0:
                    response_text = "Specified locus is not in this server. Try a different chromosome"
                else:
                    smallest_int = base_query.order_by('begin_int').first().begin_int
                    largest_int = base_query.order_by('begin_int').reverse().first().end_int
                    response_text = "That locus is not loaded in this server. Try a number in the range %i to %i." % (smallest_int, largest_int)
        assert num_locuses > 0, response_text
        #Get framing tile position ints
        first_tile_position_int = int(locuses.first().tile_id)
        last_tile_position_int = int(locuses.last().tile_id)

        #Get maximum number of spanning tiles
        max_num_spanning_tiles = query_fns.get_max_num_tiles_spanned_at_position(first_tile_position_int)

        #Create cgf_translator for each position
        cgf_translator_by_position = query_fns.get_cgf_translator(locuses, low_int, high_int, assembly)

        #Add spanning tiles to cgf_translator
        spanning_tile_variants = query_fns.get_tile_variants_spanning_into_position(first_tile_position_int)
        for var in spanning_tile_variants:
            cgf_str, bases = query_fns.get_tile_variant_cgf_str_and_bases_between_loci_unknown_locus(var, low_int, high_int, assembly)
            assert cgf_str not in cgf_translator_by_position[0], "Repeat spanning cgf_string in position %s" % (string.join(cgf_str.split('.')[:-1]), '.')
            cgf_translator_by_position[0][cgf_str] = bases
        return first_tile_position_int, last_tile_position_int, max_num_spanning_tiles, cgf_translator_by_position

    def get_bases_for_human(self, human_name, positions_queried, first_tile_position_int, last_tile_position_int, cgf_translator):
        sequence = ""
        for cgf_string in positions_queried:
            if len(cgf_string.split('+')) > 1:
                num_positions_spanned = int(cgf_string.split('+')[1])-1
            else:
                num_positions_spanned = 0
            non_spanning_cgf_string = cgf_string.split('+')[0]
            tile_position_int = int(string.join(non_spanning_cgf_string.split('.')[:-1], ''),16)
            tile_position_str = basic_fns.get_position_string_from_position_int(tile_position_int)
            assert last_tile_position_int >= tile_position_int, \
                "CGF string went over expected max position (CGF string: %s, Max position: %s)" % (tile_position_str,
                    basic_fns.get_position_string_from_position_int(last_tile_position_int))
            assert len(cgf_translator) > tile_position_int-first_tile_position_int, \
                "Translator doesn't include enough positions (Translator length: %i, Number of needed positions: %i)" % (len(cgf_translator),
                    tile_position_int-first_tile_position_int)
            if tile_position_int+num_positions_spanned >= first_tile_position_int and tile_position_int <= last_tile_position_int:
                if tile_position_int - first_tile_position_int < 0:
                    tile_position_int = first_tile_position_int
                assert non_spanning_cgf_string in cgf_translator[tile_position_int - first_tile_position_int], "Translator doesn't include %s in position %i. %s" % (non_spanning_cgf_string, tile_position_int - first_tile_position_int, str(cgf_translator))
                if len(sequence) > 0:
                    curr_ending_tag = sequence[-TAG_LENGTH:]
                    new_starting_tag = cgf_translator[tile_position_int - first_tile_position_int][non_spanning_cgf_string][:TAG_LENGTH]
                    if len(curr_ending_tag) >= len(new_starting_tag):
                        assert curr_ending_tag.endswith(new_starting_tag), \
                            "Tags do not match for human %s at position %s \n Ending Tag: %s \n Starting Tag: %s \n Positions Queried: %s" % (human_name,
                                tile_position_str, curr_ending_tag, new_starting_tag, str(positions_queried))
                    else:
                        assert new_starting_tag.startswith(curr_ending_tag), \
                            "Tags do not match for human %s at position %s \n Ending Tag: %s \n Starting Tag: %s \n Positions Queried: %s" % (human_name,
                                tile_position_str, curr_ending_tag, new_starting_tag, str(positions_queried))
                    sequence += cgf_translator[tile_position_int - first_tile_position_int][non_spanning_cgf_string][TAG_LENGTH:]
                else:
                    sequence += cgf_translator[tile_position_int - first_tile_position_int][non_spanning_cgf_string]
        return sequence

    def get_population_sequences(self, first_tile_position_int, last_tile_position_int, max_num_spanning_variants, cgf_translator):
        humans = query_fns.get_population_sequences_over_position_range(first_tile_position_int-max_num_spanning_variants, last_tile_position_int)
        human_sequence_dict = {}
        for human in humans:
            short_name = human.strip('" ').split('/')[-1]
            human_sequence_dict[human] = ['', '']
            human_sequence_dict[human][0] = self.get_bases_for_human(short_name, humans[human][0], first_tile_position_int, last_tile_position_int, cgf_translator)
            human_sequence_dict[human][1] = self.get_bases_for_human(short_name, humans[human][1], first_tile_position_int, last_tile_position_int, cgf_translator)
        humans_with_sequences = []
        for human in human_sequence_dict:
            humans_with_sequences.append(
                {'human_name':human.strip('" ').split('/')[-1],
                 'phase_A_sequence':human_sequence_dict[human][0],
                 'phase_B_sequence':human_sequence_dict[human][1],
                 'phased':False}
            )
        return humans_with_sequences

    def get(self, request, format=None):
        query_serializer = PopulationRangeQuerySerializer(data=request.query_params)
        if query_serializer.is_valid():
            try:
                lower_base = int(query_serializer.data['lower_base'])
                upper_base = int(query_serializer.data['upper_base'])
                if query_serializer.data['indexing'] == 1:
                    lower_base -= 1
                    upper_base -= 1
                first_tile_position_int, last_tile_position_int, max_num_spanning_tiles, cgf_translator = self.get_variants_and_bases(
                    int(query_serializer.data['assembly']),
                    int(query_serializer.data['chromosome']),
                    lower_base,
                    upper_base)
                humans_and_sequences = self.get_population_sequences(first_tile_position_int, last_tile_position_int, max_num_spanning_tiles, cgf_translator)
            except AssertionError as e:
                return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            except Exception as e:
                return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            return_serializer = PopulationVariantSerializer(data=humans_and_sequences, many=True)
            if return_serializer.is_valid():
                return Response(return_serializer.data)
            return Response(return_serializer.errors, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(query_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PopulationVariantQuery(APIView):
    """
    Retrieve population sequences at position "target_base" (with "number_around" bases around "target_base" also retrieved).
    Requires lantern version 0.0.3
    """
    def get_variants_and_bases(self, assembly, chromosome, target_base_int, number_bases_around):
        """
        Expects target_base_int to be 0-indexed
        Returns list of dictionaries, keyed by cgf_string:
            cgf_string : bases of interest. Includes tags!
        Each entry in the list corresponds to a position
        """
        ######### Get center position #########
        center_locus = TileLocusAnnotation.objects.filter(assembly=assembly).filter(chromosome=chromosome).filter(
            begin_int__lte=target_base_int).filter(end_int__gt=target_base_int)
        if not center_locus.exists():
            base_query = TileLocusAnnotation.objects.filter(assembly=assembly)
            if base_query.count() == 0:
                response_text = "Specified locus is not in this server. Try a different assembly"
            else:
                base_query = base_query.filter(chromosome=chromosome)
                if base_query.count() == 0:
                    response_text = "Specified locus is not in this server. Try a different chromosome"
                else:
                    smallest_int = base_query.order_by('begin_int').first().begin_int
                    largest_int = base_query.order_by('begin_int').reverse().first().end_int
                    response_text = "That locus is not loaded in this server. Try a number in the range %i to %i." % (smallest_int, largest_int)
            assert False, response_text
        center_locus = center_locus.order_by('begin_int').first()
        center_tile_position_int = int(center_locus.tile_id)

        ######### Get locuses #########
        rough_low_int = target_base_int - number_bases_around
        rough_high_int = target_base_int + number_bases_around + 1 #non_inclusive!
        locuses = TileLocusAnnotation.objects.filter(assembly=assembly).filter(chromosome=chromosome).filter(
            begin_int__lt=rough_high_int).filter(end_int__gte=rough_low_int).order_by('begin_int')

        #Get maximum number of spanning tiles
        max_num_spanning_tiles = query_fns.get_max_num_tiles_spanned_at_position(int(locuses.first().tile_id))

        #Get framing tile position ints
        first_tile_position_int = max_num_spanning_tiles + int(locuses.first().tile_id)
        last_tile_position_int = int(locuses.last().tile_id)

        #Create cgf_translator for each position
        center_cgf_translator, cgf_translator_by_position = query_fns.get_cgf_translator_and_center_cgf_translator(locuses, target_base_int, center_tile_position_int-first_tile_position_int, max_num_spanning_tiles)

        return first_tile_position_int, last_tile_position_int, cgf_translator_by_position, center_cgf_translator

    def helper_get_bases_forward(self, curr_sequence, cgf_string, translator, num_bases_around):
        non_spanning_cgf_string = cgf_string.split('+')[0]
        if len(curr_sequence) > 1:
            curr_ending_tag = curr_sequence[-TAG_LENGTH:]
            new_starting_tag = translator[non_spanning_cgf_string][:TAG_LENGTH]
            if len(curr_ending_tag) >= len(new_starting_tag):
                assert curr_ending_tag.endswith(new_starting_tag), \
                    "Tags do not match. Ending Tag: %s, Starting Tag: %s." % (curr_ending_tag, new_starting_tag)
            else:
                assert new_starting_tag.startswith(curr_ending_tag), \
                    "Tags do not match. Ending Tag: %s, Starting Tag: %s." % (curr_ending_tag, new_starting_tag)
            new_sequence = translator[non_spanning_cgf_string][TAG_LENGTH:]
        else:
            new_sequence = translator[non_spanning_cgf_string]
        if len(curr_sequence) + len(new_sequence) >= num_bases_around + 1:
            amt_to_index_into = num_bases_around + 1 - len(curr_sequence)
            return new_sequence[:amt_to_index_into], True
        else:
            return new_sequence, False

    def helper_get_bases_reverse(self, curr_sequence, cgf_string, translator, num_bases_around):
        non_spanning_cgf_string = cgf_string.split('+')[0]
        if len(curr_sequence) > 1:
            curr_ending_tag = curr_sequence[:TAG_LENGTH]
            new_starting_tag = translator[non_spanning_cgf_string][-TAG_LENGTH:]
            if len(curr_ending_tag) >= len(new_starting_tag):
                assert curr_ending_tag.endswith(new_starting_tag), \
                    "Tags do not match. Ending Tag: %s, Starting Tag: %s." % (curr_ending_tag, new_starting_tag)
            else:
                assert new_starting_tag.startswith(curr_ending_tag), \
                    "Tags do not match. Ending Tag: %s, Starting Tag: %s." % (curr_ending_tag, new_starting_tag)
            new_sequence = translator[non_spanning_cgf_string][:-TAG_LENGTH]
        else:
            new_sequence = translator[non_spanning_cgf_string]
        if len(curr_sequence) + len(new_sequence) >= num_bases_around + 1:
            amt_to_index_into = num_bases_around + 1 - len(curr_sequence)
            return new_sequence[-amt_to_index_into:], True
        else:
            return new_sequence, False

    def get_bases_for_human(self, human_name, sequence_of_tile_variants, cgf_translator, center_cgf_translator, num_bases_around):
        #Find middle
        middle_index = None
        for i, cgf_string in enumerate(sequence_of_tile_variants):
            non_spanning_cgf_string = cgf_string.split('+')[0]
            if non_spanning_cgf_string in center_cgf_translator[1]:
                middle_index = i
        assert middle_index != None, "Human %s did not have a cgf_string in the center_cgf_translator (%s)" % (human_name, str(center_cgf_translator))

        sequence = center_cgf_translator[1][sequence_of_tile_variants[middle_index].split('+')[0]]
        forward_sequence = sequence
        reverse_sequence = sequence
        #Go forward
        for i, cgf_string in enumerate(sequence_of_tile_variants[1+middle_index:]):
            if i == 0:
                new_sequence, keep_going = self.helper_get_bases_forward(forward_sequence, cgf_string, center_cgf_translator[2], num_bases_around)
            else:
                new_sequence, keep_going = self.helper_get_bases_forward(forward_sequence, cgf_string, cgf_translator[i+middle_index], num_bases_around)
            forward_sequence += new_sequence
            if not keep_going:
                break
        #go backward
        backward_seq = sequence_of_tile_variants[:middle_index]
        backward_seq.reverse()
        for i, cgf_string in enumerate(backward_seq):
            if i == 0:
                new_sequence, keep_going = self.helper_get_bases_forward(reverse_sequence, cgf_string, center_cgf_translator[0], num_bases_around)
            else:
                new_sequence, keep_going = self.helper_get_bases_forward(reverse_sequence, cgf_string, cgf_translator[middle_index - i], num_bases_around)
            reverse_sequence = new_sequence + reverse_sequence
            if not keep_going:
                break
        return reverse_sequence + forward_sequence[1:]

    def get_population_sequences(self, first_tile_position_int, last_tile_position_int, cgf_translator, center_cgf_translator, num_bases_around):
        humans = query_fns.get_population_sequences_over_position_range(first_tile_position_int, last_tile_position_int)
        human_sequence_dict = {}
        for human in humans:
            short_name = human.strip('" ').split('/')[-1]
            human_sequence_dict[human] = ['', '']
            human_sequence_dict[human][0] = self.get_bases_for_human(short_name, humans[human][0],
                                                                     first_tile_position_int, last_tile_position_int,
                                                                     cgf_translator, center_cgf_translator, num_bases_around)
            human_sequence_dict[human][1] = self.get_bases_for_human(short_name, humans[human][1],
                                                                     first_tile_position_int, last_tile_position_int,
                                                                     cgf_translator, center_cgf_translator, num_bases_around)
        humans_with_sequences = []
        for human in human_sequence_dict:
            humans_with_sequences.append(
                {'human_name':human.strip('" ').split('/')[-1],
                 'phase_A_sequence':human_sequence_dict[human][0],
                 'phase_B_sequence':human_sequence_dict[human][1],
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
                first_tile_position_int, last_tile_position_int, cgf_translator, center_cgf_translator = self.get_variants_and_bases(
                    int(query_serializer.data['assembly']),
                    int(query_serializer.data['chromosome']),
                    target_base,
                    int(query_serializer.data['number_around']))
                humans_and_sequences = self.get_population_sequences(first_tile_position_int, last_tile_position_int,
                    cgf_translator, center_cgf_translator, int(query_serializer.data['number_around']))
            except AssertionError as e:
                return Response(traceback.format_exc(), status=status.HTTP_500_INTERNAL_SERVER_ERROR )
            except Exception as e:
                return Response(traceback.format_exc(), status=status.HTTP_500_INTERNAL_SERVER_ERROR )
            return_serializer = PopulationVariantSerializer(data=humans_and_sequences, many=True)
            if return_serializer.is_valid():
                return Response(return_serializer.data)
            return Response(return_serializer.errors, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(query_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
