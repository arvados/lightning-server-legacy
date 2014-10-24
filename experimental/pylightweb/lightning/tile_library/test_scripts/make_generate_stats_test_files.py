#make test files for generate_stats
import random
import datetime
import hashlib
import string
import tile_library.basic_functions as basic_fns
import tile_library.functions as fns

now = datetime.datetime.now()
now = str(now)

def mk_genome_seq(length, uppercase=True):
    if uppercase:
        choices = ['A','G','C','T']
    else:
        choices = ['a','g','c','t']
    s = ''
    for i in range(length):
        s += random.choice(choices)
    return s

def mk_tile(start_tag=None, end_tag=None):
    if start_tag == None:
        start_tag = mk_genome_seq(24)
    if end_tag == None:
        end_tag = mk_genome_seq(24)
    return start_tag, end_tag

def mk_tilevars(num_vars, lengths, start_tag, end_tag, tile_int, out):
    assert len(lengths) == num_vars
    for i in range(num_vars):
        tile_hex = string.join(basic_fns.convert_position_int_to_position_hex_str(tile_int), "")
        tile_hex += hex(i).lstrip('0x').zfill(3)
        tile_var_int = int(tile_hex, 16)
        length = lengths[i]
        randseq_len = length - 24*2
        seq = start_tag
        seq += mk_genome_seq(randseq_len, uppercase=False)
        seq += end_tag
        digestor = hashlib.new('md5', seq)
        out.write(string.join([str(tile_var_int),str(i), str(length), digestor.hexdigest(),
                               now, now, seq,'""','""',str(tile_int)+"\n"], ","))
                  


with open('tile.csv', 'wb') as tile_file:
    with open('tilevariant.csv', 'wb') as tile_var_file:
        #make path 0
        start, end = mk_tile()
        tile_vars = [{'vars':3, 'lengths':[250,252,250]},
                     {'vars':2, 'lengths':[248,248]},
                     {'vars':3, 'lengths':[200,250,300]},
                     {'vars':1, 'lengths':[250]},
                     {'vars':1, 'lengths':[199]}]
        for j in range(5):
            tile_file.write(string.join([str(j), start, end, now+'\n'], ','))
            mk_tilevars(tile_vars[j]['vars'], tile_vars[j]['lengths'], start, end, j, tile_var_file)
            start, end = mk_tile(start_tag=start)
        #make path 1
        next_tile_int, foo = fns.get_min_position_and_tile_variant_from_path_int(1)
        start, end = mk_tile()
        tile_file.write(string.join([str(next_tile_int), start, end, now+'\n'], ','))
        mk_tilevars(5, [248,248,248,248,248], start, end, next_tile_int, tile_var_file)
        #make chr2 path
        next_tile_int, foo = fns.get_min_position_and_tile_variant_from_chromosome_int(2)
        start, end = mk_tile()
        tile_vars = [{'vars':4, 'lengths':[1000,1100,1050,1040]},
                     {'vars':2, 'lengths':[200,250]}]
        for j in range(2):
            tile_file.write(string.join([str(next_tile_int+j), start, end, now+'\n'], ','))
            mk_tilevars(tile_vars[j]['vars'], tile_vars[j]['lengths'], start, end, next_tile_int+j, tile_var_file)
            start, end = mk_tile(start_tag=start)
        
