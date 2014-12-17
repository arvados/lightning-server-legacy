package main

import "fmt"
import "strings"
import "strconv"

// Parses an 'int option' of the form:
//
//         (\d+([\+\-]\d+)?)(,(\d+([\+\-]\d+)?))*
//
// into an array of ranges.
//
// The (\d) in the above regexp matches an int
// in the specified base (up to whatever
// strconv.ParseInt accepts)
//
// Here are some examples:
//
// '0'          -> [[0,-1]]
// '0+1'        -> [[0,1]]
// '0-f'        -> [[0,15]]
// 'a-b,3-5'    -> [[10,11],[3,5]]
// 'f,4+2,a-c'  -> [[15,-1],[4,6],[10,13]]
//

func parseIntOption( istr string, base int ) ([][2]int64, error) {
  r := make( [][2]int64, 0, 8 )
  commaval := strings.Split( istr, "," )
  for i:=0; i<len(commaval); i++ {

    if strings.Contains( commaval[i], "-" ) {

      dashval := strings.Split( commaval[i], "-" )
      if len(dashval) > 2 { return nil, fmt.Errorf("invalid option %s", commaval[i]) }

      a,ee := strconv.ParseInt( dashval[0], base, 64 )
      if ee!=nil { return nil, fmt.Errorf("invalid option %s: %v", dashval[0], ee ) }

      if len(dashval[1])==0 {
        r = append( r, [2]int64{a,-1} )
        continue
      }

      b,ee := strconv.ParseInt( dashval[1], base, 64)
      if ee!=nil { return nil, fmt.Errorf("invalid option %s: %v", dashval[1], ee ) }
      r = append( r, [2]int64{a,b} )

    } else if strings.Contains( commaval[i], "+" ) {

      plusval := strings.Split( commaval[i], "+" )
      if len(plusval) > 2 { return nil, fmt.Errorf("invalid option %s", commaval[i]) }

      a,ee := strconv.ParseInt( plusval[0], base, 64 )
      if ee!=nil { return nil, fmt.Errorf("invalid option %s: %v", plusval[0], ee ) }

      if len(plusval[1])==0 {
        r = append( r, [2]int64{a,-1} )
        continue
      }

      b,ee := strconv.ParseInt( plusval[1], base, 64)
      if ee!=nil { return nil, fmt.Errorf("invalid option %s: %v", plusval[1], ee ) }
      if b<0 { return nil, fmt.Errorf("invalid option %s: %d < 0", plusval[1], b ) }
      r = append( r, [2]int64{a,a+b} )


    } else {
      a,ee := strconv.ParseInt( commaval[i], base, 64 )
      if ee!=nil { return nil, fmt.Errorf("invalid option %s: %v", commaval[i], ee ) }

      r = append( r, [2]int64{a,a+1} )
    }

  }

  return r,nil
}

