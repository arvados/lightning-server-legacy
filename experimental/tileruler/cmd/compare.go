package cmd

import (
	"bufio"
	"io"
	"os"

	"github.com/curoverse/lightning/experimental/tileruler/modules/cli"
	"github.com/curoverse/lightning/experimental/tileruler/modules/log"
)

var CmdCompare = cli.Command{
	Name:   "compare",
	Usage:  "compare 2 abv files",
	Action: runCompare,
	Flags:  []cli.Flag{},
}

func runCompare(ctx *cli.Context) {
	setup(ctx)

	if len(ctx.Args()) < 2 {
		log.Fatal("Not enough abv files to compare")
	}

	abvPath1 := ctx.Args().Get(0)
	abvPath2 := ctx.Args().Get(1)

	fr1, err := os.Open(abvPath1)
	if err != nil {
		log.Fatal("Fail to open abv file(%s): %v", abvPath1, err)
	}
	defer fr1.Close()
	fr2, err := os.Open(abvPath2)
	if err != nil {
		log.Fatal("Fail to open abv file(%s): %v", abvPath2, err)
	}
	defer fr2.Close()

	buf1 := bufio.NewReader(fr1)
	buf2 := bufio.NewReader(fr2)

	// Any character over the max variant index are treated the same color.
	// maxVarIdx := len(base.VarColors) - 1
	idx := 0
	for {
		c1, err1 := buf1.ReadByte()
		c2, err2 := buf2.ReadByte()

		if err1 != nil && err1 != io.EOF {
			log.Fatal("Fail to read abv file(%s): %v", abvPath1, err1)
		} else if err2 != nil && err2 != io.EOF {
			log.Fatal("Fail to read abv file(%s): %v", abvPath2, err2)
		}

		if err1 == nil && err2 == io.EOF {
			log.Info("%s has more characters\n", abvPath1)
			return
		} else if err1 == io.EOF && err2 == nil {
			log.Info("%s has more characters\n", abvPath2)
			return
		} else if err1 == io.EOF && err2 == io.EOF {
			break
		}

		idx++
		if c1 != c2 {
			// i1 := bytes.IndexByte(abv.EncodeStd, c1)
			// i2 := bytes.IndexByte(abv.EncodeStd, c2)
			// if (i1 >= maxVarIdx && i2 >= maxVarIdx) ||
			// 	(c1 == '#' || c2 == '#') {
			// 	continue
			// }
			log.Info("In index %d, c1='%s' but c2='%s'\n", idx-1, string(c1), string(c2))
			return
		}
	}

	log.Info("Two abv files are prefect match!")
}
