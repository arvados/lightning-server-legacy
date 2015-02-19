from constants import CHR_CHOICES, CHR_OTHER, SUPPORTED_ASSEMBLY_CHOICES

chrom_index = [i for i,j in CHR_CHOICES]
assembly_index = [i for i,j in SUPPORTED_ASSEMBLY_CHOICES]

def get_readable_chr_name(chromosome_int, alt_chromosome_name):
    if chromosome_int == CHR_OTHER:
        return alternate_chromosome_name
    else:
        return CHR_CHOICES[chrom_index.index(chromosome_int)][1]

def get_readable_assembly_name(assembly_int):
    return SUPPORTED_ASSEMBLY_CHOICES[assembly_index.index(assembly_int)][1]
