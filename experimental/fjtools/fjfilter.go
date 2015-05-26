/*

    Copyright (C) 2015 Curoverse, Inc.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

*/

package main

import "fmt"
import "os"

import "log"

import "strings"
import "strconv"

import "github.com/abeconnelly/autoio"
import "github.com/abeconnelly/sloppyjson"
import "github.com/codegangsta/cli"


var VERSION_STR string = "0.1.0, AGPLv3.0"

var g_verboseFlag bool

var g_beg_path int64
var g_beg_ver int64
var g_beg_step int64
var g_beg_variant int64

var g_end_path int64
var g_end_ver int64
var g_end_step int64
var g_end_variant int64

func init() {

  g_beg_path    = -1
  g_beg_ver     = -1
  g_beg_step    = -1
  g_beg_variant = -1

  g_end_path    = -1
  g_end_ver     = -1
  g_end_step    = -1
  g_end_variant = -1

}

func parse_filter(s string, path, ver, step, variant *int64) {
  parts := strings.Split(s, ".")
  if (len(parts)<2) || (len(parts)>4) {
    return
  }

  if len(parts)==2 {
    path_str := parts[0]
    step_str := parts[1]

    p,e := strconv.ParseInt(path_str, 16, 32)
    if e!=nil { return }
    s,e := strconv.ParseInt(step_str, 16, 32)
    if e!=nil { return }

    *path = p
    *step = s
    return
  }

  if len(parts)==3 {
    path_str := parts[0]
    ver_str := parts[1]
    step_str := parts[2]

    p,e := strconv.ParseInt(path_str, 16, 32)
    if e!=nil { return }
    v,e := strconv.ParseInt(ver_str, 16, 32)
    if e!=nil { return }
    s,e := strconv.ParseInt(step_str, 16, 32)
    if e!=nil { return }

    *path = p
    *ver = v
    *step = s

    return
  }

  if len(parts)==4 {
    path_str := parts[0]
    ver_str := parts[1]
    step_str := parts[2]
    variant_str := parts[3]


    p,e := strconv.ParseInt(path_str, 16, 32)
    if e!=nil { return }
    v,e := strconv.ParseInt(ver_str, 16, 32)
    if e!=nil { return }
    s,e := strconv.ParseInt(step_str, 16, 32)
    if e!=nil { return }
    va,e := strconv.ParseInt(variant_str, 16, 32)
    if e!=nil { return }

    *path = p
    *ver = v
    *step = s
    *variant = va

    return
  }
}

func pass_filter(tileid string, seed_tile_len int) bool {
  parts := strings.Split(tileid, ".")
  if len(parts)!=4 { return false }

  path,e := strconv.ParseInt(parts[0], 16, 32)
  if e!=nil { return false }

  ver,e := strconv.ParseInt(parts[1], 16, 32)
  if e!=nil { return false }

  step,e := strconv.ParseInt(parts[2], 16, 32)
  if e!=nil { return false }

  variant,e := strconv.ParseInt(parts[3], 16, 32)
  if e!=nil { return false }

  if (g_beg_path>=0) && (path<g_beg_path) { return false }
  if (g_end_path>=0) && (path>g_end_path) { return false }

  if (g_beg_ver>=0) && (ver<g_beg_ver) { return false }
  if (g_end_ver>=0) && (ver>g_end_ver) { return false }

  if (g_beg_step>=0) && ((step+int64(seed_tile_len))<g_beg_step) { return false }
  if (g_end_step>=0) && (step>g_end_step) { return false }

  if (g_beg_variant>=0) && (variant<g_beg_variant) { return false }
  if (g_end_variant>=0) && (variant>g_end_variant) { return false }

  return true

}

func _main( c *cli.Context ) {
  g_verboseFlag = c.Bool("Verbose")

  beg_str := c.String("start")
  end_str := c.String("end")

  if len(beg_str)>0 {
    parse_filter(beg_str, &g_beg_path, &g_beg_ver, &g_beg_step, &g_beg_variant)
  }

  if len(end_str)>0 {
    parse_filter(end_str, &g_end_path, &g_end_ver, &g_end_step, &g_end_variant)
  }

  if len( c.String("input-fastj")) == 0 {
    fmt.Fprintf( os.Stderr, "Provide input FastJ file\n" )
    cli.ShowAppHelp( c )
    os.Exit(1)
  }

  scanner,err := autoio.OpenReadScannerSimple( c.String("input-fastj") )
  if err != nil {
    fmt.Fprintf( os.Stderr, "%v", err )
    os.Exit(1)
  }
  defer scanner.Close()

  h_line := ""
  fold_width := 50

  first_pass := true

  line_no:=0
  seq := make( []byte, 300 )

  var prev_tileid string
  var prev_seed_tile_len int

  for scanner.ReadScan() {
    line_no++

    l := scanner.ReadText()
    if len(l)==0 { continue }
    if l[0]=='>' {

      sj,e := sloppyjson.Loads(l[1:])
      if e!=nil { log.Fatal(e) }

      tileid := sj.O["tileID"].S
      seed_tile_len := int(sj.O["seedTileLength"].P)

      if !first_pass {
        if pass_filter(prev_tileid, prev_seed_tile_len) {
          fmt.Printf("%s\n", h_line)
          p:=0
          for ; p<(len(seq)-fold_width); p+=fold_width {
            fmt.Printf("%s\n", seq[p:p+fold_width])
          }
          if p<len(seq) { fmt.Printf("%s\n", seq[p:]) }
          fmt.Printf("\n")
        }
      }

      first_pass = false

      h_line = l
      seq = seq[0:0]
      prev_tileid=tileid
      prev_seed_tile_len = seed_tile_len

      continue
    }

    seq = append(seq, []byte(l)... )
  }

  if !first_pass {
    if pass_filter(prev_tileid, prev_seed_tile_len) {
      fmt.Printf("%s\n", h_line)
      p:=0
      for ; p<(len(seq)-fold_width); p+=fold_width {
        fmt.Printf("%s\n", seq[p:p+fold_width])
      }
      if p<len(seq) { fmt.Printf("%s\n", seq[p:]) }
      fmt.Printf("\n")
    }
  }

}


func main() {

  app := cli.NewApp()
  app.Name  = "fjdup"
  app.Usage = "..."
  app.Version = VERSION_STR
  app.Author = "Curoverse Inc."
  app.Email = "info@curoverse.com"
  app.Action = func( c *cli.Context ) { _main(c) }

  app.Flags = []cli.Flag{
    cli.StringFlag{
      Name: "input-fastj, i",
      Usage: "Input FastJ",
    },

    cli.StringFlag{
      Name: "start, s",
      Usage: "start filter (inclusive)",
    },

    cli.StringFlag{
      Name: "end, e",
      Usage: "end filter (inclusive)",
    },

    cli.BoolFlag{
      Name: "Verbose, V",
      Usage: "Verbose flag",
    },
  }

  app.Run(os.Args)

}



