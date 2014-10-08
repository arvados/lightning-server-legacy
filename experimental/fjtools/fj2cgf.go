


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



func _main( c *cli.Context ) {
  g_verboseFlag = c.Bool("Verbose")

  if len( c.String("input-fastj")) == 0 {
    fmt.Fprintf( os.Stderr, "Provide input FastJ file\n" )
    cli.ShowAppHelp( c )
    os.Exit(1)
  }

  if len( c.String("tile-library")) == 0 {
    fmt.Fprintf( os.Stderr, "Provide tile library\n" )
    cli.ShowAppHelp( c )
    os.Exit(1)
  }

  scanner,err := bioenv.OpenScanner( c.String("input-fastj") )
  if err != nil {
    fmt.Fprintf( os.Stderr, "%v", err )
    os.Exit(1)
  }
  defer scanner.Close()



  tileSet := tile.NewTileSet( 24 )

  err = tileSet.FastjScanner( scanner.Scanner )
  if err != nil {
    fmt.Fprintf( os.Stderr, "%v\n", err )
    os.Exit(1)
  }

}


func main() {

  app := cli.NewApp()
  app.Name  = "fj2cgf"
  app.Usage = "Go from FastJ to Compact Genome Format (CGF)"
  app.Version = VERSION_STR
  app.Author = "Curoverse Inc."
  app.Email = "info@curoverse.com"
  app.Action = func( c *cli.Context ) { _main(c) }

  app.Flags = []cli.Flag{

    cli.StringFlag{
      Name: "input-fastj, i",
      Usage: "FastJ file(s)",
    },

    cli.StringFlag{
      Name: "tile-library, l",
      Usage: "Tile Library file",
    },

    cli.StringFlag{
      Name: "cgf-file, c",
      Usage: "CGF file (optional)",
    },

    cli.StringFlag{
      Name: "output-cgf, o",
      Usage: "Output CGF file",
    },

    cli.BoolFlag{
      Name: "Verbose, V",
      Usage: "Verbose flag",
    },

  }

  app.Run(os.Args)

}



