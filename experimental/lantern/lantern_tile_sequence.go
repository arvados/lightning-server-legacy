package main

import "fmt"
import "net/http"
import "encoding/json"
import "os"
import "io"

func tile_sequence_handler( w http.ResponseWriter, resp *LanternResponse, req *LanternRequest ) {

  seqmap := make( map[string]string )

  error_count:=0

  for i:=0; i<len(req.TileId); i++ {
    //fmt.Printf(">> %s\n", req.TileId[i])

    seq,e := GetTileSeq( req.TileId[i] )
    if e!=nil {
      error_count ++
      if (error_count%1000)==0 {
        fmt.Fprintf( os.Stderr, "ERROR: error count %d.  Latest error: tile_sequence_handler(%s): %v\n", error_count, req.TileId[i], e )
      }
      //fmt.Fprintf( os.Stderr, "ERROR: tile_sequence_handler(%s): %v\n", req.TileId[i], e )
      continue
    }

    seqmap[ req.TileId[i] ] = seq
  }

  //for k,v := range seqmap { fmt.Printf("%s %s\n", k, v[0:10]) }


  //DEBUG
  TileStatsPrint()


  resp.Type = "success"
  resp.Message = "tile-sequence"

  w.Header().Set("Content-Type", "application/json")
  res_json_bytes,_ := json.Marshal( seqmap )

  io.WriteString(w, "{\n")
  io.WriteString(w, "  \"Type\":\"success\", \"Message\":\"tile-sequence\",\n")
  io.WriteString(w, "  \"Result\":")
  io.WriteString(w, string(res_json_bytes))
  io.WriteString(w, "\n")
  io.WriteString(w, "}")

}


/* Do lookups without returning the actual sequence to test lookup speed
*/
func tile_sequence_handler_tracer( w http.ResponseWriter, resp *LanternResponse, req *LanternRequest ) {

  error_count := 0

  for i:=0; i<len(req.TileId); i++ {
    _,e := GetTileSeqDummy( req.TileId[i] )
    if e!=nil {
      error_count ++
      if (error_count%1000)==0 {
        fmt.Fprintf( os.Stderr, "ERROR: error count %d.  Latest error: tile_sequence_handler(%s): %v\n", error_count, req.TileId[i], e )
      }
      continue
    }

  }

  //DEBUG
  TileStatsPrint()

  resp.Type = "success"
  resp.Message = "tile-sequence"

  w.Header().Set("Content-Type", "application/json")
  io.WriteString(w, "{\n")
  io.WriteString(w, "  \"Type\":\"success\", \"Message\":\"tile-sequence\",\n")
  io.WriteString(w, "  \"Result\": {}\n")
  io.WriteString(w, "}")

}


