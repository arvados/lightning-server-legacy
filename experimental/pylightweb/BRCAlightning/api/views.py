import string
import traceback
import sys
import re

from django.http import Http404
from api.serializers import TileVariantSerializer, LocusSerializer, PopulationVariantSerializer, PopulationQuerySerializer, PopulationRangeQuerySerializer
from rest_framework import generics
from rest_framework import permissions
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from tile_library.models import Tile, TileVariant, TileLocusAnnotation, TAG_LENGTH
import tile_library.query_functions as query_fns
import tile_library.basic_functions as basic_fns

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
    def get_variants_and_bases(self, assembly, chromosome, low_int, high_int):
        """
        Expects low_int and high_int to be 0-indexed. high_int is expected to be exclusive
        Returns list of dictionaries, keyed by cgf_string:
            cgf_string : bases of interest. Includes tags!
        Each entry in the list corresponds to a position
        """
        locuses = TileLocusAnnotation.objects.filter(assembly=assembly).filter(chromosome=chromosome).filter(
            begin_int__lt=high_int).filter(end_int__gt=low_int).order_by('begin_int')
        num_locuses = locuses.count()
        #Return useful info if cannot complete query
        response_text = "Expect at least one locus to match the query"
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
        last_tile_position_int = max(int(locuses.last().tile_id), first_tile_position_int) # unsure if this max is required
        # but the max prevents choosing a last tile position that's smaller than the first tile position

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
            num_positions_spanned = basic_fns.get_number_of_tiles_spanned(cgf_string) - 1
            non_spanning_cgf_string = cgf_string.split('+')[0]
            tile_position_int = basic_fns.get_position_from_cgf_string(cgf_string)
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
                assert non_spanning_cgf_string in cgf_translator[tile_position_int - first_tile_position_int], \
                    "Translator doesn't include %s in position %i. %s" % (non_spanning_cgf_string, tile_position_int - first_tile_position_int, str(cgf_translator))
                if len(sequence) > 0:
                    curr_ending_tag = sequence[-TAG_LENGTH:]
                    new_starting_tag = cgf_translator[tile_position_int - first_tile_position_int][non_spanning_cgf_string][:TAG_LENGTH]
                    if len(curr_ending_tag) >= len(new_starting_tag):
                        assert curr_ending_tag.endswith(new_starting_tag), \
                            "Tags do not match for human %s at position %s. Ending Tag: %s. Starting Tag: %s. Positions Queried: %s" % (human_name,
                                tile_position_str, curr_ending_tag, new_starting_tag, str(positions_queried))
                    else:
                        assert new_starting_tag.startswith(curr_ending_tag), \
                            "Tags do not match for human %s at position %s. Ending Tag: %s. Starting Tag: %s. Positions Queried: %s" % (human_name,
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
                return Response(traceback.format_exc(), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            except Exception as e:
                return Response(traceback.format_exc(), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            return_serializer = PopulationVariantSerializer(data=humans_and_sequences, many=True)
            if return_serializer.is_valid():
                return Response(return_serializer.data)
            return Response(return_serializer.errors, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(query_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PopulationVariantQueryAroundLocus(APIView):
    """
    Retrieve population sequences at position "target_base" (with "number_around" bases around "target_base" also retrieved).
    If the positions are 1-indexed, set "indexing" to 1. Defaults to number_around=0.
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
            begin_int__lt=rough_high_int).filter(end_int__gt=rough_low_int).order_by('begin_int')

        #Get framing tile position ints
        first_tile_position_int =  int(locuses.first().tile_id)
        last_tile_position_int = max(int(locuses.last().tile_id), first_tile_position_int)

        #Get maximum number of spanning tiles
        max_num_spanning_tiles = query_fns.get_max_num_tiles_spanned_at_position(first_tile_position_int)

        #Create cgf_translator for each position
        if locuses.count() == last_tile_position_int - first_tile_position_int + 1:
            center_index = center_tile_position_int-first_tile_position_int
        else:
            center_index = None
            for i, locus in enumerate(locuses):
                if locus.tile_id == center_tile_position_int:
                    assert center_index == None, "multiple center locuses"
                    center_index = i
            assert center_index != None, "No center index"
        center_cgf_translator, cgf_translator_by_position = query_fns.get_cgf_translator_and_center_cgf_translator(locuses, target_base_int, center_index, max_num_spanning_tiles, assembly)

        return first_tile_position_int, last_tile_position_int, center_tile_position_int, cgf_translator_by_position, center_cgf_translator

    def helper_get_bases_forward(self, curr_sequence, cgf_string, translator, num_bases_around, string_to_print):
        non_spanning_cgf_string = cgf_string.split('+')[0]
        step_int = int(non_spanning_cgf_string.split('.')[2], 16)
        assert non_spanning_cgf_string in translator, string_to_print + "(Failed). Expects %s to be in translator (%s)" % (non_spanning_cgf_string, str(sorted(translator.keys())))
        if len(curr_sequence) > 1 and step_int > 0:
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

    def helper_get_bases_reverse(self, curr_sequence, cgf_string, translator, num_bases_around, string_to_print):
        non_spanning_cgf_string = cgf_string.split('+')[0]
        path, path_version, step, ignore = non_spanning_cgf_string.split('.')
        edge_path_int, edge_path_version, edge_path_step = basic_fns.get_position_ints_from_position_int(query_fns.get_highest_position_int_in_path(int(path,16)))
        assert non_spanning_cgf_string in translator, string_to_print + "(Failed). Expects %s to be in translator (%s)" % (non_spanning_cgf_string, str(sorted(translator.keys())))
        if len(curr_sequence) > 1 and int(step,16) < edge_path_step: # Tags will only overlap if we are on the same path
            curr_starting_tag = curr_sequence[:TAG_LENGTH]
            new_ending_tag = translator[non_spanning_cgf_string][-TAG_LENGTH:]
            if len(curr_starting_tag) >= len(new_ending_tag):
                assert curr_starting_tag.startswith(new_ending_tag), \
                    "Tags do not match. Prev Starting Tag: %s, New Ending Tag: %s." % (curr_starting_tag, new_ending_tag)
            else:
                assert new_ending_tag.endswith(curr_starting_tag), \
                    "Tags do not match. Prev Starting Tag: %s, New Ending Tag: %s." % (curr_starting_tag, new_ending_tag)
            new_sequence = translator[non_spanning_cgf_string][:-TAG_LENGTH]
        else:
            new_sequence = translator[non_spanning_cgf_string]
        if len(curr_sequence) + len(new_sequence) >= num_bases_around + 1:
            amt_to_index_into = len(new_sequence) + len(curr_sequence) - (num_bases_around + 1)
            return new_sequence[amt_to_index_into:], True
        else:
            return new_sequence, False

    def get_one_more_tile_forwards(self, human_name, phase, prev_cgf_string):
        prev_path = int(prev_cgf_string.split('.')[0], 16)
        prev_position = basic_fns.get_position_from_cgf_string(prev_cgf_string)
        curr_position = prev_position + basic_fns.get_number_of_tiles_spanned(prev_cgf_string)
        #Check to make sure we didn't go over the maximum position in the path
        check_position = query_fns.get_highest_position_int_in_path(prev_path)
        if curr_position > check_position:
            next_path_min_position, ignore = fns.get_min_position_and_tile_variant_from_path_int(prev_path+1)
            curr_position = curr_position - (check_position+1) + next_path_min_posiiton
        #Query lantern to get call at the next position
        cgf_string = query_fns.get_sub_population_sequences_over_position_range([human_name], curr_position, curr_position)[human_name][phase][0]
        #Get bases (tile_variant from cgf_string)
        bases = query_fns.get_bases_from_cgf_str(cgf_string)
        return cgf_string, bases

    def get_one_more_tile_backwards(self, human_name, phase, prev_cgf_string):
        prev_path, prev_path_version, prev_step, ignore = prev_cgf_string.split('.')
        prev_path = int(prev_path, 16)
        prev_path_version = int(prev_path_version, 16)
        prev_step = int(prev_path, 16)
        prev_position = basic_fns.get_position_from_cgf_string(prev_cgf_string)
        if prev_step == 0:
            curr_position = query_fns.get_highest_position_int_in_path(prev_path-1)
        else:
            curr_position = prev_position - 1 #First assume that the previous tile wasn't spanning...
        #Query lantern to get call at the next position
        curr_call = []
        curr_path, curr_path_version, curr_step = basic_fns.get_position_ints_from_position_int(curr_position)
        while len(curr_call) == 0:
            curr_call = query_fns.get_sub_population_sequences_over_position_range([human_name], curr_position, curr_position)[human_name][phase]
            if curr_step == 0:
                curr_position = query_fns.get_highest_position_int_in_path(curr_path-1)
            else:
                curr_position -= 1
            curr_path, curr_path_version, curr_step = basic_fns.get_position_ints_from_position_int(curr_position)

        cgf_string = curr_call[0]
        #Get bases (tile_variant from cgf_string)
        bases = query_fns.get_bases_from_cgf_str(cgf_string)
        return cgf_string, bases

    def get_bases_for_human(self, human, sequence_of_tile_variants, cgf_translator, center_cgf_translator, num_bases_around, middle_position, cgf_translator_middle_index, phase):
        middle_position_str = basic_fns.get_position_string_from_position_int(middle_position)
        middle_index = None
        for i, cgf_string in enumerate(sequence_of_tile_variants):
            curr_position = basic_fns.get_position_from_cgf_string(cgf_string)
            if curr_position <= middle_position:
                middle_index = i
        assert middle_index != None, "Human %s did not have a position less than the middle_position %s. (%s)" % (human, middle_position_str, str(center_cgf_translator))
        center_cgf_string = sequence_of_tile_variants[middle_index].split('+')[0]
        assert center_cgf_string in center_cgf_translator[1], \
            "CGF string %s at middle index %i (for middle position %s) is not in center_cgf_translator" % (center_cgf_string, middle_index, middle_position_str)
        sequence = center_cgf_translator[1][center_cgf_string]
        forward_sequence = sequence
        reverse_sequence = sequence
        #Go forward
        curr_cgf_translator_index = cgf_translator_middle_index
        for i, cgf_string in enumerate(sequence_of_tile_variants[middle_index:]):
            if i == 0:
                string_to_print = "cgf_translator length: %i. Query: center_cgf_translator, forward strand, position %s " % (len(cgf_translator), cgf_string)
                new_sequence, finished = self.helper_get_bases_forward(forward_sequence, cgf_string, center_cgf_translator[2], num_bases_around, string_to_print)
            else:
                string_to_print += "Query: position %s " % (cgf_string)
                new_sequence, finished = self.helper_get_bases_forward(forward_sequence, cgf_string, cgf_translator[curr_cgf_translator_index], num_bases_around, string_to_print)
            forward_sequence += new_sequence
            prev_cgf_translator_index = curr_cgf_translator_index
            curr_cgf_translator_index += basic_fns.get_number_of_tiles_spanned(cgf_string)
            string_to_print += "(Success). Prev_cgf_translator_index: %i, new one: %i. " % (prev_cgf_translator_index, curr_cgf_translator_index)
            if finished:
                break
            if curr_cgf_translator_index >= len(cgf_translator):
                break
        while not finished:
            cgf_string, bases = self.get_one_more_tile_forwards(human, phase, cgf_string)
            string_to_print += "(Success). Query: go forward one, position %s" % (cgf_string)
            new_sequence, finished = self.helper_get_bases_forward(forward_sequence, cgf_string, {cgf_string.split('+')[0]:bases}, num_bases_around, string_to_print)
            forward_sequence += new_sequence
        ##################################################
        #go backward
        backward_tile_variant_seq = sequence_of_tile_variants[:middle_index+1]
        backward_tile_variant_seq.reverse()
        curr_cgf_translator_index = cgf_translator_middle_index
        for i, cgf_string in enumerate(backward_tile_variant_seq):
            if i == 0:
                string_to_print = "cgf_translator length: %i. Query: center_cgf_translator, reverse strand, position %s " % (len(cgf_translator), cgf_string)
                new_sequence, finished = self.helper_get_bases_reverse(reverse_sequence, cgf_string, center_cgf_translator[0], num_bases_around, string_to_print)
            else:
                string_to_print += "Query: position %s " % (cgf_string)
                new_sequence, finished = self.helper_get_bases_reverse(reverse_sequence, cgf_string, cgf_translator[curr_cgf_translator_index], num_bases_around, string_to_print)
            reverse_sequence = new_sequence + reverse_sequence
            if finished:
                break
            #Break before we try to get the next one, since at the end of the loop we will hit an index error
            try:
                next_cgf_string = backward_tile_variant_seq[i+1]
                prev_cgf_translator_index = curr_cgf_translator_index
                curr_cgf_translator_index -= basic_fns.get_number_of_tiles_spanned(next_cgf_string)
                string_to_print += "(Success). Prev_cgf_translator_index: %i, new one: %i. " % (prev_cgf_translator_index, curr_cgf_translator_index)
            except IndexError:
                break
        while not finished:
            cgf_string, bases = self.get_one_more_tile_backwards(human, phase, cgf_string)
            string_to_print += "(Success). Query: go backward one, position %s" % (cgf_string)
            new_sequence, finished = self.helper_get_bases_reverse(reverse_sequence, cgf_string, {cgf_string.split('+')[0]:bases}, num_bases_around, string_to_print)
            reverse_sequence = new_sequence + reverse_sequence
        return reverse_sequence + forward_sequence[1:]

    def get_population_sequences(self, first_tile_position_int, last_tile_position_int, center_position_int, cgf_translator, center_cgf_translator, num_bases_around):
        #Find middle
        middle_index = None
        for i, translator_dict in enumerate(cgf_translator):
            if len(translator_dict) == 0:
                assert middle_index == None, "Expect only one empty dictionary in cgf_translator"
                middle_index = i
        assert middle_index != None, "cgf_translator did not have an empty dictionary"
        humans = query_fns.get_population_sequences_over_position_range(first_tile_position_int, last_tile_position_int)
        human_sequence_dict = {}
        for human in humans:
            short_name = human.strip('" ').split('/')[-1]
            human_sequence_dict[human] = ['', '']
            human_sequence_dict[human][0] = self.get_bases_for_human(human, humans[human][0],
                                                                     cgf_translator, center_cgf_translator, num_bases_around,
                                                                     center_position_int, middle_index, 0)
            human_sequence_dict[human][1] = self.get_bases_for_human(human, humans[human][1],
                                                                     cgf_translator, center_cgf_translator, num_bases_around,
                                                                     center_position_int, middle_index, 1)
        humans_with_sequences = []
        for human in human_sequence_dict:
            humans_with_sequences.append(
                {'human_name':human.strip('" ').split('/')[-1],
                 'phase_A_sequence':human_sequence_dict[human][0],
                 'phase_B_sequence':human_sequence_dict[human][1],
                 'phase_groups_known':False}
                 )
        return humans_with_sequences

    def get(self, request, format=None):
        query_serializer = PopulationQuerySerializer(data=request.query_params)
        if query_serializer.is_valid():
            try:
                target_base = int(query_serializer.data['target_base'])
                if query_serializer.data['indexing'] == 1:
                    target_base -= 1
                first_tile_position_int, last_tile_position_int, center_position_int, cgf_translator, center_cgf_translator = self.get_variants_and_bases(
                    int(query_serializer.data['assembly']),
                    int(query_serializer.data['chromosome']),
                    target_base,
                    int(query_serializer.data['number_around']))
                humans_and_sequences = self.get_population_sequences(first_tile_position_int, last_tile_position_int, center_position_int,
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
