Tile Ruler
==========

Tile Ruler is a command line tool for generating PNGs based on given abv files.

### Usage

- `-abv-path`: directory or path of abv file(s), can be a file path for one abv or a directory path for all abv files in that directory, both absolute or relative path are acceptable. Default is the work directory.
- `-img-dir`: path to store PNG files(s), has to be a directory.
- `-mode`: has to specify every time
	- `1`: single PNG per abv
	- `2`: all abv in one full-size PNG
	- `3`: every full-size transparent layer per abv
- `-slot-pixel`: slot pixel of width and height. Default is `2`.
- `-max-band`: max(inclusive) band index. `-1` means auto-detect.
- `-max-pos`: max(inclusive) position index. `-1` means auto-detect.

### Examples

	tileruler -mode=1 -abv-path=abram -max-band=-1 -max-pos=-1

### Known Issues

- For `-mode=1`, there might be Go `image/png.Encoder` bug for `-slot-pixel>1` and `-max-pos>20000`. To get correct PNG, make sure `-slot-pixel` is `1` or `-max-pos` is less than `20000`. 
	- Execute `-slot-pixel=2 -max-pos=19999` will be fine.
	
### Time Consuming

- Command `tileruler -mode=X -max-band=-1 -max-pos=-1`
- 863 bands and 4000 positions

#### Dev machine

- OS: Max OS X 10.9.3
- Processor: 2 GHz Intel Core i7
- Memory: 8GB 1600 MHz DDR3

#### Cost samples

- Mode 1:
	- Pixels: **1726 * 8000**
	- Size: **1.1MB**
	- Time: 4s * 154 = **10m16s**
- Mode 2:
	- Pixels: **127998 * 27614**
	- Size: **161.6MB**
	- Time: **7m41s** (total)
- Mode 3:
	- Pixels: **127998 * 27614**
	- Size: **16.4MB**
	- Time: 7m5s * 154 = **19hours**
	