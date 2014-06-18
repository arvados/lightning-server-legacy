package main

import "fmt"
import "flag"

import "os"
import "bufio"
import "time"

import "strings"
import "strconv"

import "runtime/pprof"
import "path"
import "log"

import "sort"

import "./aux"
import "./tile"

type Variation struct {
  varType string
  chr string
  seq string
  pos int
  length int
  annotation string
}


type ByAnchorTileId []string
func ( x ByAnchorTileId ) Len() int { return len(x) }
func ( x ByAnchorTileId ) Swap(i,j int) { x[i],x[j] = x[j],x[i] }
func ( x ByAnchorTileId ) Less(i,j int) bool {
  f := strings.SplitN( x[i], ".", -1 )
  g := strings.SplitN( x[j], ".", -1 )

  if len(f) != 3 { return false }
  if len(g) != 3 { return false }

  a,_ := strconv.ParseInt( f[0], 16, 0 )
  b,_ := strconv.ParseInt( g[0], 16, 0 )

  if a != b  { return a < b }

  a,_ = strconv.ParseInt( f[2], 16, 0 )
  b,_ = strconv.ParseInt( g[2], 16, 0 )

  return a < b
}


var upmap map[string]byte = map[string]byte{ "A" : 'A', "." : '.', "a" : 'A' , "c" : 'C' , "C" : 'C' , "t" : 'T' , "T" : 'T' , "g" : 'G' , "G" : 'G' }

func writeGVCFLineSimple( writer *bufio.Writer, chr string, pos1ref int, id string, ref string, alt string, qual string, filter, info, format, sample string ) {

  writer.WriteString(chr)
  writer.WriteString("\t")

  writer.WriteString( strconv.Itoa( pos1ref ) )
  writer.WriteString("\t")

  writer.WriteString(id)
  writer.WriteString("\t")

  writer.WriteByte( upmap[ref] )
  writer.WriteString("\t")

  writer.WriteByte( upmap[alt] )
  writer.WriteString("\t")

  writer.WriteString(qual)
  writer.WriteString("\t")

  writer.WriteString(filter)
  writer.WriteString("\t")

  writer.WriteString(info)
  writer.WriteString("\t")

  writer.WriteString(format)
  writer.WriteString("\t")

  writer.WriteString(sample)
  writer.WriteString("\n")

}

func writeGVCFLineRef( writer *bufio.Writer, chr string, pos1ref int, id string, ref string, alt string, qual string, filter, info string, pos1ref_end_incl int, format, sample string ) {
  writer.WriteString(chr)
  writer.WriteString("\t")

  writer.WriteString( strconv.Itoa( pos1ref ) )
  writer.WriteString("\t")

  writer.WriteString(id)
  writer.WriteString("\t")

  writer.WriteByte( upmap[ref] )
  writer.WriteString("\t")

  writer.WriteByte( upmap[alt] )
  writer.WriteString("\t")

  writer.WriteString(qual)
  writer.WriteString("\t")

  writer.WriteString(filter)
  writer.WriteString("\t")

  if len(info) > 0 {
    writer.WriteString(info)
    writer.WriteString(":")
  }
  writer.WriteString( "END=" )
  writer.WriteString( strconv.Itoa(pos1ref_end_incl) )
  writer.WriteString("\t")

  writer.WriteString(format)
  writer.WriteString("\t")

  writer.WriteString(sample)
  writer.WriteString("\n")

}

func writeGVCFLine( writer *bufio.Writer, chr string, pos1ref int, id string, ref string, alt string, qual string, filter, info, format, sample string ) {
  writer.WriteString(chr)
  writer.WriteString("\t")

  writer.WriteString( strconv.Itoa( pos1ref ) )
  writer.WriteString("\t")

  writer.WriteString(id)
  writer.WriteString("\t")

  writer.WriteString( strings.ToUpper(ref) )
  writer.WriteString("\t")

  writer.WriteString( strings.ToUpper(alt) )
  writer.WriteString("\t")

  writer.WriteString(qual)
  writer.WriteString("\t")

  writer.WriteString(filter)
  writer.WriteString("\t")

  writer.WriteString(info)
  writer.WriteString("\t")

  writer.WriteString(format)
  writer.WriteString("\t")

  writer.WriteString(sample)
  writer.WriteString("\n")

}

func printUsage() {
  fmt.Println("usage:")
  fmt.Println("  fastj2gvcf -i|-input-fastj FASTJFILE -L|-library-fastj LIBFASTJ [-o|-output-gvcf OUTGVCFFILE]")
  fmt.Println("    -i|-input-fastj    input fastj file")
  fmt.Println("    -L|-library-fastj  library fastj file")
  fmt.Println("    [-o|-output-gvcf]  output gvcf file (default to stdout)")
}

func printHeader( writer *bufio.Writer ) {
  writer.WriteString("###fileformat=VCFv4.1\n")

  t := time.Now()
  ts := fmt.Sprintf("%d%d%d", t.Year(), t.Month(), t.Day() )

  //writer.WriteString( fmt.Sprintf("##fileDate=%s\n", time.Now().Local().Format("20140523")) )
  writer.WriteString( fmt.Sprintf("##fileDate=%s\n", ts ) )
  writer.WriteString("##source=fastj2gvcf\n")
  //writer.WriteString("##sitesMaxDepth_chr18=95.2548674154515\n")
  //writer.WriteString("##indelsMaxDepth_chr18=97.6440108699989\n")
  writer.WriteString("##FILTER=<ID=QGX20,Description=\"Locus genotype quality is less than 20 or not computable.\">\n")
  writer.WriteString("##FILTER=<ID=QGT30,Description=\"Locus genotype quality is less than 30 or not computable.\">\n")
  writer.WriteString("##FILTER=<ID=FILT30,Description=\"More than 30% of bases at a site are filtered out.\">\n")
  writer.WriteString("##FILTER=<ID=MaxSB,Description=\"SNV strand bias value (SNVSB) exceeds 10\">\n")
  writer.WriteString("##FILTER=<ID=MaxHpol,Description=\"SNV contextual homopolymer length (SNVHPOL) exceeds 6\">\n")
  writer.WriteString("##FILTER=<ID=SitesMaxDepth,Description=\"Site occurs at a filtered depth greater than 'sitesMaxDepth'.\">\n")
  writer.WriteString("##FILTER=<ID=DPUX6,Description=\"Site min depth less than 6.\">\n")
  writer.WriteString("##FILTER=<ID=ICSL_FILT,Description=\"Not validated by Illumina Clinical Services Laboratory.\">\n")
  writer.WriteString("##FILTER=<ID=IndelsMaxDepth,Description=\"Indel occurs at a depth greater than 'indelsMaxDepth'.\">\n")
  writer.WriteString("##FILTER=<ID=REPEAT8,Description=\"Indel occurs in a homopolymer or dinucleotide track with a reference repeat greater than 8.\">\n")
  writer.WriteString("##FILTER=<ID=IndelConflict,Description=\"Conflicting indel/breakend evidence in region.\">\n")
  writer.WriteString("##FILTER=<ID=SiteConflict,Description=\"Site conflicts with indel/breakend evidence in region.\">\n")
  writer.WriteString("##FORMAT=<ID=GT,Number=1,Type=String,Description=\"Genotype\">\n")
  writer.WriteString("##FORMAT=<ID=GQX,Number=1,Type=Integer,Description=\"Minimum of {Genotype quality assuming variant position,Genotype quality assuming non-variant position}\">\n")
  writer.WriteString("##FORMAT=<ID=DPU,Number=1,Type=Integer,Description=\"Basecalls used to genotype site after filtration\">\n")
  writer.WriteString("##FORMAT=<ID=DPF,Number=1,Type=Integer,Description=\"Basecalls filtered from input prior to site genotyping\">\n")
  writer.WriteString("##FORMAT=<ID=AU,Number=4,Type=Integer,Description=\"Used A,C,G,T basecalls greater than Q20\">\n")
  writer.WriteString("##FORMAT=<ID=SNVSB,Number=1,Type=Float,Description=\"SNV site strand bias\">\n")
  writer.WriteString("##FORMAT=<ID=SNVHPOL,Number=1,Type=Integer,Description=\"SNV contextual homopolymer length\">\n")
  writer.WriteString("##FORMAT=<ID=DPI,Number=1,Type=Integer,Description=\"Basecall depth associated with indel, taken from the preceeding site.\">\n")
  writer.WriteString("##FORMAT=<ID=IRS,Number=A,Type=Integer,Description=\"Number of intersecting reads supporting the indel allele with prob 0.999 or greater and at least 6 bases of breakpoint overlap.\">\n")
  writer.WriteString("##FORMAT=<ID=ARS,Number=A,Type=Integer,Description=\"Number of intersecting reads supporting an alternate to the indel allele according to the IRDS criteria.\">\n")
  writer.WriteString("##FORMAT=<ID=ORS,Number=A,Type=Integer,Description=\"Number of intersecting reads not strongly supporting the indel allele or one of its alternates according to the IRDS criteria.\">\n")
  //writer.WriteString("##source_20120825.1=/illumina/development/vcftools/vcftools_0.1.8a/bin/vcf-annotate -a /illumina/development/VEP2/VEP/annotations/HGMD/hgmd_variants.dat.gz -d key=INFO,ID=hgmd_id,Number=1,Type=String,Description=HGMD Variant ID -d key=INFO,ID=hgmd_disease,Number=1,Type=String,Description=HGMD Disease -d key=INFO,ID=hgmd_alleles,Number=1,Type=String,Description=HGMD wild-type/mutant annotation -c CHROM,FROM,TO,INFO/hgmd_id,INFO/hgmd_disease,INFO/hgmd_alleles\n")
  //writer.WriteString("##source_20120825.2=/illumina/development/vcftools/vcftools_0.1.8a/bin/vcf-annotate -a /illumina/development/VEP2/VEP/annotations/HGMD/hgmd_geneID_list.coords.dat.gz -d key=INFO,ID=hgmd_gene,Number=1,Type=String,Description=Gene with an annotated variant in HGMD -c CHROM,FROM,TO,INFO/hgmd_gene\n")
  //writer.WriteString("##source_20120825.3=/illumina/development/vcftools/vcftools_0.1.8a/bin/vcf-annotate -a /illumina/development/VEP2/VEP/annotations/GWAS/gwas.dat.gz -d key=INFO,ID=gwas_sig,Number=1,Type=String,Description=GWAS significance exponent -d key=INFO,ID=gwas_rr,Number=1,Type=String,Description=GWAS relative risk -d key=INFO,ID=gwas_raf,Number=1,Type=String,Description=GWAS risk allele frequency -d key=INFO,ID=gwas_id,Number=1,Type=String,Description=GWAS associated variant ID -d key=INFO,ID=gwas_allele,Number=1,Type=String,Description=GWAS associated allele -d key=INFO,ID=gwas_association,Number=1,Type=String,Description=GWAS description -c CHROM,FROM,TO,INFO/gwas_sig,INFO/gwas_rr,INFO/gwas_raf,INFO/gwas_id,INFO/gwas_allele,INFO/gwas_association\n")
  //writer.WriteString("##source_20120825.4=/illumina/development/vcftools/vcftools_0.1.8a/bin/vcf-annotate -a /illumina/development/VEP2/VEP/annotations/CONS/phastCons_placental_elements.dat.gz -d key=INFO,ID=phastCons,Number=0,Type=Flag,Description=overlaps a phastCons element -c CHROM,FROM,TO,INFO/phastCons\n")
  //writer.WriteString("##source_20120825.5=/illumina/development/vcftools/vcftools_0.1.8a/bin/vcf-annotate -a /illumina/development/VEP2/VEP/annotations/1000/onek_dbsnp_vep_annotated.dat.gz -d key=INFO,ID=AA,Number=1,Type=String,Description=Ancestral Allele, ftp://ftp.1000genomes.ebi.ac.uk/vol1/ftp/pilot_data/technical/reference/ancestral_alignments/README -d key=INFO,ID=AF,Number=1,Type=Float,Description=Global Allele Frequency based on AC/AN -d key=INFO,ID=AMR_AF,Number=1,Type=Float,Description=Allele Frequency for samples from AMR based on AC/AN -d key=INFO,ID=ASN_AF,Number=1,Type=Float,Description=Allele Frequency for samples from ASN based on AC/AN -d key=INFO,ID=AFR_AF,Number=1,Type=Float,Description=Allele Frequency for samples from AFR based on AC/AN -d key=INFO,ID=EUR_AF,Number=1,Type=Float,Description=Allele Frequency for samples from EUR based on AC/AN -d key=INFO,ID=CSQ,Number=.,Type=String,Description=Consequence type as predicted by VEP. Format: Allele|Gene|Feature|Feature_type|Consequence|cDNA_position|CDS_position|Protein_position|Amino_acids|Codons|Existing_variation|PolyPhen|SIFT|CANONICAL|HGNC|MOTIF_NAME|MOTIF_POS|HIGH_INF_POS|MOTIF_SCORE_CHANGE|Condel -c CHROM,FROM,TO,ID,REF,ALT,INFO/AA,INFO/AF,INFO/AMR_AF,INFO/ASN_AF,INFO/AFR_AF,INFO/EUR_AF,INFO/CSQ\n")
  //writer.WriteString("##source_20120825.6=/illumina/development/vcftools/vcftools_0.1.8a/bin/vcf-annotate -a /illumina/build/clia/Projects/UYG/PG0000566-BLD/Assembly/tmp.DFFYb18045/tmp.18022.personal.vep.dat.gz -d key=INFO,ID=CSQ,Number=.,Type=String,Description=Consequence type as predicted by VEP. Format: Allele|Gene|Feature|Feature_type|Consequence|cDNA_position|CDS_position|Protein_position|Amino_acids|Codons|Existing_variation|PolyPhen|SIFT|CANONICAL|HGNC|MOTIF_NAME|MOTIF_POS|HIGH_INF_POS|MOTIF_SCORE_CHANGE|Condel -c CHROM,FROM,TO,-,REF,ALT,-,-,-,-,-,-,INFO/CSQ\n")
  writer.WriteString("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSAMPLE\n")

}

func main() {



  // Parse options, setup input/output and load fastj library.
  //
  fastjFn     := flag.String( "i", "", "input fastj file" )
  fastjFnLong := flag.String( "input-fastj", "", "input fastj file" )

  outgvcfFn       := flag.String( "o", "", "output gvcf file (default to stdout)" )
  outgvcfFnLong   := flag.String( "output-gvcf", "", "output gvcf file (default to stdout)" )

  fastjLibrary      := flag.String( "L", "", "fastj reference library" )
  fastjLibraryLong  := flag.String( "library-fastj", "", "fastj reference library" )

  profileFlag   := flag.Bool( "profile", false, "profile runtime" )
  noHeaderFlag    := flag.Bool( "N", false, "do not print header" )

  flag.Parse()

  if *profileFlag {
    profFn := fmt.Sprintf("%s.prof", path.Base( os.Args[0] ))

    f, err := os.Create( profFn )
    if err != nil { log.Fatal(err) }
    pprof.StartCPUProfile(f)
    defer pprof.StopCPUProfile()
  }



  if (len(*fastjLibrary) == 0)  && (len(*fastjLibraryLong) == 0) {
    fmt.Println("must provide fastj library")
    printUsage()
    os.Exit(1)
  }

  var inpFn string
  if len(*fastjFn) > 0 {
    inpFn = *fastjFn
  } else if len(*fastjFnLong) > 0 {
    inpFn = *fastjFnLong
  }

  if len(inpFn) == 0 {
    fmt.Println("invalid input fastj file")
    printUsage()
    os.Exit(1)
  }


  outFn := "-"

  if len(*outgvcfFn) > 0 {
    outFn = *outgvcfFn
  } else if len(*outgvcfFnLong) > 0 {
    outFn = *outgvcfFnLong
  }


  libraryTileSet := tile.NewTileSet( 24 )
  if len(*fastjLibrary) > 0 {
    err := libraryTileSet.ReadFastjFile( *fastjLibrary )
    if err != nil { panic(err) }
  } else {
    err := libraryTileSet.ReadFastjFile( *fastjLibraryLong )
    if err != nil { panic(err) }
  }


  inpfp, inpscanner, err := aux.OpenScanner( inpFn )
  if err != nil { panic(err) }
  defer inpfp.Close()



  var outfp *os.File
  if outFn == "-" {
    outfp = os.Stdout
  } else {
    outfp,err = os.Create( outFn )
    if err != nil { panic(err) }
    defer outfp.Close()

  }

  writer := bufio.NewWriter( outfp )



  // Setup is done, now we can start processing
  // the (non-library) fastj.
  //

  tileSet := tile.NewTileSet(24)
  err = tileSet.FastjScanner( inpscanner )
  if err != nil { panic(err) }


  anchorTileIdList := []string{}
  for anchorTile,_ := range tileSet.TileCopyCollectionMap {
    anchorTileIdList = append( anchorTileIdList, anchorTile )
  }
  sort.Sort( ByAnchorTileId( anchorTileIdList ) )

  if !*noHeaderFlag {
    printHeader( writer )
    writer.Flush()
  }


  // TODO: sort by tile id
  //
  //for anchorTile,_ := range tileSet.TileCopyCollectionMap {
  for anchor_ind:=0 ; anchor_ind<len(anchorTileIdList); anchor_ind++ {
    anchorTile := anchorTileIdList[ anchor_ind ]

    writer.Flush()


    tcc := tileSet.TileCopyCollectionMap[ anchorTile ]

    // Generate the reference sequence
    //
    libraryTile := libraryTileSet.TileCopyCollectionMap[ anchorTile ]
    refSeq := fmt.Sprintf("%s%s%s", libraryTile.StartTag, libraryTile.Body[0], libraryTile.EndTag )

    // Generate the raw sequence for this tile
    //
    rawSeq := fmt.Sprintf("%s%s%s", tcc.StartTag, tcc.Body[0], tcc.EndTag )


    // We need to reference it back to the hg19 build, so find out the
    // starting tile position in hg19.
    //
    header_json := tcc.MetaJson[0]
    notes := header_json.Notes

    buildFound, chr, hg19_s_0ref, hg19_e_0ref := false, "", -1, -1

    // Find our hg19 build in the locus field
    //
    for i:=0; i<len(header_json.Locus); i++ {

      build_hg19_fields := strings.Fields( header_json.Locus[i]["build"] )

      if build_hg19_fields[0] != "hg19" { continue }

      chr = build_hg19_fields[1]
      hg19_s_0ref,_ = strconv.Atoi( build_hg19_fields[2] )
      hg19_e_0ref,_ = strconv.Atoi( build_hg19_fields[3] )

      _ = hg19_e_0ref

      buildFound = true


    }

    if !buildFound {
      //writer.WriteString( fmt.Sprintf("# tile discarded, could not find hg19 build (anchor tile %s)\n", anchorTile )  )
      continue
    }

    // Collect all the annotations stored as notes in the
    // tile.
    //
    // TODO: sort on start position
    //
    varArray := []Variation{}
    for i:=0; i<len(notes); i++ {

      note := notes[i]

      annotation := ""
      if strings.IndexAny( notes[i], ";" ) >= 0 {
        tv := strings.SplitN(notes[i], ";", -1 )
        note = tv[0]
        annotation = tv[1]
      }

      note_field := strings.Fields( note )
      if len(note_field) < 7 {
        //writer.WriteString( fmt.Sprintf("# note discarded, not enough fields in '%s' (anchor tile %s)\n", notes[i], anchorTile )  )
        continue
      }

      if note_field[0] == "hg19" {
        v := Variation{}
        v.chr = note_field[1]

        v.pos,err = strconv.Atoi( note_field[6][ 1 : len(note_field[6])-1 ]  )
        v.varType = note_field[4]

        if v.varType == "DEL" {
          v.length,_ = strconv.Atoi( note_field[5] )
        } else {
          v.seq = note_field[5]
          v.length = len( note_field[5] )
        }

        v.annotation = annotation
        varArray = append( varArray, v )

      }

    }

    // We keep a pointiner into the 'raw' sequence (the sequence from
    // the fastj being converted) and to the 'ref' sequence (taken
    // from our fastj library).
    // On a reference or subsitution, both pointers are incremented.
    // On a deletion, the ref is incremented and the raw seq pointer isn't.
    // On an insertion, the raw seq pointer is incremented and the raw seq pointer isn't.
    // The appropriate base pair and ref are printed out for each of the cases.
    //

    seqpos := 0
    refpos := 0
    varind := 0
    for seqpos = 0; seqpos < len(rawSeq) ; {

      dn := len(rawSeq) - seqpos

      // We need to treat insertions and deletions specially since
      // we need to print out a reference base place
      // holder in the 'ALT' column.
      // Print out the reference sequence up to one
      // before the insertion/deletion, then print out the
      // reference sequence that is deleted .
      //
      if varind < len(varArray) {
        vv := varArray[varind]

        if (vv.varType == "DEL") || (vv.varType == "INS") {

          // Print out ref for all bases
          // up to one base before the start
          // of the deletion.
          //
          // e.g. DEL -1 implies:
          // ... AT A ...
          //

          //ds := seqpos - vv.pos - 1
          ds := vv.pos - seqpos - 1


          if ds > 0 {

            // End position is inclusive.
            //
            writeGVCFLineRef( writer, chr, hg19_s_0ref + refpos + 1, ".",
              rawSeq[ seqpos : seqpos + 1 ],
              ".",
              "200", "PASS", "", hg19_s_0ref + refpos + ds , "GT", "0/0" )
            refpos += ds
            seqpos += ds

          }

          /*
          for i:=0; i<ds; i++ {

            //DEBUG
            //
            if ((seqpos+i)<0) || ((seqpos+1)>=len(rawSeq)) {
              writer.WriteString( fmt.Sprintf("# OOB! ds %d, seqpos %d + i %d (%d), vv.pos %d  [%s]\n", ds, seqpos, i, seqpos+i, vv.pos, anchorTile ) )
              continue
            }


            if rawSeq[seqpos] != refSeq[ refpos ] {
              writer.WriteString( fmt.Sprintf("# MISMATCH(1) %s (@%d) =! %s (@%d)\n", rawSeq[seqpos:seqpos+1], seqpos, refSeq[refpos:refpos+1], refpos ) )
            }

            writeGVCFLineSimple( writer, chr, hg19_s_0ref + refpos + 1, ".",
              rawSeq[ seqpos : seqpos+1 ],
              ".",
              "200", "PASS", ".", "GT", "0/0" )

            refpos++
            seqpos++

          }
          */

          if vv.varType == "DEL" {

            writeGVCFLine( writer, chr, hg19_s_0ref + refpos + 1, ".",
              refSeq[ refpos : refpos - vv.length + 1 ],
              refSeq[ refpos : refpos+1 ],
              "200", "PASS", ".", "GT", "0/1" )

            seqpos++
            refpos += -vv.length + 1

          } else {

            writeGVCFLine( writer, chr, hg19_s_0ref + refpos + 1, ".",
              refSeq[ refpos : refpos+1 ],
              rawSeq[ seqpos : seqpos + vv.length + 1 ],
              "200", "PASS", ".", "GT", "0/1" )


            refpos++
            seqpos += vv.length + 1

          }

          varind++
          continue

        }


        // If it's neither a deletion or insertion, we
        // can just proceed as normal.
        //
        dn = varArray[varind].pos - seqpos

      }

      // Write out reference.  End position is inclusive.
      //

      writeGVCFLineRef( writer, chr, hg19_s_0ref + refpos + 1, ".",
        rawSeq[ seqpos : seqpos + 1 ],
        ".",
        "200", "PASS", "", hg19_s_0ref + refpos + dn , "GT", "0/0" )
      refpos += dn
      seqpos += dn

      /*
      for i:=0; i<dn; i++ {

        if seqpos >= len(rawSeq) {
          panic( fmt.Sprintf("seqpos %d > len(rawSeq) %d, anchorTile %s\n", seqpos, len(rawSeq), anchorTile ) )
        }

        if refpos >= len(refSeq) {
          panic( fmt.Sprintf("seqpos %d > len(rawSeq) %d, anchorTile %s\n", refpos, len(refSeq), anchorTile ) )
        }

        if rawSeq[ seqpos ] != refSeq[ refpos ] {
          writer.WriteString( fmt.Sprintf("# MISMATCH at anchor tile %s: rawSeq %s (%d), refSeq %s (%d)\n", anchorTile, rawSeq[seqpos:seqpos+1], seqpos, refSeq[refpos:refpos+1], refpos ) )
        }

        writeGVCFLineSimple( writer, chr, hg19_s_0ref + refpos + 1, ".",
          rawSeq[ seqpos : seqpos+1 ],
          ".",
          "200", "PASS", ".", "GT", "0/0" )

        refpos++
        seqpos++
      }
      */

      // Write out SNP or SUB
      //
      if varind < len(varArray) {
        vv := varArray[varind]

        if (vv.varType == "SUB") || (vv.varType == "SNP") {
          for i:=0; i<vv.length; i++ {

            writeGVCFLineSimple( writer, chr, hg19_s_0ref + refpos + i + 1, ".",
              refSeq[ refpos+i : refpos+i+1 ],
              rawSeq[ seqpos+i : seqpos+i+1 ],
              "200", "PASS", ".", "GT", "0/1" )
          }

          refpos += vv.length
          seqpos += vv.length
        } else {
          writer.WriteString( fmt.Sprintf("# ERROR: unknown variation type '%s' at anchor tile '%s', seqpos %d, refpos %d\n", vv.varType, anchorTile, seqpos, refpos ) )
        }

        varind++
      }

    }

    if seqpos != len(rawSeq) {
      writer.WriteString(  fmt.Sprintf("# ERROR: Tile did not fully output! %s", anchorTile ) )
    }

  }

  writer.Flush()

}
