// Tile Ruler is a command line tool for generating PNGs based on given abv files.
package main

import (
	"flag"
	"os"
	"runtime"

	"github.com/curoverse/lightning/experimental/tileruler/cmd"
	"github.com/curoverse/lightning/experimental/tileruler/modules/cli"
)

const (
	APP_VER = "0.2.1.0717"
)

func init() {
	runtime.GOMAXPROCS(runtime.NumCPU())
	cmd.AppVer = APP_VER
}

func main() {
	app := cli.NewApp()
	app.Name = "Tile Ruler"
	app.Usage = "Generate, reverse and compare genome tiles"
	app.Version = APP_VER
	app.Commands = []cli.Command{
		cmd.CmdGen,
		cmd.CmdReverse,
	}
	app.Flags = append(app.Flags, []cli.Flag{
		cli.BoolFlag{"noterm, n", "disable color output"},
	}...)
	app.Run(os.Args)
}

var (
	workNum = flag.Int("work-num", 10, "work chan buffer")
)

// if opt.SlotPixel < 1 {
// 	return nil, errors.New("-slot-pixel cannot be smaller than 1")
// }

// switch {
// case (opt.Mode == ALL_IN_ONE || opt.Mode == ALL_IN_ONE_ABV) && opt.BoxNum < 13:
// 	// log.Fatalln("-box-num cannot be smaller than 13 in all-in-one mode")
// case opt.MaxColIdx < 1:
// 	// log.Fatalln("-max-col cannot be smaller than 1")
// case opt.MaxWorkNum < 1:
// 	// log.Fatalln("-work-num cannot be smaller than 1")
// case opt.Border < 1:
// 	// log.Fatalln("-border cannot be smaller than 1")
// case opt.Mode == COMPARE_ABV && len(flag.Args()) < 2:
// 	// log.Fatalln("please enter two abv file name")
// }
// return opt, nil
