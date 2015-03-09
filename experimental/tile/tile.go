package tile

import "fmt"
import "bufio"
import "strings"
import "os"

import "bytes"

import "strconv"
import "sort"

import "encoding/json"

import "errors"

import "../recache"
import "../aux"

var VERSION_STR string = "0.2"

type TileHeader struct {
  TileID string `json:"tileID"`
  Md5Sum string `json:"md5sum"`
  Locus []map[ string ]string `json:"locus"`
  N int `json:"n"`

  NocallCount int `json:"nocallCount"`
  StartTile bool `json:"startTile"`
  endTile bool `json:"endTile"`

  StartTag string `json:"startTag"`
  EndTag string `json:"endTag"`

  StartSeq string `json:"startSeq"`
  EndSeq string `json:"endSeq"`

  Notes []string `json:"notes,omitempty"`
}



// Current TileId format is:
//
// Band.Revision.Pos.Copy
//
// (as a string).  For example:
//
// "2f.0.ae2.1"
//
// Which would represent band 47, revision 0,
// position (in band, 0 referenced) 2786, copy 1
//
//
// BaseTileId is just the Band.Revision.Pos
// (without the Copy number).
//
type TileCopyCollection struct {

  // For any given tile, the start and end tag
  // must be the same, regardless of copy.
  //
  StartTag, EndTag string
  BaseTileId string

  // Header information, stored as a string.
  // BaseTileId is key.
  //
  Meta map[int]string
  MetaJson map[int]TileHeader

  // There will be a different body dependant on
  // copy number.
  // Key is copy number
  //
  Body map[int]string

}

type TileSet struct {

  // key is base tile id ("band.revision.pos")
  //
  TileCopyCollectionMap map[string]TileCopyCollection

  // Key is (24bp) tag and value is base tile ID
  //
  TagToTileId map[string]string

  // Key is base til eID and value is (24bp) tag
  //
  TileIdToTag map[string]string

  TagLength int
  LineWidth int

  Version string

}

//---

func NewTileSet( tagLength int ) *TileSet {
  ts := &TileSet{ TagLength: tagLength,
                  TagToTileId: make( map[string]string ),
                  TileIdToTag: make( map[string]string ),
                  LineWidth: 50,
                  TileCopyCollectionMap: make( map[string]TileCopyCollection ),
                  Version : VERSION_STR }
  return ts
}

//---

func (ts *TileSet) getBaseTileId ( tileId string ) string {
  //var band, revision, pos, copyNum int
  //fmt.Sscanf( tileId, "%x.%x.%x.%x", &band, &revision, &pos, &copyNum )
  //return fmt.Sprintf( "%x.%x.%x", band, revision, pos )

  n := len(tileId)
  p:=n-1
  for ; (p>=0) && (tileId[p] != '.'); p-- { }

  return tileId[:p];
}

func (ts *TileSet) getCanonicalTileId ( tileId string ) string {
  var band, revision, pos, copyNum int
  fmt.Sscanf( tileId, "%x.%x.%x.%x", &band, &revision, &pos, &copyNum )
  return fmt.Sprintf( "%03x.%02x.%03x.%03x", band, revision, pos, copyNum )
}

func (ts *TileSet) getCopyNumber ( tileId string ) int {
  /*
  var band, revision, pos, copyNum int
  fmt.Sscanf( tileId, "%x.%x.%x.%x", &band, &revision, &pos, &copyNum )
  return copyNum
  */

  n := len(tileId)
  p:=n-1
  for ; (p>=0) && (tileId[p] != '.'); p-- { }
  k,_ := strconv.Atoi( tileId[p+1:] )
  return k


}

//---

func (ts *TileSet) getStartTag ( tileSeq string ) string {
  if len(tileSeq) < 2*ts.TagLength { return "" }
  b := make( []byte, ts.TagLength )
  n := len(tileSeq)

  for i:=0; i<n && i<ts.TagLength; i++ {
    b[i] = tileSeq[i]
  }
  return string(b)
}

func (ts *TileSet) getEndTag ( tileSeq string ) string {
  if len(tileSeq) < 2*ts.TagLength { return "" }
  b := make( []byte, ts.TagLength )
  n := len(tileSeq)

  for i, k := n-1, 0; (i >= 0) && (k < ts.TagLength); i-- {
    b[k] = tileSeq[ n + k - ts.TagLength ]
    k++
  }

  return string(b)
}

func (ts *TileSet) getTileBody ( tileSeq string ) string {

  return string(tileSeq)

  if len(tileSeq) < 2*ts.TagLength { return "" }
  n := len(tileSeq) - ts.TagLength
  b := make( []byte, n - ts.TagLength )

  for i, k := ts.TagLength, 0;  i<n; i++ {
    b[k] = tileSeq[i]
    k++
  }
  return string(b)
}


// Add Tile to tile set.
//
// tileSeq has the start and end tags included.
//
// TagToTileId and TileIdToTag map will be updated with
// the tileId and start tag.
//
//
func (ts *TileSet) AddTile( tileId string, tileSeq string, meta string ) {

  baseId := ts.getBaseTileId( tileId )
  copyNum := ts.getCopyNumber( tileId )

  sTag := strings.ToLower( ts.getStartTag( tileSeq ) )
  eTag := strings.ToLower( ts.getEndTag( tileSeq ) )

  body := strings.ToLower( ts.getTileBody( tileSeq ) )

  ts.TagToTileId[ sTag ]   = baseId
  ts.TileIdToTag[ baseId ] = sTag

  if _,found := ts.TileCopyCollectionMap[ baseId ] ; !found {
    ts.TileCopyCollectionMap[ baseId ] =
      TileCopyCollection{ StartTag:sTag,
                          EndTag:eTag,
                          BaseTileId:baseId,
                          Meta: make( map[int]string ),
                          MetaJson: make( map[int]TileHeader ),
                          Body: make( map[int]string ) }
  }

  ts.TileCopyCollectionMap[ baseId ].Body[ copyNum ] = body
  ts.TileCopyCollectionMap[ baseId ].Meta[ copyNum ] = meta

  header := TileHeader{}
  json.Unmarshal( []byte( meta ), &header )

  header.TileID    = tileId
  header.StartTag  = sTag
  header.EndTag    = eTag
  header.N         = len(tileSeq)
  //header.CopyNum   = copyNum+1
  header.Notes     = append(header.Notes, ts.TileCopyCollectionMap[ baseId ].MetaJson[ copyNum ].Notes... )

  ts.TileCopyCollectionMap[ baseId ].MetaJson[ copyNum ] = header

}


func (ts *TileSet) AddTileNotes( tileId string, notes []string ) {

  baseId := ts.getBaseTileId( tileId )
  copyNum := ts.getCopyNumber( tileId )

  if _,found := ts.TileCopyCollectionMap[ baseId ] ; !found {
    return
  }

  x := ts.TileCopyCollectionMap[ baseId ].MetaJson[ copyNum ]
  x.Notes = append( x.Notes, notes... )
  ts.TileCopyCollectionMap[ baseId ].MetaJson[ copyNum ] = x

}


// Remove tile from set (not implemented)
//
func (ts *TileSet) RemTile( tileId string ) {
}


// Get the whole tile sequence from tile ID
//
func (ts *TileSet) GetTileSequence( tileId string ) string {
  baseId := ts.getBaseTileId( tileId )
  copyNum := ts.getCopyNumber( tileId )

  if _,ok := ts.TileCopyCollectionMap[ baseId ]; !ok {
    return ""
  }

  sTag := ts.TileCopyCollectionMap[ baseId ].StartTag
  body := ts.TileCopyCollectionMap[ baseId ].Body[ copyNum ]
  eTag := ts.TileCopyCollectionMap[ baseId ].EndTag

  return fmt.Sprintf( "%s%s%s", sTag, body, eTag )
}


/*
func (ts *TileSet) GetTileByTag( startTag string ) TileCopyCollection {
}
*/


// Print fastj tile to stdout
//
func (ts *TileSet) PrintFastjTile( tileId string ) {
  stdout := bufio.NewWriter( os.Stdout )
  ts.WriteFastjTile( stdout, tileId )
}


// Print fastj tile to stream
//
func (ts *TileSet) WriteFastjTile( writer *bufio.Writer, tileId string ) {
  lineWidth := ts.LineWidth

  baseId := ts.getBaseTileId( tileId )
  copyNum := ts.getCopyNumber( tileId )

  sTag := ts.TileCopyCollectionMap[ baseId ].StartTag
  body := ts.TileCopyCollectionMap[ baseId ].Body[ copyNum ]
  eTag := ts.TileCopyCollectionMap[ baseId ].EndTag


  //cTileId := ts.getCanonicalTileId( tileId )

  /*
  //writer.WriteString( fmt.Sprintf("> { \"tileID\":\"%s\", ", tileId) )
  writer.WriteString( fmt.Sprintf("> { \"tileID\":\"%s\", ", cTileId) )
  writer.WriteString( fmt.Sprintf("\"n\":\"%d\", ", len(sTag) + len(body) + len(eTag) ) )
  writer.WriteString( fmt.Sprintf("\"copy\":\"%d\", ", copyNum) )
  writer.WriteString( fmt.Sprintf("\"startTag\":\"%s\", ", sTag) )
  writer.WriteString( fmt.Sprintf("\"endTag\":\"%s\" }\n", eTag) )
  */
  //writer.WriteString( fmt.Sprintf(">%s\n", ts.TileCopyCollectionMap[ baseId ].Meta[ copyNum ] ) )

  x := ts.TileCopyCollectionMap[ baseId ].MetaJson[ copyNum ]
  meta,_ := json.Marshal( &x )
  writer.WriteString( fmt.Sprintf(">%s\n", string(meta) ) )

  seq := []byte( fmt.Sprintf("%s%s%s", sTag, body, eTag ) )
  n := len(seq)

  for i:=0; i<n; i++ {
    if i>0 && (i%lineWidth)==0 {
      writer.WriteString("\n")
    }
    writer.WriteByte( seq[i] )
  }
  writer.WriteString("\n\n")

  writer.Flush()
}

// Write whole fastj file.
//
func (ts *TileSet) WriteFastj( writer *bufio.Writer ) {

  sortedBaseId := make([]string, len( ts.TileCopyCollectionMap ))
  i := 0
  for k,_ := range ts.TileCopyCollectionMap {
    sortedBaseId[i] = k
    i++
  }
  sort.Strings( sortedBaseId )

  for i:=0 ; i<len(sortedBaseId) ; i++ {
    baseId := sortedBaseId[i]
    for copyNum,_ := range ts.TileCopyCollectionMap[ baseId ].Body {
      tileId := fmt.Sprintf( "%s.%x", baseId, copyNum )
      ts.WriteFastjTile( writer, tileId )
    }

    writer.WriteString("\n\n")

  }

  writer.Flush()

}

// Write whole fastj file.
// There's still an issue of sorting the output by tileId
//
func (ts *TileSet) WriteFastjFile( filename string ) error {

  fp,err := os.Create( filename )
  if err != nil { return err }
  defer fp.Close()

  writer := bufio.NewWriter( fp )
  ts.WriteFastj( writer )

  return nil
}

func (ts *TileSet) ReadFastjFile( fastjFn string ) error {

  fp,scanner,err := aux.OpenScanner( fastjFn )
  if err != nil { return err }
  defer fp.Close()

  return ts.FastjScanner( scanner )

}

func (ts *TileSet) FastjScanner( scanner *bufio.Scanner ) error {

  var header string
  var seq bytes.Buffer
  var tileId string

  line_count := 0

  /*
  fp,scanner,err := aux.OpenScanner( fastjFn )
  if err != nil { panic(err) }
  defer fp.Close()
  */

  for scanner.Scan() {
    l := scanner.Text()

    line_count++

    if b,_ := recache.MatchString( `^#`, l )    ; b { continue }
    if b,_ := recache.MatchString( `^\s*$`, l ) ; b { continue }

    if b,_ := recache.MatchString( `^>`, l ) ; b {

      // write previous entry
      //
      if (seq.Len() > 0) && (len(header) > 0) {

        if b,_ := recache.MatchString( `[^\.]+\.[^\.]+\.[^\.]+\.[^\.]+`, tileId ) ; !b {
          return errors.New( fmt.Sprintf("Invalid tileId ('%s').  Current line %d", tileId, line_count) )
          //panic( fmt.Sprintf("Invalid tileId ('%s') in file %s.  Current line %d", tileId, fastjFn, line_count) )
        }

        ts.AddTile( tileId, seq.String(), header )

      }

      tileIDs,_ := recache.FindAllStringSubmatch( `"tileI[Dd]"\s*:\s*"([^\.]+)\.([^\.]+)\.([^\.]+)\.([^"]+)"`, l, -1 )

      tileId =
        fmt.Sprintf( "%s.%s.%s.%s", tileIDs[0][1], tileIDs[0][2], tileIDs[0][3], tileIDs[0][4] )

      header = l[1:]
      seq.Reset()

      continue

    }

    for i:=0; i<len(l); i++ {
      if (l[i] != '\n') || (l[i] != ' ') {
        seq.WriteByte( l[i] )
      }
    }

  }

  // write last entry
  //
  if (seq.Len() > 0) && (len(header) > 0) {

    //DEBUG
    //fmt.Println( "adding...(", tileId, ")\n", seq.String(), "\nheader:", header, "\n\n" )

    ts.AddTile( tileId, seq.String(), header )

  }


  return nil

}

// Print out state of TileSet
//
func (ts *TileSet) DebugPrint() {

  fmt.Println("TagLength:", ts.TagLength)
  fmt.Println()

  fmt.Println("TagToTileId:", len(ts.TagToTileId) )
  for k,v := range ts.TagToTileId {
    fmt.Println( "  ", k, v )
  }
  fmt.Println()

  fmt.Println("TileIdToTag:", len(ts.TileIdToTag) )
  for k,v := range ts.TileIdToTag{
    fmt.Println( "  ", k, v )
  }
  fmt.Println()


  fmt.Println("TileCopyCollectionMap:", len(ts.TileCopyCollectionMap) )
  for k,v := range ts.TileCopyCollectionMap {
    fmt.Println("  ", k, "(", v.BaseTileId, ")", "[", v.StartTag, ",", v.EndTag, "]")
    for k2,v2 := range v.Body {
      fmt.Println("    CopyNum:", k2, "Body:", v2)
    }
  }


}
