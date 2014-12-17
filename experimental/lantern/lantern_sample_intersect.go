package main

import "io"
import "fmt"
import "strconv"
import "net/http"

func sample_intersect( sampleIndex []int ) string {
  no_match := -5

  s0 := sampleIndex[0]

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

