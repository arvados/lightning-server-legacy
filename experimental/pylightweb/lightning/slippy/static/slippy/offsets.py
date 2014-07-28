lines = []
with open('tile_offsets.txt', 'r') as f:
    s = 0
    for line in f:
        toappend = ''
        nums = line.split(',')
        for i in nums:
            toappend += str(s) + ','
            s += int(i)
        lines.append(toappend)

with open('tile_iter.txt', 'w') as f:
    f.writelines(lines)
