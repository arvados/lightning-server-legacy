package main

import "os"
import "fmt"
import "os/exec"
import "log"

import "./aux"

var chr = []string{ "chr1", "chr2", "chr3", "chr4", "chr5", "chr6", "chr7", "chr8", "chr9", "chr10", 
                    "chr11", "chr12", "chr13", "chr14", "chr15", "chr16", "chr17", "chr18", "chr19", "chr20", 
                    "chr21", "chr22", "chrX", "chrY", "chrM" }


func main() {

  user := os.Getenv("USER")

  //bufferWindow := 5000
  bufferWindow := 0

  //bw2bedGraph := "./bin/bigWigToBedGraph"
  bw2bedGraph := fmt.Sprintf("/home/%s/%s/crunch_scripts/lightning_dev/bin/bigWigToBedGraph", user, user )
  bedGraphDestDir := fmt.Sprintf("/scratch/%s/bedGraph", user )
  cytomapFilename := "ucsc.cytomap.hg19.txt"

  fmt.Println("user:", user )
  fmt.Println("Using cytomap files:", cytomapFilename )


  bandBounds := make( map[string]map[int][2]int )

  aux.BuildBandBounds( bandBounds, cytomapFilename )

  /*
  for k,v := range bandBounds {
    for j := 0; j < len(v) ; j++ {
      fmt.Println( k, v[j][0], v[j][1] )
    }
  }
  */


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
      infile := fmt.Sprintf("/scratch/%s/wgEncodeCrgMapabilityAlign24mer.bw", user )
      outfile := fmt.Sprintf("%s/%s_band%d_s%d_e%d.bedGraph", bedGraphDestDir, chrom, j, s, e )

      oput, err := exec.Command( bw2bedGraph , opt1, opt2, opt3, infile, outfile ).CombinedOutput()
      if err != nil { panic(err) }

    }
  }

  

}

