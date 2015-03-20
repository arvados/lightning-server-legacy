import os
import re
import string
import time
from tile_library.models import TileVariant
import tile_library.basic_functions as basic_fns
import tile_library.functions as fns

CGF_LIBRARY_COLLECTION = '/home/sguthrie/keep/by_id/ad86534233b5ef6cdf0559af8951f258+2777/'

def convert():
    with open('unmatched_cgf_strings.csv', 'w') as out:
        for dirpath, dirnames, filenames in os.walk(CGF_LIBRARY_COLLECTION):
            assert len(dirnames) == 0, "Expect flat directory structure"
            total_time = 0
            for filename in sorted(filenames):
                num_incorrect_calls = 0
                num_unmatched = 0
                num_lines = 0
                matching = re.match('([0-9a-f]{3})_library\.csv', filename)
                assert matching != None, "%s does not match expected regex of file" % (filename)
                with open(dirpath+"/"+filename, 'r') as file_handle:
                    for line in file_handle:
                        num_lines += 1
                        cgf_name, popul_size, read_md5sum = line.strip().split(',')
                        position_int = basic_fns.get_position_from_cgf_string(cgf_name)
                        now = time.time()
                        try:
                            variant = TileVariant.objects.filter(tile_id=position_int).get(md5sum=read_md5sum)
                            if variant.conversion_to_cgf != cgf_name:
                                num_incorrect_calls += 1
                                variant.conversion_to_cgf = cgf_name
                                variant.save()
                        except TileVariant.DoesNotExist:
                            num_unmatched += 1
                            out.write(line)
                        later = time.time()
                        total_time += later - now
                print "File: %s, Number of lines: %i, number ignored: %i, number incorrect: %i" % (filename, num_lines, num_unmatched, num_incorrect_calls)
    print total_time
