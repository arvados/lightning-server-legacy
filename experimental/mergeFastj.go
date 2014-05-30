package main

import "fmt"
import "os"
import "./tile"

var gDebugFlag bool

func main() {

  gDebugFlag = true

  tagLen := 24

  if len(os.Args) != 4 {
    fmt.Println("usage:")
    fmt.Println("./mergeFastj <fastjInp0> <fastjInp1> <fastjOut>")
    os.Exit(0)
  }

  fastjInp0 := os.Args[1]
  fastjInp1 := os.Args[2]
  fastjOutFn := os.Args[3]

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

  // Simple N^2 scan to find duplicate tile sequences by comparing
  // the tile sequence body.
  //
  for _,tcc := range tileSet1.TileCopyCollectionMap {

    foundCopyNum := -1

    n := len(tcc.Meta)
    for i:=0 ; i<n; i++ {

      uniq := true

      if _,found := tileSet0.TileCopyCollectionMap[ tcc.BaseTileId ] ; found {

        tcc0 := tileSet0.TileCopyCollectionMap[ tcc.BaseTileId ]
        m := len( tcc0.Meta )
        for j:=0 ; j<m; j++ {
          if tcc0.Body[j] == tcc.Body[i] {

            // We've found a duplicate body, record the copy number found,
            // set the uniq flag to false and break out.
            //
            foundCopyNum = j
            uniq = false
            break

          }
        }

      }

      if uniq {

        // If we've found a unique tileId, add it to the current tile set, incrementing
        // the copy number as appropriate.
        //
        tileId := fmt.Sprintf("%s.000", tcc.BaseTileId )
        if _,ok := finalTileSet.TileCopyCollectionMap[ tcc.BaseTileId ] ; ok {
          tileId = fmt.Sprintf("%s.%03x", tcc.BaseTileId, len( finalTileSet.TileCopyCollectionMap[ tcc.BaseTileId ].Meta ) )
        }

        finalTileSet.AddTile( tileId, tcc.Body[i], tcc.Meta[i] )
      } else {

        // Construct the found tileId and add the notes of the found entry to the current set
        //
        tileId := fmt.Sprintf("%s.%03x", tcc.BaseTileId, foundCopyNum )
        finalTileSet.AddTileNotes( tileId, tcc.MetaJson[i].Notes )
      }


    }

  }

  finalTileSet.WriteFastjFile( fastjOutFn )

}

