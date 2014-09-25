package cmd

import (
  "bufio"
  "bytes"
  "compress/gzip"
  "fmt"
  "io"
  "os"
  "path"
  "sort"
  "strings"

  "github.com/curoverse/lightning/experimental/tileruler/modules/abv"
  "github.com/curoverse/lightning/experimental/tileruler/modules/base"
  "github.com/curoverse/lightning/experimental/tileruler/modules/cli"
  "github.com/curoverse/lightning/experimental/tileruler/modules/log"
)

var CmdAbv = cli.Command{
  Name:   "abv",
  Usage:  "generate abv files from fastj",
  Action: runAbv,
  Flags: []cli.Flag{
    cli.StringFlag{"human", "", "human name"},
    cli.StringFlag{"fastj-path", "fastj/hu011C57/fj.fill", "path to fastj file(s)"},
    cli.StringFlag{"lib-path", "fastj/tile_md5sum_hu154_sort.csv.gz", "path to fastj file(s)"},
    cli.BoolFlag{"count-gap", "count gaps as no-call"},

    cli.StringFlag{"lz4-path", "lz4", "path to lz4 executable"},
    cli.StringFlag{"gz-path", "gunzip", "path to gunzip executable"},
    cli.StringFlag{"bz2-path", "bunzip2", "path to bunzip2 executable"},

  },
}

type FastjNames []string

func (fn FastjNames) Len() int {
  return len(fn)
}

func (fn FastjNames) Swap(i, j int) {
  fn[i], fn[j] = fn[j], fn[i]
}

func (fn FastjNames) Less(i, j int) bool {
  chr1, chr2 := getChr(fn[i]), getChr(fn[j])
  if chr1 < chr2 {
    return true
  } else if chr1 > chr2 {
    return false
  }
  return getBand(fn[i]) < getBand(fn[j])
}

var (
  libReaders [2]*bufio.Reader
  cacheInfos [2][][]byte
  cacheBands = []int{-1, -1}
  cachePoss  = []int{-1, -1}
)

func loadRefLib(phase, band, pos int) map[string]int {
  rank := 0
  m := make(map[string]int)
  if len(cacheInfos[phase]) > 0 {
    m[string(cacheInfos[phase][2])] = rank
    // fmt.Println(cacheBands[phase], cachePoss[phase], string(cacheInfos[phase][2]), rank)
    cacheInfos[phase] = nil
    rank++
  }

  var errRead error
  var line []byte
  for errRead != io.EOF {
    line, errRead = libReaders[phase].ReadBytes('\n')
    line = bytes.TrimSpace(line)

    infos := bytes.Split(line, []byte(","))
    if len(infos) < 3 {
      continue
    }
    curBand, err := base.HexStr2int(string(infos[1][:3]))
    if err != nil {
      log.Fatal("Fail to get band index(%s): %v", string(line), err)
    }
    curPos, err := base.HexStr2int(string(infos[1][7:11]))
    if err != nil {
      log.Fatal("Fail to get pos index(%s): %v", string(line), err)
    }
    if curBand > band || curPos > pos {
      cacheBands[phase] = curBand
      cachePoss[phase] = curPos
      cacheInfos[phase] = infos
      // fmt.Println("Cache:", cacheBands[phase], cachePoss[phase])
      break
    }

    m[string(infos[2])] = rank
    // fmt.Println(curBand, curPos, string(infos[2]), rank)
    rank++
  }
  return m
}

func getFastJFileNamesFromPath( path string, opt base.Option ) ( []string, error ) {
  names_lz4,err := base.GetFileListBySuffix( opt.FastjPath, ".fj.lz4" )
  if err != nil { return nil, err }

  names_gz,err := base.GetFileListBySuffix( opt.FastjPath, ".fj.gz" )
  if err != nil { return nil, err }

  names_bz2,err := base.GetFileListBySuffix( opt.FastjPath, ".fj.bz2" )
  if err != nil { return nil, err }

  names_fj,err := base.GetFileListBySuffix( opt.FastjPath, ".fj" )
  if err != nil { return nil, err }

  names := []string{}

  names = append( names, names_lz4... )
  names = append( names, names_gz... )
  names = append( names, names_bz2... )
  names = append( names, names_fj... )

  return names, nil

}

func stageFastjFile( inp_name string, opt base.Option ) ( string, bool, error ) {

  if strings.HasSuffix( inp_name, ".lz4" ) {
    lz4 := opt.Lz4
    fjName := strings.TrimSuffix(inp_name, ".lz4")
    os.MkdirAll("/tmp/fastj/", os.ModePerm)
    fjName = "/tmp/fastj/" + path.Base(fjName)

    _, stderr, err := base.ExecCmd(lz4, "-d", inp_name, fjName)
    _ = stderr
    if err != nil { return "", false, err }

    return fjName, true, nil
  }

  if strings.HasSuffix( inp_name, ".gz" ) {
    gunzip := opt.Gz
    fjName := strings.TrimSuffix(inp_name, ".gz")
    os.MkdirAll("/tmp/fastj/", os.ModePerm)
    fjName = "/tmp/fastj/" + path.Base(fjName)
    fjNameGz := "/tmp/fastj/" + path.Base(fjName) + ".gz"

    _, stderr, err := base.ExecCmd( "cp", inp_name, fjNameGz )
    _ = stderr
    if err != nil { return "", false, err }

    _, stderr, err = base.ExecCmd( gunzip, "-d", fjNameGz )
    if err != nil { return "", false, err }

    return fjName, true, nil
  }

  if strings.HasSuffix( inp_name, ".bz2" ) {
    bz2 := opt.Bz2
    fjName := strings.TrimSuffix(inp_name, ".bz2")
    os.MkdirAll("/tmp/fastj/", os.ModePerm)
    fjName = "/tmp/fastj/" + path.Base(fjName)
    fjNameBz2 := "/tmp/fastj/" + path.Base(fjName) + ".bz2"

    _, stderr, err := base.ExecCmd( "cp", inp_name, fjNameBz2 )
    _ = stderr
    if err != nil { return "", false, err }

    _, stderr, err = base.ExecCmd( bz2 , "-d", fjNameBz2 )
    if err != nil { return "", false, err }

    return fjName, true, nil
  }

  return inp_name, false, nil

}

func runAbv(ctx *cli.Context) {
  opt := setup(ctx)

  phases := []string{"A", "B"}
  outputs := [2]*os.File{}

  // Open reference library and file writer.
  for _, phase := range []int{0, 1} {

    lr, err := os.Open(opt.RefLibPath)
    if err != nil {
      log.Fatal("Fail to open file(%s): %v", opt.RefLibPath, err)
    }
    defer lr.Close()

    glr, err := gzip.NewReader(lr)
    if err != nil {
      log.Fatal("Fail to create gzip.Reader(%s): %v", opt.RefLibPath, err)
    }
    defer glr.Close()

    libReaders[phase] = bufio.NewReader(glr)

    abvPath := "abvs/" + opt.Human + "_" + phases[phase] + ".abv"
    os.MkdirAll(path.Dir(abvPath), os.ModePerm)
    outputs[phase], err = os.Create(abvPath)
    if err != nil {
      log.Fatal("Fail to create abv file(%s): %v", abvPath, err)
    }
    outputs[phase].WriteString(opt.Human)
    defer outputs[phase].Close()

  }

  // Load and sort fastj files in order.
  //names, err := base.GetFileListBySuffix(opt.FastjPath, ".fj.lz4")
  names,err := getFastJFileNamesFromPath( opt.FastjPath, opt )

  if err != nil {
    log.Fatal("Fail to get list of fastj files: %v", err)
  }

  sort.Sort(FastjNames(names))

  for i, name_raw := range names {
    fmt.Println(i, name_raw)

    name,cleanup,err := stageFastjFile( name_raw, opt )
    if err != nil { log.Fatal( "%v", err ) }

    fr, err := os.Open(name)
    if err != nil {
      log.Fatal("Fail to open file(%s): %v", name, err)
    }

    buf := bufio.NewReader(fr)
    var errRead error
    var line []byte
    var m map[string]int
    var phase int

    for errRead != io.EOF {
      line, errRead = buf.ReadBytes('\n')
      line = bytes.TrimSpace(line)
      if (errRead != nil) && (errRead != io.EOF) {
        log.Fatal("Fail to read file(%s): %v", name, err)
      }

      if len(line) == 0 || line[0] != '>' { continue }

      phase = 0
      if bytes.HasSuffix(line, []byte("B\"]}")) { phase = 1 }

      band, err := base.HexStr2int(string(line[16:19]))
      if err != nil {
        log.Fatal("Fail to get band index(%s): %v", string(line), err)
      }

      pos, err := base.HexStr2int(string(line[23:27]))
      if err != nil {
        log.Fatal("Fail to get pos index(%s): %v", string(line), err)
      }

      if band != cacheBands[phase] || pos != cachePoss[phase] || len(cacheInfos[phase]) > 0 {
        if pos == 0 {
          outputs[phase].WriteString(" ")
          outputs[phase].Write([]byte(base.Int2HexStr(band)))
          outputs[phase].WriteString(" ")
        }
        m = loadRefLib(phase, band, pos)
      }

      var ch uint8

      if opt.CountGap && bytes.Index(line, []byte("GAP")) > -1 {
        ch = '-'
      } else {
        md5 := string(line[44:76])
        if rank, ok := m[md5]; ok {
          if rank >= len(abv.EncodeStd) { ch = '#'
          } else { ch = abv.EncodeStd[rank] }
        } else { ch = '-' }
      }
      outputs[phase].Write([]byte{ch})
    }
    fr.Close()
    if cleanup { os.Remove(name) }
  }
}
