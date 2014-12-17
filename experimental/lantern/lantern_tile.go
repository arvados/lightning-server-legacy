package main

import "fmt"
import "../tile_cache"
import "../tile_dbh"

//var gTileCacheGob string = "./tile_cache.gob"
var gTileCacheCSV string = "./tile_seq_first6.csv"
var gTileCache *tile_cache.TileCache

var gTileDB string = "./tiledb.sqlite3"
var gTileDBH *tile_dbh.TileDBH

type LanternTileStats struct {
  Total int
  CacheHit int
  CacheMiss int
  DBHit int
  DBMiss int
}

var gLanternTileStats LanternTileStats = LanternTileStats{}

func TileInit( cache_csv_fn , db_fn string ) (e error) {
  //gTileCache,e  = tile_cache.LoadCacheGob( cache_gob_fn )
  gTileCache = &tile_cache.TileCache{}
  e = gTileCache.LoadTileIDMd5SumSeqCSV( cache_csv_fn )

  if e!=nil { return e }
  gTileDBH,e = tile_dbh.OpenSqlite3( db_fn )
  if e!=nil { return e }

  return nil
}

func TileSimpleInit() (e error) {
  //return TileInit( gTileCacheGob, gTileDB )
  return TileInit( gTileCacheCSV , gTileDB )
}

func GetTileSeq( tileid string ) (string,error) {
  gLanternTileStats.Total++

  bseq,ok,err := gTileCache.GetSeq( tileid )
  if err!=nil { return "",err }
  if ok {
    gLanternTileStats.CacheHit++
    return string(bseq),nil
  }

  gLanternTileStats.CacheMiss++

  seq,e := gTileDBH.GetSeqString( tileid )
  if e!=nil {
    gLanternTileStats.DBMiss++
    return "",e
  }

  gLanternTileStats.DBHit++
  return seq,nil
}

func GetTileSeqDummy( tileid string ) (string,error) {
  gLanternTileStats.Total++

  bseq,ok,err := gTileCache.GetSeqDummy( tileid )
  if err!=nil { return "",err }
  if ok {
    gLanternTileStats.CacheHit++
    return string(bseq),nil
  }

  gLanternTileStats.CacheMiss++

  seq,e := gTileDBH.GetSeqStringDummy( tileid )
  if e!=nil {
    gLanternTileStats.DBMiss++
    return "",e
  }

  gLanternTileStats.DBHit++
  return seq,nil
}

func TileStatsPrint() {
  fmt.Printf("Total:%d,CacheHit:%d,CacheMiss:%d,DBHit:%d,DBMiss:%d\n",
    gLanternTileStats.Total,
    gLanternTileStats.CacheHit, gLanternTileStats.CacheMiss,
    gLanternTileStats.DBHit, gLanternTileStats.DBMiss )
}
