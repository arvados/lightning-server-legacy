package tile_dbh

import "fmt"
import _ "github.com/mattn/go-sqlite3"
import _ "github.com/lib/pq"
import "database/sql"



type TileDBH struct {
  DBType string
  User string
  DBName string
  Host string
  DBH *sql.DB
}

var TileSeqTable string = "tile_seq"

func Open( DBType, User, Password, DBName, Host string ) (*TileDBH, error) {
  dbh,err := sql.Open( DBType, fmt.Sprintf("user=%s dbname=%s password=%s", User, DBName, Password) )
  if err!=nil { return nil, err }

  tile_h := TileDBH{ DBType, User, DBName, Host, dbh }
  return &tile_h, nil
}

func OpenSqlite3( fn string ) (*TileDBH, error) {
  dbh,err := sql.Open( "sqlite3", fn )
  if err!=nil { return nil,err }

  tile_h := TileDBH{ "sqlite3", "", fn, "", dbh }
  return &tile_h, nil
}

func (dbh *TileDBH) Close() {
  dbh.DBH.Close()
}

func (dbh *TileDBH) GetSeqString( tileid string ) ( string, error ) {
  rows,e := dbh.DBH.Query("select seq from tile_seq where tileid = $1 limit 1", tileid)
  if e!=nil { return "", e }
  defer rows.Close()

  for rows.Next() {
    var seq string
    e = rows.Scan(&seq)
    if e!=nil { return "", e }
    return seq,nil
  }

  return "", fmt.Errorf("tile not found")
}

func (dbh *TileDBH) GetSeqStringDummy( tileid string ) ( string, error ) {
  rows,e := dbh.DBH.Query("select 1 from tile_seq where tileid = $1 limit 1", tileid)
  if e!=nil { return "", e }
  defer rows.Close()

  for rows.Next() {
    var k int
    e = rows.Scan(&k)
    if e!=nil { return "", e }
    return "",nil
  }

  return "", fmt.Errorf("tile not found")
}

func (dbh *TileDBH) GetMd5SumString( tileid string ) ( string, error ) {
  rows,e := dbh.DBH.Query("select md5sum from tile_seq where tileid = $1 limit 1", tileid)
  if e!=nil { return "", e }
  defer rows.Close()

  for rows.Next() {
    var m5 string
    e = rows.Scan(&m5)
    if e!=nil { return "", e }
    return m5,nil
  }

  return "", nil
}



func (dbh *TileDBH) GetTileidString( md5sum string ) ( string, error ) {
  rows,e := dbh.DBH.Query("select tileid from tile_seq where md5sum = $1 limit 1", md5sum)
  if e!=nil { return "", e }
  defer rows.Close()

  for rows.Next() {
    var tid string
    e = rows.Scan(&tid)
    if e!=nil { return "", e }
    return tid,nil
  }

  return "", nil
}



