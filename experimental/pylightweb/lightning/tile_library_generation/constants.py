SUPPORTED_ASSEMBLIES = {}
### ASSEMBLY parsing from TileLocusAnnotation once GenomeVariant can support multiple assemblies
#for assembly_int, name in TileLocusAnnotation.SUPPORTED_ASSEMBLY_CHOICES:
#    name1, name2 = name.split('/')
#    SUPPORTED_ASSEMBLIES[name1] = assembly_int
#    SUPPORTED_ASSEMBLIES[name2] = assembly_int
SUPPORTED_ASSEMBLIES = {'hg19':19, 'GRCh37':19}
