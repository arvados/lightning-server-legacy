package bioenv

import "fmt"
import "os"
import "io"
import "encoding/json"
import "bufio"

import "errors"

import "compress/gzip"
import "compress/bzip2"

import "flag"


type BioEnvContext struct {
  Env map[string]string
}

func init() {
  //fmt.Printf("bioenv init\n")
}

func (benv *BioEnvContext) DebugPrint() {
  for k,v := range benv.Env {
    fmt.Println(k,v)
  }
}

// Use the default config file to populate a variable map for common
// file locations.
//
//func BioEnv() (m map[string]string, err error)  {
func BioEnv() ( benv BioEnvContext, err error ) {


  fn := []string{ "/etc/bioenv", "/etc/bioenv/bioenv", "./.bioenv" }

  if home := os.Getenv( "HOME" ) ; len(home) > 0 {
    fn = append(fn, fmt.Sprintf("%s/%s", home, ".bioenv") )
  }

  for i := len(fn)-1; i>=0; i-- {

    if _,e := os.Stat(fn[i]) ; os.IsNotExist(e) {
      continue
    }

    file,e := os.Open( fn[i] )
    if e != nil { continue }
    decoder := json.NewDecoder(file)

    //m = make( map[string]string )
    benv.Env = make( map[string]string )

    //if err := decoder.Decode(&m) ; err != nil {
    if err = decoder.Decode(&(benv.Env)) ; err != nil {
      return benv, err
    }

    //return m, nil
    return benv, nil

  }

  //m = make( map[string]string )
  benv.Env = make( map[string]string )


  //return m, nil
  return benv, nil

}

// Use specified config file to populate map
//
//func BioEnvConfig( configFilename string ) (m map[string]string, err error)  {
func BioEnvConfig( configFilename string ) (benv BioEnvContext, err error) {

  if _,err := os.Stat( configFilename ) ; os.IsNotExist(err) {
    return benv, err
  }

  file,err := os.Open( configFilename )
  if err != nil { return benv, err }
  decoder := json.NewDecoder(file)

  //m = make( map[string]string )
  benv.Env = make( map[string]string )
  //if err := decoder.Decode(&m) ; err != nil {
  if err := decoder.Decode(&(benv.Env)) ; err != nil {
    return benv, err
  }

  //return m, nil
  return benv, nil

}

// Default flags for bioenv
func (benv *BioEnvContext) ProcessFlag() {

  flag.Visit( func( f *flag.Flag) { if f.Name == "reference" { benv.Env["refernece"] = f.Value.String() } } )
}

// Wrap common stream file types into one for ease of scanning
//
type BioEnvHandle struct {
  Fp *os.File
  Scanner *bufio.Scanner
  Writer *bufio.Writer

  Bz2Reader io.Reader
  GzReader *gzip.Reader
  FileType string
}

// Magic strings we look for at the beginning of the file to determine file type.
//
var magicmap map[string]string = map[string]string{ "\x1f\x8b" : ".gz" , "\x1f\x9d" : ".Z", "\x42\x5a" : ".bz2" , "\x50\x4b\x03\x04" : ".zip" }

func OpenScanner( fn string ) ( h BioEnvHandle, err error ) {

  if fn == "-" {
    h.Fp = os.Stdin
    h.Scanner = bufio.NewScanner( h.Fp )
    return h, nil
  }

  var sentinalfp *os.File

  sentinalfp,err = os.Open( fn )
  if err != nil { return h, err }
  defer sentinalfp.Close()


  b := make( []byte, 2, 2 )
  n,err := sentinalfp.Read(b)
  if (n<2) || (err != nil) {
    h.Fp,err = os.Open( fn )
    if err != nil { return h, err }
    h.Scanner = bufio.NewScanner( h.Fp )
    return h, err
  }

  if typ,ok := magicmap[string(b)] ; ok {

    h.Fp,err = os.Open( fn )
    if err != nil { return h, err }

    if typ == ".gz" {
      h.FileType = "gz"

      h.GzReader,err = gzip.NewReader( h.Fp )
      if err != nil {
        h.Fp.Close()
        return h, err
      }
      h.Scanner = bufio.NewScanner( h.GzReader )
    } else if typ == ".bz2" {

      h.FileType = "bz2"

      h.Bz2Reader = bzip2.NewReader( h.Fp )
      h.Scanner = bufio.NewScanner( h.Bz2Reader )
    } else {
      err = errors.New(typ + "extension not supported")
    }

    return h, err
  }


  b2 := make( []byte, 2, 2)
  n,err = sentinalfp.Read(b2)
  if (n<2) || (err != nil) {
    h.Fp,err = os.Open( fn )
    if err != nil { return h, err }
    h.Scanner = bufio.NewScanner( h.Fp )
    return h, err
  }

  s := string(b) + string(b2)
  if typ,ok := magicmap[s]; ok {
    if typ == ".zip" {
      err = errors.New("zip extension not supported")
      return h, err
    }
    err = errors.New(typ + "extension not supported")
    return h, err
  }

  h.Fp,err = os.Open( fn )
  if err != nil { return h, err }
  h.Scanner = bufio.NewScanner( h.Fp )

  return h, err

}

func CreateWriter( fn string ) ( h BioEnvHandle, err error ) {

  if fn == "-" {
    h.Fp = os.Stdout
  } else {
    h.Fp,err = os.Create( fn )
    if err != nil { return h, err }
  }

  h.Writer = bufio.NewWriter( h.Fp )
  return h, nil
}

func (h *BioEnvHandle) Flush() {

  if h.Writer != nil {
    h.Writer.Flush()
  }

}

func ( h *BioEnvHandle) Close() {

  if h.FileType == "gz" {
    h.GzReader.Close()
  }
  h.Fp.Close()
}
