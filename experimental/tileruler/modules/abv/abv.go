// Package abv parses abv format files based on tile rules.
package abv

import (
	"bufio"
	"bytes"
	"fmt"
	"io"
	"os"

	"github.com/curoverse/lightning/experimental/tileruler/modules/base"
	"github.com/curoverse/lightning/experimental/tileruler/modules/rule"
)

// Block represents a block for a human in given position in slippy map.
type Block struct {
	// Factor int
	// Band int // Band index.
	// Pos     int // Position index.
	Variant uint8
}

type Human struct {
	Name            string
	Blocks          map[int]map[int]*Block // map[bandIdx]map[posIdx]*Block
	BandLength      map[int]int            // 1-based. map[bandIdx]posCount
	PosCount        int
	MaxBand, MaxPos int // 0-based.
}

type WindowStat struct {
	Desc          string
	Variant       int // Non-default variant count.
	VariantSum    int // Sum of variant values.
	AvgVariantVal float32
	Unrecognize   int
}

type Statistic struct {
	WindowSize int
	WindowStat
	Windows map[int][]*WindowStat
}

var EncodeStd = []byte(".DEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/")

func Stat(name string, opt base.Option) (*Statistic, error) {
	if !base.IsFile(name) {
		return nil, fmt.Errorf("file(%s) does not exist or is not a file", name)
	}

	fr, err := os.Open(name)
	if err != nil {
		return nil, err
	}
	defer fr.Close()

	s := &Statistic{
		WindowSize: opt.WindowSize,
		WindowStat: WindowStat{
			Desc: "band index " + base.ToStr(opt.EndBandIdx),
		},
		Windows: make(map[int][]*WindowStat, opt.EndBandIdx+1),
	}
	for i := range s.Windows {
		s.Windows[i] = make([]*WindowStat, 0, 1000)
	}

	var bandIdx int    // Current band index.
	var colIdx int     // Current column index.
	var char uint8     // Current char.
	var ws *WindowStat // Current window statistic.

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
			bandIdx, err = base.HexStr2int(string(line))
			if err != nil {
				fmt.Println(string(line))
				return nil, err
			}

			if bandIdx > opt.EndBandIdx {
				break
			}
		} else {
			for colIdx, char = range line {
				if colIdx > 3999 {
					colIdx--
					break
				}

				if colIdx == 0 {
					ws = &WindowStat{
						Desc: fmt.Sprintf("%d-%d", 0, opt.WindowSize-1),
					}
				} else if colIdx%opt.WindowSize == 0 {
					if ws.Variant > 0 {
						ws.AvgVariantVal = float32(ws.VariantSum) / float32(ws.Variant)
					}
					s.Windows[bandIdx] = append(s.Windows[bandIdx], ws)
					s.Unrecognize += ws.Unrecognize
					s.Variant += ws.Variant
					s.VariantSum += ws.VariantSum
					ws = &WindowStat{
						Desc: fmt.Sprintf("%d-%d", colIdx, colIdx+opt.WindowSize-1),
					}
				}

				varIdx := -1
				switch char {
				case '-': // Not recognize.
					ws.Unrecognize++
					continue
				case '#':
					ws.Variant++
					varIdx = 62
				case '.': // Default variant.
					if opt.Mode == 1 {
						varIdx = 0
					} else {
						varIdx = 1000
					}
				default:
					ws.Variant++
					// Non-default variant.
					varIdx = bytes.IndexByte(EncodeStd, char)
					if varIdx < 1 {
						return nil, fmt.Errorf("Invalid version of variant[%s]: %s", line, string(char))
					}
				}
				ws.VariantSum += varIdx
			}

			if colIdx%opt.WindowSize != 0 {
				if ws.Variant > 0 {
					ws.AvgVariantVal = float32(ws.VariantSum) / float32(ws.Variant)
				}
				ws.Desc = fmt.Sprintf("%d-%d", colIdx-colIdx%opt.WindowSize, colIdx)
				s.Windows[bandIdx] = append(s.Windows[bandIdx], ws)
				s.Unrecognize += ws.Unrecognize
				s.Variant += ws.Variant
				s.VariantSum += ws.VariantSum
			}
		}

		isInBody = !isInBody
	}

	s.AvgVariantVal = float32(s.VariantSum) / float32(s.Variant)
	return s, nil
}

// Parse parses a abv file based on given tile rules and returns all blocks.
func Parse(
	name string,
	countOnly bool,
	r *base.Range,
	rules map[int]map[int]map[int]*rule.Rule) (*Human, error) {

	if !base.IsFile(name) {
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
	var colIdx int  // Current column index.
	var char uint8  // Current char.

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
			bandIdx, err = base.HexStr2int(string(line))
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
			for colIdx, char = range line {
				if r.EndPosIdx >= 0 && colIdx > r.EndPosIdx {
					colIdx--
					break
				}

				if countOnly {
					continue
				}

				varIdx := -1
				switch char {
				case '-': // Not recognize.
					continue
				case '#':
					varIdx = 99
				case '.': // Default variant.
					varIdx = 0
				default:
					// Non-default variant.
					varIdx = bytes.IndexByte(EncodeStd, char)
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
				h.Blocks[bandIdx][colIdx] = b
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

			if colIdx > h.MaxPos {
				h.MaxPos = colIdx
			}
			h.BandLength[bandIdx] = colIdx + 1
		}
		isInBody = !isInBody
	}

	return h, nil
}
