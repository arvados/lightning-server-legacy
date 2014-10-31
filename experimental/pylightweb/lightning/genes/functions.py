#Functions for genes!

from genes.models import GeneXRef, UCSC_Gene
from tile_library.models import Tile, TileLocusAnnotation
from django.db.models.query import QuerySet
from django.core.exceptions import ObjectDoesNotExist

def color_exons(exons, zero, total):
    """
        exons is list of tuples, the first integer is the start of the exon, second, the end
        zero is int
        total is int
    """
    def to_percent(l):
        return (int(l)-zero)/float(total-zero)*100
    
    assert type(zero)==int, "Expects zero to be an integer"
    assert type(total)==int, "Expects total to be an integer"
    assert zero < total, "zero must be smaller than total"
    assert zero >= 0, "zero must be greater than 0"
    assert total > 0, "total must be greater than 0"

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
            assert begin >= int(exons[i-1][1]), "Expects exons to end before a new one begins"
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
    assert type(s1)==int, "Expects s1 to be an integer"
    assert type(s2)==int, "Expects s2 to be an integer"
    assert type(e1)==int, "Expects e1 to be an integer"
    assert type(e2)==int, "Expects e2 to be an integer"
    assert s1 <= e1, "Expects s1 to be smaller than e1"
    assert s2 <= e2, "Expects s2 to be smaller than e2"
    smaller = min((s1, e1), (s2, e2), key=lambda x:x[0])
    larger = max((s1, e1), (s2, e2), key=lambda x:x[0])
    if smaller[1] < larger[0]:
        return False
    else:
        return True

def split_genes_into_groups(genes, by_tile=False):
    assert type(genes)==QuerySet, "Expects type QuerySet for genes"
    assert type(by_tile)==bool, "Expects type boolean for by_tile"
    overlapping_genes = []
    try:
        genes = genes.order_by('gene__start_tx')
    except FieldError:
        raise BaseException("Expects GeneXRef type of QuerySet")
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
    ret_genes = []
    for gene_group in overlapping_genes:
        for gene in gene_group[4:]:
            ret_genes.append(gene)
            begins = gene.gene.exon_starts.strip(',').split(',')
            ends = gene.gene.exon_ends.strip(',').split(',')
            all_exons.append(color_exons(zip(begins, ends), gene_group[2], gene_group[3]))
    return ret_genes, all_exons, len(genes), len(overlapping_genes)

def annotate_positions_with_exons_overlapping_genes(overlapping_genes, positions):
    assert type(overlapping_genes) == list, "Expects overlapping_genes format"
    assert type(positions) == QuerySet, "Expects QuerySet for positions"
    assert len(overlapping_genes) <= 1, "Requires all genes to overlap"
    if overlapping_genes != []:
        gene_group = overlapping_genes[0]
        assemblies = [i for i, name in TileLocusAnnotation.SUPPORTED_ASSEMBLY_CHOICES]
        assert gene_group[0] in assemblies, "Expects overlapping_genes format. Assembly not recognized"
        chromosomes = [i for i, name in TileLocusAnnotation.CHR_CHOICES]
        assert gene_group[1] in chromosomes, "Expects overlapping_genes format. Chromosome not recognized"
        assert type(gene_group[2])==int, "Expects overlapping_genes format. Start int not an integer"
        assert type(gene_group[3])==int, "Expects overlapping_genes format. End int not an integer"
        assert gene_group[2] <= gene_group[3], "Expects overlapping_genes format. Start int larger than end int"

        all_exons = []
        for gene_group in overlapping_genes:
            for gene in gene_group[4:]:
                assert type(gene)==GeneXRef, "Expects overlapping_genes format. One of the genes not GeneXRef type"
                begins = gene.gene.exon_starts.strip(',').split(',')
                ends = gene.gene.exon_ends.strip(',').split(',')
                exons = [(int(begin), int(end)) for begin, end in zip(begins, ends)]
                all_exons.extend(exons)
        
        all_exons = sorted(list(set(all_exons)), key=lambda x:x[0])
        in_exon=False
        curr_exon = 0
        exon_dict = {}
        try:
            positions.order_by('tilename')
            last_position = positions.last()
            assert type(last_position)==Tile, "Expects positions to be of type Tile"
            last_position_end_int = last_position.tile_locus_annotations.get(assembly=gene_group[0]).end_int
        except ObjectDoesNotExist:
            raise BaseException("Requires positions to have Tile Locus Annotations with the same assembly as the genes")
        all_exons.append((last_position_end_int+10, last_position_end_int+20))

        for position in positions:
            assert type(position)==Tile, "Expects positions to be of type Tile"
            try:
                begin_int = position.tile_locus_annotations.get(assembly=gene_group[0]).begin_int
                end_int = position.tile_locus_annotations.get(assembly=gene_group[0]).end_int
            except ObjectDoesNotExist:
                raise BaseException("Requires positions to have Tile Locus Annotations with the same assembly as the genes")
            name = int(position.tilename)
            while all_exons[curr_exon][1] < begin_int:
                curr_exon += 1
            if not in_exon:
                if end_int < all_exons[curr_exon][0]:
                    exon_dict[name] = in_exon #False
                else:
                    in_exon = True
                    exon_dict[name] = in_exon #True
                    if end_int - 24 > all_exons[curr_exon][1]:
                        in_exon = False
                        curr_exon += 1
            else:
                if end_int - 24 < all_exons[curr_exon][1]:
                    exon_dict[name] = in_exon #True
                else:
                    exon_dict[name] = in_exon #True
                    in_exon = False
                    curr_exon += 1
    else:
        exon_dict = {}
        for position in positions:
            assert type(position) == Tile
            exon_dict[int(position.tilename)] = False
    return exon_dict

def annotate_positions_with_exons(genes, positions):
    overlapping_genes = split_genes_into_groups(genes)
    return annotate_positions_with_exons_overlapping_genes(overlapping_genes, positions)

def color_exon_parts(genes, tile):
    assert type(genes) == QuerySet, "Expects genes to be of type QuerySet"
    if type(tile) == QuerySet:
        assert tile.count() == 1, "Expects tile to have exactly one Tile in it"
        tile = tile.get()    
    assert type(tile) == Tile, "Expects tile to be of type Tile (or a QuerySet of length 1 with type Tile)"
            
    has_exons = False
    all_exons = []
    for gene in genes:
        assert type(gene)==GeneXRef, "Expects genes to be of the type GeneXRef"
        gene_assembly = gene.gene.assembly
        try:
            tile_start = tile.tile_locus_annotations.get(assembly=gene_assembly).begin_int
            tile_end = tile.tile_locus_annotations.get(assembly=gene_assembly).end_int
            assert gene.gene.chrom == tile.tile_locus_annotations.get(assembly=gene_assembly).chromosome, "Gene in wrong chromosome"
        except ObjectDoesNotExist:
            raise BaseException("Requires tile to have Tile Locus Annotations with the same assembly as the genes")
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

