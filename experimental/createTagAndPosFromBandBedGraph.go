package main

import "os"
import "fmt"
import "path/filepath"

var x string = "hello"

var bandBounds map[string]map[int][2]int

func visit(path string, f os.FileInfo, err error) error {

  mode := f.Mode()
  if mode.IsDir() { return nil }

  fmt.Printf("visited %s\n", path)
  return nil
}

func main() {
  user := os.Getenv("USER")
  bedGraphDir := fmt.Sprintf("/scratch/%s/bedGraph", user)

  err := filepath.Walk( bedGraphDir, visit )
  _ = err

  bandBounds = make( map[string]map[int][2]int )

  fmt.Println(x)

}
