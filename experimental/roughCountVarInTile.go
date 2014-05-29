/* This generates a rough count of variants in tiles.
   This will overcount as the gff file will not have
   completely contiguous regions
*/
package main

import "fmt"
import "os"

import "strconv"
import "bufio"
import "strings"

import "sort"
import "flag"
import "path"
import "compress/gzip"

import "./tile"
import "./recache"

import "log"
import "runtime/pprof"


type TileBucket struct {
  start, end int
  varType []string
  pos []int
}

type ByStart []TileBucket
func (x ByStart) Len() int { return len(x) }
func (x ByStart) Swap(i, j int) { x[i],x[j] = x[j],x[i] }
func (x ByStart) Less(i,j int) bool { return x[i].start < x[j].start }


// Only look at the first copy of the tile to determine where in hg19 it was
// taken from.  Assumes it was taken from hg19 and it has the relevant
// information was stored in the header.
//
func initCountBucket_old( tileBucket *[]TileBucket, tileSet *tile.TileSet ) {

  for _,v := range tileSet.TileCopyCollectionMap {
    meta := v.Meta[0]
    a,_ := recache.FindAllStringSubmatch( `hg19 chr[^\s]+ (\d+)(\-\d+)? (\d+)(\+\d+)?`, meta, -1 )
    s,_ := strconv.Atoi( a[0][1] )
    e,_ := strconv.Atoi( a[0][3] )
    *tileBucket = append( *tileBucket, TileBucket{ start: s, end: e, varType: make( []string, 0), pos: make( []int, 0 ) } )
  }

  sort.Sort( ByStart( *tileBucket ) )

}

// Only look at the first copy of the tile to determine where in hg19 it was
// taken from.  Assumes it was taken from hg19 and it has the relevant
// information was stored in the header.
//
func initCountBucket( tileBucket *[]TileBucket, indexFilename string ) {

  fp,err := os.Open( indexFilename )
  if err != nil { panic(err) }
  defer fp.Close()

  scanner := bufio.NewScanner( fp )
  for scanner.Scan() {
    l := scanner.Text()
    fields := strings.SplitN( l, " ", -1 )

    s,_ := strconv.Atoi( fields[0] )
    e,_ := strconv.Atoi( fields[1] )

    *tileBucket = append( *tileBucket, TileBucket{ start: s, end: e, varType: make( []string, 0), pos: make( []int, 0 ) } )
  }

  sort.Sort( ByStart( *tileBucket ) )

}

// Add it to the appropriate bucket between start positions by way of appending to the list.
//
func dumpInBucket( tileBucketPtr *[]TileBucket, pos int, varType string, maxTileLength int ) {

  tileBucket := *tileBucketPtr

  n := len(tileBucket)
  p := sort.Search( n, func( k int ) bool { return (tileBucket[k].start > pos) } )

  if (0 < p) && (p < n) {
    p--

    if (maxTileLength > 0) && ((tileBucket[p].end - tileBucket[p].start) >= maxTileLength) { return }

    tileBucket[p].varType = append( tileBucket[p].varType, varType )
    tileBucket[p].pos = append( tileBucket[p].pos, pos )
  } else {
    fmt.Println("ERROR: pos", pos, "(", varType, ") not found in bucket")
  }

}


// Same as in dumpInBucket, but only add if the pos is within tagLength of the
// start position.
//
func dumpInBucketTag( tileBucketPtr *[]TileBucket, pos int, varType string, tagLen int, maxTileLength int ) {

  tileBucket := *tileBucketPtr

  n := len(tileBucket)
  p := sort.Search( n, func( k int ) bool { return (tileBucket[k].start > pos) } )

  if (0 < p) && (p < n) {
    p--

    if (maxTileLength > 0) && ((tileBucket[p].end - tileBucket[p].start) >= maxTileLength) { return }

    //fmt.Println(">>>> pos", pos, ", start:", tileBucket[p].start, "end:", tileBucket[p].end,
    //  "( dps:", pos - tileBucket[p].start, ", dt:", tileBucket[p].end - tileBucket[p].start , ")" )

    if ( pos - tileBucket[p].start ) < tagLen {
      tileBucket[p].varType = append( tileBucket[p].varType, varType )
      tileBucket[p].pos = append( tileBucket[p].pos, pos )
    }

  } else {
    fmt.Println("ERROR: pos", pos, "(", varType, ") not found in bucket")
  }

}

// Print out the start, end and sum of the number of elements in the bucket
// that match varType.
//
func printBucketFilter( countBucket []TileBucket, varType string ) {

  for i:=0; i<len(countBucket); i++ {
    sum := 0
    for j:=0; j<len(countBucket[i].varType); j++ {
      if countBucket[i].varType[j] == varType { sum ++ }
    }

    if sum > 0 {
      fmt.Println( countBucket[i].start, countBucket[i].end, sum )
    }

  }

}

// Print out the start, end and number in the bucket (will include REFs)
//
func printBucketAll( countBucket []TileBucket ) {

  for i:=0; i<len(countBucket); i++ {
    if len(countBucket[i].varType) > 0 {
      fmt.Println( countBucket[i].start, countBucket[i].end, len(countBucket[i].varType)  )
    }
  }

}


func printHelpOption( f *flag.Flag) {
  n := 10 - len(f.Name)
  if n<0 { n=0 }

  if ( f.Name == "gff" ) || (f.Name == "indexfile") {
    fmt.Printf("  -%s%s    %s\n", f.Name, strings.Repeat(" ", n), f.Usage )
  } else {
    fmt.Printf("  [-%s]%s  %s\n", f.Name, strings.Repeat(" ", n), f.Usage )
  }
}

func usage( progName string ) {
  fmt.Fprintf(os.Stderr, "usage: %s -gff=<choppedGffFile> -indexfile=<FastjFile> [-maxTileLen=<len>] [-taghit] [-profile] [-h|help]\n", progName)
  flag.VisitAll( printHelpOption )

}


func main() {

  tagLen := 24

  gffFn         := flag.String( "gff", "", "chopped GFF file" )
  //fastjFn       := flag.String( "fj", "", "Fastj file" )
  indexFn       := flag.String( "indexfile", "", "index file" )
  filterType    := flag.String( "filter", "all", "filter variant type (SNP|SUB|INDEL) (defaults to 'all')")
  maxTileLength := flag.Int( "maxTileLen", -1, "don't count all tiles with greater than maxTileLen" )
  tagHitFlag    := flag.Bool( "taghit", false, "filter by variants that hit a tag" )
  profileFlag   := flag.Bool( "profile", false, "profile runtime" )

  helpFlag      := flag.Bool( "h", false, "help" )
  helpFlag2     := flag.Bool( "help", false, "help" )

  flag.Parse()

  if *helpFlag || *helpFlag2 {
    fmt.Println("...")
    os.Exit(0)
  }

  if *profileFlag {
    profFn := fmt.Sprintf("%s.prof", path.Base( os.Args[0] ))

    f, err := os.Create( profFn )
    if err != nil { log.Fatal(err) }
    pprof.StartCPUProfile(f)
    defer pprof.StopCPUProfile()
  }

  if len(*gffFn) == 0 || len(*indexFn) == 0 {
    usage( path.Base( os.Args[0] ) )
    os.Exit(1)
  }


  // Initialize the bucket with the (start,end)
  // indexes stored in the file *indexFn.
  //
  countBucket := make( []TileBucket, 0, 10 )
  initCountBucket( &countBucket, *indexFn )


  // Finall, scan our gff file...
  //
  gffFp, err := os.Open( *gffFn )
  if err != nil { panic(err) }
  defer gffFp.Close()


  line_count := 0

  //scanner := bufio.NewScanner( gffFp )
  var scanner *bufio.Scanner

  if b,_ := recache.MatchString( `\.gz$`, *gffFn ); b {
    fp,err := gzip.NewReader( gffFp )
    if err!=nil { panic(err) }
    scanner = bufio.NewScanner( fp )
  } else {
    scanner = bufio.NewScanner( gffFp )
  }



  for scanner.Scan() {
    l:=scanner.Text()

    line_count++

    if b,_ := recache.MatchString( `^\s*$`, l ) ; b { continue }
    if b,_ := recache.MatchString( `^#`, l )   ; b { continue }

    fields := strings.SplitN( l, "\t", -1 )
    chrom := fields[0]
    _ = chrom

    s,_ := strconv.Atoi(fields[3])
    e,_ := strconv.Atoi(fields[4])
    _ = e

    variantType := fields[2]

    comment := fields[8]
    _ = comment

    if b,_ := recache.MatchString( `^(REF|SNP|INDEL|SUB)$`, variantType ) ; b {

      if *tagHitFlag {
        dumpInBucketTag( &countBucket, s, variantType, tagLen, *maxTileLength )
      } else {
        dumpInBucket( &countBucket, s, variantType, *maxTileLength )
      }

    }

  }

  switch *filterType {
  case "SNP" , "SUB", "INDEL" :
    printBucketFilter( countBucket, *filterType )
  default:
    printBucketAll( countBucket )
  }


}
