package tile_cache

import "os"
import _ "fmt"
import "testing"
import "io/ioutil"

func TestAll( t *testing.T ) {

  cache := TileCache{}
  cache.Init()

  tseq := []byte{}
  tseq = append(tseq, []byte("actgactgactg")... )

  ok0 := cache.SetSeq( "xx", tseq )
  if ok0 { t.Errorf("xx already found!") }

  seq,ok,e := cache.GetSeq( "xx" )
  if e!=nil { t.Errorf("%v", e) }
  if !ok { t.Errorf("xx not found!") }
  if string(seq) != string(tseq) { t.Errorf("found sequence mismatch, expected '%s' (%d) got '%s' (%d)", tseq, len(tseq), seq, len(seq) ) }

  seq,ok,e = cache.GetSeq( "yy" )
  if e!=nil { t.Errorf("%v", e) }
  if ok { t.Errorf("yy found but shouldn't exist!") }


  fngob,ferr := ioutil.TempFile( "", "" )
  if ferr != nil { t.Error( ferr ) }

  e = cache.SaveCacheGob( fngob.Name() )
  if e!=nil { t.Errorf("%v", e) }

  ehcac,err := LoadCacheGob( fngob.Name() )
  if err!=nil { t.Errorf("%v", err) }

  seq,ok,e = ehcac.GetSeq( "xx" )
  if e!=nil { t.Errorf("%v", e) }
  if !ok { t.Errorf("xx not found!") }
  if string(seq) != string(tseq) { t.Errorf("found sequence mismatch, expected '%s' (%d) got '%s' (%d)", tseq, len(tseq), seq, len(seq) ) }

  seq,ok,e = ehcac.GetSeq( "yy" )
  if e!=nil { t.Errorf("%v", e) }
  if ok { t.Errorf("yy found but shouldn't exist!") }


  e = os.Remove( fngob.Name() )
  if e!=nil { t.Errorf("%v", e) }

}
