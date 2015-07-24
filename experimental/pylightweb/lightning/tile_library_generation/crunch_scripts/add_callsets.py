#!/usr/bin/env python
"""
Purpose: Add callsets to library

Inputs:
  Required
    'input' : Collection output by add-reference or add-callsets (Currently only supports 1 reference and version). Will contain some directory substructure of the following form
        library/
            path/
                library.csv (meant for generating future libraries)
                tilevariant.csv (Not read, meant for loading into postgres) (tile_variant_int, tile_id, num_positions_spanned, variant_value, length, md5sum, created, last_modified, sequence, start_tag, end_tag)
                log.txt (Not read, meant for debugging/statistics purposes)
    'callsets' : Collection containing the FASTJ files for each callset to add. If the FASTJ files for each callset are not named by hex path identifiers (00a.fj),
                 provide 'filename-to-path-conversion'. All paths in 'input' (or defined by 'accepted-paths' and in 'input', if applicable) are expected to have a
                 FASTJ file associated with them.
        callset-name/
            path.fj[.gz]
            path.fj[.gz]
            ...
        callset-name/
            ...
    'version' : The version used to generate the callset FASTJ files (DEFAULT 00)
    'settings' : file defining settings for the lightning server
    'make-numpy' : Boolean specifying whether numpy-formatted cgf files should be created (DEFAULT True)
  Optional
    'accepted-paths' : Json-formatted text (list of lists) used to specify which paths should be converted to library format. By default, all paths in 'input' are
                       converted. Path bounds are 0-indexed and the upper path is exclusive. If a path is specified here, but is not in 'input', it will not be
                       written.
                       Ex: [ ["000","002"], ["00f","014"]] will result in paths 000, 001, 00f, 010, 011, 012, and 013 being converted to library format.

Outputs:
    library/
        path/
            library.csv (meant for generating future libraries)
            tilelocusannotation.csv (meant for loading into postgres) (assembly_int, chromosome_int, alternate_chromosome_name, start_int, end_int, tile_position_id, tile_variant_value)
            tilevariant.csv (meant for loading into postgres) (tile_variant_int, tile_id, num_positions_spanned, variant_value, length, md5sum, created, last_modified, sequence, start_tag, end_tag)
            log.txt (meant for debugging/statistics purposes)
    callsets/
        callset-name/
            path/
                quality_phase0.npy
                quality_phase1.npy
                ...
                phase0.npy
                phase1.npy
                ...
        callset-name/
        ...

Currently does not output a lanterntranslator file for postgres. That might be a final step after everything has been generated
"""
import arvados      # Import the Arvados sdk module
import sys          # used for learning size of things
import json         # used to load conversion from 'chr10_band0_s0_e3000000' -> '1c6'
import re           # used for error checking
import gzip         # used to open gzipped files
import imp          # used to import python module
import os
import string
import numpy as np
from fastj_objects import TileLibrary, TileObject
from fastj_functions import build_tile_library
from validators import validate_settings

# Read constants for entire job
########################################################################################################################
ACCEPTED_PATHS = None

known_parameters = arvados.current_job()['script_parameters']

settings = imp.load_source('settings', arvados.get_job_param_mount('settings'))

validate_settings(settings)

CURR_VERSION_HEX_STR = known_parameters['version']
assert re.match('^[0-9a-f]{%i}$' % (settings.NUM_HEX_DIGITS_FOR_VERSION), CURR_VERSION_HEX_STR) != None, \
    "'version' input did not define a correct version hex string (it does not match '^[0-9a-f]{%i}$')" % (settings.NUM_HEX_DIGITS_FOR_VERSION)

if known_parameters['accepted-paths'] != None:
    try:
        ACCEPTED_PATHS = json.loads(known_parameters['accepted-paths'])
    except ValueError:
        raise Exception("Unable to read 'accepted-paths' input as json input: %s" % (known_parameters['accepted-paths']))
    for lower_path, upper_path in ACCEPTED_PATHS:
        assert re.match('^[0-9a-f]{%i}$' % (settings.NUM_HEX_DIGITS_FOR_PATH), lower_path) != None, \
            "'accepted-paths' input contains an incorrect path hex string (%s) (it does not match '^[0-9a-f]{%i}$')" % (lower_path, settings.NUM_HEX_DIGITS_FOR_PATH)
        assert re.match('^[0-9a-f]{%i}$' % (settings.NUM_HEX_DIGITS_FOR_PATH), upper_path) != None, \
            "'accepted-paths' input contains an incorrect path hex string (%s) (it does not match '^[0-9a-f]{%i}$')" % (upper_path, settings.NUM_HEX_DIGITS_FOR_PATH)
        assert int(lower_path,16) < int(upper_path,16), "for each pair in 'accepted-paths', expects the first path to be less than the second"

########################################################################################################################
#Parallelize the job according to paths
#Copied from arvados.job_setup.one_task_per_input_file
def one_task_per_path(job_input, accepted_paths, if_sequence=0, and_end_task=True):
    if if_sequence != arvados.current_task()['sequence']:
        return
    api_client = arvados.api('v1')
    cr = arvados.CollectionReader(job_input, api_client=api_client)
    cr.normalize()
    for s in cr.all_streams():
        for f in s.all_files():
            #Start a job if the input file is the library.csv file
            if re.match('library/[0-9a-f]{%i}/library.csv$' % (settings.NUM_HEX_DIGITS_FOR_PATH), os.path.join(s.name().lstrip('./'), f.name())) != None:
                GLOBAL_PATH_HEX_STR = s.name().split('/')[-1]
                time_to_exit = False
                #Don't start the job if the path is outside the bounds of the accepted paths
                if accepted_paths != None:
                    time_to_exit = True
                    for lower_path, upper_path in accepted_paths:
                        if int(lower_path, 16) <= int(GLOBAL_PATH_HEX_STR, 16) < int(upper_path, 16):
                            time_to_exit = False
                if not time_to_exit:
                    task_input = os.path.join(job_input, s.name(), f.name())
                    new_task_attrs = {
                        'job_uuid': arvados.current_job()['uuid'],
                        'created_by_job_task_uuid': arvados.current_task()['uuid'],
                        'sequence': if_sequence + 1,
                        'parameters': {
                            'input':task_input,
                            'path': GLOBAL_PATH_HEX_STR
                        }
                    }
                    api_client.job_tasks().create(body=new_task_attrs).execute()
    if and_end_task:
        api_client.job_tasks().update(uuid=arvados.current_task()['uuid'], body={'success':True}).execute()
        exit(0)

one_task_per_path(known_parameters['input'], ACCEPTED_PATHS, if_sequence=0, and_end_task=True)

# Get the reference library file (and its collection)
curr_library_path = arvados.get_task_param_mount('input')
GLOBAL_PATH_HEX_STR = arvados.current_task()['parameters']['path']

library_file_handle = open(curr_library_path, 'r')

# Initialize library
tile_library = build_tile_library(
    library_file_handle,
    CURR_VERSION_HEX_STR,
    GLOBAL_PATH_HEX_STR,
    settings.NUM_HEX_DIGITS_FOR_VERSION,
    settings.NUM_HEX_DIGITS_FOR_PATH,
    settings.NUM_HEX_DIGITS_FOR_STEP,
    settings.NUM_HEX_DIGITS_FOR_VARIANT_VALUE
)

library_file_handle.close()

#Set-up collection and files to write out to
out = arvados.collection.Collection()

logging_file_handle = out.open('library/'+GLOBAL_PATH_HEX_STR+'/log.txt', 'w')
library_file_handle = out.open('library/'+GLOBAL_PATH_HEX_STR+'/library.csv', 'w')
tile_variant_file_handle = out.open('library/'+GLOBAL_PATH_HEX_STR+'/tilevariant.csv', 'w')

logging_file_handle.write("----------------------------------\n")
logging_file_handle.write("Path %s beginning size summary\n" % (str(GLOBAL_PATH_HEX_STR)))
positions, variants = tile_library.get_size()
logging_file_handle.write("tile_library number of positions: %i\n" % (positions))
logging_file_handle.write("tile_library number of variants: %i\n" % (variants))

print "Path %s, beginning. # Positions: %i. # Variants: %i" % (str(GLOBAL_PATH_HEX_STR), positions, variants)

def save_tile_object(curr_tile_object, curr_sequence, tile_library, callset_seq_phases, callset_quality_seq_phases, logging_file_handle, tile_variant_file_handle):
    #Need to save the previous FASTJ entry
    curr_tile_object.add_sequence(curr_sequence, logging_file_handle=logging_file_handle)
    is_new_variant, variant_value = tile_library.extend_library(curr_tile_object)
    #If the phases don't exist yet, will throw an error. Currently cannot dynamically grow sequences

    #Grow appropriate array for as many tiles as our current tile spans
    if curr_tile_object.seed_tile_length > 1:
        value_to_write = int(curr_tile_object.path+curr_tile_object.step,16)
    else:
        value_to_write = variant_value
    callset_seq_phases[curr_tile_object.phase].extend([value_to_write]*curr_tile_object.seed_tile_length)
    #Check if well-sequenced, and grow appropriate phase accordingly
    if curr_tile_object.well_sequenced:
        callset_quality_seq_phases[curr_tile_object.phase].extend([value_to_write]*curr_tile_object.seed_tile_length)
    else:
        callset_quality_seq_phases[curr_tile_object.phase].extend([-1]*curr_tile_object.seed_tile_length)
    #Write out variant if the variant has not been observed before
    if is_new_variant:
        curr_tile_object.add_variant_value(variant_value)
        curr_tile_object.check_and_write_tile_variant(tile_variant_file_handle)
    return tile_library, callset_seq_phases, callset_quality_seq_phases

def write_log(num_humans_parsed, callset_name, tile_library, logging_file_handle):
    logging_file_handle.write("----------------------------------\n")
    logging_file_handle.write("Parsed %i humans, Human %s\n" % (num_humans_parsed, str(callset_name)))
    positions, variants = tile_library.get_size()
    logging_file_handle.write("tile_library number of variants: %i\n" % (variants))
    print "Path %s. Human %s, (%ith human). # Positions: %i. # Variants: %i" % (str(GLOBAL_PATH_HEX_STR), str(callset_name), num_humans_parsed, variants)
    
#Open callsets path and read them into library
callsets_path = arvados.get_job_param_mount('callsets')
for num_humans_parsed, callset_name in enumerate(os.listdir(callsets_path)):
    for path_file in os.listdir(callsets_path+'/'+callset_name):
        callset_fastj_name = path_file.split('.')[0]
        assert re.match('^[0-9a-f]{%i}$' % (settings.NUM_HEX_DIGITS_FOR_PATH), callset_fastj_name) != None, \
            "callset FASTJ input did not define an appropriate hex string (it does not match '^[0-9a-f]{%i}$') for FASTJ name %s" % (
                settings.NUM_HEX_DIGITS_FOR_PATH,
                callset_fastj_name
            )
        if callset_fastj_name != GLOBAL_PATH_HEX_STR:
            continue
        #Open and read the file (since it is the correct path)
        if path_file.endswith('.gz'):
            callset_fastj_file_handle = gzip.open(os.path.join(callsets_path, callset_name, path_file), 'r')
        else:
            callset_fastj_file_handle = open(os.path.join(callsets_path, callset_name, path_file), 'r')

        callset_seq_phases = [[],[]]
        callset_quality_seq_phases = [[],[]]
        num_fastj_entries_parsed = 0
        for line in callset_fastj_file_handle:
            if (line.startswith('>{') or line.startswith('> {')) and num_fastj_entries_parsed > 0:
                tile_library, callset_seq_phases, callset_quality_seq_phases = save_tile_object(
                    curr_tile_object,
                    curr_sequence,
                    tile_library,
                    callset_seq_phases,
                    callset_quality_seq_phases,
                    logging_file_handle,
                    tile_variant_file_handle
                )
            if line.startswith('>{') or line.startswith('> {'):
                num_fastj_entries_parsed += 1
                curr_sequence = ''
                curr_tile_object = TileObject(
                    line,
                    CURR_VERSION_HEX_STR,
                    GLOBAL_PATH_HEX_STR,
                    settings.NUM_HEX_DIGITS_FOR_VERSION,
                    settings.NUM_HEX_DIGITS_FOR_PATH,
                    settings.NUM_HEX_DIGITS_FOR_STEP,
                    settings.NUM_HEX_DIGITS_FOR_VARIANT_VALUE,
                    settings.TAG_LENGTH,
                    settings.CHR_CHOICES,
                    settings.CHR_OTHER,
                    reference=False
                )
            elif line != '\n':
                curr_sequence += line.strip()
        #Need to save the previous FASTJ entry
        tile_library, callset_seq_phases, callset_quality_seq_phases = save_tile_object(
            curr_tile_object,
            curr_sequence,
            tile_library,
            callset_seq_phases,
            callset_quality_seq_phases,
            logging_file_handle,
            tile_variant_file_handle
        )
        write_log(num_humans_parsed, callset_name, tile_library, logging_file_handle)
        ##### Write out npy files! ####
        for phase, sequence in enumerate(callset_seq_phases):
            phase_file_handle = out.open("callsets/%s/%s/phase%i.npy" % (callset_name, GLOBAL_PATH_HEX_STR, phase), 'w')
            to_save = np.array(sequence, dtype=np.uint32)
            np.save(phase_file_handle, to_save)
            phase_file_handle.close()
        for phase, sequence in enumerate(callset_quality_seq_phases):
            phase_file_handle = out.open("callsets/%s/%s/quality_phase%i.npy" % (callset_name, GLOBAL_PATH_HEX_STR, phase), 'w')
            to_save = np.array(sequence, dtype=np.uint32)
            np.save(phase_file_handle, to_save)
            phase_file_handle.close()

logging_file_handle.write("----------------------------------\n")
logging_file_handle.write("Path %s end size summary\n" % (str(GLOBAL_PATH_HEX_STR)))
positions, variants = tile_library.get_size()
logging_file_handle.write("tile_library number of positions: %i\n" % (positions))
logging_file_handle.write("tile_library number of variants: %i\n" % (variants))

print "Path %s, ending. # Positions: %i. # Variants: %i" % (str(GLOBAL_PATH_HEX_STR), positions, variants)

tile_library.write_library(settings.NUM_HEX_DIGITS_FOR_VARIANT_VALUE, library_file_handle)

logging_file_handle.close()
library_file_handle.close()
tile_variant_file_handle.close()

task_output = out.save_new(create_collection_record=False)
arvados.current_task().set_output(task_output)

###########################################################################################################################################
