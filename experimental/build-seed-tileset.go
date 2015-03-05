/*

  Create a seed FastJ file from a FASTA reference and BedGraph file.

  Example usage:

    build-seed-tileset --input seq.fa --bedgraph inp.bedgraph -start 0 -end 2300000 --path 0 --build 'hg19 chr1' --output 000.fj

  'input' is assumed to start at the start position specifieed.
  'bedgraph' is used to determine the start of the 24mer tag chosen.
  'start' is the start of the path.
  'end' is the end of the path.
  'path' is the path name for this tile set.
  'build' is the annotaiton to put in the 'locus' portion of the FastJ header

*/

package main

import "fmt"
import "os"
import "bufio"
import "strconv"
import "strings"
import "regexp"

import "crypto/md5"

import "runtime"
import "runtime/pprof"

import "./aux"

import "github.com/abeconnelly/autoio"
import "github.com/codegangsta/cli"

var VERSION_STR string = "0.1.0"

var gProfileFlag bool
var gProfileFile string = "build-seed-tileset.pprof"

var gMemProfileFlag bool
var gMemProfileFile string = "build-seed-tilset.mprof"

var g_profileFlag bool
var g_refGenome string
var g_fastaFn string
var g_pathNum int
var g_bedGraphFn string
var g_outFastjFn string

var g_start int
var g_end int

var gVerboseFlag bool


var PID = os.Getpid()
var MIN_TILE_DIST = 200

type FastjInfo struct {
  path, revision, class int
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
                        fa_seq []byte,
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

  tileseq = append( tileseq, strings.ToLower( string( fa_seq[ tileStart - g_start : tileEnd - g_start ] ) )... )

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


  offsetBeg, offsetEnd := tagLength, tagLength
  if leftEndStopFlag { offsetBeg = 0; }
  if rightEndStopFlag { offsetEnd = 0; }

  _ = offsetBeg

  str = fmt.Sprintf( "\"locus\":[{ \"build\" : \"%s ", buildInfo )
  writerFastj.WriteString( str )


  str = fmt.Sprintf( "%d ", tileStart )
  writerFastj.WriteString( str )

  str = fmt.Sprintf( "%d", tileEnd )
  writerFastj.WriteString( str )

  str = fmt.Sprintf( "\"}], " )
  writerFastj.WriteString( str )


  str = fmt.Sprintf("\"n\":%d, ", tileEnd - tileStart )
  writerFastj.WriteString( str )


  //----
  nocallCount:=0
  for i:=tileStart-g_start; i<(tileEnd-g_start); i++ {
    if fa_seq[i]=='n' || fa_seq[i]=='N' { nocallCount++; }
  }
  writerFastj.WriteString( fmt.Sprintf("\"nocallCount\":%d,", nocallCount) )

  tf := "false"
  if leftEndStopFlag { tf = "true" }
  writerFastj.WriteString( fmt.Sprintf("\"startTile\":%s,", tf) )
  tf = "false"
  if rightEndStopFlag { tf = "true" }
  writerFastj.WriteString( fmt.Sprintf("\"endTile\":%s,", tf) )

  writerFastj.WriteString( "\"startSeq\":\"" + string( fa_seq[ tileStart - g_start : tileStart + tagLength - g_start ] ) + "\"," )
  writerFastj.WriteString( "\"endSeq\":\"" + string( fa_seq[ tileEnd - offsetEnd - g_start : tileEnd - g_start ] ) + "\"," )
  writerFastj.WriteString( "\"seedTileLength\":1," )
  //----

  str = fmt.Sprintf( "\"startTag\":\"" )
  writerFastj.WriteString( str )

  if leftEndStopFlag {
    //for i:=0; i<tagLength; i++ { writerFastj.WriteString( "." ) }
  } else {
    writerFastj.WriteString( string( fa_seq[ tileStart - g_start : tileStart + tagLength - g_start ] ) )
  }

  str = fmt.Sprintf("\", ");
  writerFastj.WriteString( str )

  str = fmt.Sprintf("\"endTag\":\"" )
  writerFastj.WriteString( str )

  if rightEndStopFlag {
    //for i:=0; i<tagLength; i++ { writerFastj.WriteString( "." ) }
  } else {
    writerFastj.WriteString( string( fa_seq[ tileEnd - offsetEnd - g_start : tileEnd - g_start ] ) )
  }

  str = fmt.Sprintf("\", ");
  writerFastj.WriteString( str )

  //---
  writerFastj.WriteString( "\"notes\":[]" )
  //---


  //str = fmt.Sprintf("\"");
  //writerFastj.WriteString( str )

  str = fmt.Sprintf("}\n" )
  writerFastj.WriteString( str )

  //---

  bpCount := 0
  for bpCount<tagLength {
    if (bpCount>0) && ((bpCount%bodyLineWidth) == 0) { writerFastj.WriteString( "\n" ) }
    writerFastj.WriteByte( lc( fa_seq[ tileStart + bpCount - g_start ] ) )
    bpCount++
  }

  for (tileStart+bpCount) < (tileEnd - tagLength) {
    if (bpCount>0) && ((bpCount%bodyLineWidth) == 0) { writerFastj.WriteString( "\n" ) }
    writerFastj.WriteByte( lc( fa_seq[ tileStart + bpCount - g_start ] ) )
    bpCount++
  }

  for (tileStart+bpCount) < tileEnd {
    if (bpCount>0) && ((bpCount%bodyLineWidth) == 0) { writerFastj.WriteString( "\n" ) }
    writerFastj.WriteByte( lc( fa_seq[ tileStart + bpCount - g_start ] ) )
    bpCount++
  }

  writerFastj.WriteString("\n")

}

// fa_seq holds an ascii block of the chromosome as it appears in the fasta file,
//   with header and newlines stripped out
// inpBedGraphFilename will open a the bedgraph file and scan it one line at a time
// outFastjFilename will write the JSON fastj tileset
// seqStart and seqEnd are the beginning and end of the 'path' (or 'sub-path') of the block
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
//   and making sure the bedGraph entries are indexed properly against the fa_seq fasta byte array.
//
func WriteFastjFromBedGraph( fa_seq []byte, inpBedGraphFilename string, outFastjFilename string,
                             seqStart int, seqEnd int,
                             fjInfo FastjInfo ) {

  benvReader,err := autoio.OpenScanner( inpBedGraphFilename )
  if err != nil { panic( fmt.Sprintf( "%s: %s", inpBedGraphFilename ,  err) ) }
  defer benvReader.Close()

  benvWriter,err := autoio.CreateWriter( outFastjFilename )
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

    tileID := fmt.Sprintf("%03x.%02x.%03x.%03x", fjInfo.path, fjInfo.revision, tilePos, 0 )

    prevTagStart = nextTagStart
    nextTagStart = s+1
    if s < minEndSeqPos{ nextTagStart = minEndSeqPos + 1 }

    if (seqEnd - nextTagStart) <= fjInfo.minTileDistance {
      mergeLastFlag = true
      break
    }

    printFastjElement( benvWriter.Writer, fa_seq, tileID,
                       prevTagStart, nextTagStart + 24, 24,
                       ( tilePos == 0 ), false, fjInfo.bodyLineWidth,
                       fjInfo.build)

    minEndSeqPos = nextTagStart + fjInfo.minTileDistance + 24
    tilePos ++

  }

  if !mergeLastFlag {
    prevTagStart = nextTagStart
  }

  tileID := fmt.Sprintf("%03x.%02x.%03x.%03x", fjInfo.path, fjInfo.revision, tilePos, 0 )

  printFastjElement( benvWriter.Writer, fa_seq, tileID,
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

func _main( c *cli.Context ) {

  g_bedGraphFn    = c.String("bedgraph")
  g_outFastjFn    = c.String("output")
  g_pathNum       = c.Int("path")
  g_start         = c.Int("start")
  g_end           = c.Int("end")
  g_fastaFn       = c.String("input")

  if c.String("input") == "" {
    fmt.Fprintf( os.Stderr, "Input required, exiting\n" )
    cli.ShowAppHelp( c )
    os.Exit(1)
  }

  ain,err := autoio.OpenReadScanner( c.String("input") ) ; _ = ain
  if err!=nil {
    fmt.Fprintf(os.Stderr, "%v\n", err)
    cli.ShowAppHelp( c )
    os.Exit(1)
  }
  defer ain.Close()


  aout,err := autoio.CreateWriter( c.String("output") ) ; _ = aout
  if err!=nil {
    fmt.Fprintf(os.Stderr, "%v\n", err)
    cli.ShowAppHelp( c )
    os.Exit(1)
  }
  defer func() { aout.Flush() ; aout.Close() }()

  if c.Bool( "pprof" ) {
    gProfileFlag = true
    gProfileFile = c.String("pprof-file")
  }

  if c.Bool( "mprof" ) {
    gMemProfileFlag = true
    gMemProfileFile = c.String("mprof-file")
  }

  gVerboseFlag = c.Bool("Verbose")

  if c.Int("max-procs") > 0 {
    runtime.GOMAXPROCS( c.Int("max-procs") )
  }

  if gProfileFlag {
    prof_f,err := os.Create( gProfileFile )
    if err != nil {
      fmt.Fprintf( os.Stderr, "Could not open profile file %s: %v\n", gProfileFile, err )
      cli.ShowAppHelp( c )
      os.Exit(2)
    }

    pprof.StartCPUProfile( prof_f )
    defer pprof.StopCPUProfile()
  }


  if (len(g_bedGraphFn)==0) || (len(g_outFastjFn)==0) {
    fmt.Fprintf( os.Stderr, "Provide input bedGraph file and output Fastj file\n" )
    cli.ShowAppHelp( c )
    os.Exit(2)
  }

  if (g_pathNum < 0) {
    fmt.Fprintf( os.Stderr, "Band must be non negative\n")
    cli.ShowAppHelp( c )
    os.Exit(2)
  }

  if (gVerboseFlag) {
    fmt.Printf("#buildTileSet\n")
    fmt.Printf("# referenceGenome: %s\n", g_refGenome )
    fmt.Printf("# Fasta file: %s\n", g_fastaFn )
  }


  fastjInfo := FastjInfo{ path: g_pathNum, revision: 0, class: 0, minTileDistance: 200, bodyLineWidth:50, build: "" }

  fastjInfo.build = c.String("build")

  if gVerboseFlag {
    fmt.Println("# finding tag set for path", g_pathNum, ", using", g_bedGraphFn )
  }

  if gVerboseFlag {
    fmt.Println("# loading", g_fastaFn, "into memory...")
  }

  fa_seq,e := aux.FaToByteArray( g_fastaFn )
  if e != nil { panic( fmt.Sprintf("%s: %s", fa_seq, e ) ) }

  aux.ToLowerInPlace(fa_seq)

  fastjInfo.path = g_pathNum

  if gVerboseFlag {
    fmt.Println( "# path:", g_pathNum, fmt.Sprintf("(%d)", fastjInfo.path), "-->", g_outFastjFn )
    fmt.Printf( "# path bounds %v %v\n", g_start, g_end )
  }

  WriteFastjFromBedGraph( fa_seq, g_bedGraphFn,
                          g_outFastjFn,
                          g_start, g_end,
                          fastjInfo )

  if gVerboseFlag {
    fmt.Printf("# done\n")
  }



}

func main() {

  app := cli.NewApp()
  app.Name  = "build-seed-tileset"
  app.Usage = "Construct FastJ files to seed a FastJ library"
  app.Version = VERSION_STR
  app.Author = "Curoverse Inc."
  app.Email = "info@curoverse.com"
  app.Action = func( c *cli.Context ) { _main(c) }

  app.Flags = []cli.Flag{
    cli.StringFlag{
      Name: "input, i",
      Usage: "INPUT-FASTA",
    },

    cli.StringFlag{
      Name: "build, B",
      Usage: "BUILD",
    },

    cli.IntFlag{
      Name: "path, p",
      Usage: "PATH",
    },

    cli.IntFlag{
      Name: "start, s",
      Usage: "START",
    },

    cli.IntFlag{
      Name: "end, e",
      Usage: "END",
    },

    cli.StringFlag{
      Name: "bedgraph, g",
      Usage: "BEDGRAPH",
    },

    cli.StringFlag{
      Name: "output, o",
      Value: "-",
      Usage: "OUTPUT-FASTJ",
    },

    cli.IntFlag{
      Name: "max-procs, N",
      Value: -1,
      Usage: "MAXPROCS",
    },

    cli.BoolFlag{
      Name: "Verbose, V",
      Usage: "Verbose flag",
    },

    cli.BoolFlag{
      Name: "pprof",
      Usage: "Profile usage",
    },

    cli.StringFlag{
      Name: "pprof-file",
      Value: gProfileFile,
      Usage: "Profile File",
    },

    cli.BoolFlag{
      Name: "mprof",
      Usage: "Profile memory usage",
    },

    cli.StringFlag{
      Name: "mprof-file",
      Value: gMemProfileFile,
      Usage: "Profile Memory File",
    },

  }

  app.Run( os.Args )

  if gMemProfileFlag {
    fmem,err := os.Create( gMemProfileFile )
    if err!=nil { panic(fmem) }
    pprof.WriteHeapProfile(fmem)
    fmem.Close()
  }

}
