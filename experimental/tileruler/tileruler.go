// Tile Ruler is a command line tool for generating PNGs based on given abv files.
package main

import (
	"errors"
	"flag"
	"fmt"
	"io/ioutil"
	"log"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"time"

	"github.com/curoverse/lightning/experimental/tileruler/abv"
	"github.com/curoverse/lightning/experimental/tileruler/utils"
)

const (
	VERSION = "0.1.2.0703"
)

var (
	abvPath      = flag.String("abv-path", "./", "directory or path of abv file(s)")
	imgDir       = flag.String("img-dir", "pngs", "path to store PNG file(s)")
	mode         = flag.Int("mode", 0, "1-single; 2-all in one; 3-all in one abv")
	slotPixel    = flag.Int("slot-pixel", 2, "slot pixel of width and height")
	hasGrids     = flag.Bool("has-grids", false, "indicates whether slot has border")
	border       = flag.Int("border", 2, "pxiel of border")
	startBandIdx = flag.Int("start-band", 0, "start band index")
	startPosIdx  = flag.Int("start-pos", 0, "start position index")
	maxBandIdx   = flag.Int("max-band", 9, "max band index")
	maxPosIdx    = flag.Int("max-pos", 49, "max position index")
	boxNum       = flag.Int("box-num", 15, "box number of width and height")
	workNum      = flag.Int("work-num", 10, "work chan buffer")
	colorSpec    = flag.String("color-spec", "", "path of color specification file")
)

var start = time.Now()

type Mode int

const (
	SINGLE Mode = iota + 1
	ALL_IN_ONE
	ALL_IN_ONE_ABV
)

type Option struct {
	ImgDir    string
	SlotPixel int
	HasGrids  bool
	Border    int
	Mode      Mode
	*abv.Range
	BoxNum     int
	MaxWorkNum int // Max goroutine number.
}

func validateInput() (*Option, error) {
	flag.Parse()

	if utils.IsFile(*colorSpec) {
		spec, err := ioutil.ReadFile(*colorSpec)
		if err != nil {
			return nil, err
		}
		parseVarColors(string(spec))
	} else {
		parseVarColors(defaultVarColors)
	}

	opt := &Option{
		ImgDir:    *imgDir,
		SlotPixel: *slotPixel,
		HasGrids:  *hasGrids,
		Border:    *border,
		Mode:      Mode(*mode),
		Range: &abv.Range{
			StartBandIdx: *startBandIdx,
			EndBandIdx:   *maxBandIdx,
			StartPosIdx:  *startPosIdx,
			EndPosIdx:    *maxPosIdx,
		},
		BoxNum:     *boxNum,
		MaxWorkNum: *workNum,
	}

	if opt.HasGrids {
		if opt.SlotPixel < 2 {
			return nil, errors.New("-slot-pixel cannot be smaller than 2 with grids")
		}
	} else if opt.SlotPixel < 1 {
		return nil, errors.New("-slot-pixel cannot be smaller than 1")
	}

	switch {
	case (opt.Mode == ALL_IN_ONE || opt.Mode == ALL_IN_ONE_ABV) && opt.BoxNum < 13:
		log.Fatalln("-box-num cannot be smaller than 13 in all-in-one mode")
	case opt.MaxWorkNum < 1:
		log.Fatalln("-work-num cannot be smaller than 1")
	case opt.Border < 1:
		log.Fatalln("-border cannot be smaller than 1")
	}
	return opt, nil
}

// getAbvList returns a list of abv file paths.
// It recognize if given path is a file.
func getAbvList(abvPath string) ([]string, error) {
	if !utils.IsExist(abvPath) {
		return nil, errors.New("Given abv path does not exist")
	} else if utils.IsFile(abvPath) {
		return []string{abvPath}, nil
	}

	// Given path is a directory.
	dir, err := os.Open(abvPath)
	if err != nil {
		return nil, err
	}

	fis, err := dir.Readdir(0)
	if err != nil {
		return nil, err
	}

	abvs := make([]string, 0, len(fis))
	for _, fi := range fis {
		if strings.HasSuffix(fi.Name(), ".abv") {
			abvs = append(abvs, filepath.Join(abvPath, fi.Name()))
		}
	}
	return abvs, nil
}

func rangeString(idx int) string {
	if idx < 0 {
		return "MAX"
	}
	return utils.ToStr(idx)
}

func main() {
	fmt.Println("Tile Ruler Version:", VERSION)

	opt, err := validateInput()
	if err != nil {
		log.Fatalln(err)
	}
	fmt.Println("Option:")
	fmt.Printf("Band Range: %d - %s\n", opt.StartBandIdx, rangeString(opt.EndBandIdx))
	fmt.Printf("Pos Range: %d - %s\n", opt.StartPosIdx, rangeString(opt.EndPosIdx))
	fmt.Println("Has Grids:", opt.HasGrids)
	fmt.Println("Box Number:", opt.BoxNum)

	runtime.GOMAXPROCS(runtime.NumCPU())

	// Parse abv file.
	var humans []*abv.Human
	names, err := getAbvList(*abvPath)
	if err != nil {
		log.Fatalf("Fail to get abv list: %v", err)
	} else if len(names) == 0 {
		log.Fatalf("No abv files found: %s", *abvPath)
	}
	// humans = make([]*abv.Human, len(names))

	switch opt.Mode {
	case SINGLE:
		fmt.Println("Mode: Single\n")
		err = GenerateAbvImgs(opt, names)
	case ALL_IN_ONE:
		fmt.Println("Mode: All-in-one\n")
		err = GenerateGiantGenomeImg(opt, names)
	case ALL_IN_ONE_ABV:
		fmt.Println("Mode: All-in-one abv\n")
		err = GenerateTransparentLayers(opt, names)
	default:
		log.Fatalln("Unknown run mode:", opt.Mode)
	}
	if err != nil {
		log.Fatalf("Fail to generate PNG files: %v", err)
	}
	fmt.Println("Time spent(total):", time.Since(start))
	return

	for i, name := range names {
		humans[i], err = abv.Parse(name, opt.Range, nil)
		if err != nil {
			log.Fatalf("Fail to parse abv file(%s): %v", name, err)
		}
		humans[i].Name = filepath.Base(name)
		fmt.Printf("%d: %s: %d * %d\n", i, humans[i].Name, humans[i].MaxBand, humans[i].MaxPos)
	}
	fmt.Println("Time spent(parse blocks):", time.Since(start))
	fmt.Println()

	// Get max band and position index.
	realMaxBandIdx := -1
	realMaxPosIdx := -1
	for _, h := range humans {
		if h.MaxBand > realMaxBandIdx {
			realMaxBandIdx = h.MaxBand
		}
		if h.MaxPos > realMaxPosIdx {
			realMaxPosIdx = h.MaxPos
		}
		// fmt.Println("Pos Count:", h.PosCount)
	}

	if opt.EndBandIdx < 0 || opt.EndBandIdx > realMaxBandIdx {
		opt.EndBandIdx = realMaxBandIdx
	}
	if opt.EndPosIdx < 0 || opt.EndPosIdx > realMaxPosIdx {
		opt.EndPosIdx = realMaxPosIdx
	}
	fmt.Println("Max Band Index:", opt.EndBandIdx, "\nMax Pos Index:", opt.EndPosIdx)
}
