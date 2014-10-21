package cgf

import "fmt"
import "os"
import "encoding/json"
import "bufio"
import "strconv"
import "strings"

var VERSION_STR string = "1.0"
var CGF_VERSION string = "0.1"

type TileMapEntry struct {
  Type string
  Ploidy int
  Variant [][]int
  VariantLength []int
}

type OverflowMapEntry struct {
  Type string
  Data string
}

type CGF struct {
  CGFVersion string
  Encoding string
  Notes string
  TileLibraryVersion string

  PathCount int
  StepPerPath []int
  StepPerPathSum []int
  TotalStep int

  TileMap []TileMapEntry

  CharMap map[string]int
  ReverseCharMap map[int]string
  CanonicalCharMap string

  ABV map[string]string
  OverflowMap map[string]int
  FinalOverflowMap map[string]OverflowMapEntry

  TileMapLookupCache map[string]int
}


func DefaultCanonicalCharMap() string {
  return ".BCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz012345678*#-"
}

func DefaultCharMap() map[string]int {
  m := make( map[string]int )
  default_base_str := "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
  for i:=0; i<len(default_base_str); i++ { m[ default_base_str[i:i+1] ] = i }
  m["."] = 0
  m["-"] = -1
  m["#"] = -2
  m["*"] = -3
  return m
}

func DefaultReverseCharMap() map[int]string {
  m := make( map[int]string )
  default_base_str := ".BCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz012345678*#-"
  for i:=0; i<len(default_base_str); i++ { m[ i ] = default_base_str[i:i+1] }
  m[-1] = "-"
  m[-2] = "#"
  m[-3] = "*"
  return m
}

func ConstructReverseCharMap( charMap map[string]int ) map[int]string {
  m := make( map[int]string )
  for k,v := range( charMap ) { m[v] = k }
  return m
}

func New() *CGF {
  cg := &(CGF{})
  cg.CGFVersion = CGF_VERSION
  cg.Encoding = "utf8"
  cg.TileLibraryVersion = ""

  cg.TileMap = DefaultTileMap()
  cg.CharMap = DefaultCharMap()
  cg.ReverseCharMap = DefaultReverseCharMap()
  cg.CanonicalCharMap = DefaultCanonicalCharMap()
  cg.ABV = make( map[string]string )
  cg.OverflowMap = make( map[string]int )
  cg.FinalOverflowMap = make( map[string]OverflowMapEntry )

  cg.PathCount = DefaultPathCount()
  cg.StepPerPath = DefaultStepPerPath()
  cg.TotalStep = 0

  cg.StepPerPathSum = make( []int, len(cg.StepPerPath) )
  for i:=0 ; i<len(cg.StepPerPath) ; i++ {
    cg.TotalStep += cg.StepPerPath[i]
    cg.StepPerPathSum[i] = cg.StepPerPath[i]
    if i>0 { cg.StepPerPathSum[i] += cg.StepPerPathSum[i-1] }
  }

  return cg
}

func (cgf *CGF) Print() {
  cgf.PrintFile( os.Stdout )
}

func (cgf *CGF) PrintFile( ofp *os.File ) {

  fmt.Fprintln( ofp, "#!cgf a\n" )

  fmt.Fprintln( ofp, "{")

  fmt.Fprintf( ofp, "  \"CGFVersion\" : \"%s\",\n", cgf.CGFVersion)
  fmt.Fprintf( ofp, "  \"Encoding\" : \"%s\",\n", cgf.Encoding)
  fmt.Fprintf( ofp, "  \"Notes\" : \"%s\",\n", cgf.Notes)
  fmt.Fprintf( ofp, "  \"TileLibraryVersion\" : \"%s\",\n", cgf.TileLibraryVersion)

  fmt.Fprintf( ofp, "  \"PathCount\" : %d,\n", cgf.PathCount )

  fmt.Fprintf( ofp, "  \"StepPerPath\" : [\n    ")
  spp_lf := 10
  for i:=0; i<len(cgf.StepPerPath); i++ {
    if i>0 { fmt.Fprintf( ofp, ",") }
    if (i>0) && ((i%spp_lf)==0) { fmt.Fprintf( ofp, "\n   " ) }
    if i>0 { fmt.Fprintf( ofp, " ") }
    fmt.Fprintf( ofp, "%d", cgf.StepPerPath[i])
  }
  fmt.Fprintf( ofp, "\n    ],\n")
  fmt.Fprintf( ofp, "  \"TotalStep\" : %d,\n", cgf.TotalStep)

  fmt.Fprintln( ofp, "")

  count:=0

  count = 0
  fmt.Fprintf( ofp, "  \"ABV\":{\n    ")
  for k,v := range cgf.ABV {
    if count>0 { fmt.Fprintf( ofp, ",\n    ") }
    fmt.Fprintf( ofp, "  \"%s\" : \"%s\"", k,v)
    count += 1
  }
  fmt.Fprintf( ofp, "\n  },\n")

  fmt.Fprintf( ofp, "  \"CharMap\" : {")
  count = 0
  for k,v := range cgf.CharMap {
    if count>0 { fmt.Fprintf( ofp, ", ") }
    fmt.Fprintf( ofp, "\"%s\":%d", k, v)
    count+=1
  }
  fmt.Fprintf( ofp, "\n  },\n")


  fmt.Fprintf( ofp, "  \"CanonicalCharMap\" : \"%s\",\n", cgf.CanonicalCharMap )


  fmt.Fprintf( ofp, "  \"TileMap\" : [\n    ")
  for i:=0; i<len(cgf.TileMap); i++ {
    if i>0 { fmt.Fprintf( ofp, ",\n    ") }

    tile_ele := cgf.TileMap[i]

    fmt.Fprintf( ofp, "{ \"Type\":\"%s\", \"Ploidy\":2, \"Variant\": [", tile_ele.Type )

    for ii:=0; ii<len(tile_ele.Variant); ii++ {
      if ii>0 { fmt.Fprintf( ofp, "," ) }
      fmt.Fprintf( ofp, "[")
      for jj:=0; jj<len(tile_ele.Variant[ii]); jj++ {
        if jj>0 { fmt.Fprintf( ofp, "," ) }
        fmt.Fprintf( ofp, "%d", tile_ele.Variant[ii][jj] )
      }
      fmt.Fprintf( ofp, "]")
    }
    fmt.Fprintf( ofp, "]")

    fmt.Fprintf( ofp, ", \"VariantLength\":[")
    for ii:=0; ii<len(tile_ele.VariantLength); ii++ {
      if ii>0 { fmt.Fprintf( ofp, "," ) }
      fmt.Fprintf( ofp, "%d", tile_ele.VariantLength[ii] )
    }
    fmt.Fprintf( ofp, "] }" )

  }
  fmt.Fprintf( ofp, "\n    ],\n")


  count = 0
  fmt.Fprintf( ofp, "  \"OverflowMap\":{\n    ")
  for k,v := range cgf.OverflowMap {
    if count>0 { fmt.Fprintf( ofp, ",\n    ") }
    fmt.Fprintf( ofp, "\"%s\":%d", k, v )
    count++
  }
  fmt.Fprintf( ofp, "\n  },\n")


  count = 0
  fmt.Fprintf( ofp, "  \"FinalOverflowMap\":{\n    ")
  for k,v := range cgf.FinalOverflowMap {
    if count>0 { fmt.Fprintf( ofp, ",\n    ") }

    fmt.Fprintf( ofp, "\"%s\" : {\n", k )
    fmt.Fprintf( ofp, "      \"Type\" : \"%s\",\n", v.Type )

    fmt.Fprintf( ofp, "      \"Data\" : ")
    fmt.Fprintf( ofp, "%s", strconv.Quote( v.Data ) )

    //fmt.Fprintf( ofp, "\",\n" )
    fmt.Fprintf( ofp, "\n" )

    fmt.Fprintf( ofp, "    }")
    count++
  }
  fmt.Fprintf( ofp, "\n  }\n")

  fmt.Fprintf( ofp, "}\n")

}


func Load( fn string ) ( cgf *CGF, err error ) {
  fp,err := os.Open( fn )
  if err != nil { return nil, err }
  defer fp.Close()

  reader := bufio.NewReader(fp)

  header,err := reader.ReadString('\n')
  if err != nil { return nil, err }

  if !strings.HasPrefix( header, "#!cgf" ) {
    return nil, fmt.Errorf("Invalid CGF header, expected '#!cgf', got '%s'", header )
  }

  cgf = &(CGF{})

  //dec := json.NewDecoder(fp)
  dec := json.NewDecoder(reader)

  err = dec.Decode( cgf )
  if err != nil { return nil, err }

  cgf.ReverseCharMap = ConstructReverseCharMap( cgf.CharMap )

  return cgf, nil
}

// Create s key for lookup into the TileMapLookupCache.
//
func ( cgf *CGF ) CreateTileMapCacheKey( variantType string, variantId [][]int ) string {
  s := [][]string{}
  tkey := []string{}
  for i:=0; i<len(variantId); i++ {
    s = append( s, []string{} )
    for j:=0; j<len(variantId[i]); j++ {
      s[i] = append( s[i], fmt.Sprintf("%x", variantId[i][j]) )
    }
    tkey = append( tkey, strings.Join( s[i], ";" ) )
  }
  key := variantType + ":" + strings.Join( tkey, ":" )

  return key
}

// Given a double array of variants, find the position int he TileMap
// it corresponds to.
// A cache is maintained so that a linear search doesn't need to
// happen every query.
//
// Returns the position in the TileMap if found, -2 otherwise.
//
func ( cg *CGF ) LookupTileMapVariant( variantType string, variantId [][]int ) int {
  if cg.TileMapLookupCache == nil { cg.TileMapLookupCache = make( map[string]int ) }

  key := cg.CreateTileMapCacheKey( variantType, variantId )
  if v,ok := cg.TileMapLookupCache[key] ; ok { return v }

  for i:=0; i<len(cg.TileMap); i++ {
    tm := cg.TileMap[i]

    if len(tm.Variant) != len(variantId) { continue }
    if variantType != tm.Type { continue }

    found := true
    for j:=0; j<len(tm.VariantLength); j++ {
      if len(tm.Variant[j]) != len(variantId[j]) { found = false ; break }
      for k:=0; k<len(tm.Variant[j]); k++ {
        if tm.Variant[j][k] != variantId[j][k] { found = false ; break }
      }
      if !found { break }
    }
    if !found { continue }


    cg.TileMapLookupCache[key] = i
    return i
  }

  cg.TileMapLookupCache[key] = -2
  return -2
}

// Returns character code as implied by the CharMap (and ReverseCharMap).
// The flag will return true if the variant was found in the TileMap, false
// otherwise.
//
func ( cgf *CGF ) LookupABVCharCode( tileMapPos int ) (string, bool) {
  if (tileMapPos < 0) || (tileMapPos >= len(cgf.TileMap)) {
    return "#", false
  }

  if tileMapPos >= len(cgf.CanonicalCharMap) {
    return "#", true
  }

  return cgf.CanonicalCharMap[tileMapPos:tileMapPos+1], true

}


func ( cgf *CGF ) Dump( fn string ) error {
  fp,err := os.Create( fn )
  if err != nil { return err }
  defer fp.Close()

  enc := json.NewEncoder( fp )
  enc.Encode( cgf )

  return nil

}
