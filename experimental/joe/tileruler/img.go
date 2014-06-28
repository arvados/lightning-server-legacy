package main

import (
	"fmt"
	"image"
	"image/color"
	"image/draw"
	"image/png"
	"log"
	"os"
	"path/filepath"
	"runtime"
	"sync"
	"time"

	"github.com/genomelightning/tileruler/abv"
)

var varColors = []color.Color{
	color.RGBA{0, 153, 0, 255},
	color.RGBA{0, 204, 0, 255},
	color.RGBA{0, 255, 0, 255},
	color.RGBA{0, 255, 255, 255},
	color.RGBA{0, 204, 255, 255},
	color.RGBA{0, 153, 255, 255},
	color.RGBA{0, 102, 255, 255},
	color.RGBA{0, 51, 255, 255},
	color.RGBA{0, 0, 255, 255},
	color.RGBA{0, 0, 102, 255},
}

func initImage2(opt *Option) *image.RGBA {
	m := image.NewRGBA(image.Rect(0, 0, *boxNum**slotPixel+1, *boxNum**slotPixel+1))
	draw.Draw(m, m.Bounds(), image.White, image.ZP, draw.Src)

	// Draw borders.
	for i := m.Bounds().Min.X; i < m.Bounds().Max.X; i++ {
		m.Set(i, m.Bounds().Min.Y, image.Black)
		m.Set(i, m.Bounds().Max.Y-1, image.Black)
	}
	for i := m.Bounds().Min.Y; i < m.Bounds().Max.Y; i++ {
		m.Set(m.Bounds().Min.X, i, image.Black)
		m.Set(m.Bounds().Max.X-1, i, image.Black)
	}

	if opt.HasGrids {
		// Draw grids.
		for i := 1; i < *boxNum; i++ {
			for j := m.Bounds().Min.Y; j < m.Bounds().Max.Y; j++ {
				m.Set(i**slotPixel, j, image.Black)
			}
		}
		for i := 1; i < *boxNum; i++ {
			for j := m.Bounds().Min.X; j < m.Bounds().Max.X; j++ {
				m.Set(j, i**slotPixel, image.Black)
			}
		}
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

// GenerateImgPerTile generates one PNG for each tile.
func GenerateImgPerTile(opt *Option, humans []*abv.Human) {
	wg := &sync.WaitGroup{}
	workChan := make(chan bool, opt.MaxWorkNum)

	os.MkdirAll(opt.ImgDir, os.ModePerm)
	for i := opt.StartBandIdx; i <= opt.EndBandIdx; i++ {
		// fmt.Println(i)
		wg.Add(opt.EndPosIdx - opt.StartPosIdx + 1)
		os.MkdirAll(fmt.Sprintf("%s/%d", opt.ImgDir, i), os.ModePerm)
		for j := opt.StartPosIdx; j <= opt.EndPosIdx; j++ {
			m := initImage2(opt)
			for k := range humans {
				if b, ok := humans[k].Blocks[i][j]; ok {
					drawSingleSquare(opt, m, int(b.Variant), k%*boxNum, k / *boxNum)
				}
			}
			workChan <- true
			go func(band, pos int) {
				if pos%1000 == 0 {
					fmt.Println(band, pos)
				}
				fw, err := os.Create(fmt.Sprintf("%s/%d/%d.png", opt.ImgDir, band, pos))
				// fw, err := os.Create(fmt.Sprintf("%s/%d/%d.png", *imgDir, i, j))
				if err != nil {
					log.Fatalf("Fail to create png file: %v", err)
				} else if err = png.Encode(fw, m); err != nil {
					log.Fatalf("Fail to encode png file: %v", err)
				}
				fw.Close()
				wg.Done()
				<-workChan
			}(i, j)
		}
		runtime.GC()
	}

	fmt.Println("Goroutine #:", runtime.NumGoroutine())
	wg.Wait()
}

func initImage(opt *Option) *image.RGBA {
	boxNum := 1
	switch opt.Mode {
	case ALL_IN_ONE, ALL_IN_ONE_ABV:
		boxNum = opt.BoxNum
	}
	m := image.NewRGBA(image.Rect(0, 0,
		(opt.EndPosIdx+1)*boxNum*opt.SlotPixel, (opt.EndBandIdx+1)*boxNum*opt.SlotPixel))
	draw.Draw(m, m.Bounds(), image.White, image.ZP, draw.Src)
	return m
}

// GenerateAbvImg generates one PNG for each abv file.
func GenerateAbvImg(opt *Option, h *abv.Human) error {
	os.MkdirAll(opt.ImgDir, os.ModePerm)

	m := initImage(opt)
	for i := opt.StartBandIdx; i <= opt.EndBandIdx; i++ {
		for j := opt.StartPosIdx; j <= opt.EndPosIdx; j++ {
			if b, ok := h.Blocks[i][j]; ok {
				drawSingleSquare(opt, m, int(b.Variant), j, i)
			}
		}
	}

	fw, err := os.Create(fmt.Sprintf("%s/%s.png", opt.ImgDir, h.Name))
	if err != nil {
		return fmt.Errorf("Fail to create PNG file(%s): %v", h.Name, err)
	}
	defer fw.Close()

	if err = png.Encode(fw, m); err != nil {
		return fmt.Errorf("Fail to encode PNG file(%s): %v", h.Name, err)
	}
	runtime.GC()
	return nil
}

// GenerateAbvImgs is a high level function to generate PNG for each abv file.
func GenerateAbvImgs(opt *Option, names []string) error {
	for i, name := range names {
		h, err := abv.Parse(name, opt.Range, nil)
		if err != nil {
			return fmt.Errorf("Fail to parse abv file(%s): %v", name, err)
		}
		h.Name = filepath.Base(name)

		opt.EndBandIdx = h.MaxBand
		opt.EndPosIdx = h.MaxPos
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
	// use user input to specify the -max-band=862 and -max-pos=59000
	// would be very nice.

	// NOTE: current implementatio does not support for sorting by colors,
	// which uses multi-reader to load data piece by piece to save memory.

	m := initImage(opt)
	fmt.Println("Time spent(init image):", time.Since(start))

	for idx, name := range names {
		h, err := abv.Parse(name, opt.Range, nil)
		if err != nil {
			return fmt.Errorf("Fail to parse abv file(%s): %v", name, err)
		}
		h.Name = filepath.Base(name)

		for i := 0; i <= h.MaxBand; i++ {
			for j, b := range h.Blocks[i] {
				drawAllInOneSquare(opt, m, int(b.Variant),
					j*(opt.SlotPixel*opt.BoxNum+1)+idx%13, i*(opt.SlotPixel*opt.BoxNum+1)+idx/13)
			}
		}
		fmt.Printf("%d[%s]: %s: %d * %d\n", idx, time.Since(start), h.Name, h.MaxBand, h.MaxPos)
		runtime.GC()
	}

	os.MkdirAll(opt.ImgDir, os.ModePerm)
	fw, err := os.Create(fmt.Sprintf("%s/all-in-one.png", opt.ImgDir))
	if err != nil {
		return fmt.Errorf("Fail to create giant PNG file: %v", err)
	}
	defer fw.Close()

	if err = png.Encode(fw, m); err != nil {
		return fmt.Errorf("Fail to encode giant PNG file: %v", err)
	}

	return nil
}
