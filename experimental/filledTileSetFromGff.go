// TODO:
//  - notice het/hom
//    * will report the full line from GFF, so one can infer het/hom.  Will report which reported het/hom it was.
//
//  - fastj output
//
//  - annotations in fastj
//
//  - band ends handling (synthetic insert of ref?)
//    *working for beginning?  Need to look at end (still a little weird).
//
//  - error checking (verification)
//
// INDELs are handled 'under the hood' as a substitution of the first min( len(refseq), len(indel) )
//   base pairs, followed by either an insertion or deletion, depending on whether len(indel) > len(refseq)
//   or len(indel) < len(refseq) respectively.  The annotation is an INDEL and if the INDEL is contained
//   inside a tile, this should be pretty transparent.  If the INDEL crosses a tile boundary, then the
//   implications of how the INDEL is done.  For example, if the first part of the synthetic INDEL (the
//   substitution) crosses the boundary, the first tile will contain part of the substitution, while the
//   next tile will contain the rest, including the latter portion of the substitution and the insertion
//   or deletion, depending.
// Here is a contrived example:
//
//  say we have (in 1ref):     INDEL 1001 1006  AGTAGT/-;ref_allele CCC
//
//  and for arguments sake we have a tile that ends at (0ref) 1002, then this INDEL would go from
//
//  xxxxxxxxxxxxxxxCC | Cxxxxxxxxxxxxxxxx
//
//  to
//
//  xxxxxxxxxxxxxxxAG | T(AGT)xxxxxxxxxxxxxxxx
//
//  Where the sequence in the parens () is an insertion and the '|' represents a tile boundary.
//

/***************************************************

 GFF notes:

   GFF is 1 based, with, end inclusive.
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

import _ "bufio"

import "sort"
import "encoding/json"
import _ "compress/gzip"

import "flag"

import "math/rand"

import "./recache"
import "./tile"
import "./bioenv"


var gDebugFlag bool = false
//var gDebugFlag bool = true
var gDebugString string
var gRefGenome string = "hg19"

// In the future, REPORTED should be the default, but for
// now phase information should essentially be ignored,
// so we default to HETA.
//
var gVariantPolicy string = "HETA"

type TileHeader struct {
  TileID string `json:"tileID"`
  Locus []map[ string ]string `json:"locus"`
  N int `json:"n"`
  CopyNum int `json:"copy"`
  StartTag string `json:"startTag"`
  EndTag string `json:"endTag"`
  Notes []string `json:"notes,omitempty"`
}


type TileStat struct {
  occurance, bpCount int
  stag_occurance, etag_occurance int
  stag_n, etag_n int
}

func (ts *TileStat) AddLeft( dbp int ) {
  ts.occurance += 1
  ts.bpCount += dbp

  ts.stag_occurance += 1
  ts.stag_n += dbp
}

func (ts *TileStat) AddRight( dbp int ) {
  ts.occurance += 1
  ts.bpCount += dbp

  ts.etag_occurance += 1
  ts.etag_n += dbp
}

func (ts *TileStat) AddBody( dbp int ) {
  ts.occurance += 1
  ts.bpCount += dbp
}

func (ts *TileStat) Advance() {
  ts.stag_n = ts.etag_n
  ts.stag_occurance = ts.etag_occurance

  ts.occurance = ts.etag_occurance
  ts.bpCount = ts.etag_n

  ts.etag_occurance = 0
  ts.etag_n = 0
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
  simpleLocusBuild string

  curChrom string

  TagLen int


  phase string


  // Statistics (for later use)
  //
  gapStat TileStat
  snpStat TileStat
  subStat TileStat
  insStat TileStat
  delStat TileStat

}


var g_gffFileName *string
var g_fastjFileName *string
var g_chromFileName *string
var g_outputFastjFileName *string
var g_notes *string

var g_variantPolicy *string
var g_randomSeed *int64

var g_discardVariantOnTag *bool
var g_discardGaps *bool
var g_verboseFlag *bool

func init() {

  g_gffFileName = flag.String( "i", "", "Input GFF file")
  flag.StringVar( g_gffFileName, "input-gff", "", "Input GFF file")

  g_fastjFileName = flag.String( "f", "", "Input FastJ file")
  flag.StringVar( g_fastjFileName, "input-fastj", "", "Input FastJ file")

  g_chromFileName = flag.String( "c", "", "Input chromosome Fasta file")
  flag.StringVar( g_chromFileName, "fasta-chromosome", "", "Input chromosome Fasta file")

  g_outputFastjFileName = flag.String( "o", "", "Output FastJ file")
  flag.StringVar( g_outputFastjFileName, "output-fastj", "", "Output FastJ file")

  g_variantPolicy = flag.String( "P", gVariantPolicy, "Variant policy (one of 'REPORTED' - as reported in gff, 'HETA' - all het var. go to first allele, 'RANDOM' - choose random allele)")
  flag.StringVar( g_variantPolicy, "variant-policy", gVariantPolicy, "Variant policy (one of 'REPORTED' - as reported in gff, 'HETA' - all het var. go to first allele, 'RANDOM' - choose random allele)")

  g_randomSeed = flag.Int64( "S", 1234, "Random seed (defaults to time)")
  flag.Int64Var( g_randomSeed, "seed", 1234, "Random seed (defaults to time)")

  // Disable these options for now
  //g_discardVariantOnTag = flag.Bool( "T", false, "Discard tile when a variant falls on a tag")
  //flag.BoolVar( g_discardVariantOnTag, "discard-variant-on-tag", false, "Discard tile when a variant falls on a tag")

  //g_discardGaps = flag.Bool( "G", false, "Discard tile when a gap falls within a tile")
  //flag.BoolVar( g_discardGaps , "discard-gaps", false, "Discard tile when a gap falls within a tile")

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

  if len(*g_outputFastjFileName)==0 {
    fmt.Fprintf( os.Stderr, "Provide output FastJ file\n")
    flag.PrintDefaults()
    os.Exit(2)
  }

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




// Each process* function is in charge of updating the sequence and addint to the final tile set.  There
// is a lot of similarity, but they each need their own special handling of when the sequence extends over
// a tile boundary so for simplicity, they each handle the sequence.
//

func (gss *GffScanState) AddTile( finalTileSet *tile.TileSet, referenceTileSet *tile.TileSet ) {

  baseTileId := gss.baseTileIdFromStartPosMap[ gss.refStart ]

  refTcc := referenceTileSet.TileCopyCollectionMap[ baseTileId ]

  /*
  fmt.Println("### DEBUG!");
  fmt.Println(">>>> baseTileId:", baseTileId)
  fmt.Printf("\n\n")
  //fmt.Println( string(gss.gffCurSeq) )
  */

  header := TileHeader{}
  json.Unmarshal( []byte( refTcc.Meta[0] ), &header )


  /*
  fmt.Printf("--(%d)>> %s\n", len(gss.gffLeftTagSeq), gss.gffLeftTagSeq )
  fmt.Printf("\n")
  */

  NormalizeTileSeq( gss.gffCurSeq, len(gss.gffLeftTagSeq), len(gss.gffRightTagSeq) )

  f := strings.SplitN( baseTileId, ".", -1 )
  newTileId := fmt.Sprintf("%s.%s.%04s.000", f[0], f[1], f[2] )

  fmt.Printf("> { ")
  //fmt.Printf("\"tileID\" : \"%s.%s\"", baseTileId, "000" )
  fmt.Printf("\"tileID\" : \"%s\"", newTileId )
  fmt.Printf(", \"locus\":[{\"build\":\"%s\"}]", header.Locus[0]["build"] )
  fmt.Printf(", \"n\":%d", len(gss.gffCurSeq) )
  fmt.Printf(", \"copy\":%d", 0 )
  fmt.Printf(", \"startSeq\":\"%s\"", gss.gffLeftTagSeq)
  fmt.Printf(", \"endSeq\":\"%s\""  , gss.gffRightTagSeq)
  fmt.Printf(", \"startTag\":\"%s\"", refTcc.StartTag )
  fmt.Printf(", \"endTag\":\"%s\""  , refTcc.EndTag )

  if len(gss.notes) > 0 {
    fmt.Printf(", \"notes\":[")
    for i:=0; i<len(gss.notes); i++ {
      if i>0 { fmt.Printf(", ") }
      fmt.Printf("\"%s\"", gss.notes[i])
    }
    fmt.Printf("]")
  }

  //DEBUG
  fmt.Printf(", \"phase\" : \"%s\"", gss.phase )

  fmt.Printf("}\n")


  for i:=0; i<len(gss.gffCurSeq); i+=50 {
    e := i+50
    if (i+50) > len(gss.gffCurSeq) { e = len(gss.gffCurSeq) }
    fmt.Printf("%s\n",  gss.gffCurSeq[i:e] )
  }
  fmt.Printf("\n\n")

  /*
  fmt.Printf("--(%d)<< %s\n", len(gss.gffRightTagSeq), gss.gffRightTagSeq )
  fmt.Printf("\n\n\n\n")
  */


}

// Reduce current sequence, shift tags and update
// other state variables.
//
func (gss *GffScanState) AdvanceState() {

  gss.refStart = gss.nextTagStart
  gss.refLen = 0

  gss.notes = gss.notes[0:0]
  if len(*g_notes) > 0 { gss.notes = append( gss.notes, *g_notes) }

  gss.gffLeftTagSeq = gss.gffLeftTagSeq[0:0]
  gss.gffLeftTagSeq = append( gss.gffLeftTagSeq, gss.gffRightTagSeq... )

  gss.gffRightTagSeq = gss.gffRightTagSeq[0:0]

  gss.gffCurSeq = gss.gffCurSeq[0:0]
  gss.gffCurSeq = append( gss.gffCurSeq, gss.gffLeftTagSeq... )

  gss.refLen = gss.TagLen

  gss.startPosIndex++
  //if gss.startPosIndex == len(gss.startPos) { return }
  if gss.startPosIndex >= len(gss.startPos) { return }

  gss.nextTagStart = gss.startPos[ gss.startPosIndex ]


  gss.gapStat.Advance()
  gss.snpStat.Advance()
  gss.subStat.Advance()
  gss.insStat.Advance()
  gss.delStat.Advance()
}


func (gss *GffScanState) processREF( finalTileSet *tile.TileSet,
                                     referenceTileSet *tile.TileSet,
                                     chromFa []byte,
                                     refStartPos int, entryLen int ) {

  if (refStartPos + entryLen) > gss.endPos {
    refStartPos = gss.endPos
    entryLen = 0
  }


  if (gss.refStart + gss.refLen) < refStartPos {
    gapLen := refStartPos - (gss.refStart + gss.refLen)
    //fmt.Println("   $>>>> GAP", gss.refLen, gapLen )

    gss.notes = append( gss.notes , fmt.Sprintf("%s %s %d %d GAP %d %d", gRefGenome, gss.curChrom, gss.refStart+gss.refLen, refStartPos-1, gss.refLen, gapLen) )

    gss.gapStat.AddBody( gapLen )
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
        gss.gffRightTagSeq = chromFa[ gss.nextTagStart : gss.nextTagStart + gss.TagLen ]
      } else {
        gss.gffRightTagSeq = append( gss.gffRightTagSeq, chromFa[ gss.refStart + gss.refLen : gss.nextTagStart + gss.TagLen ]... )
      }

      gss.AddTile( finalTileSet, referenceTileSet )

    }

    // From this point on, the sequence must be ref, so just keep pushing the releveant
    // sequence onto gffCurSeq so it can get peeled off by the above.
    //

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
func (gss *GffScanState) processSUB( finalTileSet *tile.TileSet,
                                     referenceTileSet *tile.TileSet,
                                     chromFa []byte,
                                     refStartPos int,
                                     subvar string,
                                     subType string,
                                     noteFlag bool ) {

  // Fill in with reference.
  //
  if refStartPos > (gss.refStart + gss.refLen) {

    gss.processREF( finalTileSet, referenceTileSet, chromFa, refStartPos, 0 )

  }

  /*
  //DEBUG
  fmt.Println("starting processSUB")
  fmt.Println( "   refStartPos:", refStartPos )
  */


  // Now refStartPos to entryLen contains only the SUB contained in subvar.
  //

  entryLen := len(subvar)

  // The refStartPos + entryLen (end of the reference sequence) has shot past the current tag
  // end boundary.  We want to peel off the head of the sequence, adding it to the finalTileSet
  // where appropriate.
  //
  // Here is some ascii art to help explain the reasoning of the below piece of code:
  //
  //                                                             /--tagLen---\
  //      |                       |                             |- - - - - - -
  //      |                       |                             |            '
  //  ----------------------------|||||||||||||||||||||||||||||||||||||||||||||||||||||||||----
  //      |\_____gss.refLen______/|\____________________refLenRemain_________/
  //      |                       |                             |- - - - - - -
  //      |                       |                             |
  //   gss.refStart             refStartPos               gss.nextTagStart
  //
  // Where '|||...|||' is the string to be substituted.
  //
  // (gss.refStart + gss.refLen == refStartPos) from the above 'gss.processREF' call.
  //

  lastNote := ""
  for ; (refStartPos + entryLen) >= (gss.nextTagStart + gss.TagLen) ; {


    //DEBUG
    //fmt.Fprintf(os.Stderr, "sub crosses tile boundary.  (refStartPos %d + entryLen %d) >= (gss.nextTagStart %d + gss.TagLen %d)\n",
    //  refStartPos, entryLen, gss.nextTagStart, gss.TagLen )


    if gss.refStart == gss.startPos[ gss.startPosIndex-1 ] {

      refLenRemain := (gss.nextTagStart + gss.TagLen) - (gss.refStart + gss.refLen)
      posInSeq := len(gss.gffCurSeq)

      //DEBUG
      fmt.Fprintf(os.Stderr, "overflow --> %s %s %d %d %s %s %d %d\n\n",
            gRefGenome, gss.curChrom, gss.refStart+gss.refLen, gss.nextTagStart+gss.TagLen-1,
            subType, subvar, posInSeq, refLenRemain )

      //DEBUG
      //fmt.Fprintf(os.Stderr, "valid start position, refLenRemain %d, posInSeq %d\n", refLenRemain, posInSeq )
      //fmt.Fprintf(os.Stderr, "  subvar %s (%d)\n", subvar, len(subvar) )
      //fmt.Fprintf(os.Stderr, "  gss.refStart %d + gss.refLen %d = %d\n", gss.refStart, gss.refLen, gss.refStart + gss.refLen )




      // Add the rest of the subvar to our current sequence.
      //
      gss.gffCurSeq        = append( gss.gffCurSeq, subvar[0:refLenRemain]... )

      //DEBUG
      //fmt.Println( "  @>>>>", subType, "--->", subvar, posInSeq, refLenRemain )

      if noteFlag {

        if len(lastNote) > 0 {
          gss.notes = append( gss.notes, lastNote )
        }

        curNote := fmt.Sprintf("%s %s %d %d %s %s %d %d",
            gRefGenome, gss.curChrom, gss.refStart+gss.refLen, gss.nextTagStart+gss.TagLen-1,
            subType, subvar, posInSeq, refLenRemain)
        gss.notes = append( gss.notes, curNote )

        lastNote = fmt.Sprintf("ltag: %s %s %d %d %s %s %d %d",
            gRefGenome, gss.curChrom, gss.refStart+gss.refLen, gss.nextTagStart+gss.TagLen-1,
            subType, subvar, posInSeq - len(gss.gffCurSeq) + gss.TagLen, refLenRemain)


      }

      // If the refLenRemain is greater than the tag length, then we need to add
      // to the right tag from the appropriate offset in the subvar string.
      // Otherwise we just add the appropriate amount (starting at offset 0)
      // fromt he subvar string.
      //
      if refLenRemain > gss.TagLen {
        //dbeg := gss.nextTagStart - gss.refStart
        dbeg := refLenRemain - gss.TagLen

        //DEBUG
        //fmt.Fprintf( os.Stderr, "DEBUG: len(subvar) %d\n", len(subvar) )
        //fmt.Fprintf( os.Stderr, "DEBUG: gss.refStart %d, gss.nextTagStart %d\n", gss.refStart, gss.nextTagStart )
        //fmt.Fprintf( os.Stderr, "DEBUG: dbeg %d, dbeg+taglen %d subvar %s\n", dbeg, dbeg+gss.TagLen, subvar )

        gss.gffRightTagSeq = append( gss.gffRightTagSeq, subvar[ dbeg : dbeg + gss.TagLen ]... )

        if subType == "SNP" {
          gss.snpStat.AddRight( gss.TagLen )
          gss.snpStat.AddBody( refLenRemain - gss.TagLen )
        } else if subType == "SUB"  {
          gss.subStat.AddRight( gss.TagLen )
          gss.subStat.AddBody( refLenRemain - gss.TagLen )
        }

      } else {
        gss.gffRightTagSeq = append( gss.gffRightTagSeq, subvar[ 0 : refLenRemain ]... )

        if subType == "SNP" {
          gss.snpStat.AddRight( refLenRemain )
        } else if subType == "SUB"  {
          gss.subStat.AddRight( refLenRemain )
        }


      }

      gss.AddTile( finalTileSet, referenceTileSet )

      subvar = subvar[refLenRemain:]

      //Not needed?
      //refStartPos += len(subvar)
      //entryLen     = len(subvar)

    }

    // From this point on, the sequence must be ref, so just keep pushing the releveant
    // sequence onto gffCurSeq so it can get peeled off by the above.
    //

    gss.AdvanceState()

  }

  if len(lastNote) > 0 {
    gss.notes = append( gss.notes, lastNote )
  }


  posInSeq := len(gss.gffCurSeq)


  // Finally, append trailing reference sequence to gffCurSeq.
  //
  dn := (refStartPos + entryLen) - (gss.refStart + gss.refLen)

  //REQUIRES MORE THOUGHT>>>
  if dn<=0 { return }

  //DEBUG
  //fmt.Println("dn:", dn, "refStartPos:", refStartPos, "entryLen:", entryLen, "gss.refStart:", gss.refStart, "gss.refLen:", gss.refLen)

  gss.gffCurSeq = append( gss.gffCurSeq, subvar[0:dn]... )


  //!!
  //fmt.Println("  @>>>>", subType, "--->", subvar, posInSeq, dn )

  if noteFlag {
    gss.notes = append( gss.notes , fmt.Sprintf("%s %s %d %d %s %s %d %d", gRefGenome, gss.curChrom, gss.refStart+gss.refLen, refStartPos+entryLen-1, subType, subvar, posInSeq, dn) )
  }



  // Add the right most portion of the subvar to the right tag if it falls
  // within the tag window.
  //
  subvarOffset := gss.nextTagStart - refStartPos
  if subvarOffset < len(subvar) {
    if subvarOffset < 0 { subvarOffset = 0 }
    gss.gffRightTagSeq = append( gss.gffRightTagSeq, subvar[subvarOffset:]... )


    if subType == "SNP" {
      gss.snpStat.AddRight( gss.TagLen )
      //gss.snpStat.AddBody( refLenRemain - gss.TagLen )
    } else if subType == "SUB"  {
      gss.subStat.AddRight( gss.TagLen )
      //gss.subStat.AddBody( refLenRemain - gss.TagLen )
    }


  }

  gss.refLen += dn

}



func (gss *GffScanState) processINS( finalTileSet *tile.TileSet, referenceTileSet *tile.TileSet, chromFa []byte, refStartPos int, ins_seq string, noteFlag bool ) {

  // Fill in with reference.
  //
  if refStartPos > (gss.refStart + gss.refLen) {
    gss.processREF( finalTileSet, referenceTileSet, chromFa, refStartPos, 0 )
  }

  // Since it's an insert, we don't need to advance the reference locations.  We have no
  // possibility of creating a new tile from this operation, since it all must fall
  // within a tile.  We only need to check to see if it falls within a tag boundary, and
  // if so, add it.
  //

  insPosInSeq := len(gss.gffCurSeq)

  gss.gffCurSeq = append( gss.gffCurSeq, ins_seq... )
  if refStartPos  >= gss.nextTagStart {
    gss.gffRightTagSeq = append( gss.gffRightTagSeq, ins_seq... )
  }

  //DEBUG
  //fmt.Println("   @>>>> INS", insPosInSeq, ins_seq  )

  if noteFlag {
    gss.notes = append( gss.notes , fmt.Sprintf("%s %s %d %d INS %d %s", gRefGenome, gss.curChrom, refStartPos, refStartPos-1, insPosInSeq, ins_seq ) )
  }

}



func (gss *GffScanState) processDEL( finalTileSet *tile.TileSet, referenceTileSet *tile.TileSet, chromFa []byte, refStartPos int, del_len int, noteFlag bool) {

  // Fill in with reference.
  //
  if refStartPos > (gss.refStart + gss.refLen) {
    gss.processREF( finalTileSet, referenceTileSet, chromFa, refStartPos, 0 )
  }

  /*
  //DEBUG
  fmt.Println("starting processDEL")
  fmt.Println( "   refStartPos:", refStartPos )
  */

  for ; (refStartPos + del_len) >= (gss.nextTagStart + gss.TagLen) ; {

    if gss.refStart == gss.startPos[ gss.startPosIndex-1 ] {

      //refLenRemain := (gss.nextTagStart + gss.TagLen) - (gss.refStart + gss.refLen)
      posInSeq := len(gss.gffCurSeq)

      //DEBUG
      //fmt.Println("  @>>>> DEL", posInSeq, del_len )

      if noteFlag {
        gss.notes = append( gss.notes , fmt.Sprintf("%s %s %d %d DEL %d %d", gRefGenome, gss.curChrom, refStartPos, refStartPos+del_len-1, posInSeq, del_len) )
      }

      // Since it's a deletion, nothin need be added to the right tag sequence
      //

      gss.AddTile( finalTileSet, referenceTileSet )

    }

    gss.AdvanceState()

  }

  offset := gss.refLen
  dn := (refStartPos + del_len) - (gss.refStart + gss.refLen)


  // DEBUG
  //fmt.Println( "  >>>> DEL", offset, dn )

  if noteFlag {
    gss.notes = append( gss.notes , fmt.Sprintf("%s %s %d %d DEL %d %d", gRefGenome, "chZ", gss.refStart + gss.refLen, gss.refStart + gss.refLen + del_len - 1, offset, -dn) )
  }

  gss.refLen += dn

}

func parseINDEL( comment string ) ( var0 string, var1 string, ref_seq string ) {

  comments := strings.SplitN( comment, ";", -1 )

  m,_ := recache.FindAllStringSubmatch( `alleles ([^/]+)(/(.+))?`, comments[0] , -1 )
  var0 = m[0][1]
  var1 = m[0][2]
  if ( len(var1) > 0 ) { var1 = var1[1:] }

  m,_ = recache.FindAllStringSubmatch( `ref_allele ([^;]+)`, comment, -1 )
  ref_seq = m[0][1]

  return

}

// working on it....
//
func (gss *GffScanState) processINDEL( finalTileSet *tile.TileSet, referenceTileSet *tile.TileSet, chromFa []byte, refStartPos int, indelvar string, ref_seq string, comment string ) {

  // Fill in with reference.
  //
  if refStartPos > (gss.refStart + gss.refLen) {
    gss.processREF( finalTileSet, referenceTileSet, chromFa, refStartPos, 0 )
  }

  //origTile := gss.

  startPos := gss.startPos[ gss.startPosIndex-1 ]
  baseTileId := gss.baseTileIdFromStartPosMap[ startPos ]

  prettyIndelvar := indelvar
  if len(indelvar) == 0 { prettyIndelvar = "-" }
  prettyRefSeq := ref_seq
  if len(prettyRefSeq) == 0 { prettyRefSeq = "-" }

  commentString := fmt.Sprintf("%s %s %d %d INDEL %d %s => %s",
    gRefGenome, gss.curChrom,
    gss.refStart + gss.refLen,  gss.refStart + gss.refLen + len(ref_seq),
    gss.refStart + gss.refLen - startPos,
    prettyRefSeq, prettyIndelvar )

  gss.notes = append( gss.notes, commentString )


  //DEBUG
  //fmt.Printf("!!!! INDEL indelvar %s, ref_seq %s\n", indelvar, ref_seq )

  // Take the minimum of the indelvar and ref_seq length
  //
  m := len(indelvar)
  if m > len(ref_seq) { m = len(ref_seq) }

  M := len(indelvar)
  if M < len(ref_seq) { M = len(ref_seq) }

  // If there is some overlap, replace it with a 'virtual' SUB
  //
  if m>0 {

    //DEBUG
    //fmt.Printf(">>> indel cp0: refStartPos %d, indelvar[0:%d] %s\n", refStartPos, m, indelvar[0:m] )

    gss.processSUB( finalTileSet, referenceTileSet, chromFa, refStartPos, indelvar[0:m], "SUB", false )
  }

  if len(indelvar) > len(ref_seq) {
    ds := len(indelvar) - len(ref_seq)

    //DEBUG
    //fmt.Printf(">>> indel ins cp1: refStartPos %d, indelvar[%d:%d] %s\n", refStartPos+m, m, m+ds, indelvar[m:m+ds] )



    gss.processINS( finalTileSet, referenceTileSet, chromFa, refStartPos + m, indelvar[m:m+ds], false )
  } else if len(indelvar) < len(ref_seq) {
    ds := len(ref_seq) - len(indelvar)

    //DEBUG
    //fmt.Printf(">>> indel del cp1: refStartPos %d (%d+%d), -%d\n", refStartPos+m, refStartPos, m, ds )


    gss.processDEL( finalTileSet, referenceTileSet, chromFa, refStartPos + m, ds, false )
  }


  newStartPos := gss.startPos[ gss.startPosIndex-1 ]
  newBaseTileId := gss.baseTileIdFromStartPosMap[ newStartPos ]

  if newBaseTileId != baseTileId {
    gss.notes = append( gss.notes, commentString )
  }


  /*
  comments := strings.SplitN( comment, ";", -1 )

  m,_ := recache.FindAllStringSubmatch( `alleles ([^/]+)(/(.+))?`, comments[0] , -1 )
  var0 := m[0][1]
  var1 := m[0][2]
  if ( len(var1) > 0 ) { var1 = var1[1:] }

  m,_ = recache.FindAllStringSubmatch( `ref_allele ([^;]+)`, comment, -1 )
  ref_seq := m[0][1]

  if gDebugFlag { fmt.Printf("# var1 %s, var2 %s, ref_seq %s\n", var0, var1, ref_seq ) }

  if ref_seq == "-" {

    ins_seq := var0
    if var0 == "-" { ins_seq = var1 }
    gss.processINS( finalTileSet, referenceTileSet, chromFa, startPos, ins_seq )

  } else {

    gss.processDEL( finalTileSet, referenceTileSet, chromFa, startPos, entryLen )

  }
  */

}


// This does not handle SUBINS/SUBDEL (e.g. AA -> AAAA/- )
//
func (gss *GffScanState) processINDEL_OLD( finalTileSet *tile.TileSet, referenceTileSet *tile.TileSet, chromFa []byte, startPos int, entryLen int, comment string ) {

  comments := strings.SplitN( comment, ";", -1 )

  m,_ := recache.FindAllStringSubmatch( `alleles ([^/]+)(/(.+))?`, comments[0] , -1 )
  var0 := m[0][1]
  var1 := m[0][2]
  if ( len(var1) > 0 ) { var1 = var1[1:] }

  m,_ = recache.FindAllStringSubmatch( `ref_allele ([^;]+)`, comment, -1 )
  ref_seq := m[0][1]

  if gDebugFlag { fmt.Printf("# var1 %s, var2 %s, ref_seq %s\n", var0, var1, ref_seq ) }

  if ref_seq == "-" {

    ins_seq := var0
    if var0 == "-" { ins_seq = var1 }
    gss.processINS( finalTileSet, referenceTileSet, chromFa, startPos, ins_seq, true )

  } else {

    gss.processDEL( finalTileSet, referenceTileSet, chromFa, startPos, entryLen, true )

  }

}

// Parse the SNP variations.  Ignores phase information.
// var0 returned will be non-ref (assuming input doesn't have errors).
// var1 is either empty or reference base for a het var, otherwise
// ...?
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

var g_rand *rand.Rand

func main() {

  g_rand = rand.New( rand.NewSource(*g_randomSeed) )

  tagLen := 24

  gffFn := *g_gffFileName
  fastjFn := *g_fastjFileName
  chromFaFn := *g_chromFileName
  outFastjFn := *g_outputFastjFileName
  gNoteLine := *g_notes

  fastjWriter, err := bioenv.CreateWriter( *g_outputFastjFileName )
  if err!=nil { panic( fmt.Sprintf("%s: %s", *g_outputFastjFileName, err) ) }
  defer func() { fastjWriter.Flush(); fastjWriter.Close() }()

  gDebugString = fmt.Sprintf( "%s %s %s %s %s", gffFn, fastjFn, chromFaFn, outFastjFn, gNoteLine )


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
  gss0 := GffScanState{}
  gss1 := GffScanState{}
  //gss1 := GffScanState{}

  gss0.phase = "A"
  gss1.phase = "B"

  gss0.notes = make( []string, 0, 10 )
  gss1.notes = make( []string, 0, 10 )
  if len(gNoteLine) > 0 { gss0.notes = append( gss0.notes, gNoteLine ) }
  if len(gNoteLine) > 0 { gss1.notes = append( gss1.notes, gNoteLine ) }

  // refStart is 0 based
  //
  gss0.gffCurSeq = make( []byte, 0, 10 )
  gss0.baseTileIdFromStartPosMap = make( map[int]string )
  gss0.refStart, gss0.refLen = -1, 0
  gss0.TagLen = tagLen

  gss0.generateTileStartPositions( referenceTileSet )


  gss1.gffCurSeq = make( []byte, 0, 10 )
  gss1.baseTileIdFromStartPosMap = make( map[int]string )
  gss1.refStart, gss1.refLen = -1, 0
  gss1.TagLen = tagLen

  gss1.generateTileStartPositions( referenceTileSet )

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


  // STILL NEED TO PROCESS LAST TILE
  //

  for gffReader.Scanner.Scan() {
    l := gffReader.Scanner.Text()

    line_no += 1

    if len(l)==0 { continue }
    if l[0] == '#' { continue }
    if l[0] == '\n' { continue }
    if l[0] == ' ' { }


    fields := strings.SplitN( l, "\t", -1 )
    chrom := fields[0] ; _ = chrom

    gss0.curChrom = chrom
    gss1.curChrom = chrom

    s,_ := strconv.Atoi(fields[3]) ; _ = s
    e,_ := strconv.Atoi(fields[4]) ; _ = e
    varType := fields[2] ; _ = varType
    comment := fields[8]

    condensed_comment,_ := recache.ReplaceAllString( `\s+`, comment, " " )
    //fmt.Printf("condensed_comment:>> %s\n", condensed_comment)

    // converting to 0 based, end inclusive
    //
    s -= 1
    e -= 1


    //fmt.Println(">>", s, e, varType, comment)

    if ( varType == "REF" ) {

      gss0.processREF( finalTileSet, referenceTileSet, chromFa, s, e - s + 1 )
      gss1.processREF( finalTileSet, referenceTileSet, chromFa, s, e - s + 1 )


      //DEBUG
      //fmt.Printf(" >> gss0 processREF s %d, e-s+1 %d --> %d\n", s, e-s+1, gss0.refStart )
      //fmt.Printf(" >> gss1 processREF s %d, e-s+1 %d --> %d\n", s, e-s+1, gss1.refStart )

    } else if ( varType == "INDEL" ) {

      indelvar0, indelvar1, ref_seq := parseVariants( comment )

      switch gVariantPolicy {
      case "REPORTED":

        if indelvar0 == ref_seq {
          gss0.processREF( finalTileSet, referenceTileSet, chromFa, s, len(ref_seq) )
        } else {
          gss0.notes = append( gss0.notes, condensed_comment )
          gss0.processINDEL( finalTileSet, referenceTileSet, chromFa, s, indelvar1, ref_seq, comment )
        }

        if indelvar1 == ref_seq {
          gss1.processREF( finalTileSet, referenceTileSet, chromFa, s, len(ref_seq) )
        } else {
          gss1.notes = append( gss1.notes, condensed_comment )
          gss1.processINDEL( finalTileSet, referenceTileSet, chromFa, s, indelvar1, ref_seq, comment )
        }

      case "HETA":

        if indelvar0 == ref_seq {

          gss0.notes = append( gss0.notes, condensed_comment )

          gss0.processINDEL( finalTileSet, referenceTileSet, chromFa, s, indelvar1, ref_seq, comment )
          gss1.processREF( finalTileSet, referenceTileSet, chromFa, s, len(ref_seq) )


        } else if indelvar1 == ref_seq {

          gss1.notes = append( gss1.notes, condensed_comment )

          gss0.processINDEL( finalTileSet, referenceTileSet, chromFa, s, indelvar0, ref_seq, comment )
          gss1.processREF( finalTileSet, referenceTileSet, chromFa, s, len(ref_seq) )

        } else {

          gss0.notes = append( gss0.notes, condensed_comment )
          gss1.notes = append( gss1.notes, condensed_comment )

          gss0.processINDEL( finalTileSet, referenceTileSet, chromFa, s, indelvar0, ref_seq, comment )
          gss1.processINDEL( finalTileSet, referenceTileSet, chromFa, s, indelvar1, ref_seq, comment )

        }


      case "RANDOM":

        r := g_rand.Float32()
        if r < 0.5 {

          if indelvar0 == ref_seq {

            gss0.notes = append( gss0.notes, condensed_comment )

            gss0.processINDEL( finalTileSet, referenceTileSet, chromFa, s, indelvar1, ref_seq, comment )
            gss1.processREF( finalTileSet, referenceTileSet, chromFa, s, len(ref_seq) )

          } else if indelvar1 == ref_seq {

            gss1.notes = append( gss1.notes, condensed_comment )

            gss0.processREF( finalTileSet, referenceTileSet, chromFa, s, len(ref_seq) )
            gss1.processINDEL( finalTileSet, referenceTileSet, chromFa, s, indelvar0, ref_seq, comment )

          } else {

            gss0.notes = append( gss0.notes, condensed_comment )
            gss1.notes = append( gss1.notes, condensed_comment )

            gss0.processINDEL( finalTileSet, referenceTileSet, chromFa, s, indelvar0, ref_seq, comment )
            gss1.processINDEL( finalTileSet, referenceTileSet, chromFa, s, indelvar1, ref_seq, comment )

          }

        }

      default:
      }


      //gss.notes = append( gss.notes, condensed_comment )
      //gss.processINDEL( finalTileSet, referenceTileSet, chromFa, s, e-s+1, comment )

    } else if ( (varType == "SUB") || (varType == "SNP") ) {

      subvar0, subvar1, ref_seq := parseVariants( comment )

      switch gVariantPolicy {
      case "REPORTED":

        if subvar0 == ref_seq {
          gss0.processREF( finalTileSet, referenceTileSet, chromFa, s, len(subvar0) )
        } else {
          gss0.notes = append( gss0.notes, condensed_comment )
          gss0.processSUB( finalTileSet, referenceTileSet, chromFa, s, subvar0, varType, true )
        }

        if subvar1 == ref_seq {
          gss1.processREF( finalTileSet, referenceTileSet, chromFa, s, len(subvar1) )
        } else {
          gss1.notes = append( gss1.notes, condensed_comment )
          gss1.processSUB( finalTileSet, referenceTileSet, chromFa, s, subvar1, varType, true )
        }

      case "HETA":

        if subvar0 == ref_seq {

          gss0.notes = append( gss0.notes, condensed_comment )

          gss0.processSUB( finalTileSet, referenceTileSet, chromFa, s, subvar1, varType, true )
          gss1.processREF( finalTileSet, referenceTileSet, chromFa, s, len(subvar1) )

        } else if subvar1 == ref_seq {

          gss1.notes = append( gss1.notes, condensed_comment )

          gss0.processSUB( finalTileSet, referenceTileSet, chromFa, s, subvar0, varType, true )
          gss1.processREF( finalTileSet, referenceTileSet, chromFa, s, len(subvar0) )

        } else {

          gss0.notes = append( gss0.notes, condensed_comment )
          gss1.notes = append( gss1.notes, condensed_comment )

          gss0.processSUB( finalTileSet, referenceTileSet, chromFa, s, subvar0, varType, true )
          gss1.processSUB( finalTileSet, referenceTileSet, chromFa, s, subvar1, varType, true )

        }

      case "RANDOM":

        r := g_rand.Float32()
        if r < 0.5 {

          if subvar0 == ref_seq {
            gss0.processREF( finalTileSet, referenceTileSet, chromFa, s, len(subvar0) )
          } else  {
            gss0.notes = append( gss0.notes, condensed_comment )
            gss0.processSUB( finalTileSet, referenceTileSet, chromFa, s, subvar0, varType, true )
          }

          if subvar1 == ref_seq {
            gss1.processREF( finalTileSet, referenceTileSet, chromFa, s, len(subvar1) )
          } else {
            gss1.notes = append( gss1.notes, condensed_comment )
            gss1.processSUB( finalTileSet, referenceTileSet, chromFa, s, subvar1, varType, true )
          }

        } else {

          if subvar1 == ref_seq {
            gss0.processREF( finalTileSet, referenceTileSet, chromFa, s, len(subvar1) )
          } else {
            gss0.notes = append( gss0.notes, condensed_comment )
            gss0.processSUB( finalTileSet, referenceTileSet, chromFa, s, subvar1, varType, true )
          }

          if subvar0 == ref_seq {
            gss1.processREF( finalTileSet, referenceTileSet, chromFa, s, len(subvar0) )
          } else {
            gss1.notes = append( gss1.notes, condensed_comment )
            gss1.processSUB( finalTileSet, referenceTileSet, chromFa, s, subvar0, varType, true )
          }

        }

      default:
        //???
      }

    /*
    } else if ( varType == "SNP" ) {

      gss.notes = append( gss.notes, condensed_comment )
      snpvar0, snpvar1, ref_seq := parseSNPSUB( comment ) ;  _ = snpvar1 ;  _ = snpvar0
      gss.processSUB( finalTileSet, referenceTileSet, chromFa, s, snpvar0, "SNP" )

    */

    } else {

      panic( fmt.Sprintf("unknown varType %s on line %d", varType, line_no) )
    }

  }

}
