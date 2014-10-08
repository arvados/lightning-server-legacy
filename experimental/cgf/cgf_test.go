package cgf

import "fmt"
import "os"
import "testing"
import "io/ioutil"

var test_cgf []byte = []byte(`{
      "CGFVersion" : "0.1",

      "Encoding" : "utf8",
      "Notes" : "ABV Version 0.1",

       "TileLibraryVersion" : "0.1.2",


      "PathCount" : 3,
      "StepPerPath" : [ 35, 32, 38 ],
      "TotalStep" : 108,

      "TileMap" : [
        { "Type" : "hom", "VariantALength" : 1, "VariantA" : [0], "VariantBLength" : 1, "VariantB" : [0] },
        { "Type" : "hom*", "VariantALength" : 1, "VariantA" : [0], "VariantBLength" : 1, "VariantB" : [0] },
        { "Type" : "het", "VariantALength" : 1, "VariantA" : [1], "VariantBLength" : 1, "VariantB" : [0] },
        { "Type" : "het", "VariantALength" : 1, "VariantA" : [0], "VariantBLength" : 1, "VariantB" : [1] },
        { "Type" : "het*", "VariantALength" : 1, "VariantA" : [1], "VariantBLength" : 1, "VariantB" : [0] },
        { "Type" : "het*", "VariantALength" : 1, "VariantA" : [0], "VariantBLength" : 1, "VariantB" : [1] },
        { "Type" : "hom", "VariantALength" : 1, "VariantA" : [1], "VariantBLength" : 1, "VariantB" : [1] },
        { "Type" : "hom", "VariantALength" : 1, "VariantA" : [1], "VariantBLength" : 1, "VariantB" : [1] },
        { "Type" : "het", "VariantALength" : 2, "VariantA" : [2,5], "VariantBLength" : 1, "VariantB" : [3] },
        { "Type" : "het*", "VariantALength" : 1, "VariantA" : [35], "VariantBLength" : 1, "VariantB" : [128] }
      ],

      "CharMap" : { "." :  0,
                    "A" :  0, "B" :  1, "C" :  2, "D" :  3, "E" :  4, "F" :  5, "G" :  6, "H" :  7, "I" :  8,
                    "J" :  9, "K" : 10, "L" : 11, "M" : 12, "N" : 13, "O" : 14, "P" : 15, "Q" : 16, "R" : 17,
                    "S" : 18, "T" : 19, "U" : 20, "V" : 21, "W" : 22, "X" : 23, "Y" : 24, "Z" : 25, "a" : 26,
                    "b" : 27, "c" : 28, "d" : 29, "e" : 30, "f" : 31, "g" : 32, "h" : 33, "i" : 34, "j" : 35,
                    "k" : 36, "l" : 37, "m" : 38, "n" : 39, "o" : 40, "p" : 41, "q" : 42, "r" : 43, "s" : 44,
                    "t" : 45, "u" : 46, "v" : 47, "w" : 48, "x" : 49, "y" : 50, "z" : 51, "0" : 52, "1" : 53,
                    "2" : 54, "3" : 55, "4" : 56, "5" : 57, "6" : 58, "7" : 59,

                    "^" : -4, "-" : -3, "*" : -2, "#" : -1,
                    "8" : 60, "9" : 61, "+" : 62, "/" : 63
                  },

      "ABV" : {
        "0" : "----------...----D--..#..DD-----",
        "1" : "--***G-....-A--#--..#....E---",
        "2" : "-...----***C-....-A--#--..#....F---"
      },

      "OverflowMap" : {
        "0:16" : 5,
        "1:f" : 3,
        "1:14" : 1,
        "2:15" : 7
      },

      "FinalOverflowMap" : {
        "2:1a" : {
          "Type" : "FastJ",
          "Data" : "> { \"tileID\" : \"002.00.001a.000\", \"md5sum\":\"674e7222996958b1a7f7f2d4fc2f3d3a\", \"locus\":[{\"build\":\"hg19 chr1 5406075 5406324\"}], \"n\":249, \"copy\":0, \"startSeq\":\"tttccaaaataaccactaagctca\", \"endSeq\":\"CCAATTGCCGAAATACCTAACAGC\", \"startTag\":\"TTTCCAAAATAACCACTAAGCTCA\", \"endTag\":\"CCAATTGCCGAAATACCTAACAGC\", \"notes\":[\"hg19 chr1 5406120 5406120 GAP 45 1\", \"Phase (RANDOM) A\"]}\nTTTCCAAAATAACCACTAAGCTCAtgggaaaactgggtgacttcatcccc\nacccccaactctggaaatgaaagccactcccactgctgatctctcccttc\ntcttggccatcaggcaatccagctggcccttgcctagatgatgtgacagg\ntgagagtcaggctccaatcccaggctctgcaaagtctggggcttcgatca\naatcctcccaagcactctgttaccaCCAATTGCCGAAATACCTAACAGC"
                }
      }
}`)


func TestLoad( t *testing.T ) {
  f,err := ioutil.TempFile( "", "" )
  if err != nil { t.Error( err ) }

  f.Write( test_cgf )
  f.Close()

  cgf,ee := Load( f.Name() )
  if ee != nil { t.Error(ee) }

  ee = os.Remove( f.Name() )
  if ee != nil { t.Error(ee) }

  for path:=0; path<cgf.PathCount; path++ {
    istr := fmt.Sprintf("%d", path)
    hstr := fmt.Sprintf("%x", path); _ = hstr

    abv,ok := cgf.ABV[istr]
    if !ok { t.Errorf("Could not find %s in ABV", istr) }

    for step:=0; step<len(abv); step++ {
      v,ok := cgf.CharMap[ string(abv[step]) ]
      if !ok { t.Errorf("Could not find step in %s,%d ABV", istr, step) }

      if (v>0) && (v >= len(cgf.TileMap)) {
        t.Errorf("position map %d exceeds maximum len(TileMap) (%d) in path %s ABV", v, len(cgf.TileMap), istr)
      }

      if abv[step] == '#' {
        key := fmt.Sprintf("%x:%x", path, step)

        ele0,ok := cgf.OverflowMap[key]
        if !ok {
          ele1,ok1 := cgf.FinalOverflowMap[key] ; _ = ele1
          if !ok1 { t.Errorf("Could not find overflow element %s", key) }

        } else {

          if ele0 >= len(cgf.TileMap) {
            t.Errorf("overflow element position map %d,%d (%s) exceeds maximum len(TileMap) (%d) in ABV",
              path, step, key, len(cgf.TileMap) )
          }

        }

      } else if abv[step] == '-' {
      } else if abv[step] == '*' {
      } else {
        tm := cgf.TileMap[v]
        _ = tm
      }

    }

  }

  //cgf.Print()

  of,err := ioutil.TempFile( "", "" )
  if err != nil { t.Error( err ) }


  //of,err := os.Create( test_fn )
  //if err != nil { t.Errorf("could not open output file '/tmp/test.cgf'") }
  //defer of.Close()

  cgf.PrintFile( of )
  of.Close()

  ee = os.Remove( of.Name() )

}

