#!/usr/bin/python

import cgi
import httplib
import urllib
import urllib2
import re
import sys
import json
import time

import psycopg2

import config

headers = [('Content-Type', 'text/plain')]

def status(code):
    if code not in httplib.responses:
        code = 500
    return "%d %s" % (code, httplib.responses[code])

def error(code, message):
    return status(code), headers, message


def exists(dataset):
    conn = psycopg2.connect(config.connect)
    cur = conn.cursor()

    cur.execute('select count(*) from datasets where dataset_id = %s;',
                (dataset,))
    n = int(cur.fetchone()[0])

    cur.close()
    conn.close()

    return n > 0


# GET handlers

def diff(dataset, command):
    if len(command) > 1:
        return error(400, 'Malformed syntax.')

    conn = psycopg2.connect(config.connect)
    cur = conn.cursor()

    if len(command) == 0:
        cur.execute('select data_id from data where dataset_id = %s ' +
                    'order by updated desc limit 1;',
                    (dataset,))
        stamp = cur.fetchone()[0]

        cur.close()
        conn.close()
        
        if stamp is None:
            return error(404, 'No such dataset.')
        else:
            return status(200), headers, str(stamp)
    else:
        try:
            int(command[0])
        except ValueError:
            return error(400, 'Invalid timestamp.')

        cur.execute("select count(*) from data " +
                    "where dataset_id = %s and updated > " +
                    "(select updated from data where " +
                    "dataset_id = %s and data_id = %s);",
                    (dataset, dataset, command[0]))
        c = cur.fetchone()[0]

        cur.close()
        conn.close()

        if c is None:
            return error(404, 'No such dataset.')
        else:
            return status(200), headers, ("Y" if c else "N")

def tags(dataset, command):
    if len(command) > 0:
        return error(400, 'Malformed syntax.')
    
    conn = psycopg2.connect(config.connect)
    cur = conn.cursor()

    cur.execute('select tag from data where dataset_id = %s and ' +
                'tag is not null order by updated;', (dataset,))
    tags = cur.fetchall()

    cur.close()
    conn.close()

    return status(200), headers, '\n'.join(map(lambda n: n[0], tags))

def jsonh(dataset, command):
    conn = psycopg2.connect(config.connect)
    cur = conn.cursor()

    ds = {}

    cur.execute('select title, xlabel, ylabel from datasets ' +
                'where dataset_id = %s;', (dataset,))
    ret = cur.fetchone()
    ds['title'] = ret[0]
    ds['xlabel'] = ret[1]
    ds['ylabel'] = ret[2]

    cur.execute('select updated, tag, data from data ' +
                'where dataset_id = %s order by updated desc limit 1;',
                (dataset,))
    ret = cur.fetchone()
    ds['updated'] = time.mktime(ret[0].timetuple())
    ds['tag'] = ret[1]
    ds['data'] = ret[2]

    cur.close()
    conn.close()

    return status(200), headers, json.dumps(ds)

def py(dataset, command):
    if len(command) > 0:
        try:
            timestamp = int(command[0])
        except ValueError:
            return error(400, 'Bad timestamp.')
    else:
        timestamp = None

    conn = psycopg2.connect(config.connect)
    cur = conn.cursor()

    if timestamp is None:
        cur.execute('select data from data where dataset_id = %s '
                    'order by updated desc limit 1;', (dataset,))
    else:
        cur.execute('select data from data where dataset_id = %s '
                    'and data_id = %s;',
                    (dataset, float(command[0]) / 100))

    data = cur.fetchone()

    cur.close()
    conn.close()

    if not data:
        return error(404, 'No such dataset.')
    else:
        return status(200), headers, data[0]

def kst(dataset, command):
    return error(501, "TODO")

def field(dataset, fname):
    conn = psycopg2.connect(config.connect)
    cur = conn.cursor()
    cur.execute('select %s from datasets where dataset_id = %%s;' % fname,
                (dataset,))
    fld = cur.fetchone()[0]
    cur.close()
    conn.close()
    if not fld:
        return error(404, '%s not defined for this dataset.' % fname)
    else:
        return status(200), headers, fld

get_handlers = {'diff': diff,
                'tags': tags,
                'json': jsonh,
                'py': py,
                'kst': kst,
                'title': lambda d, _: field(d, 'title'),
                'x-label': lambda d, _: field(d, 'xlabel'),
                'y-label': lambda d, _: field(d, 'ylabel')}


# POST handlers

def create(env):
    form = cgi.FieldStorage(fp=env['wsgi.input'], environ=env)
    if 'data' not in form:
        return error(400, 'No data received.')

    data = ';'.join(form.getlist('data'))

    title = form.getfirst('title', None)
    xlabel = form.getfirst('x-label', None)
    ylabel = form.getfirst('y-label', None)

    conn = psycopg2.connect(config.connect)
    cur = conn.cursor()

    cur.execute('insert into datasets (title, xlabel, ylabel) ' +
                'values (%s, %s, %s) returning dataset_id;',
                (title, xlabel, ylabel))
    dataset = cur.fetchone()[0]
    cur.execute('insert into data (dataset_id, data) values (%s, %s) '
                "returning data_id;",
                (dataset, data))
    updated = int(cur.fetchone()[0])
    conn.commit()

    cur.close()
    conn.close()

    return status(200), headers, "%d,%d" % (dataset, updated)

def load(env):
    """Loads a dataset from our RDF server."""
    form = cgi.FieldStorage(fp=env['wsgi.input'], environ=env)
    if 'uri' not in form:
        return error(400, 'Need URI.')
    uri = form.getfirst('uri')

    try:
        r = urllib2.urlopen(uri)
        xml = r.read()
        r.close()
    except Exception, e:
        return error(404, 'Cannot into RDF. ' + str(e))

    m = re.search('<rdfs:label>(.*?)</rdfs:label>', xml)
    title = None if not m else m.group(1)
    m = re.search('<ns1:x-label>(.*?)</ns1:x-label>', xml)
    xlabel = None if not m else m.group(1)
    m = re.search('<ns1:y-label>(.*?)</ns1:y-label>', xml)
    ylabel = None if not m else m.group(1)

    m = re.search('<ns1:data>(.*?)</ns1:data>', xml)
    if m is None:
        return error(500, 'Malformed RDF/XML: missing data.')
    else:
        data = m.group(1)

    conn = psycopg2.connect(config.connect)
    cur = conn.cursor()

    cur.execute('insert into datasets (title, xlabel, ylabel) ' +
                'values (%s, %s, %s) returning dataset_id;',
                (title, xlabel, ylabel))
    dataset = cur.fetchone()[0]
    cur.execute('insert into data (dataset_id, data) values (%s, %s);',
                (dataset, data))
    conn.commit()

    cur.close()
    conn.close()

    return status(200), headers, str(dataset)

def update(dataset, env):
    form = cgi.FieldStorage(fp=env['wsgi.input'], environ=env)

    conn = psycopg2.connect(config.connect)
    cur = conn.cursor()

    cur.execute('select count(*) from datasets where dataset_id = %s;',
                (dataset,))
    if not cur.fetchone()[0]:
        return error(404, 'No such dataset.')

    title = form.getfirst('title', None)
    if title is not None:
        cur.execute('update datasets set title = %s ' +
                    'where dataset_id = %s;',
                    (title, dataset))
    xlabel = form.getfirst('x-label', None)
    if xlabel is not None:
        cur.execute('update datasets set xlabel = %s ' +
                    'where dataset_id = %s;',
                    (xlabel, dataset))
    ylabel = form.getfirst('y-label', None)
    if title is not None:
        cur.execute('update datasets set ylabel = %s ' +
                    'where dataset_id = %s;',
                    (ylabel, dataset))

    data = ';'.join(form.getlist('data'))
    if not data:
        cur.execute('select data_id from data where dataset_id = %s ' +
                    'order by updated limit 1;',
                    (dataset,))
    else:
        cur.execute("insert into data (dataset_id, data) values (%s, %s) " +
                    "returning data_id;",
                    (dataset, data))
    updated = int(cur.fetchone()[0])
    conn.commit()

    cur.close()
    conn.close()
    
    return status(200), headers, str(updated)

def tag(dataset, env, command):
    form = cgi.FieldStorage(fp=env['wsgi.input'], environ=env)
    if 'tag' not in form:
        return error(400, 'No tag named.')
    tag = form.getfirst('tag')

    conn = psycopg2.connect(config.connect)
    cur = conn.cursor()

    if len(command) > 0:
        cur.execute('update data set tag = %s where dataset_id = %s ' +
                    'and data_id = %s returning data_id;',
                    (tag, dataset, command[0]))
    else:
        cur.execute('update data set tag = %s '
                    'where dataset_id = %s and data_id = '
                    '(select max(data_id) from data where dataset_id = %s)' +
                    'returning data_id;',
                    (tag, dataset, dataset))
    data_id = cur.fetchone()

    conn.commit()
    cur.close()
    conn.close()

    if data_id is None:
        return error(404, 'No such data.')
    else:
        return status(200), headers, str(data_id[0])

def rewind(dataset, env, _):
    form = cgi.FieldStorage(fp=env['wsgi.input'], environ=env)

    if 'tag' in form:
        q = 'tag = %s'
        arg = form.getfirst('tag')
    elif 'timestamp' in form:
        q = 'data_id = %s'
        try:
            arg = int(form.getfirst('timestamp'))
        except ValueError:
            return error(400, 'Invalid timestamp format.')
    else:
        return error(400, 'No tag or timestamp specified.')

    conn = psycopg2.connect(config.connect)
    cur = conn.cursor()

    cur.execute('update data set updated = now() where dataset_id = %s and ' +
                q + ' returning data_id;', (dataset, arg))
    r = cur.fetchone()

    conn.commit()
    cur.close()
    conn.close()

    if r is None:
        return error(404, 'No such data.')
    else:
        return status(200), headers, str(r[0])

post_handlers = {'create': create,
                 'load': load,
                 'update': update,
                 'tag': tag,
                 'rewind': rewind}
