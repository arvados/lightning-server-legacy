/* some simple tests of lantern functionality, not to be compiled with lantern */
/*
  to compile:

    go build flint.go lantern_tile.go

  to run:

    ./flint

*/

package main

import "fmt"
import "log"

func flint() {

  fmt.Printf("initializing\n")

  e := TileSimpleInit()
  if e!=nil { log.Fatal(e) }

  fmt.Printf("init done\n\n")

  //tileid := "241.00.0000.0005"
  tileid := "247.00.0000.0000"

  count:=0
  for k := range gTileCache.TileIDSeqMap {
    fmt.Printf("%s\n", k )
    count++
    if count>5 { break }
  }


  fmt.Printf("getting tile sequence '%s'\n", tileid)

  s,e := GetTileSeq( tileid )
  if e!=nil { log.Fatal(e) }

  fmt.Printf(">>> %s\n", s);

  TileStatsPrint()
}
