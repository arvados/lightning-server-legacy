import os
import shutil

path = "chromosomes/1/"
#os.mkdir(path + "chromosomes")
for dirpath, dirnames, fnames in os.walk(path + "pngs"):
    if len(dirnames) == 0:
        print dirpath
        columnName = dirpath.split('/')[-1]
        for fname in fnames:
            rowName = fname.split('.')[0]
            newname = path + "chromosomes/" + columnName + "_" + rowName + ".png"
            os.rename(dirpath + "/" + fname, newname)
