package main

import "fmt"
import "os"
import "./tile"

var gDebugFlag bool

func main() {

  gDebugFlag = true

  tagLen := 24

  if len(os.Args) != 3 {
    fmt.Println("usage:")
    fmt.Println("./mergeFastj <fastjInp0> <fastjInp1> [<fastjOut>]")
    os.Exit(0)
  }

  fastjInp0 := os.Args[1]
  fastjInp1 := os.Args[2]

  if gDebugFlag { fmt.Printf("# loading %s\n", fastjInp0) }

  tileSet0 := tile.NewTileSet( tagLen )
  tileSet0.ReadFastjFile( fastjInp0 )

  if gDebugFlag { fmt.Printf("# loading %s\n", fastjInp1) }

  tileSet1 := tile.NewTileSet( tagLen )
  tileSet1.ReadFastjFile( fastjInp1 )


  finalTileSet := tile.NewTileSet( tagLen )

  for _,tcc := range tileSet0.TileCopyCollectionMap {

    n := len(tcc.Meta)
    for i:=0 ; i<n; i++ {
      tileId := fmt.Sprintf("%s.%03x", tcc.BaseTileId, i )
      finalTileSet.AddTile( tileId, tcc.Body[i], tcc.Meta[i] )
    }

  }

  for _,tcc := range tileSet1.TileCopyCollectionMap {

    n := len(tcc.Meta)
    for i:=0 ; i<n; i++ {

      uniq := true

      if _,found := tileSet0.TileCopyCollectionMap[ tcc.BaseTileId ] ; found {

        tcc0 := tileSet0.TileCopyCollectionMap[ tcc.BaseTileId ]
        m := len( tcc0.Meta )
        for j:=0 ; j<m; j++ {
          if tcc0.Body[j] == tcc.Body[i] {
            uniq = false
            break
          }
        }

      }

      if uniq {

        tileId := fmt.Sprintf("%s.000", tcc.BaseTileId )
        if _,ok := finalTileSet.TileCopyCollectionMap[ tcc.BaseTileId ] ; ok {
          tileId = fmt.Sprintf("%s.%03x", tcc.BaseTileId, len( finalTileSet.TileCopyCollectionMap[ tcc.BaseTileId ].Meta ) )
        }

        finalTileSet.AddTile( tileId, tcc.Body[i], tcc.Meta[i] )
      }

    }

  }

  finalTileSet.WriteFastjFile( "foo.fj" )

}

