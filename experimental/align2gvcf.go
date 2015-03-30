package main

import "os"
import "fmt"
import "log"


import "github.com/biogo/biogo/align"
import "github.com/biogo/biogo/alphabet"
import "github.com/biogo/biogo/seq/linear"
import "github.com/biogo/biogo/feat"

import "github.com/abeconnelly/autoio"
import "github.com/codegangsta/cli"

var VERSION_STR string = "AGPLv3, v0.0.1"

var gProfileFlag bool = false
var gProfileFile string = "align2vcf.cprof"
var gMemProfileFile string = "align2vcf.mprof"
var g_verbose bool = false
var g_normalize_flag bool = true

var g_chrom string = "Un"

var g_align_type string = "nw"

type GVCFState struct {
  Start int
  N int
  State int
}

var strState []string = []string{ "nocall", "ref", "snp", "sub", "indel" }

func byte_low( b byte ) byte {
  if b >= 'A' && b <= 'Z' { return b+32 }
  return b
}


var gvcf_state GVCFState

// Move left to the first non gap character
//
func _ldash( seq []byte ) int {
  for n := len(seq)-1; n>0; n-- {
    if seq[n] != '-' { return n }
  }
  return 0
}

// Helper print function for debugging.
//
func _dbgprs( note string, s []byte, l, p, dp int ) {
  N := len(s)

  fmt.Printf("%s: ", note)
  for i:=0; i<N; i++ {
    if i==p { fmt.Printf("v")
    } else if i==p+dp { fmt.Printf("]")
    } else { fmt.Printf(" ") }

  }
  fmt.Printf("\n%s: %s\n", note, s)

  fmt.Printf("%s: ", note)
  for i:=0; i<N; i++ {
    if i==l { fmt.Printf("|")
    } else { fmt.Printf(" ") }
  }
  fmt.Printf("\n")

}

//--

func _dbgpr( note string, s []byte, p, dp int ) {
  N := len(s)

  fmt.Printf("%s: ", note)
  for i:=0; i<N; i++ {
    if i==p { fmt.Printf("v")
    } else if i==p+dp { fmt.Printf("]")
    } else { fmt.Printf(" ") }

  }
  fmt.Printf("\n%s: %s\n", note, s)
}


// http://genome.sph.umich.edu/wiki/Variant_Normalization
// pseudo code:
//   processing <- true
//   while processing do
//     /* Extend (+) */
//     if alleles end with same nucleotide then
//       truncate rightmost nucleotide on each allele
//     end if
//     /* Delete (-) */
//     if there's an empty allele then
//       extend both alleles 1 nucleotide to the left
//     end if
//   end while
//   while leftmost nucleotide of each allele are the same and all alleles have length 2 or more do
//     truncate leftmost nucleotide of each allele
//   end while
//
// for example, if we had the sequences (pre-aligned):
//
// gactactg
// gact---g
//
// Then the series of operations would be:
//
//    act -(+)-> tact -(-)-> tac -(+)-> ctac -(-)-> cta -(+)-> acta -(-)-> act -(+)-> gact
//    _   -(+)-> t    -(-)-> _   -(+)-> c    -(-)-> _   -(+)-> a    -(-)-> _   -(+)-> g
//
// From a sequence pair-alignment view, it looks vaguely like the following:
//
//  gactactg => gactactg => gactactg => gactactg
//  gact___g => gac___tg => ga___ctg => g___actg
//
// The final step of culling nucleotides from the left does not apply to this example.
//
// Note, alignments like the following may be confusing:
//
//    gcatgcatg
//    g----catg
//
//  In normalized VCF format, this would change to:
//
//    gcatgcatg
//    gcat----g
//
//  This is valid and expected.  It's informative to realize that you're really
//  trying to express the alignment of the following two sequences:
//
//    gcatgcatg
//    gcatg
//
//  Aligning the string 'gcatgcatg' to 'gcatg' could mean
//  "replace the first occurance of 'catg' with gaps" or could also mean "replace the
//  second occurance of 'gcat' with gaps".  The VCF renormalization step chooses the
//  first as the canonical representation.
//

func bp_eq( a,b byte ) bool {
  if a==b { return true }
  if (a=='N' || a=='n') && b!='-' { return true }
  if (b=='N' || b=='n') && a!='-' { return true }
  return false
}

func seq_pair_normalize( seq_a, seq_b []byte ) error {

  if len(seq_a) != len(seq_b) {
    return fmt.Errorf( "sequences have varying length.  Sequences must be of same length" )
  }

  b0 := len(seq_a)-1 ; n0 := 1
  b1 := len(seq_b)-1 ; n1 := 1

  for (b0>0) && (b1>0) {

    processing := true
    for processing {
      processing = false

      if (n0>0) && (n1>0) && bp_eq(seq_a[b0+n0-1], seq_b[b1+n1-1]) {
        processing = true
        n0--
        n1--
      }

      if (b0==0) || (b1==0) { break }

      if (n0==0) || (n1==0) {
        processing = true

        b0-- ; n0++
        b1-- ; n1++

        // inefficient, replace with saved left state
        // after we get working.
        //
        // Swap gap character with current character
        l0 := b0
        if seq_a[b0] == '-' {
          l0 = _ldash( seq_a[0:l0] )
        }

        l1 := b1
        if seq_b[b1] == '-' {
          l1 = _ldash( seq_b[0:l1] )
        }

        //if seq_a[l0] == seq_b[l1] {
        if bp_eq(seq_a[l0], seq_b[l1]) {
          if seq_a[b0] == '-' {
            seq_a[b0], seq_a[l0] = seq_a[l0], seq_a[b0]
          }
          if seq_b[b1] == '-' {
            seq_b[b1], seq_b[l1] = seq_b[l1], seq_b[b1]
          }
        }
      }

    }

    n0=0
    n1=0

  }

  return nil

}

// Return an array of SeqDiff that holds the digested information that
// can easily be converted to gVCF calls.
//
const (
  NOCALL int = 0
  REF    int = 1
  SNP    int = 2
  SUB    int = 3
  INDEL  int = 4
)

type SeqDiff struct {
  Pos []int
  Len []int
  N int
  Ref []byte
  Alt []byte
  Type int
}


// Essentially gVCF emits non-ref lines, which include
// alts.  Non ref lines that are low-quality are emited
// with a bare '<NON_REF>' Alt sequnence.
//
func emit_gvcf( seqdiff *SeqDiff ) {
  chrom := g_chrom
  pos := seqdiff.Pos[0]
  id := "."
  qual := "."
  filt := "."
  info := fmt.Sprintf("END=%d", seqdiff.Pos[0]+seqdiff.Len[0])
  format := "."

  var ref_seq string
  var alt_seq string

  // Which allele the variant falls on
  //
  // '/' unphased, '|' phased
  //
  samp := "."

  switch seqdiff.Type {
  case NOCALL:
    if len(seqdiff.Ref) > 1 {
      ref_seq = string(seqdiff.Ref[1:2])
    } else {
      ref_seq = "."
    }
    alt_seq = "<NON_REF>"
    pos++
  case REF: return
  case SNP:
  case SUB:
    ref_seq = fmt.Sprintf("%s", seqdiff.Ref)
    alt_seq = fmt.Sprintf("%s,<NON_REF>", seqdiff.Alt)

    if (seqdiff.Pos[0] > 0) {
      if len(ref_seq)>0 { ref_seq = ref_seq[1:] }
      if len(alt_seq)>0 { alt_seq = alt_seq[1:] }
    }
    pos++
  case INDEL:
    ref_seq = fmt.Sprintf("%s", seqdiff.Ref)
    alt_seq = fmt.Sprintf("%s,<NON_REF>", seqdiff.Alt)

  default:
  }


  fmt.Printf("%s\t%d\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n",
    chrom, pos, id, ref_seq, alt_seq, qual, filt, info, format, samp )

}

func debug_print_seqdiff( seqdiff SeqDiff ) {

  zz := g_var_name_map[seqdiff.Type]
  if seqdiff.Type == SUB && seqdiff.Len[0] == 1 {
    zz = "snp"
  }

  fmt.Printf("(%d) [%d+%d,%d+%d] ref(%s) alt(%s) type:%d(%s)\n",
  seqdiff.N,
  seqdiff.Pos[0], seqdiff.Len[0],
  seqdiff.Pos[1], seqdiff.Len[1],
  seqdiff.Ref, seqdiff.Alt,
  seqdiff.Type, zz )
}

var g_var_name_map map[int]string

func _t_nc( x,y byte ) bool {
  if y=='n' { return true }
  return false
}

func _t_ref( x,y byte ) bool {
  if x!='n' && y!='n' && x==y { return true }
  return false
}

func _t_indel( x,y byte ) bool {
  if x=='-' || y=='-' { return true }
  return false
}

func _t_sub( x,y byte ) bool {
  if x!='n' && y!='n' && x!='-' && y!='-' && x!=y { return true }
  return false
}

func _seqdiff_update( s *SeqDiff, typ int, x,y int, refseq,altseq []byte ) {

  s.Len[0] = x - s.Pos[0]
  s.Len[1] = y - s.Pos[1]
  s.Ref = refseq
  s.Alt = altseq
  s.Type = typ

}

func _seqdiff_reset( s *SeqDiff, x,y int ) {
  s.Pos[0] = x ; s.Pos[1] = y
  s.Len[0] = 0 ; s.Len[1] = 0
  s.N = 2
  s.Ref = make( []byte, 0, 8 )
  s.Alt = make( []byte, 0, 8 )
  s.Type = -1
}

func _transition( ref,alt byte ) (int) {

  if        _t_nc( ref, alt )  { return NOCALL
  } else if _t_ref( ref, alt ) { return REF
  } else if _t_sub( ref, alt ) { return SUB
  } else if _t_indel( ref, alt ) { return INDEL }

  fmt.Printf("ERROR transition %v %v\n", ref, alt )

  return -1
}


func _update_bp_str( seq, par_seq  []byte, s, e int ) []byte {
  if (s<0) { s=0 }

  // If we're not in the special case of being at the
  // beginning of the sequence...
  //
  if s>=0 {
    seq = append( seq, par_seq[s:e]... )
    p:=0

    // Remove '-' gap characters and resize slice.
    //
    for i:=0; i<len(seq); i++ {
      if seq[i]=='-' { continue }
      seq[p] = seq[i]
      p++
    }
    seq = seq[0:p]
    if len(seq) == 0 { seq = append(seq, '.') }
  } else {
  }

  return seq

}

func diff_from_aligned_seqs( seq_ref, seq_alt []byte ) ( []SeqDiff, error ) {

  mm := make( map[int]string )
  mm[NOCALL] = "nocall"
  mm[REF] = "ref"
  mm[SUB] = "sub"
  mm[SNP] = "snp"
  mm[INDEL] = "indel"

  seq_diffs := make( []SeqDiff, 0, 8 )

  n := len(seq_ref)
  x := 0
  y := 0

  //curdiff := SeqDiff{ []int{0,0}, []int{0,0}, 2, []byte(""), []byte(""), NOCALL }
  curdiff := &SeqDiff{ []int{0,0}, []int{0,0}, 2, []byte(""), []byte(""), NOCALL }
  prev_ref_byte := byte('.') ; _ = prev_ref_byte
  state := NOCALL
  new_state := state

  for (x<n) && (y<n) {

    new_state = _transition( seq_ref[x], seq_alt[y] )
    if new_state != state {
      _seqdiff_update( curdiff, state, x, y, []byte(""), []byte("") )

      // Skip first position
      //
      if x!=0 && y!=0 {

        // If we've transitioned from a substitution to
        // and indel, don't emit a seqdiff line but
        // change state.
        //
        if state==SUB && new_state==INDEL {
          curdiff.Type = INDEL
        } else {

          // (g)VCF wants the first REF base, so start at
          // one position before.
          //
          s,e:=curdiff.Pos[0]-1,curdiff.Pos[0]+curdiff.Len[0]
          curdiff.Ref = _update_bp_str( curdiff.Ref, seq_ref, s, e )

          s,e = curdiff.Pos[1]-1,curdiff.Pos[1]+curdiff.Len[1]
          curdiff.Alt = _update_bp_str( curdiff.Alt, seq_alt, s, e )

          seq_diffs = append(seq_diffs, *curdiff)
          curdiff = &SeqDiff{ []int{x,y}, []int{0,0}, 2, []byte(""), []byte(""), state }

        }

      } else {
        if new_state==SUB {
          curdiff.Pos[0] = 0
          curdiff.Pos[1] = 0
          curdiff.Type = SUB
        }
      }

      state = new_state
    }

    x++ ; y++

  }

  _seqdiff_update( curdiff, state, x, y, []byte(""), []byte("") )

  s,e:=curdiff.Pos[0]-1,curdiff.Pos[0]+curdiff.Len[0]
  curdiff.Ref = _update_bp_str( curdiff.Ref, seq_ref, s, e )

  s,e = curdiff.Pos[1]-1,curdiff.Pos[1]+curdiff.Len[1]
  curdiff.Alt = _update_bp_str( curdiff.Alt, seq_alt, s, e )

  seq_diffs = append(seq_diffs, *curdiff )

  return seq_diffs, nil

}

// Corner case when one or both of the sequences is 0 length.
//
func corner_gap_case( ref, seqb string ) error {
  if (len(ref)==0) && (len(seqb)==0) { return nil }

  curdiff := &SeqDiff{ []int{0,0}, []int{0,0}, 2, []byte(""), []byte(""), INDEL }
  curdiff.Pos[0] = 1

  if len(ref)==0 {
    curdiff.Ref = []byte("")
    curdiff.Alt = []byte(seqb)
    curdiff.Len[0] = len(seqb)
  } else {
    curdiff.Ref = []byte(ref)
    curdiff.Alt = []byte("")
    curdiff.Len[0] = len(ref)
  }

  emit_gvcf( curdiff )
  return nil

}

func seq_align( ref, seqb string ) error {

  if (len(ref)==0) || (len(seqb)==0) {
    return corner_gap_case( ref, seqb )
  }

  custom_alpha := alphabet.MustComplement( alphabet.NewComplementor( "-acgtnx", feat.DNA,
      alphabet.MustPair(alphabet.NewPairing("acgtnxACGTNX-", "tgcanxTGCANX-")), '-', 'n',
      !alphabet.CaseSensitive ))

  fa_ref := &linear.Seq{Seq: alphabet.BytesToLetters([]byte(ref))}
  fa_ref.Alpha = custom_alpha

  fsa := &linear.Seq{Seq: alphabet.BytesToLetters([]byte(seqb))}
  fsa.Alpha = custom_alpha

  var ok bool
  var p  int

  if ok,p = custom_alpha.AllValid(fa_ref.Seq); !ok {
    return fmt.Errorf("Invalid character in reference sequence (pos %d).  Must be one of [-actgn].", p)
  }

  if ok,p = custom_alpha.AllValid(fsa.Seq); !ok {
    return fmt.Errorf("Invalid character in sequence (pos %d).  Must be one of [-actgn].", p)
  }

  var aln_seq_a []byte
  var aln_seq_b []byte

  if g_verbose {
    fmt.Print("raw sequences:\n", fa_ref, "\n", fsa, "\n")
  }

  if g_align_type == "fa" {
    //       Query letter
    //     -   A   C   G   T
    // -   0  -1  -1  -1  -1
    // A  -1   1  -1  -1  -1
    // C  -1  -1   1  -1  -1
    // G  -1  -1  -1   1  -1
    // T  -1  -1  -1  -1   1
    //
    // Gap open: -5
    fitted := align.FittedAffine{
        Matrix: align.Linear{
            { 0, -1, -1, -1, -1, -1, -1},
            {-1,  1, -1, -1, -1, -1, -1},
            {-1, -1,  1, -1, -1, -1, -1},
            {-1, -1, -1,  1, -1, -1, -1},
            {-1, -1, -1, -1,  1, -1, -1},
            {-1, -1, -1, -1, -1,  0, -1},
            {-1, -1, -1, -1, -1, -1,  0},
        },
        GapOpen: -5,
    }

    aln, err := fitted.Align(fa_ref, fsa)
    if err!=nil { return err }

    fa := align.Format(fa_ref, fsa, aln, '-')

    aln_seq_a = []byte( fmt.Sprintf("^%s$", fa[0]) )
    aln_seq_b = []byte( fmt.Sprintf("^%s$", fa[1]) )

  } else if g_align_type == "nw" {

    //Needleman Walsh

    needle := align.NWAffine{
        Matrix: align.Linear{
            //{ 0, -1, -1, -1, -1 },
            //{-1,  1, -1, -1, -1 },
            //{-1, -1,  1, -1, -1 },
            //{-1, -1, -1,  1, -1 },
            //{-1, -1, -1, -1,  1 },

            //-   a   c   g   t   n   x
            { 0, -1, -1, -1, -1, -1, -1},
            {-1,  1, -1, -1, -1, -1, -1},
            {-1, -1,  1, -1, -1, -1, -1},
            {-1, -1, -1,  1, -1, -1, -1},
            {-1, -1, -1, -1,  1, -1, -1},
            {-1, -1, -1, -1, -1,  0, -1},
            {-1, -1, -1, -1, -1, -1,  0},
        },
        GapOpen: -5,
    }

    aln_needle,ee := needle.Align( fa_ref, fsa )
    if ee!=nil { return ee }
    fa_needle := align.Format( fa_ref, fsa, aln_needle, '-')

    // Stuff in anchor points at the beginning and end.
    //
    aln_seq_a = []byte( fmt.Sprintf("^%s$", fa_needle[0]) )
    aln_seq_b = []byte( fmt.Sprintf("^%s$", fa_needle[1]) )

  }

  if g_verbose {
    fmt.Printf("before normalization:\n%s\n%s\n", aln_seq_a, aln_seq_b)
  }

  n:=len(string(aln_seq_a))
  m:=len(string(aln_seq_b))
  if n!=m { return fmt.Errorf("n %d != m %d", n, m) }

  if g_normalize_flag {
    seq_pair_normalize( aln_seq_a, aln_seq_b )
  }

  if g_verbose {
    fmt.Printf("after normalization:\n%s\n%s\n", aln_seq_a, aln_seq_b)
  }

  d,e := diff_from_aligned_seqs( aln_seq_a[1:n], aln_seq_b[1:n] )
  if e!=nil { log.Fatal(e) }

  for i:=0; i<len(d); i++ { emit_gvcf( &d[i] ) }

  return nil

}

func normalize_tests() {
  ta := []byte("a")
  tb := []byte("b")

  // TEST0
  //
  ta = []byte("gaaaac")
  tb = []byte("gaaa-c")

  fmt.Printf("\n")
  fmt.Printf("inp:\n  a: %s\n  b: %s\n", ta, tb )
  seq_pair_normalize( ta, tb )
  fmt.Printf("out:\n  a: %s\n  b: %s\n", ta, tb )

  // TEST1
  //
  ta = []byte("xaaagaaaacw")
  tb = []byte("ya-agaaa-cz")

  fmt.Printf("\n")
  fmt.Printf("inp:\n  a: %s\n  b: %s\n", ta, tb )
  seq_pair_normalize( ta, tb )
  fmt.Printf("out:\n  a: %s\n  b: %s\n", ta, tb )

  // TEST2
  //
  ta = []byte("gactactg")
  tb = []byte("gact---g")

  fmt.Printf("\n")
  fmt.Printf("inp:\n  a: %s\n  b: %s\n", ta, tb )
  seq_pair_normalize( ta, tb )
  fmt.Printf("out:\n  a: %s\n  b: %s\n", ta, tb )

  // TEST3
  //
  ta = []byte("ga-c-a-c-$")
  tb = []byte("g-a-c-a-c$")

  fmt.Printf("\n")
  fmt.Printf("inp:\n  a: %s\n  b: %s\n", ta, tb )
  seq_pair_normalize( ta, tb )
  fmt.Printf("out:\n  a: %s\n  b: %s\n", ta, tb )

  // TEST4
  //
  ta = []byte("gcatgcat-----$")
  tb = []byte("gcatgcatgcatg$")

  fmt.Printf("\n")
  fmt.Printf("inp:\n  a: %s\n  b: %s\n", ta, tb )
  seq_pair_normalize( ta, tb )
  fmt.Printf("out:\n  a: %s\n  b: %s\n", ta, tb )

  // TEST5
  //
  ta = []byte("gcatgcat----$")
  tb = []byte("gcatgcatgcat$")

  fmt.Printf("\n")
  fmt.Printf("inp:\n  a: %s\n  b: %s\n", ta, tb )
  seq_pair_normalize( ta, tb )
  fmt.Printf("out:\n  a: %s\n  b: %s\n", ta, tb )

  // TEST6
  //
  ta = []byte("^catgcatx")
  tb = []byte("vcat----y")

  fmt.Printf("\n")
  fmt.Printf("inp:\n  a: %s\n  b: %s\n", ta, tb )
  seq_pair_normalize( ta, tb )
  fmt.Printf("out:\n  a: %s\n  b: %s\n", ta, tb )

  // TEST7
  //
  ta = []byte("gcatgcat----$")
  tb = []byte("gcazzcatgcat$")

  fmt.Printf("\n")
  fmt.Printf("inp:\n  a: %s\n  b: %s\n", ta, tb )
  seq_pair_normalize( ta, tb )
  fmt.Printf("out:\n  a: %s\n  b: %s\n", ta, tb )

  // TEST8
  //
  ta = []byte("gcatgcatgcat$")
  tb = []byte("gnnn---n--nt$")

  fmt.Printf("\n")
  fmt.Printf("inp:\n  a: %s\n  b: %s\n", ta, tb )
  seq_pair_normalize( ta, tb )
  fmt.Printf("out:\n  a: %s\n  b: %s\n", ta, tb )

  // TEST9
  //
  ta = []byte("gaaaaaaaaaat$")
  tb = []byte("gaaa---a--at$")

  fmt.Printf("\n")
  fmt.Printf("inp:\n  a: %s\n  b: %s\n", ta, tb )
  seq_pair_normalize( ta, tb )
  fmt.Printf("out:\n  a: %s\n  b: %s\n", ta, tb )

  // TEST10
  //
  ta = []byte("gaaaagaaaaat$")
  tb = []byte("gaa----a--at$")

  fmt.Printf("\n")
  fmt.Printf("inp:\n  a: %s\n  b: %s\n", ta, tb )
  seq_pair_normalize( ta, tb )
  fmt.Printf("out:\n  a: %s\n  b: %s\n", ta, tb )

}

func seqdiff_tests() {

  ta := []byte("a")
  tb := []byte("b")
  var d []SeqDiff
  var e error

  // TEST0
  fmt.Printf("test0\n")
  ta = []byte("gcat")
  tb = []byte("ggat")
  d,e = diff_from_aligned_seqs(ta,tb)
  fmt.Printf("ref: %s\nalt: %s\n", ta, tb)
  if e!=nil { fmt.Printf("error: %v\n", e) }
  for i:=0; i<len(d); i++ {
    fmt.Printf("[%d] ", i)
    debug_print_seqdiff( d[i] )
  }
  for i:=0; i<len(d); i++ { emit_gvcf( &d[i] ) }

  // TEST1
  fmt.Printf("\n")
  fmt.Printf("test1\n")
  ta = []byte("gccat")
  tb = []byte("gggat")
  d,e = diff_from_aligned_seqs(ta,tb)
  fmt.Printf("ref: %s\nalt: %s\n", ta, tb)
  if e!=nil { fmt.Printf("error: %v\n", e) }
  for i:=0; i<len(d); i++ {
    fmt.Printf("[%d] ", i)
    debug_print_seqdiff( d[i] )
  }
  for i:=0; i<len(d); i++ { emit_gvcf( &d[i] ) }

  // TEST2
  fmt.Printf("\n")
  fmt.Printf("test2\n")
  ta = []byte("gcatgcatg")
  tb = []byte("gcat----g")
  d,e = diff_from_aligned_seqs(ta,tb)
  fmt.Printf("ref: %s\nalt: %s\n", ta, tb)
  if e!=nil { fmt.Printf("error: %v\n", e) }
  for i:=0; i<len(d); i++ {
    fmt.Printf("[%d] ", i)
    debug_print_seqdiff( d[i] )
  }
  for i:=0; i<len(d); i++ { emit_gvcf( &d[i] ) }

  // TEST3
  fmt.Printf("\n")
  fmt.Printf("test3\n")
  ta = []byte("gcat----g")
  tb = []byte("gcatgcatg")
  d,e = diff_from_aligned_seqs(ta,tb)
  fmt.Printf("ref: %s\nalt: %s\n", ta, tb)
  if e!=nil { fmt.Printf("error: %v\n", e) }
  for i:=0; i<len(d); i++ {
    fmt.Printf("[%d] ", i)
    debug_print_seqdiff( d[i] )
  }
  for i:=0; i<len(d); i++ { emit_gvcf( &d[i] ) }

  // TEST4
  fmt.Printf("\n")
  fmt.Printf("test4\n")
  ta = []byte("gcta----g")
  tb = []byte("gcatgcatg")
  d,e = diff_from_aligned_seqs(ta,tb)
  fmt.Printf("ref: %s\nalt: %s\n", ta, tb)
  if e!=nil { fmt.Printf("error: %v\n", e) }
  for i:=0; i<len(d); i++ {
    fmt.Printf("[%d] ", i)
    debug_print_seqdiff( d[i] )
  }
  for i:=0; i<len(d); i++ { emit_gvcf( &d[i] ) }

  // TEST5
  fmt.Printf("\n")
  fmt.Printf("test5\n")
  ta = []byte("gcat")
  tb = []byte("gnat")
  d,e = diff_from_aligned_seqs(ta,tb)
  fmt.Printf("ref: %s\nalt: %s\n", ta, tb)
  if e!=nil { fmt.Printf("error: %v\n", e) }
  for i:=0; i<len(d); i++ {
    fmt.Printf("[%d] ", i)
    debug_print_seqdiff( d[i] )
  }
  for i:=0; i<len(d); i++ { emit_gvcf( &d[i] ) }

  // TEST6
  fmt.Printf("\n")
  fmt.Printf("test6\n")
  ta = []byte("gcat")
  tb = []byte("gnnt")
  d,e = diff_from_aligned_seqs(ta,tb)
  fmt.Printf("ref: %s\nalt: %s\n", ta, tb)
  if e!=nil { fmt.Printf("error: %v\n", e) }
  for i:=0; i<len(d); i++ {
    fmt.Printf("[%d] ", i)
    debug_print_seqdiff( d[i] )
  }
  for i:=0; i<len(d); i++ { emit_gvcf( &d[i] ) }

  // TEST7
  fmt.Printf("\n")
  fmt.Printf("test7\n")
  ta = []byte("gcatgcat")
  tb = []byte("gnntgnat")
  d,e = diff_from_aligned_seqs(ta,tb)
  fmt.Printf("ref: %s\nalt: %s\n", ta, tb)
  if e!=nil { fmt.Printf("error: %v\n", e) }
  for i:=0; i<len(d); i++ {
    fmt.Printf("[%d] ", i)
    debug_print_seqdiff( d[i] )
  }
  for i:=0; i<len(d); i++ { emit_gvcf( &d[i] ) }

  // TEST8
  fmt.Printf("\n")
  fmt.Printf("test8\n")
  ta = []byte("gcatgcat")
  tb = []byte("gnn----t")
  d,e = diff_from_aligned_seqs(ta,tb)
  fmt.Printf("ref: %s\nalt: %s\n", ta, tb)
  if e!=nil { fmt.Printf("error: %v\n", e) }
  for i:=0; i<len(d); i++ {
    fmt.Printf("[%d] ", i)
    debug_print_seqdiff( d[i] )
  }
  for i:=0; i<len(d); i++ { emit_gvcf( &d[i] ) }

  // TEST8.5
  fmt.Printf("\n")
  fmt.Printf("test8.5\n")
  ta = []byte("gaaaaagaaaag")
  tb = []byte("gaaa---aa-ag")
  d,e = diff_from_aligned_seqs(ta,tb)
  fmt.Printf("ref: %s\nalt: %s\n", ta, tb)
  if e!=nil { fmt.Printf("error: %v\n", e) }
  for i:=0; i<len(d); i++ {
    fmt.Printf("[%d] ", i)
    debug_print_seqdiff( d[i] )
  }
  for i:=0; i<len(d); i++ { emit_gvcf( &d[i] ) }

  // TEST9
  fmt.Printf("\n")
  fmt.Printf("test9\n")
  ta = []byte("gcatgcat")
  tb = []byte("g----nnt")
  d,e = diff_from_aligned_seqs(ta,tb)
  fmt.Printf("ref: %s\nalt: %s\n", ta, tb)
  if e!=nil { fmt.Printf("error: %v\n", e) }
  for i:=0; i<len(d); i++ {
    fmt.Printf("[%d] ", i)
    debug_print_seqdiff( d[i] )
  }

  for i:=0; i<len(d); i++ { emit_gvcf( &d[i] ) }


}

func is_simple_align( seqa, seqb []byte ) bool {
  n := len(seqa)
  if len(seqb) != n { return false; }
  for i:=0; i<n; i++ {
    a := byte_low(seqa[i])
    b := byte_low(seqb[i])
    if a=='n' || b=='n' { continue; }
    if seqa[i] != seqb[i] { return false; }
  }
  return true
}

func simple_seq_align( seq_ref, seq_alt []byte ) {
  n := len(seq_ref)

  seq_diffs := make( []SeqDiff, 0, 8 )


  curdiff := &SeqDiff{ []int{0,0}, []int{0,0}, 2, []byte(""), []byte(""), NOCALL }
  prev_ref_byte := byte('.') ; _ = prev_ref_byte
  state := NOCALL
  new_state := state

  for i:=0; i<n; i++ {
    _seqdiff_update( curdiff, state, i, i, []byte(""), []byte("") )

    new_state = _transition( seq_ref[i], seq_alt[i] )
    if new_state != state {

      // Skip first position
      //
      if i!=0 {

        // If we've transitioned from a substitution to
        // and indel, don't emit a seqdiff line but
        // change state.
        //
        if state==SUB && new_state==INDEL {
          curdiff.Type = INDEL
        } else {

          // (g)VCF wants the first REF base, so start at
          // one position before.
          //
          s,e:=curdiff.Pos[0]-1,curdiff.Pos[0]+curdiff.Len[0]
          curdiff.Ref = _update_bp_str( curdiff.Ref, seq_ref, s, e )

          s,e = curdiff.Pos[1]-1,curdiff.Pos[1]+curdiff.Len[1]
          curdiff.Alt = _update_bp_str( curdiff.Alt, seq_alt, s, e )

          seq_diffs = append(seq_diffs, *curdiff)
          curdiff = &SeqDiff{ []int{i,i}, []int{0,0}, 2, []byte(""), []byte(""), state }

        }
      }

      state = new_state
    }

  }


  _seqdiff_update( curdiff, state, n, n, []byte(""), []byte("") )

  s,e:=curdiff.Pos[0]-1,curdiff.Pos[0]+curdiff.Len[0]
  curdiff.Ref = _update_bp_str( curdiff.Ref, seq_ref, s, e )

  s,e = curdiff.Pos[1]-1,curdiff.Pos[1]+curdiff.Len[1]
  curdiff.Alt = _update_bp_str( curdiff.Alt, seq_alt, s, e )

  seq_diffs = append(seq_diffs, *curdiff )

  d := seq_diffs
  for i:=0; i<len(d); i++ { emit_gvcf( &d[i] ) }

  return

}

func _main( c *cli.Context ) {

  g_verbose = c.Bool("Verbose")
  g_chrom = c.String("chrom")
  g_normalize_flag = !c.Bool("no-normalize")
  g_align_type = c.String("align-type")

  if (g_align_type != "nw") && (g_align_type != "fa") {
    fmt.Printf("Invalid align-type\n")
    cli.ShowAppHelp(c)
    os.Exit(1)
  }

  if c.Bool("run-tests") {
    seqdiff_tests()
    normalize_tests()
    os.Exit(0)
  }

  if (len(c.String("ref"))==0) || (len(c.String("seq"))==0) {
    cli.ShowAppHelp(c)
    os.Exit(1)
  }

  seqa_scan,err := autoio.OpenReadScannerSimple( c.String("ref") )
  if err != nil { log.Fatal(err) }
  defer seqa_scan.Close()

  seqa := seqa_scan.ReadText()

  seqb_scan,err := autoio.OpenReadScannerSimple( c.String("seq") )
  if err != nil { log.Fatal(err) }
  defer seqb_scan.Close()

  seqb := seqb_scan.ReadText()

  ref_seq := []byte(seqa)
  alt_seq := []byte(seqb)

  if (is_simple_align(ref_seq, alt_seq)) {
    simple_seq_align(ref_seq, alt_seq)
  } else {
    e := seq_align(seqa,seqb)
    if e!=nil { fmt.Println( e ) }
  }

  return

}

func main() {

  app := cli.NewApp()
  app.Name  = "align2vcf"
  app.Usage = "algin two sequences and print out gVCF"
  app.Version = VERSION_STR
  app.Author = "Curoverse, Inc."
  app.Email = "info@curoverse.com"
  app.Action = func( c *cli.Context ) { _main(c) }

  app.Flags = []cli.Flag{
    cli.StringFlag{
      Name: "ref, r",
      Usage: "REFERENCE_SEQUENCE",
    },

    cli.StringFlag{
      Name: "seq, s",
      Usage: "VAR_SEQUENCE",
    },

    cli.StringFlag{
      Name: "chrom, c",
      Value: "Un",
      Usage: "CHROM",
    },

    cli.IntFlag{
      Name: "procs, N",
      Value: -1,
      Usage: "MAXPROCS",
    },

    cli.IntFlag{
      Name: "gap-penalty, g",
      Value: -5,
      Usage: "Affine gap penalty (initial cost of gap creation)",
    },

    cli.StringFlag{
      Name: "align-type, A",
      Value: g_align_type,
      Usage: "Alignment to use.  Can be 'nw' (Needleman-Walsh), 'fa' (Fitted Align).  Defaults to 'nw'.",
    },

    cli.StringFlag{
      Name: "score-matrix, m",
      Usage: "Score matrix as a comma separated integer list (no spaced, row major, 'gap,a,c,t,g')",
    },

    cli.BoolFlag{
      Name: "Verbose, V",
      Usage: "Verbose flag",
    },

    cli.BoolFlag{
      Name: "no-normalize, Z",
      Usage: "Don't normalize gVCF",
    },

    cli.BoolFlag{
      Name: "run-tests, T",
      Usage: "Run tests",
    },

    cli.BoolFlag{
      Name: "pprof",
      Usage: "Profile usage",
    },

    cli.StringFlag{
      Name: "pprof-file",
      Value: gProfileFile,
      Usage: "Profile File",
    },

    cli.BoolFlag{
      Name: "mprof",
      Usage: "Profile memory usage",
    },

    cli.StringFlag{
      Name: "mprof-file",
      Value: gMemProfileFile,
      Usage: "Profile Memory File",
    },

  }

  app.Run( os.Args )

}
