


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
        if ee !=nil { fmt.Fprintf( os.Stderr, "s conversion %v\n", err ) }

        e,ee := strconv.Atoi(v[4])
        if ee!=nil { fmt.Fprintf( os.Stderr, "e conversion %v\n", err ) }

        if (e < hg19_s) || (s > hg19_e) { continue }
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



  //DEBUG
  //fmt.Printf("???\n")
  //for i:=0; i<len(fjHeaderList); i++ {
  //  fmt.Printf("  [%d] %s\n", i, fjHeaderList[i].O["tileID"].S )
  //  if i>= 10 { break }
  //}



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

        fmt.Printf("ADDING '-' to allele A (x%d: %d+%d)\n", x, fjBaseId, seedTileLength)

        phaseVariant[0] = append( phaseVariant[0], '-' )
      }
      phaseVariantPrevBaseId[0] = fjBaseId + uint64(seedTileLength)

      phaseVariant[0] = append( phaseVariant[0], variantPos )
    } else if phase == "B" {
      walkTile -= seedTileLength
      phaseVariantSeedTileLength[1] += seedTileLength

      for x:=phaseVariantPrevBaseId[1]; (x+uint64(seedTileLength)) < fjBaseId; x++ {

        fmt.Printf("ADDING '-' to allele B (x%d: %d+%d)\n", x, fjBaseId, seedTileLength)

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

      /*
      if (step-prev_step) > uint64(abv_snip_len) {

        for ii:=prev_step; ii<(step-uint64(abv_snip_len)); ii++ {

          //DEBUG
          fmt.Printf(" ADDING '-' prev_step %d, step %d (step-prev_step %d), abv_snip_len %d\n",
            step, prev_step, step-prev_step, abv_snip_len )


          abv = append( abv, '-' )
        }
      }
      */

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

      //DEBUG
      //ll := len(abv)
      //fmt.Printf(" fjBaseId %d, %s:%v (tile map pos %d) abv snip : '%s' (found %v)\n",
      //  fjBaseId, variantType, phaseVariant, tile_map_pos, abv[ll-abv_snip_len:ll], found )

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

var gProfileFlag bool = true
var gProfileFile string = "fj2cgf.pprof"

var gMemProfileFlag bool = true
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

  g_verboseFlag = c.Bool("Verbose")


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

  scanner,err := bioenv.OpenScanner( c.String("input-fastj") )
  if err != nil {
    fmt.Fprintf( os.Stderr, "%v", err )
    os.Exit(1)
  }
  defer scanner.Close()



  //tileSet := tile.NewTileSet( 24 )

  /*
  err = tileSet.FastjScanner( scanner.Scanner )
  if err != nil {
    fmt.Fprintf( os.Stderr, "%v\n", err )
    os.Exit(1)
  }
  */


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

  //_,e := UpdateABV( gCGF, c.String("tile-library"), c.String("input-fastj") )

  //e := UpdateABV( gCGF, c.String("tile-library"), c.String("input-fastj") )
  //fmt.Println("err", e)

  e := UpdateABV( gCGF, c.String("tile-library"), c.String("input-fastj") )
  if e != nil { fmt.Println("err", e) }

  gCGF.Print()

  return


  s := []string{ "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr13_band0_s0_e4500000.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr13_band10_s32200000_e34000000.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr13_band11_s34000000_e35500000.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr13_band12_s35500000_e40100000.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr13_band13_s40100000_e45200000.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr13_band14_s45200000_e45800000.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr13_band15_s45800000_e47300000.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr13_band16_s47300000_e50900000.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr13_band17_s50900000_e55300000.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr13_band18_s55300000_e59600000.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr13_band19_s59600000_e62300000.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr13_band1_s4500000_e10000000.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr13_band20_s62300000_e65700000.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr13_band21_s65700000_e68600000.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr13_band22_s68600000_e73300000.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr13_band23_s73300000_e75400000.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr13_band24_s75400000_e77200000.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr13_band25_s77200000_e79000000.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr13_band26_s79000000_e87700000.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr13_band27_s87700000_e90000000.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr13_band28_s90000000_e95000000.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr13_band29_s95000000_e98200000.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr13_band2_s10000000_e16300000.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr13_band30_s98200000_e99300000.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr13_band31_s99300000_e101700000.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr13_band32_s101700000_e104800000.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr13_band33_s104800000_e107000000.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr13_band34_s107000000_e110300000.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr13_band35_s110300000_e115169878.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr13_band3_s16300000_e17900000.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr13_band4_s17900000_e19500000.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr13_band5_s19500000_e23300000.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr13_band6_s23300000_e25500000.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr13_band7_s25500000_e27800000.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr13_band8_s27800000_e28900000.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr13_band9_s28900000_e32200000.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr17_band0_s0_e3300000.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr17_band10_s38400000_e40900000.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr17_band11_s40900000_e44900000.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr17_band12_s44900000_e47400000.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr17_band13_s47400000_e50200000.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr17_band14_s50200000_e57600000.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr17_band15_s57600000_e58300000.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr17_band16_s58300000_e61100000.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr17_band17_s61100000_e62600000.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr17_band18_s62600000_e64200000.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr17_band19_s64200000_e67100000.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr17_band1_s3300000_e6500000.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr17_band20_s67100000_e70900000.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr17_band21_s70900000_e74800000.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr17_band22_s74800000_e75300000.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr17_band23_s75300000_e81195210.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr17_band2_s6500000_e10700000.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr17_band3_s10700000_e16000000.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr17_band4_s16000000_e22200000.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr17_band5_s22200000_e24000000.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr17_band6_s24000000_e25800000.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr17_band7_s25800000_e31800000.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr17_band8_s31800000_e38100000.fj.gz",
    "/scratch/pgp174.gff/hu011C57/chr13_chr17.fj/chr17_band9_s38100000_e38400000.fj.gz" }


  for i:=0; i<len(s); i++ {
    e := UpdateABV( gCGF, c.String("tile-library"), s[i] )
    if e != nil { fmt.Println("err", e) }


  }

  fmt.Printf("...%d\n", len(s))


  //gCGF.Print()

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

  }

  app.Run(os.Args)

  if gMemProfileFlag {
    fmem,err := os.Create( gMemProfileFile )
    if err!=nil { panic(fmem) }
    pprof.WriteHeapProfile(fmem)
    fmem.Close()
  }


}

