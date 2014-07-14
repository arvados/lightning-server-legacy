// Tile Ruler is a command line tool for generating PNGs based on given abv files.
package main

import (
	"errors"
	"flag"
	"fmt"
	"io/ioutil"
	"log"
	"runtime"
	"time"

	"github.com/curoverse/lightning/experimental/tileruler/abv"
	"github.com/curoverse/lightning/experimental/tileruler/utils"
)

const (
	VERSION = "0.1.4.0714"
)

var (
	abvPath     = flag.String("abv-path", "./", "directory or path of abv file(s)")
	imgDir      = flag.String("img-dir", "pngs", "path to store PNG file(s)")
	mode        = flag.Int("mode", 0, "run mode(1-4), see README.md for detail")
	slotPixel   = flag.Int("slot-pixel", 2, "slot pixel of width and height")
	border      = flag.Int("border", 2, "pxiel of border")
	maxBandIdx  = flag.Int("max-band", 9, "max band index")
	maxPosIdx   = flag.Int("max-pos", 49, "max position index")
	maxColIdx   = flag.Int("max-col", 3999, "max column index")
	boxNum      = flag.Int("box-num", 15, "box number of width and height")
	workNum     = flag.Int("work-num", 10, "work chan buffer")
	colorSpec   = flag.String("color-spec", "", "path of color specification file")
	countOnly   = flag.Bool("count-only", false, "for mode 2 and count only mode")
	force       = flag.Bool("force", false, "force regenerate existed PNG")
	reversePath = flag.String("reverse-path", "./", "directory or path of reverse PNG file(s)")
)

var start = time.Now()

type Mode int

const (
	SINGLE Mode = iota + 1
	ALL_IN_ONE
	ALL_IN_ONE_ABV
	REVERSE
)

type Option struct {
	ImgDir    string
	SlotPixel int
	Border    int
	Mode      Mode
	*abv.Range
	MaxColIdx  int
	BoxNum     int
	MaxWorkNum int // Max goroutine number.
	CountOnly  bool
	Force      bool
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
		Border:    *border,
		Mode:      Mode(*mode),
		Range: &abv.Range{
			EndBandIdx: *maxBandIdx,
			EndPosIdx:  *maxPosIdx,
		},
		MaxColIdx:  *maxColIdx,
		BoxNum:     *boxNum,
		MaxWorkNum: *workNum,
		CountOnly:  *countOnly,
		Force:      *force,
	}

	if opt.SlotPixel < 1 {
		return nil, errors.New("-slot-pixel cannot be smaller than 1")
	}

	switch {
	case (opt.Mode == ALL_IN_ONE || opt.Mode == ALL_IN_ONE_ABV) && opt.BoxNum < 13:
		log.Fatalln("-box-num cannot be smaller than 13 in all-in-one mode")
	case opt.MaxColIdx < 1:
		log.Fatalln("-max-col cannot be smaller than 1")
	case opt.MaxWorkNum < 1:
		log.Fatalln("-work-num cannot be smaller than 1")
	case opt.Border < 1:
		log.Fatalln("-border cannot be smaller than 1")
	}
	return opt, nil
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
	fmt.Printf("Band Range: 0 - %s\n", rangeString(opt.EndBandIdx))
	fmt.Printf("Pos Range: 0 - %s\n", rangeString(opt.EndPosIdx))
	fmt.Println("Box Number:", opt.BoxNum)

	runtime.GOMAXPROCS(runtime.NumCPU())

	var names []string
	if opt.Mode != REVERSE {
		// Get list of abv file(s).
		names, err = utils.GetFileListBySuffix(*abvPath, ".abv")
		if err != nil {
			log.Fatalf("Fail to get abv list: %v", err)
		} else if len(names) == 0 {
			log.Fatalf("No abv files found: %s", *abvPath)
		}
	}

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
	case REVERSE:
		fmt.Println("Mode: Reverse\n")
		err = ReverseImgsToAbvs(*reversePath)
	default:
		log.Fatalln("Unknown run mode:", opt.Mode)
	}
	if err != nil {
		log.Fatalf("Fail to run tile ruler: %v", err)
	}
	fmt.Println("Time spent(total):", time.Since(start))
}
