/*

  NAME:
     gff2fj - Convert a (chopped) GFF file to a FastJ file

  USAGE:
     gff2fj [global options] command [command options] [arguments...]

  VERSION:
     0.2.0, AGPLv3.0

  AUTHOR:
    Curoverse Inc. - <info@curoverse.com>

  COMMANDS:
     help, h      Shows a list of commands or help for one command

  GLOBAL OPTIONS:
     --input-gff, -i                      Input GFF file
     --input-fastj, -f                    Input FastJ file
     --fasta-chromosome, -c               Input chromosome Fasta file
     --output-fastj, -o                   Output FastJ file
     --variant-policy, -P 'REPORTED'      Variant policy (one of 'REPORTED', 'HETA', 'RANDOM' or 'REGEX') (default to 'REPORTED')
     --note, -a                           Annotation to add to the 'note' list in the FastJ header
     --allow-variant-on-tag, -T           Allow variants on tags (by default, tiles are extended to not allow variants on tags)
     --seed, -S '0'                       Random seed (default to current time)
     --verbose, -V                        Verbose flag
     --help, -h                           show help
     --version, -v                        print the version

*/

// Sample usage:
//
// ./gff2fj -i /scratch/tmp/chr19_band2_s13900000_e14000000.gff.gz  \
//          -f /scratch/ref/hg19.fj/chr19_band2_s13900000_e14000000.fj.gz \
//          -fasta-chromosome /scratch/ref/hg19.fa/chr19.fa \
//          -o -
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

//
// Variant Policy
// --------------
//
// There are three variant policies: HETA, REPORTED, RANDOM and REGEX.  These inform how the FastJ will
// be generated from how the variants are reported in the the GFF file.
//
// HETA:
//    - If there is only one non-ref variant, place it on the first allele (allele "A").
//    - If there are two non-ref variants, be it het or hom, place the first on allele "A" and the second
//      on allele "B".  They are placed in the order reported in the GFF file.
//
// REPORTED:
//    - Place the variant(s) on the allele in the order reported in the GFF file.
//
// RANDOM:
//    - Place the variant(s) randomely on either allele "A" or "B".  The RNG can be seeded witha value
//      from the command line.  Default is taken to be the current time
//
// REGEX:
//    - Create only one tile for both alleles with a regexp to describe the variant.  For SNPs, the
//      regexp will be in square brackets (for example, '[ag]') and for everything else, they will
//      be in parenthesis (for example, '(|aa)').  The strings inside the brackets and parenthesis
//      are sorted in lexigraphical order.  For INDELs, a deletion is denoted by an empty string.
//      Homozygous SNPs are not enclosed in brackets.
//

// Gaps
// ----
//
// Gaps are filled in with the relevant reference genome.  An annotation is generated and put in the
// JSON 'notes' array.

// Variants crossing tile boundaries
// ---------------------------------
//
// If the 'allow-variant-on-tag' option is set, INDELs that cross tile boundaries will be though of as
//   a substitution followed by a deletion or insertion.
//

// Simple Substitutions:
//
// This is a special case and an artifact of the way we tile the genome.  When substitutions cross
//   tile boundaries, then the first part of the subsititution will be placed in the end part of
//   the tail of the right tag of the first tile.  The second tile will also have the substitution
//   in the left tag but will also have the remaining substitution in the body (or beyond).
//
// The substitutions will be added to the 'notes' filed in the JSON header.  The full substitution
//   sequence might be reported for verbosity, but the length portion will indicate how much of
//   the substitution sequence appears in the tile.
//
// For example:
// > { "tileID" : ..., "n" : 249, ..., "notes" : [ { ... , "hg19 chr3 1234 1244 SUB ATTATTATTA 247 2", ... }], ...  }
// ...
// tcccaaaatgttgggagtgagccaccgtgccaggaaaggcccccccccAT
//
// Which indicates there is a substitution that is 10 bp long, but only the first 2 bp appear in the tile (starting at position 247, 0ref).
// The next tile might look as follows
//
// > { "tileID" : ..., "n" : 253, ..., "notes" : [ { ... , "hg19 chr3 1234 1244 SUB ATTATTATTA 22 2", "hg19 chr3 1236 1244 SUB TATTATTA 24 8", ... }], ...  }
// gtgccaggaaaggcccccccccATTATTATTA...
// ...
//
// This way it should be able to construct what was reported by the GFF and to easily verify how the FastJ was generated.

// INDELs:
//
// INDELs are handled 'under the hood' as a substitution of the first min( len(refseq), len(indel) )
//   base pairs, followed by either an insertion or deletion, depending on whether len(indel) > len(refseq)
//   or len(indel) < len(refseq) respectively.  The annotation is an INDEL and if the INDEL is contained
//   inside a tile, this should be pretty transparent.  If the INDEL crosses a tile boundary, then the
//   implications of how the INDEL is done become apparent when viewing the annotations.  For example,
//   if the first part of the synthetic INDEL (the substitution) crosses the boundary, the first tile
//   will contain part of the substitution, while the next tile will contain the rest, including the
//   latter portion of the substitution and the insertion or deletion, depending.
//
// Here is a contrived example:
//
// say we have (in 1ref):
//
//      INDEL 1001 1006  AGTAGT/-;ref_allele CCC
//
//  and for arguments sake we have a tile that ends at (0ref) 1002, then this INDEL would go from
//
//      xxxxxxxxxxxxxxxCC | Cxxxxxxxxxxxxxxxx
//
//  to
//
//      xxxxxxxxxxxxxxxAG | T(AGT)xxxxxxxxxxxxxxxx
//
//  Where the sequence in the parens () is an insertion and the '|' represents a tile boundary.
//


/***************************************************

 GFF notes:

   GFF is 1 based, with end inclusive.
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
import "../aux"
import "strconv"
import "strings"
import "time"

import "bufio"

import "sort"
import "encoding/json"
import _ "compress/gzip"

import "github.com/codegangsta/cli"

import "math/rand"

import "crypto/md5"

import "../recache"
import "../tile"
import "../bioenv"

import "runtime/pprof"


var VERSION_STR string = "0.2.0, AGPLv3.0"

var gBioEnvWriter bioenv.BioEnvHandle
var gOutputWriter *bufio.Writer


var gDebugFlag bool = false
var gDebugString string
var gRefGenome string = "hg19"

var gAllowVariantOnTag bool = false
var gPlaceNoCallInSeq bool = true

var gLineNo int = 0

var g_gffFileName string
var g_fastjFileName string
var g_chromFileName string
var g_outputFastjFileName string
var g_notes string

var g_variantPolicy string = "REPORTED"
var g_randomSeed int64

var g_discardVariantOnTag bool
var g_discardGaps bool
var g_verboseFlag bool

var g_referenceTileSet *tile.TileSet

//var g_start int
//var g_end int


var gProfileFlag bool
var gProfileFile string


type TileHeader struct {
  TileID string `json:"tileID"`
  Locus []map[ string ]string `json:"locus"`
  N int `json:"n"`
  //CopyNum int `json:"copy"`
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
  refStartActual, refStartVirtual int
  refLenActual, refLenVirtual int

  gffLeftTagSeqActual []byte
  gffLeftTagSeqVirtual []byte
  gffRightTagSeq []byte

  notes []string
  carryOverNotes []string
  simpleLocusBuild string

  md5sum [16]byte

  curChrom string

  TagLen int

  phase string

  variantOnTag bool
  seedTileLength int

  VariantId int

}

func (gss *GffScanState) PrintState() {
  fmt.Printf("nextTagStart %d\n", gss.nextTagStart)
  fmt.Printf("len(startPos) %d\n", len(gss.startPos) )
  fmt.Printf("startPosIndex %d\n", gss.startPosIndex )
  fmt.Printf("endPos %d\n", gss.endPos )
  fmt.Printf("gffCurSeq %s\n", gss.gffCurSeq )
  fmt.Printf("refStartVirtual %d, refLenVirtual %d\n", gss.refStartVirtual, gss.refLenVirtual )
  fmt.Printf("refStartActual %d, refLenActual %d\n", gss.refStartActual, gss.refLenActual )
  fmt.Printf("simpleLocusBuild %s\n", gss.simpleLocusBuild )
  fmt.Printf("curChrom %s\n", gss.curChrom)
  fmt.Printf("tagLen %d\n", gss.TagLen )
  fmt.Printf("phase %s\n", gss.phase )
  fmt.Printf("gffLeftTagSeqVirtual %s\n", string(gss.gffLeftTagSeqVirtual) )
  fmt.Printf("gffLeftTagSeqActual %s\n", string(gss.gffLeftTagSeqActual) )
  fmt.Printf("gffRightTagSeq %s\n", string(gss.gffRightTagSeq) )
}

func (gss *GffScanState) generateTileStartPositions(referenceTileSet *tile.TileSet, buildVersion string) {

  gss.endPos = -1

  // Sort starting position of each of the tile.
  // hg(\d+) co-ordinates stored as 0ref in tile set.
  //
  for _,tcc := range referenceTileSet.TileCopyCollectionMap {
    a,ok := recache.FindAllStringSubmatch( buildVersion + ` chr[^ ]* (\d+)(-\d+)? (\d+)(\+\d+)?`, tcc.Meta[0], -1 )
    if ok != nil {
      for i:=1 ; i<len(tcc.Meta); i++ {
        a,ok = recache.FindAllStringSubmatch( buildVersion + ` chr[^ ]* (\d+)(-\d+)? (\d+)(\+\d+)?`, tcc.Meta[i], -1 )
        if ok != nil { break }
      }
    }
    if ok != nil { continue }

    s,_ := strconv.Atoi(a[0][1])
    e,_ := strconv.Atoi(a[0][3])

    gss.startPos = append( gss.startPos, s )
    gss.baseTileIdFromStartPosMap[s] = tcc.BaseTileId

    // Put in final endpoint
    //
    if gss.endPos < e {
      gss.endPos = e
    }

  }

  if gss.endPos >= 0 {
    gss.startPos = append( gss.startPos, gss.endPos )
  }

  sort.Ints( gss.startPos )
  gss.nextTagStart = gss.startPos[1]
  gss.startPosIndex = 1

  gss.gffCurSeq = gss.gffCurSeq[0:0]

  gss.refStartActual = gss.startPos[0]
  gss.refLenActual = 0

  gss.refStartVirtual = gss.startPos[0]
  gss.refLenVirtual = 0

  gss.gffLeftTagSeqVirtual = gss.gffLeftTagSeqVirtual[0:0]
  gss.gffLeftTagSeqVirtual = append( gss.gffLeftTagSeqVirtual, []byte("")... )

  gss.gffLeftTagSeqActual = gss.gffLeftTagSeqActual[0:0]
  gss.gffLeftTagSeqActual = append( gss.gffLeftTagSeqActual, []byte("")... )

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


func (gss *GffScanState) DebugPrint( referenceTileSet *tile.TileSet ) {
  baseTileId := gss.baseTileIdFromStartPosMap[ gss.refStartActual ]

  refTcc := referenceTileSet.TileCopyCollectionMap[ baseTileId ]

  header := TileHeader{}
  json.Unmarshal( []byte( refTcc.Meta[0] ), &header )

}


// Each process* function is in charge of updating the sequence and addint to the final tile set.  There
// is a lot of similarity, but they each need their own special handling of when the sequence extends over
// a tile boundary so for simplicity, they each handle the sequence.
//

func (gss *GffScanState) AddTile( finalTileSet *tile.TileSet, referenceTileSet *tile.TileSet ) {

  baseTileId := gss.baseTileIdFromStartPosMap[ gss.refStartActual ]

  refTcc := referenceTileSet.TileCopyCollectionMap[ baseTileId ]

  header := TileHeader{}
  json.Unmarshal( []byte( refTcc.Meta[0] ), &header )


  NormalizeTileSeq( gss.gffCurSeq, len(gss.gffLeftTagSeqActual), len(gss.gffRightTagSeq) )

  f := strings.SplitN( baseTileId, ".", -1 )

  newTileId := fmt.Sprintf("%s.%s.%04s.%03x", f[0], f[1], f[2], gss.VariantId )

  gOutputWriter.WriteString("> { ")
  gOutputWriter.WriteString( fmt.Sprintf("\"tileID\" : \"%s\"", newTileId ) )

  gss.md5sum = md5.Sum( gss.gffCurSeq )

  gOutputWriter.WriteString(", \"md5sum\":\"")

  for i:=0; i<len(gss.md5sum); i++ {
    gOutputWriter.WriteString( fmt.Sprintf("%02x", gss.md5sum[i]) )
  }


  nocallCount:=0
  nocall_note := make( []string, 0, 8 )
  if gPlaceNoCallInSeq {
    nocall_run:=0
    n := len(gss.gffCurSeq)
    seq := gss.gffCurSeq
    for i:=0; i<n; i++ {

      s := i
      for ; (i<n) && ((seq[i] == 'n') || (seq[i] == 'N')); i++ {
        nocall_run++
      }

      nocallCount += nocall_run
      if nocall_run > 0 {
        nocall_note = append( nocall_note, fmt.Sprintf("nocall %d %d", s, nocall_run) )
        nocall_run=0
      }

    }

  }

  gOutputWriter.WriteString("\"")

  gOutputWriter.WriteString( fmt.Sprintf(", \"locus\":[{\"build\":\"%s\"}]", header.Locus[0]["build"] ) )
  gOutputWriter.WriteString( fmt.Sprintf(", \"n\":%d", len(gss.gffCurSeq) ) )
  gOutputWriter.WriteString( fmt.Sprintf(", \"seedTileLength\":%d", gss.seedTileLength ) )

  gOutputWriter.WriteString( ",\"startTile\":" )
  if len(gss.gffLeftTagSeqActual)==0  { gOutputWriter.WriteString( "true" )
  } else                              { gOutputWriter.WriteString( "false" ) }

  gOutputWriter.WriteString( ",\"endTile\":" )
  if len(gss.gffRightTagSeq)==0 { gOutputWriter.WriteString( "true" )
  } else                        { gOutputWriter.WriteString( "false" ) }

  gOutputWriter.WriteString( fmt.Sprintf(", \"startSeq\":\"%s\"", gss.gffLeftTagSeqActual) )
  gOutputWriter.WriteString( fmt.Sprintf(", \"endSeq\":\"%s\""  , gss.gffRightTagSeq) )
  gOutputWriter.WriteString( fmt.Sprintf(", \"startTag\":\"%s\"", refTcc.StartTag ) )
  gOutputWriter.WriteString( fmt.Sprintf(", \"endTag\":\"%s\""  , refTcc.EndTag ) )

  if gPlaceNoCallInSeq {
    gOutputWriter.WriteString( fmt.Sprintf(", \"nocallCount\":%d"  , nocallCount ) )
  }

  gss.notes = append( gss.notes, fmt.Sprintf("Phase (%s) %s", g_variantPolicy, gss.phase ) )

  if len(gss.notes) > 0 {
    gOutputWriter.WriteString(", \"notes\":[")

    note_count := 0
    for i:=0; i<len(gss.notes); i++ {
      if i>0 { gOutputWriter.WriteString(", ") }
      gOutputWriter.WriteString( fmt.Sprintf("\"%s\"", gss.notes[i]) )
      note_count++
    }

    for i:=0; i<len(nocall_note); i++ {
      if note_count>0 { gOutputWriter.WriteString(", ") }
      gOutputWriter.WriteString( fmt.Sprintf("\"%s\"", nocall_note[i]) )
      note_count++
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


}

// Reduce current sequence, shift tags and update
// other state variables.
//
func (gss *GffScanState) AdvanceState() {

  // If there's a variant on the tag, we
  // update the 'virtual' pointer along with
  // some other state variables but keep
  // the 'actual' pointer the same and
  // keep the left tag and sequence body.
  //
  if !gAllowVariantOnTag && gss.variantOnTag {


    if (gss.refStartVirtual + gss.refLenVirtual) != (gss.refStartActual + gss.refLenActual) {
      fmt.Printf(" (0) %d + %d (%d) != %d + %d (%d)  [[[[%d]]]]\n",
        gss.refStartVirtual , gss.refLenVirtual,
        gss.refStartVirtual + gss.refLenVirtual,
        gss.refStartActual , gss.refLenActual,
        gss.refStartActual + gss.refLenActual,
        gss.refStartVirtual + gss.refLenVirtual - (gss.refStartActual + gss.refLenActual),
      )

      os.Exit(-1)
    }


    gss.variantOnTag = false
    gss.seedTileLength += 1

    gss.gffRightTagSeq = gss.gffRightTagSeq[0:0]

    ds := (gss.nextTagStart + gss.TagLen) - (gss.refStartVirtual + gss.refLenVirtual)
    gss.refLenActual += ds

    if ds < 0 {

      fmt.Printf(" (!!! %d) %d + %d (%d) != %d + %d (%d)  [[[[%d]]]]\n",
        ds,
        gss.refStartVirtual , gss.refLenVirtual,
        gss.refStartVirtual + gss.refLenVirtual,
        gss.refStartActual , gss.refLenActual,
        gss.refStartActual + gss.refLenActual,
        gss.refStartVirtual + gss.refLenVirtual - (gss.refStartActual + gss.refLenActual),
      )

      os.Exit(-1)
    }

    gss.refStartVirtual = gss.nextTagStart
    gss.startPosIndex++
    if gss.startPosIndex >= len(gss.startPos) { return }
    gss.nextTagStart = gss.startPos[ gss.startPosIndex ]

    gss.refLenVirtual = 0
    gss.gffLeftTagSeqVirtual = gss.gffLeftTagSeqVirtual[0:0]
    gss.gffLeftTagSeqVirtual = append( gss.gffLeftTagSeqVirtual, gss.gffRightTagSeq... )

    gss.gffCurSeq = append( gss.gffCurSeq, gss.gffLeftTagSeqVirtual... )
    gss.refLenVirtual += gss.TagLen

    gss.notes = append( gss.notes, "VariantOnTag" )


    if (gss.refStartVirtual + gss.refLenVirtual) != (gss.refStartActual + gss.refLenActual) {
      fmt.Printf(" (A) %d + %d (%d) != %d + %d (%d)  [[[[%d]]]]\n",
        gss.refStartVirtual , gss.refLenVirtual,
        gss.refStartVirtual + gss.refLenVirtual,
        gss.refStartActual , gss.refLenActual,
        gss.refStartActual + gss.refLenActual,
        gss.refStartVirtual + gss.refLenVirtual - (gss.refStartActual + gss.refLenActual),
      )

      os.Exit(-1)
    }

    return
  }


  // If no variants are on the tag, we can advance
  // state and bring the 'virtual' and 'actual'
  // pointers in sync.
  //

  gss.refStartVirtual = gss.nextTagStart
  gss.refLenVirtual = 0

  gss.refStartActual = gss.nextTagStart
  gss.refLenActual= 0

  gss.notes = gss.notes[0:0]
  if len(g_notes) > 0 { gss.notes = append( gss.notes, g_notes) }
  if len(gss.carryOverNotes) > 0 { gss.notes = append(gss.notes, gss.carryOverNotes... ) }
  gss.carryOverNotes = gss.carryOverNotes[0:0]

  gss.gffLeftTagSeqActual = gss.gffLeftTagSeqActual[0:0]
  gss.gffLeftTagSeqActual = append( gss.gffLeftTagSeqActual, gss.gffRightTagSeq... )

  gss.gffLeftTagSeqVirtual = gss.gffLeftTagSeqVirtual[0:0]
  gss.gffLeftTagSeqVirtual = append( gss.gffLeftTagSeqVirtual, gss.gffRightTagSeq... )

  gss.gffRightTagSeq = gss.gffRightTagSeq[0:0]

  gss.gffCurSeq = gss.gffCurSeq[0:0]
  gss.gffCurSeq = append( gss.gffCurSeq, gss.gffLeftTagSeqActual... )

  gss.refLenVirtual = gss.TagLen
  gss.refLenActual = gss.TagLen

  gss.startPosIndex++
  if gss.startPosIndex >= len(gss.startPos) { return }
  gss.nextTagStart = gss.startPos[ gss.startPosIndex ]

  gss.variantOnTag = false
  gss.seedTileLength = 1

  if (gss.refStartVirtual + gss.refLenVirtual) != (gss.refStartActual + gss.refLenActual) {
    fmt.Printf(" (B) %d + %d (%d) != %d + %d (%d)\n",
      gss.refStartVirtual , gss.refLenVirtual,
      gss.refStartVirtual + gss.refLenVirtual,
      gss.refStartActual , gss.refLenActual,
      gss.refStartActual + gss.refLenActual )

      os.Exit(-2)
  }



}

func fill_no_call( s []byte, ds int ) []byte {
  for i:=0; i<ds; i++ { s = append( s, "n"... ) }
  return s
}

func append_with_ref_and_nocall( s, ref []byte, gapEndPos, spos, epos int) []byte {
  dpos := epos - spos
  if dpos < 0 {
    fmt.Fprintf( os.Stderr, "ERROR: append_with_ref_and_nocall epos (%d) < spos (%d)\n", epos, spos )
    fmt.Fprintf( os.Stdout, "ERROR: append_with_ref_and_nocall epos (%d) < spos (%d)\n", epos, spos )
    panic( fmt.Errorf("ERROR: append_with_ref_and_nocall epos (%d) < spos (%d)\n", epos, spos ) )
  }

  if dpos==0 {
    //fmt.Fprintf( os.Stderr, "ERROR: append_with_ref_and_nocall epos (%d) == spos (%d)\n", epos, spos )
    //fmt.Fprintf( os.Stdout, "ERROR: append_with_ref_and_nocall epos (%d) == spos (%d)\n", epos, spos )
    return s
  }

  if gapEndPos < spos {
    s = append( s, ref[ spos : spos + dpos ]... )
  } else if gapEndPos < (spos+dpos) {
    s = fill_no_call( s, gapEndPos - spos )
    s = append( s, ref[ gapEndPos : spos + dpos ]... )
  } else {
    s = fill_no_call( s, dpos )
  }
  return s
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

  gapLen := refStartPos - (gss.refStartVirtual + gss.refLenVirtual)
  gapEndPos := refStartPos
  gapNote := ""

  if (gss.refStartVirtual + gss.refLenVirtual) < refStartPos {
    gss.notes = append( gss.notes,
                        fmt.Sprintf("%s %s %d %d GAP %d %d",
                                    gRefGenome,
                                    gss.curChrom,
                                    gss.refStartActual + gss.refLenActual,
                                    refStartPos-1,
                                    gss.refLenActual,
                                    gapLen) )

    gapNote = fmt.Sprintf("gapOnTag %s %s %d %d GAP - %d",
                          gRefGenome,
                          gss.curChrom,
                          gss.refStartActual + gss.refLenActual,
                          refStartPos-1,
                          gapLen)
  }

  if gapLen < 0 { gapLen = 0 }

  // The refStartPos + entryLen (end of the reference sequence) has shot past the current tag
  // end boundary.  We want to peel off the head of the sequence, adding it to the finalTileSet
  // where appropriate.
  //
  for ; (refStartPos + entryLen) >= (gss.nextTagStart + gss.TagLen) ; {

    if gss.refStartVirtual == gss.startPos[ gss.startPosIndex-1 ] {

      refLenRemain := (gss.nextTagStart + gss.TagLen) - (gss.refStartVirtual + gss.refLenVirtual)

      var fa []byte

      // Update the current sequence, placing 'no-calls' as appropriate.
      //
      if gPlaceNoCallInSeq {
        fa = append_with_ref_and_nocall( fa, chromFa, gapEndPos, gss.refStartVirtual + gss.refLenVirtual, gss.nextTagStart + gss.TagLen )
      } else {
        fa = chromFa[ gss.refStartVirtual + gss.refLenVirtual : gss.nextTagStart + gss.TagLen ]
      }
      gss.gffCurSeq = append( gss.gffCurSeq, fa... )


      // Update the tag with the remainder of it's sequence, either the full ref or a partial
      // subsequence of the ref if the right tag sequence already partially filled in.
      //
      if refLenRemain > gss.TagLen {
        gss.gffRightTagSeq = gss.gffRightTagSeq[0:0]

        if gPlaceNoCallInSeq {
          gss.gffRightTagSeq = append_with_ref_and_nocall( gss.gffRightTagSeq, chromFa, gapEndPos, gss.nextTagStart, gss.nextTagStart + gss.TagLen )
        } else {
          gss.gffRightTagSeq = append( gss.gffRightTagSeq, chromFa[ gss.nextTagStart : gss.nextTagStart + gss.TagLen ]... )
        }


      } else {

        if gPlaceNoCallInSeq {

          gss.gffRightTagSeq = append_with_ref_and_nocall( gss.gffRightTagSeq,
                                                       chromFa,
                                                       gapEndPos,
                                                       gss.refStartVirtual + gss.refLenVirtual,
                                                       gss.nextTagStart + gss.TagLen )

        } else {
          gss.gffRightTagSeq = append( gss.gffRightTagSeq, chromFa[ gss.refStartVirtual + gss.refLenVirtual : gss.nextTagStart + gss.TagLen ]... )
        }

      }

      if gAllowVariantOnTag || !gss.variantOnTag {
        gss.AddTile( finalTileSet, referenceTileSet )
      }

    }

    // From this point on, the sequence must be ref, so just keep pushing the releveant
    // sequence onto gffCurSeq so it can get peeled off by the above.
    //

    if gapEndPos > (gss.refStartVirtual + gss.refLenVirtual) {
      gss.carryOverNotes = append( gss.carryOverNotes, gapNote )
    }

    gss.AdvanceState()

  }

  // Finally, append trailing reference sequence to gffCurSeq.
  //
  dn := (refStartPos + entryLen) - (gss.refStartVirtual + gss.refLenVirtual)

  if gPlaceNoCallInSeq {

    gss.gffCurSeq = append_with_ref_and_nocall( gss.gffCurSeq,
                                            chromFa,
                                            gapEndPos,
                                            gss.refStartVirtual + gss.refLenVirtual,
                                            gss.refStartVirtual + gss.refLenVirtual + dn )

  } else {
    gss.gffCurSeq = append( gss.gffCurSeq, chromFa[ gss.refStartVirtual + gss.refLenVirtual : gss.refStartVirtual + gss.refLenVirtual + dn ]... )
  }


  // The "reference" right tag length is not necessarily the length of the right
  // tag, as the current sequence can hold insertions and deletions.
  //
  refLenRightTag := (gss.refStartVirtual + gss.refLenVirtual) - (gss.nextTagStart)
  if refLenRightTag < 0 { refLenRightTag = 0 }

  // We want to find how much to add to the right tag, taking into account
  // how much of the "right tag reference sequence" we've already accounted for.
  //
  refLenTagOverflow := (refStartPos + entryLen) - (gss.nextTagStart)
  refLenTagOverflow -= refLenRightTag
  if refLenTagOverflow > 0 {
    begRightTag := gss.nextTagStart + refLenRightTag

    if gPlaceNoCallInSeq {

      gss.gffRightTagSeq = append_with_ref_and_nocall( gss.gffRightTagSeq,
                                                       chromFa,
                                                       gapEndPos,
                                                       begRightTag,
                                                       begRightTag + refLenTagOverflow )

    } else {
      gss.gffRightTagSeq = append( gss.gffRightTagSeq, chromFa[ begRightTag : begRightTag + refLenTagOverflow ]... )
    }

    if gapEndPos > begRightTag {
      gss.carryOverNotes = append( gss.carryOverNotes, gapNote )
    }

  }

  gss.refLenVirtual += dn
  gss.refLenActual += dn

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
func (gss *GffScanState) processRegexSNP( finalTileSet *tile.TileSet,
                                          referenceTileSet *tile.TileSet,
                                          chromFa []byte,
                                          refStartPos int,
                                          snpvar0 string,
                                          snpvar1 string,
                                          ref_seq string,
                                          comment string ) {

  // Fill in with reference.
  //
  if refStartPos > (gss.refStartVirtual + gss.refLenVirtual) {
    gss.processREF( finalTileSet, referenceTileSet, chromFa, refStartPos, 0 )
  }

  if refStartPos > (gss.refStartVirtual + gss.refLenVirtual) { return }

  regexSNP := fmt.Sprintf( "[%s%s]", snpvar0, snpvar1 )
  if snpvar0 == snpvar1 {
    regexSNP = fmt.Sprintf( "%s", snpvar0 )
  }

  gss.gffCurSeq = append( gss.gffCurSeq, regexSNP... )

  // End is inclusive, as per GFF convention (though still 0 referenced)
  //
  posInSeq := len(gss.gffCurSeq)
  commentString := fmt.Sprintf("%s %s %d %d SNP %d %s => %s",
    gRefGenome, gss.curChrom,
    gss.refStartVirtual + gss.refLenVirtual,  gss.refStartVirtual + gss.refLenVirtual,
    posInSeq - len(regexSNP),
    ref_seq, regexSNP )

  gss.notes = append( gss.notes, comment )
  gss.notes = append( gss.notes, commentString )


  refLenRemain := (gss.nextTagStart + gss.TagLen) - (gss.refStartVirtual + gss.refLenVirtual)
  if refLenRemain < gss.TagLen {
    gss.gffRightTagSeq = append( gss.gffRightTagSeq, regexSNP... )

    if gAllowVariantOnTag {
      gss.carryOverNotes = append( gss.carryOverNotes, fmt.Sprintf("ltag: %s", comment) )
      gss.carryOverNotes = append( gss.carryOverNotes, fmt.Sprintf("ltag: %s", commentString) )
    }

    gss.variantOnTag = true
  }


  if (refStartPos + 1) >= (gss.nextTagStart + gss.TagLen) {

    if gss.refStartVirtual == gss.startPos[ gss.startPosIndex-1 ] {

      if gAllowVariantOnTag || !gss.variantOnTag {
        gss.AddTile( finalTileSet, referenceTileSet )
      }

    }
    gss.AdvanceState()

  }

  dn := (refStartPos + 1) - (gss.refStartVirtual + gss.refLenVirtual)
  gss.refLenVirtual += dn
  gss.refLenActual += dn

}


// SNPs also happen here, as they can be thought of as a substitution of length 1 in this context.
//
// refStartPos is the beginning of the substitution sequence.  We will fill in everything from the current
// position up to the refStartPos with ref, then fill in the rest with the substitution.
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
  if refStartPos > (gss.refStartVirtual + gss.refLenVirtual) {
    gss.processREF( finalTileSet, referenceTileSet, chromFa, refStartPos, 0 )
  }

  // We've reached the end of our band, just bail out
  //
  if gss.startPosIndex == (len(gss.startPos)-1) { return }

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

  subvarAlreadyNoted := false

  lastNote := ""
  for ; (refStartPos + entryLen) >= (gss.nextTagStart + gss.TagLen) ; {

    if gss.refStartVirtual == gss.startPos[ gss.startPosIndex-1 ] {

      refLenRemain := (gss.nextTagStart + gss.TagLen) - (gss.refStartVirtual + gss.refLenVirtual)
      posInSeq := len(gss.gffCurSeq)

      // Add the rest of the subvar to our current sequence.
      //
      gss.gffCurSeq        = append( gss.gffCurSeq, subvar[0:refLenRemain]... )

      if noteFlag {

        if len(lastNote) > 0 {
          gss.notes = append( gss.notes, lastNote )
        }

        if gAllowVariantOnTag {

          curNote := fmt.Sprintf("%s %s %d %d %s %s %d %d",
              gRefGenome, gss.curChrom, gss.refStartVirtual+gss.refLenVirtual, gss.nextTagStart+gss.TagLen-1,
              subType, subvar, posInSeq, refLenRemain)
          gss.notes = append( gss.notes, curNote )

          lastNote = fmt.Sprintf("ltag: %s %s %d %d %s %s %d %d",
              gRefGenome, gss.curChrom, gss.refStartVirtual+gss.refLenVirtual, gss.nextTagStart+gss.TagLen-1,
              subType, subvar, posInSeq - len(gss.gffCurSeq) + gss.TagLen, refLenRemain)
        } else {

          if !subvarAlreadyNoted {
            curNote := fmt.Sprintf("%s %s %d %d %s %s %d %d",
                gRefGenome, gss.curChrom, gss.refStartVirtual+gss.refLenVirtual, gss.refStartVirtual+gss.refLenVirtual+len(subvar)-1,
                subType, subvar, posInSeq, len(subvar) )
            gss.notes = append( gss.notes, curNote )
          }

          subvarAlreadyNoted = true

        }


      }

      // If the refLenRemain is greater than the tag length, then we need to add
      // to the right tag from the appropriate offset in the subvar string.
      // Otherwise we just add the appropriate amount (starting at offset 0)
      // fromt he subvar string.
      //
      if refLenRemain > gss.TagLen {
        dbeg := refLenRemain - gss.TagLen

        gss.variantOnTag = true
        gss.gffRightTagSeq = append( gss.gffRightTagSeq, subvar[ dbeg : dbeg + gss.TagLen ]... )

        if noteFlag && gAllowVariantOnTag {
          subNote := fmt.Sprintf("ltag: %s %s %d %d %s %s %d %d",
            gRefGenome, gss.curChrom, gss.refStartVirtual+gss.refLenVirtual, gss.nextTagStart+gss.TagLen-1,
            subType, subvar[dbeg:dbeg+gss.TagLen], gss.refLenVirtual, len(subvar[dbeg:dbeg+gss.TagLen]))
          gss.carryOverNotes = append( gss.carryOverNotes, subNote )
        }

      } else {

        gss.variantOnTag = true
        gss.gffRightTagSeq = append( gss.gffRightTagSeq, subvar[ 0 : refLenRemain ]... )

        if noteFlag && gAllowVariantOnTag {
          subNote := fmt.Sprintf("ltag: %s %s %d %d %s %s %d %d",
            gRefGenome, gss.curChrom, gss.refStartVirtual+gss.refLenVirtual, gss.nextTagStart+gss.refLenVirtual+refLenRemain,
            subType, subvar[0:refLenRemain], gss.refLenVirtual, len(subvar[0:refLenRemain]))
          gss.carryOverNotes = append( gss.carryOverNotes, subNote )
        }

      }

      if gAllowVariantOnTag || !gss.variantOnTag {
        gss.AddTile( finalTileSet, referenceTileSet )
      }

      subvar = subvar[refLenRemain:]

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
  dn := (refStartPos + entryLen) - (gss.refStartVirtual + gss.refLenVirtual)

  // If the last bp in the subvar has fallen on the end of a tag,
  // the above block has taken care of updating state and
  // there is nothing more to do.
  //
  if dn <= 0 { return }

  gss.gffCurSeq = append( gss.gffCurSeq, subvar[0:dn]... )

  if noteFlag {

    if gAllowVariantOnTag || !subvarAlreadyNoted {
      gss.notes = append( gss.notes ,fmt.Sprintf("%s %s %d %d %s %s %d %d",
                                                 gRefGenome,
                                                 gss.curChrom,
                                                 gss.refStartActual+gss.refLenActual,
                                                 refStartPos+entryLen-1,
                                                 subType,
                                                 subvar,
                                                 posInSeq,
                                                 dn) )
    }

  }



  // Add the right most portion of the subvar to the right tag if it falls
  // within the tag window.
  //
  subvarOffset := gss.nextTagStart - refStartPos
  if subvarOffset < len(subvar) {
    if subvarOffset < 0 { subvarOffset = 0 }

    gss.variantOnTag = true
    gss.gffRightTagSeq = append( gss.gffRightTagSeq, subvar[subvarOffset:]... )

    if gAllowVariantOnTag || !subvarAlreadyNoted {
      if noteFlag {
        t := refStartPos - gss.nextTagStart
        subNote := fmt.Sprintf("%s %s %d %d %s %s %d %d",
          gRefGenome, gss.curChrom,
          gss.refStartActual+gss.refLenActual, refStartPos+entryLen-1,
          subType, subvar, t, dn)
        gss.carryOverNotes = append( gss.carryOverNotes, subNote )
      }
    }

  }

  gss.refLenVirtual += dn
  gss.refLenActual += dn

}



func (gss *GffScanState) processINS( finalTileSet *tile.TileSet, referenceTileSet *tile.TileSet, chromFa []byte, refStartPos int, ins_seq string, noteFlag bool ) {

  // Fill in with reference.
  //
  if refStartPos > (gss.refStartVirtual + gss.refLenVirtual) {
    gss.processREF( finalTileSet, referenceTileSet, chromFa, refStartPos, 0 )
  }

  // Since it's an insert, we don't need to advance the reference locations.  We have no
  // possibility of creating a new tile from this operation, since it all must fall
  // within a tile.  We only need to check to see if it falls within a tag boundary, and
  // if so, add it.
  //

  insPosInSeq := len(gss.gffCurSeq)
  _ = insPosInSeq

  gss.gffCurSeq = append( gss.gffCurSeq, ins_seq... )
  if refStartPos  >= gss.nextTagStart {

    gss.variantOnTag = true
    gss.gffRightTagSeq = append( gss.gffRightTagSeq, ins_seq... )

  }

}



func (gss *GffScanState) processDEL( finalTileSet *tile.TileSet, referenceTileSet *tile.TileSet, chromFa []byte, refStartPos int, del_len int, noteFlag bool) {

  // Fill in with reference.
  //
  if refStartPos > (gss.refStartVirtual + gss.refLenVirtual) {
    gss.processREF( finalTileSet, referenceTileSet, chromFa, refStartPos, 0 )
  }

  if (refStartPos + del_len) >= gss.nextTagStart { gss.variantOnTag = true }

  for ; (refStartPos + del_len) >= (gss.nextTagStart + gss.TagLen) ; {
    gss.variantOnTag = true

    if gss.refStartVirtual == gss.startPos[ gss.startPosIndex-1 ] {

      posInSeq := len(gss.gffCurSeq)
      _ = posInSeq

      // Since it's a deletion, nothin need be added to the right tag sequence
      //

      if gAllowVariantOnTag || !gss.variantOnTag {
        gss.AddTile( finalTileSet, referenceTileSet )
      }

    }

    gss.AdvanceState()

  }

  offset := gss.refLenVirtual
  _ = offset
  dn := (refStartPos + del_len) - (gss.refStartVirtual + gss.refLenVirtual)

  gss.refLenVirtual += dn
  gss.refLenActual += dn

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

// TODO: make sure to annotate INDELs that are longer than a tile to the
// tiles in the middle.  Right now it will only annotate the start INDEL
// tile and the end INDEL tile.
//
func (gss *GffScanState) processINDEL( finalTileSet *tile.TileSet, referenceTileSet *tile.TileSet, chromFa []byte, refStartPos int, indelvar string, ref_seq string, comment string ) {

  // Fill in with reference.
  //
  if refStartPos > (gss.refStartVirtual + gss.refLenVirtual) {
    gss.processREF( finalTileSet, referenceTileSet, chromFa, refStartPos, 0 )
  }

  startPos := gss.startPos[ gss.startPosIndex-1 ]
  baseTileId := gss.baseTileIdFromStartPosMap[ startPos ]

  prettyIndelvar := indelvar
  if len(indelvar) == 0 { prettyIndelvar = "-" }
  prettyRefSeq := ref_seq
  if len(prettyRefSeq) == 0 { prettyRefSeq = "-" }

  commentString := fmt.Sprintf("%s %s %d %d INDEL %d %s => %s",
    gRefGenome, gss.curChrom,
    gss.refStartActual + gss.refLenActual,  gss.refStartVirtual + gss.refLenVirtual + len(ref_seq),
    gss.refStartActual + gss.refLenActual - startPos,
    prettyRefSeq, prettyIndelvar )

  gss.notes = append( gss.notes, commentString )


  // Take the minimum of the indelvar and ref_seq length
  //
  m := len(indelvar)
  if m > len(ref_seq) { m = len(ref_seq) }

  M := len(indelvar)
  if M < len(ref_seq) { M = len(ref_seq) }

  // If there is some overlap, replace it with a 'virtual' SUB
  //
  if m>0 {
    gss.processSUB( finalTileSet, referenceTileSet, chromFa, refStartPos, indelvar[0:m], "SUB", false )
  }

  if len(indelvar) > len(ref_seq) {
    ds := len(indelvar) - len(ref_seq)
    gss.processINS( finalTileSet, referenceTileSet, chromFa, refStartPos + m, indelvar[m:m+ds], false )
  } else if len(indelvar) < len(ref_seq) {
    ds := len(ref_seq) - len(indelvar)
    gss.processDEL( finalTileSet, referenceTileSet, chromFa, refStartPos + m, ds, false )
  }


  newStartPos := gss.startPos[ gss.startPosIndex-1 ]
  newBaseTileId := gss.baseTileIdFromStartPosMap[ newStartPos ]

  if newBaseTileId != baseTileId {
    gss.notes = append( gss.notes, commentString )
  }

}

// ...
//
func (gss *GffScanState) processRegexAlteration( finalTileSet *tile.TileSet,
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
  if refStartPos > (gss.refStartVirtual + gss.refLenVirtual) {
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

  prettyIndelRegexSeq := indelRegex
  if len(indelRegex) == 0 { prettyIndelRegexSeq = "-" }

  commentString := fmt.Sprintf("%s %s %d %d %s %d %s => %s",
    gRefGenome, gss.curChrom,
    gss.refStartVirtual + gss.refLenVirtual,  gss.refStartVirtual + gss.refLenVirtual + len(ref_seq) - 1,
    varType,
    len(gss.gffCurSeq)-1,
    prettyRefSeq,
    prettyIndelRegexSeq )

  gss.notes = append( gss.notes, comment )
  gss.notes = append( gss.notes, commentString )

  gss.gffCurSeq = append( gss.gffCurSeq, indelRegex... )
  refLenRemain := (gss.nextTagStart + gss.TagLen) - (gss.refStartVirtual + gss.refLenVirtual)
  if refLenRemain < gss.TagLen {
    gss.gffRightTagSeq = append( gss.gffRightTagSeq, indelRegex... )

    if gAllowVariantOnTag {
      gss.carryOverNotes = append( gss.carryOverNotes, fmt.Sprintf("ltag: %s", comment) )
      gss.carryOverNotes = append( gss.carryOverNotes, fmt.Sprintf("ltag: %s", commentString) )
    }

    gss.variantOnTag = true
  }

  entryLen := len(ref_seq)

  // We've spilled over
  //
  for ; (refStartPos + entryLen) >= (gss.nextTagStart + gss.TagLen) ; {

    if gss.refStartVirtual == gss.startPos[ gss.startPosIndex-1 ] {

      if gAllowVariantOnTag || !gss.variantOnTag {
        gss.AddTile( finalTileSet, referenceTileSet )
      }
    }
    gss.AdvanceState()

  }

  dn := (refStartPos + entryLen) - (gss.refStartVirtual + gss.refLenVirtual)
  gss.refLenVirtual += dn
  gss.refLenActual += dn

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

  return var0, var1, ref_seq

}

var g_rand *rand.Rand

func initCommandLineOptions( c *cli.Context ) {
  _ = time.Now()

  g_gffFileName = c.String("input-gff")
  g_fastjFileName = c.String("input-fastj")
  g_chromFileName = c.String("fasta-chromosome")
  g_outputFastjFileName = c.String("output-fastj")

  g_variantPolicy = c.String("variant-policy")

  gAllowVariantOnTag = c.Bool("allow-variant-on-tag")

  // Default is to place 'n' for no-called regions
  // in the sequence.  Enableing this flag will
  // fill the tile with reference.
  //
  gPlaceNoCallInSeq = !c.Bool("fill-no-call-with-ref")

  ts := time.Now().UnixNano()
  _ = ts
  g_randomSeed = int64(c.Int("seed"))

  g_verboseFlag = c.Bool("verbose")
  g_notes = c.String("note")

  if g_variantPolicy == "HETA" {
  } else if g_variantPolicy == "REPORTED" {
  } else if g_variantPolicy == "RANDOM" {
  } else if g_variantPolicy == "REGEX" {
  } else {
    fmt.Fprintf( os.Stderr, "Unknown variant policy %s\n", g_variantPolicy)
    cli.ShowAppHelp(c)
    os.Exit(2)
  }

  if len(g_gffFileName)==0 {
    fmt.Fprintf( os.Stderr, "Provide input GFF file\n")
    cli.ShowAppHelp(c)
    os.Exit(2)
  }

  if len(g_fastjFileName)==0 {
    fmt.Fprintf( os.Stderr, "Provide input FastJ file\n")
    cli.ShowAppHelp(c)
    os.Exit(2)
  }

  if len(g_chromFileName)==0 {
    fmt.Fprintf( os.Stderr, "Provide chromosome FASTA file\n")
    cli.ShowAppHelp(c)
    os.Exit(2)
  }

  var err error
  gBioEnvWriter,err = bioenv.CreateWriter( g_outputFastjFileName )
  if err != nil {
    fmt.Fprintf( os.Stderr, "Could not open FastJ file '%s' for writing: %v\n", g_outputFastjFileName, err )
    os.Exit(2)
  }

  gOutputWriter = gBioEnvWriter.Writer


  gProfileFlag = c.Bool("profile")
  gProfileFile = c.String("profile-file")
}

func main() {

  app := cli.NewApp()
  app.Name  = "gff2fj"
  app.Usage = "Convert a (chopped) GFF file to a FastJ file"
  app.Version = VERSION_STR
  app.Author = "Curoverse Inc."
  app.Email = "info@curoverse.com"
  app.Action = func( c *cli.Context ) {
    initCommandLineOptions(c)
    _main(c)
  }

  app.Flags = []cli.Flag{

    cli.StringFlag{
      Name: "input-gff, i",
      Usage: "Input GFF file" },

    cli.StringFlag{
      Name: "input-fastj, f",
      Usage: "Input FastJ file" },

    cli.StringFlag{
      Name: "fasta-chromosome, c",
      Usage: "Input chromosome Fasta file" },

    cli.StringFlag{
      Name: "output-fastj, o",
      Usage: "Output FastJ file" },

    cli.StringFlag{
      Name: "variant-policy, P",
      Value: "REPORTED",
      Usage: "Variant policy (one of 'REPORTED', 'HETA', 'RANDOM' or 'REGEX') (default to 'REPORTED')" },

    cli.StringFlag{
      Name: "note, a",
      Usage: "Annotation to add to the 'note' list in the FastJ header" },

    cli.BoolFlag{
      Name: "allow-variant-on-tag, T",
      Usage: "Allow variants on tags (by default, tiles are extended to not allow variants on tags)" },

    cli.BoolFlag{
      Name: "fill-no-call-with-ref",
      Usage: "Fill in regions that weren't called with the reference provided (default places 'n' in sequence)" },

    cli.IntFlag{
      Name: "seed, S",
      Usage: "Random seed (default to current time)" },

    cli.BoolFlag{
      Name: "verbose, V",
      Usage: "Verbose flag" },

    cli.BoolFlag{
      Name: "profile",
      Usage: "Profile flag" },

    cli.StringFlag{
      Name: "profile-file",
      Value: "gff2fj.pprof",
      Usage: "Output profile file" },

  }

  app.Run(os.Args)

}

func processRegexLine( gss *GffScanState,
                       finalTileSet *tile.TileSet,
                       referenceTileSet *tile.TileSet,
                       chromFa []byte,
                       s int,
                       dn int,
                       varType string,
                       comment string,
                       condensed_comment string) {


  if ( varType == "REF" ) {

    gss.processREF( finalTileSet, referenceTileSet, chromFa, s, dn )

  } else if ( (varType == "INDEL") || (varType == "SUB") ) {

    indelvar0, indelvar1, ref_seq := parseVariants( comment )

    if indelvar0 <= indelvar1 {
      gss.processRegexAlteration( finalTileSet, referenceTileSet, chromFa, s, varType, indelvar0, indelvar1, ref_seq, condensed_comment )
    } else {
      gss.processRegexAlteration( finalTileSet, referenceTileSet, chromFa, s, varType, indelvar1, indelvar0, ref_seq, condensed_comment )
    }

  } else if ( varType == "SNP" ) {

    subvar0, subvar1, ref_seq := parseVariants( comment )

    if subvar0 <= subvar1 {
      gss.processRegexSNP( finalTileSet, referenceTileSet, chromFa, s, subvar0, subvar1, ref_seq, condensed_comment )
    } else {
      gss.processRegexSNP( finalTileSet, referenceTileSet, chromFa, s, subvar1, subvar0, ref_seq, condensed_comment )
    }

  } else {
    panic( fmt.Sprintf("unknown varType %s on line %d", varType, gLineNo) )
  }


}

func _main( c *cli.Context ) {

  if gProfileFlag {
    prof_f,err := os.Create( gProfileFile )
    if err != nil {
      fmt.Fprintf( os.Stderr, "Could not open profile file %s: %v\n", gProfileFile, err )
      os.Exit(2)
    }

    pprof.StartCPUProfile( prof_f )
    defer pprof.StopCPUProfile()
  }

  g_rand = rand.New( rand.NewSource(g_randomSeed) )

  tagLen := 24

  gffFn := g_gffFileName
  fastjFn := g_fastjFileName
  chromFaFn := g_chromFileName
  gNoteLine := g_notes

  gDebugString = fmt.Sprintf( "%s %s %s %s %s", gffFn, fastjFn, chromFaFn, g_outputFastjFileName, gNoteLine )


  //-----------------------------
  // Load the tile set for this band.
  //
  if g_verboseFlag { fmt.Println("# loading", fastjFn, "into memory...") }
  referenceTileSet := tile.NewTileSet( tagLen )
  referenceTileSet.ReadFastjFile( fastjFn )

  g_referenceTileSet = referenceTileSet

  finalTileSet := tile.NewTileSet( tagLen )
  _ = finalTileSet

  //
  //-----------------------------


  //-----------------------------
  // Initialize Gff Scan State
  //
  gss0 := GffScanState{}
  gss1 := GffScanState{}

  gss0.phase = "A"
  gss0.VariantId = 0

  gss1.phase = "B"
  gss1.VariantId = 1

  gss0.notes = make( []string, 0, 10 )
  gss1.notes = make( []string, 0, 10 )
  if len(gNoteLine) > 0 { gss0.notes = append( gss0.notes, gNoteLine ) }
  if len(gNoteLine) > 0 { gss1.notes = append( gss1.notes, gNoteLine ) }

  // refStart is 0 based
  //
  gss0.gffCurSeq = make( []byte, 0, 10 )
  gss0.baseTileIdFromStartPosMap = make( map[int]string )
  gss0.refStartVirtual, gss0.refLenVirtual = -1, 0
  gss0.refStartActual, gss0.refLenActual = -1, 0
  gss0.TagLen = tagLen
  gss0.carryOverNotes = make( []string, 0, 10 )
  gss0.seedTileLength = 1

  gss0.generateTileStartPositions( referenceTileSet, "hg19" )


  gss1.gffCurSeq = make( []byte, 0, 10 )
  gss1.baseTileIdFromStartPosMap = make( map[int]string )
  gss1.refStartVirtual, gss1.refLenVirtual = -1, 0
  gss1.refStartActual, gss1.refLenActual = -1, 0
  gss1.TagLen = tagLen
  gss1.carryOverNotes = make( []string, 0, 10 )
  gss1.seedTileLength = 1

  gss1.generateTileStartPositions( referenceTileSet, "hg19" )

  //
  //-----------------------------



  //-----------------------------
  // Load our hg reference band.
  //
  if g_verboseFlag { fmt.Println("# loading", chromFaFn, "into memory...") }
  chromFa,err := aux.FaToByteArray( chromFaFn )
  if err != nil { panic(err) }
  _ = chromFa

  count := 0
  _ = count

  if g_verboseFlag { fmt.Println("# reading gff") }

  //
  //-----------------------------


  gffReader,err := bioenv.OpenScanner( gffFn )
  if err != nil { panic(err) }
  defer gffReader.Close()

  //line_no := -1
  gLineNo = -1


  for gffReader.Scanner.Scan() {
    l := gffReader.Scanner.Text()

    //line_no += 1
    gLineNo += 1

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

    // converting to 0 based, end inclusive
    //
    s -= 1
    e -= 1

    tmpstr,_ := recache.ReplaceAllString( `\s+`, comment, " " )
    condensed_comment := fmt.Sprintf("gffsrc: %s %d %d %s %s", chrom, s, e, varType, tmpstr )

    if g_variantPolicy == "REGEX" {
      processRegexLine( &gss0, finalTileSet, referenceTileSet, chromFa, s, e-s+1, varType, comment, condensed_comment )
      continue
    }

    if ( varType == "REF" ) {

      gss0.processREF( finalTileSet, referenceTileSet, chromFa, s, e - s + 1 )
      gss1.processREF( finalTileSet, referenceTileSet, chromFa, s, e - s + 1 )

    } else if ( varType == "INDEL" ) {

      indelvar0, indelvar1, ref_seq := parseVariants( comment )

      switch g_variantPolicy {
      case "REPORTED":

        if indelvar0 == ref_seq {
          gss0.processREF( finalTileSet, referenceTileSet, chromFa, s, len(ref_seq) )
        } else {
          gss0.notes = append( gss0.notes, condensed_comment )
          gss0.processINDEL( finalTileSet, referenceTileSet, chromFa, s, indelvar0, ref_seq, comment )
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

    } else if ( (varType == "SUB") || (varType == "SNP") ) {

      subvar0, subvar1, ref_seq := parseVariants( comment )

      switch g_variantPolicy {
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

    } else {

      panic( fmt.Sprintf("unknown varType %s on line %d", varType, gLineNo) )
    }

  }

  gss0.AddTile( finalTileSet, referenceTileSet )

  if g_variantPolicy != "REGEX" {
    gss1.AddTile( finalTileSet, referenceTileSet )
  }

  gBioEnvWriter.Flush()
  gBioEnvWriter.Close()

}
