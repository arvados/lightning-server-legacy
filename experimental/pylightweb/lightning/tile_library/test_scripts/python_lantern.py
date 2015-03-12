import json
import string

import tile_library.basic_functions as basic_fns

LANTERN_PORT = 8080

population = {
    'person1':[
        ['000.00.0000.0009+4',                                                           '001.00.0000.0000'],
        ['000.00.0000.000a+2',                   '000.00.0002.0001', '000.00.0003.0000', '001.00.0000.0000']
    ],
    'person2':[
        ['000.00.0000.000b+2',                   '000.00.0002.0000+2',                   '001.00.0000.0000'],
        ['000.00.0000.0000', '000.00.0001.0000', '000.00.0002.0000+2',                   '001.00.0000.0000']
    ],
    'person3':[
        ['000.00.0000.0001', '000.00.0001.0000', '000.00.0002.0001', '000.00.0003.0000', '001.00.0000.0000'],
        ['000.00.0000.0002', '000.00.0001.0000', '000.00.0002.0000+2',                   '001.00.0000.0000']
    ],
    'person4':[
        ['000.00.0000.0003', '000.00.0001.0000', '000.00.0002.0002', '000.00.0003.0000', '001.00.0000.0000'],
        ['000.00.0000.0004+2',                   '000.00.0002.0002', '000.00.0003.0000', '001.00.0000.0000']
    ],
    'person5':[
        ['000.00.0000.0005+2',                   '000.00.0002.0000+2',                   '001.00.0000.0000'],
        ['000.00.0000.0006+2',                   '000.00.0002.0001', '000.00.0003.0000', '001.00.0000.0000']
    ],
    'person6':[
        ['000.00.0000.0007+2',                   '000.00.0002.0002', '000.00.0003.0000', '001.00.0000.0000'],
        ['000.00.0000.0008+3',                                       '000.00.0003.0000', '001.00.0000.0000']
    ],
    'person7':[
        ['000.00.0000.000c', '000.00.0001.0000', '000.00.0002.0000+2',                   '001.00.0000.0000'],
        ['000.00.0000.0000', '000.00.0001.0000', '000.00.0002.0001', '000.00.0003.0001', '001.00.0000.0000']
    ]
}

population_index = {
    'person1':[
        [[1, 1, 1, 1],[2]],
        [[1, 1, 2, 3],[4]]
    ],
    'person2':[
        [[1, 1, 2, 2],[3]],
        [[1, 2, 3, 3],[4]]
    ],
    'person3':[
        [[1, 2, 3, 4],[5]],
        [[1, 2, 3, 3],[4]]
    ],
    'person4':[
        [[1, 2, 3, 4],[5]],
        [[1, 1, 2, 3],[4]]
    ],
    'person5':[
        [[1, 1, 2, 2],[3]],
        [[1, 1, 2, 3],[4]]
    ],
    'person6':[
        [[1, 1, 2, 3],[4]],
        [[1, 1, 1, 2],[3]]
    ],
    'person7':[
        [[1, 2, 3, 3],[4]],
        [[1, 2, 3, 4],[5]]
    ]
}

def sample_position_variant(sub_pop, position_list):
    result = {}
    for person in sub_pop:
        result[person] = [[] for phase in population[person]]
        for position in position_list:
            if '-' in position:
                raise NotImplementedError("Currently do not support ranges")
            path, version, step = position.split('+')[0].split('.')
            position_int = int(version+path+step,16)
            version, path, step = basic_fns.get_position_ints_from_position_int(position_int)
            start_index = step
            if len(position.split('+')) > 1:
                end_index = start_index + int(position.split('+')[1],16) - 1
            else:
                end_index = start_index
            for phase in range(len(result[person])):
                try:
                    start = population_index[person][phase][path][start_index] - 1
                except IndexError:
                    start = 5
                try:
                    end = population_index[person][phase][path][end_index]
                except IndexError:
                    end = 5
                result[person][phase].extend(population[person][phase][start:end])
    return result

def lantern_application(environ, start_response):
    method = environ['REQUEST_METHOD']
    if method == 'POST':
        try:
            request_body_size = int(environ['CONTENT_LENGTH'])
            request_body = environ['wsgi.input'].read(request_body_size)
        except (TypeError, ValueError) as e:
            status = '400 Client Error'
            response_headers =  [('Content-type', 'text/plain')]
            start_response(status, response_headers)
            return json.dumps({'Type':'failed', 'Message':str(e)})
        try:
            request_body = json.loads(request_body)
            if request_body['Type'] == "system-info":
                status = '200 OK'
                response_headers =  [('Content-type', 'text/plain')]
                start_response(status, response_headers)
                return json.dumps({
                    'Type': 'success',
                    'Message':'system-info',
                    'LanternVersion': '0.0.3',
                    'LibraryVersion':'complicated-library',
                    'TileMapVersion':'',
                    'CGFVersion':'',
                    'Stats':'None',
                    'SampleId':population.keys()
                })
            elif request_body['Type'] == "sample-position-variant":
                if request_body['SampleId'] == []:
                    sub_pop = population.keys()
                else:
                    sub_pop = request_body['SampleId']
                result = sample_position_variant(sub_pop, request_body['Position'])
                status = '200 OK'
                response_headers =  [('Content-type', 'text/plain')]
                start_response(status, response_headers)
                return json.dumps({
                    'Type': 'success',
                    'Message':'sample_position_variant',
                    'Result': result
                })
            else:
                status = '500 Server Error'
                response_headers =  [('Content-type', 'text/plain')]
                start_response(status, response_headers)
                return json.dumps({'Type':'failed', "Message":"Only serves 'system-info' and 'sample-position-variant' queries"})
        except Exception as e:
            status = '500 Server Error'
            response_headers = [('Content-type', 'text/plain')]
            start_response(status, response_headers)
            return json.dumps({'Type':'failed', "Message":str(e)})
    status = '405 Client Error'
    response_headers = [('Content-type', 'text/plain')]
    start_response(status, response_headers)
    return json.dumps({'Type':'failed', "Message":"Only supports POST requests"})

"""
#httpd = make_server('', LANTERN_PORT, lantern_application)


import python_lantern
from wsgiref.simple_server import make_server
httpd = make_server('', python_lantern.LANTERN_PORT, python_lantern.lantern_application)
httpd.serve_forever()


httpd.shutdown()
"""
