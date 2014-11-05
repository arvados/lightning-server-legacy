SloppyJSON
==========

A no-frills JSON parser for Go.

JSON is parsed and loaded into a SloppyJSON structure:


    // S - (S)tring
    // L - (L)ist
    // O - (O)bject
    // P - (P)recision value (float)
    // Y - t(Y)pe : (S|L|O|P|true|false|null)
    //
    type SloppyJSON struct {
      S string
      L []*SloppyJSON
      O map[string]*SloppyJSON
      P float64
      Y string
    }


The `Y` variable holds the type ("S" for string, "L" for array, "O" for object, "P" for float64 or
one of "true", "false" or "null" for boolean or null types).

The appropriate element in the SloppyJSON structure will be populated depending on the value
indicated by the `Y` type.

SloppyJSON is mildly faster than using `encoding/json` (around ~30%).

Usage
=====

    package main

    import "fmt"
    import "github.com/curoverse/lightning/experimental/sloppyjson"

    func main() {
      sj,err := sloppyjson.Loads(`{ "obj" : { "test" : "a test object value" },
                                  "str" : "a string!",
                                  "arr" : [ "a", "b" ],
                                  "flo" : 0.12,
                                  "f" : false,
                                  "t": true,
                                  "n": null }`)
      if err!=nil { panic(err) }

      fmt.Printf(" obj.test : %s\n", sj.O["obj"].O["test"].S )
      fmt.Printf(" str : %s\n", sj.O["str"].S )
      fmt.Printf(" arr[0] : %s, arr[1] : %s\n", sj.O["arr"].L[0].S, sj.O["arr"].L[1].S )
      fmt.Printf(" flo : %f\n", sj.O["flo"].P )
      fmt.Printf(" t : %s\n", sj.O["t"].Y )
      fmt.Printf(" f : %s\n", sj.O["f"].Y )
      fmt.Printf(" n : %s\n", sj.O["n"].Y )

      // Produces:
      //
      // obj.test : a test object value
      // str : a string!
      // arr[0] : a, arr[1] : b
      // flo : 0.120000
      // t : true
      // f : false
      // n : null
      //

    }

