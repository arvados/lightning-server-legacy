package cmd

import (
	"os"
	"path"

	"github.com/curoverse/lightning/experimental/tileruler/modules/abv"
	"github.com/curoverse/lightning/experimental/tileruler/modules/base"
	"github.com/curoverse/lightning/experimental/tileruler/modules/cli"
	"github.com/curoverse/lightning/experimental/tileruler/modules/log"
)

var CmdStat = cli.Command{
	Name:   "stat",
	Usage:  "do statistics on abv files",
	Action: runStat,
	Flags: []cli.Flag{
		cli.IntFlag{"mode, m", 0, "generate mode(1-2), see README.md for detail"},
		cli.StringFlag{"abv-path", "./", "directory or path of abv file(s)"},
		cli.IntFlag{"max-band", 99, "max band index(inclusive) to do statistic"},
		cli.IntFlag{"size", 5, "window size of tiles"},
	},
}

func runStat(ctx *cli.Context) {
	opt := setup(ctx)

	switch opt.Mode {
	case 1:
		log.Info("Mode: Non-default variant sum")
	case 2:
		log.Info("Mode: Default variant sum")
	default:
		log.Fatal("Unknown mode: %v", opt.Mode)
	}

	names, err := base.GetFileListBySuffix(opt.AbvPath, ".abv")
	if err != nil {
		log.Fatal("Fail to get abv list: %v", err)
	}

	stats := make([]*abv.Statistic, len(names))
	maxWindows := 0

	os.MkdirAll("stat", os.ModePerm)
	fw, _ := os.Create("stat/stat.chart")
	defer fw.Close()
	fw.WriteString("===\n{ \"Name\" : \"line\", \"Height\" : 500, \"Width\" : 10000 }\n---\n")

	log.Info("[Idx] Name: non-default - unrecognize")
	for i, name := range names {
		stat, err := abv.Stat(name, opt)
		if err != nil {
			log.Fatal("Fail to parse abv file(%s): %v", name, err)
		}

		if maxWindows < len(stat.Windows[0]) {
			maxWindows = len(stat.Windows[0])
		}
		stats[i] = stat

		log.Info("[%d] %s: %d - %d", i, path.Base(name), stat.Variant, stat.Unrecognize)
	}

	for i := 1; i <= maxWindows; i++ {
		fw.WriteString(stats[0].Windows[0][i-1].Desc + " ")
		s := 0
		for k := 0; k < len(stats[0].Windows); k++ {
			for j := range stats {
				if i <= len(stats[j].Windows[k]) {
					s += int(stats[j].Windows[k][i-1].VariantSum)
				}
			}
		}
		fw.WriteString(base.ToStr(s) + " ")
		fw.WriteString("\n")
	}
}
