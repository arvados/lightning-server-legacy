/*

example usage:

 time ./gffstats data/tile_hg19.sorted.list data/hu44DCFF.gff results/hu44DCFF.stats > results/hu44DCFF.report 

*/
package main

import "fmt"
import "io/ioutil"
import "os"
import "strings"
import "strconv"
import "bufio"

/*
func abs(x int) int {
  if x < 0 return -x
  return x
}
*/

type tilebound struct {
  tileId, chrom string
  s,e int
}

type tilestat struct {
  n int

  n_gap int
  n_ltag_gap, n_rtag_gap int

  n_indel, n_snp, n_sub int
  n_ltag_indel, n_ltag_snp, n_ltag_sub int
  n_rtag_indel, n_rtag_snp, n_rtag_sub int
}


var tagLen int = 24
var TILEPOS map[string][]tilebound
var TILESTAT map[string]tilestat


func updateTileStatCount( chrom string, tileInd int, varType string ) {

  if tileInd >= len(TILEPOS[chrom]) { return }

  v := TILESTAT[ TILEPOS[chrom][tileInd].tileId ]
  switch varType {
  case "SNP": v.n_snp++
  case "SUB": v.n_sub++
  case "INDEL": v.n_indel++
  default: panic( fmt.Sprintf("BAD VARTYPE %s", varType) )
  }
  TILESTAT[ TILEPOS[chrom][tileInd].tileId ] = v

}

func updateTileStatLeftCount( chrom string, tileInd int, varType string ) {

  if tileInd >= len(TILEPOS[chrom]) { return }

  v := TILESTAT[ TILEPOS[chrom][tileInd].tileId ]
  switch varType {
  case "SNP": v.n_ltag_snp++
  case "SUB": v.n_ltag_sub++
  case "INDEL": v.n_ltag_indel++
  default: panic( fmt.Sprintf("BAD VARTYPE %s", varType) )
  }
  TILESTAT[ TILEPOS[chrom][tileInd].tileId ] = v

}

func  updateTileStatRightCount( chrom string, tileInd int, varType string ) {

  if tileInd >= len(TILEPOS[chrom]) { return }

  v := TILESTAT[ TILEPOS[chrom][tileInd].tileId ]
  switch varType {
  case "SNP": v.n_rtag_snp++
  case "SUB": v.n_rtag_sub++
  case "INDEL": v.n_rtag_indel++
  default: panic( fmt.Sprintf("BAD VARTYPE %s", varType) )
  }
  TILESTAT[ TILEPOS[chrom][tileInd].tileId ] = v

}

func emit( chrom string, tileInd int, varModifier string, varType string, s, e int, field string ) {

  if tileInd >= len(TILEPOS[chrom]) { return }

  fmt.Printf("%s %s %d %d %s%s %d %d \"%s\"\n",
    TILEPOS[chrom][tileInd].tileId,
    chrom, TILEPOS[chrom][tileInd].s, TILEPOS[chrom][tileInd].e,
    varModifier, varType,
    s, e, field )
  /*
  fmt.Printf("{%s [%s][%d] %d %d} %s%s %d %d %s\n",
    TILEPOS[chrom][tileInd].tileId,
    chrom, tileInd, TILEPOS[chrom][tileInd].s, TILEPOS[chrom][tileInd].e,
    varModifier, varType,
    s, e, field )
    */

}

func debug_func( chrom string ) {
  fmt.Printf("len(TILEPOS[%s]) = %d\n", chrom, len(TILEPOS[chrom]))
}

/*

func validate_hg19pos_bytes(hg19dat []byte) {
  //DEBUG
  line_count := 0
  n:=len(hg19dat)
  for i:=0; i<n; i++ {
    if hg19dat[i] == '\n' { line_count++ ; continue }

    if (  ( hg19dat[i] == 'c' ) ||
          ( hg19dat[i] == 'h' ) ||
          ( hg19dat[i] == 'r' ) ||
          ( hg19dat[i] == 'X' ) ||
          ( hg19dat[i] == 'Y' ) ||
          ( hg19dat[i] == 'M' ) ||
          ( hg19dat[i] == ' ' ) ||
          ( hg19dat[i] == '0' ) ||
          ( hg19dat[i] == '1' ) ||
          ( hg19dat[i] == '2' ) ||
          ( hg19dat[i] == '3' ) ||
          ( hg19dat[i] == '4' ) ||
          ( hg19dat[i] == '5' ) ||
          ( hg19dat[i] == '6' ) ||
          ( hg19dat[i] == '7' ) ||
          ( hg19dat[i] == '8' ) ||
          ( hg19dat[i] == '9' ) ) {
      continue
    }

    fmt.Println( i, hg19dat[i] , line_count)
    os.Exit(0)
  }
}

*/

func isTileBoundSorted( tbs []tilebound ) bool {
  n:=len(tbs)
  for i:=1; i<n; i++ {
    if tbs[i].s < tbs[i-1].s { return false }
  }
  return true
}

func main() {

  TILEPOS = map[string][]tilebound{}
  TILESTAT = map[string]tilestat{}

  if (len(os.Args) < 3) || (len(os.Args) > 4) {
    fmt.Printf("usage:\n  ./gffstats <hg19posfile> <gffFile> [<statFile>]\n")
    os.Exit(0)
  }

  hg19posfile := os.Args[1]
  gffFn := os.Args[2]

  fmt.Println( hg19posfile, gffFn )

  statFile := ""
  if len(os.Args) == 4 { statFile = os.Args[3] }


  hg19dat,e0 := ioutil.ReadFile( hg19posfile )
  if e0 != nil { panic(e0) }

  gffdat,e1  := ioutil.ReadFile( gffFn )
  if e1 != nil { panic(e1) }

  _ = hg19dat
  _ = gffdat

  hg19Lines := strings.SplitN( string(hg19dat), "\n", -1 )

  for i:=0; i<len(hg19Lines); i++ {
    f := strings.SplitN( hg19Lines[i], ",", -1 )
    if len(f) < 2 { continue }
    g := strings.SplitN( f[1], " ", -1 )

    tileId := f[0]
    chrom := g[1]
    x,_ := strconv.Atoi(g[2])
    y,_ := strconv.Atoi(g[3])

    TILEPOS[chrom] = append( TILEPOS[chrom], tilebound{ tileId, chrom, x, y } )

  }

  // check to make sure TILEPOS chromosomes are sorted
  for k,_ := range TILEPOS {
    if !isTileBoundSorted( TILEPOS[k] ) {
      panic( fmt.Sprintf("TILEPOS[\"%s\"] not sorted! exiting", k ) )
    }
  }

  gffLines := strings.SplitN( string(gffdat), "\n", -1 )

  prevGffChrom    := ""
  tileInd         := 0
  expected_start  := 0

  //DEBUG
  debug_count := 0

  for i:=0; i<len(gffLines); i++ {
    if len(gffLines[i]) == 0 { continue }
    if gffLines[i][0] == '#' { continue }

    fields := strings.SplitN( gffLines[i], "\t", -1 )
    chrom := fields[0]
    varType := fields[2]
    s,_ := strconv.Atoi(fields[3])
    e,_ := strconv.Atoi(fields[4])

    _ = s
    _ = e

    s--
    e--

    if prevGffChrom != chrom {
      tileInd = 0
      prevGffChrom = chrom
      expected_start = s
    }

    n := len(TILEPOS[chrom])
    for  ; (tileInd < (n-1)) && (TILEPOS[chrom][tileInd+1].s < s) ; tileInd++ { }

    if expected_start != s {

      emit( chrom, tileInd, "", "gap", s, e, "-" )

      if tileInd >= len( TILEPOS[chrom] ) {
        panic( fmt.Sprintf("tileInd %d >= len(TILEPOS[%s]) (%d) (debug_count %d)", tileInd, chrom, len(TILEPOS[chrom]), debug_count) )
      }

      //updateTileStatGapCount( chrom, tileInd )
      v := TILESTAT[ TILEPOS[chrom][tileInd].tileId ]
      v.n_gap++
      TILESTAT[ TILEPOS[chrom][tileInd].tileId ] = v

      if (s-TILEPOS[chrom][tileInd].s) < tagLen {
        //updateTileStatGapLeftCount( chrom, tileInd )

        v := TILESTAT[ TILEPOS[chrom][tileInd].tileId ]
        v.n_ltag_gap++
        TILESTAT[ TILEPOS[chrom][tileInd].tileId ] = v
      }

      //if (TILEPOS[chrom][tileInd].tile

    }

    // If we have a variant (SUB, INDEL, SNP), emit/process the
    // relevant information.
    //
    if varType != "REF" {

      // Emit the varType and update simple stat counts
      //
      emit( chrom, tileInd, "", varType, s, e, fields[8] )
      updateTileStatCount( chrom, tileInd, varType )

      // The beginning of variant falls on a tag
      //
      if (s-TILEPOS[chrom][tileInd].s) < tagLen {
        emit( chrom, tileInd, "ltag", varType, s, e, fields[8] )
        updateTileStatLeftCount( chrom, tileInd, varType )
      }

      // The beginning of a variant falls within the next tile
      //
      if (TILEPOS[chrom][tileInd].e - s) < tagLen {
        emit( chrom, tileInd+1, "+", varType, s, e, fields[8] )
        updateTileStatCount( chrom, tileInd+1, varType )

        // And it also falls within the tag of the next tile
        //
        if (TILEPOS[chrom][tileInd].e - s) < 0 {
          emit( chrom, tileInd+1, "ltag+", varType, s, e, fields[8] )
          updateTileStatLeftCount( chrom, tileInd+1, varType )
        }

      } else if ( (varType == "INDEL") || (varType == "SUB") ) && ( (TILEPOS[chrom][tileInd].e - e) < tagLen )  {

        // We assume the biggest deletion is less then the minimum tile length we have.
        //

        // The right end of the deletion hits the right tag and the tile
        //
        emit( chrom, tileInd+1, "-", varType, s, e, fields[8] )
        updateTileStatCount( chrom, tileInd+1, varType )

        emit( chrom, tileInd+1, "ltag-", varType, s, e, fields[8] )
        updateTileStatLeftCount( chrom, tileInd+1, varType )

      }

    }

    expected_start = e+1

    //DEBUG
    //if debug_count > 100000 { break }
    debug_count ++


  }

  fmt.Printf("# done\n")

  if len(statFile)>0 {
    fp,err := os.Create( statFile )
    if err != nil { panic(err) }
    defer fp.Close()

    statWriter := bufio.NewWriter(fp)
    statWriter.WriteString( "#tileID,NSNP,NSUB,NINDEL,NGap,NltagSNP,NltagSUB,NltagINDEL\n" )
    for tileId,_ := range TILESTAT {
      statWriter.WriteString(
        fmt.Sprintf("%s,%d,%d,%d,%d,%d,%d,%d\n",
          tileId,
          TILESTAT[tileId].n_snp, TILESTAT[tileId].n_sub, TILESTAT[tileId].n_indel,
          TILESTAT[tileId].n_gap,
          TILESTAT[tileId].n_ltag_snp, TILESTAT[tileId].n_ltag_sub, TILESTAT[tileId].n_ltag_indel))

    }

    statWriter.Flush()

  }

}
