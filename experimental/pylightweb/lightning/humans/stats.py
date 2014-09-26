#Statistics about a person


def unphased_person_total(A, path_lengths_TOC, chr_lengths_TOC):
    chrom_info = []
    for chrom, index in enumerate(chr_lengths_TOC):
        chrom_info.append(
