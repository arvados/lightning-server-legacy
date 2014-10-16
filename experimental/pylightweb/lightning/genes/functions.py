#Functions for genes!
#
#Gene aliases with odd cases:
#   abParts
#   5S_rRNA (138 GeneXRef matches, none overlap, multiple chromosomes)
#   CP
from genes.models import GeneXRef, UCSC_Gene

def color_exons(exons, zero, total):
    def to_percent(l):
        return (int(l)-zero)/float(total-zero)*100
    colors = []
    covers = 0
    for i, (begin, end) in enumerate(exons):
        begin = int(begin)
        end = int(end)
        assert begin >= zero, "begin must be greater than or equal to the zero"
        assert begin <= total, "begin must be less than or equal to the total"
        assert end >= zero, "end must be greater than or equal to the zero"
        assert end <= total, "end must be less than or equal to the total"
        assert begin <= end, "begin must be smaller than end"
        exon = to_percent(end) - to_percent(begin)
        if i == 0:
            to_append = (to_percent(begin), exon)
        else:
            to_append = (to_percent(begin)-to_percent(exons[i-1][1]), exon)
        colors.append(to_append)
        covers += sum(to_append)
    if len(exons) == 0:
        to_append = (100, 0)
    else:
        to_append = (100-to_percent(exons[-1][1]), 0)
    covers += sum(to_append)
    colors.append(to_append)
    assert covers == 100, "The exons don't add up to 100: "+ str(covers)
    return colors


def overlap(s1, e1, s2, e2):
    smaller = min((s1, e1), (s2, e2), key=lambda x:x[0])
    larger = max((s1, e1), (s2, e2), key=lambda x:x[0])
    if smaller[1] < larger[0]:
        return False
    else:
        return True

def split_genes_into_groups(genes, by_tile=False):
    overlapping_genes = []
    for gene in genes:
        assembly = int(gene.gene.assembly)
        chrom = int(gene.gene.chrom)
        if by_tile:
            s = int(gene.gene.tile_start_tx)
            e = int(gene.gene.tile_end_tx)
            gene.tile_tx_length = e-s
        else:
            s = int(gene.gene.start_tx)
            e = int(gene.gene.end_tx)
            gene.tx_length = e-s
        assert s <= e
        if len(overlapping_genes) == 0:
            overlapping_genes.append([assembly, chrom, s, e, gene])
        else:
            make_new = True
            for gene_group in overlapping_genes:
                if assembly != gene_group[0]:
                    #do lift-over, for now raise exception to let user know
                    #data is corrupted
                    # lift-over needs to redefine chrom, s, and e to be in correct assembly
                    raise BaseException("Lift-overs not implemented yet")
                if chrom == gene_group[1]:
                    if overlap(s, e, gene_group[2], gene_group[3]):
                        make_new = False
                        gene_group.append(gene)
                        gene_group[2] = min(gene_group[2], s)
                        gene_group[3] = max(gene_group[3], e)
            if make_new:
                overlapping_genes.append([assembly, chrom, s, e, gene])
    return overlapping_genes

def split_exons_and_get_length(genes):
    all_exons = []
    overlapping_genes = split_genes_into_groups(genes)
    for gene_group in overlapping_genes:
        for gene in gene_group[4:]:
            begins = gene.gene.exon_starts.strip(',').split(',')
            ends = gene.gene.exon_ends.strip(',').split(',')
            all_exons.append(color_exons(zip(begins, ends), gene_group[2], gene_group[3]))
    return genes, all_exons, len(genes), len(overlapping_genes)

def color_exon_parts(genes, tile_start, tile_end):
    overlapping_genes = split_genes_into_groups(genes)
    assert len(overlapping_genes) == 1, "Requires all genes to overlap"
    has_exons = False
    all_exons = []
    for gene in genes:
        begins = gene.gene.exon_starts.strip(',').split(',')
        ends = gene.gene.exon_ends.strip(',').split(',')
        colors = []
        inner_exons = []
        #Generate inner_exons
        for beg, end in zip(begins, ends):
            beg = int(beg)
            end = int(end)
            if beg >= tile_start and beg <= tile_end:
                #If beginning of exon in middle
                if end > tile_end:
                    inner_exons.append((beg, tile_end))
                else:
                    inner_exons.append((beg, end))
            elif beg <= tile_start and end >= tile_start:
                #if beginning of exon before the start of the tile, but the exon
                # ends after the tile starts
                if end > tile_end:
                    #The exon extends past the tile
                    inner_exons = [(tile_start, tile_end)]
                else:
                    inner_exons.append((tile_start, end))
            #else do nothing: the exon isn't in the tile
        colors = color_exons(inner_exons, tile_start, tile_end)
        if len(inner_exons) > 0:
            has_exons = True
        all_exons.append(colors)
    return has_exons, all_exons

def annotate_positions_with_exons(overlapping_genes, positions):
    assert len(overlapping_genes) == 1, "Requires all genes to overlap"
    all_exons = []
    for gene_group in overlapping_genes:
        for gene in gene_group[4:]:
            begins = gene.gene.exon_starts.strip(',').split(',')
            ends = gene.gene.exon_ends.strip(',').split(',')
            exons = [(int(begin), int(end)) for begin, end in zip(begins, ends)]
            all_exons.extend(exons)
    
    all_exons = sorted(list(set(all_exons)), key=lambda x:x[0])
    in_exon=False
    curr_exon = 0
    exon_dict = {}
    for position in positions:
        name = int(position.tilename)
        while all_exons[curr_exon][1] < position.min_base:
            curr_exon += 1
        if not in_exon:
            if position.max_base < all_exons[curr_exon][0]:
                exon_dict[name] = in_exon #False
            else:
                in_exon = True
                exon_dict[name] = in_exon #True
                if position.max_base - 24 > all_exons[curr_exon][1]:
                    in_exon = False
                    curr_exon += 1
        else:
            if position.max_base - 24 < all_exons[curr_exon][1]:
                exon_dict[name] = in_exon #True
            else:
                exon_dict[name] = in_exon #True
                in_exon = False
                curr_exon += 1
    return exon_dict
