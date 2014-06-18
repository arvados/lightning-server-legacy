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

import "compress/gzip"

import "./recache"
import "./aux"

var gDebugFlag bool

func main() {
  gDebugFlag = true

  //CYTOMAP_FILENAME := "custom_hg18_cytomap.txt"
  //CYTOMAP_FILENAME := "ucsc.cytomap.hg18.txt"
  CYTOMAP_FILENAME := "custom_hg18_cytomap.txt"

  BAND_BOUNDS := make( map[string]map[int][2]int  )

  if len(os.Args) != 3 {
    fmt.Println("usage:")
    fmt.Println("./chopGff.go <gffFileName> <outputBaseDir>")
    os.Exit(0)
  }

  gffFn         := os.Args[1]
  outputBaseDir := os.Args[2]

  aux.BuildBandBounds( BAND_BOUNDS, CYTOMAP_FILENAME)

  lineCount := 0
  prevChrom := "-"
  curBand := 0

  var curFp  *os.File
  var writer *gzip.Writer

  gffFp,scanner,err := aux.OpenScanner( gffFn )
  if err != nil { panic(err) }
  defer gffFp.Close()

  OOBFlag := false

  for scanner.Scan() {
    l := scanner.Text()
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

    // Skip to the end of this chromosome if we are past the
    // last band boundary (for the current chromosome).
    //
    if OOBFlag && (prevChrom == curChrom) { continue }
    OOBFlag = false

    if prevChrom != curChrom {
      var err error

      prevChrom = curChrom
      curBand = 0

      if writer != nil { writer.Flush() ; writer.Close() }
      if curFp != nil { curFp.Close() }

      startBand := BAND_BOUNDS[curChrom][curBand][0]
      endBand   := BAND_BOUNDS[curChrom][curBand][1]

      fn := fmt.Sprintf( "%s/%s_band%d_s%d_e%d.gff.gz", outputBaseDir, curChrom, curBand, startBand, endBand )

      curFp,err = os.Create( fn )
      if err != nil { panic(err) }

      writer = gzip.NewWriter( curFp )

    } else if e > BAND_BOUNDS[curChrom][curBand][1] {
      var err error

      if s < BAND_BOUNDS[curChrom][curBand][1] {
        writer.Write( []byte(l) )
        writer.Write( []byte("\n") )

        if gDebugFlag { fmt.Println("WARNING: curChrom", curChrom,  "curBand", curBand, "s", s, "<", BAND_BOUNDS[curChrom][curBand][1], "< e", e ) }
      }

      curBand ++

      if writer != nil { writer.Flush() ; writer.Close() }
      if curFp != nil { curFp.Close() }

      if curBand > len(BAND_BOUNDS[curChrom]) {
        if gDebugFlag { fmt.Println("SANITY: curChrom", curChrom, "has", len(BAND_BOUNDS[curChrom]), "but we've gone past! (s:", s, ")" ) }

        //os.Exit(1)
        OOBFlag = true
        continue
      }

      startBand := BAND_BOUNDS[curChrom][curBand][0]
      endBand   := BAND_BOUNDS[curChrom][curBand][1]

      fn := fmt.Sprintf( "%s/%s_band%d_s%d_e%d.gff.gz", outputBaseDir, curChrom, curBand, startBand, endBand)
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
