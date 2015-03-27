def get_bases_from_lantern_name(lantern_name):
    """
    No assumptions about the location of the tile library

    Can raise ValueError, TypeError if lantern_name is not the correct format
    Can raise LanternTranslator.DoesNotExist if lantern_name is not in the database
    Can raise LanternTranslator.DegradedVariantError if the lantern translator has problems re-retrieving the variant data
    """
    lantern_name = fns.get_non_spanning_cgf_string(lantern_name)
    try:
        lantern_translation = LanternTranslator.objects.get(lantern_name=lantern_name)
        if lantern_translation.tile_library_host == "":
            #In our library!
            bases = TileVariant.objects.get(tile_variant_int=int(lantern_translation.tile_variant_int)).sequence.upper()
        else:
            tile_library_path = reverse('api:tile_variant_query_by_int', args=[lantern_translation.tile_variant_int])
            r = requests.get("http://%s%s" % (lantern_translation.tile_library_host, tile_library_path))
            r.raise_for_status()
            tile_variant = json.loads(r.text)
            bases = tile_variant['sequence'].upper()
    except (TileVariant.DoesNotExist, requests.exceptions.RequestException) as e:
        raise LanternTranslator.DegradedVariantError("Translator %s has degraded. %s" % (lantern_name, str(e)))
    except LanternTranslator.DoesNotExist:
        return ""
    return bases

def get_tile_variant_lantern_name_and_bases_between_loci_known_locus(tile_variant, assembly, queried_low_int, queried_high_int, start_locus_int, end_locus_int):
    lantern_name = tile_variant.get_tile_variant_lantern_name()
    if lantern_name != "":
        bases = tile_variant.get_bases_between_loci_known_locus(assembly, queried_low_int, queried_high_int, start_locus_int, end_locus_int)
        return lantern_name, bases
    return lantern_name, ""

def get_tile_variant_cgf_str_and_bases_between_loci_unknown_locus(tile_variant, queried_low_int, queried_high_int, assembly):
    lantern_name = tile_variant.get_tile_variant_lantern_name()
    if lantern_name != "":
        bases = tile_variant.get_bases_between_loci(queried_low_int, queried_high_int, assembly)
        return lantern_name, bases
    return lantern_name, ""

def get_lantern_name_translator(locuses, low_int, high_int, assembly):
    lantern_name_translator = {}
    locus_tile_variants_list = []
    for i, locus in enumerate(locuses):
        locus_tile_variant = locus.get_tile_variant()
        locus_tile_variants_list.append(tile_variant)
        locus_position_int = int(locus.tile_position_id)
        locus_start_int = int(locus.start_int)
        locus_end_int = int(locus.end_int)
        low_variant_int = fns.convert_position_int_to_tile_variant_int(locus_position_int)
        high_variant_int = fns.convert_position_int_to_tile_variant_int(locus_position_int+1)-1
        tile_variants = TileVariant.objects.filter(tile_variant_int__range=(low_variant_int, high_variant_int)).all()
        for var in tile_variants:
            lantern_name = ''
            bases = ''
            upper_tile_position_int = int(var.tile_id) + var.num_positions_spanned -1
            if var.num_positions_spanned != 1:
                upper_locus = get_locus(assembly, upper_tile_position_int)
                if int(upper_locus.tile_position_id) + upper_locus.get_tile_variant().num_positions_spanned - 1 == upper_tile_position_int:
                    locus_end_int = int(upper_locus.end_int)
                    lantern_name, bases = get_tile_variant_lantern_name_and_bases_between_loci_known_locus(var, assembly, low_int, high_int, locus_start_int, locus_end_int)
            else:
                if int(locus.tile_position_id) + locus_tile_variant.num_positions_spanned - 1 == upper_tile_position_int:
                    lantern_name, bases = get_tile_variant_lantern_name_and_bases_between_loci_known_locus(var, assembly, low_int, high_int, start_locus_int, end_locus_int)
            if lantern_name != '':
                if lantern_name in lantern_name_translator:
                    raise CGFTranslatorError("Repeat lantern_name (%s) in lantern_name_translator" % (lantern_name)) #not raised in test cases, which is expected
                lantern_name_translator[lantern_name] = bases
    return lantern_name_translator, locus_tile_variants_list

def crosses_center_index(variant, i, center_index, max_num_spanned):
    for num in range(max_num_spanned+1):
        if center_index-num == i and variant.num_positions_spanned > num:
            return True
    return False

def get_lantern_name_translators(locuses, target_base, center_index, max_num_spanned, assembly):
    def manage_center_translator(center_lantern_name_translator, variant, start_locus, start_locus_variant):
        if int(start_locus.tile_position_id) != int(variant.tile_id):
            return center_lantern_name_translator
        start_locus_int = int(start_locus.start_int)
        lower_tile_position_int = int(variant.tile_id)
        if variant.num_positions_spanned != 1:
            end_tile_position_int = lower_tile_position_int + var.num_positions_spanned - 1
            end_locus = get_locus(assembly, end_tile_position_int)
            if int(end_locus.tile_position_id) + end_locus.get_tile_variant().num_positions_spanned - 1 != end_tile_position_int:
                return center_lanter_name_translator
            end_locus_int = int(end_locus.end_int)
        else:
            if int(start_locus.tile_position_id)+int(start_locus_variant.num_positions_spanned) != int(variant.tile_id) + int(variant.num_positions_spanned):
                return center_lantern_name_translator
            end_locus_int = int(start_locus.end_int)

        keys = [(start_locus_int, target_base), (target_base, target_base+1), (target_base+1, end_locus_int)]
        for i, translator in enumerate(center_lantern_name_translator):
            lantern_name, bases = get_tile_variant_lantern_name_and_bases_between_loci_known_locus(variant, assembly, keys[i][0], keys[i][1], start_locus_int, end_locus_int)
            if lantern_name in translator:
                if bases != translator[lantern_name]:
                    raise CGFTranslatorError("Conflicting lantern_name-base pairing, lantern_name: %s, translator: %s" % (lantern_name, center_lantern_name_translator))
            center_lantern_name_translator[i][lantern_name] = bases
        return center_lantern_name_translator

    lantern_name_translator = {}
    center_lantern_name_translator = [{}, {}, {}]
    locus_tile_variants_list = []
    for i, locus in enumerate(locuses):
        tile_variant = locus.get_tile_variant()
        locus_tile_variants_list.append(tile_variant)
        locus_position_int = int(locus.tile_position_id)
        low_variant_int = fns.convert_position_int_to_tile_variant_int(locus_position_int)
        high_variant_int = fns.convert_position_int_to_tile_variant_int(locus_position_int+1)-1
        tile_variants = TileVariant.objects.filter(tile_variant_int__range=(low_variant_int, high_variant_int)).all()[:]
        if i == center_index:
            spanning_tile_variants = get_tile_variants_spanning_into_position(tile_position_int)
            for var in spanning_tile_variants:
                center_lantern_name_translator = manage_center_translator(center_lantern_name_translator, var, locus, locus_tile_variant)
        for var in tile_variants:
            if crosses_center_index(var, i, center_index, max_num_spanned):
                center_lantern_name_translator = manage_center_translator(center_lantern_name_translator, var, locus, locus_tile_variant)
            else:
                try:
                    lantern_name, bases = get_tile_variant_lantern_name_and_all_bases(var)
                except LanternTranslator.DoesNotExist:
                    lantern_name = ''
                    bases = ''
                if lantern_name != '':
                    if lantern_name in lantern_name_translator:
                        raise CGFTranslatorError("Repeat lantern_name (%s) in non-center lantern_name_translator" % (lantern_name))
                    lantern_name_translator[lantern_name] = bases
    return center_lantern_name_translator, lantern_name_translator, locus_tile_variants_list

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

    #Create lantern_name_translator (Dictionary keyed by cgf names where the values are the necessary bases)
    lantern_name_translator, locus_tile_variants_list = query_fns.get_lantern_name_translator(locuses, low_int, high_int, assembly)

    #Add spanning tiles to cgf_translator
    spanning_tile_variants = query_fns.get_tile_variants_spanning_into_position(first_tile_position_int)
    for var in spanning_tile_variants:
        try:
            lantern_name, bases = query_fns.get_tile_variant_lantern_name_and_bases_between_loci_unknown_locus(var, low_int, high_int, assembly)
            if lantern_name != '':
                if lantern_name in lantern_name_translator: # Never raised in test cases, which is expected. This checks for odd behavior before continuing
                    raise CGFTranslatorError("Repeat spanning cgf_string: %s. %s" % (non_spanning_cgf_string, cgf_translator))
                lantern_name_translator[lantern_name] = bases
        except SpanningAssemblyError:
            pass

    return first_tile_position_int, last_tile_position_int, max_num_spanning_tiles, lantern_name_translator, locus_tile_variants_list

def concatonate_sequences(sequence_list):
    complete_sequence = ""
    for i, sequence in enumerate(sequence_list):
        if complete_sequence == "":
            complete_sequence += sequence
        else:
            if complete_sequence[-settings.TAG_LENGTH:] != sequence[:settings.TAG_LENGTH]:
                raise Exception("concatonate sequences Tag mismatch")
            complete_sequence += sequence[settings.TAG_LENGTH:]
    return complete_sequence

def get_alignments(reference_seq, tile_variant_seq):
    reference_to_tile_variant = [(0, 0, 0, 0), (len(reference_seq), len(tile_variant_seq), len(reference_seq), len(tile_variant_seq))]
    ref_seq_file = open('ref.txt', 'w')
    ref_seq_file.write(reference_seq)
    ref_seq_file.close()
    alt_seq_file = open('seq.txt', 'w')
    alt_seq_file.write(tile_variant_seq)
    alt_seq_file.close()
    p = subprocess.Popen(['~/lightning/experimental/align2vcf --ref ref.txt --seq seq.txt'], shell=True, stdout=subprocess.PIPE)
    for translation in p.stdout:
        print translation.strip().split('\t')
        chr_name, start_int, ignore, ref_base, alt_base, ignore, ignore, end, ignore, ignore = translation.strip().split('\t')
            #trans_locus_start = translation.genome_variant.locus_start_int - start_locus_int
            #trans_locus_end = translation.genome_variant.locus_end_int - start_locus_int
            # we only need to add if the variant is an INDEL, but I'm adding all of them here since we iterate over all of them anyway
            #reference_to_tile_variant.append((trans_locus_start, translation.start, trans_locus_end, translation.end))
        #reference_to_tile_variant.sort()
        #print reference_to_tile_variant
        #return reference_to_tile_variant

def get_bases_for_human(self, human_name, positions_queried, first_tile_position_int, last_tile_position_int, lantern_name_translator, locus_tile_variant_list):
    locus_tile_position_list = [int(var.tile_id) for var in locus_tile_variant_list]
    sequence = ""
    for human_tile_index, lantern_name in enumerate(positions_queried):
        num_positions_spanned = basic_fns.get_number_of_tiles_spanned_from_lantern_name(lantern_name) - 1
        non_spanning_lantern_name = lantern_name.split('+')[0]
        tile_position_int = basic_fns.get_position_from_lantern_name(lantern_name)
        tile_position_str = basic_fns.get_position_string_from_position_int(tile_position_int)
        if last_tile_position_int < tile_position_int:
            raise UnexpectedLanternBehaviorError( #Not raised in test cases, which is expected since this is lantern-specific
                "Lantern query went over expected max position (Lantern response: %s, Max position: %s)" % (tile_position_str,
                    basic_fns.get_position_string_from_position_int(last_tile_position_int))
            )
        if first_tile_position_int <= tile_position_int+num_positions_spanned and tile_position_int <= last_tile_position_int:
            if non_spanning_lantern_name not in lantern_name_translator:
                #will happen if the locus was spanning differently from the tile variant. We need to find the positions they match up
                curr_callset_index = human_tile_index
                curr_position_int = tile_position_int
                callset_subsequence = [lantern_name]
                while curr_position_int not in locus_tile_position_list and curr_callset_index > 0 and curr_position_int > locus_tile_position_list[0]:
                    curr_callset_index -= 1
                    curr_position_int = basic_fns.get_position_from_lantern_name(positions_queried[curr_callset_index])
                    callset_subsequence.insert(0, positions_queried[curr_callset_index])
                if curr_position_int not in locus_tile_position_list:
                    raise Exception("Need to query lantern again and/or get more loci")
                curr_callset_index = human_tile_index+1
                curr_position_int = basic_fns.get_position_from_lantern_name(positions_queried[curr_callset_index])
                while curr_position_int not in locus_tile_position_list and curr_callset_index < len(positions_queried) and curr_position_int < locus_tile_position_list[-1]:
                    callset_subsequence.append(positions_queried[curr_callset_index])
                    curr_callset_index += 1
                    curr_position_int = basic_fns.get_position_from_lantern_name(positions_queried[curr_callset_index])
                if curr_position_int not in locus_tile_position_list:
                    raise Exception("Need to query lantern again and/or get more loci")
                start_i  = locus_tile_position_list.index(basic_fns.get_position_from_lantern_name(callset_subsequence[0]))
                end_i  = locus_tile_position_list.index(basic_fns.get_position_from_lantern_name(callset_subsequence[-1]))
                reference_sequence = concatonate_sequences([var.sequence for var in locus_tile_variant_list[start_i:end_i+1]])
                callset_sequence = concatonate_sequences([get_lantern_name_translator(lantern_name) for lantern_name in callset_subsequence])




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
            {'human_name':human.strip('" ').split('/')[-1],
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
