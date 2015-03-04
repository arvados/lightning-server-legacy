from cgi import parse_qs, escape
import json

LANTERN_PORT = 8080

population = {
    'person1':[
        ['000.00.0000.0009+4'],
        ['000.00.0000.000a+2', '000.00.0000.0001', '000.00.0000.0000']
    ],
    'person2':[
        ['000.00.0000.000b+2', '000.00.0000.0000+2'],
        ['000.00.0000.0000', '000.00.0000.0000', '000.00.0000.0000+2']
    ],
    'person3':[
        ['000.00.0000.0001', '000.00.0000.0000', '000.00.0000.0001', '000.00.0000.0000'],
        ['000.00.0000.0002', '000.00.0000.0000', '000.00.0000.0000+2']
    ],
    'person4':[
        ['000.00.0000.0003', '000.00.0000.0000', '000.00.0000.0002', '000.00.0000.0000'],
        ['000.00.0000.0004+2', '000.00.0000.0002', '000.00.0000.0000']
    ],
    'person5':[
        ['000.00.0000.0005+2', '000.00.0000.0000+2'],
        ['000.00.0000.0006+2', '000.00.0000.0001', '000.00.0000.0000']
    ],
    'person6':[
        ['000.00.0000.0007+2', '000.00.0000.0002', '000.00.0000.0000'],
        ['000.00.0000.0008+3', '000.00.0000.0000']
    ]
}

def lantern_application(environ, start_response):
    response_body = json.dumps({'SampleId':population.keys()})
    status = '200 OK'
    response_headers =  [('Content-type', 'text/plain')]
    start_response(status, response_headers)
    return response_body
#httpd = make_server('', LANTERN_PORT, lantern_application)
#from wsgiref.simple_server import make_server
#httpd = make_server('', python_lantern.LANTERN_PORT, python_lantern.lantern_application)
#httpd.serve_forever()
#httpd.shutdown()
