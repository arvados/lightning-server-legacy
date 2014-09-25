Tile Ruler
==========

Tile Ruler is a command line tool for generating, reversing and comparing genome tiles.

### Installation

	go get -u github.com/curoverse/lightning/experimental/tileruler

## Usage

```
NAME:
   Tile Ruler - Generate, reverse and compare genome tiles

USAGE:
   Tile Ruler [global options] command [command options] [arguments...]

VERSION:
   0.2.3.0727

COMMANDS:
   gen		generate images from abv file(s)
   reverse	reverse image back to abv file(s)
   compare	compare 2 abv files
   stat		do statistics on abv files
   help, h	Shows a list of commands or help for one command

GLOBAL OPTIONS:
   --noterm, -n		disable color output
   --help, -h		show help
   --version, -v	print the version
```

### Command `gen`

```
NAME:
   gen - generate images from abv file(s)

USAGE:
   command gen [command options] [arguments...]

OPTIONS:
   --mode, -m '0'	generate mode(1-3), see README.md for detail
   --img-dir 'tr_imgs'	path to store images file(s)
   --abv-path './'	directory or path of abv file(s)
   --color-spec 	path of color specification file
   --max-band '9'	max band index(inclusive)
   --max-pos '49'	max position index(inclusive)
   --max-col '3999'	max column index(inclusive)
   --box-num '15'	box number of width and height
   --slot-pixel '2'	slot pixel of width and height
   --border '2'		border pixel between rectangles
   --force, -f		force to regenerate existed images
   --count-only, -c	for mode 2 and count only mode
```

- `-abv-path`: directory or path of abv file(s), can be a file path for one abv or a directory path for all abv files in that directory, both absolute or relative path are acceptable. Default is the work directory.
- `-img-dir`: path to store PNG files(s), has to be a directory.
- `-mode`: has to specify every time
	- `1`: single PNG per abv
	- `2`: all abv in one full-size PNG
	- `3`: every full-size transparent layer per abv
- `-slot-pixel`: slot pixel of width and height. Default is `2`.
- `-max-band`: max(inclusive) band index. `-1` means auto-detect. Default is `9`.
- `-max-pos`: max(inclusive) position index. `-1` means auto-detect. Default is `49`.
- `-max-col`: max(inclusive) column index. Default is `3999`.
- `-color-spec`: path of color specification file. Just for an example of format, which is the default colors:
	
	```
	255, 255, 255
	0, 204, 0
	0, 255, 0
	0, 255, 255
	0, 204, 255
	0, 153, 255
	0, 102, 255
	0, 51, 255
	0, 0, 255
	```

#### Examples

	tileruler gen -mode=1 -abv-path=abram -max-band=-1 -max-pos=-1

### Command `reverse`

```
NAME:
   reverse - reverse image back to abv file(s)

USAGE:
   command reverse [command options] [arguments...]

OPTIONS:
   --mode, -m '0'	generate mode(1-2), see README.md for detail
   --reverse-path './'	directory or path of reverse image file(s)
```

- `-mode`: has to specify every time
	- `1`: single abv image reverse

#### Examples

	tileruler reverse -mode=1 -reverse-path=human1.png

### Command `compare`

```
NAME:
   compare - compare 2 abv files

USAGE:
   command compare [arguments...]
```

#### Examples

	tileruler compare human1.abv human2.abv

### Command `stat`

```
NAME:
   stat - do statistics on abv files

USAGE:
   command stat [command options] [arguments...]

DESCRIPTION:


OPTIONS:
   --mode, -m '0'	generate mode(1-2), see README.md for detail
   --abv-path './'	directory or path of abv file(s)
   --max-band '99'	max band index(inclusive) to do statistic
   --size '5'		window size of tiles
```

- `-mode`: has to specify every time
	- `1`: non-default variant sum
	- `2`: default variant sum

#### Examples

	$ tileruler stat -mode=1 -abv-path=abram
	$ cd stat
	$ tileruler plot # then go to http://localhost:8000

### Known Issues

- For `-mode=1`, there might be Go `image/png.Encoder` bug for `-slot-pixel>1` and `-max-pos>20000`. To get correct PNG, make sure `-slot-pixel` is `1` or `-max-pos` is less than `20000`. 
	- Execute `-slot-pixel=2 -max-pos=19999` will be fine.

### Command `abv`

```
NAME:
   abv - Create ABV file from FastJ files

USAGE:
   command stat [command options] [arguments...]

USAGE:
   command abv [command options] [arguments...]

DESCRIPTION:


OPTIONS:
   --human                                              human name
   --fastj-path 'fastj/hu011C57/fj.fill'                path to fastj file(s)
   --lib-path 'fastj/tile_md5sum_hu154_sort.csv.gz'     path to fastj file(s)
   --count-gap                                          count gaps as no-call
   --lz4-path 'lz4'                                     path to lz4 executable
   --gz-path 'gunzip'                                   path to gunzip executable
   --bz2-path 'bunzip2'                                 path to bunzip2 executable

```

#### Examples

	$ tileruler abv --fastj-path /data/fastjdir --lib-path /data/ref/tile_md5sum_hu154_sort.csv.gz huNAME
	$ cd abvs
	$ ls
  huNAME_A.abv huNAME_B.abv


