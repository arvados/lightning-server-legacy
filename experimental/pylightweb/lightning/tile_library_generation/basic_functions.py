def copen( filename, mode ):
    if filename[-3:] == ".gz":
        return gzip.open( filename, mode )
    return open( filename, mode )

def write_line(inp_list, out, num_to_keep=None):
    thingsToJoin = []
    for i, foo in enumerate(inp_list):
        if num_to_keep == None or i < num_to_keep:
            if not foo and type(foo) == str:
                thingsToJoin.append('""')
            else:
                thingsToJoin.append(str(foo))
    thingsToJoin[-1] += '\n'
    out.write(string.join(thingsToJoin, sep=','))

def psql_parsable_json_dump(item_to_convert):
    middle = json.dump(item_to_convert)
    return re.sub('\"', '\\'+'\"', middle)
