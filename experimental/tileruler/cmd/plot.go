package cmd

import (
	"github.com/curoverse/lightning/experimental/tileruler/modules/cli"
	"github.com/curoverse/lightning/experimental/tileruler/modules/plot"
)

var CmdPlot = cli.Command{
	Name:   "plot",
	Usage:  "run plot",
	Action: runPlot,
	Flags:  []cli.Flag{},
}

func runPlot(ctx *cli.Context) {
	setup(ctx)

	plot.Start()
}
