package main

import "os"
import "fmt"
import "../cgf"

import "crypto/md5"
import "strings"
import "strconv"

import "github.com/codegangsta/cli"

var VERSION_STR string = "0.1, AGPLv3.0"

var g_verboseFlag bool

func init() {
}

func Md5sumToStr( m5 []byte ) string {
  s := ""
  for i:=0; i<len(m5); i++ {
    s += fmt.Sprintf("%02x", m5[i] )
  }
  return s
}

func _main( c *cli.Context ) {
  g_verboseFlag = c.Bool("Verbose")

  if len( c.String("input-cgf")) == 0 {
    fmt.Fprintf( os.Stderr, "Provide input CGF file\n" )
    cli.ShowAppHelp( c )
    os.Exit(1)
  }

  //cg,err := cgf.LoadLean( c.String("input-cgf") )
  cg,err := cgf.Load( c.String("input-cgf") )
  if err!=nil {
    fmt.Fprintf( os.Stderr, "%v\n", err )
    cli.ShowAppHelp( c )
    os.Exit(1)
  }

  tm_md5 := md5.Sum( []byte( cg.EncodedTileMap ) )
  str_tm_md5 := Md5sumToStr( tm_md5[:] )

  if str_tm_md5 != cg.EncodedTileMapMd5Sum {
    fmt.Fprintf( os.Stderr, "md5sums don't match! %s != %s\n", str_tm_md5, cg.EncodedTileMapMd5Sum )
  }
  //fmt.Printf("%s %s\n", Md5sumToStr(tm_md5[:]), cg.TileMapStringMd5Sum )

  for path_str := range cg.ABV {
    abv := cg.ABV[path_str]

    path,_ := strconv.ParseInt( path_str, 16, 64 )

    if (path<0) {
      fmt.Fprintf( os.Stderr, "path<0! (%d from %s)\n", path, path_str)
      continue
    }

    if path>=int64(len(cg.StepPerPath)) {
      fmt.Fprintf( os.Stderr, "path (%d) exceeds StepPerPath length (%d)!\n", path, len(cg.StepPerPath))
      continue
    }

    if len(abv) != cg.StepPerPath[path] {
      fmt.Fprintf( os.Stderr, "StepPerPath[%d] != len(abv) (%d)!\n", cg.StepPerPath[path], len(abv))
      continue
    }


    for p:=0; p<len(abv); p++ {
      overflow_key := fmt.Sprintf("%x:%x", path, p )

      ch := abv[p]
      if ch=='#' {

        lookup,found := cg.OverflowMap[ overflow_key ]
        if !found {

          s := p-10
          if s < 0 { s = 0 }
          e := p+10
          if e > len(abv) { e = len(abv) }


          fmt.Fprintf( os.Stderr, "Could not find %s in overflow table!  [%x,%x,%x) %s(!%s!)%s\n",
            overflow_key, s, p, e, abv[s:p], abv[p:p+1], abv[p+1:e] )

        }

        if (lookup < 0) || (lookup >= len(cg.TileMap)) {
          fmt.Fprintf( os.Stderr, "lookup out of range lookup %d not in [%d,%d) for overflow key %s\n", lookup, 0, len(cg.TileMap), overflow_key )
        }

      }

    }
  }

  for overflow_key := range cg.OverflowMap {
    str_ps := strings.Split( overflow_key, ":" )
    ipath,_ := strconv.ParseInt( str_ps[0], 16, 64 )
    istep,_ := strconv.ParseInt( str_ps[1], 16, 64 )

    s_path := fmt.Sprintf( "%x", ipath )
    s_step := fmt.Sprintf( "%x", istep )
    _ = s_step

    if _,ok := cg.ABV[s_path] ; !ok {
      fmt.Fprintf( os.Stderr, "could not find path %s in ABV!\n", s_path )
      continue
    }

    if cg.ABV[s_path][istep] != '#' {

      s := istep-10
      if s<0 { s=0 }
      e := int(istep+10)
      if e>len(cg.ABV[s_path]) { e = len(cg.ABV[s_path]) }

      fmt.Fprintf( os.Stderr, "Overflow entry %s does not map to overflow character! [%x,%x,%x) %s(!%s!)%s\n",
      overflow_key, s, istep, e, cg.ABV[s_path][s:istep], cg.ABV[s_path][istep:istep+1], cg.ABV[s_path][istep:e] )
      continue
    }
  }


  if g_verboseFlag { fmt.Printf("ok\n") }

}


func main() {

  app := cli.NewApp()
  app.Name  = "cgfcheck"
  app.Usage = "Do sanity checks on the FastJ"
  app.Version = VERSION_STR
  app.Author = "Curoverse Inc."
  app.Email = "info@curoverse.com"
  app.Action = func( c *cli.Context ) { _main(c) }

  app.Flags = []cli.Flag{
    cli.StringFlag{
      Name: "input-cgf, i",
      Usage: "Input CGF to check",
    },
    cli.BoolFlag{
      Name: "Verbose, V",
      Usage: "Verbose flag",
    },
  }

  app.Run(os.Args)

}
