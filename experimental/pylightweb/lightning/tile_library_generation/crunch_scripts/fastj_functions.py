import basic_functions as basic_fns

from fastj_objects import TileLibrary


def build_tile_library(library_input_file_handle, global_version, global_path, num_hex_digits_for_version, num_hex_digits_for_path, num_hex_digits_for_step, num_hex_digits_for_variant_value):
    """
    Currently does not support compressed files or multiple assemblies

    Input Files:
        library_input_file format:
           tile_var_period_sep, tile_variant_name, tile_int, population_size, md5sum, cgf_string

        loci_input_file format:
           tile_int, assembly, chromosome, locus_beg, locus_end, chrom_name


    Return values:
        tile_library (a populated TileLibrary object)
    """
    ### Initialize blank library ###
    tile_library = TileLibrary(global_version, global_path)
    ### Read current library ###
    for line in library_input_file_handle:
        human_readable_name, tile_variant_name, tile_int, population_size, md5sum = line.strip().split(',')
        version, path, step = basic_fns.get_position_strings_from_position_int(int(tile_int), num_hex_digits_for_version, num_hex_digits_for_path, num_hex_digits_for_step)
        small_library = tile_library.get_smaller_library_from_strings(version,path,step)
        small_library.initialize_library(
            int(tile_variant_name),
            md5sum,
            int(population_size),
            num_hex_digits_for_version,
            num_hex_digits_for_path,
            num_hex_digits_for_step,
            num_hex_digits_for_variant_value
        )
    ### Ensure library is built correctly ###
    tile_library.check_correct_initialization()
    return tile_library
