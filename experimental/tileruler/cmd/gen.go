package cmd

import (
	"encoding/json"
	"fmt"
	"image"
	"image/draw"
	"image/png"
	"io/ioutil"
	"os"
	"path"
	"runtime"
	"strings"

	"github.com/curoverse/lightning/experimental/tileruler/modules/abv"
	"github.com/curoverse/lightning/experimental/tileruler/modules/base"
	"github.com/curoverse/lightning/experimental/tileruler/modules/cli"
	"github.com/curoverse/lightning/experimental/tileruler/modules/log"
)

var CmdGen = cli.Command{
	Name:   "gen",
	Usage:  "generate images from abv file(s)",
	Action: runGen,
	Flags: []cli.Flag{
		cli.IntFlag{"mode, m", 0, "generate mode(1-3), see README.md for detail"},
		cli.StringFlag{"img-dir", "tr_imgs", "path to store images file(s)"},
		cli.StringFlag{"abv-path", "./", "directory or path of abv file(s)"},
		cli.StringFlag{"color-spec", "", "path of color specification file"},
		cli.IntFlag{"max-band", 9, "max band index(inclusive)"},
		cli.IntFlag{"max-pos", 49, "max position index(inclusive)"},
		cli.IntFlag{"max-col", 3999, "max column index(inclusive)"},
		cli.IntFlag{"box-num", 15, "box number of width and height"},
		cli.IntFlag{"slot-pixel", 2, "slot pixel of width and height"},
		cli.IntFlag{"border", 2, "border pixel between rectangles"},
		cli.BoolFlag{"force, f", "force to regenerate existed images"},
		cli.BoolFlag{"count-only, c", "for mode 2 and count only mode"},
	},
}

func runGen(ctx *cli.Context) {
	opt := setup(ctx)

	names, err := base.GetFileListBySuffix(opt.AbvPath, ".abv")
	if err != nil {
		log.Fatal("Fail to get abv list: %v", err)
	}

	switch opt.Mode {
	case 1:
		log.Info("Mode: Single image for each abv file")
		generateSingleAbvImgs(opt, names)
	case 2:
		log.Info("Mode: Full-size image for all abv files")
		generateFullSizeImg(opt, names)
	case 3:
		log.Info("Mode: Full-size transparent image for each abv file")
		generateTransparentLayers(opt, names)
	default:
		log.Fatal("Unknown mode: %v", opt.Mode)
	}
}

func calInitImgX(opt base.Option, boxNum, border int) int {
	cols := opt.EndPosIdx % (opt.MaxColIdx + 1)
	return (cols+1)*boxNum*opt.SlotPixel + border*cols
}

func calInitImgY(opt base.Option, totalRows, boxNum, border int) int {
	return totalRows*boxNum*opt.SlotPixel + border*(totalRows-1)
}

func initImage(opt base.Option, totalRows int) *image.RGBA {
	boxNum := 1
	border := 0
	switch opt.Mode {
	case base.FULL_SIZE, base.TRANSPARENT:
		boxNum = opt.BoxNum
		border = opt.Border
	}
	m := image.NewRGBA(image.Rect(0, 0,
		calInitImgX(opt, boxNum, border), calInitImgY(opt, totalRows, boxNum, border)))

	// Transparent layer doesn't need base color.
	if opt.Mode != base.TRANSPARENT {
		draw.Draw(m, m.Bounds(), base.Gray, image.ZP, draw.Src)
	}
	return m
}

// saveImgFile saves image to given path in PNG format.
func saveImgFile(name string, m *image.RGBA) error {
	os.MkdirAll(path.Dir(name), os.ModePerm)
	fw, err := os.Create(name)
	if err != nil {
		return fmt.Errorf("fail to create image file: %v", err)
	}
	defer fw.Close()

	if err = png.Encode(fw, m); err != nil {
		return fmt.Errorf("fail to encode image file: %v", err)
	}
	runtime.GC()
	return nil
}

//   _________.___ _______    ________.____     ___________
//  /   _____/|   |\      \  /  _____/|    |    \_   _____/
//  \_____  \ |   |/   |   \/   \  ___|    |     |    __)_
//  /        \|   /    |    \    \_\  \    |___  |        \
// /_______  /|___\____|__  /\______  /_______ \/_______  /
//         \/             \/        \/        \/        \/

// AbvProfile represents a single abv image profile.
type AbvProfile struct {
	Type      base.Mode `json:"type"`
	Name      string    `json:"name"`
	SlotPixel int       `json:"slot_pixel"`
	BandLen   []int     `json:"band_len"`
}

// getAbvImgName returns corresponding image name
// based on current option and human abv file name.
func getAbvImgName(opt base.Option, name string) string {
	return fmt.Sprintf("SI_%s_%d_%d.png", strings.TrimSuffix(name, ".abv"),
		opt.EndBandIdx+1, opt.EndPosIdx+1)
}

func drawSingleSquare(opt base.Option, m *image.RGBA, idx, x, y int) {
	// In case variant number is too large.
	if idx >= len(base.VarColors) {
		idx = len(base.VarColors) - 1
	}

	for i := 0; i < opt.SlotPixel; i++ {
		for j := 0; j < opt.SlotPixel; j++ {
			m.Set(x*opt.SlotPixel+i, y*opt.SlotPixel+j, base.VarColors[idx])
		}
	}
}

// generateAbvImg generates one PNG for each abv file.
func generateAbvImg(opt base.Option, h *abv.Human) error {
	m := initImage(opt, opt.EndBandIdx+1)
	for i := 0; i <= opt.EndBandIdx; i++ {
		for j := 0; j <= opt.EndPosIdx; j++ {
			if b, ok := h.Blocks[i][j]; ok {
				drawSingleSquare(opt, m, int(b.Variant), j, i)
			}
		}
	}

	if err := saveImgFile(path.Join(opt.ImgDir,
		getAbvImgName(opt, path.Base(h.Name))), m); err != nil {
		return fmt.Errorf("%s: %v", h.Name, err)
	}
	return nil
}

// saveAbvImgProfile generates and saves corresponding image profile
// of given information for converting back from image to abv file.
func saveAbvImgProfile(opt base.Option, h *abv.Human) error {
	rawName := strings.TrimSuffix(h.Name, ".abv")
	// Create profile information file directory.
	dirName := path.Join(opt.ImgDir,
		strings.TrimSuffix(getAbvImgName(opt, rawName), ".png"))
	os.MkdirAll(dirName, os.ModePerm)

	// Save profile.json.
	ap := &AbvProfile{
		Type:      base.SINGLE,
		Name:      rawName,
		SlotPixel: opt.SlotPixel,
	}

	ap.BandLen = make([]int, h.MaxBand+1)
	for i := 0; i < len(ap.BandLen); i++ {
		ap.BandLen[i] = h.BandLength[i]
	}

	data, err := json.MarshalIndent(ap, "", "\t")
	if err != nil {
		return err
	} else if err = ioutil.WriteFile(
		path.Join(dirName, "profile.json"), data, 0644); err != nil {
		return err
	}

	// Save or copy color map.
	if len(opt.ColorSpec) == 0 {
		err = ioutil.WriteFile(path.Join(dirName, "colormap.txt"),
			[]byte(base.DefaultVarColors), 0644)
	} else {
		err = base.Copy(opt.ColorSpec, path.Join(dirName, "colormap.txt"))
	}
	return err
}

// generateSingleAbvImgs is a high level function to generate image for each abv file.
func generateSingleAbvImgs(opt base.Option, names []string) {
	for i, name := range names {
		h, err := abv.Parse(name, false, opt.Range, nil)
		if err != nil {
			log.Fatal("Fail to parse abv file(%s): %v", name, err)
		}
		h.Name = path.Base(name)

		// Adjust range.
		if opt.EndBandIdx == -1 || opt.EndBandIdx > h.MaxBand {
			opt.EndBandIdx = h.MaxBand
		}
		if opt.EndPosIdx == -1 {
			opt.EndPosIdx = 3999
		} else if opt.EndPosIdx > h.MaxPos {
			opt.EndPosIdx = h.MaxPos
		}

		// Skip if existed.
		if !opt.Force && base.IsExist(path.Join(
			opt.ImgDir, getAbvImgName(opt, path.Base(name)))) {
			continue
		}

		if err = generateAbvImg(opt, h); err != nil {
			log.Fatal("Fail to generate abv image(%s): %v", name, err)
		} else if err = saveAbvImgProfile(opt, h); err != nil {
			log.Fatal("Fail to save abv image(%s): %v", name, err)
		}

		log.Info("[%d] %s: %d * %d", i, h.Name, h.MaxBand, h.MaxPos)
	}
}

// _______________ ___.____    .____        _________.________________________
// \_   _____/    |   \    |   |    |      /   _____/|   \____    /\_   _____/
//  |    __) |    |   /    |   |    |      \_____  \ |   | /     /  |    __)_
//  |     \  |    |  /|    |___|    |___   /        \|   |/     /_  |        \
//  \___  /  |______/ |_______ \_______ \ /_______  /|___/_______ \/_______  /
//      \/                    \/       \/         \/             \/        \/

type humanProfile struct {
	Name    string `json:"name"`
	BandLen []int  `json:"band_len"`
}

// FullSizeProfile represents full size abv image profile.
type FullSizeProfile struct {
	Type      base.Mode      `json:"type"`
	SlotPixel int            `json:"slot_pixel"`
	BoxNum    int            `json:"box_num"`
	Border    int            `json:"border"`
	Humans    []humanProfile `json:"humans"`
}

func drawFullSizeSquare(opt base.Option, m *image.RGBA, idx, x, y int) {
	// In case variant number is too large.
	if idx >= len(base.VarColors) {
		idx = len(base.VarColors) - 1
	}

	for i := 0; i < opt.SlotPixel; i++ {
		for j := 0; j < opt.SlotPixel; j++ {
			m.Set(x+i, y+j, base.VarColors[idx])
		}
	}
}

// generateFullSizeImg generates a single image file that contains all abv files' info.
func generateFullSizeImg(opt base.Option, names []string) {
	// NOTE: in order to generate whole PNG for shorter porcessing time,
	// 	use user input to specify the -max-band=862 and -max-pos=58999
	// 	would be very nice.
	if opt.EndBandIdx == -1 {
		opt.EndBandIdx = 862
	}
	if opt.EndPosIdx == -1 {
		opt.EndPosIdx = 3999
	}

	// NOTE: current implementatio does not support for sorting by colors,
	// which uses multi-reader to load data piece by piece to save memory.

	// NOTE: Go has huge memory usage for image process, consider generate images
	// directly from raw data.

	// First pass, determine how many rows are going to draw.
	maxRows := make(map[int]int)
	for _, name := range names {
		h, err := abv.Parse(name, true, opt.Range, nil)
		if err != nil {
			log.Fatal("Fail to parse abv file(%s): %v", name, err)
		}
		h.Name = path.Base(name)

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
		bandRows[i] = base.ToStr(maxRows[i])
	}

	dirName := fmt.Sprintf("%s/FS_%d(%d)_%d(%d)",
		opt.ImgDir, opt.EndBandIdx+1, totalRows,
		opt.EndPosIdx+1, opt.EndPosIdx%(opt.MaxColIdx+1)+1)
	os.MkdirAll(dirName, os.ModePerm)

	if err := ioutil.WriteFile(path.Join(dirName, "offsets.txt"),
		[]byte(strings.Join(bandRows, ",")), os.ModePerm); err != nil {
		log.Fatal("Fail to save offsets.txt: %v", err)
	}

	log.Info("Total rows: %d", totalRows)
	if opt.CountOnly {
		return
	}

	m := initImage(opt, totalRows)
	log.Info("Image initialized")

	fsp := &FullSizeProfile{
		Type:      opt.Mode,
		SlotPixel: opt.SlotPixel,
		BoxNum:    opt.BoxNum,
		Border:    opt.Border,
		Humans:    make([]humanProfile, len(names)),
	}

	// Second pass, actually draw slots.
	for idx, name := range names {
		h, err := abv.Parse(name, false, opt.Range, nil)
		if err != nil {
			log.Fatal("Fail to parse abv file(%s): %v", name, err)
		}
		h.Name = path.Base(name)

		offsetRow := 0
		for i := 0; i <= opt.EndBandIdx; i++ {
			if _, ok := h.Blocks[i]; ok {
				for j, b := range h.Blocks[i] {
					rowIdx := j/(opt.MaxColIdx+1) + offsetRow
					colIdx := j % (opt.MaxColIdx + 1)
					drawFullSizeSquare(opt, m, int(b.Variant),
						colIdx*(opt.SlotPixel*opt.BoxNum)+opt.Border*colIdx+(idx%opt.BoxNum)*opt.SlotPixel,
						rowIdx*(opt.SlotPixel*opt.BoxNum)+opt.Border*rowIdx+(idx/opt.BoxNum)*opt.SlotPixel)
				}
			}

			offsetRow += maxRows[i]
		}

		fsp.Humans[idx].Name = strings.TrimSuffix(h.Name, ".abv")
		fsp.Humans[idx].BandLen = make([]int, h.MaxBand+1)
		for i := 0; i < len(fsp.Humans[idx].BandLen); i++ {
			fsp.Humans[idx].BandLen[i] = h.BandLength[i]
		}

		log.Info("[%d] %s: %d * %d", idx, h.Name, h.MaxBand, h.MaxPos)
		runtime.GC()
	}

	if err := saveImgFile(dirName+".png", m); err != nil {
		log.Fatal("Fail to save image: %v", err)
	}

	// Save profile.json.
	data, err := json.MarshalIndent(fsp, "", "\t")
	if err != nil {
		log.Fatal("Fail to encode json: %v", err)
	} else if err = ioutil.WriteFile(
		path.Join(dirName, "profile.json"), data, 0644); err != nil {
		log.Fatal("Fail to save profile.json: %v", err)
	}

	// Save or copy color map.
	if len(opt.ColorSpec) == 0 {
		err = ioutil.WriteFile(path.Join(dirName, "colormap.txt"),
			[]byte(base.DefaultVarColors), 0644)
	} else {
		err = base.Copy(opt.ColorSpec, path.Join(dirName, "colormap.txt"))
	}
	if err != nil {
		log.Fatal("Fail to save color map: %v", err)
	}
}

// _____________________    _____    _______    ___________________  _____
// \__    ___/\______   \  /  _  \   \      \  /   _____/\______   \/  _  \
//   |    |    |       _/ /  /_\  \  /   |   \ \_____  \  |     ___/  /_\  \
//   |    |    |    |   \/    |    \/    |    \/        \ |    |  /    |    \
//   |____|    |____|_  /\____|__  /\____|__  /_______  / |____|  \____|__  /
//                    \/         \/         \/        \/                  \/
// _____________________ __________________
// \______   \_   _____/ \      \__    ___/
//  |       _/|    __)_  /   |   \|    |
//  |    |   \|        \/    |    \    |
//  |____|_  /_______  /\____|__  /____|
//         \/        \/         \/

func drawTransparentSquare(opt base.Option, m *image.RGBA, idx, x, y int) {
	// In case variant number is too large.
	if idx >= len(base.VarColors) {
		idx = len(base.VarColors) - 1
	}

	for i := 0; i < 2*opt.SlotPixel; i++ {
		for j := 0; j < 2*opt.SlotPixel; j++ {
			m.Set(x+i, y+j, base.VarColors[idx])
		}
	}
}

// generateTransparentLayer generates transparent layer for each abv file.
func generateTransparentLayer(opt base.Option, h *abv.Human) error {
	m := initImage(opt, opt.EndBandIdx+1)
	for i, _ := range h.Blocks {
		for j, b := range h.Blocks[i] {
			drawTransparentSquare(opt, m, int(b.Variant),
				j*(opt.SlotPixel*opt.BoxNum)+2*j+(opt.BoxNum-2)*opt.SlotPixel,
				i*(opt.SlotPixel*opt.BoxNum)+2*i+(opt.BoxNum-2)*opt.SlotPixel)
		}
	}

	if err := saveImgFile(fmt.Sprintf("%s/TL_%s.png", opt.ImgDir, h.Name), m); err != nil {
		return fmt.Errorf("%s: %v", h.Name, err)
	}
	return nil
}

// generateTransparentLayers is a high level function to generate transparent layer
// for each abv file.
func generateTransparentLayers(opt base.Option, names []string) {
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
			log.Fatal("Fail to parse abv file(%s): %v", name, err)
		}
		h.Name = path.Base(name)

		if err = generateTransparentLayer(opt, h); err != nil {
			log.Fatal("Fail to generate transparent abv image(%s): %v", name, err)
		}
		log.Info("[%d] %s", i, h.Name)
	}
}
