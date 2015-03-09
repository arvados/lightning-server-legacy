package main

import "fmt"
import "os"
import "crypto/md5"

import "log"

import "github.com/abeconnelly/autoio"
import "github.com/abeconnelly/sloppyjson"
import "github.com/codegangsta/cli"


var VERSION_STR string = "0.2.0, AGPLv3.0"

var g_verboseFlag bool
var g_tagLength int

func init() {
}


func md5Ascii( b [16]byte ) (s []byte) {
  for i:=0; i<len(b); i++ {
    t := fmt.Sprintf("%02x", b[i] )
    s = append( s, []byte(t)... )
  }
  return s
}

func tile_check( sj *sloppyjson.SloppyJSON, seq []byte ) error {

  // Check nocall count
  //
  nocall := 0
  for i:=0; i<len(seq); i++ {
    if seq[i] == 'n' || seq[i] == 'N' { nocall++ }
  }
  if nocall != int( sj.O["nocallCount"].P + 0.5 ) {
    return fmt.Errorf( "ERROR: nocall mismmatch (%d != %g)", nocall, sj.O["nocallCount"].P )
  }

  // Check length
  //
  n := len(seq)
  if n != int( sj.O["n"].P + 0.5 ) {
    return fmt.Errorf( "ERROR: length mismmatch (%d != %g)", n, sj.O["n"].P )
  }

  // Check begin/end of tile
  //
  if (sj.O["startTile"].Y == "true") {
    if len( sj.O["startTag"].S ) != 0 {
      return fmt.Errorf( "ERROR: startTile but len(startTag) != 0 (len(startTag) %d)", len( sj.O["startTag"].S ) )
    }
  } else if len( sj.O["startTag"].S ) != g_tagLength {

    fmt.Printf(">>>>> %v %v %v %v --> %v\n", sj.O["startTile"].Y, sj.O["startTag"].S, sj.O["startSeq"].S, "???", sj.O["startTile"].Y == "true"  )

    return fmt.Errorf( "ERROR: len(startTag) != %d (len(startTag)=%d (startTile %s))", g_tagLength, len(sj.O["startTag"].S), sj.O["startTile"].Y )
  }

  if sj.O["endTile"].Y == "true" {
    if len( sj.O["endTag"].S ) != 0 {
      return fmt.Errorf( "ERROR: endTile but len(endTag) != 0 (len(endTag) %d)", len( sj.O["endTag"].S ) )
    }
  } else if len( sj.O["endTag"].S ) != g_tagLength {
    return fmt.Errorf( "ERROR: len(endTag) != %d (len(endTag) %d)", g_tagLength, len( sj.O["endTag"].S ) )
  }

  // Check begin/end sequence tag
  m := len( sj.O["startSeq"].S )
  if string(seq[0:m]) != sj.O["startSeq"].S {
    return fmt.Errorf( "ERROR: startSeq != seq[%d:%d] ('%s' != '%s')", 0, m, string(seq[0:m]), sj.O["startSeq"].S )
  }

  m = len( sj.O["endSeq"].S )
  if string(seq[n-m:n]) != sj.O["endSeq"].S {
    return fmt.Errorf( "ERROR: endSeq != seq[%d:%d] ('%s' != '%s')", n-m, n, string(seq[n-m:n]), sj.O["endSeq"].S )
  }

  b := md5.Sum( []byte(seq) )
  m5str := string( md5Ascii(b) )

  if m5str != sj.O["md5sum"].S {
    return fmt.Errorf( "ERROR: md5sums do not match ('%s' != '%s')", m5str, sj.O["md5sum"].S )
  }


  return nil
}

func _main( c *cli.Context ) {
  g_verboseFlag = c.Bool("Verbose")
  g_tagLength = c.Int("tag-length")

  if len( c.String("input-fastj")) == 0 {
    fmt.Fprintf( os.Stderr, "Provide input FastJ file\n" )
    cli.ShowAppHelp( c )
    os.Exit(1)
  }

  if g_verboseFlag {
    fmt.Printf("g_tagLength: %d\n", g_tagLength)
  }

  scanner,err := autoio.OpenReadScanner( c.String("input-fastj") )
  if err != nil {
    fmt.Fprintf( os.Stderr, "%v", err )
    os.Exit(1)
  }
  defer scanner.Close()

  var e error
  var sj *sloppyjson.SloppyJSON
  var seq []byte

  first_pass := true
  line_no:=0

  for scanner.ReadScan() {
    line_no++

    l := scanner.ReadText()
    if len(l)==0 { continue }
    if l[0]=='>' {

      if !first_pass {
        e = tile_check( sj, seq )
        if e != nil { log.Fatal( fmt.Sprintf("%v (line_no %d)", e, line_no) ) }
      }
      first_pass=false

      seq = seq[0:0]

      sj,e = sloppyjson.Loads( l[1:] ) ; _ = sj
      if e!=nil { log.Fatal(e) }

      continue
    }

    seq = append(seq, []byte(l)... )
  }

  if !first_pass {
    e = tile_check( sj, seq )
    if e != nil { log.Fatal(e) }
  }

  fmt.Printf("ok\n");

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



