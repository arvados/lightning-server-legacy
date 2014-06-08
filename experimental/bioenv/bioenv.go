package bioenv

import "fmt"
import "os"
import "encoding/json"

func BioEnv() (m map[string]string, err error)  {

  fn := []string{ "/etc/bioenv", "/etc/bioenv/bioenv", "./.bioenv" }

  if home := os.Getenv( "HOME" ) ; len(home) > 0 {
    fn = append(fn, fmt.Sprintf("%s/%s", home, ".bioenv") )
  }

  for i := len(fn)-1; i>=0; i-- {

    if _,err := os.Stat(fn[i]) ; os.IsNotExist(err) {
      continue
    }

    file,_ := os.Open( fn[i] )
    decoder := json.NewDecoder(file)

    m = make( map[string]string )
    if err := decoder.Decode(&m) ; err != nil {
      return nil, err
    }

    return m, nil

  }

  m = make( map[string]string )

  return m, nil

}
