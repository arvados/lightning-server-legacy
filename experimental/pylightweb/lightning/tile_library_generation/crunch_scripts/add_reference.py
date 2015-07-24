#!/usr/bin/env python
"""
Purpose: Create reference library

Inputs:
  Required
    'input' : Collection of reference FASTJ files (can be gzipped if need be) (Currently only supports 1 reference and version). If the files are not named by
              hex path identifiers (00a.fj), provide 'filename-to-path-conversion'.
        path.fj[.gz]
        path.fj[.gz]
        ...
    'version' : The version used to generate the callset FASTJ files (DEFAULT 0)
    'settings' : file defining settings for the lightning server

  Optional
    'filename-to-path-conversion' : Json-formatted file (loaded with json.load()) that provides a mapping between filenames and hex path identifiers
    'accepted-paths' : Json-formatted text (list of lists) used to specify which paths should be converted to library format. By default, all paths in 'input' are
                       converted. Path bounds are 0-indexed and the upper path is exclusive. If a path is specified here, but is not in 'input', it will not be
                       written.
                       Ex: [ ["000","002"], ["00f","014"]] will result in paths 000, 001, 00f, 010, 011, 012, and 013 being converted to library format.

Outputs:
    library/
        path/
            library.csv (meant for generating future libraries)
            tile.csv (meant for loading into postgres) (tile_position_int, is_start_of_path, is_end_of_path, start_tag, end_tag, created)
            tilelocusannotation.csv (meant for loading into postgres) (assembly_int, chromosome_int, alternate_chromosome_name, start_int, end_int, tile_position_id, tile_variant_value)
            tilevariant.csv (meant for loading into postgres) (tile_variant_int, tile_id, num_positions_spanned, variant_value, length, md5sum, created, last_modified, sequence, start_tag, end_tag)
            log.txt (meant for debugging/statistics purposes)

Currently does not output a lanterntranslator file for postgres. That might be a final step after everything has been generated
"""
import arvados      # Import the Arvados sdk module
import sys          # used for learning size of things
import json         # used to load conversion from 'chr10_band0_s0_e3000000' -> '1c6'
import re           # used for error checking
import gzip         # used to open gzipped files
import imp          # used to import python module
from fastj_objects import TileLibrary, TileObject
from validators import validate_settings

# Read constants for entire job
########################################################################################################################
# NAME_TO_PATH converts filename to path if necessary
NAME_TO_PATH = None
ACCEPTED_PATHS = None

known_parameters = arvados.current_job()['script_parameters']

settings = imp.load_source('settings', arvados.get_job_param_mount('settings'))

validate_settings(settings)

CURR_VERSION_HEX_STR = known_parameters['version']
assert re.match('^[0-9a-f]{%i}$' % (settings.NUM_HEX_DIGITS_FOR_VERSION), CURR_VERSION_HEX_STR) != None, \
    "'version' input did not define a correct version hex string (it does not match '^[0-9a-f]{%i}$')" % (settings.NUM_HEX_DIGITS_FOR_VERSION)

if known_parameters['filename-to-path-conversion'] != None:
    with open(arvados.get_job_param_mount('filename-to-path-conversion'), 'r') as json_file:
        NAME_TO_PATH = json.load(json_file)

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
arvados.job_setup.one_task_per_input_file(if_sequence=0, and_end_task=True, input_as_path=True)

# Get the reference fastj file (and its collection)
reference_fastj_path = arvados.get_task_param_mount('input')
reference_fastj_name = reference_fastj_path.split('/')[-1].split('.')[0]

#Get the global path and check it is a valid path
if reference_fastj_name.startswith('chr'):
    assert NAME_TO_PATH != None, "Requires 'filename-to-path-conversion' file input to be given or the input collection FASTJ to be named after paths"
    assert reference_fastj_name in NAME_TO_PATH, "'filename-to-path-conversion' file input does not define path hex string for %s" % (reference_fastj_name)
    GLOBAL_PATH_HEX_STR = NAME_TO_PATH[reference_fastj_name]
    assert re.match('^[0-9a-f]{%i}$' % (settings.NUM_HEX_DIGITS_FOR_PATH), GLOBAL_PATH_HEX_STR) != None, \
        "'filename-to-path-conversion' file input did not define an appropriate hex string (it does not match '^[0-9a-f]{%i}$') for FASTJ name %s" % (settings.NUM_HEX_DIGITS_FOR_PATH, reference_fastj_name)
else:
    GLOBAL_PATH_HEX_STR = reference_fastj_name
    assert re.match('^[0-9a-f]{%i}$' % (settings.NUM_HEX_DIGITS_FOR_PATH), GLOBAL_PATH_HEX_STR) != None, \
        "reference FASTJ input did not define an appropriate hex string (it does not match '^[0-9a-f]{%i}$') for FASTJ name %s" % (settings.NUM_HEX_DIGITS_FOR_PATH, reference_fastj_name)

#Exit the job if the path is outside the bounds of the accepted paths
if ACCEPTED_PATHS != None:
    time_to_exit = True
    for lower_path, upper_path in ACCEPTED_PATHS:
        if int(lower_path, 16) <= int(GLOBAL_PATH_HEX_STR, 16) < int(upper_path, 16):
            time_to_exit = False
    if time_to_exit:
        arvados.current_task().set_output(None)
        exit(0)

#Set-up collection and files to write out to
out = arvados.collection.Collection()

logging_file_handle = out.open('library/'+GLOBAL_PATH_HEX_STR+'/log.txt', 'w')
library_file_handle = out.open('library/'+GLOBAL_PATH_HEX_STR+'/library.csv', 'w')
tile_file_handle = out.open('library/'+GLOBAL_PATH_HEX_STR+'/tile.csv', 'w')
locus_annotation_file_handle = out.open('library/'+GLOBAL_PATH_HEX_STR+'/tilelocusannotation.csv', 'w')
tile_variant_file_handle = out.open('library/'+GLOBAL_PATH_HEX_STR+'/tilevariant.csv', 'w')

#open the reference FASTJ file
if reference_fastj_path.endswith('.gz'):
    reference_fastj_file_handle = gzip.open(reference_fastj_path, 'r')
else:
    reference_fastj_file_handle = open(reference_fastj_path, 'r')


tile_library = TileLibrary(CURR_VERSION_HEX_STR, GLOBAL_PATH_HEX_STR)

logging_file_handle.write("----------------------------------\n")
logging_file_handle.write("Path %s beginning size summary\n" % (str(GLOBAL_PATH_HEX_STR)))
positions, variants = tile_library.get_size()
logging_file_handle.write("tile_library number of positions: %i\n" % (positions))
logging_file_handle.write("tile_library number of variants: %i\n" % (variants))


num_fastj_entries_parsed = 0
for line in reference_fastj_file_handle:
    if (line.startswith('>{') or line.startswith('> {')) and num_fastj_entries_parsed > 0:
        #Need to save the previous FASTJ entry
        curr_tile_object.add_sequence(curr_sequence)
        is_known_variant, variant_value = tile_library.extend_library(curr_tile_object, population_incr=0) #Don't add to population - this is reference
        assert not is_known_variant, "Should always be a new variant, since this is reference"
        curr_tile_object.add_variant_value(variant_value)
        curr_tile_object.check_and_write_tile_position(tile_file_handle)
        curr_tile_object.check_and_write_locus(settings.CHR_PATH_LENGTHS, locus_annotation_file_handle)
        curr_tile_object.check_and_write_tile_variant(tile_variant_file_handle)
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
            settings.CHR_OTHER
        )
    elif line != '\n':
        curr_sequence += line.strip()
#Need to save the previous FASTJ entry
curr_tile_object.add_sequence(curr_sequence)
is_known_variant, variant_value = tile_library.extend_library(curr_tile_object, population_incr=0) #Don't add to population - this is reference
assert not is_known_variant, "Should always be a new variant, since this is reference"
curr_tile_object.add_variant_value(variant_value)
curr_tile_object.check_and_write_tile_position(tile_file_handle)
curr_tile_object.check_and_write_locus(settings.CHR_PATH_LENGTHS, locus_annotation_file_handle)
curr_tile_object.check_and_write_tile_variant(tile_variant_file_handle)

reference_fastj_file_handle.close()

logging_file_handle.write("----------------------------------\n")
logging_file_handle.write("Path %s end size summary\n" % (str(GLOBAL_PATH_HEX_STR)))
positions, variants = tile_library.get_size()
logging_file_handle.write("tile_library number of positions: %i\n" % (positions))
logging_file_handle.write("tile_library number of variants: %i\n" % (variants))

tile_library.write_library(settings.NUM_HEX_DIGITS_FOR_VARIANT_VALUE, library_file_handle)

logging_file_handle.close()
library_file_handle.close()
tile_file_handle.close()
locus_annotation_file_handle.close()
tile_variant_file_handle.close()

task_output = out.save_new(create_collection_record=False)
arvados.current_task().set_output(task_output)

###########################################################################################################################################
