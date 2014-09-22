// Sample usage:
//
// ./regexTileSetFromGff -i /scratch/tmp/chr19_band2_s13900000_e14000000.gff.gz  \
//                       -f /scratch/ref/hg19.fj/chr19_band2_s13900000_e14000000.fj.gz \
//                       -fasta-chromosome /scratch/ref/hg19.fa/chr19.fa \
//                       -o -
//

// TODO:
//
//  - error checking (verification)
//  - Proper variantion/gap annotation on tags.  Right now this is a bit of a hodge
//    podge when it comes to variants crossing a single (or more) tile variants or
//    gaps crossing multiple tile variants, along with their associated annotations
//    whent hey fall on tags.
//    Right now, gaps are at least labelled if they crossover, though where exactly
//    needs to be inferred from the gap line and the build/locus annotation.
//    INDELs only handle the case then they cross over at most once and an INDEL covers
//    more than two tiles, it will not be annotated correctly.  SUBs/SNPs should be
//    handled properly.
//

// NOTES
// =====

// Regex
// -----
//
// The basic idea is to create a regular expression that excapsulates the
// unphased data.  We know the variants but not the phase.  If the
// variants fall in the middle of the tile, this is pretty straight forward.
// Things get a little more complicated when they cross left or right boundaires
// of tags.
//
// SNPs don't cross tag boundaries, so these can be handled without much trouble.
//
// SUBs and INDELs can cross tag boundaries.  Instead of worrying which portion falls
// on which tag, we assume all SUBs and INDELs fall on the 'left' and eat into any
// tags or tiles that fall to the right of it.
//
// This is a departure from the explicit sequence generation as INDELs previously
// would be considered as the composition of a substitution followed by a deletion
// or insertion.
//
// An example 'regex' tile sequence is as follows:
//
// ttgg actg cttg | acactttg (ac|gt) aacg [ac] ccga (acacacac|gcgc) | -- actg gtca
//
// Where '|' indicate tag boundaries.
// The SNPs are represented by the regex character set ('[]'), INDELs and SUBs are represented
// by ('()') and the '-'s indicate that the INDEL or SUB earlier in the tile sequence
// ate away the tag sequence.
//
// Note the tag sequence will just be shorter and will not explicitely have the '-'s in their
// sequence.

// Gaps
// ----
//
// Gaps are filled in with the relevant reference genome.  An annotation is generated and put in the
// JSON 'notes' array.


/***************************************************

 GFF notes:

   GFF is 1 based, end inclusive.
   Inserts have an end position one below the start position.

   In the variable 'comments' below (the comments section of the GFF file),
   phase information is not necessarily to be trusted.
   The comments pass through the order of what was reported by the GVCF
   file.  So, for example, if a SNP was reported as:


 chr1    CGI     SNP     53206   53206   .       +       .       alleles G/C;db_xref dbsnp.100:rs2854676;ref_allele G

   Indicates the GVCF had allele 1 as ref and allele 2 as the SNP variant C;


 chr1    CGI     SNP     82162   82162   .       +       .       alleles A/C;db_xref dbsnp.92:rs1815132;ref_allele C

   Indicates the GVCF had allele 1 as the SNP variant A and had allele 2 as ref.


 chr1    CGI     SNP     548491  548491  .       +       .       alleles T;db_xref dbsnp.100:rs2792860,dbsnp.131:rs75892356;ref_allele C

   Indicates both alleles had the SNP variant T different from ref C.


 chr1    CGI     INDEL   250237  250237  .       +       .       alleles T/-;ref_allele T

   Indicates a reported deletion in allele 2 of 1bp.


 chr1    CGI     INDEL   567240  567240  .       +       .       alleles -;db_xref dbsnp.131:rs78150957,dbsnp.129:rs60652689;ref_allele G

   Indicates a reported deletion of 1bp in both alleles.

 etc.  All the above were from hg19, in case that's relevant.



******************************************************/


package main

import "fmt"
import "os"
import "./aux"
import "strconv"
import "strings"
import "time"

import "bufio"

import "sort"
import "encoding/json"
import _ "compress/gzip"

import "flag"

import _ "math/rand"

import "crypto/md5"

import "./recache"
import "./tile"
import "./bioenv"

//var gOutputWriter bioenv.BioEnvHandle
var gBioEnvWriter bioenv.BioEnvHandle
var gOutputWriter *bufio.Writer


var gDebugFlag bool = false
//var gDebugFlag bool = true
var gDebugString string
var gRefGenome string = "hg19"

// In the future, REPORTED should be the default, but for
// now phase information should essentially be ignored,
// so we default to HETA.
//
var gVariantPolicy string = "REGEX"

type TileHeader struct {
  TileID string `json:"tileID"`
  Locus []map[ string ]string `json:"locus"`
  N int `json:"n"`
  CopyNum int `json:"copy"`
  StartTag string `json:"startTag"`
  EndTag string `json:"endTag"`
  Notes []string `json:"notes,omitempty"`
}



type GffScanState struct {
  nextTagStart int

  startPos []int
  startPosIndex int
  baseTileIdFromStartPosMap map[int]string

  endPos int

  gffCurSeq []byte
  refStart, refLen int

  gffLeftTagSeq, gffRightTagSeq []byte

  notes []string
  carryOverNotes []string
  simpleLocusBuild string

  md5sum [16]byte

  curChrom string

  TagLen int

  phase string

}

func (gss *GffScanState) PrintState() {
  fmt.Printf("nextTagStart %d\n", gss.nextTagStart)
  fmt.Printf("len(startPos) %d\n", len(gss.startPos) )
  fmt.Printf("startPosIndex %d\n", gss.startPosIndex )
  fmt.Printf("endPos %d\n", gss.endPos )
  fmt.Printf("gffCurSeq %s\n", gss.gffCurSeq )
  fmt.Printf("refStart %d, refLen %d\n", gss.refStart, gss.refLen )
  fmt.Printf("simpleLocusBuild %s\n", gss.simpleLocusBuild )
  fmt.Printf("curChrom %s\n", gss.curChrom)
  fmt.Printf("tagLen %d\n", gss.TagLen )
  fmt.Printf("phase %s\n", gss.phase )
  fmt.Printf("gffLeftTagSeq %s\n", string(gss.gffLeftTagSeq) )
  fmt.Printf("gffRightTagSeq %s\n", string(gss.gffRightTagSeq) )
}

var g_gffFileName *string
var g_fastjFileName *string
var g_chromFileName *string
var g_outputFastjFileName *string
var g_notes *string

var g_variantPolicy *string

var g_discardVariantOnTag *bool
var g_discardGaps *bool
var g_verboseFlag *bool

func init() {

  _ = time.Now()


  g_gffFileName = flag.String( "i", "", "Input GFF file")
  flag.StringVar( g_gffFileName, "input-gff", "", "Input GFF file")

  g_fastjFileName = flag.String( "f", "", "Input FastJ file")
  flag.StringVar( g_fastjFileName, "input-fastj", "", "Input FastJ file")

  g_chromFileName = flag.String( "c", "", "Input chromosome Fasta file")
  flag.StringVar( g_chromFileName, "fasta-chromosome", "", "Input chromosome Fasta file")

  g_outputFastjFileName = flag.String( "o", "-", "Output FastJ file")
  flag.StringVar( g_outputFastjFileName, "output-fastj", "-", "Output FastJ file")

  g_variantPolicy = flag.String( "P", gVariantPolicy, "Variant policy (one of 'REPORTED' - as reported in gff, 'HETA' - all het var. go to first allele, 'RANDOM' - choose random allele)")
  flag.StringVar( g_variantPolicy, "variant-policy", gVariantPolicy, "Variant policy (one of 'REPORTED' - as reported in gff, 'HETA' - all het var. go to first allele, 'RANDOM' - choose random allele)")


  g_verboseFlag = flag.Bool( "v", false, "Verbose flag")
  flag.BoolVar( g_verboseFlag, "verbose", false, "Verbose flag")

  g_notes = flag.String( "a", "", "Note annotation")
  flag.StringVar( g_notes, "note", "", "Note annotation")

  flag.Parse()

  if *g_variantPolicy == "HETA" {
    gVariantPolicy = "HETA"
  } else if *g_variantPolicy == "REPORTED" {
    gVariantPolicy = "REPORTED"
  } else if *g_variantPolicy == "RANDOM" {
    gVariantPolicy = "RANDOM"
  } else {
    gVariantPolicy = "HETA"
  }

  if len(*g_gffFileName)==0 {
    fmt.Fprintf( os.Stderr, "Provide input GFF file\n")
    flag.PrintDefaults()
    os.Exit(2)
  }

  if len(*g_fastjFileName)==0 {
    fmt.Fprintf( os.Stderr, "Provide input FastJ file\n")
    flag.PrintDefaults()
    os.Exit(2)
  }

  if len(*g_chromFileName)==0 {
    fmt.Fprintf( os.Stderr, "Provide chromosome FASTA file\n")
    flag.PrintDefaults()
    os.Exit(2)
  }

  var err error
  gBioEnvWriter,err = bioenv.CreateWriter( *g_outputFastjFileName )
  if err != nil { panic(err) }

  gOutputWriter = gBioEnvWriter.Writer

}


func (gss *GffScanState) generateTileStartPositions(referenceTileSet *tile.TileSet) {

  // Sort starting position of each of the tile.
  // hg(\d+) co-ordinates stored as 0ref in tile set.
  //
  for _,tcc := range referenceTileSet.TileCopyCollectionMap {
    a,_ := recache.FindAllStringSubmatch( `hg\d+ chr[^ ]* (\d+)(-\d+)? (\d+)(\+\d+)?`, tcc.Meta[0], -1 )

    s,_ := strconv.Atoi(a[0][1])
    e,_ := strconv.Atoi(a[0][3])

    gss.startPos = append( gss.startPos, s )
    gss.baseTileIdFromStartPosMap[s] = tcc.BaseTileId

    // Put in final endpoint
    //
    if len(a[0][4]) > 0 {
      gss.startPos = append( gss.startPos, e )
      gss.endPos = e
    }

  }

  if len(gss.startPos) < 2 { return }

  sort.Ints( gss.startPos )
  gss.nextTagStart = gss.startPos[1]
  gss.startPosIndex = 1

  gss.gffCurSeq = gss.gffCurSeq[0:0]
  gss.refStart = gss.startPos[0]
  gss.refLen = 0

  gss.gffLeftTagSeq = gss.gffLeftTagSeq[0:0]
  gss.gffLeftTagSeq = append( gss.gffLeftTagSeq, []byte("........................")... )

}




func NormalizeTileSeq( tileSeq []byte, leftlen int, rightlen int  ) {

  n := len(tileSeq)
  if n < 48 { return }

  for i:=0; i<leftlen; i++ {
    if (tileSeq[i] == 'a') || (tileSeq[i] == 'c') ||
       (tileSeq[i] == 't') || (tileSeq[i] == 'g') ||
       (tileSeq[i] == 'n') {
      tileSeq[i] -= 32
    }
  }

  for i:=0; i<rightlen; i++ {
    p := n-i-1
    if (tileSeq[p] == 'a') || (tileSeq[p] == 'c') ||
       (tileSeq[p] == 't') || (tileSeq[p] == 'g') ||
       (tileSeq[p] == 'n') {
      tileSeq[p] -= 32
    }
  }

  for i:=leftlen; i<(n-rightlen); i++ {
    if (tileSeq[i] == 'A') || (tileSeq[i] == 'C') ||
       (tileSeq[i] == 'T') || (tileSeq[i] == 'G') ||
       (tileSeq[i] == 'N') {
      tileSeq[i] += 32
    }
  }

}




// Each process function is in charge of updating the sequence and adding to the final tile set.  There
// is a lot of similarity, but they each need their own special handling of when the sequence extends over
// a tile boundary so for simplicity, they each handle the sequence.
//

func (gss *GffScanState) AddTile( finalTileSet *tile.TileSet, referenceTileSet *tile.TileSet ) {

  baseTileId,ok := gss.baseTileIdFromStartPosMap[ gss.refStart ]
  if !ok {
    //fmt.Printf("WARNING: refStart %d lookup not found (%s)\n", gss.refStart, *g_gffFileName )
    return
  }

  refTcc := referenceTileSet.TileCopyCollectionMap[ baseTileId ]

  header := TileHeader{}
  json.Unmarshal( []byte( refTcc.Meta[0] ), &header )


  NormalizeTileSeq( gss.gffCurSeq, len(gss.gffLeftTagSeq), len(gss.gffRightTagSeq) )

  f := strings.SplitN( baseTileId, ".", -1 )
  newTileId := fmt.Sprintf("%s.%s.%04s.000", f[0], f[1], f[2] )

  gOutputWriter.WriteString("> { ")
  gOutputWriter.WriteString( fmt.Sprintf("\"tileID\" : \"%s\"", newTileId ) )

  gss.md5sum = md5.Sum( gss.gffCurSeq )

  gOutputWriter.WriteString(", \"md5sum\":\"")

  for i:=0; i<len(gss.md5sum); i++ {
    gOutputWriter.WriteString( fmt.Sprintf("%02x", gss.md5sum[i]) )
  }

  gOutputWriter.WriteString("\"")

  gOutputWriter.WriteString( fmt.Sprintf(", \"locus\":[{\"build\":\"%s\"}]", header.Locus[0]["build"] ) )
  gOutputWriter.WriteString( fmt.Sprintf(", \"n\":%d", len(gss.gffCurSeq) ) )
  gOutputWriter.WriteString( fmt.Sprintf(", \"copy\":%d", 0 ) )
  gOutputWriter.WriteString( fmt.Sprintf(", \"startSeq\":\"%s\"", gss.gffLeftTagSeq) )
  gOutputWriter.WriteString( fmt.Sprintf(", \"endSeq\":\"%s\""  , gss.gffRightTagSeq) )
  gOutputWriter.WriteString( fmt.Sprintf(", \"startTag\":\"%s\"", refTcc.StartTag ) )
  gOutputWriter.WriteString( fmt.Sprintf(", \"endTag\":\"%s\""  , refTcc.EndTag ) )

  gss.notes = append( gss.notes, fmt.Sprintf( "unphased (%s)", *g_variantPolicy ) )

  if len(gss.notes) > 0 {
    gOutputWriter.WriteString(", \"notes\":[")
    for i:=0; i<len(gss.notes); i++ {
      if i>0 { gOutputWriter.WriteString(", ") }
      gOutputWriter.WriteString( fmt.Sprintf("\"%s\"", gss.notes[i]) )
    }
    gOutputWriter.WriteString("]")
  }

  gOutputWriter.WriteString("}\n")


  for i:=0; i<len(gss.gffCurSeq); i+=50 {
    e := i+50
    if (i+50) > len(gss.gffCurSeq) { e = len(gss.gffCurSeq) }
    gOutputWriter.WriteString( fmt.Sprintf("%s\n",  gss.gffCurSeq[i:e] ) )
  }
  gOutputWriter.WriteString("\n\n")


  gOutputWriter.Flush()

}

// Reduce current sequence, shift tags and update
// other state variables.
//
func (gss *GffScanState) AdvanceState() {

  gss.refStart = gss.nextTagStart
  gss.refLen = 0

  gss.notes = gss.notes[0:0]
  if len(*g_notes) > 0 { gss.notes = append( gss.notes, *g_notes) }
  if len(gss.carryOverNotes) > 0 { gss.notes = append(gss.notes, gss.carryOverNotes... ) }
  gss.carryOverNotes = gss.carryOverNotes[0:0]

  gss.gffLeftTagSeq = gss.gffLeftTagSeq[0:0]
  gss.gffLeftTagSeq = append( gss.gffLeftTagSeq, gss.gffRightTagSeq... )

  gss.gffRightTagSeq = gss.gffRightTagSeq[0:0]

  gss.gffCurSeq = gss.gffCurSeq[0:0]
  gss.gffCurSeq = append( gss.gffCurSeq, gss.gffLeftTagSeq... )

  gss.refLen = gss.TagLen

  gss.startPosIndex++
  if gss.startPosIndex >= len(gss.startPos) { return }

  gss.nextTagStart = gss.startPos[ gss.startPosIndex ]


}


func (gss *GffScanState) processREF( finalTileSet *tile.TileSet,
                                     referenceTileSet *tile.TileSet,
                                     chromFa []byte,
                                     refStartPos int, entryLen int ) {

  // Clamp if we spill over
  //
  if (refStartPos + entryLen) > gss.endPos {
    refStartPos = gss.endPos
    entryLen = 0
  }

  gapLen := refStartPos - (gss.refStart + gss.refLen)
  gapEndPos := refStartPos
  gapNote := ""

  if (gss.refStart + gss.refLen) < refStartPos {
    gss.notes = append( gss.notes , fmt.Sprintf("%s %s %d %d GAP %d %d", gRefGenome, gss.curChrom, gss.refStart+gss.refLen, refStartPos-1, gss.refLen, gapLen) )

    gapNote = fmt.Sprintf("gapOnTag %s %s %d %d GAP - %d", gRefGenome, gss.curChrom, gss.refStart+gss.refLen, refStartPos-1, gapLen)

  }


  // The refStartPos + entryLen (end of the reference sequence) has shot past the current tag
  // end boundary.  We want to peel off the head of the sequence, adding it to the finalTileSet
  // where appropriate.
  //
  for ; (refStartPos + entryLen) >= (gss.nextTagStart + gss.TagLen) ; {

    if gss.refStart == gss.startPos[ gss.startPosIndex-1 ] {

      // Add the rest of the ref sequence to the current sequence.
      //
      gss.gffCurSeq = append( gss.gffCurSeq, chromFa[ gss.refStart + gss.refLen : gss.nextTagStart + gss.TagLen ]... )

      // Update the tag with the remainder of it's sequence, either the full ref or a partial
      // subsequence of the ref if the right tag sequence already partially filled in.
      //
      refLenRemain := (gss.nextTagStart + gss.TagLen) - (gss.refStart + gss.refLen)
      if refLenRemain > gss.TagLen {
        gss.gffRightTagSeq = gss.gffRightTagSeq[0:0]
        gss.gffRightTagSeq = append( gss.gffRightTagSeq, chromFa[ gss.nextTagStart : gss.nextTagStart + gss.TagLen ]... )
      } else {
        gss.gffRightTagSeq = append( gss.gffRightTagSeq, chromFa[ gss.refStart + gss.refLen : gss.nextTagStart + gss.TagLen ]... )
      }

      gss.AddTile( finalTileSet, referenceTileSet )

    }

    // From this point on, the sequence must be ref, so just keep pushing the releveant
    // sequence onto gffCurSeq so it can get peeled off by the above.
    //

    if gapEndPos > (gss.refStart + gss.refLen) {
      gss.carryOverNotes = append( gss.carryOverNotes, gapNote )
    }

    gss.AdvanceState()

  }

  // Finally, append trailing reference sequence to gffCurSeq.
  //
  dn := (refStartPos + entryLen) - (gss.refStart + gss.refLen)
  gss.gffCurSeq = append( gss.gffCurSeq, chromFa[ gss.refStart + gss.refLen : gss.refStart + gss.refLen + dn ]... )


  // The "reference" right tag length is not necessarily the length of the right
  // tag, as the current sequence can hold insertions and deletions.
  //
  refLenRightTag := (gss.refStart + gss.refLen) - (gss.nextTagStart)
  if refLenRightTag < 0 { refLenRightTag = 0 }

  // We want to find how much to add to the right tag, taking into account
  // how much of the "right tag reference sequence" we've already accounted for.
  //
  refLenTagOverflow := (refStartPos + entryLen) - (gss.nextTagStart)
  refLenTagOverflow -= refLenRightTag
  if refLenTagOverflow > 0 {
    begRightTag := gss.nextTagStart + refLenRightTag
    gss.gffRightTagSeq = append( gss.gffRightTagSeq, chromFa[ begRightTag : begRightTag + refLenTagOverflow ]... )

    if gapEndPos > begRightTag {
      gss.carryOverNotes = append( gss.carryOverNotes, gapNote )
    }

  }

  gss.refLen += dn

}




// SNPs also happen here, as they can be thought of as a substitution of length 1 in this context.
//
// refStartPos is the beginning of the substitution sequence.  We will fill in everything from the current
// position up to the refStartPos with ref, then fill in the rest with the substitution.
//
// WORKING ON IT:
// if subvar crosses the boundary, we need to add a tile and also add the suffix of the (current) tile
// the the prefix of the next tile.
//
func (gss *GffScanState) processSNP( finalTileSet *tile.TileSet,
                                     referenceTileSet *tile.TileSet,
                                     chromFa []byte,
                                     refStartPos int,
                                     snpvar0 string,
                                     snpvar1 string,
                                     ref_seq string,
                                     comment string ) {

  // Fill in with reference.
  //
  if refStartPos > (gss.refStart + gss.refLen) {
    gss.processREF( finalTileSet, referenceTileSet, chromFa, refStartPos, 0 )
  }

  if refStartPos > (gss.refStart + gss.refLen) { return }

  regexSNP := fmt.Sprintf( "[%s%s]", snpvar0, snpvar1 )
  if snpvar0 == snpvar1 {
    regexSNP = fmt.Sprintf( "%s", snpvar0 )
  }

  gss.gffCurSeq = append( gss.gffCurSeq, regexSNP... )

  posInSeq := len(gss.gffCurSeq)
  commentString := fmt.Sprintf("%s %s %d %d SNP (%d) %s => %s",
    gRefGenome, gss.curChrom,
    gss.refStart + gss.refLen,  gss.refStart + gss.refLen + 1,
    posInSeq,
    ref_seq, regexSNP )

  gss.notes = append( gss.notes, comment )
  gss.notes = append( gss.notes, commentString )


  refLenRemain := (gss.nextTagStart + gss.TagLen) - (gss.refStart + gss.refLen)
  if refLenRemain < gss.TagLen {
    gss.gffRightTagSeq = append( gss.gffRightTagSeq, regexSNP... )
    gss.carryOverNotes = append( gss.carryOverNotes, fmt.Sprintf("ltag: %s", comment) )
    gss.carryOverNotes = append( gss.carryOverNotes, fmt.Sprintf("ltag: %s", commentString) )
  }


  if (refStartPos + 1) >= (gss.nextTagStart + gss.TagLen) {

    if gss.refStart == gss.startPos[ gss.startPosIndex-1 ] {
      gss.AddTile( finalTileSet, referenceTileSet )
    }
    gss.AdvanceState()

  }

  dn := (refStartPos + 1) - (gss.refStart + gss.refLen)
  gss.refLen += dn

}


// ...
//
func (gss *GffScanState) processAlteration( finalTileSet *tile.TileSet,
                                            referenceTileSet *tile.TileSet,
                                            chromFa []byte,
                                            refStartPos int,
                                            varType string,
                                            indelvar0 string,
                                            indelvar1 string,
                                            ref_seq string,
                                            comment string ) {

  // Fill in with reference.
  //
  if refStartPos > (gss.refStart + gss.refLen) {
    gss.processREF( finalTileSet, referenceTileSet, chromFa, refStartPos, 0 )
  }

  startPos := gss.startPos[ gss.startPosIndex-1 ]
  baseTileId := gss.baseTileIdFromStartPosMap[ startPos ]
  _ = baseTileId

  indelRegex := fmt.Sprintf( "(%s|%s)", indelvar0, indelvar1 )
  if indelvar0 == indelvar1 {
    indelRegex = indelvar0
  }
  prettyRefSeq := ref_seq
  if len(prettyRefSeq) == 0 { prettyRefSeq = "-" }

  commentString := fmt.Sprintf("%s %s %d %d %s %d %s => %s",
    gRefGenome, gss.curChrom,
    gss.refStart + gss.refLen,  gss.refStart + gss.refLen + len(ref_seq),
    varType,
    gss.refStart + gss.refLen - startPos,
    prettyRefSeq, indelRegex )

  gss.notes = append( gss.notes, comment )
  gss.notes = append( gss.notes, commentString )

  gss.gffCurSeq = append( gss.gffCurSeq, indelRegex... )
  refLenRemain := (gss.nextTagStart + gss.TagLen) - (gss.refStart + gss.refLen)
  if refLenRemain < gss.TagLen {
    gss.gffRightTagSeq = append( gss.gffRightTagSeq, indelRegex... )
    gss.carryOverNotes = append( gss.carryOverNotes, fmt.Sprintf("ltag: %s", comment) )
    gss.carryOverNotes = append( gss.carryOverNotes, fmt.Sprintf("ltag: %s", commentString) )
  }

  entryLen := len(ref_seq)

  // We've spilled over
  //
  for ; (refStartPos + entryLen) >= (gss.nextTagStart + gss.TagLen) ; {

    if gss.refStart == gss.startPos[ gss.startPosIndex-1 ] {
      gss.AddTile( finalTileSet, referenceTileSet )
    }
    gss.AdvanceState()

  }

  dn := (refStartPos + entryLen) - (gss.refStart + gss.refLen)
  gss.refLen += dn

}

// Parse the variants.
// This will pass through the phase information as inferred by the order
// of the variants.
// If the variants are homozygous non-ref, then both var0 and var1 are filled
// in with the appropriate value.
// All '-' sequences as they appear in the GFF are returned as blank strings.
//
// For example
// -----------
//
//  alleles A/C;...;ref_allele C
//
//  represents ref C, A on the first allele and C (ref) on the second allele.
//
//  alleles T;...;ref_allele G
//
//  represents ref G, T on the first allele and T on the second allele.
//
// This just passes pahse information through, so if the incoming phase information
// should be ignored, so should the resulting phase information.
//
func parseVariants( comment string ) (var0 string, var1 string, ref_seq string) {

  comments := strings.SplitN( comment, ";", -1 )

  m,_ := recache.FindAllStringSubmatch( `alleles ([^/]+)(/(.+))?`, comments[0] , -1 )
  var0 = m[0][1]
  var1 = m[0][2]
  if ( len(var1) > 0 )  { var1 = var1[1:] }
  if ( len(var1) == 0 ) { var1 = var0 }

  m,_ = recache.FindAllStringSubmatch( `ref_allele ([^;]+)`, comment, -1 )
  ref_seq = m[0][1]


  if var0 == "-" { var0 = "" }
  if var1 == "-" { var1 = "" }
  if ref_seq == "-" { ref_seq = "" }

  if gDebugFlag { fmt.Printf("# var1 %s, var2 %s, ref_seq %s\n", var0, var1, ref_seq ) }

  //if var0 == ref_seq { return var1, var0, ref_seq }
  return var0, var1, ref_seq

}

func main() {

  tagLen := 24

  gffFn := *g_gffFileName
  fastjFn := *g_fastjFileName
  chromFaFn := *g_chromFileName
  //outFastjFn := *g_outputFastjFileName
  gNoteLine := *g_notes

  //fastjWriter, err := bioenv.CreateWriter( *g_outputFastjFileName )
  //if err!=nil { panic( fmt.Sprintf("%s: %s", *g_outputFastjFileName, err) ) }
  //defer func() { fastjWriter.Flush(); fastjWriter.Close() }()

  //gDebugString = fmt.Sprintf( "%s %s %s %s %s", gffFn, fastjFn, chromFaFn, outFastjFn, gNoteLine )
  gDebugString = fmt.Sprintf( "%s %s %s %s %s", gffFn, fastjFn, chromFaFn, *g_outputFastjFileName, gNoteLine )


  //-----------------------------
  // Load the tile set for this band.
  //
  if *g_verboseFlag { fmt.Println("# loading", fastjFn, "into memory...") }
  referenceTileSet := tile.NewTileSet( tagLen )
  referenceTileSet.ReadFastjFile( fastjFn )

  finalTileSet := tile.NewTileSet( tagLen )
  _ = finalTileSet

  //
  //-----------------------------


  //-----------------------------
  // Initialize Gff Scan State
  //
  gss := GffScanState{}

  gss.phase = "(A|B)"

  gss.notes = make( []string, 0, 10 )
  if len(gNoteLine) > 0 { gss.notes = append( gss.notes, gNoteLine ) }

  // refStart is 0 based
  //
  gss.gffCurSeq = make( []byte, 0, 10 )
  gss.baseTileIdFromStartPosMap = make( map[int]string )
  gss.refStart, gss.refLen = -1, 0
  gss.TagLen = tagLen
  gss.carryOverNotes = make( []string, 0, 10 )

  gss.generateTileStartPositions( referenceTileSet )

  if len(gss.startPos) < 2 { 
    fmt.Printf("gss.startPos < 2 (%d), quiting (%s)\n", len(gss.startPos),  *g_gffFileName )
    os.Exit(0)
  }


  //
  //-----------------------------



  //-----------------------------
  // Load our hg reference band.
  //
  if *g_verboseFlag { fmt.Println("# loading", chromFaFn, "into memory...") }
  chromFa,err := aux.FaToByteArray( chromFaFn )
  if err != nil { panic(err) }
  _ = chromFa

  count := 0
  _ = count

  if *g_verboseFlag { fmt.Println("# reading gff") }

  //
  //-----------------------------


  gffReader,err := bioenv.OpenScanner( gffFn )
  if err != nil { panic(err) }
  defer gffReader.Close()

  line_no := -1

  for gffReader.Scanner.Scan() {
    l := gffReader.Scanner.Text()

    line_no += 1

    if len(l)==0 { continue }
    if l[0] == '#' { continue }
    if l[0] == '\n' { continue }
    if l[0] == ' ' { }

    fields := strings.SplitN( l, "\t", -1 )
    chrom := fields[0] ; _ = chrom

    gss.curChrom = chrom

    s,_ := strconv.Atoi(fields[3])
    e,_ := strconv.Atoi(fields[4])
    varType := fields[2]
    comment := fields[8]

    condensed_comment,_ := recache.ReplaceAllString( `\s+`, comment, " " )

    // converting to 0 based, end inclusive
    //
    s -= 1
    e -= 1

    if ( varType == "REF" ) {

      gss.processREF( finalTileSet, referenceTileSet, chromFa, s, e - s + 1 )

    } else if ( (varType == "INDEL") || (varType == "SUB") ) {

      indelvar0, indelvar1, ref_seq := parseVariants( comment )

      if indelvar0 <= indelvar1 {
        gss.processAlteration( finalTileSet, referenceTileSet, chromFa, s, varType, indelvar0, indelvar1, ref_seq, condensed_comment )
      } else {
        gss.processAlteration( finalTileSet, referenceTileSet, chromFa, s, varType, indelvar1, indelvar0, ref_seq, condensed_comment )
      }

    } else if ( varType == "SNP" ) {

      subvar0, subvar1, ref_seq := parseVariants( comment )

      if subvar0 <= subvar1 {
        gss.processSNP( finalTileSet, referenceTileSet, chromFa, s, subvar0, subvar1, ref_seq, condensed_comment )
      } else {
        gss.processSNP( finalTileSet, referenceTileSet, chromFa, s, subvar1, subvar0, ref_seq, condensed_comment )
      }

    } else {
      panic( fmt.Sprintf("unknown varType %s on line %d", varType, line_no) )
    }

  }

  gss.AddTile( finalTileSet, referenceTileSet )

  gBioEnvWriter.Flush()
  gBioEnvWriter.Close()

}
