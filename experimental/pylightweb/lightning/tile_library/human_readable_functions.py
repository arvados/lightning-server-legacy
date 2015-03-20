from tile_library.constants import CHR_CHOICES, CHR_OTHER, SUPPORTED_ASSEMBLY_CHOICES, STATISTICS_TYPE_CHOICES, PATH

chrom_index = [i for i,j in CHR_CHOICES]
assembly_index = [i for i,j in SUPPORTED_ASSEMBLY_CHOICES]
stat_index = [i for i,j in STATISTICS_TYPE_CHOICES]

def get_readable_genome_statistics_name(statistic_type, path=-1):
    if type(statistics_type) != int:
        raise TypeError("Expects statistics_type to be of type int")
    if statistics_type == PATH:
        return "%s %s" % (SUPPORTED_STATISTICS_TYPE_CHOICES[stat_index.index(statistic_type)][1], hex(path).lstrip('0x').zfill(1))
    return SUPPORTED_STATISTICS_TYPE_CHOICES[stat_index.index(statistic_type)][1]

def get_readable_chr_name(chromosome_int, alt_chromosome_name):
    if type(chromosome_int) != int:
        raise TypeError("Expects chromosome int to be of type int")
    if chromosome_int == CHR_OTHER:
        return str(alternate_chromosome_name)
    else:
        return CHR_CHOICES[chrom_index.index(chromosome_int)][1]

def get_readable_assembly_name(assembly_int):
    if type(assembly_int) != int:
        raise TypeError("Expects assembly int to be of type int")
    return SUPPORTED_ASSEMBLY_CHOICES[assembly_index.index(assembly_int)][1]
