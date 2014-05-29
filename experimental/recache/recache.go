package recache

import "regexp"
import "io"

//import "fmt"

var Cache map[string]*regexp.Regexp

func Compile( expr string ) (re *regexp.Regexp, err error) {
  if Cache == nil {
    Cache = make( map[string]*regexp.Regexp )
  }
  if Cache[expr] != nil { 
    return Cache[expr] , nil
  }
  Cache[expr],err = regexp.Compile( expr )
  return Cache[expr], err
}

//--

func MatchString( pattern string, s string) (matched bool, err error) {
  r,err := Compile(pattern)
  if err != nil { return false, err }
  return r.MatchString(s), err
}

func Match( pattern string, b []byte) (matched bool, err error) {
  r,err := Compile(pattern)
  if err != nil { return false, err }
  return r.Match(b), err
}

func MatchReader( pattern string, ior io.RuneReader) (matched bool, err error) {
  r,err := Compile(pattern)
  if err != nil { return false, err }
  return r.MatchReader(ior), err
}

//--


func FindAllStringSubmatch( pattern string, s string, n int ) ( res [][]string, err error ) {
  r,err := Compile(pattern)
  if err != nil { return nil, err }
  return r.FindAllStringSubmatch( s, n ), err
}

//--

func ReplaceAllString( pattern string, src string, repl string) ( res string, err error ) {
  r,err := Compile(pattern)
  if err != nil { return "", err }
  return r.ReplaceAllString( src, repl ),err;
}

//--

func Split( pattern string, s string, n int ) ( res []string, err error ) {
  r,err := Compile(pattern)
  if err != nil { return nil, err }
  return r.Split( s, n ),err;
}
