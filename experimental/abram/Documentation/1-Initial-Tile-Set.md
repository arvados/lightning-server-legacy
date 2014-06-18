Creating The Initial Tile Set
=============================

0. Overview
--------

In what follows, we will be using hg19 (GRCh37) to build the
initial tile set.

First we have to download the relevant files we will need:

  - [wgEncodeMapabilityAlign24mer](http://hgdownload-test.cse.ucsc.edu/goldenPath/hg19/encodeDCC/wgEncodeMapability/release1/wgEncodeCrgMapabilityAlign24mer.bw.gz)
  - [hg19 reference genome chromosomes in Fasta format](http://hgdownload.cse.ucsc.edu/goldenpath/hg19/chromosomes/)
  - [hg19 reference genome in 2bit format](http://hgdownload.soe.ucsc.edu/goldenPath/hg19/bigZips/hg19.2bit)
  - [hg19 CytoBand file](http://hgdownload.cse.ucsc.edu/goldenpath/hg19/database/cytoBand.txt.gz)

We will also need some tools to aid in processing these and other files:

  - [bigWigToBedGraph](http://hgdownload.cse.ucsc.edu/admin/exe/linux.x86_64/bigWigToBedGraph)
  - [twoBitToFa](http://hgdownload.cse.ucsc.edu/admin/exe/linux.x86_64/twoBitToFa)

The **wgEncodeMapabilityAlign24mer** contains a value for each 24mer in the hg19 reference as to how often it appears.  We will use
this to pick an initial tag set, picking each tag to be as unique as possible in the reference genome.  The **CytoBand** file has
band boundaries that we will use to create our band boundaries.  The hg19 will be used to create the initial tile set which we will
extend with other PGP participants later on.

Though strictly speaking we could construct the Fasta files ourselves from the 2bit representation (and vice versa), it's good
to have them lying around if we have the space in case we need to skip around between representations.

The files are large.  The **wgEncodeMapabilityAlign24mer** is around 5G, the hg19 Fasta files are around 3.1G and the **hg19.2bit** file is around 800M.
We will be generating large intermediate files, so make sure you have plenty of space.

As a quick overview, we will follow roughly these steps:

  - Convert the 24mer **wgEncodeMapabilityAlign24mer** BigWig file to a BedGraph file.
  - Use the CytoBand files to chop the BedGraph file into smaller BedGraph files, restricted to the appropriate band.
  - Create a tag set from the chopped BedGraph files.
  - Use the tag set to create the tile sequences from the hg19 reference genome.

At the end, we should have a tile set that covers the hg19 reference genome.  Eventually, we will extend
the tile set created here with the pool of genomes from the Personal Genomes Project (PGP), but that's getting
ahead of ourselves.

To download all the tools, run the 'setup.sh' script:

    $ setup.sh

1. Converting and Chopping wgEncodeMapabilityAlign24mer
-------------------------------------------------------

After all the tools are downloaded, you will need to run the program **createBandBedGraph**.  If it's not compiled, compile the Go program:

    $ go build createBandBedGraph.go

and execute it:

    $ createBandBedGraph

This should take a while, generating 863 files, each ranging from 0-160M.  The following files should be produced:



Once we have the chopped BedGraph files, we can now walk through each one and find our tag sets, generating Fastj files from the reference genome along the way.






