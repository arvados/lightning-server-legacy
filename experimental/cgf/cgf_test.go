package cgf

import "fmt"
import "os"
import "testing"
import "io/ioutil"

var test_cgf []byte = []byte(`{"#!cgf":"a",
      "CGFVersion" : "0.4",

      "Encoding" : "utf8",
      "Notes" : "ABV Version 0.3",

       "TileLibraryVersion" : "0.1.2",


      "PathCount" : 3,
      "StepPerPath" : [ 35, 32, 38, 10 ],
      "TotalStep" : 108,

      "EncodedTileMap":"_.0:0;_*0:0;x.1:0;x.0:1;x*1:0;x*0:1;_.1:1;_.1:1;x.2,5:3;x*23:80;x.6,7+2,8:11",
      "EncodedTileMapMd5Sum":"ea05336caf0bda6e58723f9636527b33",

      "TileMap" : [
        { "Type" : "hom", "VariantLength" : [[1],[1]], "Ploidy":2, "Variant" : [ [0],[0] ] },
        { "Type" : "hom*", "VariantLength" : [[1],[1]], "Ploidy":2, "Variant" : [ [0],[0] ] },
        { "Type" : "het", "VariantLength" : [[1],[1]], "Ploidy":2, "Variant" : [ [1],[0] ] },
        { "Type" : "het", "VariantLength" : [[1],[1]], "Ploidy":2, "Variant" : [ [0],[1] ] },
        { "Type" : "het*", "VariantLength" : [[1],[1]], "Ploidy":2, "Variant" : [ [1],[0] ] },
        { "Type" : "het*", "VariantLength" : [[1],[1]], "Ploidy":2, "Variant" : [ [0],[1] ] },
        { "Type" : "hom", "VariantLength" : [[1],[1]], "Ploidy":2, "Variant" : [ [1],[1] ] },
        { "Type" : "hom", "VariantLength" : [[1],[1]], "Ploidy":2, "Variant" : [ [1],[1] ] },
        { "Type" : "het", "VariantLength" : [[1,1],[2]], "Ploidy":2, "Variant" : [[2,5],[3]] },
        { "Type" : "het*", "VariantLength" : [[1],[1]], "Ploidy":2, "Variant" : [[35],[128]] },
        { "Type" : "het", "VariantLength" : [[1,2,1],[4]], "Ploidy":2, "Variant" : [[6,7,8],[17]] }
      ],

      "CharMap" : { "." :  0,
                    "A" :  0, "B" :  1, "C" :  2, "D" :  3, "E" :  4, "F" :  5, "G" :  6, "H" :  7, "I" :  8,
                    "J" :  9, "K" : 10, "L" : 11, "M" : 12, "N" : 13, "O" : 14, "P" : 15, "Q" : 16, "R" : 17,
                    "S" : 18, "T" : 19, "U" : 20, "V" : 21, "W" : 22, "X" : 23, "Y" : 24, "Z" : 25, "a" : 26,
                    "b" : 27, "c" : 28, "d" : 29, "e" : 30, "f" : 31, "g" : 32, "h" : 33, "i" : 34, "j" : 35,
                    "k" : 36, "l" : 37, "m" : 38, "n" : 39, "o" : 40, "p" : 41, "q" : 42, "r" : 43, "s" : 44,
                    "t" : 45, "u" : 46, "v" : 47, "w" : 48, "x" : 49, "y" : 50, "z" : 51, "0" : 52, "1" : 53,
                    "2" : 54, "3" : 55, "4" : 56, "5" : 57, "6" : 58, "7" : 59,

                    "^" : -4, "*" : -3, "#" : -2, "-" : -1,
                    "8" : 60, "9" : 61, "+" : 62, "/" : 63
                  },

      "CanonicalCharMap" : ".BCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz012345678*#-",
      "ReservedCharCount" : 3,

      "ABV" : {
        "0" : "----------...----D--..#..DD-----",
        "1" : "--***G-....-A--#--..#....E---",
        "2" : "-...----***C-....-A--#--..#....F---",
        "3" : "..BCDEK***"
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


func TestVariant( t *testing.T ) {

  f,err := ioutil.TempFile( "", "" )
  if err != nil { t.Error( err ) }

  f.Write( test_cgf )
  f.Close()

  cg,ee := Load( f.Name() )
  if ee != nil { t.Error(ee) }

  ee = os.Remove( f.Name() )
  if ee != nil { t.Error(ee) }

  path:=3

  // "3" : ".
  if !cg.HasTileVariant( path, 0, 0 ) {
    t.Error( fmt.Errorf("TestVariant(%d, %d, %d) expected, not found\n", path, 0, 0 ) )
  }

  // "3" : "..
  if !cg.HasTileVariant( path, 1, 0 ) {
    t.Error( fmt.Errorf("TestVariant(%d, %d, %d) expected, not found\n", path, 1, 0 ) )
  }

  // "3" : "..B
  if !cg.HasTileVariant( path, 2, 0 ) {
    t.Error( fmt.Errorf("TestVariant(%d, %d, %d) expected, not found\n", path, 2, 0 ) )
  }


  // "3" : "..BC
  if !cg.HasTileVariant( path, 3, 0 ) {
    t.Error( fmt.Errorf("TestVariant(%d, %d, %d) expected, not found\n", path, 3, 0 ) )
  }

  if !cg.HasTileVariant( path, 3, 1 ) {
    t.Error( fmt.Errorf("TestVariant(%d, %d, %d) expected, not found\n", path, 3, 1 ) )
  }


  // "3" : "..BCD
  if !cg.HasTileVariant( path, 4, 1 ) {
    t.Error( fmt.Errorf("TestVariant(%d, %d, %d) expected, not found\n", path, 4, 1 ) )
  }

  if !cg.HasTileVariant( path, 4, 0 ) {
    t.Error( fmt.Errorf("TestVariant(%d, %d, %d) expected, not found\n", path, 4, 0 ) )
  }


  // "3" : "..BCDE
  if !cg.HasTileVariant( path, 5, 0 ) {
    t.Error( fmt.Errorf("TestVariant(%d, %d, %d) expected, not found\n", path, 5, 0 ) )
  }

  if !cg.HasTileVariant( path, 5, 1 ) {
    t.Error( fmt.Errorf("TestVariant(%d, %d, %d) expected, not found\n", path, 5, 1 ) )
  }


  // "3" : "..BCDEK
  if !cg.HasTileVariant( path, 6, 6 ) {
    t.Error( fmt.Errorf("TestVariant(%d, %d, %d) expected, not found\n", path, 6, 6 ) )
  }

  if !cg.HasTileVariant( path, 6, 17 ) {
    t.Error( fmt.Errorf("TestVariant(%d, %d, %d) expected, not found\n", path, 6, 17 ) )
  }


  if !cg.HasTileVariant( path, 7, 7 ) {
    t.Error( fmt.Errorf("TestVariant(%d, %d, %d) expected, not found\n", path, 7, 7 ) )
  }

  if !cg.HasTileVariant( path, 9, 8 ) {
    t.Error( fmt.Errorf("TestVariant(%d, %d, %d) expected, not found\n", path, 9, 8 ) )
  }



}

func TestCreateTileMapCacheKey( t *testing.T ) {
  varTypes := []string{ "het", "het*", "hom", "hom*" }
  varIds := [][][]int{ [][]int{ []int{0,1,2,3,4}, []int{1} },
                       [][]int{ []int{3}, []int{15, 1} },
                       [][]int{ []int{0}, []int{0} },
                       [][]int{ []int{15}, []int{15} } }
  varLens := [][][]int{ [][]int{ []int{1,1,1,15,1}, []int{19} },
                        [][]int{ []int{2}, []int{1, 1} },
                        [][]int{ []int{1}, []int{1} },
                        [][]int{ []int{10}, []int{10} } }

  expected := []string{ "x.0,1,2,3+f,4:1+13", "x*3+2:f,1", "_.0:0", "_*f+a:f+a" }
  for ind:=0; ind<len(varTypes); ind++ {
    key := string( CreateEncodedTileMapKey( varTypes[ind], varIds[ind], varLens[ind] ) )

    if key!=expected[ind] {
      t.Error( fmt.Errorf("key %s != expected %s\n", key, expected[ind]) )
    }

  }

}

func TestDefaultEncodings( t *testing.T ) {

  a := string( CreateEncodedTileMap( DefaultTileMap() ) )
  b := DefaultEncodedTileMap()

  if a!=b {
    t.Error( fmt.Errorf("Default TileMap and EncodedTileMap don't match!\n" ) )
  }

}

func _cmp_tile_map( tile_map_entry_a, tile_map_entry_b []TileMapEntry ) error {

  if len(tile_map_entry_a) != len(tile_map_entry_b) {
    return fmt.Errorf("Lengths of tile map entries do not match (%d != %d)\n", len(tile_map_entry_a), len(tile_map_entry_b) )
  }

  for i:=0; i<len(tile_map_entry_a); i++ {

    if tile_map_entry_a[i].Type != tile_map_entry_b[i].Type {
      return fmt.Errorf("TileMap[%d] Type entries do not match (%s != %s)\n",
        i, tile_map_entry_a[i].Type, tile_map_entry_b[i].Type )
    }

    if tile_map_entry_a[i].Ploidy != tile_map_entry_b[i].Ploidy {
      return fmt.Errorf("TileMap[%d] Ploidy entries do not match (%d != %d)\n",
        i, tile_map_entry_a[i].Ploidy , tile_map_entry_b[i].Ploidy )
    }

    if len(tile_map_entry_a[i].Variant) != len(tile_map_entry_b[i].Variant) {
      return fmt.Errorf("TileMap[%d] Variant lengths do not match (%d != %d)\n",
        i, len(tile_map_entry_a[i].Variant), len(tile_map_entry_b[i].Variant))
    }

    m:=len(tile_map_entry_a[i].Variant)

    for j:=0; j<m; j++ {

      if len(tile_map_entry_a[i].Variant[j]) != len(tile_map_entry_b[i].Variant[j]) {
        return fmt.Errorf("TileMap[%d] Variant[%d] lengths do not match (%d != %d)\n",
          i, j, len(tile_map_entry_a[i].Variant[j]), len(tile_map_entry_b[i].Variant[j]) )
      }

      for k:=0; k<len(tile_map_entry_a[i].Variant[j]); k++ {
        if tile_map_entry_a[i].Variant[j][k] != tile_map_entry_b[i].Variant[j][k] {
          return fmt.Errorf("TileMap[%d] Variant[%d][%d] entries do not match (%d != %d)\n",
            i, j, k, tile_map_entry_a[i].Variant[j][k], tile_map_entry_b[i].Variant[j][k] )
        }
      }

      if len(tile_map_entry_a[i].VariantLength[j]) != len(tile_map_entry_b[i].VariantLength[j]) {
        return fmt.Errorf("TileMap[%d] VariantLength[%d] lengths do not match (%d != %d)\n",
          i, j, len(tile_map_entry_a[i].VariantLength[j]), len(tile_map_entry_b[i].VariantLength[j]) )
      }

      for k:=0; k<len(tile_map_entry_a[i].VariantLength[j]); k++ {
        if tile_map_entry_a[i].VariantLength[j][k] != tile_map_entry_b[i].VariantLength[j][k] {
          return fmt.Errorf("TileMap[%d] Variant[%d][%d] entries do not match (%d != %d)\n",
            i, j, k, tile_map_entry_a[i].VariantLength[j][k], tile_map_entry_b[i].VariantLength[j][k] )
        }
      }


    }

  }

  return nil

}

func TestTileMapConversion( t *testing.T ) {
  f,err := ioutil.TempFile( "", "" )
  if err != nil { t.Error( err ) }

  f.Write( test_cgf )
  f.Close()

  cg,ee := Load( f.Name() )
  if ee != nil { t.Error(ee) }

  ee = os.Remove( f.Name() )
  if ee != nil { t.Error(ee) }

  //encoded_tile_map_bytes := cg.CreateEncodedTileMap()
  encoded_tile_map_bytes := CreateEncodedTileMap( cg.TileMap )
  encoded_tile_map_string := string( encoded_tile_map_bytes )

  //tile_map_entry,e := cg.CreateTileMapFromEncodedTileMap( encoded_tile_map_string )
  tile_map_entry,e := CreateTileMapFromEncodedTileMap( encoded_tile_map_string )
  if e!=nil { t.Error(e) }

  e = _cmp_tile_map( tile_map_entry, cg.TileMap )
  if e!=nil { t.Error( e ) }

  //fmt.Printf("IGNORING Default TestTileMapConversion\n")
  //return

  unphased_tile_map := DefaultTileMapUnphased()
  unphased_encoded_tile_map := DefaultEncodedTileMapUnphased()
  converted_unphased_tile_map,err := CreateTileMapFromEncodedTileMap( unphased_encoded_tile_map )
  if err!=nil { t.Error(err) }

  e = _cmp_tile_map( unphased_tile_map, converted_unphased_tile_map )
  if e!=nil { t.Error( e ) }

  //------------

  /*
  if len(tile_map_entry) != len(cg.TileMap) {
    t.Error( fmt.Errorf("Lengths of tile map entries do not match (%d != %d)\n", len(tile_map_entry), len(cg.TileMap) ) )
  }

  for i:=0; i<len(tile_map_entry); i++ {

    if tile_map_entry[i].Type != cg.TileMap[i].Type {
      t.Error( fmt.Errorf("TileMap[%d] Type entries do not match (%s != %s)\n",
        i, tile_map_entry[i].Type, cg.TileMap[i].Type ) )
    }

    if tile_map_entry[i].Ploidy != cg.TileMap[i].Ploidy {
      t.Error( fmt.Errorf("TileMap[%d] Ploidy entries do not match (%d != %d)\n",
        i, tile_map_entry[i].Ploidy , cg.TileMap[i].Ploidy ) )
    }

    if len(tile_map_entry[i].Variant) != len(cg.TileMap[i].Variant) {
      t.Error( fmt.Errorf("TileMap[%d] Variant lengths do not match (%d != %d)\n",
        i, len(tile_map_entry[i].Variant), len(cg.TileMap[i].Variant)) )
    }

    m:=len(tile_map_entry[i].Variant)

    for j:=0; j<m; j++ {

      if len(tile_map_entry[i].Variant[j]) != len(cg.TileMap[i].Variant[j]) {
        t.Error( fmt.Errorf("TileMap[%d] Variant[%d] lengths do not match (%d != %d)\n",
          i, j, len(tile_map_entry[i].Variant[j]), len(cg.TileMap[i].Variant[j]) ) )
      }

      for k:=0; k<len(tile_map_entry[i].Variant[j]); k++ {
        if tile_map_entry[i].Variant[j][k] != cg.TileMap[i].Variant[j][k] {
          t.Error( fmt.Errorf("TileMap[%d] Variant[%d][%d] entries do not match (%d != %d)\n",
            i, j, k, tile_map_entry[i].Variant[j][k], cg.TileMap[i].Variant[j][k] ) )
        }
      }

    }

  }
  */


}


func TestNew( t *testing.T ) {

  cg := New()
  _ = cg

  if cg.PathCount != len(cg.StepPerPath) {
    t.Error( fmt.Errorf("PathCount (%d) != len(cg.StepPerPath) (%d)\n", cg.PathCount, len(cg.StepPerPath) ) )
  }

  s := 0
  for i:=0; i<len(cg.StepPerPath); i++ {
    s += cg.StepPerPath[i]
    if s != cg.StepPerPathSum[i] {
      t.Error( fmt.Errorf("StepPerPathSum[%d] (%d)!= sum(cg.StepPerPath[0:%d]) (%d)\n", i, cg.StepPerPathSum[i], i, s ) )
    }
  }

  if s != cg.TotalStep {
    t.Error( fmt.Errorf("TotalStep (%d) != sum(cg.StepPerPath) (%d)\n", cg.TotalStep, s ) )
  }

}

func TestDefaultTileMap( t *testing.T ) {

  z := DefaultTileMap()

  if len(z) == 0 { t.Error( fmt.Errorf("zero default tile map") ) }

  for i:=0; i<len(z); i++ {
    if z[i].Ploidy != 2 {
      t.Error( fmt.Errorf("Ploidy of default tile map not 2 (element:%d, value:%v)\n", i, z) )
    }

    for j:=0; j<len(z[i].Variant); j++ {
      if len(z[i].Variant[0]) != len(z[i].VariantLength[0]) {
        t.Error( fmt.Errorf("Variant %d length mismatch (%d != %d)\n", len(z[i].Variant[0]), z[i].VariantLength[0] ) )
      }
    }

  }

}

func TestLookups( t *testing.T ) {
  lookup := [][]int{ []int{0}, []int{0} }
  lookup_len := [][]int{ []int{1}, []int{1} }

  f,err := ioutil.TempFile( "", "" )
  if err != nil { t.Error( err ) }

  f.Write( test_cgf )
  f.Close()

  cg,ee := Load( f.Name() )
  if ee != nil { t.Error(ee) }

  ee = os.Remove( f.Name() )
  if ee != nil { t.Error(ee) }

  p := cg.LookupTileMapVariant( "hom", lookup, lookup_len )

  if p!=0 {
    t.Error( fmt.Errorf("Variant %v length failure (got %d, expected 0)\n", lookup, p ) )
  }

  s,found := cg.LookupABVCharCode( p )
  _ = s
  _ = found
}

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

  of,err := ioutil.TempFile( "", "" )
  if err != nil { t.Error( err ) }

  cgf.PrintFile( of )
  of.Close()

  ee = os.Remove( of.Name() )

}

