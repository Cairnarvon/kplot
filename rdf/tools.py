#!/usr/bin/python

import cgi
import httplib

import rdflib
from mako.template import Template

import config


headers = {'html': [('Content-Type', 'text/html')],
           'plain': [('Content-Type', 'text/plain')],
           'rdf': [('Content-Type', 'application/rdf+xml')]}

def status(code):
    if code not in httplib.responses:
        code = 500
    return "%d %s" % (code, httplib.responses[code])

def get_new_id():
    """Returns a unique ID for a new dataset."""
    # FIXME
    import psycopg2

    conn = psycopg2.connect('dbname=data_db user=koen')
    cur = conn.cursor()

    cur.execute('insert into dids default values returning did;')
    did = cur.fetchone()[0]

    cur.close()
    conn.close()

    return did


# /dataset/<id>

def dataset(path):
    store = rdflib.plugin.get(config.store, rdflib.store.Store)()
    store.open(config.connect)

    ns = rdflib.Namespace(config.datasets)

    g1 = rdflib.ConjunctiveGraph(store)
    g2 = rdflib.Graph()

    for triple in g1.triples((ns[path[0]], None, None)):
        g2.add(triple)

    if len(g2) > 0:
        return status(200), headers['rdf'], g2.serialize(format='xml')
    else:
        return status(404), headers['plain'], 'Dataset not found.'


# /ontology

def ontology():
    f = open('ontology.rdf')
    ont = f.read().replace('%%URL%%', config.ontology)
    f.close()
    return status(200), headers['rdf'], ont


# /sparql

rdflib.plugin.register('sparql', rdflib.query.Processor,
                       'rdfextras.sparql.processor', 'Processor')
rdflib.plugin.register('sparql', rdflib.query.Result,
                       'rdfextras.sparql.query', 'SPARQLQueryResult')

def sparql(query_string):
    store = rdflib.plugin.get(config.store, rdflib.store.Store)()
    store.open(config.connect)
    g = rdflib.ConjunctiveGraph(store)

    try:
        query = g.query(query_string)
    except Exception, e:
        return "Error!", str(e)
    else:
        return query.result
    finally:
        store.close()


def sparql_get(env):
    form = cgi.FieldStorage(fp=env['wsgi.input'], environ=env)
    if 'query' in form:
        return post(env)

    content = Template(filename='templates/sparql.front.mako',
                       module_directory='/tmp').render(ontology=config.ontology)
    return status(200), headers['html'], content

def sparql_post(env):
    form = cgi.FieldStorage(fp=env['wsgi.input'], environ=env)
    if 'query' not in form:
        return get(env)

    result = sparql(form.getfirst('query'))

    # TODO data formatting based on form flag

    content = Template(filename='templates/sparql.results.mako',
                       module_directory='/tmp').render(result=result)
    return status(200), headers['html'], content


# /submit

def submit(env):
    form = cgi.FieldStorage(fp=env['wsgi.input'], environ=env)
    triples = []

    ns = rdflib.Namespace(config.ontology)
    ds = rdflib.Namespace(config.datasets)

    # Create a new dataset URI

    our_id = get_new_id()
    node = ds[str(our_id)]
    triples.append((node, rdflib.RDF.type, ns['dataset']))


    # Translate form into RDF triples

    title = form.getfirst('title', '')
    triples.append((node, rdflib.RDFS.label, rdflib.Literal(title)))

    xlabel = form.getfirst('x-label', None)
    if xlabel:
        triples.append((node, ns['x-label'], rdflib.Literal(xlabel)))
    ylabel = form.getfirst('y-label', None)
    if ylabel:
        triples.append((node, ns['y-label'], rdflib.Literal(ylabel)))

    data = form.getfirst('data', None)
    if data is None:
        return status(400), 'Incomplete: no data.'
    triples.append((node, ns['data'], rdflib.Literal(data)))


    # Store the triples in the triplestore

    store = rdflib.plugin.get(config.store, rdflib.store.Store)()
    store.open(config.connect)
    g = rdflib.Graph(store)

    try:
        for t in triples:
            g.add(t)
        g.commit()
        g.close()
        store.close(True)
        return status(200), headers['plain'], str(our_id)
    except:
        store.close()
        return status(400), headers['plain'], 'Malformed'
