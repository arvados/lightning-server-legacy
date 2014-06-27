package main

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
