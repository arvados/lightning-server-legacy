package main

import (
	"fmt"
	"image"
	"image/color"
	"image/draw"
	"image/png"
	"io/ioutil"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"time"

	"github.com/curoverse/lightning/experimental/tileruler/abv"
	"github.com/curoverse/lightning/experimental/tileruler/utils"
)

var Gray = image.NewUniform(color.RGBA{230, 230, 230, 255})

const defaultVarColors = `255, 255, 255
0, 204, 0
0, 255, 0
0, 255, 255
0, 204, 255
0, 153, 255
0, 102, 255
0, 51, 255
0, 0, 255`

var varColors = make([]color.Color, 0, 10)

func parseVarColors(str string) error {
	lines := strings.Split(str, "\n")
	for i, line := range lines {
		infos := strings.Split(line, ",")
		if len(infos) < 3 {
			return fmt.Errorf("Not enough color assigned in line[%d]: %s", i, line)
		}
		varColors = append(varColors, color.RGBA{
			utils.StrTo(strings.TrimSpace(infos[0])).MustUint8(),
			utils.StrTo(strings.TrimSpace(infos[1])).MustUint8(),
			utils.StrTo(strings.TrimSpace(infos[2])).MustUint8(), 255})
	}
	return nil
}

func calInitImgX(opt *Option, boxNum, border int) int {
	return (opt.EndPosIdx%(opt.MaxColIdx+1)+1)*boxNum*opt.SlotPixel + border*opt.EndPosIdx%(opt.MaxColIdx+1)
}

func calInitImgY(opt *Option, totalRows, boxNum, border int) int {
	return totalRows*boxNum*opt.SlotPixel + border*(totalRows-1)
}

func initImage(opt *Option, totalRows int) *image.RGBA {
	boxNum := 1
	border := 0
	switch opt.Mode {
	case ALL_IN_ONE, ALL_IN_ONE_ABV:
		boxNum = opt.BoxNum
		border = opt.Border
	}
	m := image.NewRGBA(image.Rect(0, 0,
		calInitImgX(opt, boxNum, border), calInitImgY(opt, totalRows, boxNum, border)))

	// Transparent layer doesn't need base color.
	if opt.Mode != ALL_IN_ONE_ABV {
		draw.Draw(m, m.Bounds(), Gray, image.ZP, draw.Src)
	}
	return m
}

func drawSingleSquare(opt *Option, m *image.RGBA, idx, x, y int) {
	// In case variant number is too large.
	if idx >= len(varColors) {
		idx = len(varColors) - 1
	}

	for i := 0; i < opt.SlotPixel; i++ {
		for j := 0; j < opt.SlotPixel; j++ {
			m.Set(x*opt.SlotPixel+i, y*opt.SlotPixel+j, varColors[idx])
		}
	}
}

// saveImgFile saves image to given path in PNG format.
func saveImgFile(name string, m *image.RGBA) error {
	os.MkdirAll(filepath.Dir(name), os.ModePerm)
	fw, err := os.Create(name)
	if err != nil {
		return fmt.Errorf("fail to create PNG file: %v", err)
	}
	defer fw.Close()

	if err = png.Encode(fw, m); err != nil {
		return fmt.Errorf("fail to encode PNG file: %v", err)
	}
	runtime.GC()
	return nil
}

// GenerateAbvImg generates one PNG for each abv file.
func GenerateAbvImg(opt *Option, h *abv.Human) error {
	m := initImage(opt, opt.EndBandIdx+1)
	for i := 0; i <= opt.EndBandIdx; i++ {
		for j := 0; j <= opt.EndPosIdx; j++ {
			if b, ok := h.Blocks[i][j]; ok {
				drawSingleSquare(opt, m, int(b.Variant), j, i)
			}
		}
	}

	if err := saveImgFile(fmt.Sprintf("%s/%s.png", opt.ImgDir, h.Name), m); err != nil {
		return fmt.Errorf("%s: %v", h.Name, err)
	}
	return nil
}

// GenerateAbvImgs is a high level function to generate PNG for each abv file.
func GenerateAbvImgs(opt *Option, names []string) error {
	for i, name := range names {
		if utils.IsExist(fmt.Sprintf("%s/%s.png", opt.ImgDir, filepath.Base(name))) {
			// continue
		}

		h, err := abv.Parse(name, false, opt.Range, nil)
		if err != nil {
			return fmt.Errorf("Fail to parse abv file(%s): %v", name, err)
		}
		h.Name = filepath.Base(name)

		// Adjust range.
		if opt.EndBandIdx == -1 || opt.EndBandIdx > h.MaxBand {
			opt.EndBandIdx = h.MaxBand
		}
		if opt.EndPosIdx == -1 {
			opt.EndPosIdx = 3999
		} else if opt.EndPosIdx > h.MaxPos {
			opt.EndPosIdx = h.MaxPos
		}
		if err = GenerateAbvImg(opt, h); err != nil {
			return err
		}
		fmt.Printf("%d[%s]: %s: %d * %d\n", i, time.Since(start), h.Name, h.MaxBand, h.MaxPos)
	}
	return nil
}

func drawAllInOneSquare(opt *Option, m *image.RGBA, idx, x, y int) {
	// In case variant number is too large.
	if idx >= len(varColors) {
		idx = len(varColors) - 1
	}

	for i := 0; i < opt.SlotPixel; i++ {
		for j := 0; j < opt.SlotPixel; j++ {
			m.Set(x+i, y+j, varColors[idx])
		}
	}
}

// GenerateGiantGenomeImg generates a single PNG file that contains all abv files' info.
func GenerateGiantGenomeImg(opt *Option, names []string) error {
	// NOTE: in order to generate whole PNG for shorter porcessing time,
	// use user input to specify the -max-band=862 and -max-pos=58999
	// would be very nice.
	if opt.EndBandIdx == -1 {
		opt.EndBandIdx = 862
	}
	if opt.EndPosIdx == -1 {
		opt.EndPosIdx = 3999
	}

	// NOTE: current implementatio does not support for sorting by colors,
	// which uses multi-reader to load data piece by piece to save memory.

	// NOTE: Go has huge memory usage for image process, consider generate small ones
	// and combine by github.com/gographics/imagick
	// or http://superuser.com/questions/290656/combine-multiple-images-using-imagemagick

	// TODO: generate output file which describes how many rows in every band.

	// First pass, determine how many rows are going to draw.
	maxRows := make(map[int]int)
	for _, name := range names {
		h, err := abv.Parse(name, true, opt.Range, nil)
		if err != nil {
			return fmt.Errorf("Fail to parse abv file(%s): %v", name, err)
		}
		h.Name = filepath.Base(name)

		for i := 0; i <= opt.EndBandIdx; i++ {
			row := (h.BandLength[i]-1)/(opt.MaxColIdx+1) + 1
			if row > maxRows[i] {
				maxRows[i] = row
			} else if maxRows[i] == 0 {
				maxRows[i] = 1
			}
		}
	}

	totalRows := 0
	bandRows := make([]string, opt.EndBandIdx+1)
	for i := 0; i <= opt.EndBandIdx; i++ {
		totalRows += maxRows[i]
		bandRows[i] = utils.ToStr(totalRows)
	}

	ioutil.WriteFile(fmt.Sprintf("%s/all-in-one-%d(%d)*%d(%d).txt",
		opt.ImgDir, opt.EndBandIdx+1, totalRows,
		opt.EndPosIdx+1, opt.EndPosIdx%(opt.MaxColIdx+1)+1),
		[]byte(strings.Join(bandRows, ",")), os.ModePerm)

	fmt.Printf("[%s] Total rows: %d\n", time.Since(start), totalRows)
	if opt.CountOnly {
		return nil
	}

	m := initImage(opt, totalRows)
	fmt.Println("Time spent(init image):", time.Since(start))

	// Second pass, actually draw slots.
	for idx, name := range names {
		h, err := abv.Parse(name, false, opt.Range, nil)
		if err != nil {
			return fmt.Errorf("Fail to parse abv file(%s): %v", name, err)
		}
		h.Name = filepath.Base(name)

		offsetRow := 0
		for i := 0; i <= opt.EndBandIdx; i++ {
			if _, ok := h.Blocks[i]; ok {
				for j, b := range h.Blocks[i] {
					rowIdx := j/(opt.MaxColIdx+1) + offsetRow
					colIdx := j % (opt.MaxColIdx + 1)
					drawAllInOneSquare(opt, m, int(b.Variant),
						colIdx*(opt.SlotPixel*opt.BoxNum)+2*colIdx+(idx%opt.BoxNum)*opt.SlotPixel,
						rowIdx*(opt.SlotPixel*opt.BoxNum)+2*rowIdx+(idx/opt.BoxNum)*opt.SlotPixel)
				}
			}

			offsetRow += maxRows[i]
		}
		fmt.Printf("%d[%s]: %s: %d * %d\n", idx, time.Since(start), h.Name, h.MaxBand, h.MaxPos)
		runtime.GC()
	}

	if err := saveImgFile(fmt.Sprintf("%s/all-in-one-%d(%d)*%d(%d).png",
		opt.ImgDir, opt.EndBandIdx+1, totalRows,
		opt.EndPosIdx+1, opt.EndPosIdx%(opt.MaxColIdx+1)+1), m); err != nil {
		return fmt.Errorf("giant PNG file: %v", err)
	}
	return nil
}

func drawTransparentLayerSquare(opt *Option, m *image.RGBA, idx, x, y int) {
	// In case variant number is too large.
	if idx >= len(varColors) {
		idx = len(varColors) - 1
	}

	for i := 0; i < 2*opt.SlotPixel; i++ {
		for j := 0; j < 2*opt.SlotPixel; j++ {
			m.Set(x+i, y+j, varColors[idx])
		}
	}
}

// GenerateTransparentLayer generates transparent layer for each abv file.
func GenerateTransparentLayer(opt *Option, h *abv.Human) error {
	m := initImage(opt, opt.EndBandIdx+1)
	for i, _ := range h.Blocks {
		for j, b := range h.Blocks[i] {
			drawTransparentLayerSquare(opt, m, int(b.Variant),
				j*(opt.SlotPixel*opt.BoxNum)+2*j+(opt.BoxNum-2)*opt.SlotPixel,
				i*(opt.SlotPixel*opt.BoxNum)+2*i+(opt.BoxNum-2)*opt.SlotPixel)
		}
	}

	if err := saveImgFile(fmt.Sprintf("%s/tl-%s.png", opt.ImgDir, h.Name), m); err != nil {
		return fmt.Errorf("%s: %v", h.Name, err)
	}
	return nil
}

// GenerateTransparentLayers is a high level function
// to generate transparent layer for each abv file.
func GenerateTransparentLayers(opt *Option, names []string) error {
	// NOTE: in order to generate whole PNG for shorter porcessing time,
	// use user input to specify the -max-band=862 and -max-pos=58999
	// would be very nice.
	if opt.EndBandIdx == -1 {
		opt.EndBandIdx = 862
	}
	if opt.EndPosIdx == -1 {
		opt.EndPosIdx = 3999
	}

	for i, name := range names {
		h, err := abv.Parse(name, false, opt.Range, nil)
		if err != nil {
			return fmt.Errorf("Fail to parse abv file(%s): %v", name, err)
		}
		h.Name = filepath.Base(name)

		if err = GenerateTransparentLayer(opt, h); err != nil {
			return err
		}
		fmt.Printf("%d[%s]: %s\n", i, time.Since(start), h.Name)
	}
	return nil
}
