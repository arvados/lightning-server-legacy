//
//
package main

import "fmt"
import "os"
import "./aux"
import "strconv"
import "bufio"
import "strings"

import "./recache"
import "./tile"

import "sort"
import "encoding/json"
import "compress/gzip"

var CYTOMAP_FILENAME string
var BAND_BOUNDS map[string]map[int][2]int

var gDebugString string
var gDebugFlag bool

var gNoteLine string

type TileHeader struct {
  TileID string `json:"tileID"`
  Locus []map[ string ]string `json:"locus"`
  N int `json:"n"`
  CopyNum int `json:"copy"`
  StartTag string `json:"startTag"`
  EndTag string `json:"endTag"`
  Notes []string `json:"notes,omitempty"`
}


type GffScanState struct {
  nextTagStart int

  startPos []int
  startPosIndex int

  gffCurSeq []byte

  refStart, refLen int

  notes []string

  simpleLocusBuild string

}


// Add gss.gffCurSeq to finalTileSet, making sure it exists in the referenceTileSet.
//
func (gss *GffScanState) AddTile( finalTileSet *tile.TileSet, referenceTileSet *tile.TileSet ) {

  n := len(gss.gffCurSeq)
  if n < 48 { panic("gss.gffCurSeq < 48!") }

  NormalizeTileSeq( gss.gffCurSeq )

  stag := string(gss.gffCurSeq[0:24])
  etag := string(gss.gffCurSeq[n-24:n])
  body := string(gss.gffCurSeq[24:n-24])
  _ = body

  // Check to make sure we have start and end tags for this tile
  //
  baseTileId,ok := referenceTileSet.TagToTileId[ stag ]
  if !ok {
    fmt.Printf("WARNING: could not find start tag in tile set! (%s) (end tag: %s)\n", stag, etag)
    fmt.Println(gss.notes)
    return
  }

  _,ok = referenceTileSet.TagToTileId[ etag ]
  if !ok {
    fmt.Printf("WARNING: could not find end tag in tile set! (%s) (start tag: %s)\n", etag, stag)
    fmt.Println(gss.notes)
    return
  }

  tileCopies := referenceTileSet.TileCopyCollectionMap[ baseTileId ]

  newTileId := fmt.Sprintf("%s.%03x", baseTileId, 0 )

  newCopyNum := 1
  newN := len( gss.gffCurSeq )

  header := TileHeader{}
  json.Unmarshal( []byte( tileCopies.Meta[0] ), &header )

  header.TileID = newTileId
  header.CopyNum = newCopyNum
  header.N = newN

  if header.Notes == nil { header.Notes = make( []string, 0, 10 ) }
  header.Notes = append( header.Notes, gss.notes... )

  newMeta,_ := json.Marshal( &header )

  finalTileSet.AddTile( newTileId, string(gss.gffCurSeq), string(newMeta) )

  if gDebugFlag { fmt.Printf(">>> ***\n>>> *** adding tile [[ %s ]] %d --\n>%s\n%s\n\n", newTileId, newCopyNum, newMeta, gss.gffCurSeq) }

}


func (gss *GffScanState) advanceAndUpdateState( finalTileSet *tile.TileSet, referenceTileSet *tile.TileSet, chrFa []byte, startPos int, entryLen int, tagLen int ) {

  s := startPos

  // Add the rest of the reference to the current sequence and hand it off ot handlePossibleNewTile to potentially
  // add it to the tile library.
  //
  // For example, entryLen = 1, tagLen = 2, tagStart = 50...
  //    s = 49 (s+1==50), don't want to push to the tile library
  //    s = 50 (s+1==51), don't want to push to the tile library
  //    s = 51 (s+1==52), _do_ want to push to the tile library
  //
  for ; (s + entryLen) >= (gss.nextTagStart + tagLen) ;  {

    if gDebugFlag {
      fmt.Printf( "# [s: %d, n: %d] (refStart: %d, refLen: %d) startPos< %d, %d, %d > {nextTagStart: %d}\n",
        s, entryLen,
        gss.refStart, gss.refLen,
        gss.startPos[ gss.startPosIndex-1 ], gss.startPos[ gss.startPosIndex ], gss.startPos[ gss.startPosIndex+1 ],
        gss.nextTagStart )
    }

    if gss.refStart == gss.startPos[gss.startPosIndex-1] {

      if gDebugFlag { fmt.Printf( "# --> trying to add new tile sequence\n") }

      if gDebugFlag { fmt.Printf(">> EXTENDING %d to %d (%d to %d inclusive)\n",
            gss.refStart + gss.refLen,
            s + entryLen +1,
            gss.refStart + gss.refLen,
            s + entryLen ) }


      if ((gss.refStart + gss.refLen) < 0) || ((gss.refStart + gss.refLen) >= len(chrFa)) ||
         ((gss.nextTagStart + tagLen) < 0) || ((gss.nextTagStart + tagLen) >= len(chrFa)) ||
         ((gss.refStart + gss.refLen) > (gss.nextTagStart + tagLen))  {
        fmt.Printf("ERROR: OUT OF BOUNDS! (%s) chrFa[%d,%d] gss.refStart: %d, gss.refLen: %d, gss.nextTagStart: %d, tagLen: %d\n",
                    gDebugString,
                    0, len(chrFa), gss.refStart, gss.refLen, gss.nextTagStart, tagLen)
      }

      gss.gffCurSeq = append( gss.gffCurSeq, chrFa[ gss.refStart + gss.refLen : gss.nextTagStart + tagLen ]... )

      sprv := gss.startPos[ gss.startPosIndex-1 ]
      scur := gss.startPos[ gss.startPosIndex ]

      if gDebugFlag { fmt.Printf( "# tagsMatch on: %s\n", gss.gffCurSeq ) }

      if tagsMatch( gss.gffCurSeq, chrFa[ sprv : sprv+tagLen ], chrFa[ scur : scur+tagLen ] ) {
        gss.AddTile( finalTileSet, referenceTileSet )
      } else {
        if gDebugFlag { fmt.Printf( "# ----> discarding, snp, indel or sub on tag\n" ) }
      }

    } else {
      if gDebugFlag { fmt.Printf( "# --> discarding partial tile sequence\n") }
    }

    gss.gffCurSeq = gss.gffCurSeq[0:0]
    gss.refStart = gss.nextTagStart
    gss.refLen = 0

    gss.notes = gss.notes[0:0]
    if len(gNoteLine) > 0 { gss.notes = append( gss.notes, gNoteLine ) }

    gss.startPosIndex++
    if gss.startPosIndex == len(gss.startPos) { break }
    gss.nextTagStart = gss.startPos[ gss.startPosIndex ]

  }

  dn := (s + entryLen) - (gss.refStart + gss.refLen)
  gss.gffCurSeq = append( gss.gffCurSeq, chrFa[ gss.refStart + gss.refLen : gss.refStart + gss.refLen + dn ]... )
  gss.refLen += dn

  if gDebugFlag { fmt.Printf(">> len(gss.gffCurSeq) %d,  gss.refStart %d, gss.refLen %d, entryLen %d\n", len(gss.gffCurSeq), gss.refStart, gss.refLen, entryLen ) }

}


func NormalizeTileSeq( tileSeq []byte ) {

  n := len(tileSeq)
  if n < 48 { return }

  for i:=0; i<24; i++ {
    if (tileSeq[i] == 'a') || (tileSeq[i] == 'c') ||
       (tileSeq[i] == 't') || (tileSeq[i] == 'g') ||
       (tileSeq[i] == 'n') {
      tileSeq[i] -= 32
    }
  }

  for i:=0; i<24; i++ {
    p := n-i-1
    if (tileSeq[p] == 'a') || (tileSeq[p] == 'c') ||
       (tileSeq[p] == 't') || (tileSeq[p] == 'g') ||
       (tileSeq[p] == 'n') {
      tileSeq[p] -= 32
    }
  }

  for i:=24; i<(n-24); i++ {
    if (tileSeq[i] == 'A') || (tileSeq[i] == 'C') ||
       (tileSeq[i] == 'T') || (tileSeq[i] == 'G') ||
       (tileSeq[i] == 'N') {
      tileSeq[i] += 32
    }
  }

}


func tagsMatch( seq []byte, ltag []byte, rtag []byte ) bool {
  if len(seq) < (len(ltag) + len(rtag)) { return false }

  if string(seq[0:len(ltag)]) != string(ltag) { return false }
  if string(seq[len(seq)-len(rtag):len(seq)]) != string(rtag) { return false }
  return true
}


func main() {

  //gDebugFlag = true

  tagLen := 24
  CYTOMAP_FILENAME = "ucsc.cytomap.hg19.txt"

  // Count number of variations in a tile.
  // Key is start position of the tile (hg19 ref)
  //
  //TILE_VAR_COUNT := make( map[int]int )

  if len(os.Args) < 5 {
    fmt.Println("usage:")
    fmt.Println("  createTileSetFromGff <choppedGffFileName> <fastjFileName> <chromosomeFastaFileName> <outputFastjFileName> [<gNoteLine>]")
    os.Exit(0)
  }

  gffFn := os.Args[1]
  fastjFn := os.Args[2]
  chrFaFn := os.Args[3]
  outFastjFn := os.Args[4]
  if len(os.Args) > 5 { gNoteLine = os.Args[5] }

  gDebugString = fmt.Sprintf( "%s %s %s %s %s", gffFn, fastjFn, chrFaFn, outFastjFn, gNoteLine )

  // Load band boundaries
  //
  BAND_BOUNDS = make( map[string]map[int][2]int  )
  aux.BuildBandBounds( BAND_BOUNDS, CYTOMAP_FILENAME)

  // Load the tile set for this band.
  //
  if gDebugFlag { fmt.Println("# loading", fastjFn, "into memory...") }
  referenceTileSet := tile.NewTileSet( tagLen )
  referenceTileSet.ReadFastjFile( fastjFn )

  finalTileSet := tile.NewTileSet( tagLen )

  gss := GffScanState{}
  gss.notes = make( []string, 0, 10 )

  if len(gNoteLine) > 0 { gss.notes = append( gss.notes, gNoteLine ) }

  // Sort starting position of each of the tile.
  //
  for _,tcc := range referenceTileSet.TileCopyCollectionMap {
    a,_ := recache.FindAllStringSubmatch( `hg19 chr[^ ]* (\d+)(-\d+)? (\d+)(\+\d+)?`, tcc.Meta[0], -1 )

    s,_ := strconv.Atoi(a[0][1])
    e,_ := strconv.Atoi(a[0][3])

    gss.startPos = append( gss.startPos, s )

    // Put in final endpoing, if we've reached that point
    //
    if len(a[0][4]) > 0 {
      gss.startPos = append( gss.startPos, e )
    }
  }
  sort.Ints(gss.startPos)
  gss.nextTagStart = gss.startPos[1]
  gss.startPosIndex = 1

  // Load our hg19 reference band.
  //
  if gDebugFlag { fmt.Println("# loading", chrFaFn, "into memory...") }
  chrFa := aux.FaToByteArray( chrFaFn )
  _ = chrFa

  // Finall, scan our gff file...
  //
  gffFp, err := os.Open( gffFn )
  if err != nil { panic(err) }
  defer gffFp.Close()

  count := 0

  if gDebugFlag { fmt.Println("# reading gff") }

  // refStart is 0 based
  //
  gss.gffCurSeq = make( []byte, 0, 10 )
  gss.refStart, gss.refLen = -1, 0

  // NOTE: gff files start position at 1 (not 0)
  // and have their end position inclusve.
  // For example:
  //  ... 1 1 ...
  //  is 1 character character long, starting at the first position.
  //
  //  .... 3 6 ...
  //  is 4 characters long (6 is inclusive), starting at the 3rd position (that is, a[2])
  //
  //  SNP/SUB: [s,e] -> [s-1,e-1] (inclusive)
  //  example: 5 7 ... alleles AAA/TGG; ref_allele TGG
  //                   means the 5th through 7th bp was altered from TGG to AAA
  //           11 11 ... alleles A; ref_allele G
  //                   means the 11th bp was altered from an A to G
  //
  //  INDEL: [s+1,e] -> insertion
  //         [s,s+d] -> deletion of (d+1) bp
  //

  //scanner := bufio.NewScanner( gffFp )
  var scanner *bufio.Scanner
  if b,_ := recache.MatchString( `\.gz$`, gffFn ); b {
    fp,err := gzip.NewReader( gffFp )
    if err!=nil { panic(err) }
    scanner = bufio.NewScanner( fp )
  } else {
    scanner = bufio.NewScanner( gffFp )
  }



  for scanner.Scan() {
    l := scanner.Text()

    if gDebugFlag { fmt.Printf("#>> %s\n", l ) }

    // Skip blank line or ocmment
    //
    if b,_ := recache.MatchString( `^\s*$`, l ) ; b { continue }
    if b,_ := recache.MatchString( `^#`, l )   ; b { continue }

    fields := strings.SplitN( l, "\t", -1 )
    chrom := fields[0]

    _ = chrom

    s,_ := strconv.Atoi(fields[3])
    e,_ := strconv.Atoi(fields[4])
    typ := fields[2]
    comment := fields[8]

    // converting to 0 based, end inclusive
    //
    s -= 1
    e -= 1

    entryLen := e - s + 1

    // Initialize refStart and refLen
    //
    if gss.refStart < 0 {

      // Keep things simple, skip over anything that isn't ref
      // if we're at the beginning.
      //
      if typ != "REF" { continue }

      //gss.refStart, gss.refLen = s, entryLen
      //gss.refStart = gss.startPos[0]
      //gss.gffCurSeq = append( gss.gffCurSeq, chrFa[ gss.refStart : gss.refStart + gss.refLen ]... )

      gss.refStart, gss.refLen = s, 0
      gss.refStart = gss.startPos[0]

      gss.advanceAndUpdateState( finalTileSet, referenceTileSet, chrFa, s, entryLen, tagLen )
      if gss.startPosIndex == len(gss.startPos) { break }

      continue

    }

    if gDebugFlag {
      fmt.Printf("# [s: %d, e: %d] (refStart: %d, refLen: %d) startPos< %d, %d, %d >\n",
        s, e,
        gss.refStart, gss.refLen,
        gss.startPos[ gss.startPosIndex-1 ], gss.startPos[ gss.startPosIndex ], gss.startPos[ gss.startPosIndex+1 ] )
    }

    // Continue our contiguous sequence from the previous gff line.
    //
    if (gss.refStart + gss.refLen) == s {

      if gDebugFlag { fmt.Printf("# ------> extending current tile\n") }


    } else {

      if gDebugFlag { fmt.Printf("# ------> starting new tile (refStart(%d) + refLen(%d) = %d != %d) \n", gss.refStart, gss.refLen, gss.refStart + gss.refLen, s ) }

      gss.gffCurSeq = gss.gffCurSeq[0:0]
      gss.refStart, gss.refLen = s, 0

      gss.notes = gss.notes[0:0]
      if len(gNoteLine) > 0 { gss.notes = append( gss.notes, gNoteLine ) }

    }

    if typ == "REF" {

      gss.advanceAndUpdateState( finalTileSet, referenceTileSet, chrFa, s, entryLen, tagLen )
      if gss.startPosIndex == len(gss.startPos) { break }

    } else {

      comments := strings.SplitN( comment, ";", -1 )

      m,_ := recache.FindAllStringSubmatch( `alleles ([^/]+)(/(.+))?`, comments[0] , -1 )
      var1 := m[0][1]
      var2 := m[0][2]
      if ( len(var2) > 0 ) { var2 = var2[1:] }

      m,_ = recache.FindAllStringSubmatch( `ref_allele ([^;]+)`, comment, -1 )
      ref_seq := m[0][1]

      if gDebugFlag { fmt.Printf("# var1 %s, var2 %s, ref_seq %s\n", var1, var2, ref_seq ) }


      if typ == "SNP" {

        if gDebugFlag { fmt.Println("# SNP") }

        gss.refLen ++

        if var1 == ref_seq {
          gss.notes = append( gss.notes, fmt.Sprintf("hg19 %s %d %d SNP %s (%d)", chrom, s, e, var2, len(gss.gffCurSeq) ) )
          gss.gffCurSeq = append( gss.gffCurSeq, var2... )
        } else {
          gss.notes = append( gss.notes, fmt.Sprintf("hg19 %s %d %d SNP %s (%d)", chrom, s, e, var1, len(gss.gffCurSeq)  ) )
          gss.gffCurSeq = append( gss.gffCurSeq, var1... )
        }

        if gDebugFlag { fmt.Println("# notes:", gss.notes) }

        // We have a SNP on a tag boundary.  Reset our current sequence, update everything and move on
        //
        if (( gss.startPos[ gss.startPosIndex ] <= s ) && ( s < (gss.startPos[ gss.startPosIndex ] + tagLen ) ) ||
            ( gss.startPos[ gss.startPosIndex ] <= e ) && ( e < (gss.startPos[ gss.startPosIndex ] + tagLen ) ) ||
            ( s < gss.startPos[ gss.startPosIndex ] )  && ( e > (gss.startPos[ gss.startPosIndex ] ) ) ) {

          if gDebugFlag { fmt.Println(">>\n>> --> snp falls on tag, discarding") }

          gss.gffCurSeq = gss.gffCurSeq[0:0]

          gss.startPosIndex++
          if gss.startPosIndex == len(gss.startPos) { break }
          gss.nextTagStart = gss.startPos[ gss.startPosIndex ]

          gss.refStart = e+1
          gss.refLen ++

          gss.notes = gss.notes[0:0]
          if len(gNoteLine) > 0 { gss.notes = append( gss.notes, gNoteLine ) }
        }



      } else if typ == "SUB" {

        if gDebugFlag { fmt.Println("# SUB") }

        if var1 == ref_seq {
          gss.notes = append( gss.notes, fmt.Sprintf("hg19 %s %d %d SUB %s (%d)", chrom, s, e, var2, len(gss.gffCurSeq) ) )

          gss.gffCurSeq = append( gss.gffCurSeq, var2... )
        } else {
          gss.notes = append( gss.notes, fmt.Sprintf("hg19 %s %d %d SUB %s (%d)", chrom, s, e, var1, len(gss.gffCurSeq) ) )

          gss.gffCurSeq = append( gss.gffCurSeq, var1... )
        }

        gss.refLen += entryLen

        if (( gss.startPos[ gss.startPosIndex ] <= s ) && ( s < (gss.startPos[ gss.startPosIndex ] + tagLen ) ) ||
            ( gss.startPos[ gss.startPosIndex ] <= e ) && ( e < (gss.startPos[ gss.startPosIndex ] + tagLen ) ) ||
            ( s < gss.startPos[ gss.startPosIndex ] )  && ( e > (gss.startPos[ gss.startPosIndex ] ) ) ) {

          if gDebugFlag { fmt.Println(">>\n>> --> sub falls on tag, discarding") }

          gss.gffCurSeq = gss.gffCurSeq[0:0]
          gss.notes = gss.notes[0:0]
          if len(gNoteLine) > 0 { gss.notes = append( gss.notes, gNoteLine ) }

          gss.startPosIndex++
          if gss.startPosIndex == len(gss.startPos) { break }
          gss.nextTagStart = gss.startPos[ gss.startPosIndex ]

          gss.refStart = e+1
          gss.refLen   = 0


        }


      } else if typ == "INDEL" {

        if ref_seq == "-" {

          if gDebugFlag { fmt.Println("# INS") }

          ins_seq := var1
          if var1 == "-" { ins_seq = var2 }

          gss.notes = append( gss.notes, fmt.Sprintf("hg19 %s %d %d INS %s (%d)", chrom, s, e, ins_seq, len(gss.gffCurSeq) ) )

          gss.gffCurSeq = append( gss.gffCurSeq, ins_seq... )

          gss.refLen += 0

        } else {

          if gDebugFlag { fmt.Println("# DEL") }

          gss.refLen += entryLen

          gss.notes = append( gss.notes, fmt.Sprintf("hg19 %s %d %d DEL -%d (%d)", chrom, s, e, entryLen, len(gss.gffCurSeq) ) )

        }

        if (( gss.startPos[ gss.startPosIndex ] <= s ) && ( s < (gss.startPos[ gss.startPosIndex ] + tagLen ) ) ||
            ( gss.startPos[ gss.startPosIndex ] <= e ) && ( e < (gss.startPos[ gss.startPosIndex ] + tagLen ) ) ||
            ( s < gss.startPos[ gss.startPosIndex ] )  && ( e > (gss.startPos[ gss.startPosIndex ] ) ) ) {

          if gDebugFlag { fmt.Println(">>\n>> --> indel falls on tag, discarding") }

          gss.gffCurSeq = gss.gffCurSeq[0:0]
          gss.notes = gss.notes[0:0]
          if len(gNoteLine) > 0 { gss.notes = append( gss.notes, gNoteLine ) }

          gss.startPosIndex++
          if gss.startPosIndex == len(gss.startPos) { break }
          gss.nextTagStart = gss.startPos[ gss.startPosIndex ]

          gss.refStart = e+1
          gss.refLen = 0

        }

      }


    }


    if gDebugFlag {
      fmt.Printf("# refStart %d, refLen %d, index %d, nextTagStart %d\n", gss.refStart, gss.refLen, gss.startPosIndex, gss.nextTagStart )
      fmt.Printf("%s\n", gss.gffCurSeq)
    }

    count++

    if gDebugFlag { fmt.Printf("#%d\n\n\n", count) }

  }

  if gDebugFlag { fmt.Println(">>>> FINAL FASTJ ASSEMBLY", outFastjFn) }

  finalTileSet.WriteFastjFile( outFastjFn )

}
