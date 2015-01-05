package main

import "fmt"
import "net/http"
import "encoding/json"
import _ "os"
import "io"

import "sort"

import "strings"
import "strconv"


/*

The function should answer queries of the form:

"Give me all neighboring tiles for each sample that has this variant."

TileId consists of an array of array objects, where each object
consistes of a TileId (range)  and an array of beginning and end
indexes.  The last index is non-inclusive.

Similar to the sample-tile-group-match, results are returned
only if there was at least one match from each group.  All
matched elements in each group are returned.

Example request:

{
  "Type":"sample-tile-neighborhood",
  "Message" : "sample query",
  "Dataset" : "all",
  "SampleId" : [
    "0:/scratch/pgp174.gff/hu011C57/chr13_chr17.abv/hu011C57_chr13_chr17.reported.cgf",
    "1:/scratch/pgp174.gff/hu016B28/chr13_chr17.abv/hu016B28_chr13_chr17.reported.cgf"
  ],
  "TileId" : [[
    { "247.00.000b.000f" : [-1, 1] },
    { "247.00.000b.00f3" : [ 0, 2] },
    { "247.00.000f.0001" : [ 0, 3] }
  ]]
}

Example response (not real data):

{
  "Type":"success",
  "Message" : "sample-tile-neighborhood",
  "Result" : {
    "0:/scratch/pgp174.gff/hu011C57/chr13_chr17.abv/hu011C57_chr13_chr17.reported.cgf" : [
       "247.00.00fb.0001", "247.00.00f3.0002"
    ],
    "1:/scratch/pgp174.gff/hu016B28/chr13_chr17.abv/hu016B28_chr13_chr17.reported.cgf" : [
      "247.00.000c.0002", "247.00.000b.000f",
      "247.00.000f.0001", "247.00.0010.0003" "247.00.0011.0005"
    ]
  }
}

*/

func parseInt4( dotstr4 string, base int ) (a,b,c,d int64, e error) {
  parts := strings.SplitN(dotstr4, ".", 5)
  if len(parts)!=4 { e = fmt.Errorf("len(%d) != 4", len(parts)) ; return }

  a,e = strconv.ParseInt( parts[0], base, 64 )
  if e!=nil { return }

  b,e = strconv.ParseInt( parts[1], base, 64 )
  if e!=nil { return }

  c,e = strconv.ParseInt( parts[2], base, 64 )
  if e!=nil { return }

  d,e = strconv.ParseInt( parts[3], base, 64 )
  if e!=nil { return }

  return

}

func parseBoolInt4( dotstr4 string, base int ) (permit_flag bool,a,b,c,d int64, e error) {
  parts := strings.SplitN(dotstr4, ".", 5)
  if len(parts)!=4 { e = fmt.Errorf("len(%d) != 4", len(parts)) ; return }

  p_str_start := 0
  permit_flag = true
  if len(parts[0]) == 0 { e = fmt.Errorf("len(a) == 0 ") ; return }
  if parts[0][0] == '~' { p_str_start = 1 ; permit_flag = false }

  //a,e = strconv.ParseInt( parts[0], base, 64 )
  a,e = strconv.ParseInt( parts[0][p_str_start:], base, 64 )
  if e!=nil { return }

  b,e = strconv.ParseInt( parts[1], base, 64 )
  if e!=nil { return }

  c,e = strconv.ParseInt( parts[2], base, 64 )
  if e!=nil { return }

  d,e = strconv.ParseInt( parts[3], base, 64 )
  if e!=nil { return }

  return

}


// cnf holds a list of clauses, where each clause is a tile id and a range.  The range is to
// construct the resulting neighborhood.

func find_tile_match_set( cgf_ind int, cnf []map[string][2]int ) ( matchTile map[string]bool, resInterval map[string][2]int, err error ) {
  ABV := gCGF[cgf_ind].ABV

  still_matching := true

  matchTile   = make( map[string]bool )
  resInterval = make( map[string][2]int )

  err = nil

  for c:=0; c<len(cnf); c++ {
    if !still_matching { return nil, nil, nil }

    // Examine the clause.
    // collect all matching tiles.

    still_matching = false
    //for tileId,neighborhoodRange := range cnf[c] {
    for tileId,_ := range cnf[c] {
      permit_flag,path,ver,step,variant,e := parseBoolInt4( tileId, 16 )
      if e!=nil { return nil, nil, e }

      permit_ch := ""
      if !permit_flag { permit_ch = "~" }

      //DEBUG
      fmt.Printf("  tileId %v, path %v, ver %v, step %v, variant %v, e %v\n",
        tileId, path, ver, step, variant, e)

      str_hex_path := fmt.Sprintf("%x", path)
      abv,abv_ok := ABV[str_hex_path]
      if !abv_ok { continue }
      if (step<0) || (step>=int64(len(abv))) { continue }

      //if gCGF[cgf_ind].HasTileVariant( int(path), int(step), int(variant) ) {
      if gCGF[cgf_ind].HasTileVariant( int(path), int(step), int(variant) ) == permit_flag {
        still_matching = true

        //matchedTileId := fmt.Sprintf("%03x.%02x.%04x.%04x", path,ver,step,variant)
        matchedTileId := fmt.Sprintf("%s%03x.%02x.%04x.%04x", permit_ch, path,ver,step,variant)
        matchTile[ matchedTileId ] = true
        resInterval[ matchedTileId ] = [2]int{ cnf[c][tileId][0], cnf[c][tileId][1] }
        continue
      }

      /*

      tile_class_rank,e := gCGF[cgf_ind].LookupABVTileMapVariant( int(path), int(step) )
      if e!=nil { continue }
      if !tile_variant_in_class( int(variant), tile_class_rank ) { continue }

      still_matching = true
      for res_variant := (variant + int64(neighborhoodRange[0])) ; res_variant < (variant + int64(neighborhoodRange[1])); res_variant++ {
        if (res_variant < 0) || (res_variant >= int64(len(abv)))  { continue }
        matchedTileId := fmt.Sprintf("%03x.%02x.%04x.%04x", path,ver,step,res_variant)

        matchTile[ matchedTileId ] = true
        resInterval[ matchedTileId ] = [2]int{ cnf[c][tileId][0], cnf[c][tileId][1] }
      }

      */

    }
  }

  if !still_matching { return nil,nil,nil }

  return

}

func _add_tile_from_ranges( permit_flag bool, tileList []string, a, b, c, d [2]int64 ) ( []string ) {
  permit_ch := ""
  if !permit_flag { permit_ch = "~" }

  for w:=a[0] ; w<a[1]; w++ {
    for x:=b[0] ; x<b[1] ; x++ {
      for y:=c[0] ; y<c[1] ; y++ {
        for z:=d[0] ; z<d[1] ; z++ {
          //tileList = append( tileList, fmt.Sprintf("%03x.%02x.%04x.%04x", w, x, y, z) )
          tileList = append( tileList, fmt.Sprintf("%s%03x.%02x.%04x.%04x", permit_ch, w, x, y, z) )
        }
      }
    }
  }

  return tileList
}

func unpack_tileid_range_into_tile_list( tileIdRange string ) ( tileList []string, err error ) {

  err = nil

  psv := strings.SplitN( tileIdRange, ".", 5 )
  if len(psv) != 4 {
    return nil, fmt.Errorf("Invalid tile %s", tileIdRange )
  }

  if len(psv[0]) == 0 { return nil, fmt.Errorf("Invalid path (0 length)") }
  path_str_start := 0 ; permit_flag := true
  if psv[0][0]=='~' { path_str_start=1 ; permit_flag = false }

  //path_range,e := parseIntOption( psv[0], 16 )
  path_range,e := parseIntOption( psv[0][path_str_start:], 16 )
  if e!=nil {
    return nil, fmt.Errorf("Invalid path in %s", tileIdRange )
  }

  version_range,e := parseIntOption( psv[1], 16 ) ; _ = version_range
  if e!=nil {
    return nil, fmt.Errorf("Invalid version in %s", tileIdRange )
  }

  step_range,e := parseIntOption( psv[2], 16 )
  if e!=nil {
    return nil, fmt.Errorf("Invalid step in %s", tileIdRange )
  }

  variant_range,e := parseIntOption( psv[3], 16 )
  if e!=nil {
    return nil, fmt.Errorf("Invalid variant in %s", tileIdRange )
  }

  for i:=0 ; i < len(path_range); i++ {
    if path_range[i][1] == -1 { path_range[i][1] = path_range[i][0]+1 }
  }

  for i:=0 ; i < len(version_range); i++ {
    if version_range[i][1] == -1 { version_range[i][1] = version_range[i][0]+1 }
  }

  for i:=0 ; i < len(step_range); i++ {
    if step_range[i][1] == -1 { step_range[i][1] = step_range[i][0]+1 }
  }

  for i:=0 ; i < len(variant_range); i++ {
    if variant_range[i][1] == -1 { variant_range[i][1] = variant_range[i][0]+1 }
  }

  for i0:=0; i0<len(path_range); i0++ {
    for i1:=0; i1<len(version_range); i1++ {
      for i2:=0; i2<len(step_range); i2++ {
        for i3:=0; i3<len(variant_range); i3++  {
          tileList = _add_tile_from_ranges( permit_flag, tileList, path_range[i0], version_range[i1], step_range[i2], variant_range[i3] )
        }
      }
    }
  }

  return

}

func construct_result_set( cgf_ind int, base_set map[string][2]int ) ( []map[string]bool ) {
  //result_set := make( map[string]bool )
  result_set := make( []map[string]bool, 0, 2)
  init := false

  for tileid,interval := range base_set {
    _ = interval

    //path,ver,begin_step,variant,e := parseInt4( tileid, 16 )
    permit_flag,path,ver,begin_step,variant,e := parseBoolInt4( tileid, 16 )
    if e!=nil { continue }
    _ = variant

    permit_ch := ""
    if !permit_flag { permit_ch = "~" }
    _ = permit_ch
    _ = permit_flag

    for step:=(begin_step+int64(interval[0])) ; step<(begin_step+int64(interval[1])); step++ {

      p,s,tmv,e := gCGF[cgf_ind].LookupABVStartTileMapVariant( int(path), int(step) )
      if e!=nil { continue }

      tme := gCGF[0].TileMap[tmv]
      for i:=0; i<len(tme.Variant); i++ {

        if !init {

          for ii:=0; ii<len(tme.Variant); ii++ {
            mm := make( map[string]bool )
            result_set = append( result_set, mm )
          }
          init = true
        }

        x:=0
        for j:=0; j<len(tme.Variant[i]); j++ {
          if (p==int(path)) && ((s+x)==int(step)) {

            len_opt_str := ""
            if tme.VariantLength[i][j] > 1 {
              len_opt_str = fmt.Sprintf("+%x", tme.VariantLength[i][j])
            }
            result_tileid := fmt.Sprintf("%03x.%02x.%04x.%04x%s", p, ver, s+x, tme.Variant[i][j], len_opt_str )
            //result_set[ result_tileid ] = true
            result_set[i][result_tileid] = true
            break
          }
          x += tme.VariantLength[i][j]
        }
      }

      /*
      tile_class_rank,e := gCGF[cgf_ind].LookupABVTileMapVariant( int(path), int(step) )
      if e!=nil { continue }
      if tile_class_rank >= 0 {
        result_tileid := fmt.Sprintf("%03x.%02x.%04x.%04x", path, ver, step, tile_class_rank)
        //result_tileid := fmt.Sprintf("%s%03x.%02x.%04x.%04x", permit_ch, path, ver, step, tile_class_rank)
        result_set[ result_tileid ] = true
      }
      */

    }

    /*
    for p:=(variant+int64(interval[0])); p<(variant+int64(interval[1])); p++ {
      if p<0 { continue }

      tile_class_rank,e := gCGF[cgf_ind].LookupABVTileMapVariant( int(path), int(step) )
      if e!=nil { continue }
      if tile_variant_in_class( int(variant), tile_class_rank ) {
        result_tileid := fmt.Sprintf("%03x.%02x.%04x.%04x", path, ver, step, p)
        result_set[ result_tileid ] = true
      }

    }
    */

  }

  return result_set

}


func sample_tile_neighborhood_handler( w http.ResponseWriter, resp *LanternResponse, req *LanternRequest ) {

  sampleIndex, err := getSampleIndexArray( req.SampleId ) ; _ = sampleIndex
  if err!=nil { _errp(w) ; return }

  tgvir := req.TileGroupVariantIdRange
  tileGroupRange := make( []map[string][2]int, len(tgvir) )

  // Flatten everything to give a list of mapped TileIds to the
  // expected match intervals.
  //
  for clause_ind:=0; clause_ind < len(tgvir); clause_ind++ {
    clause := tgvir[clause_ind]

    tileGroupRange[ clause_ind ] = make( map[string][2]int )

    for ele_ind:=0; ele_ind < len(clause); ele_ind++ {
      ele_map := clause[ele_ind]

      for tileIdRange,matchedInterval := range ele_map {
        tileList,e := unpack_tileid_range_into_tile_list( tileIdRange )
        if e!=nil { _errp(w) ; return }

        for k:=0; k<len(tileList); k++ {
          mm := [2]int{ matchedInterval[0], matchedInterval[1] }
          tileGroupRange[ clause_ind ][ tileList[k] ] = mm
        }

      }
    }
  }

  //result := make( map[string][]string )
  result := make( map[string][][]string )

  for ii:=0; ii<len(sampleIndex); ii++ {


    //DEBUG
    fmt.Printf(">>> tileGroupRange %v\n", tileGroupRange)

    match_set,result_map,e := find_tile_match_set( sampleIndex[ii], tileGroupRange )
    if e!=nil { _erre(w, e) ; return }

    //DEBUG
    fmt.Printf("match_set: %v\nresult_set: %v\n", match_set, result_map)

    _ = match_set

    result_set := construct_result_set( sampleIndex[ii], result_map )


    for allele:=0; allele<len(result_set); allele++ {

      result[ gCGFName[ sampleIndex[ii] ] ] = append( result[ gCGFName[ sampleIndex[ii] ] ], []string{} )

      for t,_ := range result_set[allele] {
        result[gCGFName[ sampleIndex[ii] ]][allele] = append( result[gCGFName[ sampleIndex[ii] ]][allele], t )
      }
    }

  }

  // For convenience, sort results
  //
  for name := range result {
    for allele:=0; allele<len(result[name]); allele++ {
      sort.Sort( ByString( result[name][allele] ) )
    }
  }


  w.Header().Set("Content-Type", "application/json")
  res_json_bytes,_ := json.Marshal( result )

  io.WriteString(w, "{\n")
  io.WriteString(w, "  \"Type\":\"success\", \"Message\":\"sample-tile-neighborhood\",\n")
  io.WriteString(w, "  \"Result\": ")

  io.WriteString(w, string(res_json_bytes))

  io.WriteString(w, "\n")
  io.WriteString(w, "}")


}


