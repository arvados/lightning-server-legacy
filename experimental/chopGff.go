/*
    Chop gff file into bands as stored in 'ucsc.cytomap.hg19.txt'.
    Put into output directory as specified on the command line.
    Output files are gziped.
*/

package main

import "fmt"
import "os"
import "strings"
import "strconv"
import "flag"

import "compress/gzip"

import "./recache"
import "./aux"
import "./bioenv"

var gDebugFlag bool

var g_cytoBand *string
var g_gffFileName *string
var g_outBaseDir *string
var g_verboseFlag *bool

var benv bioenv.BioEnvContext

func init() {
  var err error

  benv,err = bioenv.BioEnv()
  if err != nil { panic(fmt.Sprintf("bioenv: %s", err)) }

  g_verboseFlag = flag.Bool( "v", false, "Verbose")
  flag.BoolVar( g_verboseFlag, "verbose", false, "Verbose")

  g_gffFileName = flag.String( "i", "", "Input GFF file")
  flag.StringVar( g_gffFileName, "input-gff", "", "Input GFF file")

  g_outBaseDir = flag.String( "D", "", "Output directory")
  flag.StringVar( g_outBaseDir, "output-directory", "", "Output directory")

  g_cytoBand = flag.String( "cytoBand", benv.Env["cytoBand"], "cytoband file")

  flag.Parse()
  benv.ProcessFlag()

  if len(*g_gffFileName)==0 {
    fmt.Fprintf( os.Stderr, "Provide input gff file" )
    flag.PrintDefaults()
    os.Exit(2)
  }

  if len(*g_outBaseDir)==0 {
    fmt.Fprintf( os.Stderr, "Provide output directory" )
    flag.PrintDefaults()
    os.Exit(2)
  }

}

func main() {

  BAND_BOUNDS := make( map[string]map[int][2]int  )

  aux.BuildBandBounds( BAND_BOUNDS, *g_cytoBand )

  lineCount := 0
  prevChrom := "-"
  curBand := 0

  var curFp  *os.File
  var writer *gzip.Writer

  gffHandle,err := bioenv.OpenScanner( *g_gffFileName )
  if err != nil { panic(err) }
  defer gffHandle.Close()

  for gffHandle.Scanner.Scan() {
    l := gffHandle.Scanner.Text()
    lineCount++

    if b,_ := recache.MatchString( `^#`, l )  ;b { continue }
    if b,_ := recache.MatchString(`^\s*$`, l) ;b { continue }

    field := strings.SplitN( l, "\t", -1)

    curChrom := field[0]
    sType := field[2]
    s,_ := strconv.Atoi( field[3] )
    e,_ := strconv.Atoi( field[4] )

    _ = sType
    _ = s
    _ = e

    if prevChrom != curChrom {
      var err error

      prevChrom = curChrom
      curBand = 0

      if writer != nil { writer.Flush() ; writer.Close() }
      if curFp != nil { curFp.Close() }

      startBand := BAND_BOUNDS[curChrom][curBand][0]
      endBand   := BAND_BOUNDS[curChrom][curBand][1]

      fn := fmt.Sprintf( "%s/%s_band%d_s%d_e%d.gff.gz", *g_outBaseDir, curChrom, curBand, startBand, endBand )

      curFp,err = os.Create( fn )
      if err != nil { panic(err) }

      writer = gzip.NewWriter( curFp )

    } else if e > BAND_BOUNDS[curChrom][curBand][1] {
      var err error

      // Just write out the current line as the last line of the previous band.
      //
      writer.Write( []byte(l) )
      writer.Write( []byte("\n") )


      curBand ++

      if writer != nil { writer.Flush() ; writer.Close() }
      if curFp != nil { curFp.Close() }

      if curBand > len(BAND_BOUNDS[curChrom]) {
        if gDebugFlag { fmt.Println("SANITY: curChrom", curChrom, "has", len(BAND_BOUNDS[curChrom]), "but we've gone past! (s:", s, ")" ) }
        os.Exit(1)
      }

      startBand := BAND_BOUNDS[curChrom][curBand][0]
      endBand   := BAND_BOUNDS[curChrom][curBand][1]

      fn := fmt.Sprintf( "%s/%s_band%d_s%d_e%d.gff.gz", *g_outBaseDir, curChrom, curBand, startBand, endBand)
      curFp,err = os.Create( fn )
      if err != nil { panic(err) }

      writer = gzip.NewWriter( curFp )

    }

    writer.Write( []byte(l) )
    writer.Write( []byte("\n") )
    writer.Flush()

  }

  if writer != nil { writer.Flush() ; writer.Close() }

  if gDebugFlag { fmt.Println("done...") }

}
