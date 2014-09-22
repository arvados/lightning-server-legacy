import re
f = open('./abv9000chars.txt', 'r')
d = f.read().split(' ')
print d[0]
print '!!!!!!!!!!!!!!!!!!!\n'
print d[:-1]
#pattern = re.compile('\s[0-9].*\s')
f.close()
