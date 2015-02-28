"""
     0                         24   26                         50   52                         76   78                         102    106                        130
     | ACGGCAGTAGTTTTGCCGCTCGGT | CG | TCAGAATGTTTGGAGGGCGGTACG | GC | TAGAGATATCACCCTCTGCTACTC | AA | CGCACCGGAACTTGTGTTTGTGTG | TGTG | GTCGCCCACTACGCACGTTATATG ||

    130                        154  156                        180  182                        206  208                        232    236                        260
     | AGAGAGCTGGCAGATGCCTTATGG | AA | GTGACTGCTACCGTTTGTTGACAC | CA | ATGCACGAGATTTAACGAGCCTTT | GT | TAGTACATTGCCCTAGTACCGATC | GTTA | AACTAGGCGCTCATTAACTCGACA ||

     0                         24   26                         50   52                         76   78                         102    106                        130
     | CTACCGTTTAGGCGGATATCGCGT | CT | TTCCTTAAACTCATCTCCTGGGGG | GA | CGTCGTGGTTTTGAGCCAGTTATG | GG | GTTCGGCTGACGGGCCGACACATG | GCCA | AGTGCCCTTCTGGCCGACGGATTT ||

    Un-allowed Genome Variants (from path definitions)
        Any variant starting before 130 and ending at or after 130

    Note: Mixing-and-matching non-interacting genome variants is allowed
"""
import hashlib

from tile_library.constants import NUM_HEX_INDEXES_FOR_VERSION, NUM_HEX_INDEXES_FOR_PATH, NUM_HEX_INDEXES_FOR_STEP, NUM_HEX_INDEXES_FOR_VARIANT_VALUE,\
    ASSEMBLY_19, CHR_1, CHR_2, TAG_LENGTH, CHR_PATH_LENGTHS
from tile_library.models import Tile, TileVariant, GenomeVariant, GenomeVariantTranslation, TileLocusAnnotation
import tile_library.basic_functions as basic_fns

assert TAG_LENGTH == 24, "complicated_library assumes that TAG_LENGTH is 24"

ref_tilevar_sequences = [[] for i in range(CHR_PATH_LENGTHS[CHR_1]+1)]
ref_tilevar_sequences[0] = [
    "ACGGCAGTAGTTTTGCCGCTCGGTcgTCAGAATGTTTGGAGGGCGGTACG".upper(),
    "TCAGAATGTTTGGAGGGCGGTACGgcTAGAGATATCACCCTCTGCTACTC".upper(),
    "TAGAGATATCACCCTCTGCTACTCaaCGCACCGGAACTTGTGTTTGTGTG".upper(),
    "CGCACCGGAACTTGTGTTTGTGTGtgtgGTCGCCCACTACGCACGTTATATG".upper()
]
ref_tilevar_sequences[1] = [
    "AGAGAGCTGGCAGATGCCTTATGGaaGTGACTGCTACCGTTTGTTGACAC".upper(),
    "GTGACTGCTACCGTTTGTTGACACcaATGCACGAGATTTAACGAGCCTTT".upper(),
    "ATGCACGAGATTTAACGAGCCTTTgtTAGTACATTGCCCTAGTACCGATC".upper(),
    "TAGTACATTGCCCTAGTACCGATCgttaAACTAGGCGCTCATTAACTCGACA".upper()
]
ref_tilevar_sequences[CHR_PATH_LENGTHS[CHR_1]] = [
    "CTACCGTTTAGGCGGATATCGCGTctTTCCTTAAACTCATCTCCTGGGGG".upper(),
    "TTCCTTAAACTCATCTCCTGGGGGgaCGTCGTGGTTTTGAGCCAGTTATG".upper(),
    "CGTCGTGGTTTTGAGCCAGTTATGggGTTCGGCTGACGGGCCGACACATG".upper(),
    "GTTCGGCTGACGGGCCGACACATGgccaAGTGCCCTTCTGGCCGACGGATTT".upper()
]

ref_loci = [[]for i in range(CHR_PATH_LENGTHS[CHR_1]+1)]
ref_loci[0] = [
    {'chr':CHR_1, 'start':0, 'end':50},
    {'chr':CHR_1, 'start':26, 'end':76},
    {'chr':CHR_1, 'start':52, 'end':102},
    {'chr':CHR_1, 'start':78, 'end':130}
]
ref_loci[1] = [
    {'chr':CHR_1, 'start':130, 'end':180},
    {'chr':CHR_1, 'start':156, 'end':206},
    {'chr':CHR_1, 'start':182, 'end':232},
    {'chr':CHR_1, 'start':208, 'end':260}
]
ref_loci[CHR_PATH_LENGTHS[CHR_1]] = [
    {'chr':CHR_2, 'start':0, 'end':50},
    {'chr':CHR_2, 'start':26, 'end':76},
    {'chr':CHR_2, 'start':52, 'end':102},
    {'chr':CHR_2, 'start':78, 'end':130}
]

def make_tile_variant(tile_var_int, sequence, num_pos_spanned):
    v, p, s, vv = basic_fns.get_tile_variant_strings_from_tile_variant_int(tile_var_int)
    tile = Tile.objects.get(tile_position_int=int(v+p+s,16))
    digestor = hashlib.new('md5', sequence)
    tv = TileVariant(
        tile_variant_int=int(v+p+s+vv,16),
        tile=tile,
        variant_value=int(vv,16),
        length=len(sequence),
        md5sum=digestor.hexdigest(),
        sequence=sequence,
        num_positions_spanned=num_pos_spanned
    )
    tv.save()
    return tv

def make_genome_variant(gv_int, start, end, ref_bases, alt_bases, assembly=ASSEMBLY_19, chrom=CHR_1, chrom_name="", names="", info=""):
    gv = GenomeVariant(
        id=gv_int,
        assembly_int=assembly,
        chromosome_int=chrom,
        alternate_chromosome_name=chrom_name,
        locus_start_int=start,
        locus_end_int=end,
        reference_bases=ref_bases,
        alternate_bases=alt_bases,
        names=names,
        info=info
    )
    gv.save()
    return gv

def make_reference():
    v = '0'*NUM_HEX_INDEXES_FOR_VERSION
    for path_int, sequence_list in enumerate(ref_tilevar_sequences):
        p = hex(path_int).lstrip('0x').zfill(NUM_HEX_INDEXES_FOR_PATH)
        for step_int, seq in enumerate(sequence_list):
            s = hex(step_int).lstrip('0x').zfill(NUM_HEX_INDEXES_FOR_STEP)
            vv = '0'*NUM_HEX_INDEXES_FOR_VARIANT_VALUE
            tile = Tile(tile_position_int=int(v+p+s,16), start_tag=seq[:TAG_LENGTH], end_tag=seq[-TAG_LENGTH:])
            tile.save()
            #print len(seq), ref_loci[path_int][step_int]['end']-ref_loci[path_int][step_int]['start']
            make_tile_variant(int(v+p+s+vv,16), seq, 1)
            TileLocusAnnotation(
                assembly_int=ASSEMBLY_19,
                chromosome_int=ref_loci[path_int][step_int]['chr'],
                alternate_chromosome_name="",
                start_int=ref_loci[path_int][step_int]['start'],
                end_int=ref_loci[path_int][step_int]['end'],
                tile_position=tile,
                tile_variant_value=int(vv,16)
            ).save()

#Genome Variant on Tile 0
#    24 C -> T (SNP)
def make_basic_snp_genome_variant(vv=1, gv_id=1):
    seq = "ACGGCAGTAGTTTTGCCGCTCGGTTGTCAGAATGTTTGGAGGGCGGTACG"
    tv = make_tile_variant(vv, seq, 1)
    gv = make_genome_variant(gv_id, 24, 25, 'C', 'T')
    gvt = GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=24, end=25)
    gvt.save()
    return tv, gv, gvt

#Genome Variant on Tile 0
#    24 CG -> TTT (SUB)
def make_basic_sub_genome_variant(vv=2, gv_id=2):
    seq = "ACGGCAGTAGTTTTGCCGCTCGGTTTTTCAGAATGTTTGGAGGGCGGTACG"
    tv = make_tile_variant(vv, seq, 1)
    gv = make_genome_variant(gv_id, 24, 26, "CG", "TTT")
    gvt = GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=24, end=27)
    gvt.save()
    return tv, gv, gvt

#Genome Variant on Tile 0
#    24 CG -> - (DEL)
def make_basic_del_genome_variant(vv=3, gv_id=3):
    seq = "ACGGCAGTAGTTTTGCCGCTCGGTTCAGAATGTTTGGAGGGCGGTACG"
    tv = make_tile_variant(vv, seq, 1)
    gv = make_genome_variant(gv_id, 24, 26, "CG", "-")
    gvt = GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=24, end=24)
    gvt.save()
    return tv, gv, gvt

#Genome Variant on Tile 0
#    24 - -> AAA (INS)
def make_basic_ins_genome_variant(vv=4, gv_id=4):
    seq = "ACGGCAGTAGTTTTGCCGCTCGGTAAACGTCAGAATGTTTGGAGGGCGGTACG"
    tv = make_tile_variant(vv, seq, 1)
    gv = make_genome_variant(gv_id, 24, 24, '-', 'AAA')
    gvt = GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=24, end=27)
    gvt.save()
    return tv, gv, gvt

#Genome Variants on Tile 0 resulting in spanning tile (num_spanning=2)
#    26 T -> A (SNP)
def make_spanning_2_snp_genome_variant(vv=5, gv_id=5):
    seq = "ACGGCAGTAGTTTTGCCGCTCGGTCGACAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTC"
    tv = make_tile_variant(vv, seq, 2)
    gv = make_genome_variant(gv_id, 26, 27, 'T', 'A')
    gvt = GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=26, end=27)
    gvt.save()
    return tv, gv, gvt

#Genome Variants on Tile 0 resulting in spanning tile (num_spanning=2)
#    25 GT -> A (SUB)
def make_spanning_2_sub_genome_variant(vv=6, gv_id=6):
    seq = "ACGGCAGTAGTTTTGCCGCTCGGTCACAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTC"
    tv = make_tile_variant(vv, seq, 2)
    gv = make_genome_variant(gv_id, 25, 27, 'GT', 'A')
    gvt = GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=25, end=26)
    gvt.save()
    return tv, gv, gvt

#Genome Variants on Tile 0 resulting in spanning tile (num_spanning=2)
#    26 T -> - (DEL)
def make_spanning_2_del_genome_variant(vv=7, gv_id=7):
    seq = "ACGGCAGTAGTTTTGCCGCTCGGTCGCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTC"
    tv = make_tile_variant(vv, seq, 2)
    gv = make_genome_variant(gv_id, 26, 27, 'T', '-')
    gvt = GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=26, end=26)
    gvt.save()
    return tv, gv, gvt

#Genome Variants on Tile 0 resulting in spanning tile (num_spanning=2)
#    26 - -> TTT (INS)
def make_spanning_2_ins_genome_variant(vv=8, gv_id=8):
    seq = "ACGGCAGTAGTTTTGCCGCTCGGTCGTTTTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTC"
    tv = make_tile_variant(vv, seq, 2)
    gv = make_genome_variant(gv_id, 26, 26, '-', 'TTT')
    gvt = GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=26, end=29)
    gvt.save()
    return tv, gv, gvt

#Genome Variant on Tile 0 resulting in spanning tile (num_spanning=3)
#    49 GGCT -> - (DEL)
def make_spanning_3_del_genome_variant(vv=9, gv_id=9):
    seq = "ACGGCAGTAGTTTTGCCGCTCGGTCGTCAGAATGTTTGGAGGGCGGTACAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTG"
    tv = make_tile_variant(vv, seq, 3)
    gv = make_genome_variant(gv_id, 49, 53, 'GGCT', '-')
    gvt = GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=49, end=49)
    gvt.save()
    return tv, gv, gvt

#Genome Variant on Tile 0 resulting in spanning tile (num_spanning=4)
#    49 GGCTAGAGATATCACCCTCTGCTACTCAAC -> - (DEL)
def make_spanning_4_del_genome_variant(vv=10, gv_id=10):
    seq = "ACGGCAGTAGTTTTGCCGCTCGGTCGTCAGAATGTTTGGAGGGCGGTACGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATG"
    tv = make_tile_variant(vv, seq, 4)
    gv = make_genome_variant(gv_id, 49, 79, 'GGCTAGAGATATCACCCTCTGCTACTCAAC', '-')
    gvt = GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=49, end=49)
    gvt.save()
    return tv, gv, gvt

#Un-allowed Genome Variants (from path definitions)
#   129 GA -> - (DEL)
#   (Essentially any variant starting before 130 and ending at or after 130)
def make_broken_genome_variant():
    v = '0'*NUM_HEX_INDEXES_FOR_VERSION
    p = '0'*(NUM_HEX_INDEXES_FOR_PATH)
    s = '0'*(NUM_HEX_INDEXES_FOR_STEP-1)+'3'
    vv = hex(1).lstrip('0x').zfill(NUM_HEX_INDEXES_FOR_VARIANT_VALUE)
    seq = "CGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGAGAGCTGGCAGATGCCTTATGGAAGTGACTGCTACCGTTTGTTGACAC"
    tv = make_tile_variant(int(v+p+s+vv,16), seq, 2)
    gv = make_genome_variant(0, 129, 131, "GA", "-")
    gvt = GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=53, end=53)
    gvt.save()
    return tv, gv, gvt

#    24 C -> T (SNP)
#    25 GT -> A (SUB)
def make_two_genome_variants_for_one_tile_variant(vv=1, gv_id=1):
    seq = "ACGGCAGTAGTTTTGCCGCTCGGTTACAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTC"
    tv = make_tile_variant(vv, seq, 2)
    gv = make_genome_variant(gv_id, 24, 25, "C", "T")
    GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=24, end=25).save()
    gv2 = make_genome_variant(gv_id+1, 25, 27, "GT", "A")
    GenomeVariantTranslation(tile_variant=tv, genome_variant=gv2, start=25, end=26).save()

#    24 CG -> - (DEL)
#    26 - -> TTT (INS)
def make_two_genome_variants_for_one_tile_variant_alter_translation_indexes(vv=1, gv_id=1):
    seq = "ACGGCAGTAGTTTTGCCGCTCGGTTTTTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTC"
    tv = make_tile_variant(vv, seq, 2)
    gv = make_genome_variant(gv_id, 24, 26, "CG", "-")
    GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=24, end=24).save()
    gv = make_genome_variant(gv_id+1, 26, 26, "-", "TTT")
    GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=24, end=27).save()

def make_entire_library():
    make_reference()
    tv, basic_snp, trans = make_basic_snp_genome_variant()
    make_basic_sub_genome_variant()
    tv, basic_del, trans = make_basic_del_genome_variant()
    make_basic_ins_genome_variant()
    make_spanning_2_snp_genome_variant()
    tv, spanning_sub, trans = make_spanning_2_sub_genome_variant()
    make_spanning_2_del_genome_variant()
    tv, spanning_ins, trans = make_spanning_2_ins_genome_variant()
    make_spanning_3_del_genome_variant()
    make_spanning_4_del_genome_variant()
    seq = "ACGGCAGTAGTTTTGCCGCTCGGTTACAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTC"
    tv = make_tile_variant(11, seq, 2)
    GenomeVariantTranslation(tile_variant=tv, genome_variant=basic_snp, start=24, end=25).save()
    GenomeVariantTranslation(tile_variant=tv, genome_variant=spanning_sub, start=25, end=26).save()
    seq = "ACGGCAGTAGTTTTGCCGCTCGGTTTTTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTC"
    tv = make_tile_variant(12, seq, 2)
    GenomeVariantTranslation(tile_variant=tv, genome_variant=basic_del, start=24, end=24).save()
    GenomeVariantTranslation(tile_variant=tv, genome_variant=spanning_ins, start=24, end=27).save()
