Overview
========

Lightning is a database to store a population of genomes
for ease of queriability, data exchange and standardization.
In addition, Lightning will introduce
a standardized description for genomic data.

Currently, we are in the preliminary research of testing feasability
and getting initial results.  This includes processing data we have
for the 150+ Personal Genomic Project participants and creating
initial libarary files.

This documentation is an attempt to record the process by which
we created Lightning and it's supporting library files.  Concepts
will be introduced and explained as needed.

Lightning is a work in progress and we are actively developing standards
and formats that are subject to change during the course of our
research.

Library File Format Description
-------------------------------

Lightning uses an intermediate format to store genomic data.  These are
represented as 'Lightning tiles'.  A Lightning tile is a genomic sequence
that is braced on either side by 24mer 'tags'.  For example, the following is
a Lightning tile:

    CTTTTTGCCCGCTCAGGCTTTTGCccccccgccgcggctttttgcccccc
    gccgccgctttccccgccgtggctttttacaccctgcccccgcagctttt
    tgcccccaccccgccttggctttttccccgccacggttttttggcccgcc
    gccgccgccgccgccgccgccgcgactttttatccccagccgccgcggct
    ttttgcccccaccccgccgcggcttTCTGCCCAGCCCCCGTCGCCGCGG

Where 'CTTTTTGCCCGCTCAGGCTTTTGC' is the 'start' or 'left' tag and
'TCTGCCCAGCCCCCGTCGCCGCGG' is the 'end' or 'right' tag.

A tile sequence must be at least 250 base pairs long.

A convenient storage format for Lightning tiles is the 'FastJ'
format.  For those familiar with FastQ or Fasta files, the FastJ
format will look familiar.  Here is an example:

    >{"tileID":"285.00.015.000","locus":[{"build":"hg19 chr15 20013562 20013837"}],"n":275,"copy":0,"startTag":"CTGCTCCACCCAAACAAAAGTTCA","endTag":"GTTTTACTGTGAAGATAAATCGTT"}
    CTGCTCCACCCAAACAAAAGTTCAgctctgtgagatgaacgcacccatca
    caaagaagtttctcagaattcttctgtctagtttttaagtggagatattt
    ccttttccaccataggcctcaaagcgctccaaatgtccacttgcagattc
    tacaaaaagagagcttcaagactgctcaaccaaaagaaaggtttaactct
    gtgagatgaacgcacacattagaaagaagtttcccaaaatacttctttct
    aGTTTTACTGTGAAGATAAATCGTT


A FastJ file can consist of multiple sequences, where each start is indicated
by a '>' (greater than) character on the line before it.  The information
on the same line after the '>' is valid JSON and gives information about the
Lightning tile ID and other information.

The motivation behind this format is that a genome can be effectively covered by
a tiling.  For a given population that has high redundancy in their genomic data,
there will be a lot of duplication of tiles, allowing for efficient representation.

In addition, for some agreed upon standard of a Lightning tile set, a common case
is when a genome is completely represented by a tile set, allowing for space efficient
transmission of whole genomes.  In the case a genome does not have portions covered by
a given tile set, space efficiency is still acheived as the only differences from the
standard tile set need to be recorded.

Outline
-------

In what follows, we will go through the steps needed to:

  - choose a tag set
  - create an initial tile set from a given genome reference (we will be using hg19)
  - create a tile set from a complete genome (we will be using a gff file)
  - merge the tile sets to create a superset of the tiles for a standard tile reference library.

We will also discuss annotating the tile sets with appropriate polyphen data and
creating auxiliary structures that will be useful for efficient analysis and queries:

These set of documents are a work in progress.
