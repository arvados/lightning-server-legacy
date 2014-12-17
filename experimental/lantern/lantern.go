package main

import "fmt"
import "os"

import "net/http"
import _ "time"
import "net"

import "strings"
import "strconv"

import "syscall"
import "os/signal"

import "io"
import _ "io/ioutil"
import "encoding/json"

import "runtime/pprof"

import "github.com/codegangsta/cli"

import "../cgf"

import "encoding/gob"

var VERSION_STR string = "0.0.1"

var gProfileFlag bool
var gProfileFile string = "lantern.pprof"

var gMemProfileFlag bool
var gMemProfileFile string = "lantern.mprof"

var g_verboseFlag bool

var gCGF []*cgf.CGF
var gCGFName []string
var gCGFIndexMap map[string]int

var gPortStr string = ":8080"
var g_incr chan int

var gTileVariantToTileClass map[int][]int
var gTileClassVersion string
var gTileLibraryVersion string

var gTileMap map[int][]int

type LanternQueryContainer struct {
  Type string
}

type TileMapVariantClass struct {
  Type string
  Variant [][]int
}



type LanternRequest struct {
  Type string
  Dataset string
  Note string
  Message string

  SampleId []string
  CaseSampleId []string
  ControlSampleId []string
  TileVariantId []string
  TileGroupVariantId [][]string
  TileGroupVariantIdRange [][]map[string][]int
  TileId []string
  Position []string

  PathStep []string

  VariantId map[string]string
  VariantClass map[string]TileMapVariantClass

}

type LanternResponse struct {
  Type string
  Message string
}

func send_error_bad_request( e_str string, w http.ResponseWriter ) {
  fmt.Printf("%s", e_str)
  w.Header().Set("Content-Type", "application/json")
  io.WriteString(w, `{"Type":"error","Message":"bad request"}` )
  return
}

func construct_tile_map( tile_map []cgf.TileMapEntry ) {
  gTileMap = make( map[int][]int )

  n:=len(tile_map)
  for tile_class_pos:=0; tile_class_pos<n; tile_class_pos++ {
    for a:=0; a<len(tile_map[tile_class_pos].Variant); a++ {
      for k:=0; k<len(tile_map[tile_class_pos].Variant[a]); k++ {
        gTileMap[tile_class_pos] = append( gTileMap[tile_class_pos], tile_map[tile_class_pos].Variant[a][k] )
      }
    }
  }

}

func construct_tile_variant_to_tile_class_map( tile_map []cgf.TileMapEntry ) {
  //var gTileVariantToTileClass map[string][]int

  gTileVariantToTileClass = make( map[int][]int )

  n:=len(tile_map)
  for tile_class_pos:=0; tile_class_pos<n; tile_class_pos++ {

    for a:=0; a<len(tile_map[tile_class_pos].Variant); a++ {

      for k:=0; k<len(tile_map[tile_class_pos].Variant[a]); k++ {
        v := tile_map[tile_class_pos].Variant[a][k]
        gTileVariantToTileClass[v] = append( gTileVariantToTileClass[v], tile_class_pos )
      }

    }
  }

}

func tile_variant_in_class( tile_variant, tile_class int ) bool {
  vtc := gTileVariantToTileClass[tile_variant]
  if vtc==nil { return false }
  for i:=0; i<len(vtc); i++ {
    if vtc[i] == tile_class { return true }
  }
  return false
}


func convert_path_step( path_step string ) (path,step int64, err error) {
  v := strings.SplitN( path_step, ":", 2 )
  if len(v) < 2 {
    err = fmt.Errorf("invalid key %s", path_step )
    return
  }
  var e error

  path,e = strconv.ParseInt( v[0], 16, 64 )
  if e!=nil {
    err = fmt.Errorf("invalid path %s", v[0])
    return
  }

  step,e = strconv.ParseInt( v[1], 16, 64 )
  if e!=nil {
    err = fmt.Errorf("invalid step %s", v[1])
    return
  }

  return

}

func convert_path_step_variant( path_step, inp_hex_variant string ) (path,step,variant int64, err error) {
  v := strings.SplitN( path_step, ":", 2 )
  if len(v) < 2 {
    err = fmt.Errorf("invalid key %s", path_step )
    return
  }
  var e error

  path,e = strconv.ParseInt( v[0], 16, 64 )
  if e!=nil {
    err = fmt.Errorf("invalid path %s", v[0])
    return
  }

  step,e = strconv.ParseInt( v[1], 16, 64 )
  if e!=nil {
    err = fmt.Errorf("invalid step %s", v[1])
    return
  }

  variant,e = strconv.ParseInt( inp_hex_variant, 16, 64 )
  if e!= nil {
    err = fmt.Errorf("invalid variant %s", inp_hex_variant)
    return
  }

  return

}

type TileRange struct {
  Range [2]int
  Permit bool
}

//func unpack_tile_list( TileVariantId []string ) ( map[string][][2]int, error ) {
func unpack_tile_list( TileVariantId []string ) ( map[string][]TileRange, error ) {

  max_elements := 2000000
  ele_count := 0

  //tileRange := make( map[string][][2]int )
  tileRanges := make( map[string][]TileRange )

  for i:=0; i<len(TileVariantId); i++ {

    tv_start := 0
    permit_flag := true

    if (len(TileVariantId[i])>0) && (TileVariantId[i][0] == '~') { tv_start = 1 ; permit_flag = false }

    psv := strings.SplitN( TileVariantId[i][tv_start:], ".", 5 )
    if len(psv) != 4 {
      return nil, fmt.Errorf("Invalid tile %s", TileVariantId[i] )
    }

    path_range,e := parseIntOption( psv[0], 16 )
    if e!=nil {
      return nil, fmt.Errorf("Invalid path in %s", TileVariantId[i] )
    }

    version_range,e := parseIntOption( psv[1], 16 ) ; _ = version_range
    if e!=nil {
      return nil, fmt.Errorf("Invalid version in %s", TileVariantId[i] )
    }

    step_range,e := parseIntOption( psv[2], 16 )
    if e!=nil {
      return nil, fmt.Errorf("Invalid step in %s", TileVariantId[i] )
    }

    variant_range,e := parseIntOption( psv[3], 16 )
    if e!=nil {
      return nil, fmt.Errorf("Invalid variant in %s", TileVariantId[i] )
    }

    max_path := 864

    for pg:=0; pg<len(path_range); pg++ {
      if path_range[pg][1] < 0 { path_range[pg][1] = int64(max_path) }

      for x:=path_range[pg][0]; x<path_range[pg][1]; x++ {
        str_hex_path := fmt.Sprintf( "%x", x )

        for sg:=0; sg<len(step_range); sg++ {

          beg_step := step_range[sg][0]
          n_step := int64(0)
          if step_range[sg][1] < 0 { n_step = int64(len( gCGF[0].ABV[str_hex_path] )) - beg_step
          } else { n_step = step_range[sg][1] - beg_step }

          if n_step < 0 { n_step=1 }

          for y:=beg_step; y<(beg_step + n_step); y++ {
            path_step := fmt.Sprintf("%x:%x", x, y)

            for vg:=0; vg<len(variant_range); vg++ {
              //tileRanges[path_step] = append( tileRanges[path_step], [2]int{ int(variant_range[vg][0]), int(variant_range[vg][1]) } )
              tileRanges[path_step] =
                append( tileRanges[path_step],
                TileRange{ Range : [2]int{ int(variant_range[vg][0]), int(variant_range[vg][1]) } , Permit: permit_flag } )
              ele_count++

              if ele_count >= max_elements {
                return nil, fmt.Errorf("max elements exceeded (max %d)", max_elements)
              }
            }
          }
        }
      }
    }
  }

  return tileRanges, nil
}

func exact_tile_class_match( w http.ResponseWriter, resp *LanternResponse, req *LanternRequest ) {
  resp.Type = "success"
  resp.Message = "testing exact-tile-class-match"

  res_count := make( map[string]int )

  n_data := 0

  for path_step := range req.VariantId {
    path,step,variant,e := convert_path_step_variant( path_step, req.VariantId[path_step] )
    if e!=nil {
      resp.Type = "error" ; resp.Message = fmt.Sprintf("%v", e)
      return
    }

    str_hex_path := fmt.Sprintf("%x", path)
    for i:=0; i<len(gCGF); i++ {
      if abv,ok := gCGF[i].ABV[str_hex_path] ; ok {

        if (step<0) || (step>=int64(len(abv))) { continue }
        tile_class_rank,e := gCGF[i].LookupABVTileMapVariant( int(path), int(step) )
        if e!=nil { continue }

        if int64(tile_class_rank) == variant {

          fmt.Printf(">> %d %d\n", tile_class_rank, variant )

          res_count[ gCGFName[i] ]++
        }

      } else {
        continue
      }
    }

    n_data++

  }

  if n_data==0 { return }

  res := []string{}

  for i:=0; i<len(gCGFName); i++ {

    if res_count[ gCGFName[i] ] == n_data {
      res = append( res, gCGFName[i] )
    }

  }

  w.Header().Set("Content-Type", "application/json")
  res_json_bytes,_ := json.Marshal( res )
  io.WriteString(w, string(res_json_bytes))

}

func getSampleIndexArray( sampleId []string ) ( sampleIndex []int, err error ) {

  if (len(sampleId)==0) {
    for i:=0; i<len(gCGF); i++ {
      sampleIndex = append(sampleIndex, i)
    }
  } else {
    for i:=0; i<len(sampleId); i++ {
      if v,ok := gCGFIndexMap[ sampleId[i] ] ; ok {
        sampleIndex = append(sampleIndex, v)
      } else {
        err = fmt.Errorf( "Could not find sampleId %s", sampleId[i] )
        return
      }
    }
  }

  return sampleIndex,nil

}

type FreqVariant struct {
  p float64
  v int
}

/*
type ByVal []FreqVariant

func (s ByVal) Len() int { return len(s) }
func (s ByVal) Swap(i,j int) { return s[i],s[j] = s[j],s[i] }
func (s ByVal) Less(i,j int) bool { return s[i].v < s[j].v }
*/

/*
func case_control( caseSampleIndex, controlSampleIndex []int, threshold float64 ) {
  casefreq := make( map[int][][]FreqVariant )
  controlfreq := make( map[int][][]FreqVariant )

  sample_ind0 := caseSampleIndex[0]
  for path_str,abv := range gCGF[sample_ind0].ABV {
    path_64,_ := strconv.ParseInt( path_str, 16, 64 )
    path := int(path_64)
    casefreq[path] = make( [][]FreqVariant, len(abv) )
    for i:=0; i<len(abv); i++ {
      var x int
      if (abv[i] == '#') || (abv[i] == '-') {
        x,_ = gCGF[sample_ind0].LookupABVTileMapVariant( path, i )
      } else if  abv[i] == '.' { x = 0
      } else if (abv[i] <= '9') && (abv[i] >= '0') { x = int(abv[i]-'0')
      } else if (abv[i] <= 'Z') && (abv[i] >= 'A') { x = int(abv[i]-'A')
      } else if (abv[i] <= 'z') && (abv[i] >= 'z') { x = int(abv[i]-'z') }
      casefreq[path][i] = append( casefreq[path][i], FreqVariant{ 1.0, x } )
    }
  }

  for c:=1; c<len(caseSampleIndex); c++ {
    sample_ind := caseSampleIndex[c]

    for path_str,abv := range gCGF[sample_ind].ABV {
      path_64,_ := strconv.ParseInt( path_str, 16, 64 )
      path := int(path_64)
      for i:=0; i<len(abv); i++ {
        var x int
        if (abv[i] == '#') || (abv[i] == '-') {
          x,_ = gCGF[sample_ind].LookupABVTileMapVariant( path, i )
        } else if  abv[i] == '.' { x = 0
        } else if (abv[i] <= '9') && (abv[i] >= '0') { x = int(abv[i]-'0')
        } else if (abv[i] <= 'Z') && (abv[i] >= 'A') { x = int(abv[i]-'A')
        } else if (abv[i] <= 'z') && (abv[i] >= 'z') { x = int(abv[i]-'z') }

        ll := len(casefreq[path][i])

        var k int
        for k=0; k<ll; k++ {
          if casefreq[path][i][k].v == x {
            casefreq[path][i][k].p += 1.0
            break
          }
        }
        if k==ll { casefreq[path][i] = append( casefreq[path][i], FreqVariant{ 1.0, x } ) }
      }
    }
  }

  // renormalize
  for _,freqvar := range casefreq {
    n := len(freqvar)
    for i:=0; i<n; i++ {
      s := 0.0
      for j:=0; j<len(freqvar[i]); j++ { s += freqvar[i][j].p }
      if s < 1.0 { s = 1.0 }
      for j:=0; j<len(freqvar[i]); j++ { freqvar[i][j].p /= s }
    }
  }


  sample_ind0 = controlSampleIndex[0]
  for path_str,abv := range gCGF[sample_ind0].ABV {
    path_64,_ := strconv.ParseInt( path_str, 16, 64 )
    path := int(path_64)
    controlfreq[path] = make( [][]FreqVariant, len(abv) )
    for i:=0; i<len(abv); i++ {
      var x int
      if (abv[i] == '#') || (abv[i] == '-') {
        x,_ = gCGF[sample_ind0].LookupABVTileMapVariant( path, i )
      } else if  abv[i] == '.' { x = 0
      } else if (abv[i] <= '9') && (abv[i] >= '0') { x = int(abv[i]-'0')
      } else if (abv[i] <= 'Z') && (abv[i] >= 'A') { x = int(abv[i]-'A')
      } else if (abv[i] <= 'z') && (abv[i] >= 'z') { x = int(abv[i]-'z') }
      controlfreq[path][i] = append( controlfreq[path][i], FreqVariant{ 1.0, x } )
    }
  }

  for c:=1; c<len(controlSampleIndex); c++ {
    sample_ind := controlSampleIndex[c]

    for path_str,abv := range gCGF[sample_ind].ABV {
      path_64,_ := strconv.ParseInt( path_str, 16, 64 )
      path := int(path_64)
      for i:=0; i<len(abv); i++ {
        var x int
        if (abv[i] == '#') || (abv[i] == '-') {
          x,_ = gCGF[sample_ind].LookupABVTileMapVariant( path, i )
        } else if  abv[i] == '.' { x = 0
        } else if (abv[i] <= '9') && (abv[i] >= '0') { x = int(abv[i]-'0')
        } else if (abv[i] <= 'Z') && (abv[i] >= 'A') { x = int(abv[i]-'A')
        } else if (abv[i] <= 'z') && (abv[i] >= 'z') { x = int(abv[i]-'z') }

        ll := len(controlfreq[path][i])

        var k int
        for k=0; k<ll; k++ {
          if controlfreq[path][i][k].v == x {
            controlfreq[path][i][k].p += 1.0
            break
          }
        }
        if k==ll { controlfreq[path][i] = append( controlfreq[path][i], FreqVariant{ 1.0, x } ) }
      }
    }
  }

  // renormalize
  for _,freqvar := range controlfreq {
    n := len(freqvar)
    for i:=0; i<n; i++ {
      s := 0.0
      for j:=0; j<len(freqvar[i]); j++ { s += freqvar[i][j].p }
      if s < 1.0 { s = 1.0 }
      for j:=0; j<len(freqvar[i]); j++ { freqvar[i][j].p /= s }
    }
  }

  for path,case_freqvar := range casefreq {
    control_freqvar,ok := controlfreq[path]
    if !ok { continue }

    n := len(case_freqvar)
    for i:=0; i<n; i++ {

      tm := map[int]float64{}
      for j:=0; j<len(case_freqvar[i]); j++ {
        tm[ case_freqvar[i][j].v ] = case_freqvar[i][j].p
      }

      if i>=len(control_freqvar) { break }

      //if control_freqvar[i] == nil { control_freqvar[i] = make( []FreqVariant, 0 ) }

      m := len(control_freqvar[i])
      if n < m { m = n }

      //for j:=0; j<len(control_freqvar[i]); j++ {
      for j:=0; j<m; j++ {
        if p,ok := tm[ control_freqvar[i][j].v ] ; ok {
          if (p - control_freqvar[i][j].p) >  threshold {
            fmt.Printf(">>>> %x.%x.%x %v (= %v - %v)\n",
              path, i, control_freqvar[i][j].v,
              p - control_freqvar[i][j].p,
              p, control_freqvar[i][j].p )
          }
        }
      }
    }
  }


}

func case_control_handler( w http.ResponseWriter, resp *LanternResponse, req *LanternRequest ) {
  resp.Type = "success"
  resp.Message = "testing tile-variant"


  caseSampleIndex,err := getSampleIndexArray( req.CaseSampleId )
  if err!=nil {
    resp.Type = "error" ; resp.Message = fmt.Sprintf("%v", err)
    return
  }

  controlSampleIndex,err := getSampleIndexArray( req.ControlSampleId )
  if err!=nil {
    resp.Type = "error" ; resp.Message = fmt.Sprintf("%v", err)
    return
  }

  case_control( caseSampleIndex, controlSampleIndex, 0.45 )

}

*/


/*
func sample_intersect( sampleIndex []int ) string {
  no_match := -5

  s0 := sampleIndex[0]
  //n := gCGF[s0].TotalStep

  v := make( map[string][]int )

  for path_str,abv := range gCGF[s0].ABV {
    m:=len(abv)
    v[path_str] = make( []int, m)

    path_64,_ := strconv.ParseInt( path_str, 16, 64 )
    path := int(path_64)

    for i:=0; i<m; i++ {

      if (abv[i] == '#') || (abv[i] == '-') {
        v[path_str][i],_ = gCGF[s0].LookupABVTileMapVariant( path, i )
        continue
      }

      if abv[i] == '.' { v[path_str][i] = 0
      } else if (abv[i] <= '9') && (abv[i] >= '0') { v[path_str][i] = int(abv[i]-'0')
      } else if (abv[i] <= 'Z') && (abv[i] >= 'A') { v[path_str][i] = int(abv[i]-'A')
      } else if (abv[i] <= 'z') && (abv[i] >= 'z') { v[path_str][i] = int(abv[i]-'z') }

    }

  }

  for s:=1; s<len(sampleIndex); s++ {
    sample_ind := sampleIndex[s]

    for path_str,abv := range gCGF[sample_ind].ABV {
      m:=len(abv)

      path_64,_ := strconv.ParseInt( path_str, 16, 64 )
      path := int(path_64)

      mm := m
      if mm > len(v[path_str]) { mm = len(v[path_str]) }

      //for i:=0; i<m; i++ {
      for i:=0; i<mm; i++ {
        if v[path_str][i] == no_match { continue }

        var x int

        if (abv[i] == '#') || (abv[i] == '-') {
          x,_ = gCGF[sample_ind].LookupABVTileMapVariant( path, i )
        } else if  abv[i] == '.' { x = 0
        } else if (abv[i] <= '9') && (abv[i] >= '0') { x = int(abv[i]-'0')
        } else if (abv[i] <= 'Z') && (abv[i] >= 'A') { x = int(abv[i]-'A')
        } else if (abv[i] <= 'z') && (abv[i] >= 'z') { x = int(abv[i]-'z') }

        if v[path_str][i] != x { v[path_str][i] = no_match }
      }
    }

  }

  ll := 0
  found_count := 0
  default_count := 0

  for path_str,_ := range v {

    fmt.Printf(" %s: [[", path_str)
    for i:=0; i<len(v[path_str]); i++  {
      if v[path_str][i] > 0 {
        fmt.Printf(" (%x.%d)", i, v[path_str][i])
        found_count++
      } else if v[path_str][i] == 0 {
        default_count++
      }
    }
    fmt.Printf(" ]]\n")

    ll += len(v[path_str])

  }

  fmt.Printf("  total: %d / %d, default %d / %d\n", found_count, ll, default_count, ll  )

  return fmt.Sprintf("{ \"Message\":\"total %d / %d, default %d / %d\" }", found_count, ll, default_count, ll )

}

*/

/*
func sample_intersect_handler( w http.ResponseWriter, resp *LanternResponse, req *LanternRequest ) {
  resp.Type = "success"
  resp.Message = "testing tile-variant"


  sampleIndex,err := getSampleIndexArray( req.SampleId )
  _ = sampleIndex
  if err!=nil {
    resp.Type = "error" ; resp.Message = fmt.Sprintf("%v", err)
    return
  }

  str := sample_intersect( sampleIndex )

  w.Header().Set("Content-Type", "application/json")
  //res_json_bytes,_ := json.Marshal( nameList )
  io.WriteString( w, str )

}
*/

func tile_variant( sampleIndex []int, tilePosition [][2]int) ( map[string]map[string]int, error ) {
  var err error

  res := make( map[string]map[string]int )

  for s:=0; s<len(sampleIndex); s++ {
    ind := sampleIndex[s]
    name := gCGFName[ind]

    res[name] = make( map[string]int )

    for p:=0; p<len(tilePosition); p++ {
      path := tilePosition[p][0]
      step := tilePosition[p][1]

      path_step := fmt.Sprintf( "%x:%x", path, step )

      res[name][ path_step ],err = gCGF[ind].LookupABVTileMapVariant( path, step )
      if err!=nil { return nil, err }
    }
  }

  return res, nil
}

func tile_variant_handler( w http.ResponseWriter, resp *LanternResponse, req *LanternRequest ) {
  resp.Type = "success"
  resp.Message = "testing tile-variant"


  sampleIndex,err := getSampleIndexArray( req.SampleId )
  _ = sampleIndex
  if err!=nil {
    resp.Type = "error" ; resp.Message = fmt.Sprintf("%v", err)
    return
  }



  max_elements := 2000
  ele_count := 0

  tilePosition := [][2]int{}

  // Unpack TileIds
  //
  for i:=0; i<len(req.TileId); i++ {
    psv := strings.SplitN( req.TileId[i], ".", 4 )
    if len(psv) != 2 {
      resp.Type = "error" ; resp.Message = fmt.Sprintf("Invalid TileId %s", req.TileId[i] )
      return
    }

    path_range,e := parseIntOption( psv[0], 16 )
    if e!=nil {
      resp.Type = "error" ; resp.Message = fmt.Sprintf("Invalid path in TileId %s", req.TileId[i] )
      return
    }

    step_range,e := parseIntOption( psv[1], 16 )
    if e!=nil {
      resp.Type = "error" ; resp.Message = fmt.Sprintf("Invalid path in TileId %s", req.TileId[i] )
      return
    }

    max_path := 864

    for pg:=0; pg<len(path_range); pg++ {
      if path_range[pg][1] < 0 { path_range[pg][1] = int64(max_path) }

      for x:=path_range[pg][0]; x<path_range[pg][1]; x++ {
        str_hex_path := fmt.Sprintf( "%x", x )

        for sg:=0; sg<len(step_range); sg++ {

          beg_step := step_range[sg][0]
          n_step := int64(0)
          if step_range[sg][1] < 0 { n_step = int64(len( gCGF[0].ABV[str_hex_path] )) - beg_step
          } else { n_step = step_range[sg][1] - beg_step }

          if n_step < 0 { n_step=1 }

          for y:=beg_step; y<(beg_step + n_step); y++ {
            ele_count++
            if ele_count >= max_elements {
              resp.Type = "error" ; resp.Message = fmt.Sprintf("max elements exceeded (max %d)", max_elements)
              return
            }

            tilePosition = append( tilePosition, [2]int{ int(x), int(y) } )
          }
        }
      }
    }
  }

  fmt.Printf("tilePosition>> %v\n", tilePosition )

  ans,err := tile_variant( sampleIndex, tilePosition )
  if err!=nil { fmt.Printf(">>>error\n") }

  w.Header().Set("Content-Type", "application/json")
  res_json_bytes,_ := json.Marshal( ans )
  io.WriteString(w, string(res_json_bytes))

}

//-------------------------------------------------------------------------------------------------
//   ___  __ _ _ __ ___  _ __ | | ___      | |_(_) | ___     __   ____ _ _ __(_) __ _ _ __ | |_   .
//  / __|/ _` | '_ ` _ \| '_ \| |/ _ \_____| __| | |/ _ \____\ \ / / _` | '__| |/ _` | '_ \| __|  .
//  \__ \ (_| | | | | | | |_) | |  __/_____| |_| | |  __/_____\ V / (_| | |  | | (_| | | | | |_   .
//  |___/\__,_|_| |_| |_| .__/|_|\___|      \__|_|_|\___|      \_/ \__,_|_|  |_|\__,_|_| |_|\__|  .
//                      |_|                                                                       .
//-------------------------------------------------------------------------------------------------


/*
func sample_tile_variant_handler( w http.ResponseWriter, resp *LanternResponse, req *LanternRequest ) {
  resp.Type = "success"
  resp.Message = "testing sample-tile-variant"

  sampleIndex,err := getSampleIndexArray( req.SampleId )
  if err!=nil {
    resp.Type = "error" ; resp.Message = fmt.Sprintf("%v", err)
    return
  }

  resSampleVariant, err := sample_tile_variant( sampleIndex, req.PathStep )
  if err!=nil {
    resp.Type = "error" ; resp.Message = fmt.Sprintf("%v", err)
    return
  }

  sample_var_map := make( map[string][]string )

  for i := range resSampleVariant {
    sampleName := gCGFName[ i ]
    sample_var_map[ sampleName ] = resSampleVariant[i]
  }

  fmt.Printf("got: %v --> %v", resSampleVariant, sample_var_map )

  w.Header().Set("Content-Type", "application/json")
  res_json_bytes,_ := json.Marshal( sample_var_map )
  io.WriteString(w, string(res_json_bytes))

}


func sample_tile_variant( sampleIndex []int, pathStep []string ) (resSampleVariant map[int][]string, err error)  {
  resSampleVariant = make( map[int]string )

  for spos:=0; spos<len(sampleIndex); spos++ {
    cgf_ind := sampleIndex[spos]

    path,step,e := convert_path_step( pathStep )
    if e!=nil { return nil, e }

    tile_variant := gCGF[cgf_ind].GetTileIds( int(path), int(step) )

    s_path, s_step, s_class, e := gCGF[cgf_ind].LookupABVStartTileMap( int(path), int(step) )
    if e!=nil { return nil, e }

    tile_class := gTileMap[ s_class ]

    resSampleVariant[spos] = [][]string{}
    if gCGF[cgf_ind].ABVTileMapVariantVariableLength( int(path), int(step) ) {
      continue
    }

    tile_class,e := gCGF[cgf_ind].LookupABVTileMapVariant( int(path), int(step) )
    if e!=nil { return nil, e }

    tile_class,ok := gTileMap[tile_class_rank]
    if !ok {  continue }

    for i:=0; i<len(tile_class); i++ {
      resSampleVariant[spos] = append( resSampleVariant[spos], fmt.Sprintf("%x.%x.%x.%x", path, 0, step, tile_class[i]) )
    }

  }

  return resSampleVariant, nil

}
*/


//-------------------------------------------------------------------------------------------
// __   ____ _ _ __(_) __ _ _ __ | |_      / _|_ __ ___  __ _ _   _  ___ _ __   ___ _   _   .
// \ \ / / _` | '__| |/ _` | '_ \| __|____| |_| '__/ _ \/ _` | | | |/ _ \ '_ \ / __| | | |  .
//  \ V / (_| | |  | | (_| | | | | ||_____|  _| | |  __/ (_| | |_| |  __/ | | | (__| |_| |  .
//   \_/ \__,_|_|  |_|\__,_|_| |_|\__|    |_| |_|  \___|\__, |\__,_|\___|_| |_|\___|\__, |  .
//                                                         |_|                      |___/   .
//-------------------------------------------------------------------------------------------

func variant_frequency_handler( w http.ResponseWriter, resp *LanternResponse, req *LanternRequest ) {
  resp.Type = "success"
  resp.Message = "testing sample-tile-group-match"

  sampleIndex,err := getSampleIndexArray( req.SampleId )
  if err!=nil {
    resp.Type = "error" ; resp.Message = fmt.Sprintf("%v", err)
    return
  }

  //tileGroupRange := make( []map[string][][2]int, 0, 8 )
  tileGroupRange := make( []map[string][]TileRange, 0, 8 )

  // Unpack TileVariantIds
  //
  for g:=0; g<len(req.TileGroupVariantId); g++ {

    tileRange,e := unpack_tile_list( req.TileGroupVariantId[g] )
    if e!=nil {
      resp.Type = "error" ; resp.Message = fmt.Sprintf("%v", e)
      return
    }

    tileGroupRange = append( tileGroupRange, tileRange )

  }

  resSample, err := sample_tile_group_match( sampleIndex, tileGroupRange )
  if err!=nil {
    resp.Type = "error" ; resp.Message = fmt.Sprintf("%v", err)
    return
  }

  nameList := []string{}
  for i:=0; i<len(resSample); i++ {
    nameList = append(nameList, gCGFName[ resSample[i] ] )
  }

  fmt.Printf("got: %v --> %v", resSample, nameList)

  w.Header().Set("Content-Type", "application/json")
  res_json_bytes,_ := json.Marshal( nameList )
  io.WriteString(w, string(res_json_bytes))


}

func variant_frequency( sampleIndex []int,
                        tileGroupVariantRange []map[string][][2]int ) (tileVariantFrequncy map[string]map[string]int, err error)  {
  return nil, nil
}


func sample_match( w http.ResponseWriter, resp *LanternResponse, req *LanternRequest ) {
  resp.Type = "success"
  resp.Message = "testing sample-match"
}

func tile_class( w http.ResponseWriter, resp *LanternResponse, req *LanternRequest ) {
  resp.Type = "success"
  resp.Message = "tile-class"

  w.Header().Set("Content-Type", "application/json")
  res,_ := json.Marshal( gCGF[0].TileMap )
  io.WriteString(w, string(res))
}

func handle_json_req( w http.ResponseWriter, r *http.Request ) {

  c := <-g_incr
  go func() { g_incr <- c+1 }()

  var body_reader io.Reader = r.Body

  req := LanternRequest{}

  dec := json.NewDecoder( body_reader )
  e := dec.Decode( &req )
  if e!=nil {
    send_error_bad_request( fmt.Sprintf("[%d] bad parse %v\n", c, e), w )
    return
  }

  resp := LanternResponse{ Type:"error", Message:"invalid command" }

  switch req.Type {

  //*
  case "sample-tile-group-match":
    sample_tile_group_match_handler( w, &resp, &req )

  //*
  case "tile-sequence":
    tile_sequence_handler( w, &resp, &req )

  //*
  case "tile-sequence-tracer":
    tile_sequence_handler_tracer( w, &resp, &req )

  //*
  case "system-info":
    system_info_handler( w, &resp, &req )

  //*
  case "sample-position-variant":
    sample_position_variant_handler( w, &resp, &req )

  case "tile-variant":
    tile_variant_handler( w, &resp, &req )
  case "sample-intersect":
    sample_intersect_handler( w, &resp, &req )

  //*
  case "sample-tile-neighborhood":
    sample_tile_neighborhood_handler( w, &resp, &req )

  //case "case-control":
  //  case_control_handler( w, &resp, &req )

    /*
  case "exact-tile-match":
    exact_tile_match( w, &resp, &req )
  case "exact-tile-class-match":
    exact_tile_class_match( w, &resp, &req )
  case "sample-match":
    sample_match( w, &resp, &req )
  case "tile-class":
    tile_class( w, &resp, &req )
    */

  default:
    io.WriteString(w, "{\n")
    io.WriteString(w, "  \"Type\":\"error\", \"Message\":\"bad command\"\n")
    io.WriteString(w, "}")
  }


  fmt.Printf(" content-type: %s\n", r.Header.Get("Content-Type") )

  fmt.Println("\n--------\n")
  //fmt.Println( req )
  fmt.Println("\n--------\n\n")

  /*
  w.Header().Set("Content-Type", "application/json")
  res,_ := json.Marshal( resp )
  io.WriteString(w, string(res))
  */

}


func _main( c *cli.Context ) {

  g_incr = make( chan int )
  go func() { g_incr <- 0 }()

  gCGFIndexMap = make( map[string]int )

  g_verboseFlag   = c.Bool("Verbose")
  gProfileFlag    = c.Bool("pprof")
  gMemProfileFlag = c.Bool("mprof")

  if gProfileFlag {
    prof_f,err := os.Create( gProfileFile )
    if err != nil {
      fmt.Fprintf( os.Stderr, "Could not open profile file %s: %v\n", gProfileFile, err )
      os.Exit(2)
    }

    pprof.StartCPUProfile( prof_f )
    defer pprof.StopCPUProfile()
  }

  z := c.StringSlice("input-cgf")

  if len(z)==0 {
    fmt.Fprintf( os.Stderr, "Provide input-cgf file(s)\n" )
    cli.ShowAppHelp(c)
    os.Exit(1)
  }

  e := TileSimpleInit()
  if e!=nil {
    fmt.Fprintf( os.Stderr, "TileSimpleInit failed %v\n", e )
    os.Exit(1)
  }


  cg,e := cgf.Load( z[0] )
  if e != nil {
    fmt.Fprintf( os.Stderr, "ERROR: could not load %s: %v\n", z[0], e )
    os.Exit(1)
  }

  sampleName := fmt.Sprintf("%d:%s", 0, z[0])

  gCGF = append( gCGF, cg )
  gCGFName = append( gCGFName, sampleName )
  gCGFIndexMap[ sampleName ] = len(gCGF)-1

  gTileClassVersion = cg.EncodedTileMapMd5Sum
  gTileLibraryVersion = cg.TileLibraryVersion

  construct_tile_map( gCGF[0].TileMap )
  construct_tile_variant_to_tile_class_map( gCGF[0].TileMap )

  for i:=1; i<len(z); i++ {
    fmt.Println(z[i])

    //cg,e := cgf.Load( z[i] )
    cg,e := cgf.LoadNoMap( z[i] )
    if e != nil {
      fmt.Fprintf( os.Stderr, "ERROR: could not load %s: %v\n", z[i], e )
      os.Exit(1)
    }

    if cg.EncodedTileMapMd5Sum != gTileClassVersion {
      fmt.Fprintf( os.Stderr, "ERROR: Could not load %s: Tile class mismatch (%s != %s)\n", z[i], cg.EncodedTileMapMd5Sum, gTileClassVersion )
      os.Exit(1)
    }

    if cg.TileLibraryVersion != gTileLibraryVersion {
      fmt.Fprintf( os.Stderr, "ERROR: Could not load %s: Tile library mismatch (%s != %s)\n", z[i], cg.TileLibraryVersion , gTileLibraryVersion )
      os.Exit(1)
    }

    sampleName := fmt.Sprintf("%d:%s", i, z[i])

    cg.TileMap = gCGF[0].TileMap

    gCGF = append( gCGF, cg )
    gCGFName = append( gCGFName, sampleName )
    gCGFIndexMap[ sampleName ] = len(gCGF)-1

  }


  z = c.StringSlice("input-cgf-gob")
  for i:=0; i<len(z); i++ {
    fmt.Println(z[i])

    cg := cgf.CGF{}
    fp,e := os.Open( z[i] )
    if e!=nil { panic(e) }

    dec := gob.NewDecoder( fp )
    e = dec.Decode(&cg)
    if e!=nil { panic(e) }

    fp.Close()

    if cg.EncodedTileMapMd5Sum != gTileClassVersion {
      fmt.Fprintf( os.Stderr, "ERROR: Could not load %s: Tile class mismatch (%s != %s)\n", z[i], cg.EncodedTileMapMd5Sum, gTileClassVersion )
      os.Exit(1)
    }

    if cg.TileLibraryVersion != gTileLibraryVersion {
      fmt.Fprintf( os.Stderr, "ERROR: Could not load %s: Tile library mismatch (%s != %s)\n", z[i], cg.TileLibraryVersion , gTileLibraryVersion )
      os.Exit(1)
    }

    sampleName := fmt.Sprintf("%d:%s", i, z[i])

    cg.TileMap = gCGF[0].TileMap

    gCGF = append( gCGF, &cg )
    gCGFName = append( gCGFName, sampleName )
    gCGFIndexMap[ sampleName ] = len(gCGF)-1

  }


  fmt.Printf("indexmap:\n\n%v\n\n", gCGFIndexMap)

  listener,err := net.Listen("tcp", gPortStr )
  if err!=nil {
    fmt.Fprintf( os.Stderr, "net.Listen%s: %v", gPortStr, err )
    os.Exit(1)
  }

  term := make(chan os.Signal, 1)
  go func( sig <-chan os.Signal) {
    s:= <-sig
    fmt.Println("caught signal:", s)
    listener.Close()
  }(term)
  signal.Notify(term, syscall.SIGTERM)

  if c.Bool( "Test" ) {
    flint()
    return
  }


  http.HandleFunc("/", handle_json_req)

  srv := &http.Server{ Addr: gPortStr }

  fmt.Printf(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>\n")

  srv.Serve(listener)

  fmt.Printf("lantern finished, shutting down\n")


}

func main() {
  app := cli.NewApp()
  app.Name  = "lantern"
  app.Usage = "Lantern server"
  app.Version = VERSION_STR
  app.Author = "Curoverse Inc."
  app.Email = "info@curoverse.com"
  app.Action = func( c *cli.Context ) { _main(c) }

  app.Flags = []cli.Flag{

    cli.StringSliceFlag{
      Name: "input-cgf, i",
      Value: &cli.StringSlice{},
      Usage: "CGF file(s)",
    },

    cli.StringSliceFlag{
      Name: "input-cgf-gob, g",
      Value: &cli.StringSlice{},
      Usage: "CGF gob file(s)",
    },

    cli.BoolFlag{
      Name: "Test, T",
      Usage: "Run tests (for debugging purposes)",
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
