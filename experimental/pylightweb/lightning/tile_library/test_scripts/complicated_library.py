"""
ASSEMBLY_37 (Want to change a bit more!)
     0                         24    27                         50   52                         76   78                         102    106                        130
     | ACGGCAGTAGTTTTGCCGCTCGGT | TTT | TCAGAATGTTTGGAGGGCGGTACG | GC | TAGAGATATCACCCTCTGCTACTC | AA | CGCACCGGAACTTGTGTTTGTGTG | TGTG | GTCGCCCACTACGCACGTTATATG ||

    130                        154  156                        180  182                        206  208                        232    236                        260
     | AGAGAGCTGGCAGATGCCTTATGG | AA | GTGACTGCTACCGTTTGTTGACAC | CA | ATGCACGAGATTTAACGAGCCTTT | GT | TAGTACATTGCCCTAGTACCGATC | GTTA | AACTAGGCGCTCATTAACTCGACA ||

     0                         24   26                         50   52                         76   78                         102    106                        130
     | CTACCGTTTAGGCGGATATCGCGT | CT | TTCCTTAAACTCATCTCCTGGGGG | GA | CGTCGTGGTTTTGAGCCAGTTATG | GG | GTTCGGCTGACGGGCCGACACATG | GCCA | AGTGCCCTTCTGGCCGACGGATTT ||

ASSEMBLY_19
     0                         24   26                         50   52                         76   78                         102    106                        130
     | ACGGCAGTAGTTTTGCCGCTCGGT | CG | TCAGAATGTTTGGAGGGCGGTACG | GC | TAGAGATATCACCCTCTGCTACTC | AA | CGCACCGGAACTTGTGTTTGTGTG | TGTG | GTCGCCCACTACGCACGTTATATG ||

    130                        154  156                        180
     | AGAGAGCTGGCAGATGCCTTATGG | AA | GTGACTGCTACCGTTTGTTGACAC ||

     0                         24   26                         50   52                         76   78                         102
     | CTACCGTTTAGGCGGATATCGCGT | CT | TTCCTTAAACTCATCTCCTGGGGG | GA | GGTCGTGGTTTTGAGCCAGTTATG | GG | GTTCGGCTGACGGGCCGACACATG ||

     102                       126  128                        152
     | CTACCGTTTAGGCGGATATCGCGT | CT | TTCCTTAAACTCATCTCCTGGGGG ||


    Un-allowed Genome Variants (from path definitions)
        Any variant starting before 130 and ending at or after 130

    Note: Mixing-and-matching non-interacting genome variants is allowed

ASSEMBLY_18
    0                         24   26                         53   55                         79   81                         105    109                        133
    | ACGGCAGTAGTTTTGCCGCTCGGT | TG AAATCAGAATGTTTGGAGGGCGGTACG  GC | TAGAGATATCACCCTCTGCTACTC | AA   CGCACCGGAACTTGTGTTTGTGTT   TGTG | GTCGCCCACTACGCACGTTATATG ||
     "ACGGCAGTAGTTTTGCCGCTCGGT   TG    TCAGAATGTTTGGAGGGCGGTACG"

   133                        157  159                         183
    | AGAGAGCTGGCAGATGCCTTATGG | AA | GTGACTGCTACCGTTTGTTGACAC ||

    0                         24   26                          50   52                         76   78                         102
    | CTACCGTTTAGGCGGATATCGCGT | CT | TTCCTTAAACTCATCTCCTGGGGG | GA | GGTCGTGGTTTTGAGCCAGTTATG | GG | GTTCGGCTGACGGGCCGACACATG ||

"""
import hashlib
import string

from django.conf import settings


TAG_LENGTH = settings.TAG_LENGTH
CHR_1 = settings.CHR_1
CHR_2 = settings.CHR_2
CHR_OTHER = settings.CHR_OTHER
ASSEMBLY_18 = settings.ASSEMBLY_18
ASSEMBLY_19 = settings.ASSEMBLY_19
NUM_HEX_INDEXES_FOR_VERSION = settings.NUM_HEX_INDEXES_FOR_VERSION
NUM_HEX_INDEXES_FOR_PATH = settings.NUM_HEX_INDEXES_FOR_PATH
NUM_HEX_INDEXES_FOR_STEP = settings.NUM_HEX_INDEXES_FOR_STEP
NUM_HEX_INDEXES_FOR_VARIANT_VALUE = settings.NUM_HEX_INDEXES_FOR_VARIANT_VALUE
NUM_HEX_INDEXES_FOR_CGF_VARIANT_VALUE = settings.NUM_HEX_INDEXES_FOR_CGF_VARIANT_VALUE

from tile_library.models import Tile, TileVariant, GenomeVariant, GenomeVariantTranslation, TileLocusAnnotation, LanternTranslator
import tile_library.basic_functions as basic_fns

assert TAG_LENGTH == 24, "complicated_library assumes that TAG_LENGTH is 24"

def make_tile_variant(tile_var_int, sequence, num_pos_spanned, start_tag="", end_tag=""):
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
        num_positions_spanned=num_pos_spanned,
        start_tag=start_tag.lower(),
        end_tag=end_tag.lower()
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

def make_library_missing_path_1():
    #Assumes only one assembly
    ref_tilevar_sequences = [[] for i in range(settings.CHR_PATH_LENGTHS[CHR_1]+1)]
    ref_tilevar_sequences[0] = [
        "ACGGCAGTAGTTTTGCCGCTCGGTcgTCAGAATGTTTGGAGGGCGGTACG".lower(),
        "TCAGAATGTTTGGAGGGCGGTACGgcTAGAGATATCACCCTCTGCTACTC".lower(),
        "TAGAGATATCACCCTCTGCTACTCaaCGCACCGGAACTTGTGTTTGTGTG".lower(),
        "CGCACCGGAACTTGTGTTTGTGTGtgtgGTCGCCCACTACGCACGTTATATG".lower()
    ]
    ref_tilevar_sequences[settings.CHR_PATH_LENGTHS[CHR_1]] = [
        "CTACCGTTTAGGCGGATATCGCGTctTTCCTTAAACTCATCTCCTGGGGG".lower(),
        "TTCCTTAAACTCATCTCCTGGGGGGAGGTCGTGGTTTTGAGCCAGTTATG".lower(),
        "GGTCGTGGTTTTGAGCCAGTTATGGGGTTCGGCTGACGGGCCGACACATG".lower()
    ]

    ref_loci = [[]for i in range(settings.CHR_PATH_LENGTHS[CHR_1]+1)]
    ref_loci[0] = [
        {'chr':CHR_1, 'start':0, 'end':50},
        {'chr':CHR_1, 'start':26, 'end':76},
        {'chr':CHR_1, 'start':52, 'end':102},
        {'chr':CHR_1, 'start':78, 'end':130}
    ]
    ref_loci[settings.CHR_PATH_LENGTHS[CHR_1]] = [
        {'chr':CHR_2, 'start':0, 'end':50},
        {'chr':CHR_2, 'start':26, 'end':76},
        {'chr':CHR_2, 'start':52, 'end':102}
    ]
    v = '0'*NUM_HEX_INDEXES_FOR_VERSION
    for path_int, sequence_list in enumerate(ref_tilevar_sequences):
        p = hex(path_int).lstrip('0x').zfill(NUM_HEX_INDEXES_FOR_PATH)
        for step_int, seq in enumerate(sequence_list):
            path_start = False
            path_end = False
            start_tag = seq[:TAG_LENGTH]
            end_tag = seq[-TAG_LENGTH:]
            variant_start_tag = ""
            variant_end_tag = ""
            if step_int == 0:
                path_start = True
                variant_start_tag = start_tag
                start_tag = ""
            if step_int == len(sequence_list)-1:
                path_end = True
                variant_end_tag = end_tag
                end_tag = ""
            s = hex(step_int).lstrip('0x').zfill(NUM_HEX_INDEXES_FOR_STEP)
            vv = '0'*NUM_HEX_INDEXES_FOR_VARIANT_VALUE
            tile = Tile(tile_position_int=int(v+p+s,16), start_tag=start_tag, end_tag=end_tag, is_start_of_path=path_start, is_end_of_path=path_end)
            tile.save()
            make_tile_variant(int(v+p+s+vv,16), seq, 1, start_tag=variant_start_tag, end_tag=variant_end_tag)
            TileLocusAnnotation(
                assembly_int=ASSEMBLY_19,
                chromosome_int=ref_loci[path_int][step_int]['chr'],
                alternate_chromosome_name="",
                start_int=ref_loci[path_int][step_int]['start'],
                end_int=ref_loci[path_int][step_int]['end'],
                tile_position=tile,
                tile_variant_value=int(vv,16)
            ).save()

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
    seq = "ACGGCAGTAGTTTTGCCGCTCGGTTACAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTC".lower()
    tv = make_tile_variant(11, seq, 2, start_tag="ACGGCAGTAGTTTTGCCGCTCGGT")
    GenomeVariantTranslation(tile_variant=tv, genome_variant=basic_snp, start=24, end=25).save()
    GenomeVariantTranslation(tile_variant=tv, genome_variant=spanning_sub, start=25, end=26).save()
    seq = "ACGGCAGTAGTTTTGCCGCTCGGTTTTTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTC".lower()
    tv = make_tile_variant(12, seq, 2, start_tag="ACGGCAGTAGTTTTGCCGCTCGGT")
    GenomeVariantTranslation(tile_variant=tv, genome_variant=basic_del, start=24, end=24).save()
    GenomeVariantTranslation(tile_variant=tv, genome_variant=spanning_ins, start=24, end=27).save()

    make_snp_genome_variant_on_start_tag_unable_to_span(vv=13,gv_id=11)

    seq = "TAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTG".lower()
    tv = make_tile_variant(int('2'+vv_min,16)+1, seq, 1)
    gv = make_genome_variant(12, 76, 78, "AA", "-")
    GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=24, end=24).save()

    seq = "TAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATG".lower()
    tv = make_tile_variant(int('2'+vv_min,16)+2, seq, 2, end_tag="GTCGCCCACTACGCACGTTATATG")
    gv = make_genome_variant(13, 101, 102, 'G', 'T')
    GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=49, end=50).save()

    make_snp_genome_variant_on_end_tag_unable_to_span(vv=1, gv_id=14)

def make_library_missing_path_0():
    #Assumes only one assembly
    ref_tilevar_sequences = [[] for i in range(settings.CHR_PATH_LENGTHS[CHR_1]+1)]
    ref_tilevar_sequences[1] = [
        "AGAGAGCTGGCAGATGCCTTATGGaaGTGACTGCTACCGTTTGTTGACAC".lower()
    ]
    ref_tilevar_sequences[settings.CHR_PATH_LENGTHS[CHR_1]] = [
        "CTACCGTTTAGGCGGATATCGCGTctTTCCTTAAACTCATCTCCTGGGGG".lower(),
        "TTCCTTAAACTCATCTCCTGGGGGGAGGTCGTGGTTTTGAGCCAGTTATG".lower(),
        "GGTCGTGGTTTTGAGCCAGTTATGGGGTTCGGCTGACGGGCCGACACATG".lower()
    ]

    ref_loci = [[]for i in range(settings.CHR_PATH_LENGTHS[CHR_1]+1)]
    ref_loci[1] = [
        {'chr':CHR_1, 'start':130, 'end':180}
    ]
    ref_loci[settings.CHR_PATH_LENGTHS[CHR_1]] = [
        {'chr':CHR_2, 'start':0, 'end':50},
        {'chr':CHR_2, 'start':26, 'end':76},
        {'chr':CHR_2, 'start':52, 'end':102}
    ]
    v = '0'*NUM_HEX_INDEXES_FOR_VERSION
    for path_int, sequence_list in enumerate(ref_tilevar_sequences):
        p = hex(path_int).lstrip('0x').zfill(NUM_HEX_INDEXES_FOR_PATH)
        for step_int, seq in enumerate(sequence_list):
            path_start = False
            path_end = False
            start_tag = seq[:TAG_LENGTH]
            end_tag = seq[-TAG_LENGTH:]
            variant_start_tag = ""
            variant_end_tag = ""
            if step_int == 0:
                path_start = True
                variant_start_tag = start_tag
                start_tag = ""
            if step_int == len(sequence_list)-1:
                path_end = True
                variant_end_tag = end_tag
                end_tag = ""
            s = hex(step_int).lstrip('0x').zfill(NUM_HEX_INDEXES_FOR_STEP)
            vv = '0'*NUM_HEX_INDEXES_FOR_VARIANT_VALUE
            tile = Tile(tile_position_int=int(v+p+s,16), start_tag=start_tag, end_tag=end_tag, is_start_of_path=path_start, is_end_of_path=path_end)
            tile.save()
            make_tile_variant(int(v+p+s+vv,16), seq, 1, start_tag=variant_start_tag, end_tag=variant_end_tag)
            TileLocusAnnotation(
                assembly_int=ASSEMBLY_19,
                chromosome_int=ref_loci[path_int][step_int]['chr'],
                alternate_chromosome_name="",
                start_int=ref_loci[path_int][step_int]['start'],
                end_int=ref_loci[path_int][step_int]['end'],
                tile_position=tile,
                tile_variant_value=int(vv,16)
            ).save()

    tv = make_tile_variant(int('1'+step_min+vv_min,16)+1, "", 1)
    gv = make_genome_variant(15, 130, 180, "AGAGAGCTGGCAGATGCCTTATGGAAGTGACTGCTACCGTTTGTTGACAC", "-")
    GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=0, end=0).save()


def make_reference(multiple_assemblies=False):
    ref_tilevar_sequences = [[] for i in range(settings.CHR_PATH_LENGTHS[CHR_1]+1)]
    ref_tilevar_sequences[0] = [
        "ACGGCAGTAGTTTTGCCGCTCGGTcgTCAGAATGTTTGGAGGGCGGTACG".lower(),
        "TCAGAATGTTTGGAGGGCGGTACGgcTAGAGATATCACCCTCTGCTACTC".lower(),
        "TAGAGATATCACCCTCTGCTACTCaaCGCACCGGAACTTGTGTTTGTGTG".lower(),
        "CGCACCGGAACTTGTGTTTGTGTGtgtgGTCGCCCACTACGCACGTTATATG".lower()
    ]
    ref_tilevar_sequences[1] = [
        "AGAGAGCTGGCAGATGCCTTATGGaaGTGACTGCTACCGTTTGTTGACAC".lower()
    ]
    ref_tilevar_sequences[settings.CHR_PATH_LENGTHS[CHR_1]] = [
        "CTACCGTTTAGGCGGATATCGCGTctTTCCTTAAACTCATCTCCTGGGGG".lower(),
        "TTCCTTAAACTCATCTCCTGGGGGGAGGTCGTGGTTTTGAGCCAGTTATG".lower(),
        "GGTCGTGGTTTTGAGCCAGTTATGGGGTTCGGCTGACGGGCCGACACATG".lower()
    ]

    ref_loci = [[]for i in range(settings.CHR_PATH_LENGTHS[CHR_1]+1)]
    ref_loci[0] = [
        {'chr':CHR_1, 'start':0, 'end':50},
        {'chr':CHR_1, 'start':26, 'end':76},
        {'chr':CHR_1, 'start':52, 'end':102},
        {'chr':CHR_1, 'start':78, 'end':130}
    ]
    ref_loci[1] = [
        {'chr':CHR_1, 'start':130, 'end':180}
    ]
    ref_loci[settings.CHR_PATH_LENGTHS[CHR_1]] = [
        {'chr':CHR_2, 'start':0, 'end':50},
        {'chr':CHR_2, 'start':26, 'end':76},
        {'chr':CHR_2, 'start':52, 'end':102}
    ]

    loci_18 = [[]for i in range(settings.CHR_PATH_LENGTHS[CHR_1]+1)]
    loci_18[0] = [
        {'chr':CHR_1, 'start':0, 'end':79, 'variant_value':14},
        {},
        {'chr':CHR_1, 'start':55, 'end':133, 'variant_value':2},
        {}
    ]
    loci_18[1] = [
        {'chr':CHR_1, 'start':133, 'end':183, 'variant_value':0}
    ]
    loci_18[settings.CHR_PATH_LENGTHS[CHR_1]] = [
        {'chr':CHR_2, 'start':0, 'end':50, 'variant_value':0},
        {'chr':CHR_2, 'start':26, 'end':76, 'variant_value':0},
        {'chr':CHR_2, 'start':52, 'end':102, 'variant_value':0}
    ]
    v = '0'*NUM_HEX_INDEXES_FOR_VERSION
    for path_int, sequence_list in enumerate(ref_tilevar_sequences):
        p = hex(path_int).lstrip('0x').zfill(NUM_HEX_INDEXES_FOR_PATH)
        for step_int, seq in enumerate(sequence_list):
            path_start = False
            path_end = False
            start_tag = seq[:TAG_LENGTH]
            end_tag = seq[-TAG_LENGTH:]
            variant_start_tag = ""
            variant_end_tag = ""
            if step_int == 0:
                path_start = True
                variant_start_tag = start_tag
                start_tag = ""
            if step_int == len(sequence_list)-1:
                path_end = True
                variant_end_tag = end_tag
                end_tag = ""
            s = hex(step_int).lstrip('0x').zfill(NUM_HEX_INDEXES_FOR_STEP)
            vv = '0'*NUM_HEX_INDEXES_FOR_VARIANT_VALUE
            tile = Tile(tile_position_int=int(v+p+s,16), start_tag=start_tag, end_tag=end_tag, is_start_of_path=path_start, is_end_of_path=path_end)
            tile.save()
            make_tile_variant(int(v+p+s+vv,16), seq, 1, start_tag=variant_start_tag, end_tag=variant_end_tag)
            TileLocusAnnotation(
                assembly_int=ASSEMBLY_19,
                chromosome_int=ref_loci[path_int][step_int]['chr'],
                alternate_chromosome_name="",
                start_int=ref_loci[path_int][step_int]['start'],
                end_int=ref_loci[path_int][step_int]['end'],
                tile_position=tile,
                tile_variant_value=int(vv,16)
            ).save()

    if multiple_assemblies:
        v = '0'*NUM_HEX_INDEXES_FOR_VERSION
        make_tile_variant(14, "ACGGCAGTAGTTTTGCCGCTCGGTTGAAATCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTC".lower(), 2, start_tag="ACGGCAGTAGTTTTGCCGCTCGGT")
        make_tile_variant(int('2'+vv_min,16)+2, "TAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATG".lower(), 2, end_tag="GTCGCCCACTACGCACGTTATATG")
        for path_int, sequence_list in enumerate(ref_tilevar_sequences):
            p = hex(path_int).lstrip('0x').zfill(NUM_HEX_INDEXES_FOR_PATH)
            for step_int, seq in enumerate(sequence_list):
                s = hex(step_int).lstrip('0x').zfill(NUM_HEX_INDEXES_FOR_STEP)
                if len(loci_18[path_int][step_int]) > 0:
                    tile = Tile.objects.get(tile_position_int=int(v+p+s,16))
                    TileLocusAnnotation(
                        assembly_int=ASSEMBLY_18,
                        chromosome_int=loci_18[path_int][step_int]['chr'],
                        alternate_chromosome_name="",
                        start_int=loci_18[path_int][step_int]['start'],
                        end_int=loci_18[path_int][step_int]['end'],
                        tile_position=tile,
                        tile_variant_value=loci_18[path_int][step_int]['variant_value']
                    ).save()
def make_alternate_reference():
    alt_ref_tilevar_sequences = [[] for i in range(settings.CHR_PATH_LENGTHS[CHR_OTHER])]
    alt_ref_tilevar_sequences[-1] = [
        "ACGGCAGTAGTTTTGCCGCTCGGTcgTCAGAATGTTTGGAGGGCGGTACG".lower(),
        "TCAGAATGTTTGGAGGGCGGTACGgcTAGAGATATCACCCTCTGCTACTC".lower(),
        "TAGAGATATCACCCTCTGCTACTCaaCGCACCGGAACTTGTGTTTGTGTG".lower(),
        "CGCACCGGAACTTGTGTTTGTGTGtgtgGTCGCCCACTACGCACGTTATATG".lower(),
        "CTACCGTTTAGGCGGATATCGCGTctTTCCTTAAACTCATCTCCTGGGGG".lower(),
        "TTCCTTAAACTCATCTCCTGGGGGgaCGTCGTGGTTTTGAGCCAGTTATG".lower(),
        "CGTCGTGGTTTTGAGCCAGTTATGggGTTCGGCTGACGGGCCGACACATG".lower(),
        "GTTCGGCTGACGGGCCGACACATGgccaAGTGCCCTTCTGGCCGACGGATTT".lower()
    ]

    alt_loci = [[]for i in range(settings.CHR_PATH_LENGTHS[CHR_OTHER])]
    alt_loci[-1] = [
        {'name':'foo', 'start':0, 'end':50},
        {'name':'foo', 'start':26, 'end':76},
        {'name':'foo', 'start':52, 'end':102},
        {'name':'foo', 'start':78, 'end':130},
        {'name':'bar', 'start':0, 'end':50},
        {'name':'bar', 'start':26, 'end':76},
        {'name':'bar', 'start':52, 'end':102},
        {'name':'bar', 'start':78, 'end':130}
    ]
    v = '0'*NUM_HEX_INDEXES_FOR_VERSION
    for path_int, sequence_list in enumerate(alt_ref_tilevar_sequences):
        p = hex(path_int).lstrip('0x').zfill(NUM_HEX_INDEXES_FOR_PATH)
        for step_int, seq in enumerate(sequence_list):
            path_start = False
            path_end = False
            start_tag = seq[:TAG_LENGTH]
            end_tag = seq[-TAG_LENGTH:]
            variant_start_tag = ""
            variant_end_tag = ""
            if step_int == 0:
                path_start = True
                variant_start_tag = start_tag
                start_tag = ""
            if step_int == len(sequence_list)-1:
                path_end = True
                variant_end_tag = end_tag
                end_tag = ""
            s = hex(step_int).lstrip('0x').zfill(NUM_HEX_INDEXES_FOR_STEP)
            vv = '0'*NUM_HEX_INDEXES_FOR_VARIANT_VALUE
            tile = Tile(tile_position_int=int(v+p+s,16), start_tag=start_tag, end_tag=end_tag, is_start_of_path=path_start, is_end_of_path=path_end)
            tile.save()
            #print len(seq), ref_loci[path_int][step_int]['end']-ref_loci[path_int][step_int]['start']
            make_tile_variant(int(v+p+s+vv,16), seq, 1, start_tag=variant_start_tag, end_tag=variant_end_tag)
            TileLocusAnnotation(
                assembly_int=ASSEMBLY_19,
                chromosome_int=CHR_OTHER,
                alternate_chromosome_name=alt_loci[path_int][step_int]['name'],
                start_int=alt_loci[path_int][step_int]['start'],
                end_int=alt_loci[path_int][step_int]['end'],
                tile_position=tile,
                tile_variant_value=int(vv,16)
            ).save()
#Genome Variant on Tile 0
#    24 C -> T (SNP)
def make_basic_snp_genome_variant(vv=1, gv_id=1):
    seq = "ACGGCAGTAGTTTTGCCGCTCGGTTGTCAGAATGTTTGGAGGGCGGTACG".lower()
    tv = make_tile_variant(vv, seq, 1, start_tag="ACGGCAGTAGTTTTGCCGCTCGGT")
    gv = make_genome_variant(gv_id, 24, 25, 'C', 'T')
    gvt = GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=24, end=25)
    gvt.save()
    return tv, gv, gvt
#Genome Variant on Tile 0
#    24 CG -> TTT (SUB)
def make_basic_sub_genome_variant(vv=2, gv_id=2):
    seq = "ACGGCAGTAGTTTTGCCGCTCGGTTTTTCAGAATGTTTGGAGGGCGGTACG".lower()
    tv = make_tile_variant(vv, seq, 1, start_tag="ACGGCAGTAGTTTTGCCGCTCGGT")
    gv = make_genome_variant(gv_id, 24, 26, "CG", "TTT")
    gvt = GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=24, end=27)
    gvt.save()
    return tv, gv, gvt
#Genome Variant on Tile 0
#    24 CG -> - (DEL)
def make_basic_del_genome_variant(vv=3, gv_id=3):
    seq = "ACGGCAGTAGTTTTGCCGCTCGGTTCAGAATGTTTGGAGGGCGGTACG".lower()
    tv = make_tile_variant(vv, seq, 1, start_tag="ACGGCAGTAGTTTTGCCGCTCGGT")
    gv = make_genome_variant(gv_id, 24, 26, "CG", "-")
    gvt = GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=24, end=24)
    gvt.save()
    return tv, gv, gvt
#Genome Variant on Tile 0
#    24 - -> AAA (INS)
def make_basic_ins_genome_variant(vv=4, gv_id=4):
    seq = "ACGGCAGTAGTTTTGCCGCTCGGTAAACGTCAGAATGTTTGGAGGGCGGTACG".lower()
    tv = make_tile_variant(vv, seq, 1, start_tag="ACGGCAGTAGTTTTGCCGCTCGGT")
    gv = make_genome_variant(gv_id, 24, 24, '-', 'AAA')
    gvt = GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=24, end=27)
    gvt.save()
    return tv, gv, gvt
#Genome Variants on Tile 0 resulting in spanning tile (num_spanning=2)
#    26 T -> A (SNP)
def make_spanning_2_snp_genome_variant(vv=5, gv_id=5):
    seq = "ACGGCAGTAGTTTTGCCGCTCGGTCGACAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTC".lower()
    tv = make_tile_variant(vv, seq, 2, start_tag="ACGGCAGTAGTTTTGCCGCTCGGT")
    gv = make_genome_variant(gv_id, 26, 27, 'T', 'A')
    gvt = GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=26, end=27)
    gvt.save()
    return tv, gv, gvt
#Genome Variants on Tile 0 resulting in spanning tile (num_spanning=2)
#    25 GT -> A (SUB)
def make_spanning_2_sub_genome_variant(vv=6, gv_id=6):
    seq = "ACGGCAGTAGTTTTGCCGCTCGGTCACAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTC".lower()
    tv = make_tile_variant(vv, seq, 2, start_tag="ACGGCAGTAGTTTTGCCGCTCGGT")
    gv = make_genome_variant(gv_id, 25, 27, 'GT', 'A')
    gvt = GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=25, end=26)
    gvt.save()
    return tv, gv, gvt
#Genome Variants on Tile 0 resulting in spanning tile (num_spanning=2)
#    26 T -> - (DEL)
def make_spanning_2_del_genome_variant(vv=7, gv_id=7):
    seq = "ACGGCAGTAGTTTTGCCGCTCGGTCGCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTC".lower()
    tv = make_tile_variant(vv, seq, 2, start_tag="ACGGCAGTAGTTTTGCCGCTCGGT")
    gv = make_genome_variant(gv_id, 26, 27, 'T', '-')
    gvt = GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=26, end=26)
    gvt.save()
    return tv, gv, gvt
#Genome Variants on Tile 0 resulting in spanning tile (num_spanning=2)
#    26 - -> TTT (INS)
def make_spanning_2_ins_genome_variant(vv=8, gv_id=8):
    seq = "ACGGCAGTAGTTTTGCCGCTCGGTCGTTTTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTC".lower()
    tv = make_tile_variant(vv, seq, 2, start_tag="ACGGCAGTAGTTTTGCCGCTCGGT")
    gv = make_genome_variant(gv_id, 26, 26, '-', 'TTT')
    gvt = GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=26, end=29)
    gvt.save()
    return tv, gv, gvt
#Genome Variant on Tile 0 resulting in spanning tile (num_spanning=3)
#    49 GGCT -> - (DEL)
def make_spanning_3_del_genome_variant(vv=9, gv_id=9):
    seq = "ACGGCAGTAGTTTTGCCGCTCGGTCGTCAGAATGTTTGGAGGGCGGTACAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTG".lower()
    tv = make_tile_variant(vv, seq, 3, start_tag="ACGGCAGTAGTTTTGCCGCTCGGT")
    gv = make_genome_variant(gv_id, 49, 53, 'GGCT', '-')
    gvt = GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=49, end=49)
    gvt.save()
    return tv, gv, gvt
#Genome Variant on Tile 0 resulting in spanning tile (num_spanning=4)
#    49 GGCTAGAGATATCACCCTCTGCTACTCAAC -> - (DEL)
def make_spanning_4_del_genome_variant(vv=10, gv_id=10):
    seq = "ACGGCAGTAGTTTTGCCGCTCGGTCGTCAGAATGTTTGGAGGGCGGTACGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATG".lower()
    tv = make_tile_variant(vv, seq, 4, start_tag="ACGGCAGTAGTTTTGCCGCTCGGT", end_tag="GTCGCCCACTACGCACGTTATATG")
    gv = make_genome_variant(gv_id, 49, 79, 'GGCTAGAGATATCACCCTCTGCTACTCAAC', '-')
    gvt = GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=49, end=49)
    gvt.save()
    return tv, gv, gvt
#Genome Variant on Tile 0
#    23 T -> - (DEL)
def make_snp_genome_variant_on_start_tag_unable_to_span(vv=11, gv_id=11):
    seq = "ACGGCAGTAGTTTTGCCGCTCGGCGTCAGAATGTTTGGAGGGCGGTACG".lower()
    tv = make_tile_variant(vv, seq, 1, start_tag="ACGGCAGTAGTTTTGCCGCTCGGC")
    gv = make_genome_variant(gv_id, 23, 24, 'T', '-')
    gvt = GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=23, end=23)
    gvt.save()
    return tv, gv, gvt
#Genome Variant on Tile 0
#    106 G -> A (SNP)
def make_snp_genome_variant_on_end_tag_unable_to_span(vv=1, gv_id=12):
    seq = "CGCACCGGAACTTGTGTTTGTGTGTGTGATCGCCCACTACGCACGTTATATG".lower()
    tv = make_tile_variant(int('3'+vv_min,16)+vv, seq, 1, end_tag="ATCGCCCACTACGCACGTTATATG")
    gv = make_genome_variant(gv_id, 106, 107, 'G', 'A')
    gvt = GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=28, end=29)
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
    seq = "CGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATGAGAGCTGGCAGATGCCTTATGGAAGTGACTGCTACCGTTTGTTGACAC".lower()
    tv = make_tile_variant(int(v+p+s+vv,16), seq, 2)
    gv = make_genome_variant(0, 129, 131, "GA", "-")
    gvt = GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=53, end=53)
    gvt.save()
    return tv, gv, gvt
#    24 C -> T (SNP)
#    25 GT -> A (SUB)
def make_two_genome_variants_for_one_tile_variant(vv=1, gv_id=1):
    seq = "ACGGCAGTAGTTTTGCCGCTCGGTTACAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTC".lower()
    tv = make_tile_variant(vv, seq, 2, start_tag="ACGGCAGTAGTTTTGCCGCTCGGT")
    gv = make_genome_variant(gv_id, 24, 25, "C", "T")
    GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=24, end=25).save()
    gv2 = make_genome_variant(gv_id+1, 25, 27, "GT", "A")
    GenomeVariantTranslation(tile_variant=tv, genome_variant=gv2, start=25, end=26).save()
#    24 CG -> - (DEL)
#    26 - -> TTT (INS)
def make_two_genome_variants_for_one_tile_variant_alter_translation_indexes(vv=1, gv_id=1):
    seq = "ACGGCAGTAGTTTTGCCGCTCGGTTTTTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTC".lower()
    tv = make_tile_variant(vv, seq, 2, start_tag="ACGGCAGTAGTTTTGCCGCTCGGT")
    gv = make_genome_variant(gv_id, 24, 26, "CG", "-")
    GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=24, end=24).save()
    gv = make_genome_variant(gv_id+1, 26, 26, "-", "TTT")
    GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=24, end=27).save()

step_min = '0'*NUM_HEX_INDEXES_FOR_STEP
vv_min = '0'*NUM_HEX_INDEXES_FOR_VARIANT_VALUE

def make_only_19_library():
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
    seq = "ACGGCAGTAGTTTTGCCGCTCGGTTACAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTC".lower()
    tv = make_tile_variant(11, seq, 2, start_tag="ACGGCAGTAGTTTTGCCGCTCGGT")
    GenomeVariantTranslation(tile_variant=tv, genome_variant=basic_snp, start=24, end=25).save()
    GenomeVariantTranslation(tile_variant=tv, genome_variant=spanning_sub, start=25, end=26).save()
    seq = "ACGGCAGTAGTTTTGCCGCTCGGTTTTTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTC".lower()
    tv = make_tile_variant(12, seq, 2, start_tag="ACGGCAGTAGTTTTGCCGCTCGGT")
    GenomeVariantTranslation(tile_variant=tv, genome_variant=basic_del, start=24, end=24).save()
    GenomeVariantTranslation(tile_variant=tv, genome_variant=spanning_ins, start=24, end=27).save()

    make_snp_genome_variant_on_start_tag_unable_to_span(vv=13,gv_id=11)

    seq = "TAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTG".lower()
    tv = make_tile_variant(int('2'+vv_min,16)+1, seq, 1)
    gv = make_genome_variant(12, 76, 78, "AA", "-")
    GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=24, end=24).save()

    seq = "TAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTTTGTGGTCGCCCACTACGCACGTTATATG".lower()
    tv = make_tile_variant(int('2'+vv_min,16)+2, seq, 2, end_tag="GTCGCCCACTACGCACGTTATATG")
    gv = make_genome_variant(13, 101, 102, 'G', 'T')
    GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=49, end=50).save()

    make_snp_genome_variant_on_end_tag_unable_to_span(vv=1, gv_id=14)

    tv = make_tile_variant(int('1'+step_min+vv_min,16)+1, "", 1)
    gv = make_genome_variant(15, 130, 180, "AGAGAGCTGGCAGATGCCTTATGGAAGTGACTGCTACCGTTTGTTGACAC", "-")
    GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=0, end=0).save()

def make_19_and_18_libraries():
    #19 ACGGCAGTAGTTTTGCCGCTCGGT | CG | TCAGAATGTTTGGAGGGCGGTACG
    #18 ACGGCAGTAGTTTTGCCGCTCGGT | TGAAATCAGAATGTTTGGAGGGCGGTACGGC | TAGAGATATCACCCTCTGCTACTC
    #   ACGGCAGTAGTTTTGCCGCTCGGT   TG   TCAGAATGTTTGGAGGGCGGTACG
    tv0 = make_tile_variant(1, "ACGGCAGTAGTTTTGCCGCTCGGTTGTCAGAATGTTTGGAGGGCGGTACG".lower(), 1, start_tag="ACGGCAGTAGTTTTGCCGCTCGGT")
    basic_snp_gv = make_genome_variant(0, 24, 25, 'C', 'T')
    GenomeVariantTranslation(tile_variant=tv0, genome_variant=basic_snp_gv, start=24, end=25).save()
#    AAA_del_gv = make_genome_variant(1, 26, 29, 'AAA', '-', assembly=ASSEMBLY_18)
#    GenomeVariantTranslation(tile_variant=tv0, genome_variant=AAA_del_gv, start=26, end=26).save()
    #19 ACGGCAGTAGTTTTGCCGCTCGGT | CG | TCAGAATGTTTGGAGGGCGGTACG
    #18 ACGGCAGTAGTTTTGCCGCTCGGT | TGAAATCAGAATGTTTGGAGGGCGGTACGGC | TAGAGATATCACCCTCTGCTACTC
    #   ACGGCAGTAGTTTTGCCGCTCGGT   TTT  TCAGAATGTTTGGAGGGCGGTACG
    tv1 = make_tile_variant(2, "ACGGCAGTAGTTTTGCCGCTCGGTTTTTCAGAATGTTTGGAGGGCGGTACG".lower(), 1, start_tag="ACGGCAGTAGTTTTGCCGCTCGGT")
    gv = make_genome_variant(2, 24, 26, "CG", "TTT")
    GenomeVariantTranslation(tile_variant=tv1, genome_variant=gv, start=24, end=27).save()
#    gv = make_genome_variant(3, 25, 27, "GA", "TT", assembly=ASSEMBLY_18)
#    GenomeVariantTranslation(tile_variant=tv1, genome_variant=gv, start=25, end=27).save()
    #19 ACGGCAGTAGTTTTGCCGCTCGGT | CG | TCAGAATGTTTGGAGGGCGGTACG
    #18 ACGGCAGTAGTTTTGCCGCTCGGT | TGAAATCAGAATGTTTGGAGGGCGGTACGGC | TAGAGATATCACCCTCTGCTACTC
    #   ACGGCAGTAGTTTTGCCGCTCGGT        TCAGAATGTTTGGAGGGCGGTACG
    tv2 = make_tile_variant(3, "ACGGCAGTAGTTTTGCCGCTCGGTTCAGAATGTTTGGAGGGCGGTACG".lower(), 1, start_tag="ACGGCAGTAGTTTTGCCGCTCGGT")
    basic_del_gv = make_genome_variant(4, 24, 26, "CG", "-")
    GenomeVariantTranslation(tile_variant=tv2, genome_variant=basic_del_gv, start=24, end=24).save()
#    gv = make_genome_variant(5, 24, 29, "TGAAA", "-", assembly=ASSEMBLY_18)
#    GenomeVariantTranslation(tile_variant=tv2, genome_variant=gv, start=24, end=24).save()
    #19 ACGGCAGTAGTTTTGCCGCTCGGT | CG | TCAGAATGTTTGGAGGGCGGTACG
    #18 ACGGCAGTAGTTTTGCCGCTCGGT | TGAAATCAGAATGTTTGGAGGGCGGTACGGC | TAGAGATATCACCCTCTGCTACTC
    #   ACGGCAGTAGTTTTGCCGCTCGGT   AAACGTCAGAATGTTTGGAGGGCGGTACG
    tv3 = make_tile_variant(4, "ACGGCAGTAGTTTTGCCGCTCGGTAAACGTCAGAATGTTTGGAGGGCGGTACG".lower(), 1, start_tag="ACGGCAGTAGTTTTGCCGCTCGGT")
    gv = make_genome_variant(6, 24, 24, '-', 'AAA')
    GenomeVariantTranslation(tile_variant=tv3, genome_variant=gv, start=24, end=27).save()
#    gv = make_genome_variant(7, 24, 26, 'TG', 'AA', assembly=ASSEMBLY_18)
#    GenomeVariantTranslation(tile_variant=tv3, genome_variant=gv, start=24, end=26).save()
#    gv = make_genome_variant(8, 27, 29, 'AA', 'CG', assembly=ASSEMBLY_18)
#    GenomeVariantTranslation(tile_variant=tv3, genome_variant=gv, start=27, end=29).save()
    #19 ACGGCAGTAGTTTTGCCGCTCGGT | CG | TCAGAATGTTTGGAGGGCGGTACG | GC | TAGAGATATCACCCTCTGCTACTC
    #18 ACGGCAGTAGTTTTGCCGCTCGGT | TGAAATCAGAATGTTTGGAGGGCGGTACG   GC | TAGAGATATCACCCTCTGCTACTC
    #   ACGGCAGTAGTTTTGCCGCTCGGT   CG   ACAGAATGTTTGGAGGGCGGTACG   GC   TAGAGATATCACCCTCTGCTACTC
    tv4 = make_tile_variant(5, "ACGGCAGTAGTTTTGCCGCTCGGTCGACAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTC".lower(), 2, start_tag="ACGGCAGTAGTTTTGCCGCTCGGT")
    gv = make_genome_variant(9, 26, 27, 'T', 'A')
    GenomeVariantTranslation(tile_variant=tv4, genome_variant=gv, start=26, end=27).save()
#    T_C_24_gv = make_genome_variant(10, 24, 25, 'T', 'C', assembly=ASSEMBLY_18)
#    GenomeVariantTranslation(tile_variant=tv4, genome_variant=T_C_24_gv, start=24, end=25).save()
#    gv = make_genome_variant(11, 26, 30, 'AAAT', 'A', assembly=ASSEMBLY_18)
#    GenomeVariantTranslation(tile_variant=tv4, genome_variant=gv, start=26, end=27).save()
    #19 ACGGCAGTAGTTTTGCCGCTCGGT | CG | TCAGAATGTTTGGAGGGCGGTACG | GC | TAGAGATATCACCCTCTGCTACTC
    #18 ACGGCAGTAGTTTTGCCGCTCGGT | TGAAATCAGAATGTTTGGAGGGCGGTACG   GC | TAGAGATATCACCCTCTGCTACTC
    #   ACGGCAGTAGTTTTGCCGCTCGGT   C    ACAGAATGTTTGGAGGGCGGTACG   GC   TAGAGATATCACCCTCTGCTACTC
    tv5 = make_tile_variant(6, "ACGGCAGTAGTTTTGCCGCTCGGTCACAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTC".lower(), 2, start_tag="ACGGCAGTAGTTTTGCCGCTCGGT")
    spanning_sub_gv = make_genome_variant(12, 25, 27, 'GT', 'A')
    GenomeVariantTranslation(tile_variant=tv5, genome_variant=spanning_sub_gv, start=25, end=26).save()
#    gaaat_a_gv = make_genome_variant(13, 25, 30, 'GAAAT', 'A', assembly=ASSEMBLY_18)
#    GenomeVariantTranslation(tile_variant=tv5, genome_variant=T_C_24_gv, start=24, end=25).save()
#    GenomeVariantTranslation(tile_variant=tv5, genome_variant=gaaat_a_gv, start=25, end=26).save()
    #19 ACGGCAGTAGTTTTGCCGCTCGGT | CG | TCAGAATGTTTGGAGGGCGGTACG | GC | TAGAGATATCACCCTCTGCTACTC
    #18 ACGGCAGTAGTTTTGCCGCTCGGT | TGAAATCAGAATGTTTGGAGGGCGGTACG   GC | TAGAGATATCACCCTCTGCTACTC
    #   ACGGCAGTAGTTTTGCCGCTCGGT   CG    CAGAATGTTTGGAGGGCGGTACG   GC   TAGAGATATCACCCTCTGCTACTC
    tv6 = make_tile_variant(7, "ACGGCAGTAGTTTTGCCGCTCGGTCGCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTC".lower(), 2, start_tag="ACGGCAGTAGTTTTGCCGCTCGGT")
    gv = make_genome_variant(14, 26, 27, 'T', '-')
    GenomeVariantTranslation(tile_variant=tv6, genome_variant=gv, start=26, end=26).save()
#    gv = make_genome_variant(15, 26, 30, 'AAAT', '-', assembly=ASSEMBLY_18)
#    GenomeVariantTranslation(tile_variant=tv6, genome_variant=T_C_24_gv, start=24, end=25).save()
#    GenomeVariantTranslation(tile_variant=tv6, genome_variant=gv, start=26, end=26).save()
    #19 ACGGCAGTAGTTTTGCCGCTCGGT | CG | TCAGAATGTTTGGAGGGCGGTACG | GC | TAGAGATATCACCCTCTGCTACTC
    #18 ACGGCAGTAGTTTTGCCGCTCGGT | TGAAATCAGAATGTTTGGAGGGCGGTACG   GC | TAGAGATATCACCCTCTGCTACTC
    #   ACGGCAGTAGTTTTGCCGCTCGGT   CGTTTTCAGAATGTTTGGAGGGCGGTACG   GC   TAGAGATATCACCCTCTGCTACTC
    tv7 = make_tile_variant(8, "ACGGCAGTAGTTTTGCCGCTCGGTCGTTTTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTC".lower(), 2, start_tag="ACGGCAGTAGTTTTGCCGCTCGGT")
    spanning_ins_gv = make_genome_variant(16, 26, 26, '-', 'TTT')
    GenomeVariantTranslation(tile_variant=tv7, genome_variant=spanning_ins_gv, start=26, end=29).save()
#    gv = make_genome_variant(17, 26, 29, 'AAA', 'TTT', assembly=ASSEMBLY_18)
#    GenomeVariantTranslation(tile_variant=tv7, genome_variant=T_C_24_gv, start=24, end=25).save()
#    GenomeVariantTranslation(tile_variant=tv7, genome_variant=gv, start=26, end=29).save()
    #19 ACGGCAGTAGTTTTGCCGCTCGGT | CG | TCAGAATGTTTGGAGGGCGGTACG | GC | TAGAGATATCACCCTCTGCTACTC | AA | CGCACCGGAACTTGTGTTTGTGTG
    #18 ACGGCAGTAGTTTTGCCGCTCGGT | TGAAATCAGAATGTTTGGAGGGCGGTACG   GC | TAGAGATATCACCCTCTGCTACTC | AA   CGCACCGGAACTTGTGTTTGTGTT   TGTG | GTCGCCCACTACGCACGTTATATG ||
    #   ACGGCAGTAGTTTTGCCGCTCGGT   CG   TCAGAATGTTTGGAGGGCGGTAC          AGAGATATCACCCTCTGCTACTC   AA   CGCACCGGAACTTGTGTTTGTGTG
    tv8 = make_tile_variant(9, "ACGGCAGTAGTTTTGCCGCTCGGTCGTCAGAATGTTTGGAGGGCGGTACAGAGATATCACCCTCTGCTACTCAACGCACCGGAACTTGTGTTTGTGTG".lower(), 3, start_tag="ACGGCAGTAGTTTTGCCGCTCGGT")
    gv = make_genome_variant(18, 49, 53, 'GGCT', '-')
    GenomeVariantTranslation(tile_variant=tv8, genome_variant=gv, start=49, end=49).save()
#    gv = make_genome_variant(19, 52, 56, 'GGCT', '-', assembly=ASSEMBLY_18)
#    GenomeVariantTranslation(tile_variant=tv8, genome_variant=AAA_del_gv, start=26, end=26).save()
#    GenomeVariantTranslation(tile_variant=tv8, genome_variant=T_C_24_gv, start=24, end=25).save()
#    GenomeVariantTranslation(tile_variant=tv8, genome_variant=gv, start=49, end=49).save()
#    T_G_104_gv = make_genome_variant(20, 104, 105, 'T', 'G', assembly=ASSEMBLY_18)
#    GenomeVariantTranslation(tile_variant=tv8, genome_variant=T_G_104_gv, start=97, end=98).save()
    #19 ACGGCAGTAGTTTTGCCGCTCGGT | CG | TCAGAATGTTTGGAGGGCGGTACG | GC | TAGAGATATCACCCTCTGCTACTC | AA | CGCACCGGAACTTGTGTTTGTGTG | TGTG | GTCGCCCACTACGCACGTTATATG ||
    #18 ACGGCAGTAGTTTTGCCGCTCGGT | TGAAATCAGAATGTTTGGAGGGCGGTACG   GC | TAGAGATATCACCCTCTGCTACTC | AA   CGCACCGGAACTTGTGTTTGTGTT   TGTG | GTCGCCCACTACGCACGTTATATG ||
    #   ACGGCAGTAGTTTTGCCGCTCGGT   CG   TCAGAATGTTTGGAGGGCGGTAC                                          GCACCGGAACTTGTGTTTGTGTG   TGTG   GTCGCCCACTACGCACGTTATATG
    tv9 = make_tile_variant(10, "ACGGCAGTAGTTTTGCCGCTCGGTCGTCAGAATGTTTGGAGGGCGGTACGCACCGGAACTTGTGTTTGTGTGTGTGGTCGCCCACTACGCACGTTATATG".lower(), 4, start_tag="ACGGCAGTAGTTTTGCCGCTCGGT", end_tag="GTCGCCCACTACGCACGTTATATG")
    gv = make_genome_variant(21, 49, 79, 'GGCTAGAGATATCACCCTCTGCTACTCAAC', '-')
    GenomeVariantTranslation(tile_variant=tv9, genome_variant=gv, start=49, end=49).save()
#    gv = make_genome_variant(22, 52, 82, 'GGCTAGAGATATCACCCTCTGCTACTCAAC', '-', assembly=ASSEMBLY_18)
#    GenomeVariantTranslation(tile_variant=tv9, genome_variant=gv, start=49, end=49).save()
#    GenomeVariantTranslation(tile_variant=tv9, genome_variant=AAA_del_gv, start=26, end=26).save()
#    GenomeVariantTranslation(tile_variant=tv9, genome_variant=T_C_24_gv, start=24, end=25).save()
#    GenomeVariantTranslation(tile_variant=tv9, genome_variant=T_G_104_gv, start=71, end=72).save()
    #19 ACGGCAGTAGTTTTGCCGCTCGGT | CG | TCAGAATGTTTGGAGGGCGGTACG | GC | TAGAGATATCACCCTCTGCTACTC | AA | CGCACCGGAACTTGTGTTTGTGTG | TGTG | GTCGCCCACTACGCACGTTATATG ||
    #18 ACGGCAGTAGTTTTGCCGCTCGGT | TGAAATCAGAATGTTTGGAGGGCGGTACG   GC | TAGAGATATCACCCTCTGCTACTC | AA   CGCACCGGAACTTGTGTTTGTGTT   TGTG | GTCGCCCACTACGCACGTTATATG ||
    #   ACGGCAGTAGTTTTGCCGCTCGGT   T    ACAGAATGTTTGGAGGGCGGTACG   GC   TAGAGATATCACCCTCTGCTACTC
    tv = make_tile_variant(11, "ACGGCAGTAGTTTTGCCGCTCGGTTACAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTC".lower(), 2, start_tag="ACGGCAGTAGTTTTGCCGCTCGGT")
    GenomeVariantTranslation(tile_variant=tv, genome_variant=basic_snp_gv, start=24, end=25).save()
    GenomeVariantTranslation(tile_variant=tv, genome_variant=spanning_sub_gv, start=25, end=26).save()
#    GenomeVariantTranslation(tile_variant=tv, genome_variant=gaaat_a_gv, start=25, end=26).save()
    #19 ACGGCAGTAGTTTTGCCGCTCGGT | CG | TCAGAATGTTTGGAGGGCGGTACG | GC | TAGAGATATCACCCTCTGCTACTC | AA | CGCACCGGAACTTGTGTTTGTGTG | TGTG | GTCGCCCACTACGCACGTTATATG ||
    #18 ACGGCAGTAGTTTTGCCGCTCGGT | TGAAATCAGAATGTTTGGAGGGCGGTACG   GC | TAGAGATATCACCCTCTGCTACTC | AA   CGCACCGGAACTTGTGTTTGTGTT   TGTG | GTCGCCCACTACGCACGTTATATG ||
    #   ACGGCAGTAGTTTTGCCGCTCGGT   T  TTTCAGAATGTTTGGAGGGCGGTACG   GC   TAGAGATATCACCCTCTGCTACTC
    tv = make_tile_variant(12, "ACGGCAGTAGTTTTGCCGCTCGGTTTTTCAGAATGTTTGGAGGGCGGTACGGCTAGAGATATCACCCTCTGCTACTC".lower(), 2, start_tag="ACGGCAGTAGTTTTGCCGCTCGGT")
    GenomeVariantTranslation(tile_variant=tv, genome_variant=basic_del_gv, start=24, end=24).save()
    GenomeVariantTranslation(tile_variant=tv, genome_variant=spanning_ins_gv, start=24, end=27).save()
#    gv = make_genome_variant(27, 25, 29, 'GAAA', 'TT', assembly=ASSEMBLY_18)
#    GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=25, end=27).save()
    #19 ACGGCAGTAGTTTTGCCGCTCGGT | CG | TCAGAATGTTTGGAGGGCGGTACG | GC | TAGAGATATCACCCTCTGCTACTC | AA | CGCACCGGAACTTGTGTTTGTGTG | TGTG | GTCGCCCACTACGCACGTTATATG ||
    #18 ACGGCAGTAGTTTTGCCGCTCGGT | TGAAATCAGAATGTTTGGAGGGCGGTACG   GC | TAGAGATATCACCCTCTGCTACTC | AA   CGCACCGGAACTTGTGTTTGTGTT   TGTG | GTCGCCCACTACGCACGTTATATG ||
    #   ACGGCAGTAGTTTTGCCGCTCGG       CGTCAGAATGTTTGGAGGGCGGTACG
    tv_a = make_tile_variant(13, "ACGGCAGTAGTTTTGCCGCTCGGCGTCAGAATGTTTGGAGGGCGGTACG".lower(), 1, start_tag="ACGGCAGTAGTTTTGCCGCTCGGC")
    gv = make_genome_variant(23, 23, 24, 'T', '-')
    GenomeVariantTranslation(tile_variant=tv_a, genome_variant=gv, start=23, end=23).save()
#    gv = make_genome_variant(24, 23, 29, 'TTGAAA', 'CG', assembly=ASSEMBLY_18)
#    GenomeVariantTranslation(tile_variant=tv_a, genome_variant=gv, start=23, end=25).save()
    #19 ACGGCAGTAGTTTTGCCGCTCGGT | CG | TCAGAATGTTTGGAGGGCGGTACG | GC | TAGAGATATCACCCTCTGCTACTC | AA | CGCACCGGAACTTGTGTTTGTGTG | TGTG | GTCGCCCACTACGCACGTTATATG ||
    #18 ACGGCAGTAGTTTTGCCGCTCGGT | TGAAATCAGAATGTTTGGAGGGCGGTACG   GC | TAGAGATATCACCCTCTGCTACTC | AA   CGCACCGGAACTTGTGTTTGTGTT   TGTG | GTCGCCCACTACGCACGTTATATG ||
    #                                                                                                   CGCACCGGAACTTGTGTTTGTGTG   TGTG   ATCGCCCACTACGCACGTTATATG
    tv = make_tile_variant(int('3'+vv_min,16)+1, "CGCACCGGAACTTGTGTTTGTGTGTGTGATCGCCCACTACGCACGTTATATG".lower(), 1, end_tag="ATCGCCCACTACGCACGTTATATG")
    gv = make_genome_variant(25, 106, 107, 'G', 'A')
    GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=28, end=29).save()
#    gv = make_genome_variant(26, 109, 110, 'G', 'A', assembly=ASSEMBLY_18)
#    GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=28, end=29).save()
#    GenomeVariantTranslation(tile_variant=tv, genome_variant=T_G_104_gv, start=23, end=24).save()

    #19 ACGGCAGTAGTTTTGCCGCTCGGT | CG | TCAGAATGTTTGGAGGGCGGTACG | GC | TAGAGATATCACCCTCTGCTACTC | AA | CGCACCGGAACTTGTGTTTGTGTG | TGTG | GTCGCCCACTACGCACGTTATATG ||
    #18 ACGGCAGTAGTTTTGCCGCTCGGT | TGAAATCAGAATGTTTGGAGGGCGGTACG   GC | TAGAGATATCACCCTCTGCTACTC | AA   CGCACCGGAACTTGTGTTTGTGTT   TGTG | GTCGCCCACTACGCACGTTATATG ||
    #                                                                   TAGAGATATCACCCTCTGCTACTC        CGCACCGGAACTTGTGTTTGTGTG
    tv = make_tile_variant(int('2'+vv_min,16)+1, "TAGAGATATCACCCTCTGCTACTCCGCACCGGAACTTGTGTTTGTGTG".lower(), 1)
    gv = make_genome_variant(28, 76, 78, "AA", "-")
    GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=24, end=24).save()
#    gv = make_genome_variant(29, 79, 81, "AA", "-", assembly=ASSEMBLY_18)
#    GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=24, end=24).save()
#    GenomeVariantTranslation(tile_variant=tv, genome_variant=T_G_104_gv, start=47, end=48).save()
    #19 ACGGCAGTAGTTTTGCCGCTCGGT | CG | TCAGAATGTTTGGAGGGCGGTACG | GC | TAGAGATATCACCCTCTGCTACTC | AA | CGCACCGGAACTTGTGTTTGTGTG | TGTG | GTCGCCCACTACGCACGTTATATG ||
    #18 ACGGCAGTAGTTTTGCCGCTCGGT | TGAAATCAGAATGTTTGGAGGGCGGTACG   GC | TAGAGATATCACCCTCTGCTACTC | AA   CGCACCGGAACTTGTGTTTGTGTT   TGTG | GTCGCCCACTACGCACGTTATATG ||
    #                                                                   TAGAGATATCACCCTCTGCTACTC   AA   CGCACCGGAACTTGTGTTTGTGTT   TGTG   GTCGCCCACTACGCACGTTATATG
    tv = TileVariant.objects.get(tile_variant_int=int('2'+vv_min,16)+2)
    gv = make_genome_variant(30, 101, 102, 'G', 'T')
    GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=49, end=50).save()

    tv = make_tile_variant(int('1'+step_min+vv_min,16)+1, "", 1)
    gv = make_genome_variant(31, 130, 180, "AGAGAGCTGGCAGATGCCTTATGGAAGTGACTGCTACCGTTTGTTGACAC", "-")
    GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=0, end=0).save()
#    gv = make_genome_variant(32, 133, 183, "AGAGAGCTGGCAGATGCCTTATGGAAGTGACTGCTACCGTTTGTTGACAC", "-", assembly=ASSEMBLY_18)
#    GenomeVariantTranslation(tile_variant=tv, genome_variant=gv, start=0, end=0).save()

def make_entire_library(multiple_assemblies=False):
    make_reference(multiple_assemblies=multiple_assemblies)
    if multiple_assemblies:
        make_19_and_18_libraries()
    else:
        make_only_19_library()

def make_lantern_translators(skip_path_0=False, skip_path_1=False):
    def mk_name(step, variant_value, path=0, version=0):
        p = hex(path).lstrip('0x').zfill(NUM_HEX_INDEXES_FOR_PATH)
        v = hex(version).lstrip('0x').zfill(NUM_HEX_INDEXES_FOR_VERSION)
        s = hex(step).lstrip('0x').zfill(NUM_HEX_INDEXES_FOR_STEP)
        vv = hex(variant_value).lstrip('0x').zfill(NUM_HEX_INDEXES_FOR_CGF_VARIANT_VALUE)
        return string.join([p,v,s,vv],sep='.')
    def mk_int(step, variant_value, path=0, version=0):
        p = hex(path).lstrip('0x').zfill(NUM_HEX_INDEXES_FOR_PATH)
        v = hex(version).lstrip('0x').zfill(NUM_HEX_INDEXES_FOR_VERSION)
        s = hex(step).lstrip('0x').zfill(NUM_HEX_INDEXES_FOR_STEP)
        vv = hex(variant_value).lstrip('0x').zfill(NUM_HEX_INDEXES_FOR_VARIANT_VALUE)
        return int(v+p+s+vv,16)
    if not skip_path_0:
        LanternTranslator(lantern_name=mk_name(0,0), tile_variant_int=1).save()
        LanternTranslator(lantern_name=mk_name(0,1), tile_variant_int=2).save()
        LanternTranslator(lantern_name=mk_name(0,2), tile_variant_int=3).save()
        LanternTranslator(lantern_name=mk_name(0,3), tile_variant_int=4).save()
        LanternTranslator(lantern_name=mk_name(0,4), tile_variant_int=5).save()
        LanternTranslator(lantern_name=mk_name(0,5), tile_variant_int=6).save()
        LanternTranslator(lantern_name=mk_name(0,6), tile_variant_int=7).save()
        LanternTranslator(lantern_name=mk_name(0,7), tile_variant_int=8).save()
        LanternTranslator(lantern_name=mk_name(0,8), tile_variant_int=9).save()
        LanternTranslator(lantern_name=mk_name(0,9), tile_variant_int=10).save()
        LanternTranslator(lantern_name=mk_name(0,10), tile_variant_int=11).save()
        LanternTranslator(lantern_name=mk_name(0,11), tile_variant_int=12).save()
        LanternTranslator(lantern_name=mk_name(0,12), tile_variant_int=13).save()
        LanternTranslator(lantern_name=mk_name(1,0), tile_variant_int=mk_int(1,0)).save()
        LanternTranslator(lantern_name=mk_name(2,0), tile_variant_int=mk_int(2,2)).save()
        LanternTranslator(lantern_name=mk_name(2,1), tile_variant_int=mk_int(2,1)).save()
        LanternTranslator(lantern_name=mk_name(2,2), tile_variant_int=mk_int(2,0)).save()
        LanternTranslator(lantern_name=mk_name(3,0), tile_variant_int=mk_int(3,0)).save()
        LanternTranslator(lantern_name=mk_name(3,1), tile_variant_int=mk_int(3,1)).save()
    if not skip_path_1:
        LanternTranslator(lantern_name=mk_name(0,0,path=1), tile_variant_int=mk_int(0,0,path=1)).save()
        LanternTranslator(lantern_name=mk_name(0,1,path=1), tile_variant_int=mk_int(0,1,path=1)).save()
    LanternTranslator(lantern_name=mk_name(0,0,path=settings.CHR_PATH_LENGTHS[CHR_1]), tile_variant_int=mk_int(0,0,path=settings.CHR_PATH_LENGTHS[CHR_1])).save()
