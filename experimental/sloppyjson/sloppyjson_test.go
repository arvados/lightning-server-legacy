package sloppyjson

import "testing"

var json_tests []string = []string{
  "{}",
  "\n\n\n{}",
  "\n\n\n{\n\n}",
  "\n\n\n{ }",
  "\n\n\n{}\n",
  "\n\n\n{}      ",
  "[]",
  "  []",
  "[]  ",
  "[ ]",
  "\n\n[ ]\n\n   ",
  "[ \"str\", \"ing\" ] ",
  "\n[ \"str\", \"in\", \"g\" ] ",
  "[ \"str\" ] ",
  "   { \"str\" : \"ing\", \"gni\" : \"rts\" } ",
  " { \n\n \"str\" : \"ing\" }" }

func TestLoads( t *testing.T ) {

  for k:=0 ; k<len(json_tests); k++ {
    dat := json_tests[k]
    if _,e := Loads( string(dat) ) ; e!=nil { t.Errorf( "%v", e ) }
  }

}
