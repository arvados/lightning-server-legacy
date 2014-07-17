package main

// CompareAbvs compares 2 abv files with special treatments based on color map.
func CompareAbvs(abvPath1, abvPath2 string) error {
	// fr1, err := os.Open(abvPath1)
	// if err != nil {
	// 	return err
	// }
	// defer fr1.Close()
	// fr2, err := os.Open(abvPath2)
	// if err != nil {
	// 	return err
	// }
	// defer fr2.Close()

	// buf1 := bufio.NewReader(fr1)
	// buf2 := bufio.NewReader(fr2)

	// // Any character over the max variant index are treated the same color.
	// maxVarIdx := len(varColors) - 1
	// idx := 0
	// for {
	// 	c1, err1 := buf1.ReadByte()
	// 	c2, err2 := buf2.ReadByte()

	// 	if err1 != nil && err1 != io.EOF {
	// 		return err1
	// 	} else if err2 != nil && err2 != io.EOF {
	// 		return err2
	// 	}

	// 	if err1 == nil && err2 == io.EOF {
	// 		fmt.Printf("%s has more characters\n", abvPath1)
	// 		return nil
	// 	} else if err1 == io.EOF && err2 == nil {
	// 		fmt.Printf("%s has more characters\n", abvPath2)
	// 		return nil
	// 	} else if err1 == io.EOF && err2 == io.EOF {
	// 		break
	// 	}

	// 	idx++
	// 	if c1 != c2 {
	// 		i1 := bytes.IndexByte(abv.EncodeStd, c1)
	// 		i2 := bytes.IndexByte(abv.EncodeStd, c2)
	// 		if (i1 >= maxVarIdx && i2 >= maxVarIdx) ||
	// 			(c1 == '#' || c2 == '#') {
	// 			continue
	// 		}
	// 		fmt.Printf("In index %d, c1='%s' but c2='%s'\n", idx-1, string(c1), string(c2))
	// 		return nil
	// 	}
	// }

	// fmt.Println("Two abv files are prefect match!")
	return nil
}

// NOTE: not doing it for now, maybe next stage of server.
// var rules map[int]map[int]map[int]*rule.Rule
// var err error
// if !com.IsExist("tilerules.gob") {
// 	// Parse tile rules.
// 	rules, err = rule.Parse("/Users/jiahuachen/Downloads/abram/tiles_w_variants.count.sorted")
// 	if err != nil {
// 		log.Fatalf("Fail to parse rule file: %v", err)
// 	}
// 	fmt.Println("Time spent(parse rules):", time.Since(start))

// 	fw, err := os.Create("tilerules.gob")
// 	if err != nil {
// 		log.Fatalf("Fail to create gob file: %v", err)
// 	}
// 	defer fw.Close()

// 	if err = gob.NewEncoder(fw).Encode(rules); err != nil {
// 		log.Fatalf("Fail to encode gob file: %v", err)
// 	}
// 	fmt.Println("Time spent(encode gob):", time.Since(start))
// } else {
// 	fr, err := os.Open("tilerules.gob")
// 	if err != nil {
// 		log.Fatalf("Fail to create gob file: %v", err)
// 	}
// 	defer fr.Close()

// 	if err = gob.NewDecoder(fr).Decode(&rules); err != nil {
// 		log.Fatalf("Fail to decode gob file: %v", err)
// 	}
// 	fmt.Println("Time spent(decode gob):", time.Since(start))
// }

// images := make([][]*image.RGBA, realMaxBandIdx+1)
// for i := range images {
// 	images[i] = make([]*image.RGBA, realMaxPosIdx+1)
// 	for j := range images[i] {
// 		images[i][j] = initImage()
// 	}
// }

// for i := range humans {
// 	for _, b := range humans[i].Blocks {
// 		drawSquare(images[b.Band][b.Pos], b.Variant, i%13, i/13)
// 	}
// }
// fmt.Println("Time spent(draw blocks):", time.Since(start))

// for i := range images {
// 	for j := range images[i] {
// 		fr, err := os.Create(fmt.Sprintf("%s/%d-%d.png", *imgDir, i, j))
// 		if err != nil {
// 			log.Fatalf("Fail to create png file: %v", err)
// 		} else if err = png.Encode(fr, images[i][j]); err != nil {
// 			log.Fatalf("Fail to encode png file: %v", err)
// 		}
// 		fr.Close()
// 	}
// }

// fmt.Println("Time spent(total):", time.Since(start))

// func initImage2(opt *Option) *image.RGBA {
// 	m := image.NewRGBA(image.Rect(0, 0, *boxNum**slotPixel+1, *boxNum**slotPixel+1))
// 	draw.Draw(m, m.Bounds(), image.White, image.ZP, draw.Src)

// 	// Draw borders.
// 	for i := m.Bounds().Min.X; i < m.Bounds().Max.X; i++ {
// 		m.Set(i, m.Bounds().Min.Y, image.Black)
// 		m.Set(i, m.Bounds().Max.Y-1, image.Black)
// 	}
// 	for i := m.Bounds().Min.Y; i < m.Bounds().Max.Y; i++ {
// 		m.Set(m.Bounds().Min.X, i, image.Black)
// 		m.Set(m.Bounds().Max.X-1, i, image.Black)
// 	}

// 	if opt.HasGrids {
// 		// Draw grids.
// 		for i := 1; i < *boxNum; i++ {
// 			for j := m.Bounds().Min.Y; j < m.Bounds().Max.Y; j++ {
// 				m.Set(i**slotPixel, j, image.Black)
// 			}
// 		}
// 		for i := 1; i < *boxNum; i++ {
// 			for j := m.Bounds().Min.X; j < m.Bounds().Max.X; j++ {
// 				m.Set(j, i**slotPixel, image.Black)
// 			}
// 		}
// 	}
// 	return m
// }

// GenerateImgPerTile generates one PNG for each tile.
// func GenerateImgPerTile(opt *Option, humans []*abv.Human) {
// 	wg := &sync.WaitGroup{}
// 	workChan := make(chan bool, opt.MaxWorkNum)

// 	os.MkdirAll(opt.ImgDir, os.ModePerm)
// 	for i := opt.StartBandIdx; i <= opt.EndBandIdx; i++ {
// 		// fmt.Println(i)
// 		wg.Add(opt.EndPosIdx - opt.StartPosIdx + 1)
// 		os.MkdirAll(fmt.Sprintf("%s/%d", opt.ImgDir, i), os.ModePerm)
// 		for j := opt.StartPosIdx; j <= opt.EndPosIdx; j++ {
// 			m := initImage2(opt)
// 			for k := range humans {
// 				if b, ok := humans[k].Blocks[i][j]; ok {
// 					drawSingleSquare(opt, m, int(b.Variant), k%*boxNum, k / *boxNum)
// 				}
// 			}
// 			workChan <- true
// 			go func(band, pos int) {
// 				if pos%1000 == 0 {
// 					fmt.Println(band, pos)
// 				}
// 				fw, err := os.Create(fmt.Sprintf("%s/%d/%d.png", opt.ImgDir, band, pos))
// 				// fw, err := os.Create(fmt.Sprintf("%s/%d/%d.png", *imgDir, i, j))
// 				if err != nil {
// 					log.Fatalf("Fail to create png file: %v", err)
// 				} else if err = png.Encode(fw, m); err != nil {
// 					log.Fatalf("Fail to encode png file: %v", err)
// 				}
// 				fw.Close()
// 				wg.Done()
// 				<-workChan
// 			}(i, j)
// 		}
// 		runtime.GC()
// 	}

// 	fmt.Println("Goroutine #:", runtime.NumGoroutine())
// 	wg.Wait()
// }
