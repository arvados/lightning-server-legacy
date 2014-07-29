package plot

import (
	"github.com/curoverse/lightning/experimental/tileruler/modules/base"
	"github.com/curoverse/lightning/experimental/tileruler/modules/log"
)

func Start(opt base.Option) {
	log.Info("Start listening on :%s", opt.HttpPort)
	log.Fatal("%v", ListenAndServe("0.0.0.0:"+opt.HttpPort))
}
