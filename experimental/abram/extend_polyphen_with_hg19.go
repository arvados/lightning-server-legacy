/*
sample usage:

  time pigz -c -d /scratch2/awz/polyphen_extract.gz | ./extend_polyphen_with_hg19 | pigz -c - > /scratch2/awz/polyphen_w_hg18ref.gz

*/

package main

import "fmt"
import "os"

import "io/ioutil"
import "bytes"
import _ "strings"
import "strconv"

import "./aux"
import "./bioenv"

var CHR = []string{ "chr1",  "chr2",  "chr3",  "chr4",  "chr5",  "chr6",  "chr7",  "chr8",  "chr9",  "chr10",
                    "chr11", "chr12", "chr13", "chr14", "chr15", "chr16", "chr17", "chr18", "chr19", "chr20",
                    "chr21", "chr22", "chrX", "chrY", "chrM" }

var CHRFA = map[string][]byte{}

func main() {

  benv,_ := bioenv.BioEnv()
  basefadir := benv["dir:hg19.fa"]

  for i:=0; i<len(CHR); i++ {
    fn := fmt.Sprintf("%s/%s.fa", basefadir, CHR[i]);
    CHRFA[ CHR[i] ] = aux.FaToByteArray( fn )
  }
  //fmt.Println("# fa loaded")


  allbytes,err := ioutil.ReadAll(os.Stdin)
  if err != nil { panic(err) }

  //fmt.Println("# bytes read")

  //lines := strings.SplitN( string(allbytes), "\n", -1 )
  lines := bytes.Split( allbytes, []byte("\n") )

  //fmt.Println("# lines calculated, processing")


  blank_sep := []byte{'\t'}
  blank_seps := []byte{' '}
  colon_sep := []byte{':'}

  n:=len(lines)
  tot:=0
  for i:=0; i<n; i++ {
    if len(lines[i]) == 0 { fmt.Printf("\n") ; continue }
    if lines[i][0] == '#'  {
      //fmt.Printf("%s\thg19ref0bp\n",  lines[i] )
      fmt.Printf("%s\thg19ref1bp\n",  lines[i] )
      continue
    }

    ind := bytes.Index( lines[i], blank_sep )
    inds := bytes.Index( lines[i][0:ind], blank_seps )
    if inds != -1 { ind = inds }

    chr_pos1ref := bytes.Split( lines[i][:ind], colon_sep )
    chr := string(chr_pos1ref[0])
    pos1ref,_ := strconv.Atoi( string(chr_pos1ref[1]) )

    pos0ref := pos1ref-1

    if (pos0ref < 0) || (pos0ref >= len(CHRFA[ string(chr) ])) {
      panic( fmt.Sprintf("OOB pos0ref %d, len(CHRFA[%s]) = %d, (pos1ref %d), line %d\n", pos0ref, string(chr), len(CHRFA[ string(chr) ]), pos1ref, i) )
    }

    //fmt.Printf("%s %s (%s{%s} %d{%s})\n", string(lines[i]), string(CHRFA[ string(chr) ][pos]), chr, chr_pos[0], pos, chr_pos[1] )
    fmt.Printf("%s\t%s\n", string(lines[i]), string(CHRFA[ string(chr) ][pos0ref]) )

    tot++
    //if tot > 10 { break }

  }
  //fmt.Println("#", tot)


}
