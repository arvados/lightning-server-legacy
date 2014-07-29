package cmd

import (
	"bufio"
	"bytes"
	"fmt"
	"io"
	"os"
	"path"
	"strings"

	// "github.com/Unknwon/com"

	"github.com/curoverse/lightning/experimental/tileruler/modules/abv"
	"github.com/curoverse/lightning/experimental/tileruler/modules/base"
	"github.com/curoverse/lightning/experimental/tileruler/modules/cli"
	"github.com/curoverse/lightning/experimental/tileruler/modules/log"
)

var CmdStat = cli.Command{
	Name:   "stat",
	Usage:  "do statistics on abv files",
	Action: runStat,
	Flags: []cli.Flag{
		cli.IntFlag{"mode, m", 0, "generate mode(1-6), see README.md for detail"},
		cli.StringFlag{"abv-path", "./", "directory or path of abv file(s)"},
		cli.IntFlag{"max-band", 99, "max band index(inclusive) to do statistic"},
		cli.IntFlag{"size", 5, "window size of tiles"},
	},
}

func runStat(ctx *cli.Context) {
	opt := setup(ctx)

	switch opt.Mode {
	case 1:
		log.Info("Mode: Non-default variant sum")
	case 2:
		log.Info("Mode: Default variant sum")
	case 3:
		log.Info("Mode: Fastj statistic")
		if err := fastjStat(ctx); err != nil {
			log.Fatal("%v", err)
		}
		return
	case 4:
		log.Info("Mode: Fastj chromosome statistic")
		if err := fastjChrStat(ctx); err != nil {
			log.Fatal("%v", err)
		}
		return
	case 5:
		log.Info("Mode: Fastj chromosome statistic")
		if err := fastjChrBandStat(ctx); err != nil {
			log.Fatal("%v", err)
		}
		return
	case 6:
		log.Info("Mode: Fastj2 chromosome statistic")
		if err := fastj2ChrBandStat(ctx); err != nil {
			log.Fatal("%v", err)
		}
		return
	default:
		log.Fatal("Unknown mode: %v", opt.Mode)
	}

	names, err := base.GetFileListBySuffix(opt.AbvPath, ".abv")
	if err != nil {
		log.Fatal("Fail to get abv list: %v", err)
	}

	stats := make([]*abv.Statistic, len(names))
	maxWindows := 0

	os.MkdirAll("stat", os.ModePerm)
	fw, _ := os.Create("stat/stat.chart")
	defer fw.Close()
	fw.WriteString("===\n{ \"Name\" : \"line\", \"Height\" : 500, \"Width\" : 10000 }\n---\n")

	log.Info("[Idx] Name: non-default - unrecognize")
	for i, name := range names {
		stat, err := abv.Stat(name, opt)
		if err != nil {
			log.Fatal("Fail to parse abv file(%s): %v", name, err)
		}

		if maxWindows < len(stat.Windows[0]) {
			maxWindows = len(stat.Windows[0])
		}
		stats[i] = stat

		log.Info("[%d] %s: %d - %d", i, path.Base(name), stat.Variant, stat.Unrecognize)
	}

	for i := 1; i <= maxWindows; i++ {
		fw.WriteString(stats[0].Windows[0][i-1].Desc + " ")
		s := 0
		for k := 0; k < len(stats[0].Windows); k++ {
			for j := range stats {
				if i <= len(stats[j].Windows[k]) {
					s += int(stats[j].Windows[k][i-1].VariantSum)
				}
			}
		}
		fw.WriteString(base.ToStr(s) + " ")
		fw.WriteString("\n")
	}
}

func fastjStat(ctx *cli.Context) error {
	names, err := base.GetFileListBySuffix("fastj/hu661AD0.fj", ".fj")
	if err != nil {
		return err
	}

	maxPos := 0
	bands := make(map[int]int)

	for i, name := range names {
		fmt.Println(i, name)
		fr, err := os.Open(name)
		if err != nil {
			return err
		}

		buf := bufio.NewReader(fr)
		var errRead error
		var line []byte
		for errRead != io.EOF {
			line, errRead = buf.ReadBytes('\n')
			line = bytes.TrimSpace(line)
			if errRead != nil {
				if errRead != io.EOF {
					return errRead
				}
			}
			if len(line) == 0 || line[0] != '>' {
				continue
			}
			posIdx, _ := base.HexStr2int(string(line[19:22]))
			if maxPos < posIdx/5 {
				maxPos = posIdx / 5
			}
			if len(line)-bytes.Index(line, []byte("notes")) <= 20 {
				bands[posIdx/5]++
			}
		}
		fr.Close()
	}

	os.MkdirAll("stat", os.ModePerm)
	fw, _ := os.Create("stat/fastj.chart")
	defer fw.Close()
	fw.WriteString("===\n{ \"Name\" : \"line\", \"Height\" : 500, \"Width\" : 10000 }\n---\n")

	for i := 0; i <= maxPos; i++ {
		fw.WriteString(base.ToStr(i) + " " + base.ToStr(bands[i]) + "\n")
	}
	return nil
}

func getChr(name string) int {
	name = path.Base(name)
	chr := name[3:strings.Index(name, "_")]
	switch chr {
	case "X":
		return 23
	case "Y":
		return 24
	default:
		num, _ := base.StrTo(chr).Int()
		return num
	}
}

func fastjChrStat(ctx *cli.Context) error {
	names, err := base.GetFileListBySuffix("fastj/hu661AD0.fj", ".fj")
	if err != nil {
		return err
	}

	minPos := make(map[int]int)
	maxPos := make(map[int]int)
	bands := make(map[int]map[int]int)
	maxChr := 0

	for i, name := range names {
		fmt.Println(i, name)

		chr := getChr(name)
		if _, ok := bands[chr]; !ok {
			bands[chr] = make(map[int]int)
			if chr > maxChr {
				maxChr = chr
			}
		}

		fr, err := os.Open(name)
		if err != nil {
			return err
		}

		buf := bufio.NewReader(fr)
		var errRead error
		var line []byte
		for errRead != io.EOF {
			line, errRead = buf.ReadBytes('\n')
			line = bytes.TrimSpace(line)
			if errRead != nil {
				if errRead != io.EOF {
					return errRead
				}
			}
			if len(line) == 0 || line[0] != '>' {
				continue
			}
			posIdx, _ := base.HexStr2int(string(line[19:22]))
			posIdx /= 5
			if minPos[chr] > posIdx {
				minPos[chr] = posIdx
			}
			if maxPos[chr] < posIdx {
				maxPos[chr] = posIdx
			}
			if len(line)-bytes.Index(line, []byte("notes")) <= 20 {
				bands[chr][posIdx]++
			}
		}
		fr.Close()
	}

	os.MkdirAll("stat", os.ModePerm)

	for chr := 0; chr <= maxChr; chr++ {
		fw, _ := os.Create("stat/chr" + base.ToStr(chr) + ".chart")
		fw.WriteString("===\n{ \"Name\" : \"line\", \"Height\" : 500, \"Width\" : 10000 }\n---\n")
		for i := 0; i <= maxPos[chr]-minPos[chr]; i++ {
			fw.WriteString(base.ToStr(i) + " " + base.ToStr(bands[chr][i+minPos[chr]]) + "\n")
		}
		fw.Close()
	}
	return nil
}

func getBand(name string) int {
	name = path.Base(name)
	band, _ := base.StrTo(name[9 : 9+strings.Index(name[9:], "_")]).Int()
	return band
}

func fastjChrBandStat(ctx *cli.Context) error {
	names, err := base.GetFileListBySuffix("fastj/hu661AD0.fj", ".fj")
	if err != nil {
		return err
	}

	maxPos := make(map[int]int)
	bands := make(map[int]map[int]int)
	maxBand := 0

	for i, name := range names {
		fmt.Println(i, name)
		chr := getChr(name)
		if chr != 1 {
			continue
		}

		band := getBand(name)
		if _, ok := bands[band]; !ok {
			bands[band] = make(map[int]int)
			if band > maxBand {
				maxBand = band
			}
		}

		fr, err := os.Open(name)
		if err != nil {
			return err
		}

		buf := bufio.NewReader(fr)
		var errRead error
		var line []byte
		for errRead != io.EOF {
			line, errRead = buf.ReadBytes('\n')
			line = bytes.TrimSpace(line)
			if errRead != nil {
				if errRead != io.EOF {
					return errRead
				}
			}
			if len(line) == 0 || line[0] != '>' {
				continue
			}
			posIdx, _ := base.HexStr2int(string(line[19:22]))
			posIdx /= 5
			if maxPos[band] < posIdx {
				maxPos[band] = posIdx
			}
			if len(line)-bytes.Index(line, []byte("notes")) <= 20 {
				bands[band][posIdx]++
			}
		}
		fr.Close()
	}

	os.MkdirAll("stat", os.ModePerm)

	for band := 0; band <= maxBand; band++ {
		fw, _ := os.Create("stat/band" + base.ToStr(band) + ".chart")
		fw.WriteString("===\n{ \"Name\" : \"line\", \"Height\" : 500, \"Width\" : 10000 }\n---\n")
		for i := 0; i <= maxPos[band]; i++ {
			fw.WriteString(base.ToStr(i) + " " + base.ToStr(bands[band][i]) + "\n")
		}
		fw.Close()
	}
	return nil
}

func fastj2ChrBandStat(ctx *cli.Context) error {
	names, err := base.GetFileListBySuffix("fastj/hu2FEC01/chr3.fj.fill", ".fj") //.lz4")
	if err != nil {
		return err
	}

	maxPos := make(map[int]int)
	bands := make(map[int]map[int]int)
	shows := make(map[int]map[int]bool)
	maxBand := 0

	for i, name := range names {
		fmt.Println(i, name)
		// _, stderr, err := com.ExecCmd("lz4", "-d", name, strings.TrimSuffix(name, ".lz4"))
		// if err != nil {
		// 	return fmt.Errorf(stderr)
		// }
		// continue
		chr := getChr(name)
		if chr != 3 {
			continue
		}

		band := getBand(name)
		if _, ok := bands[band]; !ok {
			bands[band] = make(map[int]int)
			shows[band] = make(map[int]bool)
			if band > maxBand {
				maxBand = band
			}
		}

		fr, err := os.Open(name)
		if err != nil {
			return err
		}

		buf := bufio.NewReader(fr)
		var errRead error
		var line []byte
		for errRead != io.EOF {
			line, errRead = buf.ReadBytes('\n')
			line = bytes.TrimSpace(line)
			if errRead != nil {
				if errRead != io.EOF {
					return errRead
				}
			}
			if len(line) == 0 || line[0] != '>' {
				continue
			}
			posIdx, _ := base.HexStr2int(string(line[23:27]))
			posIdx /= 10
			if maxPos[band] < posIdx {
				maxPos[band] = posIdx
			}
			if shows[band][posIdx] {
				// continue
			}
			noteIdx := bytes.Index(line, []byte("notes"))
			if len(line)-noteIdx <= 20 {
				bands[band][posIdx]++
			} else if bytes.Index(line[noteIdx:], []byte("SNP")) == -1 &&
				bytes.Index(line[noteIdx:], []byte("INDEL")) == -1 &&
				bytes.Index(line[noteIdx:], []byte("SUB")) == -1 {
				bands[band][posIdx]++
			}
			shows[band][posIdx] = true
		}
		fr.Close()
	}

	os.MkdirAll("stat", os.ModePerm)

	for band := 0; band <= maxBand; band++ {
		fw, _ := os.Create("stat/lz4_band" + base.ToStr(band) + ".chart")
		fw.WriteString("===\n{ \"Name\" : \"line\", \"Height\" : 500, \"Width\" : 10000 }\n---\n")
		for i := 0; i <= maxPos[band]; i++ {
			fw.WriteString(base.ToStr(i) + " " + base.ToStr(bands[band][i]) + "\n")
		}
		fw.Close()
	}
	return nil
}
