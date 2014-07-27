package cmd

import (
	"bytes"
	"encoding/json"
	"image"
	"io/ioutil"
	"os"
	"path"
	"strings"

	"github.com/curoverse/lightning/experimental/tileruler/modules/abv"
	"github.com/curoverse/lightning/experimental/tileruler/modules/base"
	"github.com/curoverse/lightning/experimental/tileruler/modules/cli"
	"github.com/curoverse/lightning/experimental/tileruler/modules/log"
)

var CmdReverse = cli.Command{
	Name:   "reverse",
	Usage:  "reverse image back to abv file(s)",
	Action: runReverse,
	Flags: []cli.Flag{
		cli.IntFlag{"mode, m", 0, "generate mode(1-2), see README.md for detail"},
		cli.StringFlag{"reverse-path", "./", "directory or path of reverse image file(s)"},
	},
}

func runReverse(ctx *cli.Context) {
	opt := setup(ctx)

	if !base.IsFile(opt.ReversePath) {
		log.Fatal("Given image does not exist or not a file: %s", opt.ReversePath)
	}

	// Gather information of given image file.
	profDir := strings.TrimSuffix(opt.ReversePath, ".png")
	if !base.IsDir(profDir) {
		log.Fatal("Given image does not have profile information or not a directory: %s", profDir)
	}

	if err := base.ParseColorSpec(path.Join(profDir, "colormap.txt")); err != nil {
		log.Fatal("Fail to parse color map: %v", err)
	}

	switch opt.Mode {
	case base.SINGLE:
		reverseSingleImg(opt, profDir)
	case base.FULL_SIZE:
		reverseFullSizeImg(opt, profDir)
	default:
		log.Fatal("Unknown mode: %v", opt.Mode)
	}
}

// reverseSingleImg accepts an image and its profile to reverse it to abv raw data file.
func reverseSingleImg(opt base.Option, profDir string) {
	ap := new(AbvProfile)
	data, err := ioutil.ReadFile(path.Join(profDir, "profile.json"))
	if err != nil {
		log.Fatal("Fail to read profile.json(%s): %v", opt.ReversePath, err)
	} else if err = json.Unmarshal(data, ap); err != nil {
		log.Fatal("fail to decode profile.json(%s): %v", opt.ReversePath, err)
	}

	// Decode image file.
	fr, err := os.Open(opt.ReversePath)
	if err != nil {
		log.Fatal("fail to open image(%s): %v", opt.ReversePath, err)
	}
	defer fr.Close()

	m, _, err := image.Decode(fr)
	if err != nil {
		log.Fatal("fail to decode image(%s): %v", opt.ReversePath, err)
	}

	// Declare once to save cost.
	space := byte(' ')
	buf := new(bytes.Buffer)

	// Reverse image.
	log.Info("Start reversing image: %s", path.Base(opt.ReversePath))

	// Prepare file write stream.
	fw, err := os.Create(profDir + ".abv")
	if err != nil {
		log.Fatal("fail to create abv file(%s): %v", opt.ReversePath, err)
	}
	defer fw.Close()
	fw.WriteString("\"" + ap.Name + "\" ")

	// Loop by band, so that we can write to file stream as soon as we have data.
	for y := m.Bounds().Min.Y; y < m.Bounds().Max.Y; y += ap.SlotPixel {
		yIdx := y / ap.SlotPixel
		buf.WriteString(base.Int2HexStr(yIdx))
		buf.WriteByte(space)
		for x := m.Bounds().Min.X; x < m.Bounds().Max.X; x += ap.SlotPixel {
			if yIdx == len(ap.BandLen) {
				log.Fatal("Invalid profile information: band index out of bound")
			}
			if x >= ap.BandLen[yIdx] {
				break
			}
			idx := base.GetVarColorIdx(m.At(x, y))
			switch idx {
			case -2:
				log.Fatal("Color does not recognize at (%d, %d)", x, y)
			case -1:
				buf.WriteByte('-')
			case 0:
				buf.WriteByte('.')
			case 99:
				buf.WriteByte('#')
			default:
				buf.WriteByte(abv.EncodeStd[idx])
			}
		}

		if y == m.Bounds().Max.Y-ap.SlotPixel {
			buf.WriteByte('\n')
		} else {
			buf.WriteByte(space)
		}
		fw.Write(buf.Bytes())
		buf.Reset()
	}
}

// reverseFullSizeImg accepts an fuul size image and its profiles to reverse it to abv raw data files.
func reverseFullSizeImg(opt base.Option, profDir string) {
	fsp := new(FullSizeProfile)
	data, err := ioutil.ReadFile(path.Join(profDir, "profile.json"))
	if err != nil {
		log.Fatal("Fail to read profile.json(%s): %v", opt.ReversePath, err)
	} else if err = json.Unmarshal(data, fsp); err != nil {
		log.Fatal("fail to decode profile.json(%s): %v", opt.ReversePath, err)
	}

	// Decode image file.
	fr, err := os.Open(opt.ReversePath)
	if err != nil {
		log.Fatal("fail to open image(%s): %v", opt.ReversePath, err)
	}
	defer fr.Close()

	m, _, err := image.Decode(fr)
	if err != nil {
		log.Fatal("fail to decode image(%s): %v", opt.ReversePath, err)
	}

	// Declare once to save cost.
	space := byte(' ')
	buf := new(bytes.Buffer)

	// Reverse image.
	log.Info("Start reversing image: %s", path.Base(opt.ReversePath))

	for i, h := range fsp.Humans {
		// Prepare file write stream.
		fw, err := os.Create(h.Name + ".abv")
		if err != nil {
			log.Fatal("fail to create abv file(%s): %v", opt.ReversePath, err)
		}
		fw.WriteString("\"" + h.Name + "\" ")

		// Loop by band, so that we can write to file stream as soon as we have data.
		// NOTE: results are not tested yet.
		// TODO: MaxBand, MaxCol, MaxX
		for y := m.Bounds().Min.Y; y < m.Bounds().Max.Y; y += fsp.SlotPixel {
			yIdx := y / fsp.SlotPixel
			buf.WriteString(base.Int2HexStr(yIdx))
			buf.WriteByte(space)
			for x := m.Bounds().Min.X; x < m.Bounds().Max.X; x += fsp.SlotPixel {
				if yIdx == len(h.BandLen) {
					log.Fatal("Invalid profile information: band index out of bound")
				}
				if x >= h.BandLen[yIdx] {
					break
				}
				idx := base.GetVarColorIdx(m.At(x, y))
				switch idx {
				case -2:
					log.Fatal("Color does not recognize at (%d, %d)", x, y)
				case -1:
					buf.WriteByte('-')
				case 0:
					buf.WriteByte('.')
				default:
					buf.WriteByte(abv.EncodeStd[idx])
				}
			}

			if y == m.Bounds().Max.Y-fsp.SlotPixel {
				buf.WriteByte('\n')
			} else {
				buf.WriteByte(space)
			}
			fw.Write(buf.Bytes())
			buf.Reset()
		}

		fw.Close()
		buf.Reset()
		log.Info("[%d] %s", i, h.Name)
	}
}
