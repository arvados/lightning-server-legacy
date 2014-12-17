package main

import _ "fmt"
import "net/http"
import "encoding/json"
import _ "os"
import "io"

import "bytes"

type LanternInfo struct {
  LanternVersion string
  LibraryVersion string
  TileMapVersion string
  CGFVersion string

  Stats LanternTileStats

  SampleId []string

}

func system_info_handler(  w http.ResponseWriter, resp *LanternResponse, req *LanternRequest ) {

  info := LanternInfo{}
  info.LanternVersion = VERSION_STR
  info.LibraryVersion = gCGF[0].TileLibraryVersion
  info.TileMapVersion = gCGF[0].EncodedTileMapMd5Sum
  info.CGFVersion = gCGF[0].CGFVersion
  info.Stats = gLanternTileStats
  info.SampleId = gCGFName

  resp.Type = "success"
  resp.Message = "system-info"

  w.Header().Set("Content-Type", "application/json")
  res_json_bytes,_ := json.Marshal( info )

  flatten_json_bytes := bytes.Trim( res_json_bytes, " {}\n")

  io.WriteString(w, "{\n")
  io.WriteString(w, "  \"Type\":\"success\", \"Message\":\"system-info\",\n")
  io.WriteString(w, string(flatten_json_bytes))
  io.WriteString(w, "\n")
  io.WriteString(w, "}")


}
