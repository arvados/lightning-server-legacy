package cgf

import "fmt"
import "os"
import "encoding/json"
import "crypto/md5"
import "bufio"
import "strconv"
import "strings"

import "sort"

var VERSION_STR string = "1.0"
var CGF_VERSION string = "0.4"

type TileMapEntry struct {
  Type string
  Ploidy int
  Variant [][]int
  VariantLength [][]int
}

type OverflowMapEntry struct {
  Type string
  Data string
}

type CGFLean struct {
  CGFVersion string
  Encoding string
  Notes string
  TileLibraryVersion string

  PathCount int
  StepPerPath []int
  StepPerPathSum []int
  TotalStep int

  EncodedTileMap string
  EncodedTileMapMd5Sum string

  CharMap map[string]int
  ReverseCharMap map[int]string
  CanonicalCharMap string
  ReservedCharCount int

  ABV map[string]string
  OverflowMap map[string]int
  FinalOverflowMap map[string]OverflowMapEntry

  TileMapLookupCache map[string]int
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
  EncodedTileMap string
  EncodedTileMapMd5Sum string

  CharMap map[string]int
  ReverseCharMap map[int]string
  CanonicalCharMap string
  ReservedCharCount int

  ABV map[string]string
  OverflowMap map[string]int
  FinalOverflowMap map[string]OverflowMapEntry

  TileMapLookupCache map[string]int
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

  //cg.EncodedTileMap = string(cg.CreateEncodedTileMap())
  cg.EncodedTileMap = string(CreateEncodedTileMap(cg.TileMap))
  cg.EncodedTileMapMd5Sum = cg.EncodedTileMapMd5SumString()

  cg.CharMap = DefaultCharMap()
  cg.ReverseCharMap = DefaultReverseCharMap()
  cg.CanonicalCharMap = DefaultCanonicalCharMap()
  cg.ReservedCharCount = DefaultReservedCharCount()
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

func NewUnphased() *CGF {
  cg := &(CGF{})
  cg.CGFVersion = CGF_VERSION
  cg.Encoding = "utf8"
  cg.TileLibraryVersion = ""

  cg.TileMap = DefaultTileMapUnphased()

  cg.EncodedTileMap = string(CreateEncodedTileMap(cg.TileMap))
  cg.EncodedTileMapMd5Sum = cg.EncodedTileMapMd5SumString()

  cg.CharMap = DefaultCharMap()
  cg.ReverseCharMap = DefaultReverseCharMap()
  cg.CanonicalCharMap = DefaultCanonicalCharMap()
  cg.ReservedCharCount = DefaultReservedCharCount()
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

type ByAsciiHex []string

func (t ByAsciiHex) Len() int { return len(t) }
func (t ByAsciiHex) Swap(i,j int) {t[i],t[j] = t[j],t[i] }
func (t ByAsciiHex) Less(i,j int) bool {
  x,_ := strconv.ParseInt( t[i], 16, 64 )
  y,_ := strconv.ParseInt( t[j], 16, 64 )
  return x<y
}

func (cgf *CGF) PrintFile( ofp *os.File ) {


  fmt.Fprintln( ofp, "{")
  fmt.Fprintln( ofp, "\"#!cgf\":\"a\",\n" )

  fmt.Fprintf( ofp, "  \"CGFVersion\" : \"%s\",\n", cgf.CGFVersion)
  fmt.Fprintf( ofp, "  \"Encoding\" : \"%s\",\n", cgf.Encoding)
  fmt.Fprintf( ofp, "  \"Notes\" : \"%s\",\n", cgf.Notes)
  fmt.Fprintf( ofp, "  \"TileLibraryVersion\" : \"%s\",\n", cgf.TileLibraryVersion)


  count := 0
  fmt.Fprintf( ofp, "  \"ABV\":{\n    ")

  // Output contents of ABV in sorted order
  //
  abv_key := []string{}
  for k,_ := range cgf.ABV {
    abv_key = append( abv_key, k )
  }
  sort.Sort( ByAsciiHex(abv_key) )

  for i:=0; i<len(abv_key); i++ {
    if count>0 { fmt.Fprintf( ofp, ",\n    ") }
    fmt.Fprintf( ofp, "  \"%s\" : \"%s\"", abv_key[i],cgf.ABV[abv_key[i]])
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

  fmt.Fprintf( ofp, "  \"CanonicalCharMap\" : \"%s\",\n", cgf.CanonicalCharMap )
  fmt.Fprintf( ofp, "  \"ReservedCharCount\" : %d,\n", cgf.ReservedCharCount )

  fmt.Fprintf( ofp, "  \"EncodedTileMapMd5Sum\":\"%s\",\n", cgf.EncodedTileMapMd5Sum )
  fmt.Fprintf( ofp, "  \"EncodedTileMap\":\"%s\",\n", cgf.EncodedTileMap )

  /*
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
  */


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


func LoadLean( fn string ) ( cgl *CGFLean, err error ) {
  fp,err := os.Open( fn )
  if err != nil { return nil, err }
  defer fp.Close()

  reader := bufio.NewReader(fp)

  cgl = &(CGFLean{})

  dec := json.NewDecoder(reader)

  err = dec.Decode( cgl )
  if err != nil { return nil, err }

  cgl.ReverseCharMap = ConstructReverseCharMap( cgl.CharMap )

  return cgl, nil
}

func Load( fn string ) ( cg *CGF, err error ) {
  fp,err := os.Open( fn )
  if err != nil { return nil, err }
  defer fp.Close()

  reader := bufio.NewReader(fp)

  cg = &(CGF{})

  dec := json.NewDecoder(reader)

  err = dec.Decode( cg )
  if err != nil { return nil, err }

  cg.ReverseCharMap = ConstructReverseCharMap( cg.CharMap )
  cg.TileMap,err = CreateTileMapFromEncodedTileMap( cg.EncodedTileMap )
  if err!=nil { return nil, err }

  return cg, nil
}

func LoadNoMap( fn string ) ( cg *CGF, err error ) {
  fp,err := os.Open( fn )
  if err != nil { return nil, err }
  defer fp.Close()

  reader := bufio.NewReader(fp)

  cg = &(CGF{})

  dec := json.NewDecoder(reader)

  err = dec.Decode( cg )
  if err != nil { return nil, err }

  cg.ReverseCharMap = ConstructReverseCharMap( cg.CharMap )
  //cg.TileMap,err = CreateTileMapFromEncodedTileMap( cg.EncodedTileMap )
  if err!=nil { return nil, err }

  return cg, nil
}

/*
func ( cgf *CGF ) CreateEncodedTileMap() ( []byte ) {
  typeMap := map[string][2]byte{
    "het": [2]byte{ 'x', '.' },
    "hom": [2]byte{'_', '.'} ,
    "het*": [2]byte{'x','*'},
    "hom*": [2]byte{'_','*'} }
  b := []byte{}

  for i:=0; i<len(cgf.TileMap); i++ {
    if i>0 { b = append( b, ';' ) }

    if v,ok := typeMap[ cgf.TileMap[i].Type ] ; ok {
      //xx := typeMap[ cgf.TileMap[i].Type ]
      b = append( b, v[:]... )
    } else {
      b = append(b, []byte( cgf.TileMap[i].Type )... )
    }

    for v:=0; v<len(cgf.TileMap[i].Variant); v++ {
      if v>0 { b = append(b, ':') }
      for k:=0; k<len(cgf.TileMap[i].Variant[v]); k++ {
        if k>0 { b = append(b, ',') }
        b = append(b, []byte( fmt.Sprintf("%x", cgf.TileMap[i].Variant[v][k]) )... )
      }
    }
  }

  return b
}
*/

func CreateEncodedTileMap( TileMap []TileMapEntry ) ( []byte ) {
  typeMap := map[string][2]byte{
    "het": [2]byte{ 'x', '.' },
    "hom": [2]byte{'_', '.'} ,
    "het*": [2]byte{'x','*'},
    "hom*": [2]byte{'_','*'} }
  b := []byte{}

  for i:=0; i<len(TileMap); i++ {
    if i>0 { b = append( b, ';' ) }

    if v,ok := typeMap[ TileMap[i].Type ] ; ok {
      b = append( b, v[:]... )
    } else {
      b = append(b, []byte( TileMap[i].Type )... )
    }

    for v:=0; v<len(TileMap[i].Variant); v++ {
      if v>0 { b = append(b, ':') }
      for k:=0; k<len(TileMap[i].Variant[v]); k++ {
        if k>0 { b = append(b, ',') }

        varstr := ""
        if TileMap[i].VariantLength[v][k] > 1 {
          varstr = fmt.Sprintf("+%x", TileMap[i].VariantLength[v][k])
        }
        b = append(b, []byte( fmt.Sprintf("%x%s", TileMap[i].Variant[v][k], varstr) )... )
      }
    }
  }
  return b
}


func CreateTileMapFromEncodedTileMap( s string ) ( []TileMapEntry, error ) {
  n_ele := 0

  type_map := map[string]string{ "_." : "hom", "_*":"hom*", "x.":"het", "x*":"het*" }

  for i:=0; i<len(s); i++ {
    if s[i] == ';' { n_ele++ }
  }

  tmap := make( []TileMapEntry, n_ele+1 )

  s_entry_list := strings.Split( s, ";" )

  for i:=0; i<len(s_entry_list); i++ {

    tmap[i].Type = type_map[ s_entry_list[i][0:2] ]

    tile_allele_class := strings.Split( s_entry_list[i][2:], ":" )

    tmap[i].Ploidy = len(tile_allele_class)
    tmap[i].Variant = make( [][]int, tmap[i].Ploidy )

    for j:=0; j<len(tile_allele_class); j++ {
      tile_var_list := strings.Split( tile_allele_class[j], "," )

      tmap[i].VariantLength = append( tmap[i].VariantLength, []int{} )

      for k:=0; k<len(tile_var_list); k++ {

        tile_var_list_ele := strings.Split( tile_var_list[k], "+" )
        var_len := 1
        if len(tile_var_list_ele) == 2 {
          var_len_64,e := strconv.ParseInt( tile_var_list_ele[1], 16, 64 )
          if e!=nil { return nil, e }
          var_len = int(var_len_64)
        }

        tmap[i].VariantLength[j] = append( tmap[i].VariantLength[j], var_len )

        variant,e := strconv.ParseInt( tile_var_list_ele[0], 16, 64 )
        if e!=nil { return nil, e }

        tmap[i].Variant[j] = append( tmap[i].Variant[j], int(variant) )
      }
    }

  }

  return tmap,nil

}

func ( cg *CGF ) EncodedTileMapMd5SumString() string {
  //b := cg.CreateEncodedTileMap()
  b := CreateEncodedTileMap( cg.TileMap )
  m5 := md5.Sum( b )

  s := ""
  for i:=0; i<len(m5); i++ {
    s += fmt.Sprintf("%02x", m5[i])
  }

  return s

}

// Create s key for lookup into the TileMapLookupCache.
//
func ( cgf *CGF ) CreateTileMapCacheKey( variantType string, variantId [][]int, variantIdLength [][]int ) string {
  s := [][]string{}
  tkey := []string{}
  for i:=0; i<len(variantId); i++ {
    s = append( s, []string{} )
    for j:=0; j<len(variantId[i]); j++ {

      strlen := ""
      if variantIdLength[i][j] > 1 { strlen = fmt.Sprintf("%x", variantIdLength[i][j]) }
      s[i] = append( s[i], fmt.Sprintf("%x+%x", variantId[i][j], strlen) )
    }
    tkey = append( tkey, strings.Join( s[i], ";" ) )
  }
  key := variantType + ":" + strings.Join( tkey, ":" )

  return key
}

// Given a double array of variants, find the position in the TileMap
// it corresponds to.
// A cache is maintained so that a linear search doesn't need to
// happen every query.
//
// Returns the position in the TileMap if found, -2 otherwise.
//
func ( cg *CGF ) LookupTileMapVariant( variantType string, variantId [][]int, variantIdLength [][]int ) int {
  if cg.TileMapLookupCache == nil { cg.TileMapLookupCache = make( map[string]int ) }

  key := cg.CreateTileMapCacheKey( variantType, variantId, variantIdLength )
  if v,ok := cg.TileMapLookupCache[key] ; ok { return v }

  for i:=0; i<len(cg.TileMap); i++ {
    tm := cg.TileMap[i]

    if len(tm.Variant) != len(variantId) { continue }
    if variantType != tm.Type { continue }

    found := true
    for j:=0; j<len(tm.Variant); j++ {
      if len(tm.Variant[j]) != len(variantId[j]) { found = false ; break }
      if len(tm.VariantLength[j]) != len(variantIdLength[j]) { found = false; break }
      for k:=0; k<len(tm.Variant[j]); k++ {
        if tm.Variant[j][k] != variantId[j][k] { found = false ; break }
        if tm.VariantLength[j][k] != variantIdLength[j][k] { found = false; break }
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

// Given a double array of variants, find the position int he TileMap
// it corresponds to.
// A cache is maintained so that a linear search doesn't need to
// happen every query.
//
// Returns the position in the TileMap if found, -2 otherwise.
//
func ( cg *CGF ) LookupABVTileMapVariant( path, step int ) ( variant int, err error ) {

  path_key := fmt.Sprintf("%x", path)

  abv,abv_ok := cg.ABV[path_key]
  if !abv_ok { return 0, fmt.Errorf("Could not find '%s'", path_key) }
  if (step<0) || (step>=len(abv)) { return 0, fmt.Errorf("Could not find '%s'", path_key) }

  ch := string(abv[step])
  code := cg.CharMap[ch]

  if code >= 0 { return code,nil }
  if code != -2 { return code,nil }

  path_step_key := fmt.Sprintf("%x:%x", path, step)
  overflow_val,oflow_ok := cg.OverflowMap[path_step_key]
  if !oflow_ok { return 0, fmt.Errorf("Tile variant not trivial, consult FinalOverflowMap") }

  return overflow_val,nil

}

// If we fall in a tile of variant length, scan until the parent is reached
// and return teh path, step and variant.
//
func ( cg *CGF ) LookupABVStartTileMapVariant( path, step int ) ( p,s,v int, err error ) {

  path_key := fmt.Sprintf("%x", path)

  abv,abv_ok := cg.ABV[path_key]
  if !abv_ok { return 0,0,0, fmt.Errorf("Could not find '%s'", path_key) }
  if (step<0) || (step>=len(abv)) { return 0,0,0, fmt.Errorf("Could not find '%s'", path_key) }

  ch := string(abv[step])
  code := cg.CharMap[ch]

  if code >= 0 { return path,step,code,nil }
  if code == -2 {
    path_step_key := fmt.Sprintf("%x:%x", path, step)
    overflow_val,oflow_ok := cg.OverflowMap[path_step_key]
    if !oflow_ok { return 0,0,0, fmt.Errorf("Tile variant not trivial, consult FinalOverflowMap") }

    return path,step,overflow_val,nil
  }

  if code == -1 { return path,step,code,nil }
  if code != -3 { return 0,0,0, fmt.Errorf("Unknown code %d", code) }

  for ; step>=0; step-- {
    ch := string(abv[step])
    code := cg.CharMap[ch]

    if code >= 0 { return path,step,code,nil }
    if code == -2 {
      path_step_key := fmt.Sprintf("%x:%x", path, step)
      overflow_val,oflow_ok := cg.OverflowMap[path_step_key]
      if !oflow_ok { return 0,0,0, fmt.Errorf("Tile variant not trivial, consult FinalOverflowMap") }

      return path,step,overflow_val,nil
    }

  }

  return 0,0,0, fmt.Errorf("Reached beginning of vector without finding parent")

}

// Returns character code as implied by the CharMap (and ReverseCharMap).
// The flag will return true if the variant was found in the TileMap, false
// otherwise.
//
func ( cg *CGF ) LookupABVCharCode( tileMapPos int ) (string, bool) {
  if (tileMapPos < 0) || (tileMapPos >= len(cg.TileMap)) {
    return "#", false
  }

  if tileMapPos >= len(cg.CanonicalCharMap) {
    return "#", true
  }

  if tileMapPos >= (len(cg.CanonicalCharMap)-cg.ReservedCharCount) {
    return cg.CanonicalCharMap[tileMapPos:tileMapPos+1], true
  }

  return cg.CanonicalCharMap[tileMapPos:tileMapPos+1], true

}


func ( cg *CGF ) ABVTileMapVariantVarianbleLength( path, step int ) ( bool, error ) {
  path_key := fmt.Sprintf("%x", path)

  abv,abv_ok := cg.ABV[path_key]
  if !abv_ok { return false, fmt.Errorf("Could not find '%s'", path_key) }
  if (step<0) || (step>=len(abv)) { return false, fmt.Errorf("Could not find '%s'", path_key) }

  ch := string(abv[step])
  code := cg.CharMap[ch]

  if code == -3 { return true,nil }
  return false,nil
}



func ( cgf *CGF ) Dump( fn string ) error {
  fp,err := os.Create( fn )
  if err != nil { return err }
  defer fp.Close()

  enc := json.NewEncoder( fp )
  enc.Encode( cgf )

  return nil

}
