package cmd

import (
	"github.com/curoverse/lightning/experimental/tileruler/modules/cli"
	"github.com/curoverse/lightning/experimental/tileruler/modules/plot"
)

var CmdPlot = cli.Command{
	Name:   "plot",
	Usage:  "run plot",
	Action: runPlot,
	Flags: []cli.Flag{
		cli.StringFlag{"http-port", "8000", "HTTP port"},
	},
}

func runPlot(ctx *cli.Context) {
	opt := setup(ctx)

	plot.Start(opt)
}
