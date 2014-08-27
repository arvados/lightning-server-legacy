import csv
import sys
import string

newlines = []
with open('hide/hidegene.csv', 'r') as f:
    for line in f:
        pieces = line.split(',')
        newpieces = [thing.strip('"') for thing in pieces]
        if 'None' not in newpieces:
            newlines.append(string.join(newpieces, sep=','))

with open('hide/test.csv', 'w') as f:
    f.writelines(newlines)
        
        
        
