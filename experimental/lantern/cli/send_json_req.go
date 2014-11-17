package main

import "fmt"
import "net/http"
import "io/ioutil"
import "bytes"
import "os"

func check(e error) {
  if e != nil {
    panic(e)
  }
}

func main() {
  url := "http://localhost:8080"
  fmt.Println("url:", url)

  fmt.Printf("--> %s\n", os.Args[1] )

  dat, err := ioutil.ReadFile( os.Args[1] )
  check(err)
  fmt.Printf("sending:\n%s\n\n", dat )

  req, err := http.NewRequest("POST", url, bytes.NewBuffer(dat))
  req.Header.Set("Content-Type", "application/json")

  client := &http.Client{}
  resp, err := client.Do(req)
  if err != nil {
      panic(err)
  }
  defer resp.Body.Close()

  fmt.Println("response Status:", resp.Status)
  fmt.Println("response Headers:", resp.Header)
  body, _ := ioutil.ReadAll(resp.Body)
  fmt.Println("response Body:", string(body))
}
