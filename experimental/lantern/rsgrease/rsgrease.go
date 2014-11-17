package main

import "fmt"
import "os"
import "strconv"
import "strings"

import _ "github.com/lib/pq"
import "database/sql"
import "encoding/json"

import "net/http"
import "io/ioutil"

import "bytes"


import "github.com/codegangsta/cli"

var VERSION_STR string = "0.1, AGPLv3.0"
var g_verboseFlag bool
var g_URL string = "http://localhost:8080"

var g_db *sql.DB

type LightningRequest struct {
  Type string
  Dataset string
  Note string
  SampleId []string
  TileGroupVariantId [][]string
}


//func get_rsid( c *cli.Context ) ([]int, error) {
func get_rsid( rsid_slice []string ) ([]int, error) {
  //rsid_slice := c.StringSlice("rsid")
  rsid := []int{}
  for i:=0; i<len(rsid_slice); i++ {
    st:=0
    if strings.HasPrefix( rsid_slice[i], "rs" ) { st = 2 }
    r,e := strconv.ParseInt( rsid_slice[i][st:], 10, 64 )
    if e!= nil {
      return nil, fmt.Errorf( "Invalid rsid (%s): %v\n", rsid_slice[i], e )
    }
    rsid = append( rsid, int(r) )
  }

  return rsid, nil
}

func get_tile( rsid_list []int ) ( [][]string, error ) {
  var err error

  tileid_group_list := [][]string{}

  g_db,err = sql.Open("postgres", "user=lightning dbname=lightning password=lantern")
  if err!=nil { return nil, err }

  for r:=0; r<len(rsid_list); r++ {
    rsid := rsid_list[r]

    tileid_list := []string{}

    //tileid_rows,e := g_db.Query("select tileid from tile_variant_annotation where rsid = $1 order by tileid asc", rsid)
    tileid_rows,e := g_db.Query("select tileid from tileid_md5 where md5sum in ( select md5sum from rsid_md5 where rsid = $1 ) order by tileid asc", rsid)
    if e!=nil { return nil, e }
    defer tileid_rows.Close()

    for tileid_rows.Next() {
      var tileid string
      err = tileid_rows.Scan(&tileid)
      if err!=nil { return nil, err }
      tileid_list = append( tileid_list, tileid )
    }

    tileid_group_list = append( tileid_group_list, tileid_list )

  }

  return tileid_group_list, nil
}

func send_lightning_request( byte_dat []byte ) {
  //url := "http://localhost:8080"

  req, err := http.NewRequest("POST", g_URL, bytes.NewBuffer( byte_dat ) )
  req.Header.Set("Content-Type", "application/json")

  client := &http.Client{}
  resp, err := client.Do(req)
  if err != nil {
      panic(err)
  }
  defer resp.Body.Close()

  if g_verboseFlag {
    fmt.Println("response Status:", resp.Status)
    fmt.Println("response Headers:", resp.Header)
  }

  body, _ := ioutil.ReadAll(resp.Body)

  if g_verboseFlag {
    fmt.Printf("response Body:")
  }
  fmt.Printf("%s", string(body))

}

func _main( c *cli.Context ) {

  g_verboseFlag = c.Bool("Verbose")
  g_URL = c.String("lightning-host")

  //
  //
  //rsid,e := get_rsid( c )
  rsid,e := get_rsid( c.StringSlice("rsid") )
  if e!=nil {
    fmt.Fprintf( os.Stderr, "Invalid rsid: %v\n", e)
    cli.ShowAppHelp( c )
    os.Exit(1)
  }

  if len(rsid) == 0 {
    fmt.Fprintf( os.Stderr, "Provide at least one rsid\n")
    cli.ShowAppHelp( c )
    os.Exit(1)
  }

  //
  //
  tile_group_list,e := get_tile( rsid )


  req := LightningRequest{ Type:"sample-tile-group-match", Dataset:"all", Note:"...", SampleId:[]string{} }
  req.TileGroupVariantId = tile_group_list

  if g_verboseFlag { fmt.Printf("%v\n", req.TileGroupVariantId ) }

  byte_req,e := json.Marshal( req )
  if e!= nil { panic(e) }
  if g_verboseFlag { fmt.Printf("%s\n", byte_req ) }

  //
  //
  send_lightning_request( byte_req )

}

func main() {

  app := cli.NewApp()
  app.Name  = "rsgrease"
  app.Usage = "Look up tile and/or population information by rsid"
  app.Version = VERSION_STR
  app.Author = "Curoverse Inc."
  app.Email = "info@curoverse.com"
  app.Action = func( c *cli.Context ) { _main(c) }

  app.Flags = []cli.Flag{
    cli.StringSliceFlag{
      Name: "rsid, i",
      Value: &cli.StringSlice{},
      Usage: "rsid",
    },
    cli.StringFlag{
      Name: "lightning-host, H",
      Value: g_URL,
      Usage: "host of lightning server",
    },
    cli.BoolFlag{
      Name: "Verbose, V",
      Usage: "Verbose flag",
    },
  }

  app.Run(os.Args)

}

