// Package abv parses abv format files based on tile rules.
package abv

import (
	"bufio"
	"bytes"
	"fmt"
	"io"
	"os"

	"github.com/Unknwon/com"

	"github.com/genomelightning/tileruler/rule"
)

type Range struct {
	StartBandIdx, EndBandIdx int
	StartPosIdx, EndPosIdx   int
}

// Block represents a block for a human in given position in slippy map.
type Block struct {
	// Factor int
	// Band int // Band index.
	// Pos     int // Position index.
	Variant uint8
}

type Human struct {
	Name            string
	Blocks          map[int]map[int]*Block
	BandLength      map[int]int // 1-based.
	PosCount        int
	MaxBand, MaxPos int // 0-based.
}

var encodeStd = []byte("CDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/")

// Parse parses a abv file based on given tile rules and returns all blocks.
func Parse(name string, r *Range, rules map[int]map[int]map[int]*rule.Rule) (*Human, error) {
	if !com.IsFile(name) {
		return nil, fmt.Errorf("file(%s) does not exist or is not a file", name)
	}

	fr, err := os.Open(name)
	if err != nil {
		return nil, err
	}
	defer fr.Close()

	h := new(Human)
	h.Blocks = make(map[int]map[int]*Block)
	h.BandLength = make(map[int]int)
	var bandIdx int // Current band index.

	var line []byte
	buf := bufio.NewReader(fr)

	// To skip header e.g.: "huFE71F3"
	_, errRead := buf.ReadBytes(' ')
	if errRead != nil {
		return nil, errRead
	}

	// True for next thing read will be actual body not band index.
	isInBody := false

	for errRead != io.EOF {
		line, errRead = buf.ReadBytes(' ')
		line = bytes.TrimSpace(line)

		if errRead != nil {
			if errRead != io.EOF {
				return nil, errRead
			}
		}
		if len(line) == 0 {
			isInBody = !isInBody
			continue
		}

		if !isInBody {
			bandIdx, err = com.HexStr2int(string(line))
			if err != nil {
				fmt.Println(string(line))
				return nil, err
			}

			if r.EndBandIdx >= 0 && bandIdx > r.EndBandIdx {
				break
			} else if bandIdx > h.MaxBand {
				h.MaxBand = bandIdx
			}
		} else {
			if bandIdx < r.StartBandIdx {
				isInBody = !isInBody
				continue
			}
			h.BandLength[bandIdx] = len(line)
			for i, char := range line {
				if i < r.StartPosIdx {
					continue
				} else if r.EndPosIdx >= 0 && i > r.EndPosIdx {
					break
				} else if i > h.MaxPos {
					h.MaxPos = i
				}

				varIdx := -1
				switch char {
				case '-', '#': // Not recognize or just skip.
					continue
				case '.': // Default variant.
					varIdx = 0
				default:
					// Non-default variant.
					varIdx = bytes.IndexByte(encodeStd, char)
					if varIdx < 1 {
						return nil, fmt.Errorf("Invalid version of variant[%s]: %s", line, string(char))
					}
				}
				h.PosCount++

				b := &Block{
					// Band: bandIdx,
					// Pos:     i,
					Variant: uint8(varIdx),
				}
				if _, ok := h.Blocks[bandIdx]; !ok {
					h.Blocks[bandIdx] = make(map[int]*Block)
				}
				h.Blocks[bandIdx][i] = b
				// if _, ok := h.Blocks[b.Band]; !ok {
				// 	h.Blocks[b.Band] = make(map[int]*Block)
				// }
				// h.Blocks[b.Band][b.Pos] = b

				// r, ok := rules[b.Band][b.Pos][varIdx]
				// if !ok {
				// 	return nil, fmt.Errorf("Rule not found: %d.%d.%d", b.Band, b.Pos, varIdx)
				// }
				// b.Factor = r.Factor
			}
		}
		isInBody = !isInBody
	}

	return h, nil
}
