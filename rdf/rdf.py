#!/usr/bin/python

import os
import sys

import RDF

import config
import tools

if len(sys.argv) > 1:
    # Create
    opts = ', '.join((config.storage.get('options_string', ''), 'new=true'))
    storage = RDF.Storage(storage_name=config.storage['storage_name'],
                          name=config.storage['name'],
                          options_string=opts)

    sparql.sparql('SELECT * WHERE {?person a ?name}')



def run(env, start_response):
    """Main."""
    if 'PATH_INFO' not in env:
        env['PATH_INFO'] = '/'
    path = filter(None, os.path.normpath(env['PATH_INFO']).split('/'))

    ret = tools.status(501), tools.headers['plain'], 'Not implemented (yet?).'

    if env['REQUEST_METHOD'] == 'GET':
        if len(path) == 0:
            # Front page TODO
            pass
        elif path[0].lower() == 'sparql':
            ret = tools.sparql_get(env)
        elif path[0].lower() == 'ontology':
            ret = tools.ontology()
        elif path[0].lower() == 'dataset':
            ret = tools.dataset(path[1:])

    elif env['REQUEST_METHOD'] == 'POST':
        if len(path) == 0:
            ret = tools.status(400), tools.headers['plain'], 'Error'
        elif path[0].lower() == 'sparql':
            ret = tools.sparql_post(env)
        elif path[0].lower() == 'submit':
            ret = tools.submit(env)

    elif env['REQUEST_METHOD'] == 'PUT':
        if path[0].lower() == 'submit':
            ret = tools.submit(env)

    elif env['REQUEST_METHOD'] == 'DELETE':
        # Not supported until authentication gets added TODO
        pass

    else:
        # Unsupported as yet
        pass

    status, headers, content = ret
    start_response(status, headers)
    return content

if __name__ == '__main__':
    if 'REQUEST_METHOD' in os.environ:
        from wsgiref.handlers import BaseCGIHandler
        BaseCGIHandler(sys.stdin, sys.stdout, sys.stderr, os.environ).run(run)
    else:
        from wsgiref.simple_server import WSGIServer, WSGIRequestHandler
        httpd = WSGIServer(('', config.port), WSGIRequestHandler)
        httpd.set_app(run)
        print "Serving HTTP on %s port %s ..." % httpd.socket.getsockname()
        httpd.serve_forever()
