/* STILL A WORK IN PROGRESS
   Load ucsc.cytomap.hg19.txt into memory
   Load each chromosome in use (fasta file) into memory
   scan the bedGraph file for tag positions

   doing some preliminary benchmarks to make sure this will
   complete in a reasonable amount of time.

   2014-04-25
   Got through chromosome 1, started chromosome 2 but was killed.
   Last time that happened it was due to memoery issues.
   Also, last fastj sequence is not created/written (with corresponding
   '.'*24 tag at the end)

   UPDATE:
   This should be working, but I've restricted to a chromosome by chromosome
   run.  That is, specify the chromosome on the command line and only one
   one chromosome per invocation of the program.
*/

package main

import "fmt"
import "os"
import _ "os/exec"
import "bufio"
import "strconv"
import "strings"
import "regexp"

import "flag"

import _ "io/ioutil"
import _ "time"

import _ "runtime"

import "runtime/pprof"

import "./aux"
import "./bioenv"

import "crypto/md5"

var CHR = []string{ "chr1", "chr2", "chr3", "chr4", "chr5", "chr6", "chr7", "chr8", "chr9", "chr10",
                    "chr11", "chr12", "chr13", "chr14", "chr15", "chr16", "chr17", "chr18", "chr19", "chr20",
                    "chr21", "chr22", "chrX", "chrY", "chrM" }

var BAND_BOUNDS map[string]map[int][2]int
var PID = os.Getpid()
var MIN_TILE_DIST = 200

type FastjInfo struct {
  band, revision, class int
  minTileDistance int
  bodyLineWidth int
  info map[string]interface{}
  build string
}

func uc( b byte ) byte {
  if (b >= 0x61) && (b <= 0x7a) { return b-32 }
  return b
}

func lc( b byte ) byte {
  if (b >= 0x41) && (b <= 0x5a) { return b+32 }
  return b
}

/* We're still thinking about fastj formats.  Current thinking (2014-05-07)
   is that a more 'fasta like' format is better, with the comment being json,
   with the tags optionally included and the body of the tile sequence (without
   tags) being printed.
   Only comments are valid fastj.
   */
func printFastjElement( writerFastj *bufio.Writer,
                        chrFa []byte,
                        tileID string,
                        tileStart int, tileEnd int,
                        tagLength int,
                        leftEndStopFlag bool , rightEndStopFlag bool,
                        bodyLineWidth int,
                        buildInfo string) {

  var md5sum [16]byte;
  tileseq := make( []byte, 0, 300 )

  str := fmt.Sprintf(">{ \"tileID\":\"%s\", ", tileID)
  writerFastj.WriteString( str )




  //-------------------------


  tileseq = append( tileseq, strings.ToUpper( string( chrFa[ tileStart: tileStart + tagLength] ) )... )
  tileseq = append( tileseq, strings.ToLower( string( chrFa[ tileStart + tagLength: tileEnd - tagLength ]) )... )
  tileseq = append( tileseq, strings.ToUpper( string( chrFa[ tileEnd - tagLength: tileEnd ] ) )... )

  md5sum = md5.Sum( tileseq )

  var str_md5sum [32]byte
  for i:=0; i<16; i++ {
    x := fmt.Sprintf("%02x", md5sum[i])
    str_md5sum[2*i]   = x[0]
    str_md5sum[2*i+1] = x[1]
  }

  str = fmt.Sprintf("\"md5sum\":\"%s\", ", str_md5sum)
  writerFastj.WriteString( str )

  //-------------------------



  m := 0
  offsetBeg, offsetEnd := tagLength, tagLength
  if leftEndStopFlag { offsetBeg = 0; m += tagLength }
  if rightEndStopFlag { offsetEnd = 0; m += tagLength }

  _ = offsetBeg

  //str = fmt.Sprintf("\"locus\":[{ \"build\" : \"hg19 ")
  str = fmt.Sprintf("\"locus\":[{ \"build\" : \"%s ", buildInfo)
  writerFastj.WriteString( str )


  if leftEndStopFlag {
    str = fmt.Sprintf("%d-%d ", tileStart, tagLength )
  } else {
    str = fmt.Sprintf("%d ", tileStart )
  }
  writerFastj.WriteString( str )

  if rightEndStopFlag {
    str = fmt.Sprintf("%d+%d", tileEnd, tagLength )
  } else {
    str = fmt.Sprintf("%d", tileEnd )
  }
  writerFastj.WriteString( str )

  str = fmt.Sprintf( "\"}], " )
  writerFastj.WriteString( str )


  //str = fmt.Sprintf("\"n\":\"%d\", ", tileEnd - tileStart + m )
  str = fmt.Sprintf("\"n\":%d, ", tileEnd - tileStart + m )
  writerFastj.WriteString( str )


  //str = fmt.Sprintf("\"copy\":\"1\", ")
  str = fmt.Sprintf("\"copy\":1, ")
  writerFastj.WriteString( str )

  str = fmt.Sprintf("\"startTag\":\"" )
  writerFastj.WriteString( str )

  if leftEndStopFlag {
    for i:=0; i<tagLength; i++ { writerFastj.WriteString( "." ) }
  } else {
    writerFastj.WriteString( strings.ToUpper( string( chrFa[ tileStart : tileStart + tagLength ] ) ))
  }

  str = fmt.Sprintf("\", ");
  writerFastj.WriteString( str )

  str = fmt.Sprintf("\"endTag\":\"" )
  writerFastj.WriteString( str )

  if rightEndStopFlag {
    for i:=0; i<tagLength; i++ { writerFastj.WriteString( "." ) }
  } else {
    writerFastj.WriteString( strings.ToUpper( string( chrFa[ tileEnd - offsetEnd : tileEnd ] ) ))
  }

  str = fmt.Sprintf("\"");
  writerFastj.WriteString( str )

  str = fmt.Sprintf("}\n" )
  writerFastj.WriteString( str )

  //---

  /*
  bpCount := 0

  leftTag_b := make( []byte, tagLength )
  for i:=0; i<tagLength; i++ { leftTag_b[i] = '.' }

  leftTag := string( leftTag_b )
  if !leftEndStopFlag {
    leftTag = strings.ToUpper( string( chrFa[ tileStart: tileStart + tagLength] ) )
  }

  for i:=0; i<tagLength; i++ {
    if (bpCount>0) && ((bpCount%bodyLineWidth) == 0) { writerFastj.WriteString( "\n" ) }
    writerFastj.WriteByte( leftTag[i] )
    bpCount++
  }


  //---

  midTile := chrFa[ tileStart + offsetBeg : tileEnd - offsetEnd ]

  n := len(midTile)
  for i:=0; i<n; i++ {

    if (bpCount>0) && ((bpCount%bodyLineWidth) == 0) {
      writerFastj.WriteString( "\n" )
    }
    writerFastj.WriteByte( midTile[i] )

    bpCount++
  }


  //---

  rightTag_b := make( []byte, tagLength )
  for i:=0; i<tagLength; i++ { rightTag_b[i] = '.' }

  rightTag := string( rightTag_b )
  if !rightEndStopFlag {
    rightTag = strings.ToUpper( string( chrFa[ tileEnd - offsetEnd: tileEnd ] ) )
  }

  for i:=0; i<tagLength; i++ {
    if (bpCount>0) && ((bpCount%bodyLineWidth) == 0) { writerFastj.WriteString( "\n" ) }
    writerFastj.WriteByte( rightTag[i] )
    bpCount++
  }

  //---
  */

  bpCount := 0
  for bpCount<tagLength {
    if (bpCount>0) && ((bpCount%bodyLineWidth) == 0) { writerFastj.WriteString( "\n" ) }
    writerFastj.WriteByte( uc( chrFa[ tileStart + bpCount ] ) )
    bpCount++
  }

  for (tileStart+bpCount) < (tileEnd - tagLength) {
    if (bpCount>0) && ((bpCount%bodyLineWidth) == 0) { writerFastj.WriteString( "\n" ) }
    writerFastj.WriteByte( lc( chrFa[ tileStart + bpCount ] ) )
    bpCount++
  }

  for (tileStart+bpCount) < tileEnd {
    if (bpCount>0) && ((bpCount%bodyLineWidth) == 0) { writerFastj.WriteString( "\n" ) }
    writerFastj.WriteByte( uc( chrFa[ tileStart + bpCount ] ) )
    bpCount++
  }

  writerFastj.WriteString("\n")

}


func printFastJSONElement( writerFastj *bufio.Writer,
                        chrFa []byte,
                        tileID string,
                        tileStart int, tileEnd int,
                        tagLength int,
                        leftEndStopFlag bool , rightEndStopFlag bool ) {


  str := fmt.Sprintf("  \"%s\": {\n    \"tileID\":\"%s\",\n", tileID, tileID)
  writerFastj.WriteString( str )

  m := 0
  offsetBeg, offsetEnd := tagLength, tagLength
  if leftEndStopFlag { offsetBeg = 0; m += tagLength }
  if rightEndStopFlag { offsetEnd = 0; m += tagLength }

  str = fmt.Sprintf("    \"locus\" : [{ \"build\" : \"hg19 ")
  writerFastj.WriteString( str )


  if leftEndStopFlag {
    str = fmt.Sprintf("%d-%d ", tileStart, tagLength )
  } else {
    str = fmt.Sprintf("%d ", tileStart )
  }
  writerFastj.WriteString( str )

  if rightEndStopFlag {
    str = fmt.Sprintf("%d+%d", tileEnd, tagLength )
  } else {
    str = fmt.Sprintf("%d", tileEnd )
  }
  writerFastj.WriteString( str )

  str = fmt.Sprintf( "\" }],\n" )
  writerFastj.WriteString( str )


  str = fmt.Sprintf("    \"n\":\"%d\",\n", tileEnd - tileStart + m )
  writerFastj.WriteString( str )


  str = fmt.Sprintf("    \"copy\":\"1\",\n")
  writerFastj.WriteString( str )


  str = fmt.Sprintf("    \"tile\":\"" )
  writerFastj.WriteString( str )

  if leftEndStopFlag {
    for i:=0; i<tagLength; i++ { writerFastj.WriteString( "." ) }
  } else {
    writerFastj.WriteString( strings.ToUpper( string( chrFa[ tileStart : tileStart + tagLength ] ) ))
  }

  midTile := chrFa[ tileStart + offsetBeg : tileEnd - offsetEnd ]
  writerFastj.Write( midTile )

  if rightEndStopFlag {
    for i:=0; i<tagLength; i++ { writerFastj.WriteString( "." ) }
  } else {
    writerFastj.WriteString( strings.ToUpper( string( chrFa[ tileEnd - offsetEnd : tileEnd ] ) ))
  }

  str = fmt.Sprintf("\"\n  }" )
  writerFastj.WriteString( str )

}


// chrFa holds an ascii block of the chromosome as it appears in the fasta file,
//   with header and newlines stripped out
// inpBedGraphFilename will open a the bedgraph file and scan it one line at a time
// outFastjFilename will write the JSON fastj tileset
// seqStart and seqEnd are the beginning and end of the 'band' (or 'sub-band') of the block
//   for the fastj that we're creating.
// FastjInfo holds some parameters for the fastj file creation, such as the minimum tile length.
//
// Each line of the bedGraph file has a start, end and value.  We are only concerned with values of 1
//   that represent a unique 24mer and we skip the rest.  For entries in the bedGraph that are unique,
//   if the minimum end of the sequence (that is ~200 bp away from the start of our current tile) is
//   to the right of the end of the bedGraph entry, skip.  If the minimum end sequence position is
//   in the middle of the start and end of the bedGraph entry, take the tag start to be the minimum
//   end sequence position.  If the minimum end sequence position is to the left of the start position
//   of the signal in the bedGraph file, take the start position of the bedGraph entry as the start
//   of the tag/tile.
//
// TODO: make sure we take care of the fencepost errors that might be lurking.  There is minTileDistance
//   and making sure the bedGraph entries are indexed properly against the chrFa fasta byte array.
//
func WriteFastjFromBedGraph( chrFa []byte, inpBedGraphFilename string, outFastjFilename string,
                             seqStart int, seqEnd int,
                             fjInfo FastjInfo ) {

  benvReader,err := bioenv.OpenScanner( inpBedGraphFilename )
  if err != nil { panic( fmt.Sprintf( "%s: %s", inpBedGraphFilename ,  err) ) }
  defer benvReader.Close()

  benvWriter,err := bioenv.CreateWriter( outFastjFilename )
  if err != nil { panic( fmt.Sprintf( "%s: %s", outFastjFilename, err) ) }
  defer func() { benvWriter.Flush() ; benvWriter.Close() }()

  minEndSeqPos := seqStart + fjInfo.minTileDistance
  tilePos := 0

  prevTagStart := -1
  nextTagStart := seqStart

  mergeLastFlag := false

  re_comment  ,_ := regexp.Compile( `^#` )
  re_blankline,_ := regexp.Compile( `^\s*$` )

  for benvReader.Scanner.Scan() {
    l := benvReader.Scanner.Text()

    if re_comment.MatchString( l )   { continue }
    if re_blankline.MatchString( l ) { continue }

    fields := strings.SplitN( l, "\t", -1 )
    s,_ := strconv.Atoi(fields[1])
    e,_ := strconv.Atoi(fields[2])
    v,_ := strconv.ParseFloat(fields[3], 64)

    // If this is not a unique 24mer or we fall within
    // the minimum tile window, skip.
    //
    if v != 1 { continue }
    if e < minEndSeqPos { continue }

    if tilePos>0 { benvWriter.Writer.WriteString("\n\n") }

    tileID := fmt.Sprintf("%03x.%02x.%03x.%03x", fjInfo.band, fjInfo.revision, tilePos, 0 )

    prevTagStart = nextTagStart
    nextTagStart = s+1
    if s < minEndSeqPos{ nextTagStart = minEndSeqPos + 1 }

    if (seqEnd - nextTagStart) <= fjInfo.minTileDistance {
      mergeLastFlag = true
      break
    }

    printFastjElement( benvWriter.Writer, chrFa, tileID,
                       prevTagStart, nextTagStart + 24, 24,
                       ( tilePos == 0 ), false, fjInfo.bodyLineWidth,
                       fjInfo.build)

    minEndSeqPos = nextTagStart + fjInfo.minTileDistance + 24
    tilePos ++

  }

  if !mergeLastFlag {
    prevTagStart = nextTagStart
  }

  tileID := fmt.Sprintf("%03x.%02x.%03x.%03x", fjInfo.band, fjInfo.revision, tilePos, 0 )

  printFastjElement( benvWriter.Writer, chrFa, tileID,
                     prevTagStart, seqEnd, 24,
                     ( tilePos == 0 ), true, fjInfo.bodyLineWidth ,
                     fjInfo.build)

}

func CalculateAbsoluteBand( bandBounds map[string]map[int][2]int, curChrom string , chromOrder []string ) int {
  s := 0
  for _,chrom := range chromOrder {
    if chrom == curChrom { return s }
    s += len(bandBounds[chrom])
  }
  return -1
}

var benv bioenv.BioEnvContext

var g_profileFlag *bool
var g_refGenome *string
var g_chromFaFn *string
var g_chromName *string
var g_bandNum *int
var g_bedGraphFn *string
var g_outFastjFn *string
var g_cytomapFilename *string

var g_verboseFlag *bool

func init() {
  var err error
  benv,err = bioenv.BioEnv()
  if err != nil { panic( fmt.Sprintf("bioenv: %s", err) ) }

  g_verboseFlag = flag.Bool("verbose", false, "Verbose")
  flag.BoolVar( g_verboseFlag, "v", false, "Verbose")

  g_profileFlag = flag.Bool("profile", false, "Turn profiling on ('buildTileSet.profile')")
  g_refGenome   = flag.String("reference", benv.Env["reference"], "Reference genome to use (default 'hg19')")
  g_chromFaFn     = flag.String("fasta-chromosome", "", "Chromosome fasta file location (will try to guess if none specified)")

  g_chromName     = flag.String("chromosome", "", "Chromsome name/number (e.g. '1', '2', ..., 'X', 'Y')")
  flag.StringVar( g_chromName, "c", "", "Chromsome name/number (e.g. '1', '2', ..., 'X', 'Y')")

  g_bandNum     = flag.Int("band", -1, "Band number")
  flag.IntVar( g_bandNum, "b", -1, "Band number")

  g_bedGraphFn  = flag.String("bedGraph", "", "Bedgraph file")
  flag.StringVar( g_bedGraphFn, "i", "", "BedGraph file")

  g_outFastjFn  = flag.String("fastj-output", "", "Output Fastj file")
  flag.StringVar( g_outFastjFn, "o", "", "Output Fastj file")

  g_cytomapFilename  = flag.String("cytoBand", benv.Env["cytoBand"], "Cytoband file (will use default if none specified)")

  flag.Parse()
  benv.ProcessFlag()

  //if len(*g_refGenome)==0 { *g_refGenome = benv.Env["reference"] }
  //if len(*g_cytomapFilename)==0 { *g_cytomapFilename = benv.Env["cytoBand"] }

  if (len(*g_bedGraphFn)==0) || (len(*g_outFastjFn)==0) {
    fmt.Fprintf( os.Stderr, "Provide input bedGraph file and output Fastj file\n" )
    flag.PrintDefaults()
    os.Exit(2)
  }

  if (*g_bandNum < 0) {
    fmt.Fprintf( os.Stderr, "Band must be non negative\n")
    flag.PrintDefaults()
    os.Exit(2)
  }

  if len(*g_chromName)==0 {
    fmt.Fprintf( os.Stderr, "Provide chromsome name\n")
    flag.PrintDefaults()
    os.Exit(2)
  }

  i:=0
  for i=0; i<len(CHR); i++ {
    if *g_chromName == CHR[i] {
      break
    }
    t_chrom := fmt.Sprintf("chr%s", *g_chromName)
    if t_chrom == CHR[i] { *g_chromName = t_chrom ; break }
  }

  if i==len(CHR) {
    fmt.Fprintf( os.Stderr, "Could not find chromosome\n")
    flag.PrintDefaults()
    os.Exit(2)
  }

  if len(*g_chromFaFn)==0 {
    s := *g_refGenome + ":" + *g_chromName + ".fa"
    *g_chromFaFn = benv.Env[ s ]
  }

}


func main() {

  //PROFILING
  if (*g_profileFlag) {
    profFp, _ := os.Create("buildTileSet.profile")
    pprof.StartCPUProfile(profFp)
    defer pprof.StopCPUProfile()
  }
  //PROFILING


  if (*g_verboseFlag) {
    fmt.Printf("#buildTileSet\n")
    fmt.Printf("# cytoBand: %s\n", *g_cytomapFilename )
    fmt.Printf("# referenceGenome: %s\n", *g_refGenome )
    fmt.Printf("# chromsome: %s\n", *g_chromName )
    fmt.Printf("# chromosome Fasta file: %s\n", *g_chromFaFn )
  }


  fastjInfo := FastjInfo{ band: *g_bandNum, revision: 0, class: 0, minTileDistance: 200, bodyLineWidth:50, build: "" }

  fastjInfo.build = fmt.Sprintf("hg19 %s", *g_chromName)

  if *g_verboseFlag {
    fmt.Println("# finding tag set for", *g_chromName, ", band", *g_bandNum, ", using", *g_bedGraphFn, "and", *g_cytomapFilename)
  }


  BAND_BOUNDS = make( map[string]map[int][2]int  )
  aux.BuildBandBounds( BAND_BOUNDS, *g_cytomapFilename )

  if *g_verboseFlag { 
    fmt.Println("# loading", *g_chromFaFn, "into memory...")
  }

  chrFa,e := aux.FaToByteArray( *g_chromFaFn)
  if e != nil { panic( fmt.Sprintf("%s: %s", chrFa, e ) ) }

  aux.ToLowerInPlace(chrFa)

  baseAbsoluteBand := CalculateAbsoluteBand( BAND_BOUNDS, *g_chromName, CHR )
  fastjInfo.band = baseAbsoluteBand + *g_bandNum

  if *g_verboseFlag {
    fmt.Println( "#", *g_chromName, "band:", *g_bandNum, fmt.Sprintf("(%d)", fastjInfo.band), "-->", *g_outFastjFn )
  }

  WriteFastjFromBedGraph( chrFa, *g_bedGraphFn,
                          *g_outFastjFn,
                          BAND_BOUNDS[*g_chromName][*g_bandNum][0], BAND_BOUNDS[*g_chromName][*g_bandNum][1],
                          fastjInfo )

  if *g_verboseFlag {
    fmt.Printf("# done\n")
  }


}
