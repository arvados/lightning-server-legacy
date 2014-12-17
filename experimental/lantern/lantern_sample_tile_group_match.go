package main

import "io"
import "fmt"
import "net/http"
import "encoding/json"



//----------------------------------------------------------------------------------------------------------------------------------
//                             _            _   _ _                                                              _       _         .
//   ___  __ _ _ __ ___  _ __ | | ___      | |_(_) | ___        __ _ _ __ ___  _   _ _ __        _ __ ___   __ _| |_ ___| |__      .
//  / __|/ _` | '_ ` _ \| '_ \| |/ _ \_____| __| | |/ _ \_____ / _` | '__/ _ \| | | | '_ \ _____| '_ ` _ \ / _` | __/ __| '_ \     .
//  \__ \ (_| | | | | | | |_) | |  __/_____| |_| | |  __/_____| (_| | | | (_) | |_| | |_) |_____| | | | | | (_| | || (__| | | |    .
//  |___/\__,_|_| |_| |_| .__/|_|\___|      \__|_|_|\___|      \__, |_|  \___/ \__,_| .__/      |_| |_| |_|\__,_|\__\___|_| |_|    .
//                      |_|                                    |___/                |_|                                            .
//----------------------------------------------------------------------------------------------------------------------------------

func sample_tile_group_match_handler( w http.ResponseWriter, resp *LanternResponse, req *LanternRequest ) {

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


  //DEBUG
  fmt.Printf(">>> sampleIndex %v\n", sampleIndex )

  for g:=0; g<len(tileGroupRange); g++ {
    tileRange := tileGroupRange[g]
    for k,v := range tileRange {
      fmt.Printf("...>>> [%d] tileRange %v %v\n", g, k, v)
    }
  }


  resSample, err := sample_tile_group_match( sampleIndex, tileGroupRange )

  if err!=nil {
    w.Header().Set("Content-Type", "application/json")
    io.WriteString(w, "{\n")
    io.WriteString(w, "  \"Type\":\"success\", \"Message\":\"sample-tile-group-match\" \n")
    io.WriteString(w, "}")

    return
  }

  nameList := []string{}
  for i:=0; i<len(resSample); i++ {
    nameList = append(nameList, gCGFName[ resSample[i] ] )
  }

/*
  fmt.Printf("got: %v --> %v", resSample, nameList)

  w.Header().Set("Content-Type", "application/json")
  res_json_bytes,_ := json.Marshal( nameList )
  io.WriteString(w, string(res_json_bytes))
*/


  w.Header().Set("Content-Type", "application/json")
  //res_json_bytes,_ := json.Marshal( resSample )
  res_json_bytes,_ := json.Marshal( nameList )
  tile_range_bytes,_ := json.Marshal( tileGroupRange )

  io.WriteString(w, "{\n")
  io.WriteString(w, "  \"Type\":\"success\", \"Message\":\"sample-tile-group-match\",\n")

  io.WriteString(w, "  \"TileGroupVariantId\":")
  io.WriteString(w, string(tile_range_bytes))
  io.WriteString(w, ",\n")

  io.WriteString(w, "  \"Result\":")
  io.WriteString(w, string(res_json_bytes))
  io.WriteString(w, "\n")
  io.WriteString(w, "}")


}

// Give a list of sample results from the tileGroupVariantRange
//
// Each 'group' is referenced by the slice position.  For a sample
// to be returned, the sample must have at least one tile
// variant in each group.
//
// Queries are of the form:
//
//    ( variant_range_{0,0} OR variant_range_{0,1} OR variant_range_{0,2} ... OR variant_range_{0,m_0-1} )
//      AND
//    ( variant_range_{1,0} OR variant_range_{1,1} OR variant_range_{1,2} ... OR variant_range_{1,m_1-1} )
//      AND
//      ...
//      AND
//    ( variant_range_{n-1,0} OR variant_range_{n-1,1} OR variant_range_{n-1,2} ... OR variant_range_{n-1,m_{n-1}-1} )
//
//
// For example, to get back smaples that have any of the variants "247.0.2.0" to "247.0.2.e", this would be the query:
// [ [ "247.0.2.0+f" ] ]
//
// To get back all samples that have "247.0.2.0" AND "247.0.3.1", this would be the query:
// [ [ "247.0.2.0" ], [ "247.0.3.1" ] ]
//

func sample_tile_group_match( sampleIndex []int, tileGroupVariantRange []map[string][]TileRange ) (resSample []int, err error)  {

  n_group := len(tileGroupVariantRange)
  res_count := make( []int, len(sampleIndex) )

  for spos:=0; spos<len(sampleIndex); spos++ {
    cgf_ind := sampleIndex[spos]

    variant_so_far := 0

    for g:=0; g<n_group; g++ {

      if variant_so_far != g { break }
      match_flag := false

      for path_step,variantRange := range tileGroupVariantRange[g] {
        path,step,e := convert_path_step( path_step )
        if e!=nil { err = fmt.Errorf("%v", e) ; return }

        str_hex_path := fmt.Sprintf("%x", path)
        abv,abv_ok := gCGF[cgf_ind].ABV[str_hex_path]
        if !abv_ok { continue }
        if (step<0) || (step>=int64(len(abv))) { continue }

        for vpos:=0; vpos<len(variantRange); vpos++ {

          for tile_variant:=variantRange[vpos].Range[0]; tile_variant<variantRange[vpos].Range[1]; tile_variant++ {

            if gCGF[cgf_ind].HasTileVariant( int(path), int(step), tile_variant ) == variantRange[vpos].Permit {
              match_flag = true
              variant_so_far++
              res_count[ spos ]++
            }
          }

          if match_flag { break }

        }

        if match_flag { break }


      }

    }

  }

  for spos:=0; spos<len(sampleIndex); spos++ {

    fmt.Printf("sample_tile_match>>> res_count[%d]:%d\n", spos, res_count[spos] )

    if res_count[spos] == n_group {
      resSample = append( resSample, sampleIndex[spos] )
    }
  }

  return resSample, nil

}


