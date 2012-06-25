#!/usr/bin/python

import re
import urllib
import urllib2
import json
import os
import sys

_maps = {'xlabel': 'x-label', 'ylabel': 'y-label'}

class Dataset(object):
    """
    Interesting instance variables:
        title
        xlabel
        ylabel
        dataset
        updated
        data
        tags
    """

    def __init__(self, data=None, db='http://localhost:8081', **kwargs):
        """
        First argument should be a sequence of 2-tuples of integers or floats,
        or a sequence of complex numbers, or a sequence of integers or floats.
        In the latter case, indices are taken as X values. In any event, at
        least one entry is required.
        kwargs may include title, xlabel, ylabel.

        Alternatively, first arg could also be a str, in which case it's taken
        to be a URI pointing to RDF/XML, or an int, in which case we assume
        it's a pre-existing dataset in the working storage.

        If the first arg is None, it is taken to be equal to the environment
        variable DSETID, cast to int. If that's not set, argv[1] is used.

        Second argument should be the URL of the storage server.
        """
        self.db = db

        if data is None:
            data = os.getenv('DSETID')
            if not data:
                data = sys.argv[1]
            data = int(data)

        if isinstance(data, str):
            # Fetch from URI
            form = {}
            try:
                rdf = urllib2.urlopen(data).read()
            except urllib2.URLError, e:
                raise Exception('Invalid RDF resource: %s (%s).', (data, str(e)))

            # All resources should have data and a label
            # FIXME Dohoho parsing XML with regexes
            try:
                data = re.search('<ns1:data>([^<]*)</ns1:data>',
                                 rdf).group(1)
                title = re.search('<rdfs:label>([^<]*)</rdfs:label>',
                                  rdf).group(1)
            except:
                raise Exception('Malformed RDF resource.')

            data, formatted_data = self.__prep_data(data)
            object.__setattr__(self, 'data', data)
            form['data'] = formatted_data

            object.__setattr__(self, 'title', title)
            form['title'] = title

            # Everything else is optional
            m = re.search('<ns1:x-label>([^<]*)</ns1:x-label>', rdf)
            if m is not None:
                object.__setattr__(self, 'xlabel', m.group(1))
                form['x-label'] = m.group(1)
            else:
                object.__setattr__(self, 'xlabel', None)

            m = re.search('<ns1:y-label>([^<]*)</ns1:y-label>', rdf)
            if m is not None:
                object.__setattr__(self, 'ylabel', m.group(1))
                form['y-label'] = m.group(1)
            else:
                object.__setattr__(self, 'ylabel', None)

        elif isinstance(data, int):
            # Load existing dataset from working storage
            object.__setattr__(self, 'dataset', data)
            ret = urllib2.urlopen(urllib.basejoin(self.db, '/%d/json' % data))
            ds = json.loads(ret.read())
            ret.close()

            for k in ds.keys():
                object.__setattr__(self, k, ds[k])

            # TODO tags
            return

        else:
            # Everything we need is in the args
            data, formatted_data = self.__prep_data(data)
            object.__setattr__(self, 'data', data) 

            form = {'data': formatted_data}
            for field in 'title', 'xlabel', 'ylabel':
                form[_maps.get(field, field)] = kwargs.get(field, '')
                object.__setattr__(self, field, kwargs.get(field, None))

        form = urllib.urlencode(form)

        object.__setattr__(self, 'tags', [])

        ret = urllib2.urlopen(urllib2.Request(self.db, form)).read()
        dataset, self.updated = map(int, ret.split(','))
        object.__setattr__(self, 'dataset', dataset)

    def __getattribute__(self, name):
        """
        Overwritten to ensure data is always synchronised with the DB.
        """
        if name == 'data':
            # Check if remote data is unaltered
            url = urllib.basejoin(self.db, "/%d/diff" % self.dataset)
            updated = int(urllib2.urlopen(url).read())
            if self.updated != updated:
                # Fetch remote data
                url = urllib.basejoin(self.db, "/%d/py" % self.dataset)
                data, _ = self.__prep_data(urllib2.urlopen(url).read())
                object.__setattr__(self, 'data', data)
                self.updated = updated
        return object.__getattribute__(self, name)

    def __setattr__(self, name, value):
        """
        Overwritten to ensure data is always synchronised with the DB.
        """
        if name in ('title', 'xlabel', 'ylabel'):
            form = {_maps.get(name, name): value if value is not None else ''}
            form = urllib.urlencode(form)
            url = urllib.basejoin(self.db, str(self.dataset))
            self.updated = int(urllib2.urlopen(urllib2.Request(url,
                                                               form)).read())
        elif name == 'data':
            data, formatted_data = self.__prep_data(value)
            object.__setattr__(self, 'data', data)
            form = urllib.urlencode({'data': formatted_data})
            url = urllib.basejoin(self.db, str(self.dataset))
            self.updated = int(urllib2.urlopen(urllib2.Request(url,
                                                               form)).read())
        elif name == 'dataset':
            self.rewind(value)
        elif name == 'db':
            raise AttributeError("Can't change storage server!")
        object.__setattr__(self, name, value)

    def __repr__(self):
        args = tuple(map(repr, (self.data, self.title,
                                self.xlabel, self.ylabel)))
        return 'kplot.Dataset(%s, title=%s, xlabel=%s, ylabel=%s)' % args

    def __prep_data(self, data):
        """Marshalls data, returns list of tuples and DB-formatted data."""
        if isinstance(data, str) or isinstance(data, unicode):
            data = map(lambda s: tuple(map(float, s.split(','))),
                       data.split(';'))
        if isinstance(data[0], int) or isinstance(data[0], float):
            data = list(enumerate(data))
        elif isinstance(data[0], complex):
            data = [(a.real, a.imag) for a in data]

        formatted_data = ';'.join(map(lambda (a, b): str(a) + ',' + str(b),
                                      data))

        return data, formatted_data

    def __update_tags(self):
        url = urllib.basejoin(self.db, '/%d/tags' % self.dataset)
        object.__setattr__(self, 'tags', urllib.urlopen(url).read().split('\n'))

    def tag(self, s):
        """Tags current data as `s'."""
        form = {'tag': s}
        form = urllib.urlencode(form)
        url = urllib.basejoin(self.db, '/%d/tag/%d' % (self.dataset,
                                                         self.updated))
        ret = urllib2.urlopen(urllib2.Request(url, form)).read()
        assert int(ret) == self.updated
        self.__update_tags()

    def rewind(self, s):
        """Rewinds to given tag."""
        if isinstance(s, int):
            form = {'timestamp': s}
        else:
            form = {'tag': s}
        form = urllib.urlencode(form)
        url = urllib.basejoin(self.db, '/%d/rewind' % self.dataset)
        ret = urllib2.urlopen(urllib2.Request(url, form)).read()
        self.__update_tags()
        self.data
        return int(ret)

    def publish(self, server=None):
        """
        Publishes dataset to a given server, or to the default one.
        """
        if server is None:
            server = RDFServer()
        return server.publish(self)

    def plot(self, filename=None, open=False):
        if isinstance(filename, str):
            if filename[-4:].lower() != '.png':
                filename += ".png"
            os.system('kst --png %s %s' % (filename,
                                           urllib.basejoin(self.db, 
                                                           str(self.dataset),
                                                           'kst')))
            if open:
                os.system('xdg-open %s &' % filename)
        else:
            os.system('kst %s &' % urllib.basejoin(self.db,
                                                   str(self.dataset),
                                                   'kst'))


class RDFServer(object):
    """Represents a publishing server."""

    def __init__(self, host='http://localhost:8082'):
        self.host = host

    def sparql(self, query):
        """
        Executes given SPARQL query on this RDF server and returns the results.
        NOT FULLY IMPLEMENTED
        """
        form = {'query': query, 'type': 'json'}
        form = urllib.urlencode(form)
        url = urllib.basejoin(self.host, 'sparql')
        result = urllib2.urlopen(urllib2.Request(url, form)).read()

        # TODO parse JSON
        # TODO return results (as datasets?)

        return result

    def publish(self, ds):
        """
        Publishes dataset to this RDF server. Returns False for failure and
        True for success.
        """
        form = {'title': ds.title,
                'x-label': ds.xlabel or '', 'y-label': ds.ylabel or '',
                'data': ';'.join(map(lambda (a, b): str(a) + ',' + str(b),
                                     ds.data))}
        form = urllib.urlencode(form)
        url = urllib.basejoin(self.host, 'submit')

        try:
            did = int(urllib2.urlopen(urllib2.Request(url, form)).read())
        except ValueError:
            raise Exception('! %s', did)
        else:
            return urllib.basejoin(self.host, 'dataset/') + str(did)
