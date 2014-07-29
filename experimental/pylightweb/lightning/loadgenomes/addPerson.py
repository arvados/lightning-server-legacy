#Add person to current database

from loadgenomes.models import Tile, TileVariant, TileVarAnnotation
import json

def addAnnotations(variant, annotations):
    for annotation in annotations:
        add = True
        if annotation.startswith('hu'):
            add = False
        for already_present in variant.annotations.all():
            if already_present.annotationText == annotation:
                add=False
        t= 'OTHER'
        if 'SNP' in annotation:
            t='SNP'
        if add:
            variant.annotations.create(annotationType=t, trusted=True, annotationText=annotation)

with open('loadgenomes/chr1_band0_s0_e2300000_ext.fj', 'r') as f:
    #Now need to add
    # tilevar = [tilename, length, populationSize, startTag, endTag, sequence]
    tilevar = [0, 0, 0, '', '', '']
    starting = True
    for line in f:
        if line[:3] == '> {' and not starting:
            #savetile
            defaultTile = Tile.objects.get(pk=tilevar[0])
            defaultSTag = defaultTile.startTag
            defaultETag = defaultTile.endTag
            if tilevar[3] == defaultSTag:
                tilevar[3] = ""
            if tilevar[4] == defaultETag:
                tilevar[4] = ""
            variants = defaultTile.variants.all()
            #check to see if the current variant is in variants and if so, add 1 to populationSize
            added = False
            for variant in variants:
                if variant.sequence == tilevar[5]:
                    added = True
                    variant.populationSize += 1
                    variant.save()
                    if len(annotations) > 1:
                        addAnnotations(variant, annotations)
            if not added:
                var = defaultTile.variants.create(reference=False, length=tilevar[1],
                                                  populationSize=tilevar[2], startTag=tilevar[3],
                                                  endTag=tilevar[4], sequence=tilevar[5])
                if len(annotations) > 1:
                    addAnnotations(var, annotations)
            
        if line[:3] == '> {':
            starting = False
            test = json.loads(line[1:])
            tilename = str(test[u'tileID'])
            band, path, tile, variant = tilename.split('.')
            tilename = int(band+path+tile, 16)
            tilevar = [tilename, test[u'n'], 1, str(test[u'startTag']), str(test[u'endTag']), '']
            annotations = test[u'notes']
        elif line != '\n':
            tilevar[5] += line.strip()

            
