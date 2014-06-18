/*
  Create an hg18 tile set from a list of "<tileId>","hg18 <chr> <posBeg> <posEnd>".
  Assume the input tile/hg18 positions list is sorted.
  Generate a fastj file per band.
*/

package main

import "fmt"

import "os"
import "strings"
import "strconv"

import _ "sort"
import _ "bufio"

import "encoding/json"

import "./aux"
import "./tile"
import "./recache"
import "./bioenv"


type ByTileId []string
func ( x ByTileId ) Len() int { return len(x) }
func ( x ByTileId ) Swap(i,j int) { x[i],x[j] = x[j],x[i] }
func ( x ByTileId ) Less(i,j int) bool {
  f := strings.SplitN( x[i], ".", -1 )
  g := strings.SplitN( x[j], ".", -1 )

  if len(f) != 4 {
    fmt.Println("!!!", f, len(f), x[i] )
    os.Exit(0)
  }

  if len(g) != 4 {
    fmt.Println("!!!", g, len(g), x[j] )
    os.Exit(0)
  }

  a,_ := strconv.ParseInt( f[0], 16, 0 )
  b,_ := strconv.ParseInt( g[0], 16, 0 )

  if a != b  { return a < b }

  a,_ = strconv.ParseInt( f[2], 16, 0 )
  b,_ = strconv.ParseInt( g[2], 16, 0 )

  if a != b { return a < b }

  a,_ = strconv.ParseInt( f[3], 16, 0 )
  b,_ = strconv.ParseInt( g[3], 16, 0 )

  return a < b
}


func main() {
  tagLen := 24

  if len(os.Args) != 3 {
    fmt.Println("usage:")
    fmt.Println("  ./createHG18TileSet <hg18TilePositionFile> <fastjOutputDir>")
    os.Exit(0)
  }

  odir := os.Args[2]

  benv,_ := bioenv.BioEnv()
  hg18dir := benv["dir:hg18.fa"]
  refGenome := "hg18"

  hg18_map := map[string]string{}

  fp,scanner,err := aux.OpenScanner( os.Args[1] )
  if err != nil { panic(err) }
  defer fp.Close()

  tileList := []string{}

  for scanner.Scan() {
    l := scanner.Text()

    if b,_ := recache.MatchString( `^\s*$`, l ) ; b { continue }
    if b,_ := recache.MatchString( `^\s*#`, l ) ; b { continue }

    fields := strings.SplitN( l, ",", -1 )

    hg18_map[ fields[0][1:len(fields[0])-1] ] = fields[1][1:len(fields[1])-1]

    tileList = append( tileList, fields[0][1:len(fields[0])-1] )

  }


  fmt.Print("# loaded hg18 positions...\n")


  /*
  sort.Sort( ByTileId( tileList ) )

  wfp,err := os.Create( "/scratch/abram/hg18_sorted_tile.list" )
  writ := bufio.NewWriter( wfp )
  for i:=0; i<len(tileList); i++ {
    writ.WriteString( fmt.Sprintf("\"%s\",\"%s\"\n", tileList[i], hg18_map[ tileList[i] ] ) )
  }
  writ.Flush();
  wfp.Close()

  os.Exit(0)

  fmt.Print("# sort hg18 tiles done...\n")
  */

  //curBand := 0
  tileSet := tile.NewTileSet( tagLen )
  faChrom := []byte{}

  headerTemplate := "{ \"tileID\":\"\", \"locus\":[{\"build\":\"\"}],\"n\":-1,\"copy\":-1,\"startTag\":\"\",\"endTag\":\"\",\"notes\":[] }"

  //prevRefGenome := ""
  prevTileBand := int64(-1)
  prevChrom := ""
  for i:=0 ; i<len(tileList) ; i++ {

    tileIdParts := strings.SplitN( tileList[i], ".", -1 )
    curTileBand,_ := strconv.ParseInt( tileIdParts[0], 16, 0 )

    //DEBUG
    fmt.Printf("[%d] tileId: %s, band %d, prevband %d\n", i, tileList[i], curTileBand, prevTileBand)

    v := strings.SplitN( hg18_map[ tileList[i] ], " ", -1 )

    //tRefGenome  := v[0]
    chrom       := v[1]
    s,_         := strconv.Atoi( v[2] )
    e,_         := strconv.Atoi( v[3] )

    // One time initialization
    //
    if prevChrom == "" {
      prevChrom = chrom
      faChrom = aux.FaToByteArray( fmt.Sprintf("%s/%s.fa", hg18dir, chrom) )
      prevTileBand = curTileBand
    }


    // Update state and write out fastj
    //
    if chrom != prevChrom {

      ofile := fmt.Sprintf("%s/%s_band%d_%s.fj", odir, prevChrom, prevTileBand, refGenome )
      tileSet.WriteFastjFile( ofile )

      //DEBUG
      fmt.Printf("\n\n --> %s\n", ofile)

      // Advance state
      //
      tileSet = tile.NewTileSet( tagLen )
      faChrom = aux.FaToByteArray( fmt.Sprintf("%s/%s.fa", hg18dir, chrom) )
      prevTileBand = curTileBand
    }


    if prevTileBand != curTileBand {
      ofile := fmt.Sprintf("%s/%s_band%d_%s.fj", odir, chrom, prevTileBand, refGenome )
      tileSet.WriteFastjFile( ofile )
      tileSet = tile.NewTileSet( tagLen )

      //DEBUG
      fmt.Printf("\n\n ---> %s\n", ofile)
    }

    // Create and populate header
    //
    header := tile.TileHeader{}
    json.Unmarshal( []byte( headerTemplate ), &header )

    header.Locus = make( []map[string]string, 1 )
    header.Locus[0] = make( map[string]string )
    header.Locus[0]["build"] = fmt.Sprintf("%s %s %d %d", refGenome, chrom, s, e )
    //header.Notes = make( []string, 1 )
    //header.Notes[0] = "..."

    headerStr,_ := json.Marshal( &header )

    tileSet.AddTile( tileList[i], string(faChrom[s:e]), string(headerStr) )

    prevChrom = chrom
    prevTileBand = curTileBand
    //prevRefGenome = refGenome

  }

  ofile := fmt.Sprintf("%s/%s_band%d_%s.fj", odir, prevChrom, prevTileBand, refGenome )
  tileSet.WriteFastjFile( ofile )

  //DEBUG
  fmt.Printf("\n\n ---> %s\n", ofile)

}
