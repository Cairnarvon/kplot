#!/usr/bin/python

import os
import sys

import config
import tools

def run(env, start_response):
    """Main."""
    if 'PATH_INFO' not in env:
        env['PATH_INFO'] = '/'
    path = filter(None, os.path.normpath(env['PATH_INFO']).split('/'))

    if env['REQUEST_METHOD'] == 'GET':
        if len(path) == 0:
            path.append('_')
        
        dataset, path = path[0], path[1:]

        try:
            dataset = int(dataset)
            if not tools.exists(dataset):
                raise ValueError
        except ValueError:
            ret = tools.error(404, "Invalid dataset ID.")
        else:
            if len(path) == 0:
                path.append('json')
            handler, command = path[0], path[1:]
            if handler not in tools.get_handlers:
                ret = tools.error(501, "Didn't understand (sorry).")
            else:
                ret = tools.get_handlers[handler](dataset, command)

    elif env['REQUEST_METHOD'] == 'POST' or env['REQUEST_METHOD'] == 'PUT':
        if len(path) == 0:
            # Create new dataset
            ret = tools.post_handlers['create'](env)
        elif len(path) == 1 and path[0] == 'load':
            # Load from RDF
            ret = tools.post_handlers['load'](env)
        elif len(path) == 1:
            # Update existing dataset
            try:
                dataset = int(path[0])
                if not tools.exists(dataset):
                    raise ValueError
            except ValueError:
                ret = tools.error(404, "Invalid dataset ID.")
            else:
                ret = tools.post_handlers['update'](dataset, env)
        else:
            # Handlers
            dataset, handler, command = path[0], path[1], path[2:]
            try:
                dataset = int(path[0])
                if not tools.exists(dataset):
                    raise ValueError
            except ValueError:
                ret = tools.error(404, "Invalid dataset ID.")
            else:
                if handler in tools.post_handlers:
                    ret = tools.post_handlers[handler](dataset, env, command)
                else:
                    ret = tools.error(400, "Bad request.")

    else:
        # Unsupported action
        ret = tools.error(501, "Didn't understand (sorry).")

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
