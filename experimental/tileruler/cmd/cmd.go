package cmd

import (
	"github.com/curoverse/lightning/experimental/tileruler/modules/base"
	"github.com/curoverse/lightning/experimental/tileruler/modules/cli"
	"github.com/curoverse/lightning/experimental/tileruler/modules/log"
)

var AppVer string

func setup(ctx *cli.Context) base.Option {
	if ctx.GlobalBool("noterm") {
		log.NonColor = true
	}

	log.Info("App Version: %s", AppVer)

	if err := base.ParseColorSpec(ctx.String("color-spec")); err != nil {

	}

	return base.ParseOption(ctx)
}
