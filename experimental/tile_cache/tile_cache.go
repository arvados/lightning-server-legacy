package tile_cache

import "fmt"
import "os"
import "io"
//import "bufio"
//import "encoding/gob"
import "bytes"

import "code.google.com/p/vitess/go/cgzip"


type TileCache struct {
  CompressionType string
  TileIDSeqMap map[string][]byte
  Md5SumSeqMap map[string][]byte
  TileIDMd5SumMap map[string][]byte
  Buf []byte
}

func (cache *TileCache) Init() {
  cache.CompressionType = "utf8"
  cache.TileIDSeqMap = make( map[string][]byte )
  cache.Md5SumSeqMap = make( map[string][]byte )
  cache.TileIDMd5SumMap = make( map[string][]byte )
}


// I'm open to suggestions but this was the fastest way
// I found to load the data I needed.
// Slurp the whole CSV file into memory.  Walk it and
// provide pointers into the buffer as byte slices for
// the TileID and Md5Sum sequence mappings.  Also keep
// the mapping of TileID to Md5Sum.
//
// TileID to Md5Sum mapping is a many-to-one mapping.
//
func (cache *TileCache) LoadTileIDMd5SumSeqCSV( fn string ) error {

  fp,e := os.Open( fn )
  if e!=nil { return(e) }
  defer fp.Close()

  fi,e := fp.Stat()
  if e!=nil { return(e) }

  sz := fi.Size()

  cache.Buf = make( []byte, sz )

  page := int64( 1024 )
  pos := int64( 0 )

  q := sz / page
  for qi:=int64(0) ; qi < q; qi++ {
    tbuf := cache.Buf[pos:pos+page]
    n,e := fp.Read( tbuf )

    if int64(n)!=page {
      panic( fmt.Errorf("did not read %d bytes (got %d)\n", page, n ) )
    }
    if e!=nil { panic(e) }
    pos += page
  }

  r := sz % page
  if r>0 {
    tbuf := cache.Buf[pos:sz]
    n,e := fp.Read( tbuf )
    if int64(n)!=r {
      panic( fmt.Errorf("did not read %d bytes (got %d)\n", page, n ) )
    }
    if e!=nil { panic(e) }
  }


  cache.CompressionType = "utf8"
  cache.Md5SumSeqMap = make( map[string][]byte )
  cache.TileIDSeqMap = make( map[string][]byte )
  cache.TileIDMd5SumMap = make( map[string][]byte )

  field_tot := 3
  field_cur := 0
  field := make( []int, field_tot )
  start_pos := 0

  n:=len(cache.Buf)
  line_no := 0

  for p:=0; p<n; p++ {

    if cache.Buf[p]==',' {
      field[field_cur] = p
      field_cur++
      if field_cur >= field_tot {
        return fmt.Errorf("line_no %d (pos %d), field_cur %d >= field_tot %d\n", line_no, p, field_cur, field_tot)
      }
    }

    if cache.Buf[p]=='\n' {

      tileid := string( cache.Buf[ start_pos : field[0] ] )
      md5sum := string( cache.Buf[ field[0]+1 : field[1] ] ) ; _ = md5sum
      cache.TileIDSeqMap[tileid] = cache.Buf[ field[1]+1 : p ]
      cache.Md5SumSeqMap[md5sum] = cache.Buf[ field[0]+1 : field[1] ]
      cache.TileIDMd5SumMap[tileid] = cache.Buf[ field[0]+1 : field[1] ]
      start_pos = p+1

      line_no++
      field_cur = 0
    }
  }

  if cache.Buf[n-1]!='\n' {
    tileid := string( cache.Buf[ start_pos : field[0] ] )
    md5sum := string( cache.Buf[ field[0]+1 : field[1] ] ) ; _ = md5sum
    cache.TileIDSeqMap[tileid] = cache.Buf[ field[1]+1 : n ]
    cache.Md5SumSeqMap[md5sum] = cache.Buf[ field[0]+1 : field[1] ]
    cache.TileIDMd5SumMap[tileid] = cache.Buf[ field[0]+1 : field[1] ]

    line_no++
  }

  return nil
}

func (cache *TileCache) SaveTileIDMd5SumSeqCSV( fn string ) error {
  fp,err := os.Create( fn )
  if err!=nil { return err }
  defer fp.Close()

  for k,v := range cache.TileIDSeqMap {
    m5,ok := cache.TileIDMd5SumMap[ k ]
    if !ok { return fmt.Errorf("could not find md5sum for tileid '%s'", k) }
    fmt.Fprintf( fp, "%s,%s,%s\n", k, m5, v )
  }

  return nil

}


// Deprecated
// Gobs have a 1GB memory limit
//
/*
func LoadCacheGob( fn string ) (*TileCache, error) {
  fp,err := os.Open( fn )
  if err!=nil { return nil,err }
  defer fp.Close()

  cache := TileCache{}
  cache.SeqMap = make( map[string][]byte )

  dec := gob.NewDecoder( fp )
  e := dec.Decode( &cache )
  if e!=nil { return nil,e }

  return &cache,nil
}

func (cache *TileCache) SaveCacheGob( fn string ) error {
  fp,err := os.Create( fn )
  if err!=nil { return err }
  defer fp.Close()

  gob_writer := bufio.NewWriter( fp )

  enc := gob.NewEncoder( gob_writer )
  e := enc.Encode( cache )
  if e!=nil { return e }

  gob_writer.Flush()

  return nil
}
*/

func (cache *TileCache) Exists( tileid string ) bool {
  _,ok := cache.TileIDSeqMap[tileid]
  return ok
}

// Compresses and puts it in the cache, overwritting if already
// preseent.
//
// Return true if overwritten.
//
func (cache *TileCache) SetSeq( tileid string, seq []byte ) bool {

  _,overwritten := cache.TileIDSeqMap[tileid]

  if cache.CompressionType == "gz" {
    var b bytes.Buffer
    w := cgzip.NewWriter( &b )
    w.Write( seq )
    w.Flush()
    w.Close()

    cache.TileIDSeqMap[tileid] = b.Bytes()
  } else {
    //cache.TileIDSeqMap[tileid] = []byte{}
    //copy( cache.TileIDSeqMap[tileid], seq )

    cache.TileIDSeqMap[tileid] = append( []byte{}, seq... )
  }

  return overwritten

}

// Get the uncompressed sequence.
//
// Returns byte sequence if found, flag indicating whether it was found
// or error on error.
//
func (cache *TileCache) GetSeq( tileid string ) ([]byte, bool, error) {
  b,ok := cache.TileIDSeqMap[tileid]
  if !ok { return nil, ok, nil }

  if cache.CompressionType == "gz" {

    bb := bytes.NewBuffer( b )
    gzreader,e := cgzip.NewReader( bb )
    if e!=nil { return nil, false, e }

    var buf []byte

    tot_read := 0

    tbuf := make( []byte, 1024 )
    nread,e := gzreader.Read( tbuf ) ; _ = nread
    buf = append(buf, tbuf...)
    tot_read += nread
    for e!=io.EOF {
      nread,e = gzreader.Read( tbuf )
      buf = append(buf, tbuf...)
      tot_read += nread
    }

    if tot_read==0 { return nil, false, fmt.Errorf("zero length") }
    return buf[0:tot_read], true, nil
  } else {
    return b,true,nil
  }
}

// Don't return the sequnce (and don't uncompress).
// Used for testing purposes.
//
func (cache *TileCache) GetSeqDummy( tileid string ) ([]byte, bool, error) {
  b,ok := cache.TileIDSeqMap[tileid]
  if !ok { return nil, ok, nil }

  _ = b

  return []byte{}, true, nil
}
