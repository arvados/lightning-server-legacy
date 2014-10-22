package main

import "fmt"
import "os"
import "strconv"
import "strings"
import "runtime/pprof"

import "../cgf"

import "github.com/codegangsta/cli"


var VERSION_STR string = "0.1, AGPLv3.0"
var g_verboseFlag bool

var gMemProfileFlag bool = false
var gMemProfileFile string = "cgf_helper.mprof"

func parseIntOption( istr string, base int ) ([][]int64, error) {
  r := make( [][]int64, 0, 8 )
  commaval := strings.Split( istr, "," )
  for i:=0; i<len(commaval); i++ {

    if strings.Contains( commaval[i], "-" ) {

      dashval := strings.Split( commaval[i], "-" )
      if len(dashval) > 2 { return nil, fmt.Errorf("invalid option %s", commaval[i]) }

      a,ee := strconv.ParseInt( dashval[0], base, 64 )
      if ee!=nil { return nil, fmt.Errorf("invalid option %s: %v", dashval[0], ee ) }

      /*
      if len(dashval)==1 {
        r = append( r, []int64{a,a+1} )
        continue
      }
      */

      if len(dashval[1])==0 {
        r = append( r, []int64{a,-1} )
        continue
      }

      b,ee := strconv.ParseInt( dashval[1], base, 64)
      if ee!=nil { return nil, fmt.Errorf("invalid option %s: %v", dashval[1], ee ) }
      r = append( r, []int64{a,b} )

    } else if strings.Contains( commaval[i], "+" ) {

      plusval := strings.Split( commaval[i], "+" )
      if len(plusval) > 2 { return nil, fmt.Errorf("invalid option %s", commaval[i]) }

      a,ee := strconv.ParseInt( plusval[0], base, 64 )
      if ee!=nil { return nil, fmt.Errorf("invalid option %s: %v", plusval[0], ee ) }

      if len(plusval[1])==0 {
        r = append( r, []int64{a,-1} )
        continue
      }

      b,ee := strconv.ParseInt( plusval[1], base, 64)
      if ee!=nil { return nil, fmt.Errorf("invalid option %s: %v", plusval[1], ee ) }
      if b<0 { return nil, fmt.Errorf("invalid option %s: %d < 0", plusval[1], b ) }
      r = append( r, []int64{a,a+b} )


    } else {
      a,ee := strconv.ParseInt( commaval[i], base, 64 )
      if ee!=nil { return nil, fmt.Errorf("invalid option %s: %v", commaval[i], ee ) }

      r = append( r, []int64{a,a+1} )
    }

  }

  /*
  for i:=0; i<len(r); i++ {
    for j:=0; j<len(r[i]); j++ {
      fmt.Printf("[%d][%d] %d\n", i,j, r[i][j])
    }
    fmt.Printf("\n")
  }
  */

  return r,nil
}

func _abv_peek( c *cli.Context ) {
  cg,ee := cgf.Load( c.String("cgf-file") ) ; _ = cg
  if ee!=nil { fmt.Fprintf( os.Stderr, "%s: %v\n", c.String("cgf-file"), ee) ; os.Exit(1) }

  pathraw := c.String("path") ; _ = pathraw
  stepraw := c.String("step") ; _ = stepraw
  hexpathraw := c.String("hex-path") ; _ = hexpathraw
  hexstepraw := c.String("hex-step") ; _ = hexstepraw

  path_opt := "0"
  pathbase := 10
  if hexpathraw!="0" {
    path_opt = hexpathraw
    pathbase = 16
  } else {
    path_opt = pathraw
  }

  path_ranges,ee := parseIntOption(path_opt, pathbase )
  if ee!=nil { fmt.Fprintf( os.Stderr, "%v",ee ) ; os.Exit(1) }
  _ = path_ranges

  step_ranges,ee := parseIntOption(stepraw, 10 )
  if ee!=nil { fmt.Fprintf( os.Stderr, "%v",ee ) ; os.Exit(1) }
  _ = step_ranges


  for pind:=0; pind<len(path_ranges); pind++ {

    p_s := fmt.Sprintf("%x", path_ranges[pind][0] )
    //p_e := fmt.Sprintf("%x", path_ranges[pind][1] )

    abv,abv_ok := cg.ABV[ p_s ]
    if !abv_ok {
      fmt.Fprintf( os.Stderr, "%s invalid index into ABV object\n", p_s )
      os.Exit(1)
    }

    for sind:=0; sind<len(step_ranges); sind++ {

      s_s := int(step_ranges[sind][0])
      s_e := int(step_ranges[sind][1])

      if s_e>=0 {

        if (s_s<0) || (s_e>len(abv)) || (s_s>=len(abv)) {
          fmt.Fprintf( os.Stderr, "step ranges must be in [%d,%d) (value range [%d,%d))\n", 0, len(abv), s_s, s_e)
          os.Exit(1)
        }

        fmt.Printf("%s:%x %s\n", p_s, s_s, abv[s_s:s_e] )
      } else {

        if (s_s<0) || (s_s>=len(abv)) {
          fmt.Fprintf( os.Stderr, "step ranges must be in [%d,%d) (value range [%d,%d))\n", 0, len(abv), s_s, s_e)
          os.Exit(1)
        }

        fmt.Printf("%s:%x %s\n", p_s, s_s, abv[s_s:] )
      }


    }

  }

}

func _main( c *cli.Context ) {

  action := c.String("action") ; _ = action

  if action == "abv" {
    _abv_peek( c )
  } else if action == "length" {
    cg,ee := cgf.Load( c.String("cgf-file") ) ; _ = cg
    if ee!=nil { fmt.Fprintf( os.Stderr, "%s: %v\n", c.String("cgf-file"), ee) ; os.Exit(1) }

    path := c.String("path")
    pathbase := 10
    if c.String("hex-path") != "0" { path = c.String("hex-path") ; pathbase = 16 }

    xl,e := strconv.ParseInt( path, pathbase, 64)
    x := int(xl)
    if e!=nil { fmt.Fprintf(os.Stderr, "invalid path: %v\n", e) ; os.Exit(1) }
    if (x<0) || (x>len(cg.StepPerPath)) {
      fmt.Fprintf(os.Stderr, "invalid path: %d needs to be in the range [%d,%d)\n", x, 0, len(cg.StepPerPath))
      os.Exit(1)
    }

    fmt.Printf("length:%d %d\n", x, cg.StepPerPath[x])
  }

}



func main() {

  app := cli.NewApp()
  app.Name  = "cgf_helper"
  app.Usage = "Helper program to examine cgf files"
  app.Version = VERSION_STR
  app.Author = "Curoverse Inc."
  app.Email = "info@curoverse.com"
  app.Action = func( c *cli.Context ) { _main(c) }

  app.Flags = []cli.Flag{

    cli.StringFlag{
      Name: "cgf-file, f",
      Usage: "FastJ file(s)",
    },

    cli.StringFlag{
      Name: "action, a",
      Value: "abv",
      Usage: "Action",
    },

    cli.StringFlag{
      Name: "path, p",
      Value : "0",
      Usage: "Path (decimal)",
    },

    cli.StringFlag{
      Name: "step, s",
      Value : "0",
      Usage: "Step (decimal)",
    },

    cli.StringFlag{
      Name: "hex-path, P",
      Value : "0",
      Usage: "Path (in hexadecimal)",
    },

    cli.StringFlag{
      Name: "hex-step, S",
      Value : "0",
      Usage: "Step (in hexadecimal)",
    },

    cli.BoolFlag{
      Name: "Verbose, V",
      Usage: "Verbose flag",
    },

  }

  app.Run(os.Args)

  if gMemProfileFlag {
    fmem,err := os.Create( gMemProfileFile )
    if err!=nil { panic(fmem) }
    pprof.WriteHeapProfile(fmem)
    fmem.Close()
  }

}

