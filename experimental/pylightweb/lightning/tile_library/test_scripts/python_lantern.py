from wsgiref.simple_server import make_server
from cgi import parse_qs, escape

LANTERN_PORT = 8080

population = {
    'person1':[
        ['000.00.0000.0000'],
        ['000.00.0000.0001']
    ]
    'person2':[
        ['000.00.0000.0001'],
        ['000.00.0000.0000']
    ]
    'person3':[
        ['000.00.0000.0004'],
        ['000.00.0000.0004']
    ]
    'person4':[
        ['000.00.0000.0000'],
        ['000.00.0000.0000']
    ]
    'person5':[
        ['000.00.0000.0000'],
        ['000.00.0000.0000']
    ]
}

httpd = SocketServer.TCPServer(("localhost",PORT), LanternHandler)

httpd.serve_forever()

httpd.shutdown()

def lantern_application(environ, start_response):
    try:
        request_body_size = int(environ.get('CONTENT_LENGTH', 0))
    except (ValueError):
        request_body_size = 0
    request_body = environ['wsgi.input'].read(request_body_size)
    d = parse_qs(request_body)
    request_type = d.get('Type')
    if request_type == 'system-info':
        sample_ids = population.keys()
    elif request_type == 'sample-position-variant':
        position_range = d.get('Position')
