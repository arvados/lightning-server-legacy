# all the imports
import os, sys, string
import json
from flask import Flask, request, session, g, redirect, url_for, \
     abort, render_template, flash
from contextlib import closing
from flask.ext.sqlalchemy import SQLAlchemy as sqla
import numpy as np


try: #we are deploying locally with python
    from databaseconfig import secretkey, username, password
    SECRET_KEY, USERNAME, PASSWORD = secretkey, username, password
    DEBUG = True
except ImportError: #we are running foreman or on heroku
    pass
    #SECRET_KEY = os.environ.get('SECRETKEY') 
    #USERNAME = os.environ.get('USERNAME')
    #PASSWORD = os.environ.get('PASSWORD')
    #DEBUG = False

# create our little application :)

app = Flask(__name__)
app.config.from_object(__name__)
#app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config.from_pyfile('databaseconfig.py')
db = sqla(app)


#hardcoded lists of population, genome, chromosome for now
populations = ['Personal Genome Project']
foo = os.path.dirname(os.path.abspath(__file__)) + '/phasedNPY/numpy_abvs'
bar = os.getcwd()
if DEBUG: print foo, 'bar', bar
npyfnames = [s[:-4] for s in os.listdir(foo) if s.endswith('.npy')]
npyfnames.sort()
#people = "\n".join(map(lambda x: str(x), abvfnames))
people = list(set([ foo.split('_')[0] for foo in npyfnames ]))  #strip out _phase information
people.sort()
genomes = ['hg19']
wonkychrom = 26 

def listchromosomes():
#    chromosomes = []
#    cursor = g.db.execute('SELECT DISTINCT chromosome FROM tile_library_tilelocusannotation')
#    row = cursor.fetchall()
#    for i in range(len(row)):
#        chromosomes.append(row[i][0])
#    if wonkychrom in chromosomes:
#        #get out the chromsomenames
#        cursor = g.db.execute('SELECT DISTINCT chromosome_name FROM tile_library_tilelocusannotation')
#        row = cursor.fetchall()
#        for i in range(len(row)):
#            chromosomes.append(row[i][1])
#        chromosomes = filter(None, chromosomes)
#        chromosomes.remove(wonkychrom)
#    chromosomes.sort()
    chromosomes = range(1, 26)
    return chromosomes

#this is really dumb. there has to be a python library for b64 that does this already
def a2base64index(foochar):
    std_base64chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
    b64 = range(64)
    lookup = dict(zip(std_base64chars,b64))
    index = lookup[foochar]
    return index #maps D to 3, etc.

def findtilevar(genome, path, step, numtiles):
    fname = './phasedNPY/numpy_abvs/' + genome + '.npy'
    TOCfname = './phasedNPY/path_lengths_TOC.npy'
    pathstart = None 
    #with np.load(TOCfname) as TOC:
    TOC = np.load(TOCfname)
    if DEBUG: print 'HEX finding tile variant, genome: ', genome, ', path: ', path, ', step: ', step,
    path = int(path, 16)
    step = int(step, 16)
    if DEBUG: print 'INT finding tile variant, genome: ', genome, ', path: ', path, ', step: ', step,
    pathstart = int(TOC[path])
    #if DEBUG: print 'finding tile variant, genome: ', genome, ', path: ', path, ', step: ', step, ', pathstart: ', pathstart 
    f = np.load(fname)
    #with np.load(fname) as f: ##TODO: will break? if fname does not exist. we should raise useful error mesage here.
    #tile = f[pathstart]
    var = f[int(pathstart+step):int(pathstart+step)+numtiles] #retrieve exactly two tiles
    if DEBUG: print 'finding tile variant, genome: ', genome, ', path: ', path, ', step: ', step,
    var = [int(foo) for foo in var]
    return var #this is -1,0, 1, ....

def findseq(tilevar, tile_id):
    if tilevar == -1:
        return False, 'No call'
    #elif tilevar == '#':
    #    return False, 'No data available (lost in encoding as ABV file)' 
    elif tilevar == 0:
        tilevarname = int(tile_id + '000', 16)
#    #at some point, need to deal with "complex" cases
    else: #okay, so convert to base 64 key, and then subtract 2, then append to the tile_id as 3 digits (pad with zero)
        #foo =  a2base64index(tilevar)-2
        foo = tilevar 
        tilevarname = tile_id + str(foo).zfill(3)
        tilevarname = int(tilevarname, 16)
    cursor = g.db.execute('SELECT * FROM tile_library_tilevariant WHERE %s = tile_variant_name', tilevarname)
    #cursor = g.db.execute('SELECT * FROM tile_library_tilevariant WHERE %s = variant_value', tile_id)
    row = cursor.fetchone()
    if row == None:
        msg = 'Error: Could not parse genome in database at this location. Please email the maintener with your query parameters. '
        return None, msg #this code needs to be refactored, in the meantime, 3rd possible state!
    seq = row['sequence']
    return True, seq

def findallele(tile_id, tilevars, coordinate, begin_ints, lenseqbases):
    foundseq, msg = findseq(tilevars[0], tile_id)
    if DEBUG: print 'foundseq, msg', foundseq, msg
    if foundseq == None:
        return None, msg
    if not foundseq:
        return False, msg
    else:
        seq = msg
        index = coordinate - begin_ints[0]
        if DEBUG: print 'index, coordinate, begin_ints', index, coordinate, begin_ints
        if lenseqbases <= len(seq[index:]): #if search seq fits in one tile 
            seqbases = seq[index:index+lenseqbases]
            if DEBUG: print 'searchseq fit on one tile', lenseqbases, len(seq[index:])
        else: #otherwise, we read the next tilevar and append to our current list of seqbases
            seqbases = seq[index:begin_ints[1]]
            tile_id = format(int(tile_id, 16)+1, 'x')
            if DEBUG: print 'tile_id +1', tile_id
            foundseq, msg = findseq(tilevars[1], tile_id) #the next tile_id, one step up
            if foundseq == None:
                return None, msg
            elif not foundseq:
                return False, msg
            else:
                #remove the parts that are overlapping, aka uppercase
                seq = msg.lstrip(string.uppercase)
                num_addtl = lenseqbases - len(seqbases)
                seq = seq[:num_addtl]
                if DEBUG: print 'two tiles', lenseqbases, coordinate, num_addtl, seqbases, seq, msg
                seqbases += seq
    return True, seqbases

def findtileid(search_coord, search_chrom, numtiles):
    try:
        int(search_chrom)
        iswonky = False
    except ValueError:
        iswonky = True
    if iswonky:
        cursor = g.db.execute('SELECT * FROM tile_library_tilelocusannotation WHERE %s >= begin_int AND %s < end_int AND chromosome = %s AND chromosome_name = %s LIMIT 1', [search_coord, search_coord, wonkychrom, search_chrom])
        row = cursor.fetchone()
    else:
        search_chrom_name = ''
        cursor = g.db.execute('SELECT * FROM tile_library_tilelocusannotation WHERE %s >= begin_int AND %s < end_int AND chromosome = %s LIMIT 1', [search_coord, search_coord, search_chrom])
        row = cursor.fetchone()
    if row == None:
        return None, None
    #if DEBUG: print 'tile_id before conversion to hex: ', row['tile_id']
    tile_id = format(row['tile_id'], 'x').zfill(9) #1c4000002, padded out to 9 digits
    #if DEBUG: print 'tile_id after conversion to hex: ', tile_id 
    begin_ints = []
    begin_ints.append(row['begin_int'])
    for i in range(1, numtiles):
        secondid = int(row['id'])+i
        cursor = g.db.execute('SELECT * FROM tile_library_tilelocusannotation WHERE %s = id LIMIT 1', [secondid])
        row = cursor.fetchone()
        begin_ints.append(row['begin_int'])
    return tile_id, begin_ints

def search(search_pop, search_gen, search_chrom, search_coord, search_allele, numtiles):
    flashmsg = None
    msg = {}
    #msg['debug'] = False 

    #Form Validation
    valid_chars = set('actgdi')
    if not search_allele or not search_coord:
        msg['msg'] = 'Error: You must fill out both the "Coordinate" and "Allele" fields.'
        return flashmsg, msg 
    if not set(search_allele.lower()).issubset(valid_chars):
        msg['msg'] = 'Error: Allele must consist only of the characters A,C,T,G,D, or I (case-insensitive). You searched for: ' + search_allele
        return flashmsg, msg 
    try:
        search_coord = int(search_coord)
    except ValueError:
        msg['msg'] = 'Error: Search coordinate must be an integer'
        return flashmsg, msg 
    lenseqbases = len(search_allele)
    if lenseqbases > 248:
        msg['msg'] = 'Error: Maximum search length is 248 seqbases.'
        return flashmsg, msg 

    #Begin Search
    tile_id, begin_ints = findtileid(search_coord, search_chrom, numtiles)
    if tile_id == None:
        msg['msg'] = 'Error: Is your coordinate valid? No allele(s) found at the coordinate ' + str(search_coord) + ' on chromosome ' + \
            str(search_chrom) + ' with reference genome ' + search_gen + ' for at least one of the genomes in this population.'
        return flashmsg, msg 

    path = tile_id[:3] #first three digits
    step = tile_id[-4:] #last four digits
    if DEBUG: print '!!!!!tile_id', tile_id

    count = 0
    debugmsg = []
    msg['tmpjson'] = []
    for abv in npyfnames:
        #hardcoded, we search across at most 2 tiles right now
        tilevars = findtilevar(abv, path, step, numtiles)
        foundallele, seqbases = findallele(tile_id, tilevars, search_coord, begin_ints, lenseqbases)
        listvars = 'abv, path, step, tilevars, seqbases, tile_id, begin_ints, lenseqbases\n'
        debuginfo = [abv, path, step, tilevars, seqbases, tile_id, begin_ints, lenseqbases]
        debugmsg.append(debuginfo)
        if foundallele == None:
            msg['msg'] = seqbases 
            count = None
            #return flashmsg, msg
        elif not foundallele:
            pass
            #msg['msg'] = seqbases 
        else:
            if (seqbases.lower() == search_allele.lower()):
                count += 1
        name = abv.split("_")[0]
        phase = abv.split("_")[1][-1]
        msg['tmpjson'].append({'name':name, 'phase': phase, 'tilevars': tilevars}) 
    msg['begin_ints'] = begin_ints
    if count == None:
        flashmsg = 'Error!'
    elif count != 0:
        flashmsg = True 
    else:
        flashmsg = False 
    #msg = tile_id, ' ', path, ' ', step, ' ', tilevar, ' ', allele, ' ', flashmsg
    info = 'You searched for: allele "'+ search_allele + '" at coordinate "' + str(search_coord) + \
            '" (in chr ' + str(search_chrom) + ', ' + search_gen + ', ' + search_pop + '). \n\n' 
    if 'msg' in msg:
        msg['msg'] += info
    else:
        msg['msg'] = info

    if DEBUG:
        debugmsg = listvars + "\n".join(map(lambda x: str(x), debugmsg))
        msg['debug'] = debugmsg
    return flashmsg, msg

def connect_db():
    return db.engine.connect()

@app.before_request
def before_request():
    g.db = connect_db() 

def init_db():
    pass

@app.teardown_request
def teardown_request(exception):
    db = getattr(g, 'db', None)
    if db is not None:
        g.db.close()

@app.route('/')
def show_search():
    chromosomes = listchromosomes()
    return render_template('search.html', populations=populations, genomes=genomes, chromosomes=chromosomes, people=people)

@app.route('/tmpjson/<int:searchcoord>', methods=['GET'])
def tmpjson(searchcoord):
    #foo = 'a' * (45412650-45409011)
    foo = 'aaaa'
    #flashmsg, msg = search("Personal Genome Project", "hg19", "19", "45409011", foo, 20)
    flashmsg, msg = search("Personal Genome Project", "hg19", "19", searchcoord, foo, 20)
    tiles = str(msg['tmpjson'])
    begin_ints = str(msg['begin_ints'])
    js = tiles
    #js = "var tiles = " + tiles + ";"
    #js += "var begin_ints = " + begin_ints + ";"
    return json.dumps(msg['tmpjson']) 

@app.route('/botsearch')
def botsearch():
    search_pop, search_gen, search_chrom, search_coord, search_allele = \
            request.args.get('pop'), request.args.get('refgen'), request.args.get('chrom'), request.args.get('coord'), request.args.get('allele') 
    flashmsg, msg = search(search_pop, search_gen, search_chrom, search_coord, search_allele, 2)
    return render_template('botsearch.html', flashmsg=flashmsg)


@app.route('/search', methods=['GET','POST'])
def search_entries():
    if request.method == 'GET':
        return show_search()
    else:
        search_pop, search_gen, search_chrom = \
                request.form['search_pop'], request.form['search_gen'], request.form['search_chrom']
        search_coord = request.form['search_coord']
        search_allele = request.form['search_allele']
        flashmsg, msg = search(search_pop, search_gen, search_chrom, search_coord, search_allele, 2)
        if flashmsg == None:
            flash(msg['msg'])
        else:
            flash(flashmsg)

        chromosomes = listchromosomes()
        return render_template('search.html', msg=msg, flashmsg=flashmsg, populations=populations, genomes=genomes, prev_pop=search_pop, \
        prev_gen=search_gen, chromosomes=chromosomes, prev_chrom = int(search_chrom), coordinate=search_coord, allele = search_allele, people=people)

@app.route('/people')
def show_people():
    return render_template('people.html', people=people, npyfnames=npyfnames)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
