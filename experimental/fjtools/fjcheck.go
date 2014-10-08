package main

import "fmt"
import "os"
import _ "strings"
import _ "errors"
import "crypto/md5"

import "../tile"
import "../bioenv"

import "github.com/codegangsta/cli"


var VERSION_STR string = "0.1, AGPLv3.0"

var g_verboseFlag bool

func init() {
}

func check_copy_num_consistency( tileSet *tile.TileSet ) (err error) {

  for _,tcc := range tileSet.TileCopyCollectionMap {
    copyMap := make( map[int]int )

    for copyNum,_ := range tcc.Meta {
      copyMap[copyNum] = 1
    }

    for copyNum,_ := range tcc.MetaJson {
      _,ok := copyMap[copyNum]
      if !ok { return fmt.Errorf("MetaJson has an invalid variant (variant number %d)", copyNum) }
      copyMap[copyNum]++
    }

    for copyNum,_ := range tcc.Body {
      _,ok := copyMap[copyNum]
      if !ok { return fmt.Errorf("Body has an invalid variant (variant number %d)", copyNum) }
      copyMap[copyNum]++
    }

    for copyNum,v := range copyMap {
      if v != 3 { return fmt.Errorf("Variant %d only has %d occurences", copyNum, v ) }
    }

  }

  return nil
}

func check_length( tileSet *tile.TileSet ) (err error) {

  for _,tcc := range tileSet.TileCopyCollectionMap {
    for copyNum,j := range tcc.MetaJson {
      if len( tcc.Body[copyNum] ) != j.N {
        return fmt.Errorf("Body for tileId %s (%s) does not match reported length of %d (variant %d, calculated length %d)\n%s",
          j.TileID, string(j.Md5Sum[:]), j.N, copyNum, len(tcc.Body[copyNum]), tcc.Body[copyNum] )
      }
    }
  }

  return nil

}

func md5Ascii( b [16]byte ) (s []byte) {
  for i:=0; i<len(b); i++ {
    t := fmt.Sprintf("%02x", b[i] )
    s = append( s, []byte(t)... )
  }
  return s
}

func check_md5sum( tileSet *tile.TileSet ) (err error) {

  for _,tcc := range tileSet.TileCopyCollectionMap {
    for copyNum,j := range tcc.MetaJson {

      //seq := strings.ToUpper(j.StartSeq) + strings.ToLower(tcc.Body[copyNum]) + strings.ToUpper(j.EndSeq)
      seq := tcc.Body[copyNum]
      b := md5.Sum( []byte( seq ) )

      md5sumString := string(md5Ascii( b ))

      if md5sumString != j.Md5Sum {
        return fmt.Errorf("Body for tileId %s does not match reported md5sum %s (variant %d, calculated md5sum %s)\n%s",
          j.TileID, string(j.Md5Sum[:]), copyNum, md5sumString, seq)
      }
    }
  }

  return nil

}

func _main( c *cli.Context ) {
  g_verboseFlag = c.Bool("Verbose")
  tagLength := c.Int("tag-length")

  if len( c.String("input-fastj")) == 0 {
    fmt.Fprintf( os.Stderr, "Provide input FastJ file\n" )
    cli.ShowAppHelp( c )
    os.Exit(1)
  }

  if g_verboseFlag {
    fmt.Printf("tagLength: %d\n", tagLength)
  }

  scanner,err := bioenv.OpenScanner( c.String("input-fastj") )
  if err != nil {
    fmt.Fprintf( os.Stderr, "%v", err )
    os.Exit(1)
  }
  defer scanner.Close()

  tileSet := tile.NewTileSet( tagLength )
  err = tileSet.FastjScanner( scanner.Scanner )
  if err != nil {
    fmt.Fprintf( os.Stderr, "%v\n", err )
    os.Exit(1)
  }

  if err := check_copy_num_consistency( tileSet ) ; err != nil {
    fmt.Fprintf( os.Stderr, "%v\n", err )
    os.Exit(1)
  }

  if err := check_length( tileSet ) ; err != nil {
    fmt.Fprintf( os.Stderr, "%v\n", err )
    os.Exit(1)
  }

  if err := check_md5sum( tileSet ) ; err != nil {
    fmt.Fprintf( os.Stderr, "%v\n", err )
    os.Exit(1)
  }

  fmt.Printf(">> ok\n")

}


func main() {

  app := cli.NewApp()
  app.Name  = "fjcheck"
  app.Usage = "Do sanity checks on the FastJ"
  app.Version = VERSION_STR
  app.Author = "Curoverse Inc."
  app.Email = "info@curoverse.com"
  app.Action = func( c *cli.Context ) { _main(c) }

  app.Flags = []cli.Flag{
    cli.StringFlag{
      Name: "input-fastj, i",
      Usage: "Input FastJ to check",
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



