#!/usr/bin/env python

#Add population to library
import arvados      # Import the Arvados sdk module
import logging
import sys          # used for learning size of

NUM_RETRIES = 12

LOG_NAME = 'read_fj.log'
logging.basicConfig(filename=LOG_NAME,level=logging.DEBUG)

def log_sizes():
    global GLOBAL_PATH, CURR_TILEVARS, HG19_GENOME_VARIANTS, TILEVARS_TO_WRITE, HUMAN_SEQ_PHASEA, HUMAN_SEQ_PHASEB
    logging.debug("Memory use statistics for path %s:", GLOBAL_PATH)
    logging.debug("CURR_TILEVARS: %f kB", sys.getsizeof(CURR_TILEVARS)/1000.)
    logging.debug("HG19_GENOME_VAR: %f kB", sys.getsizeof(HG19_GENOME_VARIANTS)/1000.)
    logging.debug("TILEVARS_TO_WRITE: %f kB", sys.getsizeof(TILEVARS_TO_WRITE)/1000.)
    logging.debug("HUMAN_SEQ_PHASEA: %f kB", HUMAN_SEQ_PHASEA.nbytes/1000.)
    logging.debug("HUMAN_SEQ_PHASEB: %f kB", HUMAN_SEQ_PHASEB.nbytes/1000.)


def update_variables(tile_int, notes, toSaveData, out):
    global REFERENCE_SEQ_LOOKUP, POPUL_LOCI, POPUL_TILEVARS, CURR_TILEVARS, HG19_GENOME_VARIANTS, GENOME_VARIANT_ID, TILEVARS_TO_WRITE, HUMAN_SEQ_PHASEA, HUMAN_SEQ_PHASEB
    global GENOME_VARIANT_FILE, GENOME_TRANSLATION_FILE, NEW_TILEVARIANT_FILE
    num_tiles_spanned = toSaveData['seedTileLength']
    new_md5sum = hashlib.md5(toSaveData['sequence']).hexdigest()
    if new_md5sum != toSaveData['md5sum']:
        logging.warning("Tile %s sequence md5sum is different from actual md5sum of sequence. Changing from %s to %s", toSaveData['tilename'], toSaveData['md5sum'], new_md5sum)
        toSaveData['md5sum'] = new_md5sum
    if tile_int not in CURR_TILEVARS:
        possible_variants = []
    else:
        possible_variants = [(index, TILEVARS_TO_WRITE[index][0], TILEVARS_TO_WRITE[index][1]) for index in CURR_TILEVARS[tile_int]]
    if num_tiles_spanned > 1:
        popul_locus_beg = POPUL_LOCI[tile_int]
        popul_locus_end = POPUL_LOCI[tile_int+num_tiles_spanned-1]
        assert popul_locus_beg[0] == popul_locus_end[0], "TileVariant supposedly spans a different assembly for a spanning tile"
        assert popul_locus_beg[1] == popul_locus_end[1], "TileVariant supposedly spans a chromosome for a spanning tile"
        assert popul_locus_beg[4] == popul_locus_end[4], "TileVariant supposedly spans chromosome for a spanning tile"
        locus_to_pass = (popul_locus_beg[0], popul_locus_beg[1], popul_locus_beg[2], popul_locus_end[3], popul_locus_beg[4])
    else:
        locus_to_pass = POPUL_LOCI[tile_int]
    ref_tile_lengths = [len(REFERENCE_SEQ_LOOKUP[tile_int+i]) for i in range(num_tiles_spanned)]
    retval = fns.writeTile(ref_tile_lengths, notes, toSaveData, POPUL_TILEVARS[tile_int], locus_to_pass, possible_variants,
                           HG19_GENOME_VARIANTS, GENOME_VARIANT_ID, GENOME_VARIANT_FILE, GENOME_TRANSLATION_FILE, NEW_TILEVARIANT_FILE, out)
    if retval[0] == "database":
        POPUL_TILEVARS[tile_int][retval[1]][2] += 1
        HUMAN_SEQ_PHASEA.extend(retval[2])
        HUMAN_SEQ_PHASEB.extend(retval[3])
    elif retval[0] == "modified current":
        TILEVARS_TO_WRITE[retval[1]][2] += 1
        HUMAN_SEQ_PHASEA.extend(retval[2])
        HUMAN_SEQ_PHASEB.extend(retval[3])
    else:
        if tile_int not in CURR_TILEVARS:
            CURR_TILEVARS[tile_int] = [len(TILEVARS_TO_WRITE)]
        else:
            CURR_TILEVARS[tile_int].append(len(TILEVARS_TO_WRITE))
        ignore, phaseA, phaseB, HG19_GENOME_VARIANTS, GENOME_VARIANT_ID, var_to_append = retval
        HUMAN_SEQ_PHASEA.extend(phaseA)
        HUMAN_SEQ_PHASEB.extend(phaseB)
        TILEVARS_TO_WRITE.append(var_to_append)
    return True

########################################################################################################################
#Set-up files to write out to

GENOME_VARIANT_FILE = 'genomevariant.csv'
GENOME_TRANSLATION_FILE = 'genomevarianttranslation.csv'
NEW_TILEVARIANT_FILE = 'tilevariant.csv'

# Write a new collection as output
out = arvados.CollectionWriter(num_retries=NUM_RETRIES)

#Parallelize the job according to paths and paths only => use library collection as the main input!
arvados.job_setup.one_task_per_input_file(if_sequence=0, and_end_task=True, input_as_path=True)

# Get object representing the current task
this_task = arvados.current_task()

# Get the input file for the task
input_id, library_input_path = this_task['parameters']['input'].split('/', 1)

#open the input collection (containing library files, tilelocusannotation.csv, tilevariant.csv, and possibly genomevariant.csv)
library_input_collection = arvados.CollectionReader(input_id)

#only do work if we are given a library file as input!
if library_input_path.endswith('_library.csv'):
    GLOBAL_PATH = library_input_path.split("/")[-1].split('_')[0]
    with library_input_collection.open(library_input_path) as input_file:

    LOCI_INPUT_FILE = string.join(LIBRARY_INPUT_FILE.split('/')[:-1], '/')+'/tilelocusannotation.csv'
    SEQUENCE_INPUT_FILE = string.join(LIBRARY_INPUT_FILE.split('/')[:-1], '/')+'/tilevariant.csv'

    POPUL_LOCI, REFERENCE_SEQ_LOOKUP, POPUL_TILEVARS, CURR_TILEVARS, HG19_GENOME_VARIANTS, GENOME_VARIANT_ID = fns.setup(LIBRARY_INPUT_FILE, LOCI_INPUT_FILE,
                                                                                                                         SEQUENCE_INPUT_FILE, GLOBAL_PATH, genome_variants_file=None)

    logging.debug("Non-changing memory use statistics for path %s:", GLOBAL_PATH)
    logging.debug("REF_SEQ_LOOKUP: %f kB", sys.getsizeof(REFERENCE_SEQ_LOOKUP)/1000.)
    logging.debug("POPUL_TILEVARS: %f kB", sys.getsizeof(POPUL_TILEVARS)/1000.)
    logging.debug("POPUL_LOCI: %f kB", sys.getsizeof(POPUL_LOCI)/1000.)

    TILEVARS_TO_WRITE = []

    ### Reading human collection ###
    human_collection = arvados.current_job()['script_parameters']['humans']
    cr = arvados.CollectionReader(human_collection, num_retries=NUM_RETRIES)
    for NUM_HUMANS_PARSED, s in enumerate(cr.all_streams()):
        if 'chr13_chr17.reported.fj' in s.name():
            HUMAN_NAME = s.name().lstrip('./').rstrip('/chr13_chr17.reported.fj')
            HUMAN_SEQ_PHASEA = []
            HUMAN_SEQ_PHASEB = []
            for f in s.all_files():
                if str(fns.FILENAME_TO_PATH[f.name().rstrip('.gz')]) == GLOBAL_PATH:
                    HUMAN_FILE = os.path.join(os.environ['TASK_KEEPMOUNT'], human_collection, s.name(), f.name())
                    with fns.copen(HUMAN_FILE, 'r') as human_file_handle:
                        #print "----------------------------------"
                        print NUM_HUMANS_PARSED/2.0, HUMAN_NAME, GLOBAL_PATH#, "Beginning Size summary"
                        #print_sizes()
########################################################################################################################
                        NUM_LINES_PARSED = 0
                        for line in human_file_handle:
                            if (line[:2] == '>{' or line[:3] == '> {') and NUM_LINES_PARSED > 0:
                                tile_int = int(toSaveData['tilename'], 16)
                                update_variables(tile_int, loadedData[u'notes'], toSaveData, out)
                            if (line[:2] == '>{' or line[:3] == '> {'):
                                NUM_LINES_PARSED += 1
                                toSaveData = {}
                                loadedData = json.loads(line[1:])
                                tilename = str(loadedData[u'tileID'])
                                path, version, tile, variant = tilename.split('.')
                                assert path == GLOBAL_PATH
                                tile = tile.zfill(4)
                                tile_id = int(path+version+tile, 16)
                                toSaveData['start_tag'] = str(loadedData[u'startTag'])
                                toSaveData['end_tag'] = str(loadedData[u'endTag'])
                                toSaveData['start_seq'] = ""
                                toSaveData['end_seq'] = ""
                                #Will only need to add 'start_tag' and 'end_tag' when using non-reference data which has SNPs on tags
                                if u'startSeq' in loadedData:
                                    if str(loadedData[u'startTag']).lower() != str(loadedData[u'startSeq']).lower():
                                        toSaveData['start_seq'] = str(loadedData[u'startSeq'])
                                    if str(loadedData[u'endTag']).lower() != str(loadedData[u'endSeq']).lower():
                                        toSaveData['end_seq'] = str(loadedData[u'endSeq'])
                                toSaveData['length'] = loadedData[u'n']
                                toSaveData['sequence'] = ''
                                toSaveData['md5sum'] = str(loadedData[u'md5sum'])

                                locus = str(loadedData[u'locus'][0][u'build'])
                                locus = locus.split()
                                if locus[0] == 'hg19':
                                    toSaveData['assembly'] = 19
                                if locus[1] in fns.CHR_CHOICES:
                                    toSaveData['chromosome'] = fns.CHR_CHOICES[locus[1]]
                                    toSaveData['chrom_name'] = ""
                                else:
                                    toSaveData['chromosome'] = 26
                                    toSaveData['chrom_name'] = locus[1]

                                if u'seedTileLength' in loadedData:
                                    toSaveData['seedTileLength'] = int(loadedData[u'seedTileLength'])
                                    if toSaveData['seedTileLength'] > 1:
                                        check_loci_beg = POPUL_LOCI[tile_id]
                                        check_loci_end = POPUL_LOCI[tile_id+toSaveData['seedTileLength']-1]
                                        assert check_loci_beg[0] == check_loci_end[0], "Loci need to be in the same assembly"
                                        assert check_loci_beg[0] == toSaveData['assembly'], "Loci need to be in the same assembly"
                                        assert check_loci_beg[1] == check_loci_end[1], "Loci need to be in the same chromosome"
                                        assert check_loci_beg[1] == toSaveData['chromosome'], "Loci need to be in the same chromosome"
                                        assert check_loci_beg[4] == check_loci_end[4], "Loci need to be in the same chromosome"
                                        assert check_loci_beg[4] == toSaveData['chrom_name'], "Loci need to be in the same chromosome"
                                        toSaveData['locus_begin'] = check_loci_beg[2]
                                        toSaveData['locus_end'] = check_loci_end[3]
                                        new_ref_seq = ""
                                        for i in range(toSaveData['seedTileLength']):
                                            if i == 0:
                                                new_ref_seq += REFERENCE_SEQ_LOOKUP[tile_id]
                                            else:
                                                new_ref_seq += REFERENCE_SEQ_LOOKUP[tile_id+i][24:]
                                        toSaveData['reference_seq'] = new_ref_seq
                                    else:
                                        if toSaveData['start_seq'] != "" and toSaveData['start_seq'] != "........................" and "N" not in toSaveData['start_seq'].upper() and len(toSaveData['start_seq']) == len(toSaveData['start_tag']):
                                            print hex(tile_id), toSaveData['start_seq'].upper(), toSaveData['start_tag'].upper()
                                        assert toSaveData['start_seq'] == "" or toSaveData['start_seq'] == "........................" or "N" in toSaveData['start_seq'].upper() or len(toSaveData['start_seq']) != len(toSaveData['start_tag']), "Should be no mutations on start tag"
                                        if toSaveData['end_seq'] != "" and toSaveData['end_seq'] != "........................" and "N" not in toSaveData['end_seq'].upper() and len(toSaveData['end_seq']) == len(toSaveData['end_tag']):
                                            print hex(tile_id), toSaveData['end_seq'].upper(), toSaveData['end_tag'].upper()
                                        assert toSaveData['end_seq'] == "" or toSaveData['end_seq'] == "........................" or "N" in toSaveData['end_seq'].upper() or len(toSaveData['end_seq']) != len(toSaveData['end_tag']), "Should be no mutations on end tag"
                                        try:
                                            toSaveData['locus_begin'] = int(locus[2])
                                            toSaveData['locus_end'] = int(locus[3])
                                        except ValueError:
                                            toSaveData['locus_begin'] = int(locus[2].split('-')[0])
                                            toSaveData['locus_end'] = int(locus[3].split('+')[0])
                                        toSaveData['reference_seq'] = REFERENCE_SEQ_LOOKUP[tile_id]
                                else:
                                    toSaveData['seedTileLength'] = 1
                                    try:
                                        toSaveData['locus_begin'] = int(locus[2])
                                        toSaveData['locus_end'] = int(locus[3])
                                    except ValueError:
                                        toSaveData['locus_begin'] = int(locus[2].split('-')[0])
                                        toSaveData['locus_end'] = int(locus[3].split('+')[0])
                                    toSaveData['reference_seq'] = REFERENCE_SEQ_LOOKUP[tile_id]

                                toSaveData['tilename'] = path+version+tile
                            elif line != '\n':
                                toSaveData['sequence'] += line.strip()
                        #Write last tile
                        tile_int = int(toSaveData['tilename'], 16)
                        update_variables(tile_int, loadedData[u'notes'], toSaveData, out)
                    #print "----------------------------------"
                    #print NUM_HUMANS_PARSED/2., HUMAN_NAME, "End Size summary"
                    #print_sizes()

                    out.start_new_file(HUMAN_NAME+"/phaseA_path_"+GLOBAL_PATH+".npy")
                    np.save(out, np.array(HUMAN_SEQ_PHASEA, dtype=np.uint32))

                    out.start_new_file(HUMAN_NAME+"/phaseB_path_"+GLOBAL_PATH+".npy")
                    np.save(out, np.array(HUMAN_SEQ_PHASEB, dtype=np.uint32))

    out.start_new_file(GLOBAL_PATH+"_library.csv")
    #tilevarname, popul, md5sum
    #Need to write out the ones already in the database and the we created
    for tiles in POPUL_TILEVARS:
        for variant in POPUL_TILEVARS[tiles]:
            tile_variant_name, md5sum, popul = variant
            write_to_final_library(tile_variant_name, md5sum, popul, out)
    for l in TILEVARS_TO_WRITE:
        tile_variant_name, md5sum, population_size = l
        write_to_final_library(tile_variant_name, md5sum, population_size, out)

##else:
##    print LIBRARY_INPUT_FILE.split('/')[-1]
##    with fns.copen(LIBRARY_INPUT_FILE, 'r') as inp:
##        name = LIBRARY_INPUT_FILE.split('/')[-1]
##        if 'path_lengths.txt' not in name:
##            #don't pass on path_lengths.txt
##            out.start_new_file("reference_"+name)
##            for line in inp:
##                out.write(line)

out.write_file(LOG_NAME)
# Commit the output to keep
output_id = out.finish()

# Set the output for this task to the Keep id
this_task.set_output(output_id)

# Done!
