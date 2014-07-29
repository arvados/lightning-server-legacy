// Tile Ruler is a command line tool for generating PNGs based on given abv files.
package main

import (
	"os"
	"runtime"

	"github.com/curoverse/lightning/experimental/tileruler/cmd"
	"github.com/curoverse/lightning/experimental/tileruler/modules/cli"
)

const (
	APP_VER = "0.2.4.0728"
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
		cmd.CmdCompare,
		cmd.CmdStat,
		cmd.CmdPlot,
	}
	app.Flags = append(app.Flags, []cli.Flag{
		cli.BoolFlag{"noterm, n", "disable color output"},
	}...)
	app.Run(os.Args)
}
