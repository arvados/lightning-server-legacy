package sloppyj

import "fmt"
import "strconv"

type SloppyJSON struct {
  S string
  L []*SloppyJSON
  O map[string]*SloppyJSON
  P float64
  Y string
}

func ws( indent int ) {
  for i:=0; i<indent; i++ {
    fmt.Printf(" ")
  }
}

func (sjson *SloppyJSON) Printr( indent,dw int ) {
  if sjson.Y == "true" { fmt.Printf("true") ; return }
  if sjson.Y == "false" { fmt.Printf("false") ; return }
  if sjson.Y == "null" { fmt.Printf("null") ; return }

  if sjson.Y == "S" { fmt.Printf("\"%s\"", sjson.S) ; return }
  if sjson.Y == "P" { fmt.Printf("%f", sjson.P) ; return }

  if sjson.Y == "O" {

    fmt.Printf("{\n")

    count:=0
    for k := range sjson.O {
      if count>0 { fmt.Printf(",\n") }
      ws(indent + dw)
      fmt.Printf("\"%s\":", k)
      sjson.O[k].Printr(indent+dw, dw)
      count++
    }
    fmt.Printf("\n")

    ws(indent) ; fmt.Printf("}")

    return
  }

  if sjson.Y == "L" {

    ws(indent) ; fmt.Printf("[\n") ; ws(indent+dw)

    count:=0

    for i:=0; i<len(sjson.L); i++ {
      if count>0 {
        fmt.Printf(",\n")
        ws(indent+dw)
      }
      sjson.L[i].Printr( indent+dw, dw )
      count++
    }
    fmt.Printf("\n")

    ws(indent) ; fmt.Printf("]")

    return
  }

}

func ( sjson *SloppyJSON ) Dump() { sjson.Printr( 0, 2 ) }

func skipspace( dat []byte, k int, n int ) int {

  for ; k<n; k++ {
    for ; (k<n) && (dat[k] == ' ') ; k++ { }
    for ; (k<n) && (dat[k] == '\n') ; k++ { }
    if (k<n) &&
       (dat[k] != ' ') &&
       (dat[k] != '\t') &&
       (dat[k] != '\n') &&
       (dat[k] != '\v') &&
       (dat[k] != '\f') &&
       (dat[k] != '\r') {
      return k
    }
  }
  return -k
}

func parsefloat( dat []byte, k, n int ) (*SloppyJSON, int) {

  v := &(SloppyJSON{})
  v.Y = "P"

  pcount := 0
  b:=k

  if dat[k] == '-' {
    k = skipspace(dat,k+1,n)
    if k<0 { return nil, k }
  }


  for ; k<n; k++ {
    if dat[k] =='.' {
      pcount++
      if pcount > 1 { return nil, -k }
    } else if (dat[k]<48) || (dat[k]>57) { break }
  }

  if k==n { return nil,-k }

  var e error

  v.P,e = strconv.ParseFloat( string( dat[b:k] ), 64 )
  if e!=nil { return nil,-k }

  return v, k

}

func parsefalse( dat []byte, k,n int ) (*SloppyJSON, int) {

  v := &(SloppyJSON{})
  v.Y = "false"

  if dat[k] != 'f' { return nil,-k }
  k++ ; if k==n { return nil,-k }

  if dat[k] != 'a' { return nil,-k }
  k++ ; if k==n { return nil,-k }

  if dat[k] != 'l' { return nil,-k }
  k++ ; if k==n { return nil,-k }

  if dat[k] != 's' { return nil,-k }
  k++ ; if k==n { return nil,-k }

  if dat[k] != 'e' { return nil,-k }
  k++ ; if k==n { return nil,-k }

  return v,k
}

func parsetrue( dat []byte, k,n int ) (*SloppyJSON, int) {
  v := &(SloppyJSON{})
  v.Y = "true"

  if dat[k] != 't' { return nil,-k }
  k++ ; if k==n { return nil,-k }

  if dat[k] != 'r' { return nil,-k }
  k++ ; if k==n { return nil,-k }

  if dat[k] != 'u' { return nil,-k }
  k++ ; if k==n { return nil,-k }

  if dat[k] != 'e' { return nil,-k }
  k++ ; if k==n { return nil,-k }

  return v,k
}

func parsenull( dat []byte, k,n int ) (*SloppyJSON, int) {
  v := &(SloppyJSON{})
  v.Y = "null"

  if dat[k] != 'n' { return nil,-k }
  k++ ; if k==n { return nil,-k }

  if dat[k] != 'u' { return nil,-k }
  k++ ; if k==n { return nil,-k }

  if dat[k] != 'l' { return nil,-k }
  k++ ; if k==n { return nil,-k }

  if dat[k] != 'l' { return nil,-k }
  k++ ; if k==n { return nil,-k }

  return v,k
}

func parsesimplestring( dat []byte, k,n int ) (string, int) {
  b := k
  escape := false
  for ; k<n; k++ {
    if escape { escape = false ; continue }
    if dat[k] == '\\' { escape = true ; continue }
    //for ; (k<n) && (dat[k]!='"') && (dat[k]!='\\'); k++ { }
    //if (k<n) && (dat[k] == '"') { break }
    if dat[k] == '"' { break }
  }

  if k==n { return "",-k }

  return string(dat[b:k]),k+1

}

func parsestring( dat []byte, k,n int ) (*SloppyJSON, int) {
  v:=&(SloppyJSON{})
  v.Y = "S"

  b := k
  escape := false
  for ; k<n; k++ {
    if escape { escape = false ; continue }
    if dat[k] == '\\' {
      escape = true
      continue
    }
    if dat[k] == '"' { break }
  }

  if k==n { return nil,-k }

  v.S = string(dat[b:k])

  return v,k+1

}

func parselist( dat []byte, k int, n int ) ( *SloppyJSON, int) {

  li := &(SloppyJSON{})
  li.Y = "L"
  li.L = make( []*SloppyJSON, 0, 8 )

  k = skipspace(dat,k,n)
  if k<0 { return nil, k }
  if dat[k] == ']' { return li, k+1 }

  var v *SloppyJSON

  if dat[k] == '"' { v,k = parsestring(dat,k+1,n)
  } else if ((dat[k]>='0') && (dat[k]<='9')) ||
             (dat[k]=='.') ||
             (dat[k]=='-') {
    v,k = parsefloat(dat,k,n)
  } else if dat[k] == 't' { v,k = parsetrue(dat,k,n)
  } else if dat[k] == 'f' { v,k = parsefalse(dat,k,n)
  } else if dat[k] == 'n' { v,k = parsenull(dat,k,n)
  } else if dat[k] == '{' { v,k = parseobject(dat,k+1,n)
  } else if dat[k] == '[' { v,k = parselist(dat,k+1,n)
  }

  if k<0 { return nil, k }
  li.L = append(li.L, v)

  for k = skipspace(dat,k,n) ; k<n; k = skipspace(dat,k,n) {
    if k<0 { return nil,k }

    if dat[k] == ']' { break }
    if dat[k] != ',' { return nil, -k }
    k = skipspace(dat,k+1,n)
    if k<0 { return nil, k }

    if dat[k] == '"' { v,k = parsestring(dat,k+1,n)
    } else if ((dat[k]>='0') && (dat[k]<='9')) ||
               (dat[k]=='.') ||
               (dat[k]=='-') {
      v,k = parsefloat(dat,k,n)
    } else if dat[k] == 't' { v,k = parsetrue(dat,k,n)
    } else if dat[k] == 'f' { v,k = parsefalse(dat,k,n)
    } else if dat[k] == 'n' { v,k = parsenull(dat,k,n)
    } else if dat[k] == '{' { v,k = parseobject(dat,k+1,n)
    } else if dat[k] == '[' { v,k = parselist(dat,k+1,n)
    } else { return nil, -k }

    if k<0 { return nil, k }
    li.L = append(li.L, v)

  }
  if k==n { return nil, -k }


  return li,k+1
}

func parseobject( dat []byte, k int, n int ) (*SloppyJSON, int) {
  var v *SloppyJSON
  var str string

  obj := &(SloppyJSON{})
  obj.Y = "O"
  obj.O = make( map[string]*SloppyJSON )

  k = skipspace(dat,k,n)
  if k<0 { return nil, k }

  if dat[k] != '"' { return nil, -k }

  str,k = parsesimplestring(dat,k+1,n)
  if k<0 { return nil, k }

  k = skipspace(dat,k,n)
  if k<0 { return nil, k }

  if dat[k] != ':' { return nil, -k }
  k = skipspace(dat,k+1,n)
  if k<0 { return nil, k }

  if dat[k] == '"' { v,k = parsestring(dat,k+1,n)
  //} else if ((dat[k] >= '0') && (dat[k] <= '9')) || (dat[k] == '.') {
  } else if ((dat[k]>='0') && (dat[k]<='9')) ||
             (dat[k]=='.') ||
             (dat[k]=='-') {
    v,k = parsefloat(dat,k,n)
  } else if dat[k] == 't' { v,k = parsetrue(dat,k,n)
  } else if dat[k] == 'f' { v,k = parsefalse(dat,k,n)
  } else if dat[k] == 'n' { v,k = parsenull(dat,k,n)
  } else if dat[k] == '{' { v,k = parseobject(dat,k+1,n)
  } else if dat[k] == '[' { v,k = parselist(dat,k+1,n)
  } else { return nil,-k }

  if k<0 { return nil,k }
  obj.O[str] = v

  for k = skipspace(dat,k,n) ; k<n; k = skipspace(dat,k,n) {
    if k<0 { return nil,k }

    if dat[k] == '}' { return obj,k+1 }
    if dat[k] != ',' { return nil,-k }
    k = skipspace(dat,k+1,n)
    if k<0 { return nil,k }

    if dat[k] != '"' { return nil,-k }

    str,k = parsesimplestring(dat,k+1,n)
    if k<0 { return nil,k }

    k = skipspace(dat,k,n)
    if k<0 { return nil,k }

    if dat[k] != ':' { return nil,-k }
    k = skipspace(dat,k+1,n)
    if k<0 { return nil,k }

    if dat[k] == '"' { v,k = parsestring(dat,k+1,n)
    //} else if ((dat[k] >= '0') && (dat[k] <= '9')) || (dat[k] == '.') {
    } else if ((dat[k]>='0') && (dat[k]<='9')) ||
               (dat[k]=='.') ||
               (dat[k]=='-') {
      v,k = parsefloat(dat,k,n)
    } else if dat[k] == 't' { v,k = parsetrue(dat,k,n)
    } else if dat[k] == 'f' { v,k = parsefalse(dat,k,n)
    } else if dat[k] == 'n' { v,k = parsenull(dat,k,n)
    } else if dat[k] == '{' { v,k = parseobject(dat,k+1,n)
    } else if dat[k] == '[' { v,k = parselist(dat,k+1,n)
    } else { return nil,-k }
    if k<0 { return nil,k }

    obj.O[str] = v
  }
  if k==n { return nil,-k }

  return obj,k

}

//func parse( dat []byte ) (*SloppyJSON,int) {
func Load( dat []byte ) (*SloppyJSON,error) {
  var v *SloppyJSON
  k,n := 0,len(dat)

  k=skipspace(dat,k,n)
  if k<0 { return nil,fmt.Errorf("Parse error at initial skipspace (character %d)", k) }

  if dat[k] == '['        { v,k = parselist( dat, k+1, n )
  } else if dat[k] == '{' { v,k = parseobject( dat, k+1 , n )
  } else { return nil,fmt.Errorf("Parse error at character %d (1)", -k) }

  if k<0 { return nil,fmt.Errorf("Parse error at character %d (2)", k) }
  if k==n { return v,nil }

  for ; k<n; k++ {
    if (dat[k] != ' ') &&
       (dat[k] != '\t') &&
       (dat[k] != '\n') &&
       (dat[k] != '\r') {
      return nil,fmt.Errorf("Parse error for trailing whitespace at character %d", -k)
    }
  }
  return v,nil

}


/*
import "os"
import "io/ioutil"

func main() {
  dat,e := ioutil.ReadFile( os.Args[1] )
  if e != nil { panic(e) }

  n:=len(dat)

  obj,k := parse( dat )
  _=obj

  if k<0 {
    k = -k
    s := k - 10
    if s<0 { s=0 }
    e := k+10
    if e>n { e=n }

    for z:=s; z<e; z++ {
      if z==k { fmt.Printf("(*%c)", dat[z])
    } else { fmt.Printf("%c", dat[z]) }
    }

    fmt.Printf("\n")

  }
}
*/
