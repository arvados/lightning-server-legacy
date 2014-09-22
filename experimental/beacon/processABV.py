fi = open("./abv1000chars.txt", "w")
data = open("./hu0A4518.abv", "r")
fi.write(data.read(90000))
fi.close()
data.close()


