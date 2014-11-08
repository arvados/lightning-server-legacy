Compact Genome Format
=====================

The compact genome format (CGF) is a file format that efficiently describes a genomic sequence efficiently.
This document aims to give an overview of the format.

Overview
--------

This is a draft of the current compact genome format specification.

The compact genome format (CGF) describes a genome against a tile library.  At a high level, the compact genome
format can be thought of a long array of pointers referencing the tile variants in the tile library.  The specifics
are a bit more involved as the mapping is against an internal table that describes which combination of tiles
represent the sequence at a particular genomic location.  This mapping allows for genomic regions to account
for heterozygous and homozygous mutations.

The ASCII CGF (aCGF) header consists of the string `{"#!cgf":"a",` followed by a string encoded JSON
structure describing the parameters of the file.  Here is an example:

    {"#!cgf":"a",
      "CGFVersion" : "0.1",
      "Encoding" : "utf8",
      "Notes" : "ABV Version 0.1",

      "TileLibraryVersion" : "4743efb3fe7c46208aedaf6e0816ad12",
      "ABV" : {
        "0" : "----------....----D--..#.. ... DD-----",
        "1" : "-----***1-....-A--#--..#.. ... ..3---",
        ...
        "35e" : "-----***1-....-A--#--..#.. ... ..3---"
      },

      "CharMap" : { "A":0, ".":0, "B":1, "-" : 1, "C":2, "D":3, "E":4, ... , "+":62, "*":-3, "#":-2, "-":-1 },
      "CanonicalCharMap" : ".BCDEFGHIJKLNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz012345678*#-",

      "PathCount" : 863,
      "StepPerPath" : [ 5433, 11585, ..., 181, 35 ],
      "TotalStep" : 10655006,

      "TileMap" : [
        { "Type" : "hom",  "Ploidy" : 2, "Variant" : [ [0], [0] ], 1, "VariantLength" : [1,1] },
        { "Type" : "hom*", "Ploidy" : 2, "Variant" : [ [0], [0] ], 1, "VariantLength" : [1,1] },
        { "Type" : "het",  "Ploidy" : 2, "Variant" : [ [1], [0] ], 1, "VariantLength" : [1,1] },
        { "Type" : "hom*", "Ploidy" : 2, "Variant" : [ [0], [1] ], 1, "VariantLength" : [1,1] },
        { "Type" : "het*", "Ploidy" : 2, "Variant" : [ [1], [0] ], 1, "VariantLength" : [1,1] },
        { "Type" : "het*", "Ploidy" : 2, "Variant" : [ [0], [1] ], 1, "VariantLength" : [1,1] },
        { "Type" : "hom",  "Ploidy" : 2, "Variant" : [ [1], [1] ], 1, "VariantLength" : [1,1] },
        { "Type" : "hom*", "Ploidy" : 2, "Variant" : [ [1], [1] ], 1, "VariantLength" : [1,1] },
        { "Type" : "het",  "Ploidy" : 2, "Variant" : [ [0,0], [1] ], 1, "VariantLength" : [2,1] },
        ...
        { "Type" : "het",  "Ploidy" : 2, "Variant" : [ [2,5], [3] ], 1, "VariantLength" : [2,1] },
        ...
        { "Type" : "het",  "Ploidy" : 2, "Variant" : [ [35], [128] ], 1, "VariantLength" : [1,1] }
      ],

      "PhaseLoci" : {
        "PhaseGroup_0_0_0_1" :
        [
          [ "1e:50:30", "1f:32:201" ],
          ...
          [ "23:f1:45", "25:32:50" ]
        ],
        "PhaseGroup_0_0_1_12" :
        [
          [ "1e:50:28", "1e:50:2a" ],
          ...
          [ "33:f0:5e", "33:f0:5f" ]
        ]
      },

      "OverflowMap" : {
        "0:1e" : 5,
        "1:211" : 35,
        ...
        "ff:123" : 310
      },

      "FinalOverflowMap" : {
        ...
        "35e:13a3" : { "Type" : "FastJ", "Data" : ">{ \"tileID\" : \"35e.00.13a3.000\", \"locus\" : ... }\nACCCAA ... AAC\nCT\n" },
        ...
      }

    }

The `TileLibraryVersion` is an md5sum of the canonical tile library listing.

The `CharMap` object maps character codes as they appear in the `ABV` elements to positions in the `TileMap` object.
For example, if an 'E' is encountered, this maps to the 4th position in the `TileMap` array.

The `CharMap` maps many characters to a single value.  It is an error if a character maps to multiple values in the `CharMap` object.
Multiple mapping is done to allow for different character mappings at ABV positions while keeping a path to compatibility
with the base64 encoding.
Any character that appears in the keys of the `CharMap` object may appear in the `ABV` element values.

The `CanonicalCharMap` gives the default encoding for the `ABV` value entries, where the character encoding is given by the character
at the appropriate position in the string array.

Non negative mapped values (that is, not a `-`, `#` or `*`) at Positions in the entries of the `ABV` JSON object encode a position into the `TileMap` JSON object.

When the `ABV` entry maps to a position in the `TileMap` table, the `Type` filed indicates whether it is a heterozygous, homozygous or
non-simple variant and which tile variant to use when consulting the tile library.
For example, should the entry be `D`, this maps to the fourth position in the `TileMap` JSON object (as indicated by the `CharMap` table),
which indicates that for the path and step, tile variant 0 should be used for the 'A' allele and tile variant 1 should be used for the 'B' allele.

A mapped value of `-1` represents a 'no-call'.

If a mapped value of `-2` is encountered (that is, a `#` in the above mapping), the appropriate entry can be looked up in either the
`OverflowMap` JSON object or `FinalOverflowMap` JSON object.
The key into the `OverflowMap` or `FinalOverflowMap` object is utf8 encoded hexadecimal step and position concatenated with the colon character (`:`).
For example, if at decimal path 175 and at decimal position 31 a hash (`#`) is encountered in the `ABV` string, the entry `af:1e` should be referenced in the `OverflowMap` JSON object.
For that entry in the above example, the `Type` field is `Map` and the `Data` field is '5', so this references the `TileMap` entry at index 5.

If the key is not found in the `OverflowMap`, the `FinalOverflowMap` should be consulted.  It is an error if an overflowed tile does not appear
in either the `OverflowMap` or `FinalOverflowMap` object.

For now, the only option for the `FinalOverflowMap` JSON object entry is `FastJ`.
In this case the `Data` field will be a JSON encoded string of a FastJ tile corresponding to that entry.
This is included in case the CGF file has a novel tile that is not included in the tile library referenced.

A non-simple variant is indicated in the `ABV` string as a mapped `-3` value (i.e. `*`).
In the case of a non-simple variant, this is interpreted as a tile that spans multiple 'seed' tiles.
The first non negative mapped value before the contiguous list of mapped `-3` values indicates the position in the `TileMap` (or
if the overflow objects should be consulted).

This tile is still referenced in the tile library, as pointed to by the `TileMap` object.
The number of seed tiles it spans is indicated by the number of contiguous mapped `-3` values (i.e. `*`s) plus one.
For example, if the string `--.D**f..-` is encountered, this is a tile that spans 3 seed tiles and maps to `TileMap` element 3 (from the `D`).

In the non-simple case, each of the alleles has the list of tiles encoded in the `Variant` array.  Note
that the tiles in either of these lists can be of varying seed tile lengths.

For example, if the first allele spans 3 seed tiles and the second allele has nothing but default tiles, this could be indicated as:

    ...J**...

With a `TileMap` entry:

    { "Type" : "non-simple", "Variant" : [ [ 54 ], [ 0, 0, 0 ] ], ... }

The non-simple case can have 'interleaved' tiles of varying seed tile length.
For example, the first allele could have a non-simple tile of seed tile length 3 followed by two default tiles, whereas
the second allele could have a
default tile followed by a non-simple tile that spans 4 seed tiles.
In this case, the maximum seed tile length that spans the entire non-simple region is taken which, in this case, is 5.
Here is an example of the what the portion of the `ABV` string might look like along with the entry in the `TileMap` lookup table:

    ...Z****...

With a `TileMap` entry:

    { "Type" : "non-simple", "Variant" : [ [ 101, 0, 0 ], [ 0, 122 ] ], ... }

Where again, in this example, tile variant 101 spans 3 default tiles whereas tile variant 122 spans 4 default tiles.


The `PhaseLoci` object attempts to capture phased groupings.  Each element in the `PhaseLoci` object maps to an array of tile intervals
represented as ASCII encode path and step (separated by a colon).



Notes
-----

  - The `FinalOverflowMap` was added instead of making each value a structure in the `OverflowMap` for simplicity.
  - It's unclear how many values the `CharMap` field should have (64, 65, 66?).  For now, 64 values are chosen in the case we want to go to a binary representation.
  - The `CharMap` is a many to one mapping in an attempt to be able to recover the base64 encoding easily.
  - Should the `ABV` ever need to be base64 encoded, one can take the convention that negative numbers are relative to 64.  That is, a `-1` could map to
    the value `63` (mapped to a `/` character), a `-2` value could map to value `62` (mapped to a `+` character) and a `-3` value could map to value
    `61` (mapped to a `9` character).
  - By convention, negative values are used to handle special cases for tiles as in the overflow indicators, non-simple and complex tile types.



