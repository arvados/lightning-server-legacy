package cgf

import "fmt"
import "os"
import "encoding/json"
import _ "bufio"
import "strconv"

var VERSION_STR string = "1.0"

type TileMapEntry struct {
  Type string
  VariantA []int
  VariantB []int

  VariantALength int
  VariantBLength int
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
  TotalStep int

  TileMap []TileMapEntry

  CharMap map[string]int

  ABV map[string]string
  OverflowMap map[string]int
  FinalOverflowMap map[string]OverflowMapEntry
}


func (cgf *CGF) Print() {
  cgf.PrintFile( os.Stdout )
}

func (cgf *CGF) PrintFile( ofp *os.File ) {

  fmt.Fprintln( ofp, "{")
  //fmt.Fprintf( ofp, "  ")

  fmt.Fprintf( ofp, "  \"CGFVersion\" : \"%s\",\n", cgf.CGFVersion)
  fmt.Fprintf( ofp, "  \"Encoding\" : \"%s\",\n", cgf.Encoding)
  fmt.Fprintf( ofp, "  \"Notes\" : \"%s\",\n", cgf.Notes)
  fmt.Fprintf( ofp, "  \"TileLibraryVersion\" : \"%s\",\n", cgf.TileLibraryVersion)

  fmt.Fprintf( ofp, "  \"PathCount\" : %d,\n", cgf.PathCount )

  fmt.Fprintf( ofp, "  \"StepPerPath\" : [\n    ")
  for i:=0; i<len(cgf.StepPerPath); i++ {
    if i>0 { fmt.Fprintf( ofp, ", ") }
    fmt.Fprintf( ofp, "%d", cgf.StepPerPath[i])
  }
  fmt.Fprintf( ofp, "\n    ],\n")
  fmt.Fprintf( ofp, "  \"TotalStep\" : %d,\n", cgf.TotalStep)

  fmt.Fprintln( ofp, "")

  fmt.Fprintf( ofp, "  \"TileMap\" : [\n    ")
  for i:=0; i<len(cgf.TileMap); i++ {
    if i>0 { fmt.Fprintf( ofp, ",\n    ") }

    tile_ele := cgf.TileMap[i]

    fmt.Fprintf( ofp, "\"Type\":\"%s\", \"VariantA\": %v, \"VariantB\": %v, \"VariantALength\":%d, \"VariantBLength\":%d",
      tile_ele.Type, tile_ele.VariantA, tile_ele.VariantB,
      tile_ele.VariantALength, tile_ele.VariantBLength)
  }
  fmt.Fprintf( ofp, "\n    ],\n")

  fmt.Fprintf( ofp, "  \"CharMap\" : {")
  count:=0
  for k,v := range cgf.CharMap {
    if count>0 { fmt.Fprintf( ofp, ", ") }
    fmt.Fprintf( ofp, "\"%s\":%d", k, v)
    count+=1
  }
  fmt.Fprintf( ofp, "\n  },\n")

  count = 0
  fmt.Fprintf( ofp, "  \"ABV\":{\n    ")
  for k,v := range cgf.ABV {
    if count>0 { fmt.Fprintf( ofp, ",\n    ") }
    fmt.Fprintf( ofp, "  \"%s\" : \"%s\"", k,v)
    count += 1
  }
  fmt.Fprintf( ofp, "\n  },\n")

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

    //fmt.Fprintf( ofp, "      \"Data\" : \"%s\",\n", v.Data )
    fmt.Fprintf( ofp, "      \"Data\" : \"")
    fmt.Fprintf( ofp, "%s", strconv.Quote( v.Data ) )

    //for i:=0; i<len(v.Data); i++ { fmt.Fprintf( ofp, "%c", v.Data[i] ) }
    //ofp.Write( []byte(v.Data) )

    fmt.Fprintf( ofp, "\",\n" )

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

  cgf = &(CGF{})

  dec := json.NewDecoder(fp)
  err = dec.Decode( cgf )
  if err != nil { return nil, err }

  return cgf, nil

}


func ( cgf *CGF ) Dump( fn string ) error {
  fp,err := os.Create( fn )
  if err != nil { return err }
  defer fp.Close()

  enc := json.NewEncoder( fp )
  enc.Encode( cgf )

  return nil

}
