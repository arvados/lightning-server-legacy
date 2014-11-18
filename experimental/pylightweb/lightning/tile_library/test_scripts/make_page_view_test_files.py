#make test files for page_view_test
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
        tile_vars = [{'vars':3, 'lengths':[250,252,250]}, #1
                     {'vars':2, 'lengths':[248,248]}, #2
                     {'vars':3, 'lengths':[200,250,300]}, #3
                     {'vars':1, 'lengths':[250]}, #4
                     {'vars':1, 'lengths':[199]}, #5
                     {'vars':4, 'lengths':[150,250,200,220]}, #6
                     {'vars':4, 'lengths':[250,250,250,251]}, #7
                     {'vars':1, 'lengths':[1200]}, #8
                     {'vars':3, 'lengths':[300,300,301]}, #9
                     {'vars':2, 'lengths':[264,265]}, #10
                     {'vars':6, 'lengths':[251,250,250,251,252,249]}, #11
                     {'vars':2, 'lengths':[275,276]}, #12
                     {'vars':2, 'lengths':[277,277]}, #13
                     {'vars':1, 'lengths':[267]}, #14
                     {'vars':1, 'lengths':[258]}, #15
                     {'vars':3, 'lengths':[248,248,248]}, #16
                     {'vars':1, 'lengths':[250]},
                     ]
        for j in range(17):
            tile_file.write(string.join([str(j), start, end, now+'\n'], ','))
            mk_tilevars(tile_vars[j]['vars'], tile_vars[j]['lengths'], start, end, j, tile_var_file)
            start = end
            start, end = mk_tile(start_tag=start)
        
        
