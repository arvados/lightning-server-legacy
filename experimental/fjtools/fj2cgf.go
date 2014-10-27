


package main

import "fmt"
import "os"
import "strings"
import "strconv"
import _ "errors"
import "bufio"
import "sort"

//import "encoding/json"
import "../sloppyjson"

import _ "../tile"
import "../bioenv"
import "../cgf"

import "github.com/codegangsta/cli"

import "runtime/pprof"


var VERSION_STR string = "0.1, AGPLv3.0"
var g_verboseFlag bool
var gCGF *cgf.CGF

var ABV_VERSION string = "0.1"

func init() {
  _ = gCGF
}

func md5Ascii( b [16]byte ) (s []byte) {
  for i:=0; i<len(b); i++ {
    t := fmt.Sprintf("%02x", b[i] )
    s = append( s, []byte(t)... )
  }
  return s
}

/*
type FastJHeader struct {
  TileId string `json:"tileId"`
  Md5sum string `json:"md5sum"`
  locus []map[string]string `json:"locus"`
  N int `json:"n"`
  SeedTileLength  int `json:"seedTileLength"`
  StartSeq string `json:"startSeq"`
  EndSeq string `json:"endSeq"`
  StartTag string `json:"startSeq"`
  EndTag string `json:"endTag"`
  Notes []string `json:"notes"`
}
*/

type TileLibraryElement struct {
  BaseName string
  BaseId uint64
  TileId []uint64
  TileSId []string
  Md5sum []string
  Freq []int

  Md5sumPosMap map[string]int
}

func PrintTileLibraryElement( tle *TileLibraryElement ) {
  fmt.Println("BaseName:", tle.BaseName)
  fmt.Println("BaseId:", tle.BaseId)

  for i:=0; i<len(tle.TileId); i++ {
    fmt.Printf("[%d] %d %s %s freq:%d\n", i,
      tle.TileId[i], tle.TileSId[i], tle.Md5sum[i], tle.Freq[i])
  }

  fmt.Printf("[")
  for k:=range tle.Md5sumPosMap {
    fmt.Printf(" %s:%d", k, tle.Md5sumPosMap[k] )
  }
  fmt.Printf(" ]\n")
}

var cacheLibLine []string

func ( tle *TileLibraryElement) ScanBaseTile( scanner *bufio.Scanner ) error {

  var g_err error

  curBase := ""
  origBase := ""

  tle.TileId = nil
  tle.TileSId = nil
  tle.Md5sum = nil
  tle.Freq = nil

  tle.Md5sumPosMap = make( map[string]int )

  if len(cacheLibLine)==0 {

    if !scanner.Scan() { return nil }
    lib_line := scanner.Text()

    for (len(lib_line)==0) || (lib_line[0]=='\n') || (lib_line[0]=='#') {
      if scanner.Scan() {
        lib_line = scanner.Text()
      }
    }
    cacheLibLine = append( cacheLibLine, lib_line )

  }

  for curBase == origBase {

    lib_line := cacheLibLine[ len(cacheLibLine)-1 ]

    line_ele := strings.Split(lib_line, `,` )
    curBase = line_ele[2]

    if len(origBase) == 0 {
      origBase = line_ele[2]
    }

    if curBase == origBase {
      tle.BaseName = curBase

      tle.BaseId,g_err = strconv.ParseUint( curBase, 10, 64 )
      if g_err != nil { return g_err }

      id,e := strconv.ParseUint( line_ele[1], 16, 64 )
      if e != nil { return e }

      f,e := strconv.Atoi( line_ele[3] )
      if e != nil { return e }

      tle.TileId = append( tle.TileId, id )
      tle.Md5sum = append( tle.Md5sum, line_ele[4] )
      tle.TileSId = append( tle.TileSId, line_ele[0] )
      tle.Freq = append( tle.Freq, f )

      tle.Md5sumPosMap[ line_ele[4] ] = len(tle.TileId)-1
    } else {
      continue
    }

    if !scanner.Scan() { break }
    peek_line := scanner.Text()

    for (len(peek_line)==0) || (peek_line[0]=='\n') || (peek_line[0]=='#') {
      if scanner.Scan() {
        peek_line = scanner.Text()
      } else {
        break
      }
    }

    cacheLibLine = append( cacheLibLine, peek_line )

  }

  if len(cacheLibLine) > 0 {
    trail_line := cacheLibLine[ len(cacheLibLine)-1 ]
    cacheLibLine = nil
    cacheLibLine = append( cacheLibLine, trail_line )
  }

  return nil
}

func streqn( a,b string, n int ) bool {
  l_a := len(a)
  l_b := len(b)

  if n < l_a { l_a = n }
  if n < l_b { l_b = n }

  return a[:l_a] == b[:l_b]

}

func tileIdPathStep( tileId string ) (uint64, uint64, error) {
  s := strings.Split( tileId,  `.` )
  if len(s)!=4 { return 0,0,fmt.Errorf("invalid TileId") }

  path,e := strconv.ParseUint( s[0], 16, 64 )
  if e!=nil { return 0,0,e }

  step,e := strconv.ParseUint( s[2], 16, 64 )
  if e!=nil { return 0,0,e }

  return path,step,nil

}

func tileIdToBaseId( tileId string ) (uint64, error) {
  s := strings.Split( tileId,  `.` )
  if len(s)!=4 { return 0,fmt.Errorf("invalid TileId") }

  a,e := strconv.ParseUint( s[0], 16, 64 )
  if e!=nil { return 0,e }

  b,e := strconv.ParseUint( s[1], 16, 64 )
  if e!=nil { return 0,e }

  c,e := strconv.ParseUint( s[2], 16, 64 )
  if e!=nil { return 0,e }

  return uint64(uint(c) + ((1<<16) * uint(b) ) + ((1<<(16+8))*uint(a)) ), nil
}

// Find phase information from 'notes' list.  Phase string
// should be of the form 'Phase ... (A|B)'
//
func deducePhase( fjHeader *sloppyjson.SloppyJSON ) ( string, error ) {

  for i:=len(fjHeader.O["notes"].L)-1; i>=0; i-- {

    if streqn( fjHeader.O["notes"].L[i].S, "Phase ", len("Phase ") ) {
      n := len(fjHeader.O["notes"].L[i].S)
      return fjHeader.O["notes"].L[i].S[ n-1:n ], nil
    }

    if streqn( fjHeader.O["notes"].L[i].S, "Unphased ", len("Unphased ") ) {
      return "B", nil
    }

  }

  return "", fmt.Errorf("could not deduce phase")
}

func hasGap( fjHeader *sloppyjson.SloppyJSON ) bool {
  var err error
  hg19_s := 0
  hg19_e := 0

  for i:=0; i<len(fjHeader.O["locus"].L); i++ {
    if nod,ok := fjHeader.O["locus"].L[i].O["build"] ; ok {
      vv := strings.Split( nod.S, " " )
      v := strings.Split( vv[2], "-" )
      hg19_s,err = strconv.Atoi(v[0])
      if err!=nil { fmt.Fprintf( os.Stderr, "hg19_s conversion %v\n", err ) }

      v = strings.Split( vv[3], "+" )
      hg19_e,err = strconv.Atoi(v[0])
      if err!=nil { fmt.Fprintf( os.Stderr, "hg19_e conversion %v\n", err ) }
    }
  }

  for i:=len(fjHeader.O["notes"].L)-1; i>=0; i-- {
    if strings.Contains( fjHeader.O["notes"].L[i].S, " GAP " ) {
      if strings.HasPrefix( fjHeader.O["notes"].L[i].S, "gapOnTag ") {
        v := strings.Split( fjHeader.O["notes"].L[i].S, " " )
        s,ee := strconv.Atoi(v[3])
        if ee !=nil { fmt.Fprintf( os.Stderr, "s conversion %v\n", ee ) }

        e,ee := strconv.Atoi(v[4])
        if ee!=nil { fmt.Fprintf( os.Stderr, "e conversion %v\n", ee ) }

        if (e < hg19_s) || (s > hg19_e) { continue }

        //fmt.Printf( "s%d, e%d (hg19 s%d,e%d)\n", s, e, hg19_s, hg19_e )

        return true
      } else { return true }
    }
  }
  return false
}


type ByTileId []*sloppyjson.SloppyJSON

func (t ByTileId) Len() int          { return len(t) }
func (t ByTileId) Swap(i,j int)      { t[i],t[j] = t[j],t[i] }
func (t ByTileId) Less(i,j int) bool { return t[i].O["tileID"].S < t[j].O["tileID"].S }

func maxvi( v []int ) int {
  var m int
  for i:=0; i<len(v); i++ {
    if i==0 { m=v[i] }
    if m<v[i] { m=v[i] }
  }
  return m
}

// We make minimal assumptions about how the FastJ appears, but we assume the tile library
// is in sorted order.
//
func UpdateABV( cg *cgf.CGF, tileLibFn string, fastjFn string ) error {

  //---------------
  //
  // Process the FastJ headers and sort
  //
  fjHeaderList := []*sloppyjson.SloppyJSON{}

  fastj_h,err := bioenv.OpenScanner( fastjFn )
  if err != nil { return err }
  for fastj_h.Scanner.Scan() {
    fastj_line := fastj_h.Scanner.Text()
    if (len(fastj_line) == 0) || (fastj_line[0] != '>') { continue }

    fastjHeader,e := sloppyjson.Loads( fastj_line[1:] )
    if e != nil { return e }

    fjHeaderList = append( fjHeaderList, fastjHeader )

  }
  fastj_h.Close()

  sort.Sort(ByTileId(fjHeaderList))
  //
  //
  //---------------


  var fjSaveBase uint64
  var recentBaseTileId uint64 = 0
  walkTile := 0
  firstPass := true

  abv := make( []byte, 0, 1024) ; _ = abv
  tleCache := make( map[uint64]*TileLibraryElement )

  // Hold the variant ids and the seed tile lengths of each
  // phase.  We add/update to these as we process the FastJ
  // headers.
  //
  phaseVariant := [][]int{ []int{}, []int{} }
  phaseVariantSeedTileLength := []int{ 0, 0 }
  phaseVariantPrevBaseId := []uint64{ 0, 0 }

  gapFlag := false


  // We assume the tile library is in tileID sorted order
  //
  lib_h,err := bioenv.OpenScanner(tileLibFn)
  if err != nil { return err }
  defer lib_h.Close()

  var prev_path uint64
  var prev_step uint64

  for fjpos:=0; fjpos<len( fjHeaderList ); fjpos++ {
    phase,err := deducePhase( fjHeaderList[fjpos] )
    if err != nil { return err }

    path,step,e := tileIdPathStep( fjHeaderList[fjpos].O["tileID"].S )
    if e != nil { return e }

    if fjpos==0 { prev_path = path }
    if path != prev_path {


      //Tie off the abv vector and add it to the cgf structure
      //
      n := uint64(cg.StepPerPath[ prev_path ])
      for i:=prev_step; i<n; i++ {
        abv = append( abv, '-' )
      }

      cg.ABV[ fmt.Sprintf("%x", prev_path) ] = string(abv)

      abv = make( []byte, 0, 1024)
      prev_step = 0

    }


    fjBaseId,e := tileIdToBaseId( fjHeaderList[fjpos].O["tileID"].S )
    if e!=nil { return e }
    if firstPass {
      fjSaveBase = fjBaseId
      firstPass = false
      phaseVariantPrevBaseId[0] = fjBaseId
      phaseVariantPrevBaseId[1] = fjBaseId
    }

    // Notice this tile has a GAP on it
    //
    if hasGap( fjHeaderList[fjpos] ) { gapFlag = true }

    // Bring the tile library scanner up to date
    //
    for (recentBaseTileId == 0) || (recentBaseTileId < fjBaseId) {
      t := &(TileLibraryElement{})
      t.ScanBaseTile( lib_h.Scanner )

      tleCache[ t.BaseId ] = t
      recentBaseTileId = t.BaseId
    }

    md5s := fjHeaderList[fjpos].O["md5sum"].S

    seedTileLength := 1
    if _,ok := fjHeaderList[fjpos].O["seedTileLength"] ; ok {
      seedTileLength = int( fjHeaderList[fjpos].O["seedTileLength"].P + 0.5 )
    }

    variantPos := -2
    if pos,ok := tleCache[ fjBaseId ].Md5sumPosMap[md5s] ; ok {
      variantPos = pos
    } else {
      fmt.Fprintf( os.Stderr, "WARNING: %d %s not found in tleCache!\n", fjBaseId, md5s )
    }


    // If we encounter the first allele (phase 'A'), then we add
    // the seedTileLength (the number of seed tiles the tile variant
    // takes up) to the 'walkTile' count.
    // If we encounter the second allele (phase 'B') then we subtract
    // the seedTileLength.
    // If the 'walkTile' variable hits 0, we know it's time to emit
    // an ABV snippet.
    //

    if phase == "A" {
      walkTile += seedTileLength
      phaseVariantSeedTileLength[0] += seedTileLength

      for x:=phaseVariantPrevBaseId[0]; (x+uint64(seedTileLength)) < fjBaseId; x++ {

        //fmt.Printf("ADDING '-' to allele A (x%d: %d+%d)\n", x, fjBaseId, seedTileLength)

        phaseVariant[0] = append( phaseVariant[0], '-' )
      }
      phaseVariantPrevBaseId[0] = fjBaseId + uint64(seedTileLength)

      phaseVariant[0] = append( phaseVariant[0], variantPos )
    } else if phase == "B" {
      walkTile -= seedTileLength
      phaseVariantSeedTileLength[1] += seedTileLength

      for x:=phaseVariantPrevBaseId[1]; (x+uint64(seedTileLength)) < fjBaseId; x++ {

        //fmt.Printf("ADDING '-' to allele B (x%d: %d+%d)\n", x, fjBaseId, seedTileLength)

        phaseVariant[1] = append( phaseVariant[1], '-' )
      }
      phaseVariantPrevBaseId[1] = fjBaseId + uint64(seedTileLength)

      phaseVariant[1] = append( phaseVariant[1], variantPos )
    } else {
      return fmt.Errorf("invalid phase '%s' (fjpos %d, md5sum %s)", phase, fjpos, fjHeaderList[fjpos].O["md5sum"].S)
    }

    if (walkTile == 0) {

      variantType := "hom"
      if len(phaseVariant[0]) != len(phaseVariant[1]) { variantType = "het"
      } else {
        for ii:=0; ii<len(phaseVariant[0]); ii++ {
          if phaseVariant[0][ii] != phaseVariant[1][ii] { variantType = "het" }
        }
      }
      if gapFlag { variantType = variantType + "*" }

      tile_map_pos        := cg.LookupTileMapVariant( variantType, phaseVariant )
      abv_char_code,found := cg.LookupABVCharCode( tile_map_pos )
      abv_snip_len        := maxvi( phaseVariantSeedTileLength )

      _ = found

      abv = append( abv, abv_char_code... )
      for ii:=0; ii<(abv_snip_len-1); ii++ {
        abv = append( abv, '*' )
      }

      if found && (abv_char_code=="#") {
        step_pos_key := fmt.Sprintf("%x:%x", path, step - uint64(abv_snip_len-1) )
        cg.OverflowMap[ step_pos_key ] = tile_map_pos
      } else if !found {
        step_pos_key := fmt.Sprintf("%x:%x", path, step - uint64(abv_snip_len-1) )

        k := cg.CreateTileMapCacheKey( variantType, phaseVariant )
        cg.FinalOverflowMap[ step_pos_key ] = cgf.OverflowMapEntry{ Type : "message", Data: "{ \"Message\" : \"not implemented yet\", \"VarKey\":\"" + k + "\" }" }
      }

      // Remove un-needed elements in the cache
      //
      for ; fjSaveBase < fjBaseId ; fjSaveBase++ { tleCache[ fjSaveBase ] = nil }

      // Reset state
      //
      phaseVariant[0] = phaseVariant[0][0:0]
      phaseVariant[1] = phaseVariant[1][0:0]

      phaseVariantSeedTileLength[0] = 0
      phaseVariantSeedTileLength[1] = 0
      gapFlag = false

      prev_step = step
    }

  }

  //Tie off the final abv vector and add it to the cgf structure
  //
  n := uint64(cg.StepPerPath[ prev_path ])
  for i:=prev_step; i<n; i++ {
    abv = append( abv, '-' )
  }
  cg.ABV[ fmt.Sprintf("%x", prev_path) ] = string(abv)

  return nil

}

var gProfileFlag bool
var gProfileFile string = "fj2cgf.pprof"

var gMemProfileFlag bool
var gMemProfileFile string = "fj2cgf.mprof"


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

  g_verboseFlag   = c.Bool("Verbose")
  gProfileFlag    = c.Bool("pprof")
  gMemProfileFlag = c.Bool("mprof")


  if len( c.String("input-fastj")) == 0 {
    fmt.Fprintf( os.Stderr, "Provide input FastJ file\n" )
    cli.ShowAppHelp( c )
    os.Exit(1)
  }

  if len( c.String("tile-library")) == 0 {
    fmt.Fprintf( os.Stderr, "Provide tile library\n" )
    cli.ShowAppHelp( c )
    os.Exit(1)
  }


  if len(c.String("cgf-file")) > 0 {
    var err error
    gCGF,err = cgf.Load( c.String("cgf-file") )
    if err!=nil {
      fmt.Fprintf( os.Stderr, "%v\n", err )
      os.Exit(1)
    }
  } else {
    gCGF = cgf.New()
  }


  tile_lib_fns := strings.Split( c.String("tile-library"), "," )
  fastj_fns := strings.Split( c.String("input-fastj"), "," )

  if len(tile_lib_fns) != len(fastj_fns) {
    fmt.Fprintf( os.Stderr, "tile library list length (%d) does not match fastj input list length (%d)\n",
      len(tile_lib_fns), len(fastj_fns) )
    os.Exit(1)
  }

  for i:=0; i<len(tile_lib_fns); i++ {

    if g_verboseFlag {
      fmt.Fprintf( os.Stderr, ">>> %s %s\n", tile_lib_fns[i], fastj_fns[i])
    }

    e := UpdateABV( gCGF, tile_lib_fns[i], fastj_fns[i] )
    if e!=nil {
      fmt.Fprintf( os.Stderr, "ERROR: processing %s %s: %v\n", tile_lib_fns[i], fastj_fns[i], e)
      os.Exit(1)
    }
  }

  var ofp *os.File
  if ( (c.String("output-cgf")=="") || (c.String("output-cgf")=="-")) {
    ofp = os.Stdout
  } else {
    ofp,err := os.Create( c.String("output-cgf") )
    if err!=nil {
      fmt.Fprintf( os.Stderr, "%v", err )
      os.Exit(1)
    }
    defer ofp.Close()
  }

  gCGF.PrintFile(ofp)


}


func main() {

  app := cli.NewApp()
  app.Name  = "fj2cgf"
  app.Usage = "Go from FastJ to Compact Genome Format (CGF)"
  app.Version = VERSION_STR
  app.Author = "Curoverse Inc."
  app.Email = "info@curoverse.com"
  app.Action = func( c *cli.Context ) { _main(c) }

  app.Flags = []cli.Flag{

    cli.StringFlag{
      Name: "input-fastj, i",
      Usage: "FastJ file(s)",
    },

    cli.StringFlag{
      Name: "tile-library, l",
      Usage: "Tile Library file",
    },

    cli.StringFlag{
      Name: "cgf-file, f",
      Usage: "CGF file (optional)",
    },

    cli.StringFlag{
      Name: "output-cgf, o",
      Usage: "Output CGF file",
    },

    cli.BoolFlag{
      Name: "Verbose, V",
      Usage: "Verbose flag",
    },

    cli.BoolFlag{
      Name: "pprof",
      Usage: "Profile usage",
    },

    cli.BoolFlag{
      Name: "mprof",
      Usage: "Profile memory usage",
    },

  }

  app.Run(os.Args)

  if gMemProfileFlag {
    fmem,err := os.Create( gMemProfileFile )
    if err!=nil { panic(fmem) }
    pprof.WriteHeapProfile(fmem)
    fmem.Close()
  }


}

