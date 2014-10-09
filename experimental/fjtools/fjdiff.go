


package main

import "fmt"
import "os"
import _ "strings"
import _ "errors"

import "../tile"
import "../bioenv"

import "github.com/codegangsta/cli"


var VERSION_STR string = "0.1, AGPLv3.0"
var g_verboseFlag bool

func init() {
}


func md5Ascii( b [16]byte ) (s []byte) {
  for i:=0; i<len(b); i++ {
    t := fmt.Sprintf("%02x", b[i] )
    s = append( s, []byte(t)... )
  }
  return s
}


func cmp_fastj( a *tile.TileSet, b *tile.TileSet ) {

  a_md5sum_map := make( map[string]bool )
  b_md5sum_map := make( map[string]bool )

  for _,tcc := range a.TileCopyCollectionMap {
    for _,j := range tcc.MetaJson {
      if _,ok := a_md5sum_map[ j.Md5Sum ]; ok {
        fmt.Printf("< Duplicate md5sum '%s'\n", j.Md5Sum )
      }
      a_md5sum_map[ j.Md5Sum ] = true
    }
  }

  for _,tcc := range b.TileCopyCollectionMap {
    for _,j := range tcc.MetaJson {
      if _,ok := b_md5sum_map[ j.Md5Sum ]; ok {
        fmt.Printf("> Duplicate md5sum '%s'\n", j.Md5Sum )
      }
      b_md5sum_map[ j.Md5Sum ] = true
    }
  }

  for k,_ := range a_md5sum_map {
    if _,ok := b_md5sum_map[k] ; !ok { fmt.Printf("< %s\n", k) }
  }

  for k,_ := range b_md5sum_map {
    if _,ok := a_md5sum_map[k] ; !ok { fmt.Printf("> %s\n", k) }
  }

}


func _main( c *cli.Context ) {
  g_verboseFlag = c.Bool("Verbose")
  tagLength := c.Int("tag-length")

  if len( c.String("a-input-fastj")) == 0 {
    fmt.Fprintf( os.Stderr, "Provide input A FastJ file\n" )
    cli.ShowAppHelp( c )
    os.Exit(1)
  }

  if len( c.String("b-input-fastj")) == 0 {
    fmt.Fprintf( os.Stderr, "Provide input B FastJ file\n" )
    cli.ShowAppHelp( c )
    os.Exit(1)
  }

  if g_verboseFlag {
    fmt.Printf("tagLength: %d\n", tagLength)
  }

  a_scanner,err := bioenv.OpenScanner( c.String("a-input-fastj") )
  if err != nil {
    fmt.Fprintf( os.Stderr, "%v", err )
    os.Exit(1)
  }
  defer a_scanner.Close()

  b_scanner,err := bioenv.OpenScanner( c.String("b-input-fastj") )
  if err != nil {
    fmt.Fprintf( os.Stderr, "%v", err )
    os.Exit(1)
  }
  defer b_scanner.Close()

  aTileSet := tile.NewTileSet( tagLength )
  bTileSet := tile.NewTileSet( tagLength )

  err = aTileSet.FastjScanner( a_scanner.Scanner )
  if err != nil {
    fmt.Fprintf( os.Stderr, "%v\n", err )
    os.Exit(1)
  }

  err = bTileSet.FastjScanner( b_scanner.Scanner )
  if err != nil {
    fmt.Fprintf( os.Stderr, "%v\n", err )
    os.Exit(1)
  }

  cmp_fastj( aTileSet, bTileSet )

}


func main() {

  app := cli.NewApp()
  app.Name  = "fjdiff"
  app.Usage = "Compare two FastJ files"
  app.Version = VERSION_STR
  app.Author = "Curoverse Inc."
  app.Email = "info@curoverse.com"
  app.Action = func( c *cli.Context ) { _main(c) }

  app.Flags = []cli.Flag{

    cli.StringFlag{
      Name: "a-input-fastj, a",
      Usage: "First input FastJ file (A)",
    },

    cli.StringFlag{
      Name: "b-input-fastj, b",
      Usage: "Second input FastJ file (B)",
    },

    cli.IntFlag{
      Name: "tag-length, t",
      Value: 24,
      Usage: "Tag length",
    },

    cli.BoolFlag{
      Name: "Verbose, V",
      Usage: "Verbose flag",
    },

  }

  app.Run(os.Args)

}



