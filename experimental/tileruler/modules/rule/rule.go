// Package rule is a genome tile rule parser of lightning project.
package rule

import (
	"bufio"
	"fmt"
	"io"
	"os"
	"strings"

	"github.com/curoverse/lightning/experimental/tileruler/modules/base"
)

// Rule represents a tile rule.
type Rule struct {
	TileId  string `xorm:"VARCHAR(15) UNIQUE(s)"`
	Factor  int    // Common factor.
	Band    int    `xorm:"INDEX"` // Band index.
	Pos     int    // Position index.
	Variant int    `xorm:"UNIQUE(s)"` // Variant index.
}

// parseTileId parses given tile information and returns
// corresponding band and position index.
func parseTileId(info string) (band int, pos int, err error) {
	infos := strings.Split(info, ".")
	if len(infos) != 4 {
		return -1, -1, fmt.Errorf("invalid format")
	}

	band, err = base.HexStr2int(infos[0])
	if err != nil {
		return -1, -1, fmt.Errorf("cannot parse band index: %v", err)
	}

	pos, err = base.HexStr2int(infos[2])
	if err != nil {
		return -1, -1, fmt.Errorf("cannot parse position index: %v", err)
	}
	return band, pos, nil
}

// Parse parses a tile rule file and returns all rules.
func Parse(name string) (map[int]map[int]map[int]*Rule, error) {
	rules := make(map[int]map[int]map[int]*Rule)
	if err := IterateParse(name, func(r *Rule) error {
		if _, ok := rules[r.Band]; !ok {
			rules[r.Band] = make(map[int]map[int]*Rule)
		}
		if _, ok := rules[r.Band][r.Pos]; !ok {
			rules[r.Band][r.Pos] = make(map[int]*Rule)
		}
		rules[r.Band][r.Pos][r.Variant] = r
		return nil
	}); err != nil {
		return nil, err
	}
	return rules, nil
}

type IterateFunc func(*Rule) error

func IterateParse(name string, fn IterateFunc) error {
	if !base.IsFile(name) {
		return fmt.Errorf("file(%s) does not exist or is not a file", name)
	}

	fr, err := os.Open(name)
	if err != nil {
		return err
	}
	defer fr.Close()

	lastTileId := ""
	curVarIndex := 0

	var errRead error
	var line string
	buf := bufio.NewReader(fr)
	for idx := 0; errRead != io.EOF; idx++ {
		line, errRead = buf.ReadString('\n')
		line = strings.TrimSpace(line)

		if errRead != nil {
			if errRead != io.EOF {
				return errRead
			}
		}
		if len(line) == 0 {
			break // Nothing left.
		}

		r := new(Rule)
		infos := strings.Split(line, ",")
		r.Factor, err = base.StrTo(infos[0]).Int()
		if err != nil {
			return fmt.Errorf("%d: cannot parse factor of line[%s]: %v", idx, line, err)
		}

		r.TileId = infos[1][1 : len(infos[1])-1]
		r.Band, r.Pos, err = parseTileId(r.TileId)
		if err != nil {
			return fmt.Errorf("%d: cannot parse ID of line[%s]: %v", idx, line, err)
		}

		// NOTE: limit band and position just for debugging purpose.
		if r.Band > 10 {
			break
		}

		if r.Pos > 50 {
			continue
		}

		curVarIndex++
		if r.TileId == lastTileId {
			r.Variant = curVarIndex
		} else {
			curVarIndex = 0
			lastTileId = r.TileId
		}

		if err = fn(r); err != nil {
			return err
		}
	}
	return nil
}
