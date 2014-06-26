package main

import "os"
import "fmt"
import "os/exec"
//import "log"

import "flag"

import "./aux"
import "./bioenv"

var chr = []string{ "chr1", "chr2", "chr3", "chr4", "chr5", "chr6", "chr7", "chr8", "chr9", "chr10",
                    "chr11", "chr12", "chr13", "chr14", "chr15", "chr16", "chr17", "chr18", "chr19", "chr20",
                    "chr21", "chr22", "chrX", "chrY", "chrM" }


var benv bioenv.BioEnvContext

var g_bw2bedGraph       *string
var g_cytomapFilename   *string
var g_bigWigFilename    *string
var g_bedGraphDestDir   *string

func init() {
  var err error
  benv, err = bioenv.BioEnv()
  if err != nil { panic(err) }

  g_bw2bedGraph     = flag.String( "bigWigToBedGraph", benv.Env["bigWigToBedGraph"], "Location of the bigWigToBedGraph executable")
  g_cytomapFilename = flag.String( "cytoBand", benv.Env["cytoBand"], "Location of the cytoBand file")
  g_bigWigFilename  = flag.String( "bigWig", benv.Env["wgEncodeCrgMapabilityAlign24mer.bw"], "Location of the bigWig mapability file")
  g_bedGraphDestDir = flag.String( "destination-dir", "", "Destination Directory" )

  flag.Parse()
  benv.ProcessFlag()

  if len(*g_bedGraphDestDir)==0 {
    fmt.Fprintf( os.Stderr, "Provide destination directory\n" )
    flag.PrintDefaults()
    os.Exit(2)
  }

}

func main() {

  bufferWindow := 0
  bandBounds := make( map[string]map[int][2]int )

  aux.BuildBandBounds( bandBounds, *g_cytomapFilename )

  // Create bedGraph files, one per band
  //
  for i := 0 ; i < len(chr); i++ {
    chrom := chr[i]

    n := len(bandBounds[chrom])
    for j := 0; j < n; j++ {

      var s,e int

      if j==0 && j==(n-1) {
        fmt.Println( "*", chrom, bandBounds[chrom][j][0], bandBounds[chrom][j][1] )

        s = bandBounds[ chrom ][j][0]
        e = bandBounds[ chrom ][j][1]
      } else if j == 0 {
        fmt.Println( "-", chrom,
                    bandBounds[chrom][ j ][0], bandBounds[chrom][ j ][1], ",",
                    bandBounds[chrom][j+1][0], bandBounds[chrom][j+1][1])

        s = bandBounds[ chrom ][j][0]
        e = bandBounds[ chrom ][j][1] + bufferWindow
      } else if j == (n-1) {
        fmt.Println( "+", chrom,
                    bandBounds[chrom][j-1][0], bandBounds[chrom][j-1][1] , ",",
                    bandBounds[chrom][ j ][0], bandBounds[chrom][ j ][1] )

        s = bandBounds[ chrom ][j][0] - bufferWindow
        e = bandBounds[ chrom ][j][1]
      } else {
        fmt.Println( ".", chrom,
                    bandBounds[chrom][j-1][0], bandBounds[chrom][j-1][1] , ",",
                    bandBounds[chrom][ j ][0], bandBounds[chrom][ j ][1] , ",",
                    bandBounds[chrom][j+1][0], bandBounds[chrom][j+1][1] )

        s = bandBounds[ chrom ][j][0] - bufferWindow
        e = bandBounds[ chrom ][j][1] + bufferWindow
      }

      opt1 := fmt.Sprintf("-chrom=%s", string(chrom) )
      opt2 := fmt.Sprintf("-start=%d", s)
      opt3 := fmt.Sprintf("-end=%d", e)
      //infile := fmt.Sprintf("/scratch/%s/wgEncodeCrgMapabilityAlign24mer.bw", user )
      infile := *g_bigWigFilename
      outfile := fmt.Sprintf("%s/%s_band%d_s%d_e%d.bedGraph", *g_bedGraphDestDir, chrom, j, s, e )

      oput, err := exec.Command( *g_bw2bedGraph , opt1, opt2, opt3, infile, outfile ).CombinedOutput()
      _ = oput
      if err != nil { panic(err) }

    }
  }



}

