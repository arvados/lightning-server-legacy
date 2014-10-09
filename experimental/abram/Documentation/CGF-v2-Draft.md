Compact Genome Format
=====================

This is a quick note to detail the experimental next version
of the compressed genome format (CGF).  This is mostly here
to serve as a reminder of the ideas involved and is subject
change or to be scrapped compleletely.

Overview
--------

As in v1 of the CGF, this is also a lookup based encoding.
Associated with every genome is a tile library, specified in
the header of every CGF file, that can be used to reconstruct
the original genome given the list of pointers referencing it.

Chromosomes are encoded as a list of `words`, to be described
below, that encode references into a map.  The map gives a
reference to which tile variant to use in the tile library.

For space and efficiency reasons, references into the map
are stored in a more efficient manner than having a simple
integer reference into the map.

Words are of a fixed bit length, `b`, and split into two
regions, the `synopsis` bits, of length `s` bits,  and the `hexit region`.  The
`hexit region` is of fixed bit width `H`, and is composed of
a variable number of `hexits`, each of bit length `h`, with
a maximum number of `floor( H/h )` bits each.  For simplicity
we will only consider `hexits` whose length is an exact multiple
of `H`.

A diagram is illustrative:

    /--------- s ----------\/----------------------------- H ------------------------------\
    |    synopsis bits     |                       hexit region                            |
    ----------------------------------------------------------------------------------------
    |                      |                                                               |
    |                      | [ hexit_0 ] [ hexit_1 ] ... [ hexit_{k-1} ]  <    unused   >  |
    |                      |                                                               |
    ----------------------------------------------------------------------------------------
                             \___ h ___/ \___ h ___/     \_____ h _____/  \__ H - k*h __/
    \______________________________________ b _____________________________________________/


From a high level perspective, mapping to a tile variant can be thought of as a sort of 'cascade',
where first the synopsis bits are consulted, then the hexit region is consulted and finally
the spillover tables if need be.  The logic is roughly as follows:

    if ( synopsis bit is 0 ) -> use default tile variant
    else { // consult hexit region
      if ( hexit encoding maps to a tile variant ) --> use that tile variant
      else { // consult OverflowMap
        if ( path and step are in the OverflowMap table ) --> use the tile variant reported by the OverflowMap
        else { // consult FinalOverflowMap
          if ( path and step are in the FinalOverflowMap ) --> use the tile variant reported by the FinalOverflowMap
          else ERROR
        }
      }
    }

The `OverflowMap` and the `FinalOverflowMap` are the same as in the v1 of the CGF document.
The encoding of the synopsis bits and hexit region is discussed below.

Each word encodes for `s` tiles.  A `0` value for the synopsis bit at a location
encodes for the 'default' tile at that location (variant 0 in the `map`).  If the synopsis
bit is `1` at that location, the value must be derived by looking
in the `hexit region.

The `hexit region` encodes a variable number of hexits.  Each hexit is a digit in a variable
length encoding of the `map` variant id.  Each `hexit` is of `h` bits
long, with the first `h-1` bits encoding a value and the last bit encoding a flag
indicating that the value has spilled over and the next hexit in the sequence
should be used to construct the value.  In this way, the value decoded is of a
variable number of bits.  This gives the ability to capture common cases while
allowing for the more uncommon values to be captured by being able to dynamically
grow the bits used for the mapping.

`Hexits` are read from left to right in the order the synopsis bits are seen.
A special value is reserved that is used to declare the tile lookup to be too big
to fit in the representation.  In such a situation the `spillover table` should be consulted
to derive which lookup value to use.

If more true `synopsis` bits are seen than `hexits` allowed, the `spillover table`
should be consulted for the remaining values.

Each string of `hexits` encodes a value used to find the position in the
`tile library lookup table`, which will be referred to as the `map` table from
here on.

The `map` encodes which tile variant and of which phased type the genomic tile is
(heterozygous, homozygous, with gap, without gap, etc.).


The rest of the encoding is similar to CGF v1.  The map and the rest of the meta
information is kept similar.  The biggest difference is the `ABV` section is now
replacedby by the `tile map variable length encoding` (TMLE).



