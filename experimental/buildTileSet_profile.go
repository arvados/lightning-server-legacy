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
*/

package main

import "fmt"
import "os"
import _ "os/exec"
import "bufio"
import "strconv"
import "strings"
import "regexp"
import _ "io/ioutil"
import _ "time"

import _ "runtime"

import "runtime/pprof"

import "./aux"

var CHR = []string{ "chr1", "chr2", "chr3", "chr4", "chr5", "chr6", "chr7", "chr8", "chr9", "chr10",
                    "chr11", "chr12", "chr13", "chr14", "chr15", "chr16", "chr17", "chr18", "chr19", "chr20",
                    "chr21", "chr22", "chrX", "chrY", "chrM" }
//var BAND_BOUNDS = make( map[string]map[int][2]int )
var BAND_BOUNDS map[string]map[int][2]int 
var PID = os.Getpid()
var MIN_TILE_DIST = 200

type FastjInfo struct {
  band, revision, class int
  minTileDistance int
  info map[string]interface{}
}

func printFastjElement( writerFastj *bufio.Writer,
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

  bgFp, err := os.Open( inpBedGraphFilename )
  if err != nil { panic(err) }
  defer bgFp.Close()

  fastjFp, err := os.Create(outFastjFilename)
  if err != nil { panic(err) }
  defer fastjFp.Close()
  writerFastj := bufio.NewWriter(fastjFp)

  minEndSeqPos := seqStart + fjInfo.minTileDistance
  tilePos := 0

  prevTagStart := -1
  nextTagStart := seqStart

  mergeLastFlag := false

  writerFastj.WriteString("{\n")

  re_comment  ,_ := regexp.Compile( `^#` )
  re_blankline,_ := regexp.Compile( `^\s*$` )

  scanner := bufio.NewScanner( bgFp )
  for scanner.Scan() {
    l := scanner.Text()

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

    if tilePos > 0 { writerFastj.WriteString(",\n\n") }
    //tileID := fmt.Sprintf("%03x%02x%03x%03x", fjInfo.band, fjInfo.revision, tilePos, 0 )
    tileID := fmt.Sprintf("%03x.%02x.%03x.%03x", fjInfo.band, fjInfo.revision, tilePos, 0 )

    prevTagStart = nextTagStart
    nextTagStart = s+1
    if s < minEndSeqPos{ nextTagStart = minEndSeqPos + 1 }

    if (seqEnd - nextTagStart) <= fjInfo.minTileDistance { 
      mergeLastFlag = true
      break 
    }

    printFastjElement( writerFastj, chrFa, tileID,
                       prevTagStart, nextTagStart + 24, 24,
                       ( tilePos == 0 ), false )

    minEndSeqPos = nextTagStart + fjInfo.minTileDistance + 24
    tilePos ++

  }

  if tilePos > 0 { writerFastj.WriteString(",\n\n") }

  if !mergeLastFlag {
    prevTagStart = nextTagStart
  }

  //tileID := fmt.Sprintf("%03x%02x%03x%03x", fjInfo.band, fjInfo.revision, tilePos, 0 )
  tileID := fmt.Sprintf("%03x.%02x.%03x.%03x", fjInfo.band, fjInfo.revision, tilePos, 0 )
  printFastjElement( writerFastj, chrFa, tileID,
                     prevTagStart, seqEnd, 24,
                     ( tilePos == 0 ), true )

  writerFastj.WriteString( "\n}\n" )
  if err := writerFastj.Flush(); err != nil { panic(err) }

}

func CalculateAbsoluteBand( bandBounds map[string]map[int][2]int, curChrom string , chromOrder []string ) int {
  s := 0
  for _,chrom := range chromOrder {
    if chrom == curChrom { return s }
    s += len(bandBounds[chrom])
  }
  return -1
}


func main() {


  //PROFILING
  profFp, _ := os.Create("buildTileSet_profile.profile")
  pprof.StartCPUProfile(profFp)
  defer pprof.StopCPUProfile()
  //PROFILING

  cytomapFilename  := "ucsc.cytomap.hg19.txt"

  if len(os.Args) != 6 {
    fmt.Println("usage: bedGraph band filename")
    fmt.Println("./buildTileSet.go <chromosomeNumber> <chromsomeFastaFile> <bandNumber> <bedGraphBandFile> <outputFastjFn>")
    os.Exit(0)
  }

  //chromNumber, err := strconv.Atoi(os.Args[1]); if err != nil { panic(err) }
  chromStr := os.Args[1]
  chrFastaFilename := os.Args[2]
  band, err := strconv.Atoi(os.Args[3]); if err != nil { panic(err) }
  bandBedGraphFilename := os.Args[4]
  fastjFn := os.Args[5]


  //curChrom := fmt.Sprintf("chr%d", chromNumber)
  curChrom := fmt.Sprintf( "chr%s", chromStr )
  fastjInfo := FastjInfo{ band: band, revision: 0, class: 0, minTileDistance: 200 }

  fmt.Println("# finding tag set for", curChrom, ", band", band, ", using", bandBedGraphFilename, "and", cytomapFilename)


  // should probably be BAND_BOUNDS = aux.BuildBandBounds( cytomapFilename ) ?
  //
  BAND_BOUNDS = make( map[string]map[int][2]int  )
  aux.BuildBandBounds( BAND_BOUNDS, cytomapFilename )

  fmt.Println("# loading", chrFastaFilename, "into memory...")
  chrFa := aux.FaToByteArray( chrFastaFilename )

  aux.ToLowerInPlace(chrFa)

  baseAbsoluteBand := CalculateAbsoluteBand( BAND_BOUNDS, curChrom, CHR )
  fastjInfo.band = baseAbsoluteBand + band

  /*
  fastjFn := fmt.Sprintf( "/scratch/abram/fastj/%s_band%d_s%d_e%d.fj",
                          curChrom,
                          band,
                          BAND_BOUNDS[curChrom][band][0],
                          BAND_BOUNDS[curChrom][band][1] )
                          */


  fmt.Println( "#", curChrom, "band:", band, fmt.Sprintf("(%d)", fastjInfo.band), "-->", fastjFn )

  WriteFastjFromBedGraph( chrFa, bandBedGraphFilename, 
                          fastjFn, 
                          BAND_BOUNDS[curChrom][band][0], BAND_BOUNDS[curChrom][band][1],
                          fastjInfo )


  fmt.Printf("# done\n")


}
