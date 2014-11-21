import os
import string
from tile_library.models import TileVariant
import tile_library.basic_functions as base_fns


def create_cgf_conversion(CGF_LIBRARY_DIRNAME):
    for subdir, dirs, files in os.walk(CGF_LIBRARY_DIRNAME):
        for f in files:
            if "_library.csv" in f:
                with open(subdir+f, 'r') as file_handle:
                    for line in file_handle:
                        cgf_name, popul_size, read_md5sum = line.split(',')
                        var_qs = TileVariant.objects.filter(md5sum=read_md5sum)
                        if var_qs.exists():
                            #get will throw an error if too many people come back
                            var = var_qs.select_for_update().get()
                            var.conversion_to_cgf = cgf_name
                            var.save()
                        else:
                            reference_pk = int(string.join(cgf_name.split('.')[:-1], '')+'000',16)
                            var = TileVariant.objects.select_for_update().get(tile_variant_name=reference_pk)
                            assert var.conversion_to_cgf == '' or var.conversion_to_cgf == cgf_name
                            var.conversion_to_cgf = cgf_name
                            var.save()
                            
                            
