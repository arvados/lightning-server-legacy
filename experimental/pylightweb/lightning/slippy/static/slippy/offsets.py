lines = []
with open('offsets.txt', 'r') as f:
    s = 0
    for line in f:
        toappend = ''
        nums = line.split(',')
        for i in nums:
            s += int(i)
            toappend += str(s) + ','
        lines.append(toappend)

with open('iter.txt', 'w') as f:
    f.writelines(lines)
