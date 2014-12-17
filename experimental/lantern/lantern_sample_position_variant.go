package main

import "fmt"
import "net/http"
import "encoding/json"
import "io"

import "strings"

/*

Example request:

{
  "Type":"sample-position-variant",
  "Message" : "sample query",
  "Dataset" : "all",
  "SampleId" : [ "0:/scratch/pgp174.gff/hu011C57/chr13_chr17.abv/hu011C57_chr13_chr17.reported.cgf",
                 "1:/scratch/pgp174.gff/hu016B28/chr13_chr17.abv/hu016B28_chr13_chr17.reported.cgf" ],
  "Position" : [ "247.00.0000", "247.00.0003-000f" ]
}

Example response:

{
  "Type":"success",
  "Message" : "sample-position-variant",
  "Result" : {
    "0:/scratch/pgp174.gff/hu011C57/chr13_chr17.abv/hu011C57_chr13_chr17.reported.cgf" : [
      [
        "247.00.0000.0000",
        "247.00.0005.0000",
        "247.00.0007.0000",
        "247.00.0008.0000",
        "247.00.0009.0000",
        "247.00.000a.0002",
        "247.00.000c.0000",
        "247.00.000d.0004",
        "247.00.0003.0000",
        "247.00.0004.0000",
        "247.00.0006.0000",
        "247.00.000b.0000",
        "247.00.000e.0000"
      ],
      [
        "247.00.0003.0000",
        "247.00.0004.0000",
        "247.00.0005.0000",
        "247.00.0006.0000",
        "247.00.0007.0000",
        "247.00.0008.0000",
        "247.00.0009.0002",
        "247.00.000c.0001",
        "247.00.000d.0004",
        "247.00.000e.0000",
        "247.00.0000.0000",
        "247.00.000b.0004"
      ]
    ]
  }
}


*/

func sample_position_variant_handler( w http.ResponseWriter, resp *LanternResponse, req *LanternRequest ) {

  library_version := 0

  n_ele := 0
  max_elements := 20000

  sampleIndex,err := getSampleIndexArray( req.SampleId )
  if err!=nil { _errp(w) ; return }

  // result is a map of sampleid to an array of maps.
  // Position for the array of maps represents the allele.
  // The map is there to indicate if a tileid (represented by
  // a key of it's normalized ascii hex name) is found.
  //
  result := make( map[string][]map[string]bool )

  // Pre-allocate result
  //
  for i:=0; i<len(sampleIndex); i++ {
    sample_name := gCGFName[ sampleIndex[i] ]
    result[sample_name] = []map[string]bool{}
    for j:=0; j<len(gCGF[0].TileMap[0].Variant); j++ {
      m := make(map[string]bool)
      result[sample_name] = append( result[sample_name], m )
    }
  }

  for i:=0; i<len(req.Position); i++ {
    pvs := strings.SplitN( req.Position[i], ".", 3 )
    if len(pvs)!=3 { _errp(w) ; return }

    path_range,e := parseIntOption( pvs[0], 16 )
    if e!= nil { _errp(w) ; return }

    step_range,e := parseIntOption( pvs[2], 16 )
    if e!= nil { _errp(w) ; return }

    for pi:=0; pi<len(path_range); pi++ {
      for path:=path_range[pi][0]; path<path_range[pi][1]; path++ {

        for si:=0; si<len(step_range); si++ {
          for step:=step_range[si][0]; step<step_range[si][1]; step++ {

            for k:=0; k<len(sampleIndex); k++ {
              cgf_ind := sampleIndex[k]
              name := gCGFName[cgf_ind]

              n_ele ++
              if n_ele >= max_elements { _errm(w) ; return }

              p,s,tmv,e := gCGF[cgf_ind].LookupABVStartTileMapVariant( int(path), int(step) )
              if e!=nil { continue }

              tme := gCGF[0].TileMap[tmv]

              for allele:=0; allele<len(tme.Variant); allele++ {
                x := 0
                for v_ind:=0; v_ind<len(tme.Variant[allele]); v_ind++ {
                  if (p==int(path)) && ((s+x)==int(step)) {
                    result_tileid := fmt.Sprintf("%03x.%02x.%04x.%04x", p, library_version, s+x, tme.Variant[allele][v_ind] )
                    result[name][allele][result_tileid] = true
                    break
                  }
                  x += tme.VariantLength[allele][v_ind]
                }
              }

            }

          }
        }

      }

    }

  }


  resp.Type = "success"
  resp.Message = "system-info"

  fin_result := map[string][][]string{}

  for name := range result {
    fin_result[name] = [][]string{}
    for allele:=0; allele<len(result[name]); allele++ {
      a := []string{}
      fin_result[name] = append( fin_result[name], a )
      for tileid := range result[name][allele] {
        fin_result[name][allele] = append(fin_result[name][allele], tileid)
      }
    }
  }

  w.Header().Set("Content-Type", "application/json")
  //res_json_bytes,_ := json.Marshal( result )
  res_json_bytes,_ := json.Marshal( fin_result )

  io.WriteString(w, "{\n")
  io.WriteString(w, "  \"Type\":\"success\", \"Message\":\"sample_position_variant\",\n")
  io.WriteString(w, "  \"Result\": ")
  io.WriteString(w, string(res_json_bytes))
  io.WriteString(w, "\n")
  io.WriteString(w, "}")


}

