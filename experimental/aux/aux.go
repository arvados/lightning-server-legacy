package aux

import "regexp"
import _ "reflect"
import "os"
import "bufio"
import "strings"
import "strconv"

import "io/ioutil"

import "compress/gzip"
import "compress/bzip2"


func OpenScanner( fn string ) ( fp *os.File, scanner *bufio.Scanner, err error ) {

  fp,err = os.Open( fn )
  if err != nil { return fp, scanner, err }

  n := len(fn)

  if n >= 3 && fn[ n-3 : ] == ".gz" {

    fpReader,e := gzip.NewReader( fp )
    if e != nil { return fp, scanner, err }
    scanner = bufio.NewScanner( fpReader )

  } else if n >= 4 && fn[ n-4 : ] == ".bz2" {

    fpReader:= bzip2.NewReader( fp )
    scanner = bufio.NewScanner( fpReader )

  } else {
    scanner = bufio.NewScanner( fp )
  }

  return fp, scanner, err

}

// build bandBounds for each chromosome
//
// bandBounds example: bandbounds["chr1"][3][0] would represent the start of chromosome 1, band 3 (4th band)
// cytomapFile is the open file descriptor to the cytomap file
//
//func buildBandBounds( bandBounds map[string]map[int][2]int, cytomapFile *os.File) {
func BuildBandBounds( bandBounds map[string]map[int][2]int, cytomapFileName string) {

  cytomapFile, err := os.Open( cytomapFileName )
  if err != nil { panic(err) }
  defer cytomapFile.Close()

  prevChrom := "none"
  bandPos := -1

  re_comment,_   := regexp.Compile( `^#` )
  re_blankline,_ := regexp.Compile( `^\s*$` )

  scanner := bufio.NewScanner(cytomapFile)
  for scanner.Scan() {
    l := scanner.Text()
    //if m,_ := regexp.MatchString(`^#`, l ); m  { continue }
    //if m,_ := regexp.MatchString(`^\s*$`, l ); m { continue }

    if re_comment.MatchString( l )   { continue }
    if re_blankline.MatchString( l ) { continue }

    fields := strings.SplitN( l, "\t", -1 )

    chrom := fields[0]
    start,_ := strconv.Atoi(fields[1])
    end,_ := strconv.Atoi(fields[2])

    if chrom != prevChrom {
      prevChrom = chrom
      bandPos = 0
    }

    if bandBounds[chrom] == nil { bandBounds[chrom] = make( map[int][2]int ) }

    x := [2]int{start, end}
    bandBounds[ chrom ][bandPos] = x
    bandPos++
  }

}


// Load whole fasta file into memory.  Strip out header information and remove returns.
// 
func FaToByteArray( fn string ) []byte {

  b, err := ioutil.ReadFile( fn )
  if err != nil { panic(err) }

  n := len(b)


  bpos := 0
  for ; bpos<n; bpos++ {
    if b[bpos] == '\n' { break }
  }
  bpos_start := bpos

  m := 0
  for ; bpos<n; bpos++ {
    if b[bpos] == '\n' { continue }
    m++
  }

  s := make( []byte, m )

  spos := 0
  for bpos = bpos_start ; bpos < n; bpos++ {
    if b[bpos] == '\n' { continue }
    s[spos] = b[bpos]
    spos++
  }

  return s

}

func ToLowerInPlace( buf []byte ) {
  n := len(buf)

  for i:=0; i<n; i++ {
    if (buf[i] >= 0x41) && (buf[i] <= 0x5a) {
      buf[i] += 32
    }
  }

}
