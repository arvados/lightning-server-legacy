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

Two versions of the CGF are discussed, one ASCII encoded and one binary encoded.  The ASCII version will be
described first as it motivates the binary encoding.

The ASCII CGF (aCGF) header consists of the string '#!cgf a' followed by a string encoded JSON
structure describing the parameters of the file.  Here is an example:

    #!cgf a
    {
      "CGFVersion" : "0.1",
      "Encoding" : "utf8",
      "Notes" : "ABV Version 0.1",

      "TileLibraryVersion" : "0.1.2",

      "PathCount" : 863,
      "StepPerPath" : [ 5433, 11585, ..., 181, 35 ],
      "TotalStep" : 10655006,

      "TileMap" : [
        { "Type" : "hom", "VariantALength" : 1, "VariantA" : [0], "VariantBLength" : 1, "VariantB" : [0] },
        { "Type" : "hom*", "VariantALength" : 1, "VariantA" : [0], "VariantBLength" : 1, "VariantB" : [0] },
        { "Type" : "het", "VariantALength" : 1, "VariantA" : [1], "VariantBLength" : 1, "VariantB" : [0] },
        { "Type" : "het", "VariantALength" : 1, "VariantA" : [0], "VariantBLength" : 1, "VariantB" : [1] },
        { "Type" : "het*", "VariantALength" : 1, "VariantA" : [1], "VariantBLength" : 1, "VariantB" : [0] },
        { "Type" : "het*", "VariantALength" : 1, "VariantA" : [0], "VariantBLength" : 1, "VariantB" : [1] },
        { "Type" : "hom", "VariantALength" : 1, "VariantA" : [1], "VariantBLength" : 1, "VariantB" : [1] },
        { "Type" : "hom", "VariantALength" : 1, "VariantA" : [1], "VariantBLength" : 1, "VariantB" : [1] },
        ...
        { "Type" : "het", "VariantALength" : 2, "VariantA" : [2,5], "VariantBLength" : 1, "VariantB" : [3] },
        ...
        { "Type" : "het*", "VariantALength" : 1, "VariantA" : [35], "VariantBLength" : 1, "VariantB" : [128] },
      ],

      "CharMap" : { "." : 0, "-" : 1, "C" : 2, "D" : 3, "E" : 4, ... , "+" : 62, "*" : -2, "#" : -1 },

      "ABV" : {
        "0" : "----------....----D--..#.. ... DD-----",
        "1" : "-----***1-....-A--#--..#.. ... ..3---",
        ...
        "35e" : "-----***1-....-A--#--..#.. ... ..3---"
      },

      "OverflowMap" : {
        "af:1e" : 5,
        "12f:211" : 35,
        ...
        "ff:123" : 310
      },

      "FinalOverflowMap" : {
        ...
        "2fe0:13a3" : { "Type" : "FastJ", "Data" : ">{ \"tileID\" : \"28e.00.001.000\", \"locus\" : ... }\nACCCAA ... AAC\nCT\n" },
        ...
      }

    }

Non hash and non star values (that is, not `#` and not `*`) values at Positions in the entries of the `ABV` JSON object encode a position into the `TileMap' JSON object.
If a hash is encountered (`#`), the appropriate entry can be looked up in the `OverflowMap` JSON object.
In the case of a star (`*`), the encoding is more complex and will be discussed in more detail below.

When the `ABV` entry maps to a position in the `TileMap` table, the `Type` filed indicates whether it is a heterozygous, homozygous or non-simple variant and which tile variant to use when consulting the tile libarary.
For example, should the entry be `D`, this maps to the fourth position in the `TileMap` JSON object (as indicated by the `CharMap` table), which indicates that for the path and step, tile variant 0 should be used for the 'A' allele and tile variant 1 should be used for the 'B' allele.

If a hash is encountered (`#`), there will be an appropriate entry in the `OverflowMap` JSON object where the key is utf8 encoded hexademial step and position concatenated with the colon character (`:`).
For example, if at decimal path 175 and at decimal position 31 a hash (`#`) is encounted in the `ABV` string, the entry `af:1e` should be referenced in the `OverflowMap` JSON object.

For that entry in the above example, the `Type` field is `Map` and the `Data` field is `5`, so this references the `TileMap` entry of 5.

If the entry does not appear in the `OverflowMap` JSON object, then the `FinalOverflowMap` JSON object should be consulted.

For now, the only option for the `FinalOverflowMap` JSON object entry is `FastJ` and, in this case, the `Data` field will be a JSON encoded string of a FastJ tile corresponding to that entry.
This is included in case the CGF file has a novel tile that is not included in the tile library referenced.


A non-simple variant is indicated in the `ABV` string as a star (`*`).
In the case of a non-simple vairant (that is a star (`*`) is encountered), this is interpreted as a tile that spans multiple default tiles.
This tile is still referenced in the tile libarary, as pointed to by the `TileMap` object.
The number of default tiles it spans is indicated by the number of contiguous stars plus one.
For example, if the string `--.D**f..-` is encountered, this is a tile that spans 3 default tiles.
The first non star character encoutered is the encoded position into the `TileMap` JSON object.
If the first non star character is a hash (`#`), the `OverflowMap` JSON object table (or `FinalOverflowMap` if it doesn't exist
in the `OverflowMap` table) should be consulted to determine the mapped variant type.

In the non-simple case, each of the alleles has the list of tiles encoded in the `VariantA` and `VariantB` field.  Note
that the tiles in either of these lists can be of varying default tile lengths.

For exapmle, if 'A' allele spans 3 default tiles and the 'B' allele has nothing but default tiles, this would be indicated as:

    ...**J...

    ...
    { "Type" : "non-simple", "VariantA" : [ 54 ], "VariantB" : [ 0, 0, 0 ], ... }
    ...

The non-simple case can have 'interleaved' tiles of varying default tile length.
For example, allele 'A' could have a non-simple tile of default tile length 3 followed by two default tiles, whereas allele 'B' could have a
default tile followed by a non-simple tile that spans 4 default tiles.
In this case, the maximum default tile length that spans the entire non-simple region is taken which, in this case, is 5.
Here is an example of the what the portion of the `ABV` string might look like along with the entry in the `TileMap` lookup table:

    ...****Z...

    { "Type" : "non-simple", "VariantA" : [ 101, 0, 0 ], "VariantB" : [ 0, 122 ], ... }

Where again, in this example, tile variant 101 spans 3 default tiles whereas tile variant 122 spans 4 default tiles.





Notes
-----

  - The `FinalOverflowMap` was added instead of making each value a structure in the `OverflowMap` for simplicity.
  - It's unclear how many values the `CharMap` field should have (64, 65, 66?).  For now, 64 values are chosen in the case we want to go to a binary represtation.
  - A possible choice of the `TileMap` structure is to have the `VariantA` and `VariantB` conditionally be lists if the `Type` field indicates it (with a '+' character, for example).
    This was not done for simplicites sake.  In addition the length field is also provided, even though it can be derived from the array to ease viewability.



