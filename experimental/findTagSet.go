/* STILL A WORK IN PROGRESS
   Load ucsc.cytomap.hg19.txt into memory
   Load each chromosome in use (fasta file) into memory
   scan the bedGraph file for tag positions

   doing some preliminary benchmarks to make sure this will
   complete in a reasonable amount of time.
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



func WriteFastjFromBedGraph( chrFa []byte, inpBedGraphFilename string, outFastjFilename string, 
                             seqStart int,
                             fjInfo FastjInfo ) {

  bgFp, err := os.Open( inpBedGraphFilename )
  if err != nil { panic(err) }
  defer bgFp.Close()

  fastjFp, err := os.Create(outFastjFilename)
  if err != nil { panic(err) }
  defer func() { if err := fastjFp.Close(); err != nil { panic(err) } }()
  writerFastj := bufio.NewWriter(fastjFp)


  nextSeqPos := seqStart + fjInfo.minTileDistance
  tilePos := 0

  tagStart := seqStart
  preTag := "........................"
  tag := "XXXX"


  writerFastj.WriteString("{\n")

  scanner := bufio.NewScanner( bgFp )
  for scanner.Scan() {
    l := scanner.Text()
    if m,_ := regexp.MatchString( `^#`  , l ); m { continue }
    if m,_ := regexp.MatchString(`^\s*$`, l ); m { continue }

    fields := strings.SplitN( l, "\t", -1 )
    s,_ := strconv.Atoi(fields[1])
    e,_ := strconv.Atoi(fields[2])
    v,_ := strconv.ParseFloat(fields[3], 64)

    _ = e

    if v != 1 { continue }
    if e < nextSeqPos { continue }

    prevTagStart := tagStart

    tagStart = s+1
    if s < nextSeqPos { tagStart = nextSeqPos + 1 }

    if tilePos > 0 {
      preTag = tag
    }

    tag = strings.ToUpper( string(chrFa[tagStart:tagStart+24]) )

    tileID := fmt.Sprintf("%03x%02x%03x%03x", fjInfo.band, fjInfo.revision, tilePos, 0 )
    
    //r := []byte(fmt.Sprintf("%d %d %s\n", tagStart, tagStart+24, tag ))
    //writerFastj.Write( r )

    if tilePos > 0 { writerFastj.WriteString(",\n") }

    str := fmt.Sprintf("  \"%s\": {\n    \"tileID\":\"%s\",\n", tileID, tileID)
    writerFastj.WriteString( str )

    str = fmt.Sprintf("    \"locus\" : [{ \"build\" : \"dummy\", \"pos\":\"dummy\" }],\n")
    writerFastj.WriteString( str )

    str = fmt.Sprintf("    \"copy\":\"1\",\n")
    writerFastj.WriteString( str )

    str = fmt.Sprintf("    \"tile\":\"%s", preTag )
    writerFastj.WriteString( str )

    midTile := strings.ToLower( string(chrFa[prevTagStart:tagStart]) )
    writerFastj.WriteString( midTile )

    str = fmt.Sprintf("%s\"\n  }", tag )
    writerFastj.WriteString( str )


    nextSeqPos = tagStart + MIN_TILE_DIST + 24
    tilePos ++

  }

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
  fastjInfo := FastjInfo{ band: 0, revision: 0, class: 0, minTileDistance: 200 }
  curChrom := CHR[19]

  cytomapFilename  := "ucsc.cytomap.hg19.txt"
  bedGraphFilename := fmt.Sprintf("/scratch/abram/bedGraph/%s.bedGraph", curChrom )
  chrFastaFilename := fmt.Sprintf("/scratch/abram/chr.fa/%s.fa", curChrom )

  fmt.Println("# finding tag set for", curChrom, "using", bedGraphFilename, "and", cytomapFilename)

  // should probably be BAND_BOUNDS = aux.BuildBandBounds( cytomapFilename ) ?
  //
  BAND_BOUNDS = make( map[string]map[int][2]int  )
  aux.BuildBandBounds( BAND_BOUNDS, cytomapFilename )

  nBands := len(BAND_BOUNDS[ curChrom ])
  fmt.Println( "#", curChrom, nBands )

  fmt.Println("# loading", chrFastaFilename, "into memory...")
  chrFa := aux.FaToByteArray( chrFastaFilename )

  baseAbsoluteBand := CalculateAbsoluteBand( BAND_BOUNDS, curChrom, CHR )

  for band := 0; band < nBands ; band++ {

    fastjInfo.band = baseAbsoluteBand + band


    bgFn := fmt.Sprintf( "/scratch/abram/bedGraph/%s_band%d_s%d_e%d.bedGraph",
                        curChrom, 
                        band,
                        BAND_BOUNDS[curChrom][band][0],
                        BAND_BOUNDS[curChrom][band][1] )

    fastjFn := fmt.Sprintf( "/scratch/abram/fastj/%s_band%d_s%d_e%d.fj",
                            curChrom,
                            band,
                            BAND_BOUNDS[curChrom][band][0],
                            BAND_BOUNDS[curChrom][band][1] )


    fmt.Println( curChrom, "band:", band, fmt.Sprintf("(%d)", fastjInfo.band), "-->", fastjFn )

    WriteFastjFromBedGraph( chrFa, bgFn, fastjFn, BAND_BOUNDS[curChrom][band][0], fastjInfo )

  }

  fmt.Println("done")
  os.Exit(0)


  bgFp, err := os.Open( bedGraphFilename )
  if err != nil { panic(err) }
  defer bgFp.Close()

  curBand := 0
  _ = curBand

  line_count:=0

  fmt.Println("# length of chromosome (that we have):", len(chrFa) )

  nextSeqPos := BAND_BOUNDS[curChrom][0][0] + MIN_TILE_DIST

  scanner := bufio.NewScanner( bgFp )
  for scanner.Scan() {
    l := scanner.Text()
    if m,_ := regexp.MatchString( `^#`  , l ); m { continue }
    if m,_ := regexp.MatchString(`^\s*$`, l ); m { continue }

    fields := strings.SplitN( l, "\t", -1 )
    s,_ := strconv.Atoi(fields[1])
    e,_ := strconv.Atoi(fields[2])
    v,_ := strconv.ParseFloat(fields[3], 64)

    _ = e

    line_count++

    //if (line_count%10000) == 0 { fmt.Println("#", line_count) }

    if v != 1 { continue }
    if e < nextSeqPos { continue }

    tagStart := s+1
    if s < nextSeqPos { tagStart = nextSeqPos + 1 }

    tag := strings.ToUpper( string(chrFa[tagStart:tagStart+24]) )
    
    r := []byte(fmt.Sprintf("%d %d %s\n", tagStart, tagStart+24, tag ))
    os.Stdout.Write( r )

    nextSeqPos = tagStart + MIN_TILE_DIST + 24

    //if line_count > 1000000 { os.Exit(0) }

  }


}
