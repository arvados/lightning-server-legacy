/*
    Chop CGI Var file into bands as stored in 'ucsc.cytomap.hg19.txt'.
    Put into output directory as specified on the command line.
    Output files are gziped.
*/

package main

import "fmt"
import "os"

import "strings"
import "strconv"

import "compress/gzip"

import "./recache"
import "./aux"
import "./bioenv"

//import "runtime/pprof"

var gDebugFlag bool

var gFileCount int

var BAND_BOUNDS map[string]map[int][2]int
var CYTOMAP_FILENAME string

func main() {

  /*
  //PROFILING
  profFp, _ := os.Create("chopCGIVar.profile")
  pprof.StartCPUProfile(profFp)
  defer pprof.StopCPUProfile()
  //PROFILING
  */


  gDebugFlag = true

  benv,err := bioenv.BioEnv()
  if err != nil { panic(err) }

  CYTOMAP_FILENAME = benv["bandFile"]
  BAND_BOUNDS = make( map[string]map[int][2]int  )

  if len(os.Args) != 3 {
    fmt.Println("usage:")
    fmt.Println("./chopCGIVar.go <cgiVarFileName> <outputBaseDir>")
    os.Exit(0)
  }

  cgiVarFn        := os.Args[1]
  outputBaseDir   := os.Args[2]

  aux.BuildBandBounds( BAND_BOUNDS, CYTOMAP_FILENAME)

  lineCount := 0
  prevChrom := "-"
  curBand := 0

  var curFp  *os.File
  var writer *gzip.Writer

  cgiVarFp,scanner,err := aux.OpenScanner( cgiVarFn )
  if err != nil { panic(err) }
  defer cgiVarFp.Close()

  hAllelePos := 2
  hChrPos := 3
  hBegPos := 4
  hEndPos := 5
  hTypPos := 6

  _ = hAllelePos

  headerStr := ""

  for scanner.Scan() {
    l := scanner.Text()
    lineCount++

    // Remap header
    if b,_ := recache.MatchString(`^>`, l) ;b {
      hstr,_ := recache.ReplaceAllString( `^>`, l, "")
      hmap := make( map[string]int )
      harr := strings.SplitN( hstr, "\t", -1 )
      for i:=0; i<len(harr); i++ {
        hmap[ harr[i] ] = i
      }

      hAllelePos = hmap[ "allele" ]
      hChrPos = hmap[ "chromosome" ]
      hBegPos = hmap[ "begin" ]
      hEndPos = hmap[ "end" ]
      hTypPos = hmap[ "varType" ]

      headerStr = fmt.Sprintf("%s\n", l)

      continue
    }

    if b,_ := recache.MatchString( `^#`, l )  ;b { continue }
    if b,_ := recache.MatchString(`^\s*$`, l) ;b { continue }

    field := strings.SplitN( l, "\t", -1)

    curChrom := field[ hChrPos ]
    sType := field[ hTypPos ]
    s,_ := strconv.Atoi( field[ hBegPos ] )
    e,_ := strconv.Atoi( field[ hEndPos ] )

    if prevChrom != curChrom {
      var err error

      prevChrom = curChrom
      curBand = 0

      gFileCount++

      if writer != nil { writer.Flush() ; writer.Close() }
      if curFp != nil { curFp.Close() }

      startBand := BAND_BOUNDS[curChrom][curBand][0]
      endBand   := BAND_BOUNDS[curChrom][curBand][1]

      fn := fmt.Sprintf( "%s/%s_band%d_s%d_e%d.cgivar.gz", outputBaseDir, curChrom, curBand, startBand, endBand )

      curFp,err = os.Create( fn )
      if err != nil { panic(err) }

      writer = gzip.NewWriter( curFp )

      // Write header to each file
      //
      writer.Write( []byte(headerStr) )


    } else if e > BAND_BOUNDS[curChrom][curBand][1] {
      var err error

      // CGI Var files are 0-referenced, so we need to do an inclusive less than test
      //
      if s <= BAND_BOUNDS[curChrom][curBand][1] {
        writer.Write( []byte(l) )
        writer.Write( []byte("\n") )

        if sType == "1" {
          scanner.Scan()
          l2 := scanner.Text()
          writer.Write( []byte(l2) )
          writer.Write( []byte("\n") )
        }

        if gDebugFlag { fmt.Println("WARNING: curChrom", curChrom,  "curBand", curBand, "s", s, "<", BAND_BOUNDS[curChrom][curBand][1], "< e", e ) }
      }

      curBand ++

      if writer != nil { writer.Flush() ; writer.Close() }
      if curFp != nil { curFp.Close() }

      if curBand > len(BAND_BOUNDS[curChrom]) {
        if gDebugFlag { fmt.Println("SANITY: curChrom", curChrom, "has", len(BAND_BOUNDS[curChrom]), "but we've gone past! (s:", s, ")" ) }
        os.Exit(1)
      }

      startBand := BAND_BOUNDS[curChrom][curBand][0]
      endBand   := BAND_BOUNDS[curChrom][curBand][1]

      fn := fmt.Sprintf( "%s/%s_band%d_s%d_e%d.cgivar.gz", outputBaseDir, curChrom, curBand, startBand, endBand)
      curFp,err = os.Create( fn )
      if err != nil { panic(err) }

      writer = gzip.NewWriter( curFp )

      gFileCount++

      // Write header to each file
      //
      writer.Write( []byte(headerStr) )



    }

    writer.Write( []byte(l) )
    writer.Write( []byte("\n") )
    if sType == "1" {
      scanner.Scan()
      l2 := scanner.Text()
      writer.Write( []byte(l2) )
      writer.Write( []byte("\n") )
    }
    //writer.Flush()

  }

  if writer != nil { writer.Flush() ; writer.Close() }

  if gDebugFlag { fmt.Println("done...") }

}
