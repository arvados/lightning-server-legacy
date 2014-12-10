package tile_cache

import _ "fmt"
import "os"
import "io"
import "bufio"
import "encoding/gob"
import "bytes"

import "code.google.com/p/vitess/go/cgzip"


type TileCache struct {
  SeqMap map[string][]byte
}

func (cache *TileCache) Init() {
  cache.SeqMap = make( map[string][]byte )
}

func LoadCacheGob( fn string ) (*TileCache, error) {
  fp,err := os.Open( fn )
  if err!=nil { return nil,err }
  defer fp.Close()

  cache := TileCache{}
  cache.SeqMap = make( map[string][]byte )

  dec := gob.NewDecoder( fp )
  e := dec.Decode( &(cache.SeqMap) )
  if e!=nil { return nil,e }

  return &cache,nil
}


func (cache *TileCache) SaveCacheGob( fn string ) error {
  fp,err := os.Create( fn )
  if err!=nil { return err }
  defer fp.Close()

  gob_writer := bufio.NewWriter( fp )

  enc := gob.NewEncoder( gob_writer )
  e := enc.Encode( cache.SeqMap )
  if e!=nil { return e }

  gob_writer.Flush()

  return nil
}

func (cache *TileCache) Exists( tileid string ) bool {
  _,ok := cache.SeqMap[tileid]
  return ok
}

// Compresses and puts it in the cache, overwritting if already
// preseent.
//
// Return true if overwritten.
//
func (cache *TileCache) SetSeq( tileid string, seq []byte ) bool {
  var b bytes.Buffer
  w := cgzip.NewWriter( &b )
  w.Write( seq )
  w.Flush()
  w.Close()

  _,overwritten := cache.SeqMap[tileid]

  cache.SeqMap[tileid] = b.Bytes()

  return overwritten

}

// Get the uncompressed sequence.
//
func (cache *TileCache) GetSeq( tileid string ) ([]byte, bool, error) {
  b,ok := cache.SeqMap[tileid]
  if !ok { return nil, ok, nil }

  bb := bytes.NewBuffer( b )
  gzreader,e := cgzip.NewReader( bb )
  if e!=nil { return nil, false, e }

  var buf []byte

  tot_read := 0

  tbuf := make( []byte, 1024 )
  nread,e := gzreader.Read( tbuf ) ; _ = nread
  tbuf = append(tbuf, buf...)
  tot_read += nread
  for e!=io.EOF {
    nread,e = gzreader.Read( tbuf )
    tbuf = append(tbuf, buf...)
    tot_read += nread
  }

  return tbuf[0:tot_read], true, nil
}
