// Takes in, from stdin, a concatentated list of all fastj files for
// all people you want to make a tiling for.  Assumes each persons
// tiles are grouped together, but not necessarily contiguous.
//
// Also takes in a list of tiles with frequency, tile id and
// variant string.  The variant string is the comma seperated list of quoted strings
// of the variants.  This is the same as it appears in the fastj file for
// a human.  The variant string is used as the key to figure out which
// fastj tile from stdin is associated to which tile variant.
//
// The variant id in the tile frequency needs to appear but does not need
// change, as it is calculated and inferred by the position in the tile frequency
// list.
//
// Output format is on line per human, each line is space seprated, first field is
// human identifier followed by band name, ascii encoded hex 8bit vector per position
// pairs.
//
// For example:
// hu1234 0 aefaef1230044... 1 001240011231...
//
// The 8bit vector positions denote:
// 0    - uknown (no call)
// 1    - hom ref
// 2    - complex
// 3k   - het A variant with tile instance k  ( 1 <= k <= 84 )
// 3k+1 - het B variant with tile instance k
// 3k+2 - homozygous variant with tile instance k
// ...
// 252  - het A variant with tile instance 84
// 253  - het B variant with tile instance 84
// 254  - homozygous variant with tile instance 84
// 255  - exception
//

package main

import "fmt"
import "os"
import "bufio"

import "runtime"

import "strings"
import "strconv"

import "./aux"
import "./recache"

var gDebugFlag bool

var INITIAL_WIDTH int = 50

// Maps prefix tile id (just first 3 'numbers', omitting the last)
// and variant string to an instance number for use in the tiling.
//
var TILE_LOOKUP map[string]map[string]int

func loadTileInstances( fn string ) {

  //DEBUG
  line_count :=0

  fp,tileScanner,err := aux.OpenScanner( fn )
  if err != nil { panic(err) }
  defer fp.Close()

  instance := 0

  prevTilePrefix := ""

  for tileScanner.Scan() {
    l := tileScanner.Text()

    field := strings.SplitN( l, ",", -1 )
    count,_ := strconv.Atoi( field[0] )
    tileId := field[1]

    _ = count

    tilePrefix,_ := recache.ReplaceAllString( `"(.*)\.\d+"`, tileId, "$1" )

    if prevTilePrefix != tilePrefix {
      instance = 0
    }

    variantStr := ""
    if len(field) > 2 {
      variantStr = strings.Join( field[2:], "," )
    }

    if _,ok := TILE_LOOKUP[tilePrefix] ; !ok {
      TILE_LOOKUP[tilePrefix] = make( map[string]int )
    }

    TILE_LOOKUP[tilePrefix][variantStr] = instance

    instance++

    //DEBUG
    //if line_count > 100 { break }
    line_count++

    if gDebugFlag {
      if (line_count % 100000) == 0 {
        fmt.Printf("# %d\n", line_count) 
        //runtime.GC()
      }

    }

    prevTilePrefix = tilePrefix


  }

  // Force an immediate clean up after ourselves.
  //
  runtime.GC()

}

func printTileLookup() {

  for x := range(TILE_LOOKUP) {
    for y := range(TILE_LOOKUP[x]) {
      fmt.Printf("%s %s %d\n", x, y, TILE_LOOKUP[x][y] )
    }
    fmt.Printf("\n")
  }
}

func makeTileVector() [][]byte {
  n := 500
  h := make( [][]byte, n )
  for i:=0; i<n; i++ {
    h[i] = make( []byte, INITIAL_WIDTH )
  }
  return h
}

func setTileVectorByte( h *[][]byte, band int, pos int, val byte ) {

  if band >= len(*h) {
    for i:=len(*h) ; i<=band ; i++ {
      *h = append( *h, make( [][]byte, (band - len(*h)) + 1 )... )
    }
  }

  if pos >= len( (*h)[band] ) {
    (*h)[band] = append( (*h)[band], make( []byte, (pos-len((*h)[band])) + 1 )... )
  }

  (*h)[band][pos] = val

}

//var lookupTable []byte = []byte{ 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '+', '/'}
var lookupTable []byte = []byte{ '-', '.', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '+', '/'}

func convertbyte( b byte ) byte {
  if b < 3 { return lookupTable[b] }
  z := b/3 + 2
  if z > 63 { return '#' }
  return lookupTable[z]

}

func writeTileVector( h [][]byte, huId string, fn string ) {
  fp,err := os.Create(fn)
  if err != nil { panic(err) }
  defer fp.Close()

  fp.Write( []byte(fmt.Sprintf("%s", huId)) )
  for i:=0; i<len(h); i++ {

    fp.Write( []byte(fmt.Sprintf(" %x ", i )) )
    for j:=0; j<len(h[i]); j++ {
      //fp.Write( []byte(fmt.Sprintf("%02x", h[i][j] )) )
      fp.Write( []byte(fmt.Sprintf("%c", convertbyte( h[i][j] ))) )
    }

  }

  fp.Write( []byte("\n") )

}

func main() {

  gDebugFlag = true

  outputDir := "/scratch2/abram"

  if len(os.Args) != 2 {
    fmt.Printf("provide tile frequency order file")
    os.Exit(0)
  }


  scanner := bufio.NewScanner(os.Stdin)
  //for scanner.Scan() { break }
  _ = scanner

  TILE_LOOKUP = make( map[string]map[string]int )
  loadTileInstances( os.Args[1] )

  //printTileLookup()

  line_count := 0

  prevHuId := ""

  var human [][]byte

  for scanner.Scan() {
    l := scanner.Text()

    if len(l) == 0 { continue }
    if l[0] != '>' { continue }

    m,_ := recache.FindAllStringSubmatch( `"tileID"\s*:\s*"([^"]+)"`, l, -1 )
    tileId := m[0][1]

    m,_ = recache.FindAllStringSubmatch( `^(.*)\.[^\.]+$`, tileId, -1 )
    prefixTileId := m[0][1]

    m,_ = recache.FindAllStringSubmatch( `"notes"\s*:\s*\[([^\]]+)\]`, l, -1 )
    notes := m[0][1]

    a := strings.SplitN( notes, ",", -1 )
    hu := a[0]

    if hu != prevHuId {

      if len(prevHuId) > 0 {
        cleanedHuId,_ := recache.ReplaceAllString( `"`, prevHuId, "")
        writeTileVector( human, prevHuId, fmt.Sprintf("%s/%s.abv", outputDir, cleanedHuId) )
      }

      human = makeTileVector()
      runtime.GC()
    }

    prevHuId = hu

    variantStr := ""
    if len(a) > 1 {
      variantStr = strings.Join( a[1:], "," )
    }


    if _,ok := TILE_LOOKUP[prefixTileId] ; !ok { panic( prefixTileId ) }
    instanceId,ok := TILE_LOOKUP[prefixTileId][variantStr]
    if !ok { panic( fmt.Sprintf("could not find variantStr %s (%s,%s) at line %d", variantStr, tileId, prefixTileId, line_count ) ) }

    var b byte
    switch {
    case instanceId == 0:
      b = 1
    case instanceId < 85:
      b = byte(instanceId * 3)
    default:
      b = 255
    }

    m,_ = recache.FindAllStringSubmatch( `([^\.]+)\.([^\.]+)\.([^\.]+)\.([^\.]+)`, tileId, -1 )
    band,_ := strconv.ParseInt( m[0][1], 16, 0 )
    pos,_ := strconv.ParseInt( m[0][3], 16, 0 )

    //fmt.Printf(" band %x (%d),pos %x (%d),instance %02x (%d) (%s)\n", band, band, pos, pos, b, instanceId, hu )

    setTileVectorByte( &human, int(band), int(pos), b )


    //fmt.Printf("tileId: %s, prefixTileId: %s, notes: %s, human: %s, varStr: %s\n", tileId, prefixTileId, notes, hu, variantStr)
    //fmt.Printf("instanceId: %d\n", instanceId)

    line_count++
    if (line_count % 10000) == 0 { fmt.Println("#", line_count) }
    //if line_count > 1000 { break; }
  }

  if len(prevHuId) > 0 {
    cleanedHuId,_ := recache.ReplaceAllString( `"`, prevHuId, "")
    writeTileVector( human, prevHuId, fmt.Sprintf("%s/%s.abv", outputDir, cleanedHuId) )
  }


}
