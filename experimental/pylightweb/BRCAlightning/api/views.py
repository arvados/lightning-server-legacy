from api.serializers import VariantSerializer, PopulationQuerySerializer, PopulationVariantSerializer
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

class PopulationVariantQuery(APIView):
    """
    Retrieve population sequences at specific position
    To get the ending loci in that chromosome and assembly
        base_query = TileLocusAnnotation.object.filter(assembly=data['assembly']).filter(chromosome=data['chromosome'])
        smallest_int = base_query.order_by('begin_int').first().begin_int
        largest_int = base_query.order_by('begin_int').reverse().first().end_int
        response_text = "That locus is not loaded into this library. Try a number in the range %i to %i." % (smallest_int, largest_int)
        response = {'text': response_text}
    """
    def get_tile_variant_cgf_str_and_bases(self, tile_variant, low_int, high_int, assembly):
        tile_position_int = basic_fns.convert_tile_variant_int_to_position_int(int(tile_variant.tile_variant_name))
        locus = TileLocusAnnotation.object.filter(assembly=assembly).get(tile_id=tile_position_int)
        start_locus_int = int(locus.start_int)
        return self.get_tile_variant_cgf_str_and_bases_fast(tile_variant, low_int, high_int, start_locus_int)

    def get_tile_variant_cgf_str_and_bases_fast(self, tile_variant, low_int, high_int, start_locus_int):
        cgf_str = tile_variant.conversion_to_cgf
        end_locus_int = start_locus_int + int(tile_variant.length)
        if cgf_str == "":
            #Backwards compatability
            cgf_str = tile_variant.getString()
        assert low_int <= end_locus_int, "Asked to get information of tile_variant that is before the low base of interest"
        assert high_int >= start_locus_int, "Asked to get information of tile_variant that is after the high base of interest"
        lower_base_position = max(low_int-start_locus_int, 0)
        higher_base_position = min(high_int, end_locus_int) - (start_locus_int+1) #add 1 for 0-indexing compatability
        if lower_base_position == higher_base_position:
            bases = tile_variant.getBaseAtPosition(lower_base_position).upper()
        else:
            bases = tile_variant.getBaseGroupBetweenPositions(lower_base_position, higher_base_position).upper()
        return cgf_str, bases

    def get_variants_and_bases_to_query(self, assembly, chromosome, target_base_int, number_bases_around):
        """
        Expects target_base_int to be 0-indexed
        Returns list of list of dictionaries, each containing keys:
            'cgf': cgf_string to query
            'bases': bases of interest. Includes tags!
        """
        low_int = target_base_int - number_bases_around
        high_int = target_base_int + number_bases_around
        locuses = TileLocusAnnotation.objects.filter(assembly=assembly).filter(chromosome=chromosome).filter(
            begin_int__lt=high_int).filter(end_int__gte=low_int)
        num_locuses = locuses.count()
        variants_to_query = [[] for i in range(num_locuses)]
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
        for i, locus in enumerate(locuses):
            tile_position_int = int(locus.tile_id)
            start_locus_int = int(locus.begin_int)
            if i == 0: #Note these can be the same!
                spanning_tile_variants = query_fns.get_tile_variants_spanning_into_position(tile_position_int)
                for var in spanning_tile_variants:
                    cgf_str, bases = self.get_tile_variant_cgf_str_and_bases(var, low_int, high_int, assembly)
                    variants_to_query[i].append({'cgf':cgf_str, 'bases':bases})
            low_variant_int = basic_fns.convert_position_int_to_tile_variant_int(tile_position_int)
            high_variant_int = basic_fns.convert_position_int_to_tile_variant_int(tile_position_int+1)-1
            tile_variants = TileVariant.objects.filter(tile_variant_name__range=(low_variant_int, high_variant_int)).all()
            for var in tile_variants:
                cgf_str, bases = self.get_tile_variant_cgf_str_and_bases_fast(var, low_int, high_int, start_locus_int)
                variants_to_query[i].append({'cgf':cgf_str, 'bases':bases})
        return variants_to_query

    def get_population_sequences_from_variants(self, variants_to_query):
        humans = {}
        for i, variants in enumerate(variants_to_query):
            human_seq_at_curr_position = {}
            for variant in variants:
                humans_with_variant = query_fns.get_population_with_tile_variant(variant['cgf'])
                for hu in humans_with_variant:
                    if hu != '':
                        if hu in human_seq_at_curr_position:
                            assert human_seq_at_curr_position[hu]['A'] == human_seq_at_curr_position[hu]['B'], 'Human %s is tri-allelic' % (hu)
                            human_seq_at_curr_position[hu]['B'] = variant['bases']
                        else:
                            #Assume same variant on both strands. We'll change it if not
                            human_seq_at_curr_position[hu] = {'A': variant['bases'], 'B': variant['bases']}
            if i == 0:
                humans = human_seq_at_curr_position
            elif i > 1:
                for human in human_seq_at_curr_position:
                    humans[human]['A'] += human_seq_at_curr_position[human]['A'][TAG_LENGTH:]
                    humans[human]['B'] += human_seq_at_curr_position[human]['B'][TAG_LENGTH:]

        humans_with_sequences = []
        for human in humans:
            humans_with_sequences.append(
                {'human_name':human,
                 'phase_A_sequence':humans[human]['A'],
                 'phase_B_sequence':humans[human]['B'],
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
                variants_to_query = self.get_variants_and_bases_to_query(
                    int(query_serializer.data['assembly']),
                    int(query_serializer.data['chromosome']),
                    target_base,
                    int(query_serializer.data['number_around']))
                humans_and_sequences = self.get_population_sequences_from_variants(variants_to_query)
            except AssertionError as e:
                return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            except Exception as e:
                return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            return_serializer = PopulationVariantSerializer(data=humans_and_sequences, many=True)
            if return_serializer.is_valid():
                return Response(return_serializer.data)
            return Response(return_serializer.errors, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(query_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
