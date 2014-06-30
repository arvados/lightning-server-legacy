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

- Mode 1: `tileruler -mode=1 -abv-path=abram -max-band=-1 -max-pos=-1`
- Mode 2:
- Mode 3: