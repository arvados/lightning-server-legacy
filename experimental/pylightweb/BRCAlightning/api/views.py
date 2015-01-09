import string

from api.serializers import VariantSerializer, LocusSerializer, PopulationQuerySerializer, PopulationVariantSerializer
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
        locuses = TileLocusAnnotations.objects.filter(tile_id=tile_id).all()
        serializer = LocusSerializer(locuses, many=True)
        return Response(serializer.data)


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
        Each entry in the list corresponds
        """
        low_int = target_base_int - number_bases_around
        high_int = target_base_int + number_bases_around + 1
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
        cgf_translator_by_position = query_fns.get_cgf_translator(locuses, low_int, high_int)

        #Add spanning tiles to cgf_translator
        spanning_tile_variants = query_fns.get_tile_variants_spanning_into_position(first_tile_position_int)
        for var in spanning_tile_variants:
            cgf_str, bases = query_fns.get_tile_variant_cgf_str_and_bases(var, low_int, high_int, assembly)
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
        query_serializer = PopulationQuerySerializer(data=request.query_params)
        if query_serializer.is_valid():
            try:
                target_base = int(query_serializer.data['target_base'])
                if query_serializer.data['indexing'] == 1:
                    target_base -= 1
                first_tile_position_int, last_tile_position_int, max_num_spanning_tiles, cgf_translator = self.get_variants_and_bases(
                    int(query_serializer.data['assembly']),
                    int(query_serializer.data['chromosome']),
                    target_base,
                    int(query_serializer.data['number_around']))
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
