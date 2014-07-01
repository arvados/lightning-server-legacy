package main

import (
	"testing"

	. "github.com/smartystreets/goconvey/convey"

	"github.com/genomelightning/tileruler/abv"
)

func Test_calInitImg(t *testing.T) {
	type Val struct {
		endBandIdx, endPosIdx int
		slotPixel             int
		boxNum, border        int
		x, y                  int
	}
	vals := []Val{
		{9, 9, 1, 13, 1, 139, 139},
		{9, 99, 1, 13, 1, 1399, 139},
		{99, 99, 1, 13, 1, 1399, 1399},
		{99, 999, 1, 13, 1, 13999, 1399},
		{862, 999, 1, 13, 1, 13999, 12081},
		{862, 9999, 1, 13, 1, 139999, 12081},
		{862, 19999, 1, 13, 1, 279999, 12081},
		{862, 29999, 1, 13, 1, 419999, 12081},
		{862, 39999, 1, 13, 1, 559999, 12081},
		{862, 49999, 1, 13, 1, 699999, 12081},
		{862, 59999, 1, 13, 1, 839999, 12081},
		{862, 59999, 2, 13, 1, 1619999, 23300},
		{862, 59999, 2, 13, 2, 1679998, 24162},
		{862, 59999, 2, 14, 2, 1799998, 25888},
		{862, 59999, 2, 15, 2, 1919998, 27614},
	}
	Convey("Calculate init image x and y", t, func() {
		for _, v := range vals {
			opt := &Option{
				Range: &abv.Range{
					EndBandIdx: v.endBandIdx,
					EndPosIdx:  v.endPosIdx,
				},
				SlotPixel: v.slotPixel,
			}
			So(calInitImgX(opt, v.boxNum, v.border), ShouldEqual, v.x)
			So(calInitImgY(opt, v.boxNum, v.border), ShouldEqual, v.y)
		}
	})
}
