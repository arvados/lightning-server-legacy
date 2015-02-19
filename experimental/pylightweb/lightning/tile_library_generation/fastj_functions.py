"""
Needs GLOBAL PATH
"""

from tile_library_generation.fastj_objects import TileObject, LightTileObject
from tile_library_generation.constants import SUPPORTED_ASSEMBLIES, CHR_CHOICES
from tile_library.models import TAG_LENGTH, TileLocusAnnotation
from errors import NoteParseError

def build_tile_library(collection_reader, library_input_filename, loci_input_filename, sequence_input_filename, unpaired_cgf_string_library_filename, global_path):
    """
    Input Files:
        library_input_file format:
           tile_var_period_sep, tile_variant_name, tile_int, population_size, md5sum, cgf_string

        loci_input_file format:
           tile_int, assembly, chromosome, locus_beg, locus_end, chrom_name

        sequence_input_file format:
           tilevarname, varname, length, md5sum, created, updated, sequence, start, end, tile_int

        unpaired_cgf_string_library_file format:
            cgf_string, population_size, md5sum
            (note: population size is unused)

    Return values:
        tile_library (a populated TileLibrary object)
    """
    ### Initialize blank library ###
    tile_library = TileLibrary(global_path)
    ### Read current library ###
        #Unsure if this will work on gzipped files...
        #Current library is guaranteed to exist only in path, so don't need to check
    with collection_reader.open(library_input_filename) as f:
        for line in f:
            human_readable_name, tile_variant_name, tile_int, popul, md5sum, cgf_string = line.strip().split(',')
            small_library = tile_library.get_smaller_library(int(tile_int))
            small_library.initialize_library(int(tile_variant_name), md5sum, int(population_incr), cgf_string)
    ### Read in loci for current library ###
        #Unsure if this will work on gzipped files...
        #Loci input might cover multiple paths, so only load loci in if it's in the path
    with collection_reader.open(loci_input_filename) as f:
        for line in f:
            tile_int, assembly, chromosome, locus_beg, locus_end, chrom_name = line.strip().split(',')
            path = hex(int(tile_int)).lstrip('0x').zfill(9)[:3]
            if path == global_path:
                small_library = tile_library.get_smaller_library(int(tile_int))
                if chrom_name == '""':
                    chrom_name = ''
                locus = LocusObject(assembly, chromosome, locus_beg, locus_end, chrom_name)
                small_library.add_locus(locus)
    ### Read in reference sequences for current library ###
        #Unsure if this will work on gzipped files...
        #sequence input might cover multiple paths, so only load sequence in if it's in the path
    with collection_reader.open(sequence_input_filename) as f:
        for line in f:
            tilevarname, varname, length, md5sum, created, updated, sequence, start, end, tile_int, num_spanning_tiles = line.strip().split(',')
            path = hex(int(tile_int)).lstrip('0x').zfill(9)[:3]
            if path == global_path and int(varname) == 0:
                small_library = tile_library.get_smaller_library(int(tile_int))
                small_library.add_reference_sequence(sequence, md5sum, tilevarname)
    ### Read in unpaired cgf strings for current library ###
        #Unsure if this will work on gzipped files...
        #input might cover multiple paths, so only load sequence if it's the path
    with collection_reader.open(unpaired_cgf_string_library_filename) as f:
        for line in f:
            cgf_string, population_size, md5sum = line.strip().split(',')
            path = cgf_string.split('.')[0]
            position_int = basic_fns.get_position_from_cgf_string(cgf_string)
            if path == global_path:
                small_library = tile_library.get_smaller_library(position_int)
                small_library.add_cgf_string(cgf_string, md5sum)
    ### Ensure library is built correctly ###
    tile_library.check_correct_formation()

    return tile_library

#GenomeVariants are expected to fade out and be replaced by annotations directly to tile variants in the tile library
#This data structure is not built to span multiple studies
def build_genome_variants(genome_variants_filename, global_path):
    """
    Input Files:
        genome_variants_file format:
           genome_variant_id, assembly_int, chrom_int, locus_begin_int, locus_end_int, reference_bases, alternate_bases, \
                names (aliases), info (in psql-readable json), created, last_modified

    Return values:
        HG19_GENOME_VARIANTS[(chrom_name, locus_beg_int, locus_end_int, ref_seq, var_seq)] = genome_variant_id
    """
    HG19_GENOME_VARIANTS = {}
    GENOME_VARIANT_ID = int(global_path+'00'+'0000'+'000', 16)
    ### Read in genome variants for current library if we want to prebuild the dictionary ###
    ### And update GENOME_VARIANT_ID if necessary
    if genome_variants_file != None:
        with copen(genome_variants_file, 'r') as f:
            for line in f:
                line_list = line.strip().split(',')
                HG19_GENOME_VARIANTS[(int(line_list[1]), int(line_list[2]), int(line_list[3]), int(line_list[4]), line_list[6], line_list[7])] = int(line_list[0])
                GENOME_VARIANT_ID = max(GENOME_VARIANT_ID, int(line_list[0])+1)

def parse_fj_header(loadedData):
    """
        Accepts the json-parsed header read from FJ

        Checks the tile is in the GLOBAL_PATH we are supposed to be parsing

        Adds tilename, start tag, end tag, start sequence, end sequence, reference sequence, md5sum, assembly, chromosome, start and end locus ints,
            and seed tile length to tile_to_save

        Returns tile_to_save (TileObject)
    """
    tilename = str(loadedData[u'tileID'])
    path, version, step, variant = tilename.split('.')
    assert path == GLOBAL_PATH
    step = step.zfill(4)
    tile_id = int(path+version+step, 16)
    tile_to_save = TileObject(tile_id, str(loadedData[u'startTag']), str(loadedData[u'endTag']), loadedData[u'n'], str(loadedData[u'md5sum']))

    #Alter start and end sequence if necessary (in the case of non-sequenced tags)
    if u'startSeq' in loadedData:
        if str(loadedData[u'startTag']).lower() != str(loadedData[u'startSeq']).lower():
            tile_to_save.start_seq = str(loadedData[u'startSeq'])
        if str(loadedData[u'endTag']).lower() != str(loadedData[u'endSeq']).lower():
            tile_to_save.end_seq = str(loadedData[u'endSeq'])

    #Add assembly and chromosome information
    locus = str(loadedData[u'locus'][0][u'build'])
    locus = locus.split()
    assert locus[0] in SUPPORTED_ASSEMBLIES, "Not yet able to support multiple assemblies"
    tile_to_save.locus.assembly = SUPPORTED_ASSEMBLIES[locus[0]]
    if locus[1] in CHR_CHOICES:
        tile_to_save.locus.chromosome = CHR_CHOICES[locus[1]]
    else:
        tile_to_save.locus.chromosome = 26
        tile_to_save.locus.chrom_name = locus[1]

    #Add reference sequence, loci begins and ends, and the number of tiles spanned
    if u'seedTileLength' in loadedData:
        tile_to_save.seed_tile_length = int(loadedData[u'seedTileLength'])
        if tile_to_save.seed_tile_length > 1:
            beg_locus = POPUL_LOCI[tile_id]
            end_locus = POPUL_LOCI[tile_id+tile_to_save.seed_tile_length-1]
            tile_to_save.add_loci(beg_locus, end_locus_object=end_locus)
            new_ref_seq = ""
            for i in range(tile_to_save.seed_tile_length):
                if i == 0:
                    new_ref_seq += REFERENCE_SEQ_LOOKUP[tile_id]
                else:
                    new_ref_seq += REFERENCE_SEQ_LOOKUP[tile_id+i][24:]
            tile_to_save.reference_sequence = new_ref_seq
        else:
            tile_to_save.locus.begin = int(locus[2].split('-')[0])
            tile_to_save.locus.end = int(locus[3].split('+')[0])
            tile_to_save.reference_sequence = REFERENCE_SEQ_LOOKUP[tile_id]
    else:
        tile_to_save.seed_tile_length = 1
        tile_to_save.locus.begin = int(locus[2].split('-')[0])
        tile_to_save.locus.end  = int(locus[3].split('+')[0])
        tile_to_save.reference_sequence = REFERENCE_SEQ_LOOKUP[tile_id]
    return tile_to_save

def translate_locus(genome_variant_locus, tile_locus, ref_tile_int, ref_tile_lengths):
    try:
        tile_locus.check_same_assembly_and_chrom(genome_variant_locus)
    except AssertionError:
        return False, None
    if genome_variant_locus.start < tile_locus.start: #If the Variant starts before the Tile starts
        return False, None
    if genome_variant_locus.end > tile_locus.end: #If the Variant ends after the Tile ends
        return False, None

    start_position = ref_tile_int
    start_int = genome_variant_locus.start - tile_locus.start
    starting_point = 0
    while start_int >= sum(ref_tile_lengths[:starting_point+1]) and len(ref_tile_lengths) >= starting_point:
        starting_point += 1
        start_position += 1
    start_int -= sum(ref_tile_lengths[:starting_point])
    assert start_int >=0, "GenomeVariant translate_locus went too far with start_int"

    end_position = ref_tile_int
    end_int = genome_variant_locus.end - tile_locus.start
    stopping_point = 0
    while end_int >= sum(ref_tile_lengths[:stopping_point+1]) and len(ref_tile_lengths) >= stopping_point:
        stopping_point += 1
        end_position += 1
    end_int -= sum(ref_tile_lengths[:stopping_point])
    assert end_int < sum(ref_tile_lengths[:stopping_point+1]), \
        "GenomeVariant continues past the given locus: Start_position: %s, start_int: %i, End_position: %s, end_int %i, Reference_tile_lengths %s" % (
            hex(start_position), start_int, hex(end_position), end_int, str(ref_tile_lengths)
        )
    assert end_int >= 0, "GenomeVariant translate_locus went too far with end_int"
    genome_variant = GenomeVariantObject(genome_variant_locus, start_position, start_int, end_position, end_int)
    return True, genome_variant

def parse_gff_note(note, tile_locus, tile_position_int, reference_tile_lengths):
    regex = '^gffsrc: chr[1-9][0-9]* [0-9]+ [0-9]+ [IS][NU][DBP][E]?[L]?'
    assert re.match(regex, note) != None, "%s Doesn't match the recognized gffsrc note type" % str(note)
    gff_list = note.split()
    genome_variant_locus = LocusObject(tile_locus.assembly, None, "", int(gff_list[2].split('-')[0]), 1+int(gff_list[3].split('+')[0]))
    if gff_list[1] in CHR_CHOICES:
        genome_variant_locus.chromosome = CHR_CHOICES[gff_list[1]]
    else:
        genome_variant_locus.chromosome = 26
        genome_variant_locus.chrom_name = gff_list[1]
    tile_locus.check_self()
    genome_variant_locus.check_self()
    in_locus, genome_variant = translate_locus(genome_variant_locus, tile_locus, tile_position_int, reference_tile_lengths)
    if in_locus:
        for gff_info in string.join(gff_list[5:]).split(';'):
            #Find the reference allele and other info (except the variant allele)
            if gff_info.startswith('ref_allele'):
                genome_variant.ref_seq = gff_info.split()[1]
            elif gff_info.startswith('alleles'):
                pass
            elif gff_info.startswith('db_xref'):
                genome_variant.known_aliases = gff_info.split()[1].split(',') #take off db_xref
            elif gff_info.startswith('amino_acid'):
                genome_variant.info['amino_acid'] = gff_info
            elif gff_info.startswith('ucsc_trans'):
                genome_variant.info['ucsc_trans'] = gff_info
            else:
                genome_variant.info['other'] = gff_info
        assert genome_variant.ref_seq != None, "Expects GFF note to have a ref_allele entry"
        for gff_info in string.join(gff_list[5:]).split(';'):
            if gff_info.startswith('alleles'):
                poss_var_seqs = gff_info.split()[1].split('/')
                if len(poss_var_seqs) == 1:
                    genome_variant.var_seq = poss_var_seqs[0]
                else:
                    assert len(poss_var_seqs) == 2, "Expects GFF alleles note to only have 2 phase possibilities. Parsing went off"
                    if genome_variant.ref_seq in poss_var_seqs:
                        poss_var_seqs.remove(genome_variant.ref_seq)
                        genome_variant.var_seq = poss_var_seqs[0]

                    else:
                        if isPhaseA:
                            genome_variant.var_seq = poss_var_seqs[0]
                        else:
                            genome_variant.var_seq = poss_var_seqs[1]
        assert var_seq != None, "Expects GFF note to have an alleles entry"
        gff_notes[(start_tile_pos, start_int, end_tile_pos, end_int, ref_seq, var_seq)] = [aliases, info]

def bare_parse_notes(notes):
    """
        notes: list of notes read in from FASTJ format

        Throws NoteParseError if phase not given or phase is not of type 'Reported'

        Returns wellSequenced boolean and isPhaseA boolean
    """
    wellSequenced = True
    isPhaseA = None
    for note in notes:
        if 'GAP' in note or 'nocall' in note: #human-specific gaps; should not be in tile library; should be in the abv/npy file
            wellSequenced = False
        elif 'Phase' in note:
            if 'REPORTED' not in note:
                raise NoteParseError("Parsing requires Reported phasing")
            if note.endswith('A'):
                isPhaseA = True
            else:
                isPhaseA = False
    if isPhaseA == None:
        raise NoteParseError("Expects phase annotation in 'notes'")
    return wellSequenced, isPhaseA

def parse_notes(notes, tile_to_save, tile_variant_id, tile_position_int, reference_tile_lengths, genome_variants_at_position, curr_genome_variant_id,
              reference_seq, whole_variant_seq, locus, genome_variant_filename, translation_filename, out):
    """
        notes: list of annotations read in from FASTJ format. Assumed to use reported genomes
    tile_variant_id: the primary key for the tile_variant containing these GenomeVariants
    tile_position_int: the position integer for the tile_variant

    genome_variants_at_position: dictionary keyed by genome_variant pointing to their ids
    curr_genome_variant_id: next free integer id for genome_variant
    reference_seq: reference seq to check against/read in from
    locus: hg19 locuses spanned by the tile

    Possible note types:
        human name (starts with 'hu')
        gffsrc (can be multiple)
        GenomeVariant (can be multiple)
        Phase
        VariantOnTag
        GAP and nocall

    no phenotypic data is known to be passed from the FASTJ file
    Currently do not check that db_xrefs are the same
    """
    # for tile_library_genomevariant: id, start_tile_position, start_increment, end_increment, end_tile_position, names, reference_bases, alternate_bases, info, created, last_modified
    # for tile_library_genomevarianttranslation: (id), start, end, genome_variant_id, tile_variant_id,
    assert sum(reference_tile_lengths)-24*(len(reference_tile_lengths)-1)==len(tile_to_save.reference_sequence), "Expects reference sequence and reference_tile_lengths to match"
    PATH = tile_to_save.get_path()
    genome_variants = {}
    matched_genome_variants = []
    gff_notes = {}
    skip = False
    #Check if well sequenced, which phase it is, and assert that 'REPORTED' is in the Phase call
    wellSequenced, isPhaseA = bare_parse_notes(notes)

    for note in notes:
        if note.startswith('gffsrc'):
            regex = 'gffsrc: chr[1-9][0-9]* [0-9]+ [0-9]+ [IS][NU][DBP][E]?[L]?'
            assert re.match(regex, note) != None, "%s Doesn't match the recognized gffsrc note type" % str(note)
            gff_list = note.split()
            in_locus, converted_locus = translate_locus('hg19', gff_list[1], gff_list[2], str(int(gff_list[3]) + 1), locus, tile_position_int, reference_tile_lengths)
            if in_locus:
                start_tile_pos, start_int, end_tile_pos, end_int = converted_locus
                info = {}
                aliases = []
                ref_seq = None
                var_seq = None
                for gff_info in string.join(gff_list[5:]).split(';'):
                    #Find the reference allele and other info (except the variant allele)
                    if gff_info.startswith('ref_allele'):
                        ref_seq = gff_info.split()[1]
                    elif gff_info.startswith('alleles'):
                        pass
                    elif gff_info.startswith('db_xref'):
                        aliases = gff_info.split()[1].split(',') #take off db_xref
                    elif gff_info.startswith('amino_acid'):
                        info['amino_acid'] = gff_info
                    elif gff_info.startswith('ucsc_trans'):
                        info['ucsc_trans'] = gff_info
                    else:
                        info['other'] = gff_info
                assert ref_seq != None, "Expects GFF note to have a ref_allele entry"
                for gff_info in string.join(gff_list[5:]).split(';'):
                    if gff_info.startswith('alleles'):
                        poss_var_seqs = gff_info.split()[1].split('/')
                        if len(poss_var_seqs) == 1:
                            var_seq = poss_var_seqs[0]
                        else:
                            assert len(poss_var_seqs) == 2, "Expects GFF alleles note to only have 2 phase possibilities. Parsing went off"
                            if ref_seq in poss_var_seqs:
                                poss_var_seqs.remove(ref_seq)
                                var_seq = poss_var_seqs[0]
                                assert var_seq != ref_seq, "GFF note has same variant sequence as reference sequence"
                            else:
                                if isPhaseA:
                                    var_seq = poss_var_seqs[0]
                                else:
                                    var_seq = poss_var_seqs[1]
                                assert var_seq != ref_seq, "GFF note has the same variant sequence as reference sequence"
                assert var_seq != None, "Expects GFF note to have an alleles entry"
                gff_notes[(start_tile_pos, start_int, end_tile_pos, end_int, ref_seq, var_seq)] = [aliases, info]
        elif note.startswith('ltag') or note.startswith('rtag'):
            pass
        elif 'SNP' in note or 'SUB' in note or 'INDEL' in note:
            regex = 'hg19 chr[1-9][0-9]* [0-9]+ [0-9]+ [IS][NU][DBP][E]?[L]?'
            assert re.match(regex, note) != None, "%s Doesn't match the recognized SNP, SUB, or INDEL note type" % str(note)
            variant_list = note.split()
            if variant_list[4] == 'INDEL':
                in_locus, converted_locus = translate_locus(variant_list[0], variant_list[1], variant_list[2], variant_list[3], locus, tile_position_int, reference_tile_lengths)
            else:
                in_locus, converted_locus = translate_locus(variant_list[0], variant_list[1], variant_list[2], str(int(variant_list[3])+1), locus, tile_position_int, reference_tile_lengths)
            if in_locus:
                start_tile_pos, start_int, end_tile_pos, end_int = converted_locus
                type_variant = variant_list[4]
                rest = string.join(variant_list[4:])
                if type_variant == 'INDEL':
                    start = int(variant_list[5])
                    ref_seq = variant_list[6].upper()
                    var_seq = variant_list[8].upper()
                    if ref_seq == '-':
                        end = start
                    else:
                        end = start+len(ref_seq)
                    variant = (start_tile_pos, start_int, end_tile_pos, end_int, ref_seq, var_seq)
                    if int(variant_list[3]) - int(variant_list[2]) != end-start:
                        print "----------------------------------"
                        print "Mismatching hg19 and tile lengths for indel"
                        print "Path:", PATH
                        print "Tile id:", hex(tile_variant_id)
                        print "Variant causing trouble:", variant, (start, end, type_variant)
                        raise Exception("Mismatching hg19 and tile lengths for indel")
                else:
                    var_seq = variant_list[5].upper()
                    start = int(variant_list[6])
                    length = int(variant_list[7])
                    ref_seq = get_reference_seq(reference_seq, variant_list[0], variant_list[1], variant_list[2], length, locus)
                    indexing_var_seq = whole_variant_seq[start:start+length].upper()
                    if len(ref_seq) != len(var_seq):
                        print "----------------------------------"
                        print "Wrong length: reference sequence and variant sequence are not equal for SNP or SUB"
                        print "Path:", PATH
                        print "Tile id:", hex(tile_variant_id)
                        print "Ref length, variant seq, ref_seq, read-in note:", len(reference_seq), var_seq, ref_seq, note
                        print "All notes:", notes
                    assert len(ref_seq) == len(var_seq), "Wrong length: reference sequence and variant sequence are not equal for SNP or SUB"
                    if var_seq != indexing_var_seq:
                        print "----------------------------------"
                        print "Reported variant sequence and looked-up variant sequence are not equal for SNP or SUB"
                        print "Path:", PATH
                        print "Tile id:", hex(tile_variant_id)
                        print "Ref length, variant seq, ref_seq, read-in note:", len(reference_seq), var_seq, indexing_var_seq, ref_seq, note
                        print "All notes:", notes
                    assert var_seq == indexing_var_seq, "Reported variant sequence and looked-up variant sequence are not equal for SNP or SUB"
                    end = start+length
                    variant = (start_tile_pos, start_int, end_tile_pos, end_int, ref_seq, var_seq)
                    if int(variant_list[3]) - int(variant_list[2]) != end-start-1:
                        print "----------------------------------"
                        print "Mismatching hg19 and tile lengths for SNP/SUB ... attempting to fix ..."
                        print "Path:", PATH
                        print "Tile id:", hex(tile_variant_id)
                        print "Variant making trouble:", variant, (start, end, type_variant)
                        in_locus, converted_locus = translate_locus(variant_list[0], variant_list[1], variant_list[2], str(int(variant_list[2])+end-start-1), locus, tile_position_int, reference_tile_lengths)
                        assert in_locus, "Trying to change the length resulted in the SUB/SNP extending over given locus"
                        start_tile_pos, start_int, end_tile_pos, end_int = converted_locus
                        variant = (start_tile_pos, start_int, end_tile_pos, end_int, ref_seq, var_seq)
                        print "Changed to:", variant, (start, end, type_variant)

                if variant in genome_variants:
                    pass
                    #Happens when multiple tiles are squashed together
                    print "----------------------------------"
                    print "Variant already in genome variants"
                    print "Path:", PATH
                    print "Tile id:", hex(tile_variant_id),
                    print "Variant making trouble:", variant
                    print "Current GenomeVariants:", genome_variants
                    print "Read from FJ:", notes
                else:
                    genome_variants[variant] = (start, end, type_variant)

    if len(gff_notes) != len(genome_variants):
        print "----------------------------------"
        print "Length of gff_notes and genome_variants do not match"
        print "Path:", PATH
        print "Tile id:", hex(tile_variant_id)
        print "Gff notes:", gff_notes
        print "Available variants:", genome_variants
        print "All notes:", notes
        skip = True
    if skip:
        return genome_variants_at_position, curr_genome_variant_id, wellSequenced, isPhaseA
    assert len(gff_notes) == len(genome_variants), "Expects same length of gff_notes and genome_variants"
    for gff_variant in gff_notes:
        matched = False
        for variant in genome_variants:
            translation = genome_variants[variant]
            if variant == gff_variant:
                matched_genome_variants.append(variant)
                assert not matched, "Expects a one-to-one corresponding GenomeVariant for each gfftag, not multiple GenomeVariants per gfftag"
                matched = True
                #Check if GenomeVariant already exists
                if variant in genome_variants_at_position:
                    #if so, add the connection to translation_filename
                    out.start_new_file(translation_filename)
                    write_line([translation[0], translation[1], genome_variants_at_position[variant], tile_variant_id], out)
                else:
                    #Otherwise add the connection and the GenomeVariant
                    genome_variants_at_position[variant] = curr_genome_variant_id
                    start_tile_pos, start_int, end_tile_pos, end_int, ref_seq, var_seq = variant
                    aliases = gff_notes[gff_variant][0]
                    info = gff_notes[gff_variant][1]
                    out.start_new_file(translation_filename)
                    write_line([translation[0], translation[1], curr_genome_variant_id, tile_variant_id], out)
                    out.start_new_file(genome_variant_filename)
                    #id, start_tile_position, start_increment, end_increment, end_tile_position, names, reference_bases, alternate_bases, info, created, last_modified
                    if len(aliases) == 0:
                        aliases_to_write = ''
                    else:
                        aliases_to_write = '"'+string.join(aliases, '\t')+'\t"'
                    write_line([curr_genome_variant_id, start_tile_pos, start_int, end_tile_pos, end_int, aliases_to_write,
                                ref_seq, var_seq, '"'+psql_parsable_json_dump(info)+'"', now, now], out)
                    curr_genome_variant_id += 1

        if not matched:
            print "----------------------------------"
            print "Expects a corresponding GenomeVariant for each gfftag: a gfftag is hanging"
            print "Path:", PATH
            print "Tile_id:", hex(tile_variant_id)
            print "Hanging gfftag:", gff_variant, gff_notes[gff_variant]
            print "Possible GenomeVariants:", genome_variants
            print "From FJ:", notes
        #assert matched, "Expects a corresponding GenomeVariant for each gfftag"
    for variant in genome_variants:
        translation = genome_variants[variant]
        if variant not in matched_genome_variants:
            print "----------------------------------"
            print "Expects a corresponding GenomeVariant for each gfftag: a GenomeVariant is hanging"
            print "Path:", PATH
            print "Tile id:", hex(tile_variant_id)
            print "Trouble-making variant:", variant, genome_variants[variant]
            print "Possible gfftags:", gff_notes
            print "Read from FJ:", notes
            #Check: does this GenomeVariant already exist?
            if variant in genome_variants_at_position:
                #if so, add the connection to genomevarianttranslation
                out.start_new_file(translation_filename)
                write_line([translation[0], translation[1], genome_variants_at_position[variant], tile_variant_id], out)
            else:
                #otherwise, add the connection and the variant
                genome_variants_at_position[variant] = curr_genome_variant_id
                start_tile_pos, start_int, end_tile_pos, end_int, ref_seq, var_seq = variant
                out.start_new_file(translation_filename)
                write_line([translation[0], translation[1], curr_genome_variant_id, tile_variant_id], out)
                out.start_new_file(genome_variant_filename)
                write_line([curr_genome_variant_id, start_tile_pos, start_int, end_tile_pos, end_int, '',
                            ref_seq, var_seq, '"{}"', now, now], out)
                curr_genome_variant_id += 1

    return genome_variants_at_position, curr_genome_variant_id, wellSequenced, isPhaseA

def get_reference_seq(reference_seq, assembly, chrom, start, length, locus):
    if assembly == 'hg19':
        if 19 != locus[0]:
            return False
    else:
        raise Exception("Did not recognize assembly")
    if chrom in CHR_CHOICES:
        if CHR_CHOICES[chrom] != locus[1]:
            return False
    else:
        if 26 != locus[1] or chrom != locus[4]:
            return False
    start = max([0, eval(start)])
    tile_start = start - locus[2]
    return reference_seq[tile_start:tile_start+length].upper()

def writeHuman(isPhaseA, isWellSequenced, int_to_write, num_to_extend=1):
    if not isWellSequenced:
        int_to_write = -1
    if isPhaseA:
        return ([int_to_write]*num_to_extend, [])
    else:
        return ([], [int_to_write]*num_to_extend)

def writeTile(reference_sequence_lengths, notes, toSaveData, popul_tilevars_at_position, population_locus, possible_variants, genome_variants_in_path, curr_genome_variant_id,
              genome_variant_filename, translation_filename, tilevariant_filename, out):
    #Append csv statements
    # things to add:
    #   for tile_library_tilevariant: tile_variant_name, variant_value, length, md5sum, created, last_modified, sequence, start_tag, end_tag, tile_id, (population)
    #       start_tag and end_tag only if they differ from the reference (from tags[tile_id])
    #Add only if tilevariant isn't present

    tile_hex = toSaveData['tilename']
    tile_int = int(tile_hex, 16)
    #Check if we have the tile_variant in current database
    for index, variant in enumerate(popul_tilevars_at_position):
        if toSaveData['md5sum'] == variant[1]:
            wellSequenced, isPhaseA = readNotesEfficiently(notes)
            variant_hex = hex(int(variant[0])).lstrip('0x').zfill(12)[9:]
            if toSaveData['seedTileLength'] == 1:
                phaseA, phaseB = writeHuman(isPhaseA, wellSequenced, int(variant_hex,16)) #Write person variant
            else:
                phaseA, phaseB = writeHuman(isPhaseA, wellSequenced, int(tile_hex[5:]+variant_hex,16), num_to_extend=toSaveData['seedTileLength'])
            #Tell caller this tilevariant is in the database, which index in the database it's in, and what to add to phaseA and phaseB
            return "database", index, phaseA, phaseB

    #Not currently in the database, so might be in current files
    #Modify current files
    #Do we have anything at this position in the current files to write?
    for index, tile_variant_int, md5sum in possible_variants:
        if toSaveData['md5sum'] == md5sum:
            wellSequenced, isPhaseA = readNotesEfficiently(notes)
            variant_hex = hex(int(tile_variant_int)).lstrip('0x').zfill(12)[9:]
            if toSaveData['seedTileLength'] == 1:
                phaseA, phaseB = writeHuman(isPhaseA, wellSequenced, int(variant_hex,16)) #Write person variant
            else:
                phaseA, phaseB = writeHuman(isPhaseA, wellSequenced, int(tile_hex[5:]+variant_hex,16), num_to_extend=toSaveData['seedTileLength'])
            #Tell caller this tilevariant is in the current list, which index in the list it's in, and what to add to phaseA and phaseB
            return "modified current", index, phaseA, phaseB
    #Add a new variant
    varname = hex(len(popul_tilevars_at_position) + len(possible_variants)).lstrip('0x').zfill(3)
    tilevarname = int(tile_hex+varname, 16)
    check_locus = (toSaveData['assembly'], toSaveData['chromosome'], toSaveData['locus_begin'], toSaveData['locus_end'], toSaveData['chrom_name'])
    assert population_locus == check_locus, "Locus does not align"
    if toSaveData['seedTileLength'] == 1:
        genome_variants_in_path, curr_genome_variant_id, wellSequenced, isPhaseA = readNotes(notes, tilevarname, tile_int, reference_sequence_lengths,
                                                                                             genome_variants_in_path,
                                                                                             curr_genome_variant_id, toSaveData['reference_seq'], toSaveData['sequence'],
                                                                                             population_locus, genome_variant_filename, translation_filename, out)
        phaseA, phaseB = writeHuman(isPhaseA, wellSequenced, int(varname,16)) #Write person variant
    else:
        genome_variants_in_path, curr_genome_variant_id, wellSequenced, isPhaseA = readNotes(notes, tilevarname, tile_int, reference_sequence_lengths,
                                                                                             genome_variants_in_path,
                                                                                             curr_genome_variant_id, toSaveData['reference_seq'], toSaveData['sequence'],
                                                                                             population_locus, genome_variant_filename, translation_filename, out)
        phaseA, phaseB = writeHuman(isPhaseA, wellSequenced, int(tile_hex[5:]+varname,16), num_to_extend=toSaveData['seedTileLength'])

    now = str(datetime.datetime.now())
    out.start_new_file(tilevariant_filename)
    write_line([tilevarname, int(varname,16), toSaveData['length'], toSaveData['md5sum'], now, now, toSaveData['sequence'],
                toSaveData['start_seq'], toSaveData['end_seq'], tile_int, toSaveData['seedTileLength']], out)
    return "new current", phaseA, phaseB, genome_variants_in_path, curr_genome_variant_id, [tilevarname, toSaveData['md5sum'], 1]
